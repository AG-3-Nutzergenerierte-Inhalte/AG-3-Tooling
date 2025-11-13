"""
Text Utilities

This module provides utility functions for text manipulation, such as sanitizing strings for use in filenames.
"""

import re

def sanitize_filename(filename):
    """
    Sanitizes a string to be used as a filename.

    Args:
        filename (str): The string to sanitize.

    Returns:
        str: The sanitized filename.
    """
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove special characters
    filename = re.sub(r'[^a-zA-Z0-9_-]', '', filename)
    # Convert to lowercase
    filename = filename.lower()
    return filename
