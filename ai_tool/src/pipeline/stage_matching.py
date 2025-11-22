"""
Core logic for Stage 'Matching': 1:1 Mapping.

This module is responsible for generating the 1:1 mappings between BSI
IT-Grundschutz Edition 2023 "Anforderungen" and G++ "Controls" using an AI model.
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



def _validate_mapping_keys(mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Validates that the keys in the mapping dictionary match the Anforderung ID format.

    Args:
        mapping: The mapping dictionary from the AI response.

    Returns:
        A new dictionary containing only the valid key-value pairs.
    """
    if not mapping:
        return {}

    validated_mapping = {}
    for key, value in mapping.items():
        if ANFORDERUNG_ID_PATTERN.match(key):
            validated_mapping[key] = value
        else:
            logger.warning(f"Invalid key '{key}' in AI response mapping. Discarding.")
    return validated_mapping


async def _process_mapping(
    baustein_id: str,
    zielobjekt_uuid: str,
    ai_client: AiClient,
    zielobjekt_controls_map: Dict[str, List[str]],
    gpp_stripped_isms_md: str,
    gpp_stripped_md: str,
    bsi_stripped_md: str,
    prompt_config: Dict[str, Any],
    matching_schema: Dict[str, Any],
    zielobjekte_hierarchy: Dict[str, Any],
    baustein_anforderungen_map: Dict[str, List[str]],
    semaphore: asyncio.Semaphore,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Processes a single mapping between a Baustein and a Zielobjekt.
    """
    logger.info(f"Processing mapping for Baustein '{baustein_id}' and Zielobjekt '{zielobjekt_uuid}'...")

    gpp_control_ids = zielobjekt_controls_map.get(zielobjekt_uuid, [])
    if not gpp_control_ids:
        logger.warning(f"No G++ controls found for Zielobjekt {zielobjekt_uuid}. Skipping.")
        return None

    # Technical Bausteine are mapped against technical G++ controls.
    # Process Bausteine (ISMS, ORP, etc.) are mapped against ISMS G++ controls.
    baustein_main_group = baustein_id.split(".")[0]
    gpp_source_md = (
        gpp_stripped_md
        if baustein_main_group in ALLOWED_MAIN_GROUPS
        or baustein_id in ALLOWED_PROCESS_BAUSTEINE
        else gpp_stripped_isms_md
    )

    anforderung_ids = baustein_anforderungen_map.get(baustein_id, [])
    if not anforderung_ids:
        logger.warning(f"No Anforderungen found for Baustein {baustein_id}. Skipping.")
        return None

    filtered_gpp_md = data_parser.filter_markdown(gpp_control_ids, gpp_source_md)
    filtered_bsi_md = data_parser.filter_markdown(anforderung_ids, bsi_stripped_md)

    if not filtered_gpp_md or not filtered_bsi_md:
        logger.error(f"Could not create filtered markdown for Baustein {baustein_id}. Skipping.")
        return None

    prompt_template = prompt_config["anforderung_to_kontrolle_1_1_prompt"]
    full_prompt = (
        f"{prompt_template}\n\n"
        f"Ed2023 Source:\n{filtered_bsi_md}\n\n"
        f"G++ Source:\n{filtered_gpp_md}"
    )

    # logger.debug(f"full promt: {full_prompt}")

    async with semaphore:
        ai_response = await ai_client.generate_validated_json_response(
            prompt=full_prompt,
            json_schema=matching_schema,
            request_context_log=f"AnforderungToKontrolle-{baustein_id}",
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
    logger.info("Starting Stage 'Matching': 1:1 Mapping of Anforderungen to controls")

    if os.path.exists(CONTROLS_ANFORDERUNGEN_JSON_PATH) and not app_config.overwrite_temp_files:
        logger.info("Output file already exists and OVERWRITE_TEMP_FILES is false. Skipping Matching Stage.")
        return

    try:
        ai_client = AiClient(app_config)
        prompt_config = data_loader.load_json_file(PROMPT_CONFIG_PATH)
        matching_schema = data_loader.load_json_file(MATCHING_SCHEMA_PATH)

        baustein_zielobjekt_data = data_loader.load_json_file(
            BAUSTEIN_ZIELOBJEKT_JSON_PATH
        )
        zielobjekt_controls_data = data_loader.load_json_file(
            ZIELOBJEKT_CONTROLS_JSON_PATH
        )
        zielobjekte_data = data_loader.load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
        zielobjekte_hierarchy = data_parser.parse_zielobjekte_hierarchy(zielobjekte_data)
        bsi_data = data_loader.load_json_file(BSI_2023_JSON_PATH)

        # Validate that all essential data was loaded before parsing
        loaded_data_checks = {
            PROMPT_CONFIG_PATH: prompt_config,
            MATCHING_SCHEMA_PATH: matching_schema,
            BAUSTEIN_ZIELOBJEKT_JSON_PATH: baustein_zielobjekt_data,
            ZIELOBJEKT_CONTROLS_JSON_PATH: zielobjekt_controls_data,
            ZIELOBJEKTE_CSV_PATH: zielobjekte_data,
            BSI_2023_JSON_PATH: bsi_data,
        }
        for path, data in loaded_data_checks.items():
            if not data:
                logger.error(f"Essential data file is empty or failed to load: {path}")
                sys.exit(1)

        # Now that we've validated the files, we can safely extract the nested data.
        baustein_zielobjekt_map = baustein_zielobjekt_data.get("baustein_zielobjekt_map", {})
        if not baustein_zielobjekt_map:
            logger.error(f"The 'baustein_zielobjekt_map' key in {BAUSTEIN_ZIELOBJEKT_JSON_PATH} is empty. No Baustein-Zielobjekt mappings found.")
            sys.exit(1)

        zielobjekt_controls_map = zielobjekt_controls_data.get("zielobjekt_controls_map", {})
        if not zielobjekt_controls_map:
            logger.error(f"The 'zielobjekt_controls_map' key in {ZIELOBJEKT_CONTROLS_JSON_PATH} is empty. No Zielobjekt-Control mappings found.")
            sys.exit(1)

        baustein_anforderungen_map = data_parser.get_anforderungen_for_bausteine(bsi_data)
        if not baustein_anforderungen_map:
            logger.error(f"Could not parse any 'Anforderungen' from {BSI_2023_JSON_PATH}. The resulting map is empty.")
            sys.exit(1)

        gpp_stripped_md = data_loader.load_text_file(GPP_STRIPPED_MD_PATH)
        gpp_stripped_isms_md = data_loader.load_text_file(GPP_STRIPPED_ISMS_MD_PATH)
        bsi_stripped_md = data_loader.load_text_file(BSI_STRIPPED_MD_PATH)

        # Validate that all essential data was loaded
        text_file_checks = {
            GPP_STRIPPED_MD_PATH: gpp_stripped_md,
            GPP_STRIPPED_ISMS_MD_PATH: gpp_stripped_isms_md,
            BSI_STRIPPED_MD_PATH: bsi_stripped_md,
        }
        for path, data in text_file_checks.items():
            if not data:
                logger.error(f"Essential data file is empty or failed to load: {path}")
                sys.exit(1)

    except (FileNotFoundError, IOError, KeyError) as e:
        logger.error(f"Failed to load required data for matching stage: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during data loading: {e}")
        sys.exit(1)

    final_output: Dict[str, Any] = {}
    semaphore = asyncio.Semaphore(app_config.max_concurrent_ai_requests)

    # Determine the pairs to process based on test mode
    all_pairs = list(baustein_zielobjekt_map.items())
    if not all_pairs:
        logger.critical(
            f"The baustein-to-zielobjekt map from '{BAUSTEIN_ZIELOBJEKT_JSON_PATH}' is empty. No pairs to process. Aborting."
        )
        sys.exit(1)

    pairs_to_process = all_pairs[:3] if app_config.is_test_mode else all_pairs

    tasks = [
        _process_mapping(
            baustein_id,
            zielobjekt_uuid,
            ai_client,
            zielobjekt_controls_map,
            gpp_stripped_isms_md,
            gpp_stripped_md,
            bsi_stripped_md,
            prompt_config,
            matching_schema,
            zielobjekte_hierarchy,
            baustein_anforderungen_map,
            semaphore,
        )
        for baustein_id, zielobjekt_uuid in pairs_to_process
    ]

    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            zielobjekt_uuid, data = result
            final_output[zielobjekt_uuid] = data

    if not final_output:
        logger.critical("No successful AI mappings were generated after processing all pairs. The output file would be empty. Aborting stage.")
        sys.exit(1)

    data_loader.save_json_file(final_output, CONTROLS_ANFORDERUNGEN_JSON_PATH)
    logger.info("Stage 'Matching' completed successfully.")
