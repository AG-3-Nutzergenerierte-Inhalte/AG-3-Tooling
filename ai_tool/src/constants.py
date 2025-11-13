"""
Defines application-wide constants.

This module centralizes all static, non-configurable values used across the
application. This improves maintainability by providing a single, authoritative
source for these constants.
"""

import os
import re

# --- Path Configuration ---
# All paths are resolved as absolute paths to ensure the application runs
# correctly regardless of the current working directory.
SRC_ROOT = os.path.dirname(os.path.abspath(__file__))
# REPO_ROOT is the parent directory of the 'ai_tool' project folder.
REPO_ROOT = os.path.abspath(os.path.join(SRC_ROOT, "..", ".."))

ANFORDERUNG_ID_PATTERN = re.compile(r"^[A-Z]{2,}(\.\d{1,2}){1,3}(\.A\d{1,2})?$")

# --- Data File Paths ---
ZIELOBJEKTE_CSV_PATH = os.path.join(REPO_ROOT, "Stand-der-Technik-Bibliothek/Dokumentation/namespaces/zielobjekte.csv")
BSI_2023_JSON_PATH = os.path.join(REPO_ROOT, "BSI-GS-Benutzerdefinierte-Edition23-OSCAL/BS_GK_OSCAL_JSON_DATA/BSI_GS_OSCAL_current_2023_benutzerdefinierte.json")
GPP_KOMPENDIUM_JSON_PATH = os.path.join(REPO_ROOT, "Stand-der-Technik-Bibliothek/Kompendien/Grundschutz++-Kompendium/Grundschutz++-Kompendium.json")

# --- Filtering ---
ALLOWED_MAIN_GROUPS = ["SYS", "INF", "IND", "APP", "NET"]

# --- Output to Stand der Technik Submodule File Paths ---
SDT_OUTPUT_DIR = os.path.join(REPO_ROOT, "Stand-der-Technik-Bibliothek/Zielobjekt-Bausteine")
SDT_HELPER_OUTPUT_DIR = os.path.join(SDT_OUTPUT_DIR, "hilfsdateien")
BAUSTEINE_ZIELOBJEKTE_JSON_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "bausteine_zielobjekt.json")
CONTROLS_ANFORDERUNGEN_JSON_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "controls_anforderungen.json")
ZIELOBJEKT_CONTROLS_JSON_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "zielobjekt_controls.json")
PROZZESSBAUSTEINE_CONTROLS_JSON_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "prozessbausteine_mapping.json")

# Paths for the 'stage_strip' output files

GPP_STRIPPED_MD_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "gpp_stripped.md")
GPP_STRIPPED_ISMS_MD_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "gpp_isms_stripped.md")
BSI_STRIPPED_MD_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "bsi_2023_stripped.md")
BSI_STRIPPED_ISMS_MD_PATH = os.path.join(SDT_HELPER_OUTPUT_DIR, "bsi_2023_stripped_ISMS.md")


# --- Asset Paths ---
PROMPT_CONFIG_PATH = os.path.join(SRC_ROOT, "assets/json/prompt_config.json")
BAUSTEIN_TO_ZIELOBJEKT_SCHEMA_PATH = os.path.join(SRC_ROOT, "assets/schemas/baustein_to_zielobjekt_schema.json")
ANFORDERUNG_TO_KONTROLLE_SCHEMA_PATH = os.path.join(SRC_ROOT, "assets/schemas/anforderung_to_kontrolle_schema.json")
MATCHING_SCHEMA_PATH = os.path.join(SRC_ROOT, "assets/schemas/matching_schema.json")

# --- AI Model Configuration ---
GROUND_TRUTH_MODEL = "gemini-2.5-flash"
GROUND_TRUTH_MODEL_PRO = "gemini-2.5-pro"

# --- API Configuration ---
# Constants for external API interactions, such as retry logic parameters.
API_MAX_RETRIES = 5
API_RETRY_BACKOFF_FACTOR = 2
API_RETRY_JITTER = 0.5  # 50% jitter
API_TEMPERATURE = 0.2
API_MAX_OUTPUT_TOKEN = 65536

# --- Logging ---
LOG_LEVEL_TEST = "DEBUG"
LOG_LEVEL_PRODUCTION = "INFO"
THIRD_PARTY_LOG_LEVEL_PRODUCTION = "WARNING"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# --- OSCAL Metadata ---
# Default values and namespaces for OSCAL artifact generation.
OSCAL_VERSION = "1.1.3"
OSCAL_NAMESPACE = "http://csrc.nist.gov/ns/oscal/1.0"
