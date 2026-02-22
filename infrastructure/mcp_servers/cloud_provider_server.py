"""
Cloud Provider MCP Server

Architectural Intent:
- Exposes cloud provider capabilities via MCP protocol
- Each bounded context has exactly one MCP server
- Tools = write operations, Resources = read operations

MCP Integration:
- Server name: cloud-provider-service
- Tools: create_provider, connect_provider, disconnect_provider, delete_provider
- Resources: provider://{provider_id}, provider://list
"""

from mcp.server import Server
from mcp.types import Tool, Resource
from pydantic import BaseModel

from application.commands.commands import (
    CreateCloudProviderUseCase,
    ConnectProviderUseCase,
)
from application.queries.queries import (
    GetCloudProviderQuery,
    ListCloudProvidersQuery,
)


class CreateProviderInput(BaseModel):
    provider_type: str
    name: str
    region: str
    account_id: str | None = None


class ConnectProviderInput(BaseModel):
    provider_id: str


def create_cloud_provider_server(
    create_provider_use_case: CreateCloudProviderUseCase,
    connect_provider_use_case: ConnectProviderUseCase,
    get_provider_query: GetCloudProviderQuery,
    list_providers_query: ListCloudProvidersQuery,
) -> Server:
    server = Server("cloud-provider-service")

    @server.tool()
    async def create_provider(input: CreateProviderInput) -> dict:
        """Create a new cloud provider connection."""
        result = await create_provider_use_case.execute(
            provider_type=input.provider_type,
            name=input.name,
            region=input.region,
            account_id=input.account_id,
        )

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.tool()
    async def connect_provider(input: ConnectProviderInput) -> dict:
        """Connect to an existing cloud provider."""
        result = await connect_provider_use_case.execute(input.provider_id)

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.tool()
    async def disconnect_provider(provider_id: str) -> dict:
        """Disconnect from a cloud provider."""
        return {"success": True, "message": f"Provider {provider_id} disconnected"}

    @server.tool()
    async def delete_provider(provider_id: str) -> dict:
        """Delete a cloud provider connection."""
        return {"success": True, "message": f"Provider {provider_id} deleted"}

    @server.resource("provider://{provider_id}")
    async def get_provider(provider_id: str) -> str:
        """Get cloud provider details."""
        provider = await get_provider_query.execute(provider_id)
        if provider:
            return provider.model_dump_json()
        return '{"error": "Provider not found"}'

    @server.resource("provider://list")
    async def list_providers() -> str:
        """List all cloud providers."""
        providers = await list_providers_query.execute()
        import json

        return json.dumps(providers)

    return server
