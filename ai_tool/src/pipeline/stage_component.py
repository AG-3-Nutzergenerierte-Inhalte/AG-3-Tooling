"""
Pipeline Stage: Component Definition Generation

This stage generates OSCAL Component Definition files for each Baustein.
"""
import sys
import urllib.parse
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

def get_source_url(local_path: str) -> str:
    """Constructs the correct remote GitHub URL for a given local file path."""
    base_url = "https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main"
    sdt_root = os.path.join(REPO_ROOT, "Stand-der-Technik-Bibliothek")

    relative_path = os.path.relpath(local_path, sdt_root)
    relative_path_posix = relative_path.replace(os.sep, '/')
    encoded_path = urllib.parse.quote(relative_path_posix, safe='/')

    return f"{base_url}/{encoded_path}"

def generate_detailed_component(baustein_id: str, baustein_title: str, zielobjekt_name: str, profile_path: str, metadata: list, bsi_catalog: dict, gpp_catalog: dict, output_dir: str):
    """Generates the detailed, user-defined component file."""
    sanitized_zielobjekt_name = sanitize_filename(zielobjekt_name)
    sanitized_baustein_id = sanitize_filename(baustein_id)
    output_filename = f"{sanitized_zielobjekt_name}_{sanitized_baustein_id}-enhanced-component.json"

    if not os.path.exists(profile_path):
        logger.warning(f"Profile not found for {baustein_id} at {profile_path}. Skipping detailed component.")
        return

    gpp_controls_lookup = {control.get("id"): control for group in gpp_catalog.get("catalog", {}).get("groups", []) for control in group.get("controls", [])}

    implemented_reqs = []
    for item in metadata:
        if item.get("sub_requirement_id", "").startswith(baustein_id):
            gpp_control_id = item["gpp_control_id"]
            gpp_control_data = gpp_controls_lookup.get(gpp_control_id, {})

            prose = "".join([part.get("prose", "").strip().replace("\n", "<BR>") for part in gpp_control_data.get("parts", []) if part.get("name") == "prose"])
            guidance = "".join([part.get("prose", "").strip().replace("\n", "<BR>") for part in gpp_control_data.get("parts", []) if part.get("name") == "guidance"])
            description = f"{prose}BR{guidance}" if prose and guidance else prose or guidance

            implemented_reqs.append({
                "uuid": str(uuid.uuid4()),
                "control-id": gpp_control_id,
                "description": description,
                "props": [
                    {"name": "maturity-level", "value": item.get("maturity_level")},
                    {"name": "phase", "value": item.get("phase")}
                ]
            })

    bsi_baustein_lookup = {baustein.get("id"): baustein for group in bsi_catalog.get("catalog", {}).get("groups", []) for baustein in group.get("groups", [])}
    baustein_parts = bsi_baustein_lookup.get(baustein_id, {}).get("parts", [])
    component_props = [{"name": part.get("title").strip(), "value": part.get("prose").strip()} for part in baustein_parts if part.get("title") and part.get("prose")]

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
                    "source": get_source_url(profile_path),
                    "description": f"Implementation for all controls in Baustein {baustein_id}",
                    "implemented-requirements": implemented_reqs
                }]
            }]
        }
    }

    output_path = os.path.join(output_dir, output_filename)
    write_json_file(output_path, component_definition)
    validate_oscal(output_path, OSCAL_COMPONENT_SCHEMA_PATH)


def generate_minimal_component(baustein_id: str, baustein_title: str, zielobjekt_name: str, profile_path: str, output_dir: str):
    """Generates the minimal component file that only imports the profile."""
    sanitized_zielobjekt_name = sanitize_filename(zielobjekt_name)
    sanitized_baustein_id = sanitize_filename(baustein_id)
    output_filename = f"{sanitized_zielobjekt_name}_{sanitized_baustein_id}-component.json"

    if not os.path.exists(profile_path):
        logger.warning(f"Profile not found for {baustein_id} at {profile_path}. Skipping minimal component.")
        return

    profile = read_json_file(profile_path)
    if not profile:
        logger.error(f"Failed to load profile for {baustein_id} from {profile_path}")
        return

    gpp_controls = profile.get("profile", {}).get("imports", [{}])[0].get("include-controls", [{}])[0].get("with-ids", [])

    implemented_reqs = [{"uuid": str(uuid.uuid4()), "control-id": gpp_control_id, "description": "Implemented as defined in the profile."} for gpp_control_id in gpp_controls]

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
                    "source": get_source_url(profile_path),
                    "description": f"Imports all controls from the profile for Baustein {baustein_id}.",
                    "implemented-requirements": implemented_reqs
                }]
            }]
        }
    }

    output_path = os.path.join(output_dir, output_filename)
    write_json_file(output_path, component_definition)
    validate_oscal(output_path, OSCAL_COMPONENT_SCHEMA_PATH)


