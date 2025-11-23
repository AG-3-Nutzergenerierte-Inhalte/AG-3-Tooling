"""
Core data processing logic for the OSCAL generation pipeline.

This module contains the orchestrator function for running the entire pipeline
from start to finish, executing each stage in the correct sequence.
"""

import logging
from pipeline import stage_strip, stage_gpp, stage_match_bausteine, stage_matching, stage_profiles, stage_component

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
        stage_strip.run_stage_strip()
        logger.info("--- STAGE: STRIP - COMPLETE ---")

        # Stage 2: Perform high-level Baustein-to-Zielobjekt mapping.
        # Stage 2.1: Process G++ Kompendium and create deterministic mappings.
        logger.info("--- STAGE: GPP ---")
        stage_gpp.run_stage_gpp()
        logger.info("--- STAGE: GPP - COMPLETE ---")

        # Stage 2.2: Perform high-level Baustein-to-Zielobjekt mapping.
        logger.info("--- STAGE: MATCH BAUSTEINE ---")
        await stage_match_bausteine.run_stage_match_bausteine()
        logger.info("--- STAGE: MATCH BAUSTEINE - COMPLETE ---")

        # Stage 3: Perform detailed Anforderung-to-Kontrolle mapping.
        logger.info("--- STAGE: MATCHING ---")
        await stage_matching.run_stage_matching()
        logger.info("--- STAGE: MATCHING - COMPLETE ---")

        # Stage 4: Generate OSCAL profiles for each Zielobjekt.
        logger.info("--- STAGE: PROFILES ---")
        stage_profiles.run_stage_profiles()
        logger.info("--- STAGE: PROFILES - COMPLETE ---")

        # Stage 5: Generate OSCAL components  for each Zielobjekt.
        logger.info("--- STAGE: COMPONENTS ---")
        logger.info("Starting: Generating OSCAL components.")
        await stage_component.run_stage_component()
        logger.info("--- STAGE: COMPONENTS - COMPLETE ---")



    except Exception as e:
        logger.critical("A critical error occurred during the full pipeline execution.", exc_info=True)
        # Re-raise the exception to ensure the script exits with a non-zero status code.
        raise
    
    logger.info("--- Full Pipeline Execution Finished Successfully ---")