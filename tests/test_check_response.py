"""Tests for check_response module."""
import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_response(status_code=200, json_data=None, content=b""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        import simplejson
        resp.json.side_effect = simplejson.errors.JSONDecodeError("err", "doc", 0)
    return resp


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    import config
    monkeypatch.setattr(config, "errors", lambda: [])
    monkeypatch.setattr(config, "sensitive_data", lambda: [])


def import_check_response():
    import check_response
    return check_response


class TestAuthProblem:
    def test_403_status(self):
        cr = import_check_response()
        resp = _make_response(403, {"result": "ok"})
        status, error = cr.check_response({}, resp)
        assert status == "auth_problem"
        assert error is None

    def test_not_authorised_in_body(self):
        cr = import_check_response()
        resp = _make_response(200, {"error": {"message": "Not authorised"}})
        status, _ = cr.check_response({}, resp)
        assert status == "auth_problem"

    def test_relogin_in_body(self):
        cr = import_check_response()
        resp = _make_response(200, {"error": {"message": "Please re-login"}})
        status, _ = cr.check_response({}, resp)
        assert status == "auth_problem"


class TestForbidden:
    def test_no_permissions(self):
        cr = import_check_response()
        resp = _make_response(200, {"error": {"message": "No permissions to referred object"}})
        status, _ = cr.check_response({}, resp)
        assert status == "forbidden"

    def test_no_rights(self):
        cr = import_check_response()
        resp = _make_response(200, {"result": "no rights here"})
        status, _ = cr.check_response({}, resp)
        assert status == "forbidden"


class TestJsonError:
    def test_jsonrpc_reserved_error_code(self):
        cr = import_check_response()
        resp = _make_response(200, {"error": {"code": -32700, "message": "Parse error"}})
        status, error = cr.check_response({}, resp)
        assert status == "json_error"
        assert error is None

    def test_boundary_low(self):
        cr = import_check_response()
        resp = _make_response(200, {"error": {"code": -32768, "message": "x"}})
        status, _ = cr.check_response({}, resp)
        assert status == "json_error"

    def test_outside_range_returns_error(self):
        cr = import_check_response()
        resp = _make_response(200, {"error": {"code": -100, "message": "custom"}})
        status, error = cr.check_response({}, resp)
        assert status == "error"
        assert error is not None


class TestHttpError:
    def test_500_is_error(self):
        cr = import_check_response()
        resp = _make_response(500, {"result": "crash"})
        status, error = cr.check_response({}, resp)
        assert status == "error"
        assert error["response_code"] == 500

    def test_custom_error_code(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "errors", lambda: [503])
        cr = import_check_response()
        resp = _make_response(503, {"result": "unavailable"})
        status, error = cr.check_response({}, resp)
        assert status == "error"


class TestSensitiveData:
    def test_select_in_response(self):
        cr = import_check_response()
        resp = _make_response(200, {"result": "SELECT * FROM users"})
        status, error = cr.check_response({}, resp)
        assert status == "error"
        assert "select" in error["reason"]

    def test_custom_sensitive_keyword(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "sensitive_data", lambda: ["secret"])
        cr = import_check_response()
        resp = _make_response(200, {"result": "here is your secret key"})
        status, error = cr.check_response({}, resp)
        assert status == "error"


class TestOkResponse:
    def test_normal_200_ok(self):
        cr = import_check_response()
        resp = _make_response(200, {"result": "success"})
        status, error = cr.check_response({}, resp)
        assert status is None
        assert error is None
