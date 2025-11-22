"""
Manages the import of environment variables for the application.

This module retrieves configuration settings from the environment, providing
a single source of truth for all configurable parameters. It includes type
casting and default values to ensure robustness.
"""

import os
from typing import Optional


class AppConfig:
    """A dataclass-like container for application configuration."""

    def __init__(self):
        self.gcp_project_id: Optional[str] = os.environ.get("GCP_PROJECT_ID")
        self.bucket_name: Optional[str] = os.environ.get("BUCKET_NAME")
        self.ai_endpoint_id: Optional[str] = os.environ.get("AI_ENDPOINT_ID")
        self.region: Optional[str] = os.environ.get("REGION", "global")
        self.source_prefix: Optional[str] = os.environ.get("SOURCE_PREFIX")
        self.output_prefix: Optional[str] = os.environ.get("OUTPUT_PREFIX")
        self.is_test_mode: bool = os.environ.get("TEST", "false").lower() == "true"
        self.overwrite_temp_files: bool = (
            os.environ.get("OVERWRITE_TEMP_FILES", "false").lower() == "true"
        )
        self.max_concurrent_ai_requests: int = int(
            os.environ.get("MAX_CONCURRENT_AI_REQUESTS", "5")
        )

        if not self.is_test_mode:
            self._validate_production_config()

    def _validate_production_config(self):
        """Ensures all required variables are set in a non-test environment."""
        required_vars = {
            "GCP_PROJECT_ID": self.gcp_project_id,
            "BUCKET_NAME": self.bucket_name,
            "AI_ENDPOINT_ID": self.ai_endpoint_id,
            "SOURCE_PREFIX": self.source_prefix,
            "OUTPUT_PREFIX": self.output_prefix,
        }
        missing_vars = [key for key, value in required_vars.items() if value is None]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )


# Create a single, importable instance of the AppConfig.
app_config = AppConfig()
