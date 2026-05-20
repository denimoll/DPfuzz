"""Merge multiple example JSON files for a method into a single combined file."""
import glob
import json
import os


def _recurs_merge(base, override):
    """Recursively merge override into base, returning merged dict."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _recurs_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def create_common_json(path):
    """
    Merge all *.json files in `path` into merge.json.
    Skips if fewer than 2 source files exist.
    """
    merge_path = os.path.join(path, "merge.json")
    try:
        os.remove(merge_path)
    except OSError:
        pass

    files = [f for f in glob.glob(os.path.join(path, "*.json")) if f != merge_path]
    if len(files) < 2:
        return False

    with open(files[0], encoding="utf-8") as f:
        first = json.load(f)

    main_info = {
        "jsonrpc": first.get("jsonrpc"),
        "method": first.get("method"),
        "auth": first.get("auth"),
        "id": first.get("id"),
    }
    merged_params = first.get("params")

    for file in files[1:]:
        with open(file, encoding="utf-8") as f:
            content = json.load(f)
        params = content.get("params")
        if not isinstance(params, list) and not isinstance(merged_params, list):
            merged_params = _recurs_merge(merged_params or {}, params or {})

    result = dict(main_info)
    result["params"] = merged_params
    with open(merge_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    return True


def create_common_jsons(path):
    """Create merge.json for every method directory under `path`."""
    for method in os.listdir(path):
        method_path = os.path.join(path, method)
        if os.path.isdir(method_path):
            create_common_json(method_path)
