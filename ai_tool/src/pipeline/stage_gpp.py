"""
This stage is responsible for processing the G++ Kompendium to create a
deterministic mapping between Zielobjekte and their applicable controls.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from constants import GPP_KOMPENDIUM_JSON_PATH, ZIELOBJEKTE_CSV_PATH, ZIELOBJEKT_CONTROLS_JSON_PATH
from utils.data_loader import load_json_file, save_json_file, load_zielobjekte_csv

logger = logging.getLogger(__name__)


def _find_prop_value(props_list: List[Dict[str, Any]], prop_name: str) -> Optional[str]:
    """
    Safely finds a value for a given property name in a list of property dictionaries.
    """
    if not isinstance(props_list, list):
        return None
    for prop in props_list:
        if isinstance(prop, dict) and prop.get("name") == prop_name:
            return prop.get("value")
    return None


def _process_control(control: Dict[str, Any]) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """
    Extracts key details, UUID, and a simplified representation of a control.
    """
    uuid = _find_prop_value(control.get("props", []), "alt-identifier")
    if not uuid:
        control_id = control.get('id', 'N/A')
        logger.debug(f"Control '{control_id}' is missing 'alt-identifier' property. Skipping.")
        return None

    key = "ISMS"
    parts = control.get("parts", [])
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict):
                target_obj_val = _find_prop_value(part.get("props", []), "target_objects")
                if target_obj_val:
                    key = target_obj_val
                    break

    prose = ""
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict) and part.get("name") == "statement":
                prose = part.get("prose", "")
                break

    simplified_control = {
        "id": control.get("id"),
        "class": control.get("class"),
        "title": control.get("title"),
        "prose": prose,
    }

    return key, uuid, simplified_control


def _traverse_and_extract_controls(node: Dict[str, Any], all_controls: Dict[str, Any]) -> None:
    """
    Recursively traverses the JSON structure to find and process all control objects.
    """
    if "controls" in node and isinstance(node["controls"], list):
        for control in node["controls"]:
            if not isinstance(control, dict):
                continue

            processed_data = _process_control(control)
            if processed_data:
                key, uuid, simplified_control = processed_data
                all_controls.setdefault(key, {})
                all_controls[key][uuid] = simplified_control

            _traverse_and_extract_controls(control, all_controls)

    if "groups" in node and isinstance(node["groups"], list):
        for group in node["groups"]:
            if isinstance(group, dict):
                _traverse_and_extract_controls(group, all_controls)


def _create_target_controls_map() -> Dict[str, Any]:
    """
    Loads the G++ Kompendium and flattens it into a target-controls-map.
    """
    logger.info(f"Loading G++ Kompendium from {GPP_KOMPENDIUM_JSON_PATH}...")
    data = load_json_file(GPP_KOMPENDIUM_JSON_PATH)
    if not data or 'catalog' not in data:
        logger.error("G++ Kompendium is empty or missing 'catalog' key.")
        return {}

    logger.info("Starting recursive extraction of controls to create target-controls-map...")
    extracted_controls: Dict[str, Any] = {}
    _traverse_and_extract_controls(data['catalog'], extracted_controls)
    total_controls = sum(len(controls) for controls in extracted_controls.values())
    logger.info(f"Extraction complete. Found {total_controls} controls.")
    return extracted_controls


def _get_parent_names_recursive(
    zielobjekt_uuid: str,
    zielobjekte_raw_map: Dict[str, Any],
    visited: set
) -> List[str]:
    """
    Recursively collects the names of all parent Zielobjekte.
    """
    if zielobjekt_uuid in visited:
        logger.warning(f"Circular dependency detected for UUID: {zielobjekt_uuid}. Stopping recursion.")
        return []
    visited.add(zielobjekt_uuid)

    parent_names = []
    zielobjekt_data = zielobjekte_raw_map.get(zielobjekt_uuid)

    if not zielobjekt_data:
        return []

    parent_uuid = zielobjekt_data.get("ChildOfUUID")
    if parent_uuid and parent_uuid in zielobjekte_raw_map:
        parent_name = zielobjekte_raw_map[parent_uuid].get("Zielobjekt")
        if parent_name:
            parent_names.append(parent_name)
        parent_names.extend(_get_parent_names_recursive(parent_uuid, zielobjekte_raw_map, visited))

    return parent_names


def _create_zielobjekt_map() -> Dict[str, Any]:
    """
    Creates a map of all Zielobjekte with their names and parent names.
    """
    logger.info(f"Loading Zielobjekte from {ZIELOBJEKTE_CSV_PATH}...")
    zielobjekte_data = load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
    if not zielobjekte_data:
        logger.error("No data loaded from Zielobjekte CSV.")
        return {}

    # C.3: Create a raw map for easy lookup by UUID
    zielobjekte_raw_map = {
        z["GART_Objekt_UUID"]: {
            "Zielobjekt": z["Zielobjekt"],
            "ChildOfUUID": z.get("ChildOfUUID")
        }
        for z in zielobjekte_data if "GART_Objekt_UUID" in z
    }

    # C.4: Recursively get all parent names for each Zielobjekt
    zielobjekt_map_with_parents = {}
    for uuid, data in zielobjekte_raw_map.items():
        own_name = data["Zielobjekt"]
        parent_names = _get_parent_names_recursive(uuid, zielobjekte_raw_map, set())

        zielobjekt_map_with_parents[uuid] = {
            "name": own_name,
            "all_applicable_names": [own_name] + parent_names
        }
    logger.info(f"Created zielobjekt-map with {len(zielobjekt_map_with_parents)} entries.")
    return zielobjekt_map_with_parents


def run_stage_gpp():
    """Main function for the stage_gpp."""
    logger.info("Starting stage_gpp...")

    # C.2: Flatten the GPP Kompendium into a target-controls-map
    target_controls_map = _create_target_controls_map()
    if not target_controls_map:
        logger.error("Failed to create target-controls-map. Aborting stage_gpp.")
        return

    # C.3 & C.4: Create the zielobjekt-map with parent inheritance
    zielobjekt_map = _create_zielobjekt_map()
    if not zielobjekt_map:
        logger.error("Failed to create zielobjekt-map. Aborting stage_gpp.")
        return

    # C.5: Match controls from target-controls-map to the zielobjekt-map
    logger.info("Matching controls to Zielobjekte...")
    final_zielobjekt_controls_map = {}
    for uuid, data in zielobjekt_map.items():
        applicable_controls = set()
        for name in data["all_applicable_names"]:
            if name in target_controls_map:
                # The controls are nested under their UUIDs, so we extract the 'id' from each.
                for control_data in target_controls_map[name].values():
                    if 'id' in control_data:
                        applicable_controls.add(control_data['id'])

        final_zielobjekt_controls_map[uuid] = sorted(list(applicable_controls))

    # C.6: Store the final map
    output_data = {"zielobjekt_controls_map": final_zielobjekt_controls_map}
    logger.info(f"Saving the final Zielobjekt-controls map to {ZIELOBJEKT_CONTROLS_JSON_PATH}...")
    save_json_file(output_data, ZIELOBJEKT_CONTROLS_JSON_PATH)

    logger.info(f"Stage_gpp finished. Processed {len(final_zielobjekt_controls_map)} Zielobjekte.")
