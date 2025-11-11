"""
This module contains the logic for matching BSI Bausteine to G++ Zielobjekte.
This module contains the logic for matching BSI Bausteine to G++ Zielobjekte.
"""
import logging
from typing import Dict, Any
from typing import Dict, Any

from clients.ai_client import AiClient

logger = logging.getLogger(__name__)


async def match_baustein_to_zielobjekt(
    ai_client: AiClient,
    baustein: Dict[str, Any],
    zielobjekte_map: Dict[str, Any],
    prompt_template: str,
    schema: Dict[str, Any],
) -> str | None:
    """
    Matches a BSI Baustein to the best G++ Zielobjekt using an AI model.
    Matches a BSI Baustein to the best G++ Zielobjekt using an AI model.

    Args:
        ai_client: The AI client instance.
        baustein: The Baustein object to match.
        zielobjekte_map: A dictionary of all available Zielobjekte.
        prompt_template: The prompt template to use for the AI call.

    Returns:
        The UUID of the best-matching Zielobjekt, or None if no match is found.
        The UUID of the best-matching Zielobjekt, or None if no match is found.
    """
    choices = {
        uuid: f"{data.get('title', '')} - {data.get('description', '')}"
        for uuid, data in zielobjekte_map.items()
    }

    json_input = {
        "description": f"{baustein.get('title', '')} - {baustein.get('description', '')}",
        "choices": choices,
    }

    # Use the schema-validated method, as no simple text generation method exists.
    response_json = await ai_client.generate_validated_json_response(
        prompt=prompt_template.format(json_input=json.dumps(json_input, indent=2)),
        json_schema=schema,
        request_context_log=f"BausteinToZielobjekt-{baustein.get('id', 'unknown')}",
    )

    matched_uuid = response_json.get("matched_uuid")

    if matched_uuid and matched_uuid in zielobjekte_map:
        logger.info(f"Successfully matched Baustein '{baustein['id']}' to Zielobjekt '{matched_uuid}'.")
        return matched_uuid

    logger.warning(f"Could not find a suitable match for Baustein '{baustein['id']}'.")
    return None
