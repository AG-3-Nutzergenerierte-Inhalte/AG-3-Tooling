"""
Core logic for Stage 'Metadata Generation': Regenerating Metadata for Mappings.

This module is responsible for regenerating metadata, such as maturity levels and
phases, for the new sub-requirement-to-control mappings using an AI model.
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


async def _process_metadata_generation(
    sub_requirement_id: str,
    gpp_control_id: str,
    sub_requirement_text: str,
    gpp_control_text: str,
    ai_client: AiClient,
    prompt_config: Dict[str, Any],
    metadata_generation_schema: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Dict[str, str]:
    """
    Processes a single metadata generation.
    """
    logger.info(f"Generating metadata for sub-requirement '{sub_requirement_id}' and control '{gpp_control_id}'...")

    prompt_template = prompt_config["metadata_generation_prompt"]
    full_prompt = prompt_template.format(
        sub_requirement_text=sub_requirement_text, gpp_control_text=gpp_control_text
    )

    async with semaphore:
        ai_response = await ai_client.generate_validated_json_response(
            prompt=full_prompt,
            json_schema=metadata_generation_schema,
            request_context_log=f"MetadataGeneration-{sub_requirement_id}-{gpp_control_id}",
        )

    if not ai_response:
        logger.error(f"AI response was empty for sub-requirement {sub_requirement_id}. Skipping.")
        return {}

    return ai_response.get("generated_metadata", [{}])[0]


async def run_stage_metadata_generation() -> None:
    """
    Executes the main steps for the metadata generation stage.
    """
    logger.info("Starting Stage 'Metadata Generation': Regenerating Metadata for Mappings")

    if os.path.exists(GENERATED_METADATA_JSON_PATH) and not app_config.overwrite_temp_files:
        logger.info("Output file already exists and OVERWRITE_TEMP_FILES is false. Skipping Metadata Generation Stage.")
        return

    try:
        ai_client = AiClient(app_config)
        prompt_config = data_loader.load_json_file(PROMPT_CONFIG_PATH)
        metadata_generation_schema = data_loader.load_json_file(METADATA_GENERATION_SCHEMA_PATH)
        controls_anforderungen = data_loader.load_json_file(CONTROLS_ANFORDERUNGEN_JSON_PATH)
        decomposed_anforderungen = data_loader.load_json_file(DECOMPOSED_ANFORDERUNGEN_JSON_PATH)
        gpp_data = data_loader.load_json_file(GPP_KOMPENDIUM_JSON_PATH)

        sub_requirement_texts = {
            sub_req["id"]: sub_req["description"]
            for anforderung in decomposed_anforderungen["decomposed_anforderungen"]
            for sub_req in anforderung["sub_requirements"]
        }
        gpp_control_texts = data_parser.get_gpp_control_texts(gpp_data)

    except (FileNotFoundError, IOError, KeyError) as e:
        logger.error(f"Failed to load required data for metadata generation stage: {e}")
        sys.exit(1)

    final_output = {"generated_metadata": []}
    semaphore = asyncio.Semaphore(app_config.max_concurrent_ai_requests)

    tasks = []
    for zielobjekt in controls_anforderungen.values():
        for baustein in zielobjekt:
            for sub_req_id, gpp_control_id in baustein["mapping"].items():
                tasks.append(
                    _process_metadata_generation(
                        sub_req_id,
                        gpp_control_id,
                        sub_requirement_texts.get(sub_req_id, ""),
                        gpp_control_texts.get(gpp_control_id, ""),
                        ai_client,
                        prompt_config,
                        metadata_generation_schema,
                        semaphore,
                    )
                )

    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            final_output["generated_metadata"].append(result)

    if not final_output["generated_metadata"]:
        logger.critical("No successful metadata generations were generated. Aborting stage.")
        sys.exit(1)

    data_loader.save_json_file(final_output, GENERATED_METADATA_JSON_PATH)
    logger.info("Stage 'Metadata Generation' completed successfully.")
