import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import regex
from jsonschema import Draft7Validator, validators, ValidationError

from config import app_config
from constants import (
    BAUSTEINE_ZIELOBJEKTE_JSON_PATH,
    BSI_2023_JSON_PATH,
    CONTROLS_ANFORDERUNGEN_JSON_PATH,
    OSCAL_COMPONENT_SCHEMA_PATH,
    SDT_COMPONENTS_DE_DIR,
    SDT_PROFILES_DIR,
)
from utils.data_loader import load_json_file, save_json_file

logger = logging.getLogger(__name__)


# Create a custom validator that uses the 'regex' library for full Unicode support
def is_regex(instance):
    """Custom regex format checker using the 'regex' library."""
    try:
        regex.compile(instance)
        return True
    except (regex.error, TypeError):
        return False

format_checker = Draft7Validator.FORMAT_CHECKER
format_checker.checks("regex", raises=regex.error)(is_regex)

CustomValidator = validators.extend(
    Draft7Validator, {"format_checker": format_checker}
)


def _validate_component_schema(component_data: Dict[str, Any]) -> bool:
    """Validates the generated component against the OSCAL component schema."""
    try:
        schema = load_json_file(OSCAL_COMPONENT_SCHEMA_PATH)
        if not schema:
            logger.error(f"Failed to load OSCAL component schema from {OSCAL_COMPONENT_SCHEMA_PATH}")
            return False
        validator = CustomValidator(schema)
        validator.validate(instance=component_data)
        logger.debug("Component schema validation successful.")
        return True
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e.message}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during schema validation: {e}")
        return False


