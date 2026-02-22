"""
Application Tests - Orchestration

Architectural Intent:
- Parallel workflow tests verifying correct execution order
- Following Rule 4: Mandatory Testing Coverage
- Tests verify DAG orchestration and parallelization
"""

import pytest
import asyncio

from application.orchestration.workflows import (
    DAGOrchestrator,
    WorkflowStep,
    StepStatus,
)


class TestDAGOrchestrator:
    @pytest.mark.asyncio
    async def test_sequential_steps(self):
        execution_order = []

        async def step1(ctx):
            execution_order.append("step1")
            return "step1_result"

        async def step2(ctx):
            execution_order.append("step2")
            return "step2_result"

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("step1", step1, []),
                WorkflowStep("step2", step2, ["step1"]),
            ]
        )

        results = await orchestrator.execute({})

        assert execution_order == ["step1", "step2"]
        assert results["step1"].status == StepStatus.COMPLETED
        assert results["step2"].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_parallel_steps(self):
        execution_order = []

        async def step1(ctx):
            await asyncio.sleep(0.1)
            execution_order.append("step1")
            return "step1_result"

        async def step2(ctx):
            await asyncio.sleep(0.05)
            execution_order.append("step2")
            return "step2_result"

        async def step3(ctx):
            execution_order.append("step3")
            return "step3_result"

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("step1", step1, []),
                WorkflowStep("step2", step2, []),
                WorkflowStep("step3", step3, ["step1", "step2"]),
            ]
        )

        results = await orchestrator.execute({})

        assert "step1" in execution_order
        assert "step2" in execution_order
        assert execution_order.index("step3") > max(
            execution_order.index("step1"),
            execution_order.index("step2"),
        )

    @pytest.mark.asyncio
    async def test_step_failure(self):
        async def failing_step(ctx):
            raise ValueError("Step failed")

        async def dependent_step(ctx):
            return "dependent_result"

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("fail", failing_step, []),
                WorkflowStep("dependent", dependent_step, ["fail"]),
            ]
        )

        results = await orchestrator.execute({})

        assert results["fail"].status == StepStatus.FAILED
        assert "Step failed" in results["fail"].error

    @pytest.mark.asyncio
    async def test_timeout(self):
        async def slow_step(ctx):
            await asyncio.sleep(2)
            return "result"

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("slow", slow_step, [], timeout=0.1),
            ]
        )

        results = await orchestrator.execute({})

        assert results["slow"].status == StepStatus.FAILED
        assert "timed out" in results["slow"].error.lower()

    def test_circular_dependency_detection(self):
        async def step1(ctx):
            return "step1"

        async def step2(ctx):
            return "step2"

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("step1", step1, ["step2"]),
                WorkflowStep("step2", step2, ["step1"]),
            ]
        )

        with pytest.raises(ValueError, match="Circular dependency"):
            asyncio.get_event_loop().run_until_complete(orchestrator.execute({}))

    @pytest.mark.asyncio
    async def test_context_passing(self):
        async def step1(ctx):
            return {"value": 10}

        async def step2(ctx):
            return {"value": ctx["step1_result"]["value"] * 2}

        orchestrator = DAGOrchestrator(
            [
                WorkflowStep("step1", step1, []),
                WorkflowStep("step2", step2, ["step1"]),
            ]
        )

        results = await orchestrator.execute({})

        assert results["step1"].result == {"value": 10}
        assert results["step2"].result == {"value": 20}
