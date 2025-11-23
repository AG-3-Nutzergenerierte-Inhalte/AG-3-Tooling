"""
Pipeline Stage: Component Definition Generation

This stage generates OSCAL Component Definition files for each Baustein.
"""
import sys
import urllib.parse
import os
import uuid
import logging
import json
import asyncio
from datetime import datetime, timezone

from constants import *
from constants import GROUND_TRUTH_MODEL_PRO
from config import app_config
from utils.file_utils import create_dir_if_not_exists, read_json_file, write_json_file, read_csv_file, read_text_file
from utils.data_parser import extract_all_gpp_controls, filter_markdown
from utils.oscal_utils import validate_oscal
from utils.text_utils import sanitize_filename
from clients.ai_client import AiClient

# Configure logging
logger = logging.getLogger(__name__)

# Constants for schema
ENHANCED_CONTROL_RESPONSE_SCHEMA_PATH = os.path.join(SRC_ROOT, "assets/schemas/enhanced_control_response_schema.json")

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

    # Get the path relative to the submodule root, not the whole repo.
    relative_path = os.path.relpath(local_path, sdt_root)

    # Ensure forward slashes for the URL and encode special characters.
    relative_path_posix = relative_path.replace(os.sep, '/')
    encoded_path = urllib.parse.quote(relative_path_posix, safe='/')

    return f"{base_url}/{encoded_path}"

def build_oscal_control(control_id: str, title: str, generated_data: dict) -> dict:
    """Constructs the OSCAL implemented-requirement object from AI generated data."""
    oscal_statements = []
    levels = [("Partial", "partial", "1"), ("Foundational", "foundational", "2"), ("Defined", "defined", "3"), ("Enhanced", "enhanced", "4"), ("Comprehensive", "comprehensive", "5")]

    for title_suffix, class_suffix, level_num in levels:
        statement_key = f"level_{level_num}_statement"
        guidance_key = f"level_{level_num}_guidance"
        assessment_key = f"level_{level_num}_assessment"

        statement_text = generated_data.get(statement_key)

        if statement_text:
            statement_props = [
                {"name": "statement", "value": statement_text},
                {"name": "guidance", "value": generated_data.get(guidance_key, "")},
                {"name": "assessment-method", "value": generated_data.get(assessment_key, "")}
            ]

            oscal_statements.append({
                "statement-id": f"{control_id}-m{level_num}",
                "uuid": str(uuid.uuid4()),
                "description": f"Maturity Level {level_num}: {title_suffix}",
                "props": statement_props
            })

    props_ns = "https://www.bsi.bund.de/ns/grundschutz"

    # Extract props from generated data
    props = [
        {"name": "phase", "value": generated_data.get('phase', 'N/A'), "ns": props_ns},
        {"name": "effective_on_c", "value": str(generated_data.get("effective_on_c", "")).lower(), "ns": props_ns},
        {"name": "effective_on_i", "value": str(generated_data.get("effective_on_i", "")).lower(), "ns": props_ns},
        {"name": "effective_on_a", "value": str(generated_data.get("effective_on_a", "")).lower(), "ns": props_ns}
    ]

    # Add class if it exists
    if generated_data.get("class"):
         props.append({"name": "class", "value": generated_data.get("class"), "ns": props_ns})

    # Add practice if it exists (though not currently in AI schema, keeping for future proofing or if added later)
    if generated_data.get("practice"):
         props.append({"name": "practice", "value": generated_data.get("practice"), "ns": props_ns})

    return {
        "uuid": str(uuid.uuid4()),
        "control-id": control_id,
        "description": f"(BSI Baustein context) Implementation of {title}", # Placeholder description, real one is generated inside generate_detailed_component context
        "props": props,
        "statements": oscal_statements
    }

