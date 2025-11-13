"""
Pipeline Stage: Profile Generation

This stage generates OSCAL (Open Security Controls Assessment Language) profiles for
each Zielobjekt based on the controls mapped in the ZIELOBJEKT_CONTROLS_JSON_PATH file.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone

from constants import (
    ZIELOBJEKT_CONTROLS_JSON_PATH,
    SDT_OUTPUT_DIR,
    ZIELOBJEKTE_CSV_PATH,
    OSCAL_VERSION
)
from utils.file_utils import create_dir_if_not_exists, read_json_file, write_json_file, read_csv_file
from utils.text_utils import sanitize_filename

# Configure logging
logger = logging.getLogger(__name__)

def create_oscal_profile(zielobjekt_id, zielobjekt_name, controls):
    """
    Creates a basic OSCAL profile for a given Zielobjekt.

    Args:
        zielobjekt_id (str): The UUID of the Zielobjekt.
        zielobjekt_name (str): The name of the Zielobjekt.
        controls (list): A list of control IDs to include in the profile.

    Returns:
        dict: The OSCAL profile as a dictionary.
    """
    profile_uuid = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()
    catalog_url = "https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/refs/heads/main/Kompendien/Grundschutz%2B%2B-Kompendium/Grundschutz%2B%2B-Kompendium.json"

    profile = {
        "profile": {
            "uuid": profile_uuid,
            "metadata": {
                "title": f"{zielobjekt_id} {zielobjekt_name}",
                "last-modified": now_utc,
                "version": "0.0.1",
                "oscal-version": OSCAL_VERSION
            },
            "imports": [
                {
                    "href": catalog_url,
                    "include-controls": [
                        {
                            "with-ids": controls
                        }
                    ]
                }
            ]
        }
    }
    return profile

def run_stage_profiles():
    """
    Executes the profile generation stage.
    """
    logger.info("Starting Stage: Profile Generation")

    output_dir = os.path.join(SDT_OUTPUT_DIR, "profiles")
    create_dir_if_not_exists(output_dir)

    zielobjekt_controls = read_json_file(ZIELOBJEKT_CONTROLS_JSON_PATH)
    if not zielobjekt_controls:
        logger.error(f"Could not load Zielobjekt controls from {ZIELOBJEKT_CONTROLS_JSON_PATH}")
        return

    zielobjekte_data = read_csv_file(ZIELOBJEKTE_CSV_PATH)
    if not zielobjekte_data:
        logger.error(f"Could not load Zielobjekte from {ZIELOBJEKTE_CSV_PATH}")
        return

    zielobjekt_name_map = {row['UUID']: row['Zielobjekt'] for row in zielobjekte_data if 'UUID' in row and 'Zielobjekt' in row}

    for zielobjekt_id, controls in zielobjekt_controls.get("zielobjekt_controls_map", {}).items():
        zielobjekt_name = ""
        if zielobjekt_id == "ISMS":
            zielobjekt_name = "ISMS"
        elif zielobjekt_id in zielobjekt_name_map:
            zielobjekt_name = zielobjekt_name_map[zielobjekt_id]
        else:
            logger.warning(f"No name found for Zielobjekt with UUID {zielobjekt_id}. Skipping profile generation.")
            continue

        profile = create_oscal_profile(zielobjekt_id, zielobjekt_name, controls)

        sanitized_name = sanitize_filename(zielobjekt_name)
        output_filename = f"{sanitized_name}_profile.json"
        output_path = os.path.join(output_dir, output_filename)

        write_json_file(output_path, profile)
        logger.info(f"Generated OSCAL profile for {zielobjekt_name} at {output_path}")

    logger.info("Finished Stage: Profile Generation")

if __name__ == '__main__':
    # This allows the script to be run directly for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_stage_profiles()
