"""
This module contains the logic for matching BSI Bausteine to G++ Zielobjekte.
"""
import asyncio
import logging
from typing import Dict, Any, List

from ..clients.ai_client import AiClient
from ..utils.data_loader import load_json_file, save_json_file, load_zielobjekte_csv
from ..utils.data_parser import find_bausteine_with_prose
from ..constants import (
    BSI_2023_JSON_PATH,
    ZIELOBJEKTE_CSV_PATH,
    PROMPT_CONFIG_PATH,
    BAUSTEIN_TO_ZIELOBJEKT_SCHEMA_PATH,
    BAUSTEINE_ZIELOBJEKTE_JSON_PATH,
)

logger = logging.getLogger(__name__)


async def match_baustein_to_zielobjekt(
    ai_client: AiClient,
    baustein: Dict[str, Any],
    zielobjekte_map: Dict[str, Any],
    prompt_instruction: str,
    schema: Dict[str, Any],
) -> tuple[str, str | None]:
    """
    Matches a BSI Baustein to the best G++ Zielobjekt using an AI model.
    Returns the Baustein ID and the matched Zielobjekt UUID.
    """
    baustein_id = baustein.get("id", "unknown")
    zielobjekte_choices = "\n".join(
        [
            f"* {data.get('Zielobjekt', '')}: {data.get('Definition', '')}"
            for data in zielobjekte_map.values()
        ]
    )

    prompt = (
        f"{prompt_instruction}\n\n"
        f"**BSI Baustein to Match:**\n"
        f"* Title: {baustein.get('title', '')}\n"
        f"* Description: {baustein.get('description', '')}\n\n"
        f"**Available G++ Zielobjekte:**\n"
        f"{zielobjekte_choices}\n\n"
        "Based on the information above, which is the best match?"
    )

    zielobjekt_names = [data.get("Zielobjekt", "") for data in zielobjekte_map.values()]
    dynamic_schema = schema.copy()
    dynamic_schema["properties"]["matched_zielobjekt"]["enum"] = zielobjekt_names

    response_json = await ai_client.generate_validated_json_response(
        prompt=prompt,
        json_schema=dynamic_schema,
        request_context_log=f"BausteinToZielobjekt-{baustein_id}",
    )

    matched_zielobjekt_name = response_json.get("matched_zielobjekt")

    if matched_zielobjekt_name:
        for uuid, data in zielobjekte_map.items():
            if data.get("Zielobjekt") == matched_zielobjekt_name:
                logger.info(
                    f"Successfully matched Baustein '{baustein.get('title')}' to "
                    f"Zielobjekt '{matched_zielobjekt_name}' (UUID: {uuid})."
                )
                return baustein_id, uuid

    logger.warning(f"Could not find a suitable match for Baustein '{baustein_id}'.")
    return baustein_id, None


async def _run_matching_tasks(
    ai_client: AiClient,
    bausteine: List[Dict[str, Any]],
    zielobjekte_map: Dict[str, Any],
    prompt_instruction: str,
    schema: Dict[str, Any],
) -> Dict[str, str]:
    """
    Creates and runs concurrent matching tasks for all Bausteine.
    """
    tasks = [
        match_baustein_to_zielobjekt(
            ai_client, baustein, zielobjekte_map, prompt_instruction, schema
        )
        for baustein in bausteine
    ]
    results = await asyncio.gather(*tasks)

    # Filter out None results and construct the final map
    baustein_zielobjekt_map = {
        baustein_id: zielobjekt_uuid
        for baustein_id, zielobjekt_uuid in results
        if zielobjekt_uuid is not None
    }
    return baustein_zielobjekt_map


def run_stage_match_bausteine():
    """
    Main function to run the Baustein-to-Zielobjekt matching stage.
    """
    logger.info("Starting stage_match_bausteine...")

    # Load all necessary data
    bsi_data = load_json_file(BSI_2023_JSON_PATH)
    zielobjekte_data = load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
    prompt_config = load_json_file(PROMPT_CONFIG_PATH)
    schema = load_json_file(BAUSTEIN_TO_ZIELOBJEKT_SCHEMA_PATH)

    # Prepare data for matching
    bausteine_with_prose = find_bausteine_with_prose(bsi_data)
    zielobjekte_map = {
        z["GART_Objekt_UUID"]: {"Zielobjekt": z["Zielobjekt"], "Definition": z.get("Definition", "")}
        for z in zielobjekte_data if "GART_Objekt_UUID" in z
    }
    prompt_instruction = prompt_config.get("baustein_zielobjekt_matching_instruction", "")

    # Initialize AI client
    ai_client = AiClient()

    # Run the asynchronous matching process
    logger.info(f"Starting AI matching for {len(bausteine_with_prose)} Bausteine...")
    final_map = asyncio.run(
        _run_matching_tasks(
            ai_client,
            bausteine_with_prose,
            zielobjekte_map,
            prompt_instruction,
            schema,
        )
    )

    # Save the results
    output_data = {"baustein_zielobjekt_map": final_map}
    logger.info(f"Saving the final Baustein-Zielobjekt map to {BAUSTEINE_ZIELOBJEKTE_JSON_PATH}...")
    save_json_file(output_data, BAUSTEINE_ZIELOBJEKTE_JSON_PATH)

    logger.info(f"Stage_match_bausteine finished. Matched {len(final_map)} Bausteine.")

if __name__ == "__main__":
    # Configure logging for direct script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_stage_match_bausteine()
