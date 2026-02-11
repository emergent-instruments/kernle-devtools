"""Diagnostic session and report functions.

These were extracted from kernle.cli.commands.doctor as part of the
kernle-devtools separation. They provide formal diagnostic session
management with operator trust gating and privacy-preserving reports.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List

try:
    from kernle.structural import StructuralFinding, run_structural_checks
except ImportError:
    raise ImportError(
        "kernle-devtools requires kernle>=0.12.4 (kernle.structural module). "
        "Please upgrade: pip install --upgrade kernle"
    )


def _check_operator_consent(k, session_type: str) -> bool:
    """Check trust gate for operator-initiated sessions."""
    if session_type != "operator_initiated":
        return True
    result = k.gate_memory_input(source_entity="stack-owner", action="diagnostic")
    return result.get("allowed", False)


def _generate_report_findings(
    structural_findings: List[StructuralFinding],
) -> List[dict]:
    """Convert StructuralFindings into DiagnosticReport findings format.

    Privacy boundary: reports contain structural data only (IDs, scores,
    counts), never memory content.
    """
    return [
        {
            "severity": f.severity,
            "category": f.check,
            "description": f.message,
            "recommendation": _recommendation_for(f.check),
        }
        for f in structural_findings
    ]


def _recommendation_for(check: str) -> str:
    """Get a recommendation for a given check type."""
    recommendations = {
        "orphaned_reference": "Remove or update broken references",
        "low_confidence_belief": "Review and verify or archive low-confidence beliefs",
        "stale_relationship": "Re-engage or archive stale relationships",
        "belief_contradiction": "Review and resolve contradicting beliefs",
        "stale_goal": "Review goal status -- complete, archive, or re-prioritize",
    }
    return recommendations.get(check, "Review finding and take appropriate action")


def _generate_summary(findings: List[dict]) -> str:
    """Generate a summary of diagnostic findings."""
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    infos = sum(1 for f in findings if f["severity"] == "info")
    total = len(findings)
    if total == 0:
        return "No issues found. Memory graph is healthy."
    parts = []
    if errors:
        parts.append(f"{errors} error(s)")
    if warnings:
        parts.append(f"{warnings} warning(s)")
    if infos:
        parts.append(f"{infos} info")
    return f"Found {total} finding(s): {', '.join(parts)}"


def cmd_doctor_session_start(args, k):
    """Start a new diagnostic session."""
    from kernle.storage.base import DiagnosticSession

    session_type = getattr(args, "type", "self_requested") or "self_requested"
    access_level = getattr(args, "access", "structural") or "structural"
    output_json = getattr(args, "json", False)

    valid_types = {"self_requested", "routine", "anomaly_triggered", "operator_initiated"}
    if session_type not in valid_types:
        print(
            f"Error: Invalid session type '{session_type}'. "
            f"Must be one of: {', '.join(sorted(valid_types))}"
        )
        return

    valid_levels = {"structural", "content", "full"}
    if access_level not in valid_levels:
        print(
            f"Error: Invalid access level '{access_level}'. "
            f"Must be one of: {', '.join(sorted(valid_levels))}"
        )
        return

    if not _check_operator_consent(k, session_type):
        print("Error: Insufficient trust for operator-initiated diagnostic session.")
        print("The agent's trust assessment for 'stack-owner' must meet the diagnostic threshold.")
        return

    now = datetime.now(timezone.utc)
    session = DiagnosticSession(
        id=str(uuid.uuid4()),
        stack_id=k.stack_id,
        session_type=session_type,
        access_level=access_level,
        status="active",
        consent_given=True,
        started_at=now,
    )
    k._storage.save_diagnostic_session(session)

    findings_raw = run_structural_checks(k)
    findings = _generate_report_findings(findings_raw)
    summary = _generate_summary(findings)

    from kernle.storage.base import DiagnosticReport

    report = DiagnosticReport(
        id=str(uuid.uuid4()),
        stack_id=k.stack_id,
        session_id=session.id,
        findings=findings,
        summary=summary,
        created_at=now,
    )
    k._storage.save_diagnostic_report(report)
    k._storage.complete_diagnostic_session(session.id)

    if output_json:
        output = {
            "session_id": session.id,
            "report_id": report.id,
            "session_type": session_type,
            "access_level": access_level,
            "summary": summary,
            "findings": findings,
        }
        print(json.dumps(output, indent=2))
    else:
        print()
        print("=" * 55)
        print("  Kernle Doctor - Diagnostic Session")
        print("=" * 55)
        print(f"  Stack: {k.stack_id}")
        print(f"  Session: {session.id[:12]}...")
        print(f"  Type: {session_type}")
        print(f"  Access: {access_level}")
        print()
        print(f"  {summary}")
        print()

        if not findings:
            print("  All structural checks passed. Memory graph is healthy.")
        else:
            errors = [f for f in findings if f["severity"] == "error"]
            warnings = [f for f in findings if f["severity"] == "warning"]
            infos = [f for f in findings if f["severity"] == "info"]

            if errors:
                print("-" * 55)
                print("ERRORS")
                print("-" * 55)
                for f in errors:
                    print(f"  [{f['severity']}]   {f['description']}")
                    print(f"           -> {f['recommendation']}")
                print()

            if warnings:
                print("-" * 55)
                print("WARNINGS")
                print("-" * 55)
                for f in warnings:
                    print(f"  [{f['severity']}] {f['description']}")
                    print(f"           -> {f['recommendation']}")
                print()

            if infos:
                print("-" * 55)
                print("INFO")
                print("-" * 55)
                for f in infos:
                    print(f"  [{f['severity']}]    {f['description']}")
                print()

        print(f"  Report saved: {report.id[:12]}...")
        print()


def cmd_doctor_session_list(args, k):
    """List diagnostic sessions."""
    output_json = getattr(args, "json", False)
    sessions = k._storage.get_diagnostic_sessions(limit=20)

    if output_json:
        output = [
            {
                "id": s.id,
                "session_type": s.session_type,
                "access_level": s.access_level,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ]
        print(json.dumps(output, indent=2))
    else:
        print()
        print("=" * 55)
        print("  Kernle Doctor - Diagnostic Sessions")
        print("=" * 55)
        print(f"  Stack: {k.stack_id}")
        print()

        if not sessions:
            print("  No diagnostic sessions found.")
            print("  Start one with: kernle doctor session start")
            print()
            return

        for s in sessions:
            started = s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "?"
            status_icon = {
                "active": "[active]",
                "completed": "[done]  ",
                "cancelled": "[cancel]",
            }.get(s.status, f"[{s.status}]")
            print(f"  {status_icon} {s.id[:12]}...  {s.session_type:20s}  {started}")
        print()


def cmd_doctor_report(args, k):
    """Show a diagnostic report."""
    output_json = getattr(args, "json", False)
    session_id = getattr(args, "session_id", None)

    if session_id == "latest":
        reports = k._storage.get_diagnostic_reports(limit=1)
        if not reports:
            print("No diagnostic reports found.")
            return
        report = reports[0]
    else:
        report = k._storage.get_diagnostic_report(session_id)
        if not report:
            reports = k._storage.get_diagnostic_reports(session_id=session_id, limit=1)
            if reports:
                report = reports[0]
            else:
                print(f"No report found for ID: {session_id}")
                return

    if output_json:
        output = {
            "id": report.id,
            "session_id": report.session_id,
            "summary": report.summary,
            "findings": report.findings or [],
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
        print(json.dumps(output, indent=2))
    else:
        print()
        print("=" * 55)
        print("  Kernle Doctor - Diagnostic Report")
        print("=" * 55)
        print(f"  Stack: {k.stack_id}")
        print(f"  Report: {report.id[:12]}...")
        print(f"  Session: {report.session_id[:12]}...")
        if report.created_at:
            print(f"  Created: {report.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()

        if report.summary:
            print(f"  Summary: {report.summary}")
            print()

        findings = report.findings or []
        if not findings:
            print("  No findings -- memory graph is healthy.")
        else:
            errors = [f for f in findings if f.get("severity") == "error"]
            warnings = [f for f in findings if f.get("severity") == "warning"]
            infos = [f for f in findings if f.get("severity") == "info"]

            if errors:
                print("-" * 55)
                print("ERRORS")
                print("-" * 55)
                for f in errors:
                    print(f"  [{f['severity']}]   {f['description']}")
                    print(f"           -> {f['recommendation']}")
                print()

            if warnings:
                print("-" * 55)
                print("WARNINGS")
                print("-" * 55)
                for f in warnings:
                    print(f"  [{f['severity']}] {f['description']}")
                    print(f"           -> {f['recommendation']}")
                print()

            if infos:
                print("-" * 55)
                print("INFO")
                print("-" * 55)
                for f in infos:
                    print(f"  [{f['severity']}]    {f['description']}")
                print()

        print()
