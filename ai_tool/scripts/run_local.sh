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
# ./scripts/run_local.sh <stage_name>
#
# Example:
# ./scripts/run_local.sh stage_0
# ./scripts/run_local.sh stage_strip
#

# --- Configuration ---
# Set the script to exit immediately if any command fails.
set -e

# Check if a stage name was provided.
if [ -z "$1" ]; then
    echo "Error: No stage name provided."
    echo "Usage: $0 <stage_name>"
    echo "Available stages: stage_0, stage_strip, stage_matching"
    exit 1
fi

STAGE_NAME=$1

# Change to the application's root directory (the parent of the scripts directory)
# This makes the script runnable from any location.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR/.."

echo "--- Starting Local Pipeline Execution for Stage: $STAGE_NAME ---"
echo "Working Directory: $(pwd)"

# --- Environment Setup ---
# Set environment variables for local run.
export GCP_PROJECT_ID="privates-476309"
export BUCKET_NAME="local-dev-bucket"
export AI_ENDPOINT_ID="local-dev-endpoint"
export SOURCE_PREFIX="input"
export OUTPUT_PREFIX="output"
export TEST="true"
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
python3 src/main.py --stage "$STAGE_NAME"

echo "--- Local Pipeline Execution Finished ---"
