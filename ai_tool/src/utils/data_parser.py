"""
Utility functions for parsing the loaded data into structured formats.

This module contains the logic to transform the raw data loaded from files
into more structured and accessible formats that the pipeline can easily use.
"""

import logging
from typing import Any, Dict, List, Tuple

from constants import ALLOWED_MAIN_GROUPS, ALLOWED_PROCESS_BAUSTEINE


def find_bausteine_with_prose(bsi_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses the BSI 2023 JSON to extract a list of Bausteine that have prose.
    """
    bausteine_with_prose = []
    catalog = bsi_data.get("catalog", {})
    for group in catalog.get("groups", []):
        for sub_group in group.get("groups", []):
            if sub_group.get("class") == "baustein":
                # Find the 'usage' description for the Baustein
                baustein_description = ""
                for part in sub_group.get("parts", []):
                    if part.get("name") == "usage":
                        baustein_description = part.get("prose", "")
                        break

                if (
                    group.get("id") in ALLOWED_MAIN_GROUPS
                    or sub_group.get("id") in ALLOWED_PROCESS_BAUSTEINE
                ):
                    if baustein_description:
                        bausteine_with_prose.append(
                            {
                                "id": sub_group.get("id"),
                                "title": _ensure_string_title(sub_group.get("title")),
                                "description": baustein_description,
                            }
                        )
    return bausteine_with_prose


def get_anforderungen_for_bausteine(bsi_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Parses the BSI 2023 JSON data to create a map from Baustein ID to a list of its Anforderung IDs.
    """
    baustein_anforderungen_map = {}
    catalog = bsi_data.get("catalog", {})
    for group in catalog.get("groups", []):
        for sub_group in group.get("groups", []):
            baustein_id = sub_group.get("id")
            if baustein_id and (
                group.get("id") in ALLOWED_MAIN_GROUPS
                or baustein_id in ALLOWED_PROCESS_BAUSTEINE
            ):
                anforderung_ids = []
                if "controls" in sub_group:
                    for control in sub_group["controls"]:
                        anforderung_ids.append(control["id"])
                baustein_anforderungen_map[baustein_id] = anforderung_ids
    return baustein_anforderungen_map

logger = logging.getLogger(__name__)

def _ensure_string_title(title_value: Any) -> str:
    """Ensures the title value is a single string, handling lists."""
    if isinstance(title_value, list) and title_value:
        # If it's a list (common in the source JSON), take the first element.
        return str(title_value[0])
    elif isinstance(title_value, str):
        return title_value
    # Fallback for empty lists or other types.
    return ""



def parse_zielobjekte_hierarchy(zielobjekte_data: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    Parses Zielobjekte data to create a lookup map by UUID.

    Args:
        zielobjekte_data: A list of dictionaries, each representing a Zielobjekt.

    Returns:
        A dictionary mapping each Zielobjekt's UUID to its corresponding data row.
    """
    logger.debug("Parsing and normalizing Zielobjekte data into a UUID lookup map...")
    zielobjekte_map = {}
    for row in zielobjekte_data:
        uuid = row.get("UUID")
        if uuid:
            # The CSV headers are positional: UUID, Definition, Zielobjekt, ChildOfUUID
            # The data loader correctly uses these as keys.
            zielobjekte_map[uuid] = {
                "UUID": uuid,
                "Definition": row.get("Definition", ""),
                "Zielobjekt": row.get("Zielobjekt", ""),
                "ChildOfUUID": row.get("ChildOfUUID", ""),
            }

    logger.debug(f"Successfully created a lookup map for {len(zielobjekte_map)} normalized Zielobjekte.")
    return zielobjekte_map


def parse_bsi_2023_controls(
    bsi_2023_data: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses the BSI 2023 JSON to extract a list of Bausteine with their controls.

    This function iterates through the catalog, filters for allowed main groups,
    and extracts "Bausteine" along with a reduced list of their controls.
    Bausteine from non-allowed groups are collected separately.

    Args:
        bsi_2023_data: The loaded BSI 2023 JSON data.

    Returns:
        A tuple containing two lists:
        - The first list has Bausteine to be processed.
        - The second list has Bausteine that were filtered out.
    """
    logger.debug("Parsing BSI 2023 Bausteine and their controls...")
    parsed_bausteine = []
    filtered_out_bausteine = []

    try:
        main_groups = bsi_2023_data.get("catalog", {}).get("groups", [])
        for main_group in main_groups:

            def _parse_baustein_details(baustein: Dict[str, Any]) -> Dict[str, Any]:
                # Find the 'usage' description for the Baustein
                baustein_description = ""
                for part in baustein.get("parts", []):
                    if part.get("name") == "usage":
                        baustein_description = part.get("prose", "")
                        break

                parsed_baustein = {
                    "id": baustein.get("id"),
                    "title": _ensure_string_title(baustein.get("title")),
                    "description": baustein_description,
                    "controls": [],
                }
                for control in baustein.get("controls", []):
                    reduced_control = {
                        "id": control.get("id"),
                        "title": _ensure_string_title(control.get("title")),
                        "prose": None,
                    }
                    for part in control.get("parts", []):
                        if part.get("class") == "maturity-level-defined":
                            for sub_part in part.get("parts", []):
                                if sub_part.get("name") == "statement":
                                    reduced_control["prose"] = sub_part.get("prose")
                                    break
                            break
                    parsed_baustein["controls"].append(reduced_control)
                return parsed_baustein

            bausteine_in_group = main_group.get("groups", [])
            target_list = (
                parsed_bausteine
                if main_group.get("id") in ALLOWED_MAIN_GROUPS
                else filtered_out_bausteine
            )

            for baustein in bausteine_in_group:
                if baustein.get("class") == "baustein":
                    target_list.append(_parse_baustein_details(baustein))

    except Exception as e:
        logger.error(f"Failed to parse BSI 2023 Bausteine due to an error: {e}")
        raise

    logger.debug(f"Successfully parsed {len(parsed_bausteine)} Bausteine for processing.")
    logger.info(
        f"Filtered out {len(filtered_out_bausteine)} Bausteine for later use."
    )
    return parsed_bausteine, filtered_out_bausteine


def _traverse_and_collect_controls(
    controls: List[Dict[str, Any]],
    zielobjekt_to_controls_map: Dict[str, List[str]],
    gpp_control_titles: Dict[str, str],
):
    """
    Recursively traverses a list of controls to populate the maps, ensuring no
    duplicate control IDs are added for any Zielobjekt.
    """
    for control in controls:
        control_id = control.get("id")
        if not control_id:
            continue

        control_title_value = control.get("title")
        final_title = _ensure_string_title(control_title_value)

        if final_title:
            gpp_control_titles[control_id] = final_title

        for part in control.get("parts", []):
            for prop in part.get("props", []):
                if prop.get("name") == "target_objects":
                    zielobjekte = [
                        zo.strip() for zo in prop.get("value", "").split(",")
                    ]
                    for zo_name in zielobjekte:
                        if zo_name not in zielobjekt_to_controls_map:
                            zielobjekt_to_controls_map[zo_name] = []
                        if control_id not in zielobjekt_to_controls_map[zo_name]:
                            zielobjekt_to_controls_map[zo_name].append(control_id)

        # Recursive step for nested controls
        if "controls" in control and control["controls"]:
            _traverse_and_collect_controls(
                control["controls"],
                zielobjekt_to_controls_map,
                gpp_control_titles,
            )


def parse_gpp_kompendium_controls(
    gpp_kompendium_data: Dict[str, Any]
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Parses the G++ Kompendium to create two maps:
    1. A map of Zielobjekt names to their associated G++ control IDs.
    2. A map of all G++ control IDs to their titles for semantic matching.

    Args:
        gpp_kompendium_data: The loaded G++ Kompendium JSON data.

    Returns:
        A tuple containing:
        - A dictionary mapping Zielobjekt names to a list of G++ control IDs.
        - A dictionary mapping G++ control IDs to their titles.
    """
    logger.debug("Parsing G++ Kompendium for Zielobjekt-control and control-title maps...")
    zielobjekt_to_controls_map = {}
    gpp_control_titles = {}

    try:
        groups = gpp_kompendium_data.get("catalog", {}).get("groups", [])
        for group in groups:
            for sub_group in group.get("groups", []):
                if sub_group.get("controls"):
                    _traverse_and_collect_controls(
                        sub_group["controls"],
                        zielobjekt_to_controls_map,
                        gpp_control_titles,
                    )
    except Exception as e:
        logger.error(f"Failed to parse G++ Kompendium controls due to an error: {e}")
        raise

    logger.debug(f"Successfully mapped {len(zielobjekt_to_controls_map)} Zielobjekte to controls.")
    logger.debug(f"Successfully parsed {len(gpp_control_titles)} G++ control titles.")
    return zielobjekt_to_controls_map, gpp_control_titles


def extract_all_gpp_controls(gpp_kompendium_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Recursively extracts all controls from the G++ Kompendium data into a flat dictionary.

    Args:
        gpp_kompendium_data: The loaded G++ Kompendium JSON data.

    Returns:
        A dictionary mapping Control IDs to their full Control objects.
    """
    logger.debug("Recursively extracting all G++ controls...")
    all_controls = {}

    def _traverse(controls_list: List[Dict[str, Any]]):
        for control in controls_list:
            control_id = control.get("id")
            if control_id:
                all_controls[control_id] = control

            if "controls" in control and control["controls"]:
                _traverse(control["controls"])

    def _traverse_group(group_list: List[Dict[str, Any]]):
        for group in group_list:
            # Extract controls from the current group
            if group.get("controls"):
                _traverse(group["controls"])

            # Recursively process subgroups
            if group.get("groups"):
                _traverse_group(group["groups"])

    try:
        # Start traversal from the top-level groups
        groups = gpp_kompendium_data.get("catalog", {}).get("groups", [])
        _traverse_group(groups)

    except Exception as e:
        logger.error(f"Failed to extract all G++ controls due to error: {e}")
        raise

    logger.debug(f"Successfully extracted {len(all_controls)} G++ controls.")
    return all_controls


def filter_markdown(control_ids: List[str], markdown_content: str) -> str:
    """
    Filters a markdown table to include only rows with specified IDs.

    This function is more robust than a regex search as it processes the table
    line by line.

    Args:
        control_ids: A list of IDs (e.g., "GPP.1.1", "SYS.1.1.A1") to retain.
        markdown_content: The full markdown table as a string.

    Returns:
        A string of the filtered markdown table, or an empty string if filtering fails.
    """

    if not control_ids:
        return ""

    lines = markdown_content.strip().splitlines()

    if len(lines) < 2:
        logger.warning("Markdown content is too short to contain a header and separator.")
        return ""

    header = lines[0]
    separator = lines[1]

    # Validate that the separator line looks correct
    if not separator.strip().startswith('|'):
        logger.warning("Markdown separator line is malformed.")
        return ""

    # Efficiently find all relevant rows in a single pass
    rows = []
    control_id_set = set(control_ids)
    for line in lines[2:]:
        line_trimmed = line.strip()
        if line_trimmed.startswith('|'):
            parts = [p.strip() for p in line_trimmed.split('|')]
            if len(parts) > 2 and parts[1] in control_id_set:
                rows.append(line)

    if not rows:
        logger.warning(f"No rows found for control IDs: {control_ids}")
        return ""

    return "\n".join([header, separator] + rows)