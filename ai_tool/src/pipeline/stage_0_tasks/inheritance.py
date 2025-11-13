"""
Handles the recursive inheritance logic for Zielobjekt controls.

This module provides the functionality to traverse the Zielobjekt hierarchy
and aggregate a complete list of all inherited G++ controls for any given
Zielobjekt.
"""

import logging
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


def get_all_inherited_controls(
    zielobjekt_uuid: str,
    zielobjekte_map: Dict[str, Dict[str, str]],
    zielobjekt_to_gpp_controls_map: Dict[str, List[str]],
    gpp_control_titles: Dict[str, str],
    memo: Optional[Dict[str, Set[str]]] = None,
    _stack: Optional[Set[str]] = None,
) -> Dict[str, str]:
    """
    Recursively aggregates all inherited G++ controls for a Zielobjekt.
    Includes cycle detection and robust handling of hierarchy data.

    Args:
        zielobjekt_uuid: The UUID of the Zielobjekt to process.
        zielobjekte_map: The full hierarchy map.
        zielobjekt_to_gpp_controls_map: Map of names to explicit control IDs.
        gpp_control_titles: Map of control IDs to titles.
        memo: Memoization dictionary (internal use).
        _stack: Recursion stack for cycle detection (internal use).

    Returns:
        A dictionary of control IDs to their titles.
    """
    # --- Initialization ---
    if memo is None:
        memo = {}
    if _stack is None:
        _stack = set()

    # --- Input Validation/Normalization ---
    # Ensure the input UUID is treated consistently (e.g., stripped of whitespace)
    current_uuid = zielobjekt_uuid.strip() if isinstance(zielobjekt_uuid, str) else ""

    if not current_uuid:
        return {}

    # --- Cycle Detection ---
    if current_uuid in _stack:
        logger.error(
            f"Cycle detected in Zielobjekt hierarchy involving UUID: {current_uuid}. "
            f"Please check ChildOfUUID relationships in the CSV. Stack: {_stack}"
        )
        # Stop recursion immediately upon detecting a cycle
        return {}

    # --- Memoization Check ---
    if current_uuid in memo:
        # The memo stores IDs, so we need to convert it back to a dict with titles
        return {cid: gpp_control_titles.get(cid, "") for cid in memo[current_uuid]}

    _stack.add(current_uuid)

    # --- Hierarchy Traversal ---
    current_zielobjekt = zielobjekte_map.get(current_uuid)
    if not current_zielobjekt:
        # This might happen if a ChildOfUUID points to a non-existent UUID
        logger.warning(f"Zielobjekt UUID {current_uuid} not found in map during inheritance traversal. Possibly a broken reference.")
        _stack.remove(current_uuid)
        return {}

    # Get control IDs directly associated with the current Zielobjekt
    zielobjekt_name = current_zielobjekt.get("Zielobjekt", "")
    # Use set for automatic deduplication
    inherited_control_ids = set(zielobjekt_to_gpp_controls_map.get(zielobjekt_name, []))

    # --- Robust Parent UUID Handling ---
    # Ensure we handle potential messy data (whitespace, non-string types) robustly
    parent_uuid_raw = current_zielobjekt.get("ChildOfUUID")
    parent_uuid: Optional[str] = None

    if isinstance(parent_uuid_raw, str):
        stripped_uuid = parent_uuid_raw.strip()
        if stripped_uuid:
            parent_uuid = stripped_uuid

    # Recursively get control IDs from the parent
    if parent_uuid:
        # The recursive call returns a dict, we only need the keys (IDs) for the set logic
        parent_controls_dict = get_all_inherited_controls(
            parent_uuid,
            zielobjekte_map,
            zielobjekt_to_gpp_controls_map,
            gpp_control_titles,
            memo,
            _stack,
        )
        inherited_control_ids.update(parent_controls_dict.keys())

    # Remove the current UUID from the stack as we backtrack
    _stack.remove(current_uuid)

    # Store the set of IDs in the memo
    memo[current_uuid] = inherited_control_ids

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
    memo = {}  # Memoization table shared across all calls

    for zielobjekt_uuid in zielobjekte_map:
        # Initialize the stack for cycle detection for each traversal start
        all_inherited_controls_with_titles = get_all_inherited_controls(
            zielobjekt_uuid,
            zielobjekte_map,
            zielobjekt_to_gpp_controls_map,
            gpp_control_titles,
            memo,
            _stack=set(), # Initialize a fresh stack for this specific traversal
        )
        
        # Normalize the key for the output map as well
        normalized_uuid = zielobjekt_uuid.strip() if isinstance(zielobjekt_uuid, str) else zielobjekt_uuid
        if normalized_uuid:
            # We only need the control IDs (keys) for the final output
            full_controls_map[normalized_uuid] = sorted(
                list(all_inherited_controls_with_titles.keys())
            )

    return full_controls_map