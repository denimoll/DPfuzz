"""Tests for validate_json module."""
import io
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import validate_json


class TestValidateJson:
    def test_valid_json_returns_true(self):
        f = io.StringIO('{"key": "value"}')
        assert validate_json.validate_json(f) is True

    def test_valid_json_array(self):
        f = io.StringIO('[1, 2, 3]')
        assert validate_json.validate_json(f) is True

    def test_invalid_json_returns_exception(self):
        f = io.StringIO('{bad json}')
        result = validate_json.validate_json(f)
        assert result is not True
        assert isinstance(result, Exception)

    def test_empty_content_returns_exception(self):
        f = io.StringIO('')
        result = validate_json.validate_json(f)
        assert result is not True

    def test_nested_json_valid(self):
        f = io.StringIO('{"a": {"b": [1, 2, {"c": true}]}}')
        assert validate_json.validate_json(f) is True
