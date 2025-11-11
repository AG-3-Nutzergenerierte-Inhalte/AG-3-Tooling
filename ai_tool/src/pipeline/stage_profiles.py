"""
Core logic for Stage 'Profiles': OSCAL Profile Generation.

This module is responsible for generating OSCAL profiles for each Zielobjekt
and for the ISMS controls.
"""

import logging
import os
import uuid
from typing import Dict, Any, List

from constants import (
    ZIELOBJEKT_CONTROLS_JSON_PATH,
    GPP_STRIPPED_ISMS_MD_PATH,
    PROZZESSBAUSTEINE_CONTROLS_JSON_PATH,
    ZIELOBJEKTE_CSV_PATH,
    SDT_OUTPUT_DIR,
)
from utils import data_loader, data_parser

logger = logging.getLogger(__name__)


def _create_profile_json(title: str, control_ids: List[str]) -> Dict[str, Any]:
    """
    Creates a dictionary representing an OSCAL profile.
    """
    return {
        "profile": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": title,
                "version": "1",
                "oscal-version": "1.1.3",
            },
            "import": {
                "href": "https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/refs/heads/main/Kompendien/Grundschutz%2B%2B-Kompendium/Grundschutz%2B%2B-Kompendium.json"
            },
            "include": {"with-ids": control_ids},
        }
    }


def run_stage_profiles() -> None:
    """
    Executes the main steps for the profile generation stage.
    """
    logger.info("Starting Stage 'Profiles': OSCAL Profile Generation...")

    # --- Generate and save ISMS controls mapping ---
    gpp_isms_stripped_md = data_loader.load_text_file(GPP_STRIPPED_ISMS_MD_PATH)
    isms_control_ids = data_parser.parse_gpp_isms_controls(gpp_isms_stripped_md)
    data_loader.save_json_file(
        {"isms_controls": isms_control_ids}, PROZZESSBAUSTEINE_CONTROLS_JSON_PATH
    )

    # --- Generate ISMS Profile ---
    isms_profile = _create_profile_json("ISMS_profile", isms_control_ids)
    isms_profile_path = os.path.join(SDT_OUTPUT_DIR, "ISMS_profile.json")
    data_loader.save_json_file(isms_profile, isms_profile_path)
    logger.info(f"Successfully generated ISMS profile at: {isms_profile_path}")

    # --- Generate Zielobjekt Profiles ---
    zielobjekt_controls_map = data_loader.load_json_file(
        ZIELOBJEKT_CONTROLS_JSON_PATH
    ).get("zielobjekt_controls_map", {})
    zielobjekte_data = data_loader.load_zielobjekte_csv(ZIELOBJEKTE_CSV_PATH)
    zielobjekte_hierarchy = data_parser.parse_zielobjekte_hierarchy(zielobjekte_data)

    for zielobjekt_uuid, control_ids in zielobjekt_controls_map.items():
        zielobjekt_name = zielobjekte_hierarchy.get(zielobjekt_uuid, {}).get(
            "name", "Unknown"
        )
        profile_title = f"{zielobjekt_name}_profile"
        profile_json = _create_profile_json(profile_title, control_ids)

        # Sanitize filename
        safe_filename = "".join(c for c in zielobjekt_name if c.isalnum() or c in (' ', '_')).rstrip()
        safe_filename = f"{safe_filename.replace(' ', '_')}_profile.json"

        profile_path = os.path.join(SDT_OUTPUT_DIR, safe_filename)
        data_loader.save_json_file(profile_json, profile_path)
        logger.info(f"Successfully generated profile for '{zielobjekt_name}' at: {profile_path}")

    logger.info("Stage 'Profiles' completed successfully.")
