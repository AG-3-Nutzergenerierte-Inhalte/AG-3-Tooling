"""
Main entry point for the OSCAL generation pipeline.

This script initializes the application's configuration and logging, then
starts the main processing pipeline. It is designed to be executed as the
entry point for the GCP Cloud Run job.
"""

import logging
import asyncio
import argparse

from pipeline import stage_strip, stage_gpp, stage_match_bausteine, stage_matching, stage_profiles, stage_component, processing
from utils.logger import setup_logging


async def main() -> None:
    """
    Orchestrates the OSCAL generation pipeline.

    This function executes the main steps of the pipeline based on the
    provided command-line arguments.
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="OSCAL Generation Pipeline")
    parser.add_argument(
        "--stage",
        type=str,
        required=False,
        choices=["stage_gpp", "stage_match_bausteine", "stage_strip", "stage_matching", "stage_profiles", "stage_component"],
        help="The pipeline stage to execute. If not provided, the full pipeline will run.",
    )
    args = parser.parse_args()


    if args.stage:
        logger.info(f"Starting OSCAL generation pipeline for stage: {args.stage}...")
        if args.stage == "stage_gpp":
            stage_gpp.run_stage_gpp()
        elif args.stage == "stage_match_bausteine":
            await stage_match_bausteine.run_stage_match_bausteine()
        elif args.stage == "stage_strip":
            stage_strip.run_stage_strip()
        elif args.stage == "stage_matching":
            await stage_matching.run_stage_matching()
        elif args.stage == "stage_profiles":
            stage_profiles.run_stage_profiles()
        elif args.stage == "stage_component":
            await stage_component.run_stage_component()
    else:
        logger.info("No stage specified. Starting full pipeline execution...")
        await processing.run_full_pipeline()


    logger.debug("OSCAL generation pipeline finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())