"""Tests for create_jsons_for_generation module."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import create_jsons_for_generation


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def read_json(path):
    with open(path) as f:
        return json.load(f)


class TestRecursUpdateKey:
    def test_scalar_replaced(self):
        assert create_jsons_for_generation._recurs_update_key(42) == "fuzzint"

    def test_string_replaced(self):
        assert create_jsons_for_generation._recurs_update_key("hello") == "fuzzstr"

    def test_bool_replaced(self):
        assert create_jsons_for_generation._recurs_update_key(True) == "fuzzbool"

    def test_float_replaced(self):
        assert create_jsons_for_generation._recurs_update_key(3.14) == "fuzzfloat"

    def test_dict_recursed(self):
        result = create_jsons_for_generation._recurs_update_key({"a": 1, "b": "x"})
        assert result == {"a": "fuzzint", "b": "fuzzstr"}

    def test_list_recursed(self):
        result = create_jsons_for_generation._recurs_update_key([1, "s", True])
        assert result == ["fuzzint", "fuzzstr", "fuzzbool"]

    def test_nested(self):
        result = create_jsons_for_generation._recurs_update_key({"params": {"x": 1, "tags": ["a", "b"]}})
        assert result["params"]["x"] == "fuzzint"
        assert result["params"]["tags"] == ["fuzzstr", "fuzzstr"]


class TestCreateJsonForGeneration:
    def test_uses_merge_json(self, tmp_path):
        write_json(tmp_path / "merge.json", {
            "jsonrpc": "2.0", "method": "m", "auth": None, "id": 1,
            "params": {"limit": 100, "active": True}
        })
        create_jsons_for_generation.create_json_for_generation(str(tmp_path))
        result = read_json(tmp_path / "for_generation.json")
        assert result["params"]["limit"] == "fuzzint"
        assert result["params"]["active"] == "fuzzbool"

    def test_fallback_to_0_json(self, tmp_path):
        write_json(tmp_path / "0.json", {
            "jsonrpc": "2.0", "method": "m", "auth": None, "id": 1,
            "params": {"name": "test"}
        })
        create_jsons_for_generation.create_json_for_generation(str(tmp_path))
        result = read_json(tmp_path / "for_generation.json")
        assert result["params"]["name"] == "fuzzstr"

    def test_returns_false_when_no_source(self, tmp_path):
        result = create_jsons_for_generation.create_json_for_generation(str(tmp_path))
        assert result is False
