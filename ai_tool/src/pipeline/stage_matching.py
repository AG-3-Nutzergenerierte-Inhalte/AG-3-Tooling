"""
Core logic for Stage 'Matching': Mapping Sub-Requirements to Controls.

This module is responsible for generating the mappings between decomposed BSI
IT-Grundschutz Edition 2023 "Anforderungen" (sub-requirements) and G++ "Controls"
using an AI model.
"""

import logging
import os
import sys
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from config import app_config
from constants import *
from clients.ai_client import AiClient
from utils import data_loader, data_parser

logger = logging.getLogger(__name__)


def _create_sub_requirement_markdown(sub_requirements: List[Dict[str, str]]) -> str:
    """
    Creates a markdown table from a list of sub-requirements.
    """
    if not sub_requirements:
        return ""

    header = "| Sub-Requirement ID | Description |\n|---|---|\n"
    rows = [f"| {sr['id']} | {sr['description']} |" for sr in sub_requirements]
    return header + "\n".join(rows)


def _validate_mapping_keys(mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Validates that the keys in the mapping dictionary match the sub-requirement ID format.
    """
    if not mapping:
        return {}

    validated_mapping = {}
    for key, value in mapping.items():
        if "_sub_" in key:  # Simple check for sub-requirement format
            validated_mapping[key] = value
        else:
            logger.warning(f"Invalid key '{key}' in AI response mapping. Discarding.")
    return validated_mapping


def _filter_markdown(
    control_ids: List[str], markdown_content: str
) -> str:
    """
    Filters a markdown table to include only rows with specified IDs.
    """
    if not control_ids:
        return ""
    lines = markdown_content.strip().splitlines()
    if len(lines) < 2:
        return ""
    header = lines[0]
    separator = lines[1]
    rows = [line for line in lines[2:] if any(f"| {cid} |" in line for cid in control_ids)]
    if not rows:
        return ""
    return "\n".join([header, separator] + rows)


async def _process_mapping(
    baustein_id: str,
    zielobjekt_uuid: str,
    ai_client: AiClient,
    zielobjekt_controls_map: Dict[str, List[str]],
    gpp_stripped_isms_md: str,
    gpp_stripped_md: str,
    decomposed_anforderungen: Dict[str, List[Dict[str, str]]],
    prompt_config: Dict[str, Any],
    matching_schema: Dict[str, Any],
    zielobjekte_hierarchy: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Processes a single mapping between a Baustein's sub-requirements and a Zielobjekt's controls.
    """
    logger.info(f"Processing mapping for Baustein '{baustein_id}' and Zielobjekt '{zielobjekt_uuid}'...")

    gpp_control_ids = zielobjekt_controls_map.get(zielobjekt_uuid, [])
    if not gpp_control_ids:
        logger.warning(f"No G++ controls found for Zielobjekt {zielobjekt_uuid}. Skipping.")
        return None

    baustein_main_group = baustein_id.split('.')[0]
    gpp_source_md = gpp_stripped_md if baustein_main_group in ALLOWED_MAIN_GROUPS else gpp_stripped_isms_md

    sub_requirements = decomposed_anforderungen.get(baustein_id, [])
    if not sub_requirements:
        logger.warning(f"No sub-requirements found for Baustein {baustein_id}. Skipping.")
        return None

    filtered_gpp_md = _filter_markdown(gpp_control_ids, gpp_source_md)
    sub_requirements_md = _create_sub_requirement_markdown(sub_requirements)

    if not filtered_gpp_md or not sub_requirements_md:
        logger.error(f"Could not create filtered markdown for Baustein {baustein_id}. Skipping.")
        return None

    prompt_template = prompt_config["anforderung_to_kontrolle_1_1_prompt"]
    full_prompt = (
        f"{prompt_template}\n\n"
        f"Ed2023 Source:\n{sub_requirements_md}\n\n"
        f"G++ Source:\n{filtered_gpp_md}"
    )

    async with semaphore:
        ai_response = await ai_client.generate_validated_json_response(
            prompt=full_prompt,
            json_schema=matching_schema,
            request_context_log=f"SubRequirementToControl-{baustein_id}",
            model_override=GROUND_TRUTH_MODEL_PRO
        )

    if not ai_response:
        logger.error(f"AI response was empty for Baustein {baustein_id}. Skipping.")
        return None

    validated_mapping = _validate_mapping_keys(ai_response.get("mapping", {}))
    zielobjekt_name = zielobjekte_hierarchy.get(zielobjekt_uuid, {}).get("Zielobjekt", "Unknown")
    result = {
        "zielobjekt_name": zielobjekt_name,
        "baustein_id": baustein_id,
        "mapping": validated_mapping,
        "unmapped_gpp": ai_response.get("unmapped_gpp", []),
        "unmapped_ed2023": ai_response.get("unmapped_ed2023", []),
    }
    return zielobjekt_uuid, result


async def run_stage_matching() -> None:
    """
    Executes the main steps for the matching stage.
    """
    logger.info("Starting Stage 'Matching': Mapping of Sub-Requirements to controls")

    if os.path.exists(CONTROLS_ANFORDERUNGEN_JSON_PATH) and not app_config.overwrite_temp_files:
        logger.info("Output file already exists and OVERWRITE_TEMP_FILES is false. Skipping Matching Stage.")
        return

    try:
        ai_client = AiClient(app_config)
        prompt_config = data_loader.load_json_file(PROMPT_CONFIG_PATH)
        matching_schema = data_loader.load_json_file(MATCHING_SCHEMA_PATH)
        baustein_zielobjekt_map = data_loader.load_json_file(BAUSTEIN_ZIELOBJEKT_JSON_PATH).get("baustein_zielobjekt_map", {})
        zielobjekt_controls_map = data_loader.load_json_file(ZIELOBJEKT_CONTROLS_JSON_PATH).get("zielobjekt_controls_map", {})
        zielobjekte_data = data_loader.load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
        zielobjekte_hierarchy = data_parser.parse_zielobjekte_hierarchy(zielobjekte_data)
        decomposed_data = data_loader.load_json_file(DECOMPOSED_ANFORDERUNGEN_JSON_PATH).get("decomposed_anforderungen", [])

        decomposed_anforderungen = {}
        for item in decomposed_data:
            baustein_id = ".".join(item["original_anforderung_id"].split(".")[:2])
            if baustein_id not in decomposed_anforderungen:
                decomposed_anforderungen[baustein_id] = []
            decomposed_anforderungen[baustein_id].extend(item["sub_requirements"])

        gpp_stripped_md = data_loader.load_text_file(GPP_STRIPPED_MD_PATH)
        gpp_stripped_isms_md = data_loader.load_text_file(GPP_STRIPPED_ISMS_MD_PATH)

    except (FileNotFoundError, IOError, KeyError) as e:
        logger.error(f"Failed to load required data for matching stage: {e}")
        sys.exit(1)

    final_output: Dict[str, Any] = {}
    semaphore = asyncio.Semaphore(app_config.max_concurrent_ai_requests)
    pairs_to_process = list(baustein_zielobjekt_map.items())
    if app_config.is_test_mode:
        pairs_to_process = pairs_to_process[:3]

    tasks = [
        _process_mapping(
            baustein_id,
            zielobjekt_uuid,
            ai_client,
            zielobjekt_controls_map,
            gpp_stripped_isms_md,
            gpp_stripped_md,
            decomposed_anforderungen,
            prompt_config,
            matching_schema,
            zielobjekte_hierarchy,
            semaphore,
        )
        for baustein_id, zielobjekt_uuid in pairs_to_process
    ]

    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            zielobjekt_uuid, data = result
            if zielobjekt_uuid not in final_output:
                final_output[zielobjekt_uuid] = []
            final_output[zielobjekt_uuid].append(data)

    if not final_output:
        logger.critical("No successful AI mappings were generated. Aborting stage.")
        sys.exit(1)

    data_loader.save_json_file(final_output, CONTROLS_ANFORDERUNGEN_JSON_PATH)
    logger.info("Stage 'Matching' completed successfully.")
