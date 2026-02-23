"""
SCC Threat Detection (PRD 4.8)

Architectural Intent:
- Security Command Center threat detection for cloud resources
- Monitors for security threats, vulnerabilities, and policy violations
- Pure domain logic for threat classification and risk scoring

MCP Integration:
- Tools: scan_resources, get_threats, acknowledge_threat
- Resources: threats://active, threats://{resource_id}

Parallelization Strategy:
- Scanning multiple resources runs concurrently
- Threat classification for independent findings runs in parallel
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional


class ThreatSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(Enum):
    VULNERABILITY = "vulnerability"
    MISCONFIGURATION = "misconfiguration"
    DATA_EXPOSURE = "data_exposure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    COMPLIANCE_VIOLATION = "compliance_violation"


class ThreatStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    MITIGATED = "mitigated"
    FALSE_POSITIVE = "false_positive"


@dataclass(frozen=True)
class ThreatFinding:
    """A single security threat or vulnerability finding."""
    id: UUID
    category: ThreatCategory
    severity: ThreatSeverity
    title: str
    description: str
    resource_id: Optional[UUID] = None
    resource_name: Optional[str] = None
    status: ThreatStatus = ThreatStatus.ACTIVE
    remediation: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def acknowledge(self) -> "ThreatFinding":
        from dataclasses import replace
        return replace(self, status=ThreatStatus.ACKNOWLEDGED)

    def mitigate(self) -> "ThreatFinding":
        from dataclasses import replace
        return replace(self, status=ThreatStatus.MITIGATED)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "resource_name": self.resource_name,
            "status": self.status.value,
            "remediation": self.remediation,
            "detected_at": self.detected_at.isoformat(),
        }


class ThreatDetectionService:
    """Scans resources and identifies security threats."""

    def __init__(self):
        self._findings: dict[UUID, ThreatFinding] = {}

    def scan_resource(self, resource_id: UUID, resource_name: str, resource_config: dict) -> list[ThreatFinding]:
        """Scan a resource for security issues."""
        findings = []

        # Check for common misconfigurations
        if resource_config.get("public_access", False):
            findings.append(ThreatFinding(
                id=uuid4(),
                category=ThreatCategory.MISCONFIGURATION,
                severity=ThreatSeverity.HIGH,
                title="Public access enabled",
                description=f"Resource '{resource_name}' has public access enabled",
                resource_id=resource_id,
                resource_name=resource_name,
                remediation="Disable public access and use VPC endpoints or private links",
            ))

        if not resource_config.get("encryption_enabled", True):
            findings.append(ThreatFinding(
                id=uuid4(),
                category=ThreatCategory.DATA_EXPOSURE,
                severity=ThreatSeverity.CRITICAL,
                title="Encryption not enabled",
                description=f"Resource '{resource_name}' does not have encryption at rest",
                resource_id=resource_id,
                resource_name=resource_name,
                remediation="Enable encryption at rest using KMS managed keys",
            ))

        if not resource_config.get("logging_enabled", True):
            findings.append(ThreatFinding(
                id=uuid4(),
                category=ThreatCategory.COMPLIANCE_VIOLATION,
                severity=ThreatSeverity.MEDIUM,
                title="Audit logging disabled",
                description=f"Resource '{resource_name}' does not have audit logging enabled",
                resource_id=resource_id,
                resource_name=resource_name,
                remediation="Enable CloudTrail/audit logging for compliance",
            ))

        for finding in findings:
            self._findings[finding.id] = finding

        return findings

    def get_active_threats(self) -> list[ThreatFinding]:
        return [f for f in self._findings.values() if f.status == ThreatStatus.ACTIVE]

    def get_threats_by_severity(self, severity: ThreatSeverity) -> list[ThreatFinding]:
        return [f for f in self._findings.values() if f.severity == severity]

    def acknowledge_threat(self, finding_id: UUID) -> Optional[ThreatFinding]:
        finding = self._findings.get(finding_id)
        if finding:
            updated = finding.acknowledge()
            self._findings[finding_id] = updated
            return updated
        return None

    def get_risk_summary(self) -> dict:
        active = self.get_active_threats()
        return {
            "total_findings": len(self._findings),
            "active_threats": len(active),
            "by_severity": {
                s.value: len([f for f in active if f.severity == s])
                for s in ThreatSeverity
            },
            "by_category": {
                c.value: len([f for f in active if f.category == c])
                for c in ThreatCategory
            },
        }
