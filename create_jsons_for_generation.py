"""Create for_generation.json files that use 'fuzz<type>' placeholders."""
import glob
import json
import os


def _recurs_update_key(value):
    """Replace leaf values with 'fuzz<type>' placeholders."""
    if isinstance(value, dict):
        return {k: _recurs_update_key(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recurs_update_key(v) for v in value]
    return "fuzz%s" % type(value).__name__


def create_json_for_generation(path):
    """
    Create for_generation.json in `path` based on merge.json (or 0.json as fallback).
    """
    candidates = glob.glob(os.path.join(path, "merge.json")) or glob.glob(os.path.join(path, "0.json"))
    if not candidates:
        return False
    with open(candidates[0], encoding="utf-8") as f:
        data = json.load(f)
    data["params"] = _recurs_update_key(data.get("params"))
    with open(os.path.join(path, "for_generation.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return True


def create_jsons_for_generation(path):
    """Create for_generation.json for every method directory under `path`."""
    for method in os.listdir(path):
        method_path = os.path.join(path, method)
        if os.path.isdir(method_path):
            create_json_for_generation(method_path)
