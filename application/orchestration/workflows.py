"""
DAG Orchestration for Parallel Workflow Execution

Architectural Intent:
- Executes workflow steps respecting dependency order
- Parallelizes independent steps automatically
- Following Pattern 1: Fan-Out/Fan-In from skill2026.md

Parallelization Strategy:
- Steps with no dependencies run concurrently
- Steps with satisfied dependencies run concurrently
- Results aggregated for dependent steps
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any
from enum import Enum


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    name: str
    execute: Callable
    depends_on: list[str] = field(default_factory=list)
    timeout: float = 60.0


@dataclass
class StepResult:
    name: str
    status: StepStatus
    result: Any = None
    error: str | None = None
    duration: float = 0.0


class DAGOrchestrator:
    """
    Executes workflow steps respecting dependency order,
    parallelizing independent steps automatically.
    """

    def __init__(self, steps: list[WorkflowStep]):
        self.steps = {s.name: s for s in steps}
        self._validate_no_cycles()

    def _validate_no_cycles(self) -> None:
        visited = set()
        path = set()

        def visit(name: str):
            if name in path:
                raise ValueError(f"Circular dependency detected: {name}")
            if name in visited:
                return

            path.add(name)
            for dep in self.steps[name].depends_on:
                visit(dep)
            path.remove(name)
            visited.add(name)

        for name in self.steps:
            visit(name)

    async def execute(self, context: dict) -> dict[str, StepResult]:
        completed: dict[str, StepResult] = {}
        pending = set(self.steps.keys())

        while pending:
            ready = [
                name
                for name in pending
                if all(dep in completed for dep in self.steps[name].depends_on)
            ]

            if not ready:
                raise RuntimeError("Circular dependency detected")

            results = await asyncio.gather(
                *(self._execute_step(name, context, completed) for name in ready),
                return_exceptions=True,
            )

            for name, result in zip(ready, results):
                if isinstance(result, Exception):
                    completed[name] = StepResult(
                        name=name,
                        status=StepStatus.FAILED,
                        error=str(result),
                    )
                else:
                    completed[name] = result
                pending.discard(name)

        return completed

    async def _execute_step(
        self,
        name: str,
        context: dict,
        completed: dict[str, StepResult],
    ) -> StepResult:
        import time

        start = time.time()

        try:
            step = self.steps[name]
            step_context = {**context}

            for dep_name in step.depends_on:
                step_context[f"{dep_name}_result"] = completed[dep_name].result

            result = await asyncio.wait_for(
                step.execute(step_context),
                timeout=step.timeout,
            )

            duration = time.time() - start
            return StepResult(
                name=name,
                status=StepStatus.COMPLETED,
                result=result,
                duration=duration,
            )

        except asyncio.TimeoutError:
            duration = time.time() - start
            return StepResult(
                name=name,
                status=StepStatus.FAILED,
                error=f"Step timed out after {self.steps[name].timeout}s",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start
            return StepResult(
                name=name,
                status=StepStatus.FAILED,
                error=str(e),
                duration=duration,
            )


class AgentWorkflowOrchestrator:
    """
    Orchestrates multi-agent workflows with parallel execution.
    """

    def __init__(self, agent_executor):
        self.executor = agent_executor

    async def execute_parallel_tasks(
        self,
        agent,
        tasks: list[str],
        context: dict,
    ) -> list[dict]:
        results = await asyncio.gather(
            *(self.executor.execute_task(agent, task, context) for task in tasks),
            return_exceptions=True,
        )

        return [
            r if not isinstance(r, Exception) else {"error": str(r)} for r in results
        ]

    async def execute_sequential_workflow(
        self,
        agent,
        steps: list[dict],
        initial_context: dict,
    ) -> list[dict]:
        results = []
        context = initial_context

        for step in steps:
            result = await self.executor.execute_task(
                agent,
                step["task"],
                context,
            )
            results.append(result)

            if step.get("update_context", True):
                context = {**context, "last_result": result}

        return results


class InfrastructureProvisioningWorkflow:
    """
    Workflow for provisioning infrastructure with parallel validation.
    """

    def __init__(
        self,
        create_resource_use_case,
        cost_analysis_use_case,
        observability_port,
    ):
        self.create_resource = create_resource_use_case
        self.analyze_cost = cost_analysis_use_case
        self.observability = observability_port

    async def provision_with_validation(
        self,
        provider_id: str,
        resources: list[dict],
    ) -> dict:
        orchestrator = DAGOrchestrator(
            [
                WorkflowStep(
                    name="validate_provider",
                    execute=self._validate_provider,
                    depends_on=[],
                ),
                WorkflowStep(
                    name="plan_resources",
                    execute=self._plan_resources,
                    depends_on=["validate_provider"],
                ),
                WorkflowStep(
                    name="calculate_costs",
                    execute=self._calculate_costs,
                    depends_on=["plan_resources"],
                ),
                WorkflowStep(
                    name="provision_resources",
                    execute=self._provision_resources,
                    depends_on=["plan_resources", "calculate_costs"],
                ),
                WorkflowStep(
                    name="configure_monitoring",
                    execute=self._configure_monitoring,
                    depends_on=["provision_resources"],
                ),
            ]
        )

        results = await orchestrator.execute(
            {
                "provider_id": provider_id,
                "resources": resources,
            }
        )

        return {
            "status": "completed"
            if all(r.status == StepStatus.COMPLETED for r in results.values())
            else "failed",
            "steps": {
                name: {"status": r.status.value, "result": r.result, "error": r.error}
                for name, r in results.items()
            },
        }

    async def _validate_provider(self, context: dict) -> dict:
        return {"validated": True, "provider_id": context["provider_id"]}

    async def _plan_resources(self, context: dict) -> dict:
        return {"plan": context["resources"], "plan_id": "plan-123"}

    async def _calculate_costs(self, context: dict) -> dict:
        return {"estimated_cost": 1000.0, "currency": "USD"}

    async def _provision_resources(self, context: dict) -> dict:
        return {"provisioned": len(context["resources"]), "resource_ids": []}

    async def _configure_monitoring(self, context: dict) -> dict:
        return {"monitoring_configured": True}
