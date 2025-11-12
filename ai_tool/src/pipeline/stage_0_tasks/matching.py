"""
This module contains the logic for matching BSI Bausteine to G++ Zielobjekte.
"""
import json
import logging
from typing import Dict, Any

from clients.ai_client import AiClient

logger = logging.getLogger(__name__)


async def match_baustein_to_zielobjekt(
    ai_client: AiClient,
    baustein: Dict[str, Any],
    zielobjekte_map: Dict[str, Any],
    prompt_instruction: str,
    schema: Dict[str, Any],
) -> str | None:
    """
    Matches a BSI Baustein to the best G++ Zielobjekt using an AI model.

    Args:
        ai_client: The AI client instance.
        baustein: The Baustein object to match, including 'description'.
        zielobjekte_map: A dictionary of all available Zielobjekte, including 'Definition'.
        prompt_instruction: The introductory text for the prompt.
        schema: The JSON schema for validating the AI's response.

    Returns:
        The UUID of the best-matching Zielobjekt, or None if no match is found.
    """
    # Construct the detailed prompt with descriptions for both the Baustein and Zielobjekte
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

    # The AI is now expected to return the NAME of the best match, not the UUID.
    response_json = await ai_client.generate_validated_json_response(
        prompt=prompt,
        json_schema=schema,
        request_context_log=f"BausteinToZielobjekt-{baustein.get('id', 'unknown')}",
    )

    matched_zielobjekt_name = response_json.get("matched_zielobjekt")

    if matched_zielobjekt_name:
        # Find the corresponding UUID from the name.
        for uuid, data in zielobjekte_map.items():
            if data.get("Zielobjekt") == matched_zielobjekt_name:
                logger.info(
                    f"Successfully matched Baustein '{baustein.get('title')}' to "
                    f"Zielobjekt '{matched_zielobjekt_name}' (UUID: {uuid})."
                )
                return uuid

    logger.warning(f"Could not find a suitable match for Baustein '{baustein.get('id')}'.")
    return None

    logger.warning(f"Could not find a suitable match for Baustein '{baustein.get('id')}'.")
    return None