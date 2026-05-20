"""Tests for config module."""
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


@pytest.fixture(autouse=True)
def reset_config():
    original = dict(config.CONFIG)
    yield
    config.CONFIG.clear()
    config.CONFIG.update(original)


class TestAccessors:
    def test_url(self):
        config.CONFIG["URL"] = "http://example.com"
        assert config.url() == "http://example.com"

    def test_token_prefers_auth_method(self):
        config.CONFIG["AUTH_METHOD"] = "/path/to/login.json"
        config.CONFIG["TOKEN"] = "my_token"
        assert config.token() == "/path/to/login.json"

    def test_token_falls_back_to_token(self):
        config.CONFIG["AUTH_METHOD"] = "none"
        config.CONFIG["TOKEN"] = "my_token"
        assert config.token() == "my_token"

    def test_max_iface_req_count_default(self):
        config.CONFIG["MAX_IFACE_REQUEST_COUNT"] = "default"
        assert config.max_iface_req_count() == 1

    def test_max_iface_req_count_value(self):
        config.CONFIG["MAX_IFACE_REQUEST_COUNT"] = 5
        assert config.max_iface_req_count() == 5

    def test_max_error_count_none(self):
        config.CONFIG["MAX_ERROR_COUNT"] = "none"
        assert config.max_error_count() == 999 ** 99

    def test_max_error_count_value(self):
        config.CONFIG["MAX_ERROR_COUNT"] = 10
        assert config.max_error_count() == 10

    def test_max_time_none(self):
        config.CONFIG["MAX_TIME"] = "none"
        assert config.max_time() == 999 ** 99

    def test_max_time_value(self):
        config.CONFIG["MAX_TIME"] = 120
        assert config.max_time() == 120

    def test_ssh_password_no_typo(self):
        config.CONFIG["SSH_PASSWORD"] = "secret"
        assert config.ssh_password() == "secret"

    def test_errors_returns_list(self):
        config.CONFIG["ERRORS"] = [503, 504]
        assert config.errors() == [503, 504]

    def test_sensitive_data_returns_list(self):
        config.CONFIG["SENSITIVE_DATA"] = ["secret", "password"]
        assert config.sensitive_data() == ["secret", "password"]

    def test_report_format(self):
        config.CONFIG["REPORT_FORMAT"] = "json"
        assert config.report_format() == "json"


class TestValidateConfigParameters:
    def _setup_valid(self, tmp_path):
        config.CONFIG["URL"] = "http://example.com"
        config.CONFIG["PATH_TO_EXAMPLES"] = str(tmp_path)
        config.CONFIG["AUTH_METHOD"] = "none"
        config.CONFIG["MAX_IFACE_REQUEST_COUNT"] = "default"
        config.CONFIG["MAX_ERROR_COUNT"] = "none"
        config.CONFIG["MAX_TIME"] = "none"
        config.CONFIG["ERRORS"] = []
        config.CONFIG["SENSITIVE_DATA"] = []
        config.CONFIG["REPORT_FORMAT"] = "default"

    def test_valid_config(self, tmp_path):
        self._setup_valid(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("config.requests.get", return_value=mock_resp):
            result = config.validate_config_parameters()
        assert result is True

    def test_unreachable_url(self, tmp_path):
        self._setup_valid(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch("config.requests.get", return_value=mock_resp):
            result = config.validate_config_parameters()
        assert result is None

    def test_empty_url_fails(self, tmp_path):
        self._setup_valid(tmp_path)
        config.CONFIG["URL"] = ""
        result = config.validate_config_parameters()
        assert result is None

    def test_bad_report_format(self, tmp_path):
        self._setup_valid(tmp_path)
        config.CONFIG["REPORT_FORMAT"] = "xml"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("config.requests.get", return_value=mock_resp):
            result = config.validate_config_parameters()
        assert result is None

    def test_url_exception_returns_none(self, tmp_path):
        self._setup_valid(tmp_path)
        with patch("config.requests.get", side_effect=Exception("connection refused")):
            result = config.validate_config_parameters()
        assert result is None
