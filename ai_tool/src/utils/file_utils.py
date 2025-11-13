"""
File Utilities

This module provides utility functions for file and directory operations,
such as creating directories and reading/writing JSON and CSV files.
"""

import os
import json
import csv
import logging

logger = logging.getLogger(__name__)

def create_dir_if_not_exists(directory_path):
    """
    Creates a directory if it does not already exist.

    Args:
        directory_path (str): The path to the directory.
    """
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logger.info(f"Directory created: {directory_path}")
        except OSError as e:
            logger.error(f"Error creating directory {directory_path}: {e}")

def read_json_file(file_path):
    """
    Reads a JSON file and returns its content.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The content of the JSON file, or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {file_path}")
        return None

def write_json_file(file_path, data):
    """
    Writes data to a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        data (dict): The data to write to the file.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Successfully wrote to {file_path}")
    except IOError as e:
        logger.error(f"Error writing to file {file_path}: {e}")

def read_csv_file(file_path):
    """
    Reads a CSV file and returns its content as a list of dictionaries.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list: A list of dictionaries representing the rows of the CSV file,
              or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        return None
