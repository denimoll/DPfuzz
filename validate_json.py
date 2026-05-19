"""JSON validation utilities."""
import json


def validate_json(file_obj):
    """
    Validate that file_obj contains valid JSON.
    Returns True on success, or the exception on failure.
    """
    try:
        json.load(file_obj)
        return True
    except Exception as e:
        return e
