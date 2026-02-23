"""
Domain Tests - Cloud Readiness Score (PRD 4.11)

Architectural Intent:
- Tests R-Model analysis and cloud readiness scoring
- Pure domain tests, no mocks needed
"""

import pytest

from domain.services.cloud_readiness import (
    CloudReadinessService,
    CloudReadinessScore,
    MigrationStrategy,
    ReadinessDimension,
)


class TestCloudReadinessService:
    def setup_method(self):
        self.service = CloudReadinessService()

    def test_assess_high_readiness(self):
        result = self.service.assess(
            "my-app",
            architecture_score=0.9,
            data_score=0.8,
            security_score=0.9,
            performance_score=0.85,
            team_score=0.8,
            cost_score=0.9,
        )
        assert isinstance(result, CloudReadinessScore)
        assert result.overall_score > 0.8
        assert result.recommended_strategy == MigrationStrategy.REHOST

    def test_assess_medium_readiness(self):
        result = self.service.assess(
            "legacy-app",
            architecture_score=0.5,
            data_score=0.6,
            security_score=0.5,
            performance_score=0.5,
            team_score=0.5,
            cost_score=0.5,
        )
        assert 0.4 <= result.overall_score <= 0.7
        assert result.recommended_strategy in (MigrationStrategy.REPLATFORM, MigrationStrategy.REFACTOR)

    def test_assess_low_readiness(self):
        result = self.service.assess(
            "ancient-app",
            architecture_score=0.1,
            data_score=0.2,
            security_score=0.1,
            performance_score=0.15,
            team_score=0.1,
            cost_score=0.2,
        )
        assert result.overall_score < 0.3
        assert len(result.risk_factors) > 0

    def test_risk_factors_identified(self):
        result = self.service.assess(
            "risky-app",
            architecture_score=0.2,
            data_score=0.1,
            security_score=0.2,
        )
        assert any("High risk" in r for r in result.risk_factors)

    def test_effort_estimation(self):
        result = self.service.assess("app", architecture_score=0.9, data_score=0.9,
                                      security_score=0.9, performance_score=0.9,
                                      team_score=0.9, cost_score=0.9)
        assert result.estimated_effort_days > 0

    def test_to_dict(self):
        result = self.service.assess("app")
        d = result.to_dict()
        assert "application_name" in d
        assert "overall_score" in d
        assert "recommended_strategy" in d
        assert "dimensions" in d

    def test_dimensions_count(self):
        result = self.service.assess("app")
        assert len(result.dimensions) == 6
