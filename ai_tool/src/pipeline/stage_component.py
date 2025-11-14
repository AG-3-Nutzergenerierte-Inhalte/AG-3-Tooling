"""
Pipeline Stage: Component Definition Generation

This stage generates OSCAL Component Definition files for each Baustein.
"""

import os
import uuid
import logging
from datetime import datetime, timezone

from constants import *
from utils.file_utils import create_dir_if_not_exists, read_json_file, write_json_file, read_csv_file
from utils.oscal_utils import validate_oscal
from utils.text_utils import sanitize_filename

# Configure logging
logger = logging.getLogger(__name__)

def get_component_type(baustein_id: str) -> str:
    """Determines the component type based on the Baustein ID prefix."""
    prefix = baustein_id.split('.')[0]
    type_map = {
        "NET": "interconnection",
        "APP": "software",
        "IND": "software",
        "SYS": "hardware",
        "ISMS": "policy",
        "ORP": "policy",
        "CON": "policy",
        "OPS": "policy",
        "DER": "policy",
        "INF": "physical",
    }
    return type_map.get(prefix, "service")

def generate_detailed_component(baustein_id: str, baustein_title: str, profile_path: str, mapping: dict, bsi_catalog: dict, gpp_catalog: dict, output_dir: str):
    """Generates the detailed, user-defined component file."""
    sanitized_name = sanitize_filename(f"{baustein_title}_{baustein_id}_{baustein_title}")

    if not os.path.exists(profile_path):
        logger.warning(f"Profile not found for {baustein_id} at {profile_path}. Skipping detailed component.")
        return

    profile = read_json_file(profile_path)
    if not profile:
        logger.error(f"Failed to load profile for {baustein_id} from {profile_path}")
        return

    gpp_controls_in_profile = profile.get("profile", {}).get("imports", [{}])[0].get("include-controls", [{}])[0].get("with-ids", [])

    bsi_controls_lookup = {}
    bsi_baustein_lookup = {}
    for group in bsi_catalog.get("catalog", {}).get("groups", []):
        for baustein in group.get("groups", []):
            bsi_baustein_lookup[baustein.get("id")] = baustein
            for control in baustein.get("controls", []):
                bsi_controls_lookup[control.get("id")] = control

    gpp_controls_lookup = {}
    for group in gpp_catalog.get("catalog", {}).get("groups", []):
        for control in group.get("controls", []):
            gpp_controls_lookup[control.get("id")] = control

    implemented_reqs = []
    for gpp_control_id in gpp_controls_in_profile:
        bsi_anforderung_id = next((bsi_id for bsi_id, gpp_id in mapping.items() if gpp_id == gpp_control_id), None)

        if bsi_anforderung_id and bsi_anforderung_id in bsi_controls_lookup:
            bsi_control_data = bsi_controls_lookup[bsi_anforderung_id]
            gpp_control_data = gpp_controls_lookup.get(gpp_control_id, {})

            prose = ""
            guidance = ""
            for part in gpp_control_data.get("parts", []):
                if part.get("name") == "prose":
                    prose = part.get("prose", "").strip().replace("\n", "<BR>")
                elif part.get("name") == "guidance":
                    guidance = part.get("prose", "").strip().replace("\n", "<BR>")

            description = f"{prose}BR{guidance}" if prose and guidance else prose or guidance

            statements = []
            for part in bsi_control_data.get("parts", []):
                if part.get("name") == "maturity-level-description":
                    statement_props = []
                    for sub_part in part.get("parts", []):
                        statement_props.append({
                            "name": sub_part.get("name", "").strip().replace("\n", "<BR>"),
                            "value": sub_part.get("prose", "").strip().replace("\n", "<BR>")
                        })

                    statements.append({
                        "statement-id": part.get("id", str(uuid.uuid4())),
                        "uuid": str(uuid.uuid4()),
                        "description": part.get("title", "No description available.").strip().replace("\n", "<BR>"),
                        "props": statement_props
                    })

            implemented_reqs.append({
                "uuid": str(uuid.uuid4()),
                "control-id": gpp_control_id,
                "description": description,
                "props": bsi_control_data.get("props", []),
                "statements": statements
            })

    baustein_key_for_parts = "ISMS.1" if baustein_id == "ISMS" else baustein_id
    baustein_parts = bsi_baustein_lookup.get(baustein_key_for_parts, {}).get("parts", [])

    component_props = []
    for part in baustein_parts:
        title = part.get("title")
        prose = part.get("prose")
        if title and prose:
            component_props.append({
                "name": title.strip().replace("\n", "<BR>"),
                "value": prose.strip().replace("\n", "<BR>")
            })

    component_definition = {
        "component-definition": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": f"{baustein_id} {baustein_title} - Benutzerdefiniert",
                "last-modified": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "oscal-version": OSCAL_VERSION,
            },
            "components": [{
                "uuid": str(uuid.uuid4()),
                "type": get_component_type(baustein_id),
                "title": f"{baustein_id} {baustein_title}",
                "description": f"This component represents the implementation of all controls for Baustein {baustein_id}.",
                "props": component_props,
                "control-implementations": [{
                    "uuid": str(uuid.uuid4()),
                    "source": profile_path.replace(os.path.abspath(REPO_ROOT), "https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main"),
                    "description": f"Implementation for all controls in Baustein {baustein_id}",
                    "implemented-requirements": implemented_reqs
                }]
            }]
        }
    }

    output_filename = f"{sanitized_name}-benutzerdefiniert-component.json"
    output_path = os.path.join(output_dir, output_filename)
    write_json_file(output_path, component_definition)

    validate_oscal(output_path, OSCAL_COMPONENT_SCHEMA_PATH)


