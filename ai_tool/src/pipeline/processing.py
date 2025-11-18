"""
Core data processing logic for the OSCAL generation pipeline.

This module contains the orchestrator function for running the entire pipeline
from start to finish, executing each stage in the correct sequence.
"""

import logging
from pipeline import (
    stage_strip,
    stage_gpp,
    stage_match_bausteine,
    stage_decomposition,
    stage_matching,
    stage_metadata_generation,
    stage_profiles,
    stage_component,
)

logger = logging.getLogger(__name__)


async def run_full_pipeline() -> None:
    """
    Executes the entire data processing and OSCAL generation pipeline.

    This function orchestrates the full, end-to-end pipeline, running each
    stage in the required order to ensure data dependencies are met.
    """
    logger.info("--- Starting Full Pipeline Execution ---")

    try:
        logger.info("--- STAGE: STRIP ---")
        stage_strip.run_stage_strip()
        logger.info("--- STAGE: STRIP - COMPLETE ---")

        logger.info("--- STAGE: GPP ---")
        stage_gpp.run_stage_gpp()
        logger.info("--- STAGE: GPP - COMPLETE ---")

        logger.info("--- STAGE: MATCH BAUSTEINE ---")
        await stage_match_bausteine.run_stage_match_bausteine()
        logger.info("--- STAGE: MATCH BAUSTEINE - COMPLETE ---")

        logger.info("--- STAGE: DECOMPOSITION ---")
        await stage_decomposition.run_stage_decomposition()
        logger.info("--- STAGE: DECOMPOSITION - COMPLETE ---")

        logger.info("--- STAGE: MATCHING ---")
        await stage_matching.run_stage_matching()
        logger.info("--- STAGE: MATCHING - COMPLETE ---")

        logger.info("--- STAGE: METADATA GENERATION ---")
        await stage_metadata_generation.run_stage_metadata_generation()
        logger.info("--- STAGE: METADATA GENERATION - COMPLETE ---")

        logger.info("--- STAGE: PROFILES ---")
        stage_profiles.run_stage_profiles()
        logger.info("--- STAGE: PROFILES - COMPLETE ---")

        logger.info("--- STAGE: COMPONENTS ---")
        stage_component.run_stage_component()
        logger.info("--- STAGE: COMPONENTS - COMPLETE ---")

    except Exception as e:
        logger.critical("A critical error occurred during the full pipeline execution.", exc_info=True)
        raise

    logger.info("--- Full Pipeline Execution Finished Successfully ---")