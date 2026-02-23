"""
OpenTelemetry (OTLP) Observability Ports (PRD 4.7)

Architectural Intent:
- Defines port interfaces for observability following OpenTelemetry standard
- Supports traces, metrics, and logs via OTLP protocol
- Enables pluggable backends (Cloud Monitoring, Prometheus, Jaeger)

MCP Integration:
- Resources: telemetry://traces, telemetry://metrics, telemetry://logs
- Tools: create_span, record_metric, query_traces

Parallelization Strategy:
- Metrics collection from multiple sources runs concurrently
- Trace export is non-blocking via async batching
"""

from typing import Protocol, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID, uuid4
from enum import Enum


class SpanKind(Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True)
class SpanContext:
    """OpenTelemetry-compatible span context."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None


@dataclass(frozen=True)
class Span:
    """OpenTelemetry-compatible span for distributed tracing."""
    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: Optional[datetime] = None
    attributes: dict = field(default_factory=dict)
    status: str = "ok"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "attributes": self.attributes,
            "status": self.status,
        }


@dataclass(frozen=True)
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    labels: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class TracingPort(Protocol):
    """Port for distributed tracing (OTLP-compatible)."""
    async def start_span(self, name: str, parent: Optional[SpanContext] = None, **attributes) -> Span: ...
    async def end_span(self, span: Span, status: str = "ok") -> None: ...
    async def get_traces(self, service: Optional[str] = None, limit: int = 100) -> list[Span]: ...


class MetricsPort(Protocol):
    """Port for metrics collection (OTLP-compatible)."""
    async def record(self, name: str, value: float, metric_type: MetricType, **labels) -> None: ...
    async def query(self, name: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> list[MetricPoint]: ...


class LoggingPort(Protocol):
    """Port for structured logging (OTLP-compatible)."""
    async def log(self, level: str, message: str, **attributes) -> None: ...
    async def query_logs(self, level: Optional[str] = None, service: Optional[str] = None, limit: int = 100) -> list[dict]: ...


class OTLPExporterPort(Protocol):
    """Port for exporting telemetry data via OTLP protocol."""
    async def export_spans(self, spans: list[Span]) -> bool: ...
    async def export_metrics(self, metrics: list[MetricPoint]) -> bool: ...