def generate_minimal_component(baustein_id: str, baustein_title: str, profile_path: str, output_dir: str):
    """Generates the minimal component file that only imports the profile."""
    sanitized_name = sanitize_filename(f"{baustein_title}_{baustein_id}_{baustein_title}")

    if not os.path.exists(profile_path):
        logger.warning(f"Profile not found for {baustein_id} at {profile_path}. Skipping minimal component.")
        return

    profile = read_json_file(profile_path)
    if not profile:
        logger.error(f"Failed to load profile for {baustein_id} from {profile_path}")
        return

    gpp_controls = profile.get("profile", {}).get("imports", [{}])[0].get("include-controls", [{}])[0].get("with-ids", [])

    implemented_reqs = [{
        "uuid": str(uuid.uuid4()),
        "control-id": gpp_control_id,
        "description": f"This control is implemented as defined in the profile."
    } for gpp_control_id in gpp_controls]

    component_definition = {
        "component-definition": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": f"{baustein_id} {baustein_title}",
                "last-modified": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "oscal-version": OSCAL_VERSION,
            },
            "components": [{
                "uuid": str(uuid.uuid4()),
                "type": get_component_type(baustein_id),
                "title": f"{baustein_id} {baustein_title}",
                "description": f"This component imports the profile for Baustein {baustein_id}.",
                "control-implementations": [{
                    "uuid": str(uuid.uuid4()),
                    "source": profile_path.replace(os.path.abspath(REPO_ROOT), "https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main"),
                    "description": f"Imports all controls from the profile for Baustein {baustein_id}.",
                    "implemented-requirements": implemented_reqs
                }]
            }]
        }
    }

    output_filename = f"{sanitized_name}-component.json"
    output_path = os.path.join(output_dir, output_filename)
    write_json_file(output_path, component_definition)

    validate_oscal(output_path, OSCAL_COMPONENT_SCHEMA_PATH)


