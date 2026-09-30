"""
tests/test_report.py

Tests for assurance report generation.
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.reporting.report_generator import (
    generate_report,
    save_report,
    load_report,
    _overall_verdict,
    _severity_summary,
    COVERAGE,
    REPORT_SCHEMA_VERSION,
)

# ---------------------------------------------------------------------------
# Verdict logic tests
# ---------------------------------------------------------------------------

class TestOverallVerdict:
    def test_empty_findings_inconclusive(self):
        assert _overall_verdict([]) == "INCONCLUSIVE"

    def test_all_pass(self):
        findings = [{"result": "PASS"}, {"result": "NOT ASSESSED"}]
        assert _overall_verdict(findings) == "PASS"

    def test_anomaly_detected(self):
        findings = [{"result": "PASS"}, {"result": "ANOMALY_DETECTED"}]
        assert _overall_verdict(findings) == "ANOMALIES_DETECTED"

    def test_fail_overrides_anomaly(self):
        findings = [{"result": "ANOMALY_DETECTED"}, {"result": "FAIL"}]
        assert _overall_verdict(findings) == "FAIL"


class TestSeveritySummary:
    def test_counts(self):
        findings = [
            {"severity": "CRITICAL"},
            {"severity": "HIGH"},
            {"severity": "HIGH"},
            {"severity": "MEDIUM"},
            {"severity": "INFO"},
        ]
        s = _severity_summary(findings)
        assert s["CRITICAL"] == 1
        assert s["HIGH"] == 2
        assert s["MEDIUM"] == 1
        assert s["LOW"] == 0


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_basic_structure(self):
        report = generate_report()
        for key in ("schema_version", "report_id", "generated_at", "verdict",
                    "findings_count", "sections", "coverage", "confidence_basis"):
            assert key in report

    def test_schema_version(self):
        report = generate_report()
        assert report["schema_version"] == REPORT_SCHEMA_VERSION

    def test_pass_verdict_for_clean_findings(self):
        findings = [{"result": "PASS", "severity": "INFO", "check_id": "X"}]
        report = generate_report(dataset_findings=findings)
        assert report["verdict"] == "PASS"

    def test_anomaly_verdict(self):
        findings = [{
            "result": "ANOMALY_DETECTED",
            "severity": "HIGH",
            "check_id": "SEC-DS-001",
            "recommended_action": "Review dataset",
        }]
        report = generate_report(dataset_findings=findings)
        assert report["verdict"] == "ANOMALIES_DETECTED"
        assert "Review dataset" in report["recommended_actions"]

    def test_coverage_has_required_keys(self):
        report = generate_report()
        for key in ("implemented", "partial", "unsupported", "assumptions", "known_limitations"):
            assert key in report["coverage"]

    def test_target_name_preserved(self):
        report = generate_report(target_name="Test Audit")
        assert report["target_name"] == "Test Audit"

    def test_findings_count(self):
        ds = [{"result": "PASS", "severity": "INFO", "check_id": "A"}]
        mdl = [{"result": "PASS", "severity": "INFO", "check_id": "B"}]
        report = generate_report(dataset_findings=ds, model_findings=mdl)
        assert report["findings_count"] == 2


# ---------------------------------------------------------------------------
# Save / load tests
# ---------------------------------------------------------------------------

class TestReportIO:
    def test_round_trip(self, tmp_path):
        report = generate_report(target_name="IO Test")
        out = tmp_path / "report.json"
        save_report(report, out)
        assert out.exists()
        loaded = load_report(out)
        assert loaded["report_id"] == report["report_id"]
        assert loaded["target_name"] == "IO Test"

    def test_output_dir_created(self, tmp_path):
        report = generate_report()
        nested = tmp_path / "a" / "b" / "report.json"
        save_report(report, nested)
        assert nested.exists()
