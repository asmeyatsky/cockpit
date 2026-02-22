"""
Resource MCP Server

Architectural Intent:
- Exposes infrastructure resource management via MCP protocol
- Tools = write operations, Resources = read operations

MCP Integration:
- Server name: infrastructure-resource-service
- Tools: create_resource, start_resource, stop_resource, terminate_resource
- Resources: resource://{resource_id}, resource://list
"""

from mcp.server import Server
from mcp.types import Tool, Resource
from pydantic import BaseModel
from typing import Optional

from application.commands.commands import (
    CreateResourceUseCase,
    ManageResourceUseCase,
)
from application.queries.queries import (
    GetResourceQuery,
    ListResourcesQuery,
)


class CreateResourceInput(BaseModel):
    provider_id: str
    resource_type: str
    name: str
    region: str
    config: dict = {}
    tags: Optional[dict] = None


def create_resource_server(
    create_resource_use_case: CreateResourceUseCase,
    manage_resource_use_case: ManageResourceUseCase,
    get_resource_query: GetResourceQuery,
    list_resources_query: ListResourcesQuery,
) -> Server:
    server = Server("infrastructure-resource-service")

    @server.tool()
    async def create_resource(input: CreateResourceInput) -> dict:
        """Create a new infrastructure resource."""
        result = await create_resource_use_case.execute(
            provider_id=input.provider_id,
            resource_type=input.resource_type,
            name=input.name,
            region=input.region,
            config=input.config,
            tags=input.tags,
        )

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.tool()
    async def start_resource(resource_id: str) -> dict:
        """Start a stopped resource."""
        result = await manage_resource_use_case.start(resource_id)

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.tool()
    async def stop_resource(resource_id: str) -> dict:
        """Stop a running resource."""
        result = await manage_resource_use_case.stop(resource_id)

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.tool()
    async def terminate_resource(resource_id: str) -> dict:
        """Terminate a resource."""
        result = await manage_resource_use_case.terminate(resource_id)

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.resource("resource://{resource_id}")
    async def get_resource(resource_id: str) -> str:
        """Get resource details."""
        resource = await get_resource_query.execute(resource_id)
        if resource:
            return resource.model_dump_json()
        return '{"error": "Resource not found"}'

    @server.resource("resource://list")
    async def list_resources(
        provider_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        """List resources with optional filters."""
        resources = await list_resources_query.execute(
            provider_id=provider_id,
            resource_type=resource_type,
            state=state,
        )
        import json

        return json.dumps(resources)

    return server
