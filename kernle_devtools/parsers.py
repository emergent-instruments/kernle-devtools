"""Shared argparse builders — used by both plugin and standalone CLI."""


def add_dashboard_parser(parent_sub):
    """Add dashboard subcommand parser."""
    dash = parent_sub.add_parser("dashboard", help="Launch web inspector")
    dash.add_argument("--port", type=int, default=8420)
    dash.add_argument("--host", default="127.0.0.1")
    dash.add_argument("--no-open", action="store_true")
    return dash


def add_session_parsers(parent_sub):
    """Add session/report parsers for standalone CLI.

    Uses same grammar as core: 'session start', 'session list', 'report'.
    """
    p_session = parent_sub.add_parser("session", help="Diagnostic sessions")
    session_sub = p_session.add_subparsers(dest="session_action", required=True)

    p_start = session_sub.add_parser("start", help="Start diagnostic session")
    p_start.add_argument("--type", "-t", default="self_requested")
    p_start.add_argument("--access", "-a", default="structural")
    p_start.add_argument("--json", "-j", action="store_true")

    p_list = session_sub.add_parser("list", help="List diagnostic sessions")
    p_list.add_argument("--json", "-j", action="store_true")

    p_report = parent_sub.add_parser("report", help="Show diagnostic report")
    p_report.add_argument("session_id")
    p_report.add_argument("--json", "-j", action="store_true")