def _find_bsi_baustein(baustein_id: str, bsi_catalog: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Finds a Baustein node in the BSI catalog by its ID."""
    for main_group in bsi_catalog.get("catalog", {}).get("groups", []):
        for baustein_group in main_group.get("groups", []):
            if baustein_group.get("id") == baustein_id:
                return baustein_group
    return None


def _find_bsi_anforderung(anforderung_id: str, baustein_node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Finds an Anforderung (control) within a Baustein node by its ID."""
    for control in baustein_node.get("controls", []):
        if control.get("id") == anforderung_id:
            return control
    return None


def _create_base_component_definition(title: str, component_uuid: str) -> Dict[str, Any]:
    """Creates the base structure for an OSCAL component definition."""
    now_utc = datetime.now(timezone.utc).isoformat()
    return {
        "component-definition": {
            "uuid": component_uuid,
            "metadata": {
                "title": title,
                "last-modified": now_utc,
                "version": "1.0.0",
                "oscal-version": "1.1.3",
            },
            "components": [],
        }
    }


async def run_stage_component() -> None:
    """
    Generates OSCAL Component Definition files for each Baustein.
    """
    logger.info("Starting stage_component...")
    os.makedirs(SDT_COMPONENTS_DE_DIR, exist_ok=True)

    # Load necessary data files
    baustein_zielobjekt_map = load_json_file(BAUSTEINE_ZIELOBJEKTE_JSON_PATH)
    controls_anforderungen_map = load_json_file(CONTROLS_ANFORDERUNGEN_JSON_PATH)
    bsi_catalog = load_json_file(BSI_2023_JSON_PATH)

    if not all([baustein_zielobjekt_map, controls_anforderungen_map, bsi_catalog]):
        logger.error("One or more required data files could not be loaded. Aborting stage_component.")
        return

    baustein_map = baustein_zielobjekt_map.get("baustein_zielobjekt_map", {})

    for baustein_id, zielobjekt_uuid in baustein_map.items():
        logger.info(f"Processing Baustein: {baustein_id} for Zielobjekt UUID: {zielobjekt_uuid}")

        # 1. Find and load the corresponding profile
        zielobjekt_mapping_data = controls_anforderungen_map.get(zielobjekt_uuid, {})
        zielobjekt_name = zielobjekt_mapping_data.get("zielobjekt_name", "Unknown")
        profile_filename = f"{zielobjekt_name.lower().replace(' ', '_')}_profile.json"
        profile_path = os.path.join(SDT_PROFILES_DIR, profile_filename)

        if not os.path.exists(profile_path):
            logger.warning(f"Profile not found for Baustein {baustein_id} at {profile_path}. Skipping.")
            continue

        profile_data = load_json_file(profile_path)
        if not profile_data:
            logger.warning(f"Failed to load profile data from {profile_path}. Skipping.")
            continue

        profile_url = f"https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/main/Zielobjekt-Bausteine/profiles/{profile_filename}"
        gpp_source_url = profile_data.get("profile", {}).get("imports", [{}])[0].get("href")
        
        try:
            required_gpp_controls = set(profile_data["profile"]["imports"][0]["include-controls"][0]["with-ids"])
        except (KeyError, IndexError):
            logger.warning(f"Could not extract required controls from profile {profile_path}. Skipping.")
            continue

        # 2. Find the Baustein in the BSI catalog
        bsi_baustein_node = _find_bsi_baustein(baustein_id, bsi_catalog)
        if not bsi_baustein_node:
            logger.warning(f"Baustein ID '{baustein_id}' not found in BSI catalog. Skipping.")
            continue
        
        baustein_title = bsi_baustein_node.get("title", baustein_id)
        component_uuid = str(uuid.uuid4())
        
        # 3. Build the full component definition
        full_comp_def = _create_base_component_definition(f"{baustein_title} Component Definition", component_uuid)
        
        implemented_requirements = []
        bsi_to_gpp_map = zielobjekt_mapping_data.get("mapping", {})

        for bsi_anforderung_id, gpp_control_id in bsi_to_gpp_map.items():
            if gpp_control_id in required_gpp_controls:
                anforderung_node = _find_bsi_anforderung(bsi_anforderung_id, bsi_baustein_node)
                if not anforderung_node:
                    logger.debug(f"Anforderung '{bsi_anforderung_id}' not found in Baustein '{baustein_id}'.")
                    continue

                statements = []
                for part in anforderung_node.get("parts", []):
                    if part.get("name") == "maturity-level-description":
                        prose = ""
                        for sub_part in part.get("parts", []):
                            if sub_part.get("name") == "statement":
                                prose = sub_part.get("prose", "")
                                break
                        statements.append({
                            "statement-id": part.get("id"),
                            "uuid": str(uuid.uuid4()),
                            "description": prose
                        })

                implemented_requirements.append({
                    "uuid": str(uuid.uuid4()),
                    "control-id": gpp_control_id,
                    "description": f"Implementation based on BSI Anforderung: {anforderung_node.get('title', bsi_anforderung_id)}",
                    "props": anforderung_node.get("props", []),
                    "statements": statements
                })

        if implemented_requirements:
            full_comp_def["component-definition"]["components"].append({
                "uuid": str(uuid.uuid4()),
                "type": "software",
                "title": baustein_title,
                "description": f"This component provides the implementation of controls for the Baustein '{baustein_title}'.",
                "control-implementations": [{
                    "uuid": str(uuid.uuid4()),
                    "source": gpp_source_url,
                    "description": f"Implementation of controls for Baustein {baustein_id} based on the corresponding profile.",
                    "implemented-requirements": implemented_requirements
                }]
            })

            # 4. Validate and save the full component file
            if _validate_component_schema(full_comp_def):
                save_path = os.path.join(SDT_COMPONENTS_DE_DIR, f"{baustein_id}-component.json")
                save_json_file(full_comp_def, save_path)
                logger.info(f"Successfully saved full component for {baustein_id} to {save_path}")

        # 5. Build, validate, and save the reference component file
        ref_comp_def = _create_base_component_definition(f"{baustein_title} Reference Component", str(uuid.uuid4()))
        ref_comp_def["component-definition"]["metadata"]["links"] = [{"href": profile_url, "rel": "profile"}]
        ref_comp_def["component-definition"]["components"].append({
            "uuid": str(uuid.uuid4()),
            "type": "service",
            "title": baustein_title,
            "description": f"A reference component for Baustein '{baustein_title}'. See the linked profile for control selection."
        })

        if _validate_component_schema(ref_comp_def):
            save_path = os.path.join(SDT_COMPONENTS_DE_DIR, f"{baustein_id}-Reference-Component.json")
            save_json_file(ref_comp_def, save_path)
            logger.info(f"Successfully saved reference component for {baustein_id} to {save_path}")

    logger.info("Stage_component finished.")