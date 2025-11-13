"""
OSCAL Validation Utilities

This module provides helper functions for working with OSCAL files, primarily
for validating them against their corresponding JSON schemas.
"""

import logging
from jsonschema import validate, ValidationError

from utils.file_utils import read_json_file

logger = logging.getLogger(__name__)

def validate_oscal(json_path: str, schema_path: str) -> bool:
    """
    Validates a JSON file against a given JSON schema.

    Args:
        json_path (str): The path to the JSON file to validate.
        schema_path (str): The path to the JSON schema file.

    Returns:
        bool: True if validation is successful, False otherwise.
    """
    schema = read_json_file(schema_path)
    if not schema:
        logger.error(f"Could not load schema from {schema_path}")
        return False

    instance = read_json_file(json_path)
    if not instance:
        logger.error(f"Could not load JSON instance from {json_path}")
        return False

    try:
        validate(instance=instance, schema=schema)
        logger.info(f"Successfully validated {json_path} against {schema_path}")
        return True
    except ValidationError as e:
        logger.error(f"Validation failed for {json_path}: {e.message} on instance {e.instance}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during validation of {json_path}: {e}")
        return False
