"""Tests for create_common_jsons module."""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import create_common_jsons


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def read_json(path):
    with open(path) as f:
        return json.load(f)


class TestCreateCommonJson:
    def test_skips_when_fewer_than_two_files(self, tmp_path):
        write_json(tmp_path / "0.json", {"params": {"a": 1}})
        result = create_common_jsons.create_common_json(str(tmp_path))
        assert result is False
        assert not (tmp_path / "merge.json").exists()

    def test_merges_two_files(self, tmp_path):
        write_json(tmp_path / "0.json", {
            "jsonrpc": "2.0", "method": "test", "auth": None, "id": 1,
            "params": {"a": 1}
        })
        write_json(tmp_path / "1.json", {
            "jsonrpc": "2.0", "method": "test", "auth": None, "id": 1,
            "params": {"b": 2}
        })
        result = create_common_jsons.create_common_json(str(tmp_path))
        assert result is True
        merged = read_json(tmp_path / "merge.json")
        assert "a" in merged["params"]
        assert "b" in merged["params"]

    def test_existing_merge_removed_and_recreated(self, tmp_path):
        write_json(tmp_path / "0.json", {"jsonrpc": "2.0", "method": "m", "auth": None, "id": 1, "params": {"x": 10}})
        write_json(tmp_path / "1.json", {"jsonrpc": "2.0", "method": "m", "auth": None, "id": 1, "params": {"y": 20}})
        write_json(tmp_path / "merge.json", {"stale": True})
        create_common_jsons.create_common_json(str(tmp_path))
        merged = read_json(tmp_path / "merge.json")
        assert "stale" not in merged

    def test_list_params_not_merged(self, tmp_path):
        write_json(tmp_path / "0.json", {"jsonrpc": "2.0", "method": "m", "auth": None, "id": 1, "params": [1, 2]})
        write_json(tmp_path / "1.json", {"jsonrpc": "2.0", "method": "m", "auth": None, "id": 1, "params": [3, 4]})
        result = create_common_jsons.create_common_json(str(tmp_path))
        assert result is True
        merged = read_json(tmp_path / "merge.json")
        assert isinstance(merged["params"], list)


class TestCreateCommonJsons:
    def test_processes_all_subdirs(self, tmp_path):
        for method in ("user_get", "host_create"):
            d = tmp_path / method
            d.mkdir()
            write_json(d / "0.json", {"jsonrpc": "2.0", "method": method, "auth": None, "id": 1, "params": {"a": 1}})
            write_json(d / "1.json", {"jsonrpc": "2.0", "method": method, "auth": None, "id": 1, "params": {"b": 2}})
        create_common_jsons.create_common_jsons(str(tmp_path))
        for method in ("user_get", "host_create"):
            assert (tmp_path / method / "merge.json").exists()