async def generate_detailed_component(baustein_id: str, baustein_title: str, zielobjekt_name: str, profile_path: str, bsi_catalog: dict, gpp_controls_lookup: dict, output_dir: str, ai_client: AiClient):
    """Generates the detailed, user-defined component file with AI-enhanced data."""
    sanitized_zielobjekt_name = sanitize_filename(zielobjekt_name)
    sanitized_baustein_id = sanitize_filename(baustein_id)
    output_filename = f"{sanitized_zielobjekt_name}_{sanitized_baustein_id}-enhanced-component.json"

    if not os.path.exists(profile_path):
        logger.warning(f"Profile not found for {baustein_id} at {profile_path}. Skipping detailed component.")
        return

    profile = read_json_file(profile_path)
    if not profile:
        logger.error(f"Failed to load profile for {baustein_id} from {profile_path}")
        return

    # 1. Identify Target Controls
    gpp_controls_in_profile = profile.get("profile", {}).get("imports", [{}])[0].get("include-controls", [{}])[0].get("with-ids", [])
    logger.debug(f"Expected controls for Baustein {baustein_id}: {gpp_controls_in_profile}")

    # 2. Extract Baustein Context (Parts)
    bsi_baustein_lookup = {}
    for group in bsi_catalog.get("catalog", {}).get("groups", []):
        for baustein in group.get("groups", []):
            bsi_baustein_lookup[baustein.get("id")] = baustein

    baustein_key_for_parts = "ISMS.1" if baustein_id == "ISMS" else baustein_id
    baustein_data = bsi_baustein_lookup.get(baustein_key_for_parts, {})
    baustein_parts_text = ""
    component_props = []

    if baustein_data:
        # Include 'introduction' and 'risk' parts as context
        for part in baustein_data.get("parts", []):
            part_name = part.get("name", "")
            title = part.get("title")
            prose = part.get("prose")

            # Store props for all parts with title and prose
            if title and prose:
                 component_props.append({
                    "name": title.strip().replace("\n", "<BR>"),
                    "value": prose.strip().replace("\n", "<BR>")
                })

            # Specific filtering for context generation
            if part_name == "introduction" and prose:
                 baustein_parts_text += f"Part: {title or 'Introduction'}\nContent: {prose}\n\n"

            if part_name == "risk" and prose:
                 baustein_parts_text += f"--------------------------------------------------\n## Risks\nContent: {prose}\n\n"

    # 3. Prepare AI Input for Controls
    control_descriptions = {} # Store original descriptions to prepend later

    # Load markdown files for filtering. This is done here but ideally could be passed in.
    # Reading files inside the loop is inefficient if called many times, but we rely on OS caching or we can load it once outside.
    # Given the function signature, we load it here or assume it's fast enough.
    # To follow the architecture, we should have loaded these outside, but the function signature doesn't support it yet.
    # However, for correctness as per instructions, I will read them here or use a cached approach if possible.
    # I'll read them here for simplicity as per instructions.

    gpp_md_path = GPP_STRIPPED_ISMS_MD_PATH if baustein_id == "ISMS" else GPP_STRIPPED_MD_PATH
    gpp_markdown_content = read_text_file(gpp_md_path)

    if not gpp_markdown_content:
        logger.error(f"Failed to load markdown content from {gpp_md_path}")
        return

    filtered_markdown = filter_markdown(gpp_controls_in_profile, gpp_markdown_content)

    for gpp_control_id in gpp_controls_in_profile:
        gpp_control_data = gpp_controls_lookup.get(gpp_control_id, {})

        prose = ""
        guidance = ""
        for part in gpp_control_data.get("parts", []):
            if part.get("name") == "prose":
                prose = part.get("prose", "").strip()
            elif part.get("name") == "guidance":
                guidance = part.get("prose", "").strip()

        # Store for description generation
        desc_prose = prose.replace("\n", "<BR>")
        desc_guidance = guidance.replace("\n", "<BR>")
        control_descriptions[gpp_control_id] = f"{desc_prose}BR{desc_guidance}" if desc_prose and desc_guidance else desc_prose or desc_guidance

    # 4. Call AI
    if not filtered_markdown:
        logger.warning(f"No controls found (or filtered) for profile {profile_path}. Skipping generation.")
        return

    # Construct the full prompt input
    # Retrieve the prompt template from the config file, if stored there, or hardcode/construct here
    # The requirement says "store in a text file in assets". But I put it in prompt_config.json as requested.
    # The AiClient loads prompt_config.json internally for system message, but for this specific prompt
    # we need to pass the full prompt text (template + data) to generate_validated_json_response.

    # We need to read the prompt template.
    # Ideally AiClient handles templates, but generate_validated_json_response takes 'prompt' string.
    # So I will load the template here.

    try:
        prompt_config = read_json_file(PROMPT_CONFIG_PATH)
        prompt_template = prompt_config.get("generate_enhanced_controls_prompt", "")
    except Exception as e:
        logger.error(f"Failed to load prompt config: {e}")
        return

    # Combine template with data
    # The template expects "input list" which we provide as Markdown now
    full_prompt = f"{prompt_template}\n\nContext:\nTitle: {baustein_title}\n{baustein_parts_text}\n\nInput Data (Markdown):\n{filtered_markdown}"

    try:
        # Load schema for validation
        response_schema = read_json_file(ENHANCED_CONTROL_RESPONSE_SCHEMA_PATH)

        # Use GROUND_TRUTH_MODEL_PRO for this complex task as requested
        ai_response = await ai_client.generate_validated_json_response(
            prompt=full_prompt,
            json_schema=response_schema,
            request_context_log=f"EnhancedComponent-{baustein_id}",
            model_override=GROUND_TRUTH_MODEL_PRO
        )

        # ai_response should be a list of objects based on the schema
        if not isinstance(ai_response, list):
            logger.error(f"AI response is not a list as expected. Type: {type(ai_response)}")
            return

    except Exception as e:
        logger.error(f"AI Generation failed for Baustein {baustein_id}: {e}")
        return

    # 5. Process AI Response & Build OSCAL
    implemented_reqs = []

    # Create a map for faster lookup of AI results with ID normalization (strip)
    ai_results_map = {}
    ai_ids = []
    for item in ai_response:
        if 'id' in item:
            clean_id = item['id'].strip()
            ai_results_map[clean_id] = item
            ai_ids.append(clean_id)

    logger.debug(f"AI returned data for {len(ai_ids)} controls. IDs: {ai_ids}")

    for gpp_control_id in gpp_controls_in_profile:
        # Normalize lookup key
        lookup_id = gpp_control_id.strip()
        generated_data = ai_results_map.get(lookup_id)

        if generated_data:
            control_title = gpp_controls_lookup.get(gpp_control_id, {}).get("title", "")

            # Build the base object
            oscal_obj = build_oscal_control(gpp_control_id, control_title, generated_data)

            # Enrich description with source info as per requirement
            original_description = control_descriptions.get(gpp_control_id, "")
            # Requirement B.3/D.3: "description must be prepended with context about its origin (e.g., (BSI Baustein ID...))"
            # And "followed by a concatenation of the prose and guidance from the G++ control"

            prefix = f"(BSI Baustein {baustein_id})"
            oscal_obj["description"] = f"{prefix} {original_description}".strip()

            implemented_reqs.append(oscal_obj)
        else:
            logger.warning(f"No AI generated data for control {gpp_control_id} (Looked for '{lookup_id}' in AI response)")

    # 6. Final Component Assembly
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


