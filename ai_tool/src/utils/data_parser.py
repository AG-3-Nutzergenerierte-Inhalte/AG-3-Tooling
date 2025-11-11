"""
Utility functions for parsing the loaded data into structured formats.

This module contains the logic to transform the raw data loaded from files
into more structured and accessible formats that the pipeline can easily use.
"""

import logging
from typing import Any, Dict, List, Tuple

from constants import ALLOWED_MAIN_GROUPS

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
    logger.info("Parsing Zielobjekte data into a UUID lookup map...")
    zielobjekte_map = {row["UUID"]: row for row in zielobjekte_data if row.get("UUID")}
    logger.info(f"Successfully created a lookup map for {len(zielobjekte_map)} Zielobjekte.")
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
    logger.info("Parsing BSI 2023 Bausteine and their controls...")
    parsed_bausteine = []
    filtered_out_bausteine = []

    try:
        main_groups = bsi_2023_data.get("catalog", {}).get("groups", [])
        for main_group in main_groups:

            def _parse_baustein_details(baustein: Dict[str, Any]) -> Dict[str, Any]:
                parsed_baustein = {
                    "id": baustein.get("id"),
                    "title": _ensure_string_title(baustein.get("title")),
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

    logger.info(f"Successfully parsed {len(parsed_bausteine)} Bausteine for processing.")
    logger.info(
        f"Filtered out {len(filtered_out_bausteine)} Bausteine for later use."
    )
    return parsed_bausteine, filtered_out_bausteine


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
    logger.info("Parsing G++ Kompendium for Zielobjekt-control and control-title maps...")
    zielobjekt_to_controls_map = {}
    gpp_control_titles = {}

    try:
        groups = gpp_kompendium_data.get("catalog", {}).get("groups", [])
        for group in groups:
            for sub_group in group.get("groups", []):
                for control in sub_group.get("controls", []):
                    control_id = control.get("id")
                    control_title_value = control.get("title")

                    final_title = _ensure_string_title(control_title_value)
                    
                    if control_id and final_title:
                        gpp_control_titles[control_id] = final_title

                    for part in control.get("parts", []):
                        for prop in part.get("props", []):
                            if prop.get("name") == "target_objects":
                                zielobjekte = [zo.strip() for zo in prop.get("value", "").split(",")]
                                for zo_name in zielobjekte:
                                    if zo_name not in zielobjekt_to_controls_map:
                                        zielobjekt_to_controls_map[zo_name] = []
                                    if control_id:
                                        zielobjekt_to_controls_map[zo_name].append(control_id)
    except Exception as e:
        logger.error(f"Failed to parse G++ Kompendium controls due to an error: {e}")
        raise

    logger.info(f"Successfully mapped {len(zielobjekt_to_controls_map)} Zielobjekte to controls.")
    logger.info(f"Successfully parsed {len(gpp_control_titles)} G++ control titles.")
    return zielobjekt_to_controls_map, gpp_control_titles