def run_stage_component():
    """Executes the component definition generation stage."""
    logger.info("Starting Stage: Component Definition Generation")

    output_dir = SDT_COMPONENTS_DE_DIR
    profile_dir = SDT_PROFILES_DIR
    create_dir_if_not_exists(output_dir)
    create_dir_if_not_exists(SDT_COMPONENTS_GPP_DIR)

    try:
        zielobjekte_data = read_csv_file(ZIELOBJEKTE_CSV_PATH)
        zielobjekt_name_map = {row['UUID'].strip(): row['Zielobjekt'].strip() for row in zielobjekte_data if 'UUID' in row and 'Zielobjekt' in row}

        baustein_zielobjekt_map = read_json_file(BAUSTEIN_ZIELOBJEKT_JSON_PATH).get("baustein_zielobjekt_map", {})
        generated_metadata = read_json_file(GENERATED_METADATA_JSON_PATH).get("generated_metadata", [])
        bsi_catalog = read_json_file(BSI_2023_JSON_PATH)
        gpp_catalog = read_json_file(GPP_KOMPENDIUM_JSON_PATH)

        bsi_baustein_title_lookup = {baustein.get("id"): baustein.get("title") for group in bsi_catalog.get("catalog", {}).get("groups", []) for baustein in group.get("groups", [])}
    except (IOError, FileNotFoundError, TypeError, KeyError) as e:
        logger.critical(f"Failed to load critical data for component generation: {e}", exc_info=True)
        sys.exit(1)

    for baustein_id, zielobjekt_uuid in baustein_zielobjekt_map.items():
        logger.info(f"Processing Baustein: {baustein_id}")
        zielobjekt_name = zielobjekt_name_map.get(zielobjekt_uuid)
        if not zielobjekt_name:
            logger.warning(f"No name found for Zielobjekt UUID {zielobjekt_uuid}. Skipping.")
            continue

        baustein_title = bsi_baustein_title_lookup.get(baustein_id, zielobjekt_name)
        sanitized_zielobjekt_name = sanitize_filename(zielobjekt_name)
        profile_path = os.path.join(profile_dir, f"{sanitized_zielobjekt_name}_profile.json")

        generate_detailed_component(baustein_id, baustein_title, zielobjekt_name, profile_path, generated_metadata, bsi_catalog, gpp_catalog, output_dir)
        generate_minimal_component(baustein_id, baustein_title, zielobjekt_name, profile_path, output_dir)

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
        profile_path = os.path.join(SDT_PROFILES_DIR, f"{sanitized_name}_profile.json")

        if not os.path.exists(profile_path):
            logger.warning(f"Profile not found for {zielobjekt_name}. Skipping component generation.")
            continue

        profile = read_json_file(profile_path)
        if not profile:
            logger.error(f"Failed to load profile for {zielobjekt_name}")
            continue

        gpp_controls = profile.get("profile", {}).get("imports", [{}])[0].get("include-controls", [{}])[0].get("with-ids", [])
        implemented_reqs = [{"uuid": str(uuid.uuid4()), "control-id": gpp_control_id, "description": "Implemented as defined in profile."} for gpp_control_id in gpp_controls]

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
                        "source": get_source_url(profile_path),
                        "description": f"Imports all controls from the profile for {zielobjekt_name}.",
                        "implemented-requirements": implemented_reqs
                    }]
                }]
            }
        }
        output_path = os.path.join(SDT_COMPONENTS_GPP_DIR, f"{sanitized_name}-component.json")
        write_json_file(output_path, component_definition)
        validate_oscal(output_path, OSCAL_COMPONENT_SCHEMA_PATH)
        logger.info(f"Generated component for Zielobjekt: {zielobjekt_name}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_stage_component()