def run_stage_component():
    """Executes the component definition generation stage."""
    logger.info("Starting Stage: Component Definition Generation")

    output_dir = os.path.join(SDT_OUTPUT_DIR, "components", "DE")
    profile_dir = SDT_PROFILES_DIR
    create_dir_if_not_exists(output_dir)
    create_dir_if_not_exists(SDT_COMPONENTS_GPP_DIR)

    zielobjekte_data = read_csv_file(ZIELOBJEKTE_CSV_PATH)
    if not zielobjekte_data:
        logger.error(f"Could not load Zielobjekte from {ZIELOBJEKTE_CSV_PATH}")
        return
    zielobjekt_name_map = {row['UUID'].strip(): row['Zielobjekt'].strip() for row in zielobjekte_data if 'UUID' in row and 'Zielobjekt' in row}

    baustein_zielobjekt_map = read_json_file(BAUSTEINE_ZIELOBJEKTE_JSON_PATH)
    controls_anforderungen = read_json_file(CONTROLS_ANFORDERUNGEN_JSON_PATH)
    prozessbausteine_mapping = read_json_file(PROZZESSBAUSTEINE_CONTROLS_JSON_PATH)
    bsi_catalog = read_json_file(BSI_2023_JSON_PATH)
    gpp_catalog = read_json_file(GPP_KOMPENDIUM_JSON_PATH)

    if not all([zielobjekt_name_map, baustein_zielobjekt_map, controls_anforderungen, prozessbausteine_mapping, bsi_catalog, gpp_catalog]):
        logger.error("Failed to load one or more required data files. Aborting.")
        return

    baustein_titles = {
        value['baustein_id']: value['zielobjekt_name']
        for value in controls_anforderungen.values() if 'baustein_id' in value and 'zielobjekt_name' in value
    }

    bsi_baustein_title_lookup = {}
    for group in bsi_catalog.get("catalog", {}).get("groups", []):
        for baustein in group.get("groups", []):
            if baustein.get("id") and baustein.get("title"):
                bsi_baustein_title_lookup[baustein["id"]] = baustein["title"]

    for baustein_id, zielobjekt_uuid in baustein_zielobjekt_map.get("baustein_zielobjekt_map", {}).items():
        logger.info(f"Processing Baustein: {baustein_id}")

        zielobjekt_name = zielobjekt_name_map.get(zielobjekt_uuid)
        if not zielobjekt_name:
            logger.warning(f"No name found for Zielobjekt UUID {zielobjekt_uuid} (Baustein {baustein_id}). Skipping.")
            continue

        baustein_title = baustein_titles.get(baustein_id) or bsi_baustein_title_lookup.get(baustein_id)
        if not baustein_title:
            logger.warning(f"No title found for Baustein ID {baustein_id}. Using Zielobjekt name as fallback.")
            baustein_title = zielobjekt_name

        sanitized_zielobjekt_name = sanitize_filename(zielobjekt_name)
        profile_filename = f"{sanitized_zielobjekt_name}_profile.json"
        profile_path = os.path.join(profile_dir, profile_filename)

        mapping = controls_anforderungen.get(zielobjekt_uuid, {}).get("mapping", {})

        generate_detailed_component(baustein_id, baustein_title, profile_path, mapping, bsi_catalog, gpp_catalog, output_dir)
        generate_minimal_component(baustein_id, baustein_title, profile_path, output_dir)

    logger.info("Processing special ISMS Baustein")
    isms_baustein_id = "ISMS"
    isms_baustein_title = "ISMS"
    isms_profile_path = os.path.join(profile_dir, "isms_profile.json")
    isms_mapping = prozessbausteine_mapping.get("prozessbausteine_mapping", {})
    generate_detailed_component(isms_baustein_id, isms_baustein_title, isms_profile_path, isms_mapping, bsi_catalog, gpp_catalog, output_dir)
    generate_minimal_component(isms_baustein_id, isms_baustein_title, isms_profile_path, output_dir)

    generate_zielobjekt_components()

    logger.info("Finished Stage: Component Definition Generation")

def generate_zielobjekt_components():
    """Generates minimal component files for all Zielobjekte."""
    logger.info("Starting generation of Zielobjekt components.")

    zielobjekte_data = read_csv_file(ZIELOBJEKTE_CSV_PATH)
    if not zielobjekte_data:
        logger.error(f"Could not load Zielobjekte from {ZIELOBJEKTE_CSV_PATH}")
        return

    for row in zielobjekte_data:
        zielobjekt_name = row.get('Zielobjekt')
        if not zielobjekt_name:
            continue

        sanitized_name = sanitize_filename(zielobjekt_name)
        profile_filename = f"{sanitized_name}_profile.json"
        profile_path = os.path.join(SDT_PROFILES_DIR, profile_filename)

        if not os.path.exists(profile_path):
            logger.warning(f"Profile not found for {zielobjekt_name} at {profile_path}. Skipping component generation.")
            continue

        profile = read_json_file(profile_path)
        if not profile:
            logger.error(f"Failed to load profile for {zielobjekt_name} from {profile_path}")
            continue

        gpp_controls = profile.get("profile", {}).get("imports", [{}])[0].get("include-controls", [{}])[0].get("with-ids", [])

        implemented_reqs = [{
            "uuid": str(uuid.uuid4()),
            "control-id": gpp_control_id,
            "description": f"This control is implemented as defined in the profile."
        } for gpp_control_id in gpp_controls]


        component_definition = {
            "component-definition": {
                "uuid": str(uuid.uuid4()),
                "metadata": {
                    "title": zielobjekt_name,
                    "last-modified": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "oscal-version": OSCAL_VERSION,
                },
                "components": [{
                    "uuid": str(uuid.uuid4()),
                    "type": "service",
                    "title": zielobjekt_name,
                    "description": f"This component imports the profile for {zielobjekt_name}.",
                    "control-implementations": [{
                        "uuid": str(uuid.uuid4()),
                        "source": profile_path.replace(os.path.abspath(REPO_ROOT), "https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main"),
                        "description": f"Imports all controls from the profile for {zielobjekt_name}.",
                        "implemented-requirements": implemented_reqs
                    }]
                }]
            }
        }

        output_filename = f"{sanitized_name}-component.json"
        output_path = os.path.join(SDT_COMPONENTS_GPP_DIR, output_filename)
        write_json_file(output_path, component_definition)
        validate_oscal(output_path, OSCAL_COMPONENT_SCHEMA_PATH)
        logger.info(f"Generated component for Zielobjekt: {zielobjekt_name}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_stage_component()
