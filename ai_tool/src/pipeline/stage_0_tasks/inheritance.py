"""
Handles the recursive inheritance logic for Zielobjekt controls.

This module provides the functionality to traverse the Zielobjekt hierarchy
and aggregate a complete list of all inherited G++ controls for any given
Zielobjekt.
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


def get_all_inherited_controls(
    zielobjekt_uuid: str,
    zielobjekte_map: Dict[str, Dict[str, str]],
    zielobjekt_to_gpp_controls_map: Dict[str, List[str]],
    gpp_control_titles: Dict[str, str],
    memo: Dict[str, Set[str]] = None,
) -> Dict[str, str]:
    """
    Recursively aggregates all inherited G++ controls for a Zielobjekt.
    Returns a dictionary of control IDs to their titles.
    """
    if memo is None:
        memo = {}
    if zielobjekt_uuid in memo:
        # The memo stores IDs, so we need to convert it back to a dict with titles
        return {cid: gpp_control_titles.get(cid, "") for cid in memo[zielobjekt_uuid]}

    current_zielobjekt = zielobjekte_map.get(zielobjekt_uuid)
    if not current_zielobjekt:
        return {}

    # Get control IDs directly associated with the current Zielobjekt
    zielobjekt_name = current_zielobjekt.get("Zielobjekt", "")
    inherited_control_ids = set(zielobjekt_to_gpp_controls_map.get(zielobjekt_name, []))

    # Recursively get control IDs from the parent
    parent_uuid = current_zielobjekt.get("ChildOfUUID")
    if parent_uuid:
        # The recursive call returns a dict, we only need the keys (IDs) for the set logic
        parent_controls_dict = get_all_inherited_controls(
            parent_uuid,
            zielobjekte_map,
            zielobjekt_to_gpp_controls_map,
            gpp_control_titles,
            memo,
        )
        inherited_control_ids.update(parent_controls_dict.keys())

    # Store the set of IDs in the memo
    memo[zielobjekt_uuid] = inherited_control_ids

    # Return the final dictionary of control IDs to titles
    return {cid: gpp_control_titles.get(cid, "") for cid in inherited_control_ids}


def generate_full_zielobjekt_controls_map(
    zielobjekte_map: Dict[str, Dict[str, str]],
    zielobjekt_to_gpp_controls_map: Dict[str, List[str]],
    gpp_control_titles: Dict[str, str],
) -> Dict[str, List[str]]:
    """
    Generates a complete map of all Zielobjekte to their inherited G++ controls.

    This function iterates through every Zielobjekt and recursively finds all
    associated controls, creating a deterministic and comprehensive map.

    Args:
        zielobjekte_map: A dictionary mapping Zielobjekt UUIDs to their data.
        zielobjekt_to_gpp_controls_map: A dictionary mapping Zielobjekt names
                                         to a list of G++ control IDs.
        gpp_control_titles: A dictionary mapping G++ control IDs to their titles.

    Returns:
        A dictionary where each key is a Zielobjekt UUID and the value is a
        sorted list of all inherited G++ control IDs.
    """
    full_controls_map = {}
    memo = {}  # Memoization table for the recursive calls

    for zielobjekt_uuid in zielobjekte_map:
        all_inherited_controls_with_titles = get_all_inherited_controls(
            zielobjekt_uuid,
            zielobjekte_map,
            zielobjekt_to_gpp_controls_map,
            gpp_control_titles,
            memo,
        )
        # We only need the control IDs (keys) for the final output
        full_controls_map[zielobjekt_uuid] = sorted(
            list(all_inherited_controls_with_titles.keys())
        )

    return full_controls_map
