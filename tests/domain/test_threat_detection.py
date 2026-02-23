"""
Domain Tests - SCC Threat Detection (PRD 4.8)

Architectural Intent:
- Tests threat scanning, classification, and lifecycle
- Pure domain tests, no mocks needed
"""

import pytest
from uuid import uuid4

from domain.services.threat_detection import (
    ThreatDetectionService,
    ThreatFinding,
    ThreatSeverity,
    ThreatCategory,
    ThreatStatus,
)


class TestThreatDetectionService:
    def setup_method(self):
        self.service = ThreatDetectionService()

    def test_scan_public_access(self):
        findings = self.service.scan_resource(
            uuid4(), "my-bucket",
            {"public_access": True}
        )
        assert len(findings) >= 1
        assert any(f.category == ThreatCategory.MISCONFIGURATION for f in findings)

    def test_scan_no_encryption(self):
        findings = self.service.scan_resource(
            uuid4(), "my-db",
            {"encryption_enabled": False}
        )
        assert any(f.severity == ThreatSeverity.CRITICAL for f in findings)

    def test_scan_no_logging(self):
        findings = self.service.scan_resource(
            uuid4(), "my-vm",
            {"logging_enabled": False}
        )
        assert any(f.category == ThreatCategory.COMPLIANCE_VIOLATION for f in findings)

    def test_scan_clean_resource(self):
        findings = self.service.scan_resource(
            uuid4(), "clean-resource",
            {"public_access": False, "encryption_enabled": True, "logging_enabled": True}
        )
        assert len(findings) == 0

    def test_get_active_threats(self):
        self.service.scan_resource(uuid4(), "bad", {"public_access": True})
        active = self.service.get_active_threats()
        assert len(active) >= 1

    def test_acknowledge_threat(self):
        findings = self.service.scan_resource(uuid4(), "r", {"public_access": True})
        finding_id = findings[0].id
        updated = self.service.acknowledge_threat(finding_id)
        assert updated.status == ThreatStatus.ACKNOWLEDGED

    def test_risk_summary(self):
        self.service.scan_resource(uuid4(), "r1", {"public_access": True})
        self.service.scan_resource(uuid4(), "r2", {"encryption_enabled": False})
        summary = self.service.get_risk_summary()
        assert summary["total_findings"] >= 2
        assert "by_severity" in summary
        assert "by_category" in summary

    def test_threat_finding_to_dict(self):
        findings = self.service.scan_resource(uuid4(), "r", {"public_access": True})
        d = findings[0].to_dict()
        assert "category" in d
        assert "severity" in d
        assert "remediation" in d
