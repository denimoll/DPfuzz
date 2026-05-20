"""Analyse HTTP responses from the fuzzed API."""
import json
import logging

import simplejson

import config

logger = logging.getLogger(__name__)

_JSONRPC_ERROR_RANGE = range(-32768, -31999)  # JSON-RPC reserved error codes


def check_response(req, response):
    """
    Classify an HTTP response.

    Returns (status, error_dict) where status is one of:
      'auth_problem', 'forbidden', 'json_error', 'error', None
    """
    errors = {500} | {int(e) for e in config.errors() if str(e).isdigit()}
    sensitive = {"select"} | {str(s).lower() for s in config.sensitive_data()}

    code = response.status_code
    try:
        content = str(response.json())
    except (json.decoder.JSONDecodeError, simplejson.errors.JSONDecodeError):
        content = str(response.content)
    content_lower = content.lower()

    if code == 403 or "not authorised" in content_lower or "re-login" in content_lower:
        return "auth_problem", None

    for word in ("no permissions", "forbidden", "no rule", "no access", "no rights"):
        if word in content_lower:
            return "forbidden", None

    try:
        json_error = response.json().get("error")
        if json_error is not None:
            json_code = json_error.get("code")
            if isinstance(json_code, int) and json_code in _JSONRPC_ERROR_RANGE:
                return "json_error", None
            logger.warning("Request: %s\nResponse %s: %s", req, code, content)
            return "error", {
                "reason": "Unknown JSON-RPC error code",
                "request": req,
                "response_code": code,
                "response_data": content,
            }
    except Exception:
        pass

    if code in errors:
        logger.warning("Request: %s\nResponse %s: %s", req, code, content)
        return "error", {
            "reason": "HTTP error code",
            "request": req,
            "response_code": code,
            "response_data": content,
        }

    for keyword in sensitive:
        if keyword in content_lower:
            logger.warning("Request: %s\nResponse %s: %s", req, code, content)
            return "error", {
                "reason": "Response contains sensitive keyword: %s" % keyword,
                "request": req,
                "response_code": code,
                "response_data": content,
            }

    return None, None