async def run_stage_component():
    """Executes the component definition generation stage."""
    logger.info("Starting Stage: Component Definition Generation")

    # Initialize AI Client
    try:
        ai_client = AiClient(app_config)
    except Exception as e:
        logger.critical(f"Failed to initialize AI Client: {e}", exc_info=True)
        sys.exit(1)

    output_dir = SDT_COMPONENTS_DE_DIR
    profile_dir = SDT_PROFILES_DIR
    try:
        create_dir_if_not_exists(output_dir)
        create_dir_if_not_exists(SDT_COMPONENTS_GPP_DIR)
    except OSError as e:
        logger.critical(f"Failed to create output directories: {e}", exc_info=True)
        raise

    try:
        zielobjekte_data = read_csv_file(ZIELOBJEKTE_CSV_PATH)
        if not zielobjekte_data:
            raise FileNotFoundError(f"Zielobjekte data is empty or could not be loaded from {ZIELOBJEKTE_CSV_PATH}")
        zielobjekt_name_map = {row['UUID'].strip(): row['Zielobjekt'].strip() for row in zielobjekte_data if 'UUID' in row and 'Zielobjekt' in row}
    except (IOError, FileNotFoundError, TypeError, KeyError) as e:
        logger.critical(f"Failed to load or parse Zielobjekte CSV data: {e}", exc_info=True)
        raise

    try:
        baustein_zielobjekt_map = read_json_file(BAUSTEIN_ZIELOBJEKT_JSON_PATH)
        controls_anforderungen = read_json_file(CONTROLS_ANFORDERUNGEN_JSON_PATH)
        prozessbausteine_mapping = read_json_file(PROZZESSBAUSTEINE_CONTROLS_JSON_PATH)
        bsi_catalog = read_json_file(BSI_2023_JSON_PATH)
        gpp_catalog = read_json_file(GPP_KOMPENDIUM_JSON_PATH)

        # Check each loaded data file individually to provide a specific error message.
        data_to_check = {
            BAUSTEIN_ZIELOBJEKT_JSON_PATH: baustein_zielobjekt_map,
            CONTROLS_ANFORDERUNGEN_JSON_PATH: controls_anforderungen,
            PROZZESSBAUSTEINE_CONTROLS_JSON_PATH: prozessbausteine_mapping,
            BSI_2023_JSON_PATH: bsi_catalog,
            GPP_KOMPENDIUM_JSON_PATH: gpp_catalog,
        }
        for path, data in data_to_check.items():
            if not data:
                raise IOError(f"Data file loaded from '{path}' is empty or could not be loaded.")
    except (IOError, FileNotFoundError, Exception) as e:
        logger.critical(f"Failed to load critical data for component generation: {e}", exc_info=True)
        sys.exit(1)

    baustein_titles = {
        value['baustein_id']: value['zielobjekt_name']
        for value in controls_anforderungen.values() if 'baustein_id' in value and 'zielobjekt_name' in value
    }

    bsi_baustein_title_lookup = {}
    for group in bsi_catalog.get("catalog", {}).get("groups", []):
        for baustein in group.get("groups", []):
            if baustein.get("id") and baustein.get("title"):
                bsi_baustein_title_lookup[baustein["id"]] = baustein["title"]

    # Extract G++ controls once for efficiency
    logger.info("Extracting G++ controls for lookup...")
    gpp_controls_lookup = extract_all_gpp_controls(gpp_catalog)
    logger.info(f"Successfully extracted {len(gpp_controls_lookup)} G++ controls.")

    # Concurrency control
    sem = asyncio.Semaphore(app_config.max_concurrent_ai_requests)

    async def process_single_baustein(baustein_id, zielobjekt_uuid):
        async with sem:
            logger.info(f"Processing Baustein: {baustein_id}")

            zielobjekt_name = zielobjekt_name_map.get(zielobjekt_uuid)
            if not zielobjekt_name:
                logger.warning(f"No name found for Zielobjekt UUID {zielobjekt_uuid} (Baustein {baustein_id}). Skipping.")
                return

            baustein_title = baustein_titles.get(baustein_id) or bsi_baustein_title_lookup.get(baustein_id)
            if not baustein_title:
                logger.warning(f"No title found for Baustein ID {baustein_id}. Using Zielobjekt name as fallback.")
                baustein_title = zielobjekt_name

            sanitized_zielobjekt_name = sanitize_filename(zielobjekt_name)
            profile_filename = f"{sanitized_zielobjekt_name}_profile.json"
            profile_path = os.path.join(profile_dir, profile_filename)

            # mapping = controls_anforderungen.get(zielobjekt_uuid, {}).get("mapping", {}) # Unused

            await generate_detailed_component(baustein_id, baustein_title, zielobjekt_name, profile_path, bsi_catalog, gpp_controls_lookup, output_dir, ai_client)
            generate_minimal_component(baustein_id, baustein_title, zielobjekt_name, profile_path, output_dir)

    tasks = []
    for baustein_id, zielobjekt_uuid in baustein_zielobjekt_map.get("baustein_zielobjekt_map", {}).items():
        tasks.append(process_single_baustein(baustein_id, zielobjekt_uuid))

    # Add special ISMS Baustein to tasks
    async def process_isms_baustein():
        async with sem:
            logger.info("Processing special ISMS Baustein")
            isms_baustein_id = "ISMS"
            isms_baustein_title = "ISMS"
            isms_profile_path = os.path.join(profile_dir, "isms_profile.json")
            # isms_mapping = prozessbausteine_mapping.get("prozessbausteine_mapping", {}) # Unused
            await generate_detailed_component(isms_baustein_id, isms_baustein_title, "ISMS", isms_profile_path, bsi_catalog, gpp_controls_lookup, output_dir, ai_client)
            generate_minimal_component(isms_baustein_id, isms_baustein_title, "ISMS", isms_profile_path, output_dir)

    tasks.append(process_isms_baustein())

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

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
                        "source": get_source_url(profile_path),
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
    asyncio.run(run_stage_component())
