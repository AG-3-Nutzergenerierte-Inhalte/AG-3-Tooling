"""
Core logic for Stage 'Decomposition': Decomposing BSI Anforderungen.

This module is responsible for decomposing BSI IT-Grundschutz Edition 2023
"Anforderungen" into more granular sub-requirements using an AI model.
"""

import logging
import os
import sys
import asyncio
from typing import Dict, Any, List

from config import app_config
from constants import *
from clients.ai_client import AiClient
from utils import data_loader, data_parser

logger = logging.getLogger(__name__)


async def _process_anforderung_decomposition(
    anforderung_id: str,
    anforderung_text: str,
    ai_client: AiClient,
    prompt_config: Dict[str, Any],
    decomposition_schema: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> List[Dict[str, str]]:
    """
    Processes a single Anforderung decomposition.
    """
    logger.info(f"Decomposing Anforderung '{anforderung_id}'...")

    prompt_template = prompt_config["decomposition_prompt"]
    full_prompt = prompt_template.format(anforderung_text=anforderung_text)

    async with semaphore:
        ai_response = await ai_client.generate_validated_json_response(
            prompt=full_prompt,
            json_schema=decomposition_schema,
            request_context_log=f"Decomposition-{anforderung_id}",
        )

    if not ai_response:
        logger.error(f"AI response was empty for Anforderung {anforderung_id}. Skipping.")
        return []

    return ai_response.get("decomposed_anforderungen", [])


async def run_stage_decomposition() -> None:
    """
    Executes the main steps for the decomposition stage.
    """
    logger.info("Starting Stage 'Decomposition': Decomposing BSI Anforderungen")

    if os.path.exists(DECOMPOSED_ANFORDERUNGEN_JSON_PATH) and not app_config.overwrite_temp_files:
        logger.info("Output file already exists and OVERWRITE_TEMP_FILES is false. Skipping Decomposition Stage.")
        return

    try:
        ai_client = AiClient(app_config)
        prompt_config = data_loader.load_json_file(PROMPT_CONFIG_PATH)
        decomposition_schema = data_loader.load_json_file(DECOMPOSITION_SCHEMA_PATH)
        bsi_data = data_loader.load_json_file(BSI_2023_JSON_PATH)
        anforderungen_map = data_parser.get_anforderungen_for_bausteine(bsi_data)

    except (FileNotFoundError, IOError, KeyError) as e:
        logger.error(f"Failed to load required data for decomposition stage: {e}")
        sys.exit(1)

    final_output = {"decomposed_anforderungen": []}
    semaphore = asyncio.Semaphore(app_config.max_concurrent_ai_requests)

    tasks = [
        _process_anforderung_decomposition(
            anforderung_id,
            anforderung_text,
            ai_client,
            prompt_config,
            decomposition_schema,
            semaphore,
        )
        for anforderung_id, anforderung_text in anforderungen_map.items()
    ]

    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            final_output["decomposed_anforderungen"].extend(result)

    if not final_output["decomposed_anforderungen"]:
        logger.critical("No successful decompositions were generated. Aborting stage.")
        sys.exit(1)

    data_loader.save_json_file(final_output, DECOMPOSED_ANFORDERUNGEN_JSON_PATH)
    logger.info("Stage 'Decomposition' completed successfully.")
