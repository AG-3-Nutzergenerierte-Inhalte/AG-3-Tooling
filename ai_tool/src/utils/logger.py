"""
Configures the application's logging based on the execution environment.

This module provides a centralized logging setup function that adheres to the
project's conditional logging requirements. It adjusts log levels for the
application and third-party libraries based on whether the application is in
"test" or "production" mode.
"""

import logging
import sys

from config import app_config
from constants import *


def setup_logging() -> None:
    """
    Initializes and configures the root logger for the application.

    This function sets the logging level and format for the root logger.
    In production mode (TEST=false), it also suppresses verbose output from
    noisy third-party libraries to ensure logs remain clean and focused on
    high-level status updates.
    """
    if app_config.is_test_mode:
        log_level = LOG_LEVEL_TEST
    else:
        log_level = LOG_LEVEL_PRODUCTION

    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        stream=sys.stdout  # Ensure logs go to stdout
    )

    # In production, reduce the noise from third-party libraries
    if not app_config.is_test_mode:
        noisy_libraries = ["google.auth", "urllib3"]
        for lib_name in noisy_libraries:
            logging.getLogger(lib_name).setLevel(
                THIRD_PARTY_LOG_LEVEL_PRODUCTION
            )

    logger = logging.getLogger(__name__)
    logger.debug("Logging configured for %s mode.", "test" if app_config.is_test_mode else "production")
