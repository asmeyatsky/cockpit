"""
Application Tests - Orchestrator Backpressure (5.5)

Architectural Intent:
- Tests that DAG orchestrator respects max_concurrency
- Verifies backpressure limits parallel execution
"""

import pytest
import asyncio

from application.orchestration.workflows import (
    DAGOrchestrator,
    WorkflowStep,
    StepStatus,
)


class TestBackpressure:
    @pytest.mark.asyncio
    async def test_max_concurrency_respected(self):
        max_concurrent = 0
        current_concurrent = 0

        async def tracked_step(ctx):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.05)
            current_concurrent -= 1
            return "done"

        # Create 5 independent steps with max_concurrency=2
        steps = [
            WorkflowStep(f"step{i}", tracked_step, [])
            for i in range(5)
        ]
        orchestrator = DAGOrchestrator(steps, max_concurrency=2)
        results = await orchestrator.execute({})

        assert all(r.status == StepStatus.COMPLETED for r in results.values())
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_default_concurrency(self):
        orchestrator = DAGOrchestrator(
            [WorkflowStep("s1", lambda ctx: "ok", [])],
        )
        assert orchestrator._max_concurrency == 10

    @pytest.mark.asyncio
    async def test_backpressure_with_dependencies(self):
        execution_order = []

        async def step(name):
            async def _step(ctx):
                execution_order.append(name)
                await asyncio.sleep(0.01)
                return name
            return _step

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("a", await step("a"), []),
                WorkflowStep("b", await step("b"), []),
                WorkflowStep("c", await step("c"), ["a", "b"]),
            ],
            max_concurrency=1,
        )
        results = await orchestrator.execute({})

        assert results["c"].status == StepStatus.COMPLETED
        # c must come after both a and b
        assert execution_order.index("c") > execution_order.index("a")
        assert execution_order.index("c") > execution_order.index("b")
