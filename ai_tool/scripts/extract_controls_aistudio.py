import json
import logging
import argparse
from typing import Dict, Any, List, Optional, Tuple

# Adhering to §9.2, set up conditional logging.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def find_prop_value(props_list: List[Dict[str, Any]], prop_name: str) -> Optional[str]:
    """
    Safely finds a value for a given property name in a list of property dictionaries.

    Args:
        props_list: A list of dictionaries, where each dict represents a property.
        prop_name: The 'name' of the property to find.

    Returns:
        The 'value' of the found property, or None if not found.
    """
    if not isinstance(props_list, list):
        return None
    for prop in props_list:
        if isinstance(prop, dict) and prop.get("name") == prop_name:
            return prop.get("value")
    return None

def process_control(control: Dict[str, Any]) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """
    Extracts key details, UUID, and a simplified representation of a control.

    The key is determined by the 'target_objects' property, defaulting to 'ISMS'.
    The simplified control contains only id, class, title, and prose.

    Args:
        control: A dictionary representing a single control.

    Returns:
        A tuple containing (classification_key, uuid, simplified_control_dict),
        or None if the control cannot be processed.
    """
    uuid = find_prop_value(control.get("props", []), "alt-identifier")
    if not uuid:
        control_id = control.get('id', 'N/A')
        logging.warning(f"Control '{control_id}' is missing 'alt-identifier' property. Skipping.")
        return None

    # Determine classification key
    key = "ISMS"
    parts = control.get("parts", [])
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict):
                target_obj_val = find_prop_value(part.get("props", []), "target_objects")
                if target_obj_val:
                    key = target_obj_val
                    break

    # Extract prose from the 'statement' part
    prose = ""
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict) and part.get("name") == "statement":
                prose = part.get("prose", "")
                break

    # Create the simplified control object
    simplified_control = {
        "id": control.get("id"),
        "class": control.get("class"),
        "title": control.get("title"),
        "prose": prose,
    }

    return key, uuid, simplified_control


def traverse_and_extract_controls(node: Dict[str, Any], all_controls: Dict[str, Any]) -> None:
    """
    Recursively traverses the JSON structure to find and process all control objects,
    populating a nested dictionary for optimal access.

    Args:
        node: The current dictionary node in the JSON tree to process.
        all_controls: The main dictionary to populate with extracted controls.
    """
    if "controls" in node and isinstance(node["controls"], list):
        for control in node["controls"]:
            if not isinstance(control, dict):
                continue

            processed_data = process_control(control)
            if processed_data:
                key, uuid, simplified_control = processed_data
                
                # Ensure the top-level key (e.g., "Netze") exists
                all_controls.setdefault(key, {})
                
                # Add the control to the nested dictionary, keyed by its UUID
                all_controls[key][uuid] = simplified_control

            # A control can contain nested controls, so we recurse into it
            traverse_and_extract_controls(control, all_controls)

    if "groups" in node and isinstance(node["groups"], list):
        for group in node["groups"]:
            if isinstance(group, dict):
                traverse_and_extract_controls(group, all_controls)


def main() -> None:
    """
    Main function to load, process, and save control data into an optimal format.
    """
    parser = argparse.ArgumentParser(
        description="Extract all controls from a Grundschutz Kompendium JSON file into an optimal format."
    )
    parser.add_argument("input_file", help="Path to the input JSON file.")
    parser.add_argument("output_file", help="Path for the output JSON file.")
    args = parser.parse_args()

    logging.info(f"Loading data from {args.input_file}...")
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {args.input_file}")
        return
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {args.input_file}.")
        return

    extracted_controls: Dict[str, Any] = {}
    
    if 'catalog' in data:
        logging.info("Starting recursive extraction of controls...")
        traverse_and_extract_controls(data['catalog'], extracted_controls)
        total_controls = sum(len(controls) for controls in extracted_controls.values())
        logging.info(
            f"Extraction complete. Found {total_controls} controls across "
            f"{len(extracted_controls)} categories."
        )
    else:
        logging.warning("'catalog' key not found. No controls to extract.")

    logging.info(f"Saving extracted controls to {args.output_file}...")
    try:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_controls, f, ensure_ascii=False, indent=2)
        logging.info(f"Successfully saved the output file to {args.output_file}")
    except IOError as e:
        logging.error(f"Failed to write to output file {args.output_file}: {e}")

if __name__ == "__main__":
    main()