"""
Migration Factory Pipeline (PRD 4.12)

Architectural Intent:
- Orchestrates end-to-end migration waves
- Pipeline: Assess → Plan → Execute → Validate → Cutover
- Each stage can be parallelized across independent workloads

MCP Integration:
- Tools: create_wave, execute_wave, validate_migration
- Resources: migration://{wave_id}/status, migration://waves

Parallelization Strategy:
- Assessment of independent applications runs concurrently
- Execution of independent workloads in a wave runs concurrently
- Validation checks for different resources run concurrently
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional

from domain.exceptions import DomainError


class MigrationStage(Enum):
    ASSESS = "assess"
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"
    CUTOVER = "cutover"
    COMPLETE = "complete"
    FAILED = "failed"


class WorkloadStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class MigrationWorkload:
    """Single workload within a migration wave."""
    id: UUID
    name: str
    source_environment: str
    target_environment: str
    strategy: str  # rehost, replatform, refactor
    status: WorkloadStatus = WorkloadStatus.PENDING
    progress_percent: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "source": self.source_environment,
            "target": self.target_environment,
            "strategy": self.strategy,
            "status": self.status.value,
            "progress": self.progress_percent,
            "error": self.error,
        }


@dataclass(frozen=True)
class MigrationWave:
    """A wave of migrations executed together."""
    id: UUID
    name: str
    stage: MigrationStage
    workloads: tuple[MigrationWorkload, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    domain_events: tuple = field(default_factory=tuple)

    def add_workload(self, workload: MigrationWorkload) -> "MigrationWave":
        if self.stage != MigrationStage.PLAN:
            raise DomainError(f"Cannot add workloads in stage {self.stage.value}")
        return MigrationWave(
            id=self.id,
            name=self.name,
            stage=self.stage,
            workloads=self.workloads + (workload,),
            created_at=self.created_at,
        )

    def advance_stage(self) -> "MigrationWave":
        stage_order = [
            MigrationStage.ASSESS, MigrationStage.PLAN,
            MigrationStage.EXECUTE, MigrationStage.VALIDATE,
            MigrationStage.CUTOVER, MigrationStage.COMPLETE,
        ]
        current_idx = stage_order.index(self.stage)
        if current_idx >= len(stage_order) - 1:
            raise DomainError("Migration already complete")
        next_stage = stage_order[current_idx + 1]
        return MigrationWave(
            id=self.id,
            name=self.name,
            stage=next_stage,
            workloads=self.workloads,
            created_at=self.created_at,
            started_at=self.started_at or datetime.now(UTC),
            completed_at=datetime.now(UTC) if next_stage == MigrationStage.COMPLETE else None,
            domain_events=self.domain_events + (
                WaveStageAdvancedEvent(self.id, next_stage),
            ),
        )

    @property
    def progress_percent(self) -> int:
        if not self.workloads:
            return 0
        return sum(w.progress_percent for w in self.workloads) // len(self.workloads)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "stage": self.stage.value,
            "progress": self.progress_percent,
            "workloads": [w.to_dict() for w in self.workloads],
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class WaveStageAdvancedEvent:
    wave_id: UUID
    new_stage: MigrationStage
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MigrationFactoryService:
    """Orchestrates migration waves through the pipeline."""

    def __init__(self):
        self._waves: dict[UUID, MigrationWave] = {}

    def create_wave(self, name: str) -> MigrationWave:
        wave = MigrationWave(
            id=uuid4(),
            name=name,
            stage=MigrationStage.ASSESS,
        )
        self._waves[wave.id] = wave
        return wave

    def add_workload(
        self, wave_id: UUID, name: str, source: str, target: str, strategy: str
    ) -> MigrationWave:
        wave = self._waves.get(wave_id)
        if not wave:
            raise DomainError(f"Wave {wave_id} not found")
        workload = MigrationWorkload(
            id=uuid4(),
            name=name,
            source_environment=source,
            target_environment=target,
            strategy=strategy,
        )
        wave = wave.add_workload(workload)
        self._waves[wave.id] = wave
        return wave

    def advance_wave(self, wave_id: UUID) -> MigrationWave:
        wave = self._waves.get(wave_id)
        if not wave:
            raise DomainError(f"Wave {wave_id} not found")
        wave = wave.advance_stage()
        self._waves[wave.id] = wave
        return wave

    def get_wave(self, wave_id: UUID) -> Optional[MigrationWave]:
        return self._waves.get(wave_id)

    def list_waves(self) -> list[MigrationWave]:
        return list(self._waves.values())
