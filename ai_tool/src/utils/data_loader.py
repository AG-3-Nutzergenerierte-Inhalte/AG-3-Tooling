"""
Utility functions for loading and parsing data from various file formats.

This module provides a centralized set of functions to handle the I/O and
initial parsing of the data sources required by the pipeline, such as CSV
and JSON files.
"""

import csv
import json
import logging
from functools import lru_cache
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def load_zielobjekte_csv(file_path: str) -> List[Dict[str, str]]:
    """
    Loads the Zielobjekte CSV file into a list of dictionaries.

    Args:
        file_path: The path to the CSV file.

    Returns:
        A list of dictionaries, where each dictionary represents a row.
    """
    logger.debug(f"Loading Zielobjekte from {file_path}...")
    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            data = [row for row in reader]
            logger.debug(f"Successfully loaded {len(data)} Zielobjekte.")
            return data
    except FileNotFoundError:
        logger.error(f"Error: The file at {file_path} was not found.")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading the CSV file: {e}")
        raise


@lru_cache(maxsize=None)
def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Loads a JSON file into a dictionary.

    Args:
        file_path: The path to the JSON file.

    Returns:
        A dictionary representing the JSON content.
    """
    logger.debug(f"Loading JSON data from {file_path}...")
    try:
        with open(file_path, mode="r", encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)
            logger.debug("Successfully loaded JSON data.")
            return data
    except FileNotFoundError:
        logger.error(f"Error: The file at {file_path} was not found.")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON from the file at {file_path}.")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading the JSON file: {e}")
        raise


import os

def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """
    Saves a dictionary to a JSON file.

    Args:
        data: The dictionary to save.
        file_path: The path to the output JSON file.
    """
    logger.debug(f"Saving JSON data to {file_path}...")
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug("Successfully saved JSON data.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while writing the JSON file: {e}")
        raise
