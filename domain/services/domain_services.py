"""
Domain Services

Architectural Intent:
- Encapsulates domain logic that doesn't belong to a single entity
- Following Rule 1: Zero business logic in infrastructure components
- Services use ports to interact with external systems
"""

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime, timedelta

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.entities.resource import Resource, ResourceState
from domain.value_objects.money import Money
from domain.ports.repository_ports import (
    CloudProviderRepositoryPort,
    ResourceRepositoryPort,
)
from domain.ports.infrastructure_ports import CostPort, ObservabilityPort


class ProviderDomainService:
    def __init__(self, provider_repo: CloudProviderRepositoryPort):
        self._repo = provider_repo

    async def get_active_providers(self) -> list[CloudProvider]:
        providers = await self._repo.get_all()
        return [p for p in providers if p.status == ProviderStatus.CONNECTED]

    async def get_providers_by_type(
        self, provider_type: CloudProviderType
    ) -> list[CloudProvider]:
        return await self._repo.get_by_type(provider_type)


class ResourceDomainService:
    def __init__(self, resource_repo: ResourceRepositoryPort):
        self._repo = resource_repo

    async def get_running_resources(self) -> list[Resource]:
        resources = await self._repo.get_all()
        return [r for r in resources if r.state == ResourceState.RUNNING]

    async def get_resources_by_provider(self, provider_id: UUID) -> list[Resource]:
        return await self._repo.get_by_provider(provider_id)

    async def get_failed_resources(self) -> list[Resource]:
        resources = await self._repo.get_all()
        return [r for r in resources if r.state == ResourceState.FAILED]

    def calculate_total_cost(
        self, resources: list[Resource], cost_per_hour: dict
    ) -> Money:
        total = Money.zero()
        for resource in resources:
            if resource.state == ResourceState.RUNNING:
                rate = cost_per_hour.get(resource.resource_type.value, 0.1)
                total = total + Money(rate, "USD")
        return total


class CostOptimizationService:
    def __init__(self, cost_port: CostPort, resource_repo: ResourceRepositoryPort):
        self._cost_port = cost_port
        self._resource_repo = resource_repo

    async def analyze_costs(self, provider_id: UUID) -> dict:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        current_cost = await self._cost_port.get_current_cost(
            provider_id, start_date, end_date
        )
        cost_breakdown = await self._cost_port.get_cost_breakdown(
            provider_id, start_date, end_date
        )
        forecast = await self._cost_port.get_forecast(provider_id, 30)

        return {
            "current_month_cost": current_cost,
            "cost_breakdown": cost_breakdown,
            "monthly_forecast": forecast,
            "recommendations": self._generate_recommendations(cost_breakdown),
        }

    def _generate_recommendations(self, breakdown: dict) -> list[dict]:
        recommendations = []

        for service, cost in breakdown.get("by_service", {}).items():
            if cost.amount > 1000:
                recommendations.append(
                    {
                        "type": "cost_alert",
                        "service": service,
                        "message": f"High spending detected: {service} at {cost.format()}/month",
                        "potential_savings": cost * 0.2,
                    }
                )

        return recommendations
