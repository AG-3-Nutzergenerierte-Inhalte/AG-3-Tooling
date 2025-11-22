#!/bin/bash
#
# run_local.sh
#
# Executes the OSCAL generation pipeline locally for development purposes.
#
# This script sets environment variables to simulate the Cloud Run environment
# and runs the main Python application. It enables TEST mode by default to
# prevent accidental execution against production resources and to provide
# verbose logging.
#
# Usage:
# ./scripts/run_local.sh [stage_name]
#
# Example:
# ./scripts/run_local.sh             # Runs the full pipeline
# ./scripts/run_local.sh stage_0
# ./scripts/run_local.sh stage_strip
#

# Change to the application's root directory (the parent of the scripts directory)
# This makes the script runnable from any location.
# BASH_SOURCE[0] is the path to the script itself.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR/.."

# --- Argument Parsing for --clear-all ---
if [[ " $@ " =~ " --clear-all " ]]; then
    echo "--- Clearing Generated Files (--clear-all) ---"

    # Define directories to be cleared
    # Note: Paths are relative to the project root where this script cd's into.
    declare -a DIRS_TO_CLEAR=(
        "../Stand-der-Technik-Bibliothek/Nutzergenerierte-Inhalte/hilfsdateien"
        "../Stand-der-Technik-Bibliothek/Nutzergenerierte-Inhalte/komponenten/DE"
        "../Stand-der-Technik-Bibliothek/Kompendien/Grundschutz++-Kompendium/profile"
        "../Stand-der-Technik-Bibliothek/Kompendien/Grundschutz++-Kompendium/komponenten"
    )

    for dir in "${DIRS_TO_CLEAR[@]}"; do
        if [ -d "$dir" ]; then
            echo "Clearing contents of '$dir/'..."
            # Delete all files inside the directory, but not the directory itself.
            # Use find to handle cases where the directory is empty.
            find "$dir" -type f -name "*.json" -delete
        else
            echo "Warning: Directory '$dir' not found. Skipping."
        fi
    done
    cp src/assets/json/prozessbausteine_mapping.json ../Stand-der-Technik-Bibliothek/Nutzergenerierte-Inhalte/hilfsdateien/
    echo "--- Finished Clearing Files ---"
fi

# --- Configuration ---
# Set the script to exit immediately if any command fails.
set -e

STAGE_INFO=${1:-"full pipeline"}
echo "--- Starting Local Pipeline Execution for: $STAGE_INFO ---"
echo "Working Directory: $(pwd)"

# --- Environment Setup ---
# Set environment variables for local run.
export GCP_PROJECT_ID="privates-476309"
export BUCKET_NAME="local-dev-bucket"
export AI_ENDPOINT_ID="local-dev-endpoint"
export SOURCE_PREFIX="input"
export OUTPUT_PREFIX="output"
export TEST="false"
export OVERWRITE_TEMP_FILES="true"

# Ensure that Python output is unbuffered, so logs appear immediately.
export PYTHONUNBUFFERED=1

echo "Environment Variables:"
echo "GCP_PROJECT_ID: $GCP_PROJECT_ID"
echo "BUCKET_NAME: $BUCKET_NAME"
echo "TEST: $TEST"
echo "---------------------------------------"

# --- Execution ---
# Run the main Python application from the application root.
# "$@" passes all command-line arguments from this script to the python script.
python3 src/main.py "$@"

echo "--- Local Pipeline Execution Finished ---"