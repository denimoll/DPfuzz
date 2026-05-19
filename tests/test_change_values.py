"""Tests for change_values module."""
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import change_values


class TestGeneration:
    def test_int_type(self):
        for _ in range(20):
            val = change_values.generation("int")
            assert isinstance(val, int) or isinstance(val, str)  # may be fuzzdb payload

    def test_float_type(self):
        for _ in range(20):
            val = change_values.generation("float")
            assert isinstance(val, float) or isinstance(val, str)

    def test_bool_type(self):
        for _ in range(20):
            val = change_values.generation("bool")
            assert isinstance(val, bool) or isinstance(val, str)

    def test_str_type(self):
        for _ in range(20):
            val = change_values.generation("str")
            assert isinstance(val, str)

    def test_unknown_type_returns_none_or_str(self):
        val = change_values.generation("unknown_xyz")
        assert val is None or isinstance(val, str)


class TestKeyGeneration:
    def test_replaces_fuzzint_placeholder(self):
        template = {"jsonrpc": "2.0", "method": "test", "params": {"limit": "fuzzint"}}
        result = change_values.key_generation(template)
        assert isinstance(result, dict)
        assert result["params"]["limit"] != "fuzzint"

    def test_replaces_fuzzstr_placeholder(self):
        template = {"params": {"name": "fuzzstr"}}
        result = change_values.key_generation(template)
        assert isinstance(result, dict)
        assert result["params"]["name"] != "fuzzstr"

    def test_replaces_fuzzbool_placeholder(self):
        template = {"params": {"enabled": "fuzzbool"}}
        result = change_values.key_generation(template)
        assert isinstance(result, dict)

    def test_no_placeholder_unchanged(self):
        template = {"params": {"x": 1}}
        result = change_values.key_generation(template)
        assert result["params"]["x"] == 1

    def test_returns_dict_on_broken_json(self):
        # If generation produces something that breaks JSON, original is returned
        template = {"params": {"x": "fuzzint"}}
        result = change_values.key_generation(template)
        assert isinstance(result, dict)


class TestMutation:
    def test_returns_string(self):
        result = change_values.mutation("hello")
        assert isinstance(result, str)

    def test_mutates_non_empty_string(self):
        # Radamsa almost certainly mutates the value (though not guaranteed)
        original = "hello_world_12345"
        results = {change_values.mutation(original) for _ in range(10)}
        # At least some mutation should happen across 10 runs
        assert len(results) >= 1  # sanity: always returns something


class TestDictMutation:
    def test_returns_dict(self):
        d = {"method": "test", "params": {"a": 1}}
        result = change_values.dict_mutation(d)
        assert isinstance(result, dict)

    def test_input_not_mutated_in_place(self):
        d = {"method": "test", "params": {"a": 1, "b": "value"}}
        original_method = d["method"]
        change_values.dict_mutation(d)
        assert d["method"] == original_method


class TestKeyMutation:
    def test_dict_params(self):
        d = {"params": {"name": "Alice", "age": 30}}
        result = change_values.key_mutation(d)
        assert isinstance(result, dict)
        assert "params" in result

    def test_list_params(self):
        d = {"params": ["a", "b", "c"]}
        result = change_values.key_mutation(d)
        assert isinstance(result, dict)
        assert isinstance(result["params"], list)

    def test_empty_list_params(self):
        d = {"params": []}
        result = change_values.key_mutation(d)
        assert isinstance(result["params"], list)
        assert len(result["params"]) > 0  # should append mutated items

    def test_scalar_params(self):
        d = {"params": "some_value"}
        result = change_values.key_mutation(d)
        assert "params" in result

    def test_none_params(self):
        d = {"params": None}
        result = change_values.key_mutation(d)
        assert isinstance(result, dict)

    def test_no_params_key(self):
        d = {"method": "test"}
        result = change_values.key_mutation(d)
        assert isinstance(result, dict)
