"""
Core logic for Phase 0: Crosswalk Curation.

This module is responsible for generating the initial 1:1 mappings
between BSI IT-Grundschutz Edition 2023 "Bausteine" and G++ "Zielobjekte",
and between BSI "Anforderungen" and G++ "Controls".
"""

import logging
import os
import asyncio
from typing import Dict, Any, List, Set

from config import app_config
from constants import *
from clients.ai_client import AiClient
from .stage_0_tasks import inheritance, matching
from utils import data_loader, data_parser

logger = logging.getLogger(__name__)


async def run_phase_0() -> None:
    """
    Executes the main steps for Phase 0 to generate the crosswalk files asynchronously.
    """
    logger.debug("Starting Phase 0: Crosswalk Curation...")

    # --- Idempotency Check ---
    if (
        os.path.exists(BAUSTEINE_ZIELOBJEKTE_JSON_PATH)
        and os.path.exists(ZIELOBJEKT_CONTROLS_JSON_PATH)
        and not app_config.overwrite_temp_files
    ):
        logger.info(
            "Output files already exist and OVERWRITE_TEMP_FILES is false. "
            "Skipping Phase 0."
        )
        return

    # --- Initialize AI Client ---
    ai_client = AiClient(app_config)
    prompt_config = data_loader.load_json_file(PROMPT_CONFIG_PATH)
    baustein_schema = data_loader.load_json_file(BAUSTEIN_TO_ZIELOBJEKT_SCHEMA_PATH)


    # --- Load Data ---
    zielobjekte_data = data_loader.load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
    bsi_2023_data = data_loader.load_json_file(BSI_2023_JSON_PATH)
    gpp_kompendium_data = data_loader.load_json_file(GPP_KOMPENDIUM_JSON_PATH)

    # --- Parse Data ---
    zielobjekte_map = data_parser.parse_zielobjekte_hierarchy(zielobjekte_data)
    bausteine, filtered_out_bausteine = data_parser.parse_bsi_2023_controls(
        bsi_2023_data
    )
    if filtered_out_bausteine:
        logger.info(
            f"{len(filtered_out_bausteine)} Bausteine have been filtered out "
            "and will be processed in a later stage."
        )
    (
        zielobjekt_to_gpp_controls_map,
        gpp_control_titles,
    ) = data_parser.parse_gpp_kompendium_controls(gpp_kompendium_data)

    # --- Main Processing Logic ---
    # Generate the deterministic control map for all Zielobjekte
    zielobjekt_controls_output = (
        inheritance.generate_full_zielobjekt_controls_map(
            zielobjekte_map, zielobjekt_to_gpp_controls_map, gpp_control_titles
        )
    )

    # Perform the AI-based matching of Bausteine to Zielobjekte
    bausteine_zielobjekte_map: Dict[str, str] = {}
    bausteine_to_process = bausteine[:3] if app_config.is_test_mode else bausteine

    sem = asyncio.Semaphore(10)

    async def process_baustein_with_semaphore(
        baustein: Dict[str, Any]
    ) -> (Dict[str, Any], str | None):
        """Processes a single Baustein, acquiring the semaphore before the AI call."""
        async with sem:
            matched_zielobjekt_uuid = await matching.match_baustein_to_zielobjekt(
                ai_client,
                baustein,
                zielobjekte_map,
                prompt_config["baustein_to_zielobjekt_prompt"],
                baustein_schema,
            )
            return baustein, matched_zielobjekt_uuid

    tasks = [
        process_baustein_with_semaphore(baustein) for baustein in bausteine_to_process
    ]
    results = await asyncio.gather(*tasks)

    for baustein, matched_zielobjekt_uuid in results:
        if matched_zielobjekt_uuid:
            # Add a check to ensure the matched UUID is valid
            if matched_zielobjekt_uuid in zielobjekte_map:
                bausteine_zielobjekte_map[baustein["id"]] = matched_zielobjekt_uuid
            else:
                logger.warning(
                    f"AI returned a non-existent Zielobjekt UUID: "
                    f"{matched_zielobjekt_uuid} for Baustein {baustein['id']}. "
                    "This mapping will be skipped."
                )

    # --- Format and Save Output ---
    bausteine_output = {"bausteine_zielobjekte_map": bausteine_zielobjekte_map}
    data_loader.save_json_file(
        bausteine_output, BAUSTEINE_ZIELOBJEKTE_JSON_PATH
    )

    zielobjekt_controls_output_final = {"zielobjekt_controls_map": zielobjekt_controls_output}
    data_loader.save_json_file(
        zielobjekt_controls_output_final, ZIELOBJEKT_CONTROLS_JSON_PATH
    )

    logger.info("Phase 0 completed successfully.")
