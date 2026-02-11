"""Tests for admin health diagnostics (migrated from kernle core)."""

import json
import uuid
from datetime import datetime, timezone

import pytest

from kernle.storage.base import Belief, DiagnosticReport, DiagnosticSession
from kernle_devtools.admin_health.diagnostics import (
    _check_operator_consent,
    _generate_report_findings,
    _generate_summary,
    _recommendation_for,
    cmd_doctor_report,
    cmd_doctor_session_list,
    cmd_doctor_session_start,
)
from kernle.structural import StructuralFinding, run_structural_checks


class TestOperatorConsentGate:
    """Tests for trust gating of operator-initiated sessions."""

    def test_self_requested_bypasses_gate(self, diag_setup):
        k, _ = diag_setup
        assert _check_operator_consent(k, "self_requested") is True

    def test_routine_bypasses_gate(self, diag_setup):
        k, _ = diag_setup
        assert _check_operator_consent(k, "routine") is True

    def test_operator_initiated_without_trust(self, diag_setup):
        k, _ = diag_setup
        result = _check_operator_consent(k, "operator_initiated")
        assert result is False

    def test_operator_initiated_with_trust(self, diag_with_trust):
        k, _ = diag_with_trust
        result = _check_operator_consent(k, "operator_initiated")
        assert result is True


class TestReportGeneration:
    """Tests for converting structural findings to report format."""

    def test_generate_report_findings(self):
        findings = [
            StructuralFinding(
                check="orphaned_reference",
                severity="error",
                memory_type="episode",
                memory_id="abc-123",
                message="Episode #abc has broken ref",
            ),
            StructuralFinding(
                check="low_confidence_belief",
                severity="warning",
                memory_type="belief",
                memory_id="def-456",
                message="Belief #def has low confidence",
            ),
        ]

        result = _generate_report_findings(findings)
        assert len(result) == 2
        assert result[0]["severity"] == "error"
        assert result[0]["category"] == "orphaned_reference"
        assert "broken ref" in result[0]["description"]
        assert result[0]["recommendation"] is not None
        assert result[1]["severity"] == "warning"

    def test_generate_summary_healthy(self):
        summary = _generate_summary([])
        assert "healthy" in summary.lower()

    def test_generate_summary_with_findings(self):
        findings = [
            {"severity": "error"},
            {"severity": "warning"},
            {"severity": "warning"},
            {"severity": "info"},
        ]
        summary = _generate_summary(findings)
        assert "4" in summary
        assert "1 error" in summary
        assert "2 warning" in summary
        assert "1 info" in summary


class TestPrivacyBoundary:
    """Tests ensuring reports contain structural data only, never content."""

    def test_findings_contain_no_content(self, diag_setup):
        secret_content = "My secret belief about something private"
        findings = [
            StructuralFinding(
                check="low_confidence_belief",
                severity="warning",
                memory_type="belief",
                memory_id="xyz-789",
                message="Belief #xyz-789 (confidence 0.20) -- low confidence",
            ),
        ]

        result = _generate_report_findings(findings)
        result_str = json.dumps(result)

        assert secret_content not in result_str
        assert "xyz-789" in result_str or "low_confidence" in result_str

    def test_structural_finding_uses_ids_not_content(self):
        finding = StructuralFinding(
            check="low_confidence_belief",
            severity="warning",
            memory_type="belief",
            memory_id="abc-123-full-id",
            message="Belief #abc-123-full (confidence 0.15) -- low confidence",
        )
        d = finding.to_dict()
        assert d["memory_id"] == "abc-123-full-id"
        assert d["memory_type"] == "belief"
        assert "confidence" in d["message"]


class TestEndToEndSession:
    """Integration tests for the full diagnostic session workflow."""

    def test_session_workflow(self, diag_setup):
        k, storage = diag_setup

        belief = Belief(
            id=str(uuid.uuid4()),
            stack_id="test_agent",
            statement="Test belief",
            confidence=0.1,
            created_at=datetime.now(timezone.utc),
        )
        storage.save_belief(belief)

        now = datetime.now(timezone.utc)

        session = DiagnosticSession(
            id=str(uuid.uuid4()),
            stack_id="test_agent",
            session_type="self_requested",
            access_level="structural",
            consent_given=True,
            started_at=now,
        )
        storage.save_diagnostic_session(session)

        raw_findings = run_structural_checks(k)
        findings = _generate_report_findings(raw_findings)
        summary = _generate_summary(findings)

        report = DiagnosticReport(
            id=str(uuid.uuid4()),
            stack_id="test_agent",
            session_id=session.id,
            findings=findings,
            summary=summary,
            created_at=now,
        )
        storage.save_diagnostic_report(report)
        storage.complete_diagnostic_session(session.id)

        completed_session = storage.get_diagnostic_session(session.id)
        assert completed_session.status == "completed"

        saved_report = storage.get_diagnostic_report(report.id)
        assert saved_report is not None
        assert saved_report.session_id == session.id

        assert len(saved_report.findings) > 0
        low_conf = [f for f in saved_report.findings if f["category"] == "low_confidence_belief"]
        assert len(low_conf) > 0

    def test_healthy_session(self, diag_setup):
        k, storage = diag_setup
        now = datetime.now(timezone.utc)

        session = DiagnosticSession(
            id=str(uuid.uuid4()),
            stack_id="test_agent",
            session_type="routine",
            consent_given=True,
            started_at=now,
        )
        storage.save_diagnostic_session(session)

        raw_findings = run_structural_checks(k)
        findings = _generate_report_findings(raw_findings)
        summary = _generate_summary(findings)

        report = DiagnosticReport(
            id=str(uuid.uuid4()),
            stack_id="test_agent",
            session_id=session.id,
            findings=findings,
            summary=summary,
            created_at=now,
        )
        storage.save_diagnostic_report(report)
        storage.complete_diagnostic_session(session.id)

        saved_report = storage.get_diagnostic_report(report.id)
        assert saved_report.findings == []
        assert "healthy" in saved_report.summary.lower()


