"""Tests for shared parser builders."""

import argparse

from kernle_devtools.parsers import add_dashboard_parser, add_session_parsers


class TestDashboardParser:
    """Tests for dashboard parser builder."""

    def test_dashboard_parser_defaults(self):
        parent = argparse.ArgumentParser()
        sub = parent.add_subparsers(dest="command")
        add_dashboard_parser(sub)
        args = parent.parse_args(["dashboard"])
        assert args.port == 8420
        assert args.host == "127.0.0.1"
        assert args.no_open is False

    def test_dashboard_parser_custom(self):
        parent = argparse.ArgumentParser()
        sub = parent.add_subparsers(dest="command")
        add_dashboard_parser(sub)
        args = parent.parse_args(["dashboard", "--port", "9000", "--host", "0.0.0.0", "--no-open"])
        assert args.port == 9000
        assert args.host == "0.0.0.0"
        assert args.no_open is True


class TestSessionParsers:
    """Tests for session/report parser builders."""

    def test_session_start_defaults(self):
        parent = argparse.ArgumentParser()
        sub = parent.add_subparsers(dest="command")
        add_session_parsers(sub)
        args = parent.parse_args(["session", "start"])
        assert args.type == "self_requested"
        assert args.access == "structural"
        assert args.json is False

    def test_session_start_custom(self):
        parent = argparse.ArgumentParser()
        sub = parent.add_subparsers(dest="command")
        add_session_parsers(sub)
        args = parent.parse_args(["session", "start", "-t", "routine", "-a", "full", "-j"])
        assert args.type == "routine"
        assert args.access == "full"
        assert args.json is True

    def test_session_list(self):
        parent = argparse.ArgumentParser()
        sub = parent.add_subparsers(dest="command")
        add_session_parsers(sub)
        args = parent.parse_args(["session", "list", "-j"])
        assert args.session_action == "list"
        assert args.json is True

    def test_report_parser(self):
        parent = argparse.ArgumentParser()
        sub = parent.add_subparsers(dest="command")
        add_session_parsers(sub)
        args = parent.parse_args(["report", "latest", "-j"])
        assert args.session_id == "latest"
        assert args.json is True
