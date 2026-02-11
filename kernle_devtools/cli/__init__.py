"""Standalone CLI entry point: kernle-dev."""

import argparse
import sys


def main():
    """Entry point for `kernle-dev` command."""
    parser = argparse.ArgumentParser(
        prog="kernle-dev",
        description="Kernle devtools — standalone admin tools",
    )
    parser.add_argument("--stack", "-s", required=True, help="Stack ID")

    from kernle_devtools.parsers import add_dashboard_parser, add_session_parsers

    sub = parser.add_subparsers(dest="command", required=True)
    add_dashboard_parser(sub)
    add_session_parsers(sub)

    args = parser.parse_args()

    from kernle import Kernle

    k = Kernle(stack_id=args.stack)

    if args.command == "dashboard":
        from kernle_devtools.cli.dashboard import cmd_dashboard

        cmd_dashboard(args, k)
    elif args.command == "session":
        from kernle_devtools.admin_health.diagnostics import (
            cmd_doctor_session_start,
            cmd_doctor_session_list,
        )

        if args.session_action == "start":
            cmd_doctor_session_start(args, k)
        elif args.session_action == "list":
            cmd_doctor_session_list(args, k)
        else:
            print("Usage: kernle-dev --stack ID session {start|list}")
            sys.exit(1)
    elif args.command == "report":
        from kernle_devtools.admin_health.diagnostics import cmd_doctor_report

        cmd_doctor_report(args, k)
    else:
        parser.print_help()
        sys.exit(1)
