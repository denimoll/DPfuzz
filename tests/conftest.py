"""Configure test environment: mock pyradamsa binary dependency."""
import sys
from unittest.mock import MagicMock, patch


class _FakeRadamsa:
    """Radamsa stub: appends 'X' to simulate mutation without breaking JSON."""
    def fuzz(self, data: bytes) -> bytes:
        return data + b"X" if data else b"X"


class _FakePyradamsaModule:
    Radamsa = _FakeRadamsa


class _FakePyradamsa:
    pyradamsa = _FakePyradamsaModule()


# Inject the fake module before any test imports change_values
sys.modules.setdefault("pyradamsa", _FakePyradamsa())
sys.modules.setdefault("pyradamsa.pyradamsa", _FakePyradamsaModule())
