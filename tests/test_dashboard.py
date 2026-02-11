"""Tests for dashboard server and serialization."""

import json
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

from kernle_devtools.dashboard.server import DashboardHandler, serialize


class TestSerialize:
    """Tests for the serialize() helper."""

    def test_none(self):
        assert serialize(None) is None

    def test_primitives(self):
        assert serialize("hello") == "hello"
        assert serialize(42) == 42
        assert serialize(3.14) == 3.14
        assert serialize(True) is True

    def test_datetime(self):
        dt = datetime(2026, 1, 15, 12, 0, 0)
        assert serialize(dt) == "2026-01-15T12:00:00"

    def test_list(self):
        assert serialize([1, "a", None]) == [1, "a", None]

    def test_dict(self):
        assert serialize({"key": "val"}) == {"key": "val"}

    def test_nested(self):
        result = serialize({"items": [1, datetime(2026, 1, 1)]})
        assert result == {"items": [1, "2026-01-01T00:00:00"]}

    def test_unknown_type(self):
        result = serialize(object())
        assert isinstance(result, str)


class TestDashboardHandler:
    """Tests for dashboard HTTP handler."""

    def test_handler_has_expected_attributes(self):
        assert hasattr(DashboardHandler, "kernle_instance")
        assert hasattr(DashboardHandler, "_send_json")
        assert hasattr(DashboardHandler, "_send_html")
        assert hasattr(DashboardHandler, "_send_error")

    def test_get_int_param_default(self):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert handler._get_int_param({}, "limit", 100) == 100

    def test_get_int_param_provided(self):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert handler._get_int_param({"limit": ["50"]}, "limit", 100) == 50

    def test_get_int_param_invalid(self):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert handler._get_int_param({"limit": ["abc"]}, "limit", 100) == 100

    def test_get_bool_param_none(self):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert handler._get_bool_param({}, "processed") is None

    def test_get_bool_param_true(self):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert handler._get_bool_param({"processed": ["true"]}, "processed") is True

    def test_get_bool_param_false(self):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert handler._get_bool_param({"processed": ["false"]}, "processed") is False
