"""
OpenTelemetry (OTLP) Adapter (PRD 4.7)

Architectural Intent:
- Implements TracingPort and MetricsPort using OpenTelemetry-compatible storage
- In-memory implementation for development; production uses OTLP exporters
- Following Rule 2: Interface-First Development

MCP Integration:
- Feeds observability MCP server with telemetry data
- Resources: telemetry://traces, telemetry://metrics

Parallelization Strategy:
- Metric recording is non-blocking
- Trace export uses async batching
"""

import logging
from datetime import datetime, UTC
from typing import Optional
from uuid import uuid4

from domain.ports.observability_ports import (
    TracingPort,
    MetricsPort,
    LoggingPort,
    OTLPExporterPort,
    Span,
    SpanContext,
    SpanKind,
    MetricPoint,
    MetricType,
)

logger = logging.getLogger(__name__)


class InMemoryTracingAdapter:
    """In-memory tracing implementation (OTLP-compatible interface)."""

    def __init__(self):
        self._spans: list[Span] = []

    async def start_span(
        self, name: str, parent: Optional[SpanContext] = None, **attributes
    ) -> Span:
        context = SpanContext(
            trace_id=parent.trace_id if parent else uuid4().hex[:32],
            span_id=uuid4().hex[:16],
            parent_span_id=parent.span_id if parent else None,
        )
        span = Span(
            name=name,
            context=context,
            attributes=attributes,
        )
        self._spans.append(span)
        return span

    async def end_span(self, span: Span, status: str = "ok") -> None:
        from dataclasses import replace
        ended = replace(span, end_time=datetime.now(UTC), status=status)
        self._spans = [s if s.context.span_id != span.context.span_id else ended for s in self._spans]

    async def get_traces(self, service: Optional[str] = None, limit: int = 100) -> list[Span]:
        spans = self._spans
        if service:
            spans = [s for s in spans if s.attributes.get("service") == service]
        return spans[-limit:]


class InMemoryMetricsAdapter:
    """In-memory metrics implementation (OTLP-compatible interface)."""

    def __init__(self):
        self._metrics: list[MetricPoint] = []

    async def record(self, name: str, value: float, metric_type: MetricType, **labels) -> None:
        point = MetricPoint(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels,
        )
        self._metrics.append(point)

    async def query(
        self, name: str, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> list[MetricPoint]:
        results = [m for m in self._metrics if m.name == name]
        if start:
            results = [m for m in results if m.timestamp >= start]
        if end:
            results = [m for m in results if m.timestamp <= end]
        return results


class InMemoryLoggingAdapter:
    """In-memory structured logging (OTLP-compatible interface)."""

    def __init__(self):
        self._logs: list[dict] = []

    async def log(self, level: str, message: str, **attributes) -> None:
        entry = {
            "level": level,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **attributes,
        }
        self._logs.append(entry)

    async def query_logs(
        self, level: Optional[str] = None, service: Optional[str] = None, limit: int = 100
    ) -> list[dict]:
        results = self._logs
        if level:
            results = [l for l in results if l.get("level") == level]
        if service:
            results = [l for l in results if l.get("service") == service]
        return results[-limit:]


class MockOTLPExporter:
    """Mock OTLP exporter for development."""

    async def export_spans(self, spans: list[Span]) -> bool:
        logger.debug("Exported %d spans via OTLP", len(spans))
        return True

    async def export_metrics(self, metrics: list[MetricPoint]) -> bool:
        logger.debug("Exported %d metrics via OTLP", len(metrics))
        return True
