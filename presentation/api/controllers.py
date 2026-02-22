"""
API Controllers

Architectural Intent:
- Presentation layer handles HTTP requests/responses
- Only interacts with application layer (use cases, queries)
- Thin layer - no business logic here
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from application.commands.commands import (
    CreateCloudProviderUseCase,
    ConnectProviderUseCase,
    CreateResourceUseCase,
    ManageResourceUseCase,
    CreateAgentUseCase,
    AnalyzeCostUseCase,
)
from application.queries.queries import (
    GetCloudProviderQuery,
    ListCloudProvidersQuery,
    GetResourceQuery,
    ListResourcesQuery,
    GetAgentQuery,
    ListAgentsQuery,
)


@dataclass
class APIResponse:
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class CloudProviderController:
    def __init__(
        self,
        create_provider_use_case: CreateCloudProviderUseCase,
        connect_provider_use_case: ConnectProviderUseCase,
        get_provider_query: GetCloudProviderQuery,
        list_providers_query: ListCloudProvidersQuery,
    ):
        self._create = create_provider_use_case
        self._connect = connect_provider_use_case
        self._get = get_provider_query
        self._list = list_providers_query

    async def create(
        self,
        provider_type: str,
        name: str,
        region: str,
        account_id: Optional[str] = None,
    ) -> APIResponse:
        result = await self._create.execute(provider_type, name, region, account_id)
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def connect(self, provider_id: str) -> APIResponse:
        result = await self._connect.execute(provider_id)
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def disconnect(self, provider_id: str) -> APIResponse:
        return APIResponse(
            success=True, data={"message": f"Provider {provider_id} disconnected"}
        )

    async def get(self, provider_id: str) -> APIResponse:
        provider = await self._get.execute(provider_id)
        if provider:
            return APIResponse(success=True, data=provider.to_dict())
        return APIResponse(success=False, error="Provider not found")

    async def list(self) -> APIResponse:
        providers = await self._list.execute()
        return APIResponse(success=True, data={"providers": providers})


class ResourceController:
    def __init__(
        self,
        create_resource_use_case: CreateResourceUseCase,
        manage_resource_use_case: ManageResourceUseCase,
        get_resource_query: GetResourceQuery,
        list_resources_query: ListResourcesQuery,
    ):
        self._create = create_resource_use_case
        self._manage = manage_resource_use_case
        self._get = get_resource_query
        self._list = list_resources_query

    async def create(
        self,
        provider_id: str,
        resource_type: str,
        name: str,
        region: str,
        config: dict,
        tags: Optional[dict] = None,
    ) -> APIResponse:
        result = await self._create.execute(
            provider_id, resource_type, name, region, config, tags
        )
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def start(self, resource_id: str) -> APIResponse:
        result = await self._manage.start(resource_id)
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def stop(self, resource_id: str) -> APIResponse:
        result = await self._manage.stop(resource_id)
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def terminate(self, resource_id: str) -> APIResponse:
        result = await self._manage.terminate(resource_id)
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def get(self, resource_id: str) -> APIResponse:
        resource = await self._get.execute(resource_id)
        if resource:
            return APIResponse(success=True, data=resource.to_dict())
        return APIResponse(success=False, error="Resource not found")

    async def list(
        self,
        provider_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        state: Optional[str] = None,
    ) -> APIResponse:
        resources = await self._list.execute(provider_id, resource_type, state)
        return APIResponse(success=True, data={"resources": resources})


class AgentController:
    def __init__(
        self,
        create_agent_use_case: CreateAgentUseCase,
        get_agent_query: GetAgentQuery,
        list_agents_query: ListAgentsQuery,
    ):
        self._create = create_agent_use_case
        self._get = get_agent_query
        self._list = list_agents_query

    async def create(
        self,
        name: str,
        description: str,
        provider: str,
        model: str,
        system_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> APIResponse:
        result = await self._create.execute(
            name, description, provider, model, system_prompt, max_tokens, temperature
        )
        return APIResponse(success=result.success, data=result.data, error=result.error)

    async def activate(self, agent_id: str) -> APIResponse:
        return APIResponse(
            success=True, data={"message": f"Agent {agent_id} activated"}
        )

    async def deactivate(self, agent_id: str) -> APIResponse:
        return APIResponse(
            success=True, data={"message": f"Agent {agent_id} deactivated"}
        )

    async def get(self, agent_id: str) -> APIResponse:
        agent = await self._get.execute(agent_id)
        if agent:
            return APIResponse(success=True, data=agent.to_dict())
        return APIResponse(success=False, error="Agent not found")

    async def list(self) -> APIResponse:
        agents = await self._list.execute()
        return APIResponse(success=True, data={"agents": agents})


class CostController:
    def __init__(self, analyze_cost_use_case: AnalyzeCostUseCase):
        self._analyze = analyze_cost_use_case

    async def analyze(self, provider_id: str) -> APIResponse:
        result = await self._analyze.execute(provider_id)
        return APIResponse(success=result.success, data=result.data, error=result.error)
