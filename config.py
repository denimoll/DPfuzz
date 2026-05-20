"""DPFuzz configuration.

Values are read from CONFIG first, then overridden by environment variables:

  DPFUZZ_URL                    → URL
  DPFUZZ_PATH_TO_EXAMPLES       → PATH_TO_EXAMPLES
  DPFUZZ_TOKEN                  → TOKEN
  DPFUZZ_AUTH_METHOD            → AUTH_METHOD
  DPFUZZ_MAX_IFACE_REQUEST_COUNT→ MAX_IFACE_REQUEST_COUNT
  DPFUZZ_MAX_ERROR_COUNT        → MAX_ERROR_COUNT
  DPFUZZ_MAX_TIME               → MAX_TIME
  DPFUZZ_ERRORS                 → ERRORS (comma-separated integers)
  DPFUZZ_SENSITIVE_DATA         → SENSITIVE_DATA (comma-separated strings)
  DPFUZZ_REPORT_FORMAT          → REPORT_FORMAT
  DPFUZZ_WORKERS                → WORKERS
  DPFUZZ_SSH_IP                 → SSH_IP
  DPFUZZ_SSH_USER               → SSH_USER
  DPFUZZ_SSH_PASSWORD           → SSH_PASSWORD
"""
import glob
import logging
import os

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

CONFIG = {
    # required parameters
    "URL": "",                  # http://domain or http://IP
    "PATH_TO_EXAMPLES": "",     # absolute path to dir with examples

    # authentication
    "TOKEN": "none",            # none or token value
    "AUTH_METHOD": "none",      # none or path to json-file with login:password request

    # fuzzing parameters
    "MAX_IFACE_REQUEST_COUNT": "default",   # default (=1) or integer value
    "MAX_ERROR_COUNT": "none",              # none or integer value
    "MAX_TIME": "none",                     # none or seconds as integer
    "ERRORS": [],                           # additional HTTP error codes to treat as errors
    "SENSITIVE_DATA": [],                   # keywords to detect in responses
    "WORKERS": 4,                           # parallel request threads

    # reporting
    "REPORT_FORMAT": "default",  # default (terminal only), txt, json, docx

    # SSH monitoring
    "SSH_IP": "",
    "SSH_USER": "root",
    "SSH_PASSWORD": "",
}

_ENV_MAP = {
    "DPFUZZ_URL":                     "URL",
    "DPFUZZ_PATH_TO_EXAMPLES":        "PATH_TO_EXAMPLES",
    "DPFUZZ_TOKEN":                   "TOKEN",
    "DPFUZZ_AUTH_METHOD":             "AUTH_METHOD",
    "DPFUZZ_MAX_IFACE_REQUEST_COUNT": "MAX_IFACE_REQUEST_COUNT",
    "DPFUZZ_MAX_ERROR_COUNT":         "MAX_ERROR_COUNT",
    "DPFUZZ_MAX_TIME":                "MAX_TIME",
    "DPFUZZ_REPORT_FORMAT":           "REPORT_FORMAT",
    "DPFUZZ_WORKERS":                 "WORKERS",
    "DPFUZZ_SSH_IP":                  "SSH_IP",
    "DPFUZZ_SSH_USER":                "SSH_USER",
    "DPFUZZ_SSH_PASSWORD":            "SSH_PASSWORD",
}


def _apply_env_overrides():
    for env_key, cfg_key in _ENV_MAP.items():
        value = os.environ.get(env_key)
        if value is not None:
            CONFIG[cfg_key] = value
    errors_env = os.environ.get("DPFUZZ_ERRORS")
    if errors_env:
        CONFIG["ERRORS"] = [v.strip() for v in errors_env.split(",") if v.strip()]
    sensitive_env = os.environ.get("DPFUZZ_SENSITIVE_DATA")
    if sensitive_env:
        CONFIG["SENSITIVE_DATA"] = [v.strip() for v in sensitive_env.split(",") if v.strip()]


_apply_env_overrides()


def url():
    return CONFIG.get("URL")


def examples():
    return CONFIG.get("PATH_TO_EXAMPLES")


def token():
    auth = CONFIG.get("AUTH_METHOD")
    if auth and auth != "none":
        return auth
    return CONFIG.get("TOKEN")


def max_iface_req_count():
    count = CONFIG.get("MAX_IFACE_REQUEST_COUNT")
    if str(count) == "default":
        return 1
    return int(count)


def max_error_count():
    value = CONFIG.get("MAX_ERROR_COUNT")
    if value == "none" or value is None:
        return 999 ** 99
    return int(value)


def max_time():
    value = CONFIG.get("MAX_TIME")
    if value == "none" or value is None:
        return 999 ** 99
    return int(value)


def errors():
    return CONFIG.get("ERRORS", [])


def sensitive_data():
    return CONFIG.get("SENSITIVE_DATA", [])


def report_format():
    return CONFIG.get("REPORT_FORMAT", "default")


def workers():
    return int(CONFIG.get("WORKERS", 4))


def ssh_ip():
    return CONFIG.get("SSH_IP")


def ssh_user():
    return CONFIG.get("SSH_USER")


def ssh_password():
    return CONFIG.get("SSH_PASSWORD")


def validate_config_parameters():
    """Validate all config parameters. Returns True on success, None on failure."""
    target_url = url()
    if not target_url:
        return _fail("URL parameter is empty")
    try:
        if requests.get(target_url, verify=False, timeout=10).status_code != 200:
            return _fail("URL is not reachable, check URL parameter")
    except Exception as e:
        return _fail("URL check failed: %s" % e)

    if not glob.glob(examples()):
        return _fail("PATH_TO_EXAMPLES path does not exist")

    auth = CONFIG.get("AUTH_METHOD")
    if auth and auth != "none":
        if not glob.glob(auth) or not auth.endswith(".json"):
            return _fail("AUTH_METHOD path is invalid or not a .json file")

    count = CONFIG.get("MAX_IFACE_REQUEST_COUNT")
    if count != "default":
        if not isinstance(count, int) or count < 1:
            return _fail("MAX_IFACE_REQUEST_COUNT must be 'default' or a positive integer")

    if CONFIG.get("MAX_ERROR_COUNT") != "none":
        if max_error_count() < 1:
            return _fail("MAX_ERROR_COUNT must be 'none' or a positive integer")

    if CONFIG.get("MAX_TIME") != "none":
        if max_time() < 1:
            return _fail("MAX_TIME must be 'none' or a positive integer")

    if not isinstance(errors(), list):
        return _fail("ERRORS must be a list")

    if not isinstance(sensitive_data(), list):
        return _fail("SENSITIVE_DATA must be a list")

    if report_format() not in ("default", "txt", "json", "docx"):
        return _fail("REPORT_FORMAT must be one of: default, txt, json, docx")

    if workers() < 1:
        return _fail("WORKERS must be a positive integer")

    return True


def _fail(message):
    logger.error("Config error: %s", message)
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    validate_config_parameters()
