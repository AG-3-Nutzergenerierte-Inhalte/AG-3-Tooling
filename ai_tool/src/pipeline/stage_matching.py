"""
Core logic for Stage 'Matching': 1:1 Mapping.

This module is responsible for generating the 1:1 mappings between BSI
IT-Grundschutz Edition 2023 "Anforderungen" and G++ "Controls" using an AI model.
"""

import logging
import os
import asyncio
import re
from typing import Dict, Any, List, Set

from config import app_config
from constants import *
from clients.ai_client import AiClient
from utils import data_loader, data_parser

logger = logging.getLogger(__name__)


def _filter_markdown(
    control_ids: List[str], markdown_content: str
) -> str:
    """
    Filters a markdown table to include only rows with specified IDs.

    This function is more robust than a regex search as it processes the table
    line by line.

    Args:
        markdown_content: The full markdown table as a string.
        ids_to_keep: A set of IDs (e.g., "GPP.1.1", "SYS.1.1.A1") to retain.

    Returns:
        A string of the filtered markdown table, or an empty string if filtering fails.
    """

    if not control_ids:
        return ""

    lines = markdown_content.strip().splitlines()

    if len(lines) < 2:
        logger.warning("Markdown content is too short to contain a header and separator.")
        return ""

    header = lines[0]
    separator = lines[1]
    
    # Validate that the separator line looks correct
    if not separator.strip().startswith('|'):
        logger.warning("Markdown separator line is malformed.")
        return ""

    # Efficiently find all relevant rows in a single pass
    # This pattern ensures we match the full line for each control ID.
    # It looks for lines starting with '|', followed by spaces, the control ID, and then more characters.
    rows = []
    control_id_set = set(control_ids)
    for line in lines[2]:
        # Check if the line starts with one of the control IDs, formatted as a markdown table row.
        # Example: | GPP.10.1 | ...
        line_trimmed = line.strip()
        logger.warning(f"parts[1]: {line}")
        if line_trimmed.startswith('|'):
            parts = [p.strip() for p in line_trimmed.split('|')]
            if len(parts) > 2 and parts[1] in control_id_set:
                rows.append(line)

    if not rows:
        logger.warning(f"No rows found for control IDs: {control_ids}")
        return ""

    return "\n".join([header, separator] + rows)

async def run_stage_matching() -> None:
    """
    Executes the main steps for the matching stage.
    """
    logger.debug("Starting Stage 'Matching': 1:1 Mapping...")

    # --- Idempotency Check ---
    if (
        os.path.exists(CONTROLS_ANFORDERUNGEN_JSON_PATH)
        and not app_config.overwrite_temp_files
    ):
        logger.info(
            "Output file already exists and OVERWRITE_TEMP_FILES is false. "
            "Skipping Matching Stage."
        )
        return

    # --- Initialize AI Client ---
    ai_client = AiClient(app_config)
    prompt_config = data_loader.load_json_file(PROMPT_CONFIG_PATH)
    matching_schema = data_loader.load_json_file(MATCHING_SCHEMA_PATH)


    # --- Load Data ---
    bausteine_zielobjekte_map = data_loader.load_json_file(
        BAUSTEINE_ZIELOBJEKTE_JSON_PATH
    ).get("bausteine_zielobjekte_map", {})
    zielobjekt_controls_map = data_loader.load_json_file(
        ZIELOBJEKT_CONTROLS_JSON_PATH
    ).get("zielobjekt_controls_map", {})
    zielobjekte_data = data_loader.load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
    zielobjekte_hierarchy = data_parser.parse_zielobjekte_hierarchy(zielobjekte_data)


    gpp_stripped_md = data_loader.load_text_file(GPP_STRIPPED_MD_PATH)
    gpp_stripped_isms_md = data_loader.load_text_file(GPP_STRIPPED_ISMS_MD_PATH)
    bsi_stripped_md = data_loader.load_text_file(BSI_STRIPPED_MD_PATH)

    # --- Main Processing Logic ---
    final_output: Dict[str, Any] = {}

    pairs_to_process = (
        list(bausteine_zielobjekte_map.items())[:3]
        if app_config.is_test_mode
        else bausteine_zielobjekte_map.items()
    )

    for baustein_id, zielobjekt_uuid in pairs_to_process:
        logger.debug(f"Processing mapping for Baustein '{baustein_id}' and Zielobjekt '{zielobjekt_uuid}'...")

        gpp_control_ids = zielobjekt_controls_map.get(zielobjekt_uuid, [])
        if not gpp_control_ids:
            logger.warning(f"No G++ controls found for Zielobjekt {zielobjekt_uuid}. Skipping.")
            continue

        # Select correct GPP markdown source
        gpp_source_md = (
            gpp_stripped_isms_md
            if baustein_id.startswith("ISMS")
            else gpp_stripped_md
        )

        # Filter markdown files
        filtered_gpp_md = _filter_markdown(gpp_control_ids, gpp_source_md)
        filtered_bsi_md = _filter_markdown(baustein_id, bsi_stripped_md)

        if not filtered_gpp_md or not filtered_bsi_md:
            logger.error(f"Could not create filtered markdown for Baustein {baustein_id}. Skipping.")
            continue

        # --- Call AI Model ---
        prompt_template = prompt_config["anforderung_to_kontrolle_1_1_prompt"]

        # The context (markdown tables) must be part of the main prompt string.
        full_prompt = (
            f"{prompt_template}\n\n"
            f"Ed2023 Source:\n{filtered_bsi_md}\n\n"
            f"G++ Source:\n{filtered_gpp_md}"
        )

        # Corrected AI client call with valid arguments.
        ai_response = await ai_client.generate_validated_json_response(
            prompt=full_prompt,
            json_schema=matching_schema,
            request_context_log=f"AnforderungToKontrolle-{baustein_id}",
            model_override=GROUND_TRUTH_MODEL_PRO # Use the more powerful model for this complex task
        )


        # --- Validate Response ---
        if not ai_response:
            logger.error(f"AI response was empty for Baustein {baustein_id}. Skipping.")
            continue

        validated_response = ai_response

        # --- Aggregate Results ---
        zielobjekt_name = zielobjekte_hierarchy.get(zielobjekt_uuid, {}).get("Zielobjekt", "Unknown")
        final_output[zielobjekt_uuid] = {
            "zielobjekt_name": zielobjekt_name,
            "baustein_id": baustein_id,
            "mapping": validated_response.get("mapping", {}),
            "unmapped_gpp": validated_response.get("unmapped_gpp", []),
            "unmapped_ed2023": validated_response.get("unmapped_ed2023", []),
        }

    # --- Save Output ---
    data_loader.save_json_file(final_output, CONTROLS_ANFORDERUNGEN_JSON_PATH)

    logger.info("Stage 'Matching' completed successfully.")