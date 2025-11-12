"""
This module contains the logic for the 'stage_strip' of the pipeline.

It is responsible for stripping down large JSON files to a more manageable
markdown format, using centralized path constants.
"""

import logging
import json
import os
from config import app_config
from constants import *

def _process_controls_recursively(controls, target_objects_list, isms_list):
    """
    Recursively processes a list of controls, sorting them into two lists
    based on the presence of 'target_objects'.
    """
    for control in controls:
        # Extract common control data
        control_id = control.get("id", "N/A")
        title = control.get("title", "N/A").replace("\n", " ")
        description = "N/A"
        for part in control.get("parts", []):
            if part.get("name") == "statement":
                description = part.get("prose", "N/A").replace("\n", " ")[:150]
                break
        uuid = "N/A"
        for prop in control.get("props", []):
            if prop.get("name") == "alt-identifier":
                uuid = prop.get("value", "N/A")
                break

        control_data = [control_id, title, description, uuid]

        # Sort the control into the appropriate list
        if _has_target_objects(control):
            target_objects_list.append(control_data)
        else:
            isms_list.append(control_data)

        # If there are nested controls, process them recursively
        if "controls" in control:
            _process_controls_recursively(control["controls"], target_objects_list, isms_list)

def _has_target_objects(control):
    """
    Checks if a control has a 'target_objects' property within its parts.
    """
    for part in control.get("parts", []):
        for prop in part.get("props", []):
            if prop.get("name") == "target_objects":
                return True
    return False

def _strip_gpp_file():
    """
    Reads the G++ Kompendium JSON, recursively finds all controls, separates
    them based on 'target_objects', and saves them as two markdown tables.
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Reading G++ Kompendium file from: {GPP_KOMPENDIUM_JSON_PATH}")

    if app_config.overwrite_temp_files:
        for path in [GPP_STRIPPED_MD_PATH, GPP_STRIPPED_ISMS_MD_PATH]:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Removed existing file: {path}")

    try:
        with open(GPP_KOMPENDIUM_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"G++ input file not found at: {GPP_KOMPENDIUM_JSON_PATH}")
        return
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from: {GPP_KOMPENDIUM_JSON_PATH}")
        return

    target_objects_controls = []
    isms_controls = []
    for main_group in data.get("catalog", {}).get("groups", []):
        for sub_group in main_group.get("groups", []):
            if "controls" in sub_group:
                _process_controls_recursively(sub_group["controls"], target_objects_controls, isms_controls)

    # --- Write the file for controls WITH target_objects ---
    header = "| ID | name | description | UUID (only for G++ controls!) |\n|---|---|---|---|\n"
    rows_target = [f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} |" for c in target_objects_controls]
    markdown_content_target = header + "\n".join(rows_target)

    os.makedirs(SDT_HELPER_OUTPUT_DIR, exist_ok=True)
    with open(GPP_STRIPPED_MD_PATH, "w", encoding="utf-8") as f:
        f.write(markdown_content_target)
    logger.debug(f"Successfully wrote {len(target_objects_controls)} controls with target_objects to: {GPP_STRIPPED_MD_PATH}")

    # --- Write the file for controls WITHOUT target_objects ---
    rows_isms = [f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} |" for c in isms_controls]
    markdown_content_isms = header + "\n".join(rows_isms)

    with open(GPP_STRIPPED_ISMS_MD_PATH, "w", encoding="utf-8") as f:
        f.write(markdown_content_isms)
    logger.debug(f"Successfully wrote {len(isms_controls)} ISMS controls to: {GPP_STRIPPED_ISMS_MD_PATH}")


def _strip_bsi_file():
    """
    Reads the BSI 2023 JSON, filters controls into allowed and non-allowed
    groups, and saves them as two separate markdown tables.
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Reading BSI 2023 file from: {BSI_2023_JSON_PATH}")

    try:
        with open(BSI_2023_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"BSI input file not found at: {BSI_2023_JSON_PATH}")
        return
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from: {BSI_2023_JSON_PATH}")
        return

    allowed_controls = []
    isms_controls = []
    for main_group in data.get("catalog", {}).get("groups", []):
        for baustein in main_group.get("groups", []):
            if baustein.get("class") == "baustein":
                for control in baustein.get("controls", []):
                    control_id = control.get("id", "N/A")
                    title = control.get("title", "N/A").replace("\n", " ")

                    description = "N/A"
                    for part in control.get("parts", []):
                        if part.get("class") == "maturity-level-defined":
                            for sub_part in part.get("parts", []):
                                if sub_part.get("name") == "statement":
                                    description = sub_part.get("prose", "N/A").replace("\n", " ")[:150]
                                    break
                            break

                    # Check if the control's main group is in the allowed list
                    control_main_group = control_id.split('.')[0]
                    if control_main_group in ALLOWED_MAIN_GROUPS:
                        allowed_controls.append([control_id, title, description])
                    else:
                        isms_controls.append([control_id, title, description])

    # Write the allowed controls file
    header = "| ID | name | description |\n|---|---|---|\n"
    allowed_rows = [f"| {c[0]} | {c[1]} | {c[2]} |" for c in allowed_controls]
    allowed_content = header + "\n".join(allowed_rows)

    os.makedirs(SDT_HELPER_OUTPUT_DIR, exist_ok=True)
    with open(BSI_STRIPPED_MD_PATH, "w", encoding="utf-8") as f:
        f.write(allowed_content)
    logger.debug(f"Successfully wrote {len(allowed_controls)} allowed BSI controls to: {BSI_STRIPPED_MD_PATH}")

    # Write the ISMS (non-allowed) controls file
    isms_rows = [f"| {c[0]} | {c[1]} | {c[2]} |" for c in isms_controls]
    isms_content = header + "\n".join(isms_rows)

    with open(BSI_STRIPPED_ISMS_MD_PATH, "w", encoding="utf-8") as f:
        f.write(isms_content)
    logger.debug(f"Successfully wrote {len(isms_controls)} ISMS BSI controls to: {BSI_STRIPPED_ISMS_MD_PATH}")


def run_stage_strip():
    """
    Executes the main logic of the stripping stage.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Executing stage_strip...")

    _strip_gpp_file()
    _strip_bsi_file()

    logger.info("stage_strip finished.")
