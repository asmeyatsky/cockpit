"""
Infrastructure Tests - OTLP Adapters (PRD 4.7)

Architectural Intent:
- Tests in-memory OTLP tracing, metrics, and logging implementations
"""

import pytest
from datetime import datetime, UTC

from infrastructure.adapters.otlp_adapter import (
    InMemoryTracingAdapter,
    InMemoryMetricsAdapter,
    InMemoryLoggingAdapter,
    MockOTLPExporter,
)
from domain.ports.observability_ports import MetricType, SpanContext


class TestInMemoryTracing:
    @pytest.mark.asyncio
    async def test_start_and_end_span(self):
        tracer = InMemoryTracingAdapter()
        span = await tracer.start_span("test-operation", service="my-service")
        assert span.name == "test-operation"
        assert span.end_time is None

        await tracer.end_span(span, status="ok")
        spans = await tracer.get_traces()
        assert len(spans) == 1

    @pytest.mark.asyncio
    async def test_child_span(self):
        tracer = InMemoryTracingAdapter()
        parent = await tracer.start_span("parent")
        child = await tracer.start_span("child", parent=parent.context)
        assert child.context.parent_span_id == parent.context.span_id
        assert child.context.trace_id == parent.context.trace_id

    @pytest.mark.asyncio
    async def test_filter_by_service(self):
        tracer = InMemoryTracingAdapter()
        await tracer.start_span("op1", service="svc-a")
        await tracer.start_span("op2", service="svc-b")
        spans = await tracer.get_traces(service="svc-a")
        assert len(spans) == 1


class TestInMemoryMetrics:
    @pytest.mark.asyncio
    async def test_record_and_query(self):
        metrics = InMemoryMetricsAdapter()
        await metrics.record("cpu_usage", 75.5, MetricType.GAUGE, host="web-1")
        results = await metrics.query("cpu_usage")
        assert len(results) == 1
        assert results[0].value == 75.5

    @pytest.mark.asyncio
    async def test_query_nonexistent(self):
        metrics = InMemoryMetricsAdapter()
        results = await metrics.query("missing_metric")
        assert len(results) == 0


class TestInMemoryLogging:
    @pytest.mark.asyncio
    async def test_log_and_query(self):
        logger = InMemoryLoggingAdapter()
        await logger.log("error", "Something failed", service="api")
        await logger.log("info", "Started up", service="api")
        results = await logger.query_logs(level="error")
        assert len(results) == 1
        assert results[0]["message"] == "Something failed"

    @pytest.mark.asyncio
    async def test_query_by_service(self):
        logger = InMemoryLoggingAdapter()
        await logger.log("info", "msg1", service="api")
        await logger.log("info", "msg2", service="worker")
        results = await logger.query_logs(service="api")
        assert len(results) == 1


class TestMockOTLPExporter:
    @pytest.mark.asyncio
    async def test_export_spans(self):
        exporter = MockOTLPExporter()
        assert await exporter.export_spans([]) is True

    @pytest.mark.asyncio
    async def test_export_metrics(self):
        exporter = MockOTLPExporter()
        assert await exporter.export_metrics([]) is True