class TestCLISessionCommands:
    """Tests for CLI command functions."""

    def test_cmd_session_start_json(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            type = "self_requested"
            access = "structural"
            json = True

        cmd_doctor_session_start(Args(), k)
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "session_id" in data
        assert "report_id" in data
        assert data["session_type"] == "self_requested"
        assert data["access_level"] == "structural"
        assert "summary" in data

    def test_cmd_session_start_text(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            type = "routine"
            access = "structural"
            json = False

        cmd_doctor_session_start(Args(), k)
        output = capsys.readouterr().out
        assert "Diagnostic Session" in output
        assert "Report saved" in output

    def test_cmd_session_start_invalid_type(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            type = "invalid_type"
            access = "structural"
            json = False

        cmd_doctor_session_start(Args(), k)
        output = capsys.readouterr().out
        assert "Invalid session type" in output

    def test_cmd_session_start_invalid_access(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            type = "self_requested"
            access = "invalid_level"
            json = False

        cmd_doctor_session_start(Args(), k)
        output = capsys.readouterr().out
        assert "Invalid access level" in output

    def test_cmd_session_start_operator_no_trust(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            type = "operator_initiated"
            access = "structural"
            json = False

        cmd_doctor_session_start(Args(), k)
        output = capsys.readouterr().out
        assert "Insufficient trust" in output

    def test_cmd_session_start_operator_with_trust(self, diag_with_trust, capsys):
        k, _ = diag_with_trust

        class Args:
            type = "operator_initiated"
            access = "structural"
            json = True

        cmd_doctor_session_start(Args(), k)
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["session_type"] == "operator_initiated"

    def test_cmd_session_list_empty(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            json = False

        cmd_doctor_session_list(Args(), k)
        output = capsys.readouterr().out
        assert "No diagnostic sessions found" in output

    def test_cmd_session_list_json(self, diag_setup, capsys):
        k, _ = diag_setup

        class StartArgs:
            type = "self_requested"
            access = "structural"
            json = False

        cmd_doctor_session_start(StartArgs(), k)
        capsys.readouterr()

        class ListArgs:
            json = True

        cmd_doctor_session_list(ListArgs(), k)
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) >= 1

    def test_cmd_report_latest(self, diag_setup, capsys):
        k, _ = diag_setup

        class StartArgs:
            type = "self_requested"
            access = "structural"
            json = False

        cmd_doctor_session_start(StartArgs(), k)
        capsys.readouterr()

        class ReportArgs:
            session_id = "latest"
            json = True

        cmd_doctor_report(ReportArgs(), k)
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "id" in data
        assert "session_id" in data
        assert "summary" in data

    def test_cmd_report_not_found(self, diag_setup, capsys):
        k, _ = diag_setup

        class Args:
            session_id = "nonexistent-id"
            json = False

        cmd_doctor_report(Args(), k)
        output = capsys.readouterr().out
        assert "No report found" in output

    def test_cmd_report_by_session_id(self, diag_setup, capsys):
        k, _ = diag_setup

        class StartArgs:
            type = "self_requested"
            access = "structural"
            json = True

        cmd_doctor_session_start(StartArgs(), k)
        start_output = json.loads(capsys.readouterr().out)
        sid = start_output["session_id"]

        report_args = type("ReportArgs", (), {"session_id": sid, "json": True})()

        cmd_doctor_report(report_args, k)
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["session_id"] == sid


class TestRecommendations:
    """Tests for recommendation mapping."""

    def test_known_recommendations(self):
        assert "Remove" in _recommendation_for("orphaned_reference")
        assert "verify" in _recommendation_for("low_confidence_belief").lower()
        assert "archive" in _recommendation_for("stale_relationship").lower()
        assert "resolve" in _recommendation_for("belief_contradiction").lower()
        assert "review" in _recommendation_for("stale_goal").lower()

    def test_unknown_recommendation(self):
        result = _recommendation_for("unknown_check")
        assert "Review" in result
