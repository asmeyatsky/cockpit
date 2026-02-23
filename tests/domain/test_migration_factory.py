"""
Domain Tests - Migration Factory (PRD 4.12)

Architectural Intent:
- Tests migration wave pipeline stages and workload management
- Pure domain tests, no mocks needed
"""

import pytest
from uuid import uuid4

from domain.services.migration_factory import (
    MigrationFactoryService,
    MigrationWave,
    MigrationWorkload,
    MigrationStage,
    WorkloadStatus,
)
from domain.exceptions import DomainError


class TestMigrationFactory:
    def setup_method(self):
        self.factory = MigrationFactoryService()

    def test_create_wave(self):
        wave = self.factory.create_wave("Wave 1")
        assert wave.stage == MigrationStage.ASSESS
        assert wave.name == "Wave 1"

    def test_advance_wave_stages(self):
        wave = self.factory.create_wave("Wave 1")
        # Assess -> Plan
        wave = self.factory.advance_wave(wave.id)
        assert wave.stage == MigrationStage.PLAN
        # Plan -> Execute
        wave = self.factory.advance_wave(wave.id)
        assert wave.stage == MigrationStage.EXECUTE
        # Execute -> Validate
        wave = self.factory.advance_wave(wave.id)
        assert wave.stage == MigrationStage.VALIDATE
        # Validate -> Cutover
        wave = self.factory.advance_wave(wave.id)
        assert wave.stage == MigrationStage.CUTOVER
        # Cutover -> Complete
        wave = self.factory.advance_wave(wave.id)
        assert wave.stage == MigrationStage.COMPLETE

    def test_advance_complete_wave_raises(self):
        wave = self.factory.create_wave("Wave")
        for _ in range(5):
            wave = self.factory.advance_wave(wave.id)
        assert wave.stage == MigrationStage.COMPLETE
        with pytest.raises(DomainError, match="already complete"):
            self.factory.advance_wave(wave.id)

    def test_add_workload_in_plan_stage(self):
        wave = self.factory.create_wave("Wave")
        wave = self.factory.advance_wave(wave.id)  # -> PLAN
        wave = self.factory.add_workload(
            wave.id, "App1", "on-prem", "aws", "rehost"
        )
        assert len(wave.workloads) == 1
        assert wave.workloads[0].name == "App1"

    def test_add_workload_wrong_stage_raises(self):
        wave = self.factory.create_wave("Wave")
        with pytest.raises(DomainError, match="Cannot add workloads"):
            self.factory.add_workload(
                wave.id, "App1", "on-prem", "aws", "rehost"
            )

    def test_list_waves(self):
        self.factory.create_wave("A")
        self.factory.create_wave("B")
        assert len(self.factory.list_waves()) == 2

    def test_get_wave(self):
        wave = self.factory.create_wave("W")
        retrieved = self.factory.get_wave(wave.id)
        assert retrieved.id == wave.id

    def test_wave_to_dict(self):
        wave = self.factory.create_wave("W")
        d = wave.to_dict()
        assert d["name"] == "W"
        assert d["stage"] == "assess"

    def test_workload_to_dict(self):
        wl = MigrationWorkload(
            id=uuid4(), name="App", source_environment="dc1",
            target_environment="aws", strategy="replatform",
        )
        d = wl.to_dict()
        assert d["strategy"] == "replatform"
        assert d["status"] == "pending"


class TestMigrationWaveDomainEvents:
    def test_advance_emits_event(self):
        wave = MigrationWave(
            id=uuid4(), name="W", stage=MigrationStage.ASSESS,
        )
        advanced = wave.advance_stage()
        assert len(advanced.domain_events) == 1
