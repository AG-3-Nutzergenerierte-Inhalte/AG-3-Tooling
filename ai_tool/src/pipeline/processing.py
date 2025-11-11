"""
Core data processing logic for the OSCAL generation pipeline.

This module contains the orchestrator function for running the entire pipeline
from start to finish, executing each stage in the correct sequence.
"""

import logging
from pipeline import stage_0, stage_strip, stage_matching

logger = logging.getLogger(__name__)


async def run_full_pipeline() -> None:
    """
    Executes the entire data processing and OSCAL generation pipeline.

    This function orchestrates the full, end-to-end pipeline, running each
    stage in the required order to ensure data dependencies are met.
    """
    logger.info("--- Starting Full Pipeline Execution ---")

    try:
        # Stage 1: Strip source files into markdown for AI context.
        logger.info("--- STAGE: STRIP ---")
        logger.info("Starting: Pre-processing and stripping source files.")
        stage_strip.run_stage_strip()
        logger.info("Completed: Pre-processing and stripping source files.")
        logger.info("--- STAGE: STRIP - COMPLETE ---")

        # Stage 2: Perform high-level Baustein-to-Zielobjekt mapping.
        logger.info("--- STAGE: 0 ---")
        logger.info("Starting: Baustein to Zielobjekt mapping.")
        await stage_0.run_phase_0()
        logger.info("Completed: Baustein to Zielobjekt mapping.")
        logger.info("--- STAGE: 0 - COMPLETE ---")

        # Stage 3: Perform detailed Anforderung-to-Kontrolle mapping.
        logger.info("--- STAGE: MATCHING ---")
        logger.info("Starting: Anforderung to Kontrolle 1:1 mapping.")
        await stage_matching.run_stage_matching()
        logger.info("Completed: Anforderung to Kontrolle 1:1 mapping.")
        logger.info("--- STAGE: MATCHING - COMPLETE ---")

    except Exception as e:
        logger.critical("A critical error occurred during the full pipeline execution.", exc_info=True)
        # Re-raise the exception to ensure the script exits with a non-zero status code.
        raise
    
    logger.info("--- Full Pipeline Execution Finished Successfully ---")