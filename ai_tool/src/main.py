"""
Main entry point for the OSCAL generation pipeline.

This script initializes the application's configuration and logging, then
starts the main processing pipeline. It is designed to be executed as the
entry point for the GCP Cloud Run job.
"""

import logging
import asyncio
import argparse

from pipeline import stage_0, stage_strip, stage_matching
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
        required=True,
        choices=["stage_0", "stage_strip", "stage_matching"],
        help="The pipeline stage to execute.",
    )
    args = parser.parse_args()


    logger.debug(f"Starting OSCAL generation pipeline for stage: {args.stage}...")

    if args.stage == "stage_0":
        await stage_0.run_phase_0()
    elif args.stage == "stage_strip":
        stage_strip.run_stage_strip()
    elif args.stage == "stage_matching":
        await stage_matching.run_stage_matching()
    else:
        logger.error(f"Unknown stage: {args.stage}")


    logger.debug("OSCAL generation pipeline finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
