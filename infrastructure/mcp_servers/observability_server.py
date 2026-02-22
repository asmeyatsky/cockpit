"""
Observability Service MCP Server

Architectural Intent:
- Exposes monitoring, logging, and tracing via MCP protocol
- Tools for metrics, logs, traces, and alerts

MCP Integration:
- Server name: observability-service
- Tools: get_metrics, get_logs, get_traces, setup_alerts
- Resources: metrics://{provider_id}, logs://{resource_id}
"""

from mcp.server import Server
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime, timedelta


class MetricsInput(BaseModel):
    provider_id: str
    metric_name: str
    start_time: str
    end_time: str
    interval: Optional[str] = "1h"


class LogsInput(BaseModel):
    provider_id: str
    resource_id: str
    start_time: str
    end_time: str
    log_level: Optional[str] = None


class TracesInput(BaseModel):
    provider_id: str
    trace_id: str


class AlertsInput(BaseModel):
    provider_id: str
    resource_id: str
    metric_name: str
    threshold: float
    condition: str


def create_observability_server() -> Server:
    server = Server("observability-service")

    @server.tool()
    async def get_metrics(input: MetricsInput) -> dict:
        """Get metrics for a provider."""
        return {
            "success": True,
            "data": {
                "metric_name": input.metric_name,
                "provider_id": input.provider_id,
                "datapoints": [
                    {
                        "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                        "value": 100 + i * 10,
                    }
                    for i in range(24)
                ],
                "statistics": {
                    "min": 100,
                    "max": 330,
                    "avg": 215,
                    "sum": 5160,
                },
            },
        }

    @server.tool()
    async def get_logs(input: LogsInput) -> dict:
        """Get logs for a resource."""
        return {
            "success": True,
            "data": {
                "resource_id": input.resource_id,
                "logs": [
                    {
                        "timestamp": (
                            datetime.now() - timedelta(minutes=i)
                        ).isoformat(),
                        "level": "INFO",
                        "message": f"Log entry {i}",
                    }
                    for i in range(10)
                ],
                "total_count": 10,
            },
        }

    @server.tool()
    async def get_traces(input: TracesInput) -> dict:
        """Get trace details."""
        return {
            "success": True,
            "data": {
                "trace_id": input.trace_id,
                "provider_id": input.provider_id,
                "duration_ms": 150,
                "spans": [
                    {
                        "name": "HTTP GET",
                        "duration_ms": 50,
                        "status": "ok",
                    },
                    {
                        "name": "Database Query",
                        "duration_ms": 80,
                        "status": "ok",
                    },
                    {
                        "name": "Response",
                        "duration_ms": 20,
                        "status": "ok",
                    },
                ],
            },
        }

    @server.tool()
    async def setup_alerts(input: AlertsInput) -> dict:
        """Setup alerts for a resource."""
        return {
            "success": True,
            "data": {
                "alert_id": f"alert-{input.resource_id}-{input.metric_name}",
                "provider_id": input.provider_id,
                "resource_id": input.resource_id,
                "metric_name": input.metric_name,
                "threshold": input.threshold,
                "condition": input.condition,
                "status": "active",
            },
        }

    @server.resource("metrics://{provider_id}")
    async def get_metrics_summary(provider_id: str) -> str:
        """Get metrics summary for a provider."""
        return json.dumps(
            {
                "provider_id": provider_id,
                "metrics": [
                    {"name": "cpu_usage", "status": "healthy", "current_value": 45.2},
                    {
                        "name": "memory_usage",
                        "status": "healthy",
                        "current_value": 62.8,
                    },
                    {"name": "disk_usage", "status": "warning", "current_value": 78.5},
                    {"name": "network_in", "status": "healthy", "current_value": 1024},
                    {"name": "network_out", "status": "healthy", "current_value": 512},
                ],
            }
        )

    @server.resource("logs://{resource_id}")
    async def get_logs_summary(resource_id: str) -> str:
        """Get logs summary for a resource."""
        return json.dumps(
            {
                "resource_id": resource_id,
                "summary": {
                    "total_logs": 150,
                    "by_level": {"INFO": 100, "WARNING": 30, "ERROR": 20},
                    "time_range": "24h",
                },
            }
        )

    @server.prompt()
    async def metrics_dashboard(provider_id: str) -> str:
        """Generate a metrics dashboard summary."""
        return f"""Metrics Dashboard for Provider {provider_id}

CPU Usage: 45.2%
Memory Usage: 62.8%  
Disk Usage: 78.5% ⚠️
Network In: 1,024 KB/s
Network Out: 512 KB/s

Alerts: 1 active (Disk usage warning)
"""

    return server
