"""
Cloud Readiness Score / R-Model Analysis (PRD 4.11)

Architectural Intent:
- Calculates cloud readiness scores for applications
- Implements the R-Model (Rehost, Replatform, Refactor, Repurchase, Retire, Retain)
- Pure domain logic, no infrastructure dependencies

MCP Integration:
- Exposed via agent-service MCP tools
- Tools: assess_readiness, get_migration_recommendation
- Resources: readiness://{app_id}/score

Parallelization Strategy:
- Multiple application assessments can run concurrently
- Each R-Model dimension evaluated independently
"""

from dataclasses import dataclass, field
from enum import Enum


class MigrationStrategy(Enum):
    """6R Migration Strategies."""
    REHOST = "rehost"         # Lift and shift
    REPLATFORM = "replatform"  # Lift, tinker, and shift
    REFACTOR = "refactor"     # Re-architect
    REPURCHASE = "repurchase"  # Drop and shop (SaaS)
    RETIRE = "retire"         # Decommission
    RETAIN = "retain"         # Keep as-is


@dataclass(frozen=True)
class ReadinessDimension:
    """Individual dimension of cloud readiness assessment."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    findings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CloudReadinessScore:
    """Composite cloud readiness assessment result."""
    application_name: str
    overall_score: float
    recommended_strategy: MigrationStrategy
    dimensions: tuple[ReadinessDimension, ...]
    risk_factors: tuple[str, ...] = field(default_factory=tuple)
    estimated_effort_days: int = 0

    def to_dict(self) -> dict:
        return {
            "application_name": self.application_name,
            "overall_score": round(self.overall_score, 2),
            "recommended_strategy": self.recommended_strategy.value,
            "dimensions": [
                {"name": d.name, "score": round(d.score, 2), "findings": list(d.findings)}
                for d in self.dimensions
            ],
            "risk_factors": list(self.risk_factors),
            "estimated_effort_days": self.estimated_effort_days,
        }


class CloudReadinessService:
    """Assesses application cloud readiness using R-Model analysis."""

    DIMENSIONS = [
        "architecture_complexity",
        "data_dependencies",
        "security_compliance",
        "performance_requirements",
        "team_readiness",
        "cost_impact",
    ]

    def assess(
        self,
        application_name: str,
        architecture_score: float = 0.5,
        data_score: float = 0.5,
        security_score: float = 0.5,
        performance_score: float = 0.5,
        team_score: float = 0.5,
        cost_score: float = 0.5,
    ) -> CloudReadinessScore:
        dimensions = (
            ReadinessDimension("architecture_complexity", architecture_score, 1.5),
            ReadinessDimension("data_dependencies", data_score, 1.2),
            ReadinessDimension("security_compliance", security_score, 1.3),
            ReadinessDimension("performance_requirements", performance_score, 1.0),
            ReadinessDimension("team_readiness", team_score, 0.8),
            ReadinessDimension("cost_impact", cost_score, 1.0),
        )

        total_weight = sum(d.weight for d in dimensions)
        overall = sum(d.score * d.weight for d in dimensions) / total_weight

        strategy = self._recommend_strategy(overall, dimensions)
        risk_factors = self._identify_risks(dimensions)
        effort = self._estimate_effort(strategy, overall)

        return CloudReadinessScore(
            application_name=application_name,
            overall_score=overall,
            recommended_strategy=strategy,
            dimensions=dimensions,
            risk_factors=tuple(risk_factors),
            estimated_effort_days=effort,
        )

    def _recommend_strategy(
        self, overall: float, dimensions: tuple[ReadinessDimension, ...]
    ) -> MigrationStrategy:
        if overall >= 0.8:
            return MigrationStrategy.REHOST
        elif overall >= 0.6:
            return MigrationStrategy.REPLATFORM
        elif overall >= 0.4:
            return MigrationStrategy.REFACTOR
        elif overall >= 0.2:
            return MigrationStrategy.REPURCHASE
        else:
            return MigrationStrategy.RETIRE

    def _identify_risks(self, dimensions: tuple[ReadinessDimension, ...]) -> list[str]:
        risks = []
        for d in dimensions:
            if d.score < 0.3:
                risks.append(f"High risk: {d.name} scored {d.score:.0%}")
        return risks

    def _estimate_effort(self, strategy: MigrationStrategy, score: float) -> int:
        base_efforts = {
            MigrationStrategy.REHOST: 30,
            MigrationStrategy.REPLATFORM: 60,
            MigrationStrategy.REFACTOR: 120,
            MigrationStrategy.REPURCHASE: 45,
            MigrationStrategy.RETIRE: 15,
            MigrationStrategy.RETAIN: 5,
        }
        base = base_efforts.get(strategy, 60)
        complexity_factor = max(0.5, 2.0 - score)
        return int(base * complexity_factor)
