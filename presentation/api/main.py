"""
FastAPI Web Application

Architectural Intent:
- REST API for Cockpit platform
- Follows presentation layer patterns
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from infrastructure.config.dependency_injection import get_container
from presentation.api.controllers import (
    CloudProviderController,
    ResourceController,
    AgentController,
    CostController,
)


app = FastAPI(
    title="Cockpit API",
    description="Agentic Cloud Modernization Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_provider_controller() -> CloudProviderController:
    container = get_container()
    return CloudProviderController(
        create_provider_use_case=container.create_cloud_provider_use_case(),
        connect_provider_use_case=container.create_connect_provider_use_case(),
        get_provider_query=container.get_cloud_provider_query(),
        list_providers_query=container.list_cloud_providers_query(),
    )


def get_resource_controller() -> ResourceController:
    container = get_container()
    return ResourceController(
        create_resource_use_case=container.create_resource_use_case(),
        manage_resource_use_case=container.create_manage_resource_use_case(),
        get_resource_query=container.get_resource_query(),
        list_resources_query=container.list_resources_query(),
    )


def get_agent_controller() -> AgentController:
    container = get_container()
    return AgentController(
        create_agent_use_case=container.create_agent_use_case(),
        get_agent_query=container.get_agent_query(),
        list_agents_query=container.list_agents_query(),
    )


def get_cost_controller() -> CostController:
    container = get_container()
    return CostController(
        analyze_cost_use_case=container.create_cost_analysis_use_case()
    )


class CreateProviderRequest(BaseModel):
    provider_type: str
    name: str
    region: str
    account_id: Optional[str] = None


class CreateResourceRequest(BaseModel):
    provider_id: str
    resource_type: str
    name: str
    region: str
    config: dict = {}
    tags: Optional[dict] = None


class CreateAgentRequest(BaseModel):
    name: str
    description: str
    provider: str
    model: str
    system_prompt: str
    max_tokens: int = 4096
    temperature: float = 0.7


@app.get("/")
async def root():
    return {
        "name": "Cockpit API",
        "version": "1.0.0",
        "description": "Agentic Cloud Modernization Platform",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/providers")
async def create_provider(
    request: CreateProviderRequest,
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.create(
        provider_type=request.provider_type,
        name=request.name,
        region=request.region,
        account_id=request.account_id,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.get("/api/providers")
async def list_providers(
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.list()
    return result.data


@app.get("/api/providers/{provider_id}")
async def get_provider(
    provider_id: str,
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.get(provider_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@app.post("/api/providers/{provider_id}/connect")
async def connect_provider(
    provider_id: str,
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.connect(provider_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/providers/{provider_id}/disconnect")
async def disconnect_provider(
    provider_id: str,
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.disconnect(provider_id)
    return result.data


@app.post("/api/resources")
async def create_resource(
    request: CreateResourceRequest,
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.create(
        provider_id=request.provider_id,
        resource_type=request.resource_type,
        name=request.name,
        region=request.region,
        config=request.config,
        tags=request.tags,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.get("/api/resources")
async def list_resources(
    provider_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    state: Optional[str] = None,
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.list(provider_id, resource_type, state)
    return result.data


@app.get("/api/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.get(resource_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@app.post("/api/resources/{resource_id}/start")
async def start_resource(
    resource_id: str,
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.start(resource_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/resources/{resource_id}/stop")
async def stop_resource(
    resource_id: str,
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.stop(resource_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/resources/{resource_id}/terminate")
async def terminate_resource(
    resource_id: str,
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.terminate(resource_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/agents")
async def create_agent(
    request: CreateAgentRequest,
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.create(
        name=request.name,
        description=request.description,
        provider=request.provider,
        model=request.model,
        system_prompt=request.system_prompt,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.get("/api/agents")
async def list_agents(controller: AgentController = Depends(get_agent_controller)):
    result = await controller.list()
    return result.data


@app.get("/api/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.get(agent_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@app.post("/api/agents/{agent_id}/activate")
async def activate_agent(
    agent_id: str,
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.activate(agent_id)
    return result.data


@app.post("/api/agents/{agent_id}/deactivate")
async def deactivate_agent(
    agent_id: str,
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.deactivate(agent_id)
    return result.data


@app.get("/api/costs/{provider_id}")
async def analyze_costs(
    provider_id: str,
    controller: CostController = Depends(get_cost_controller),
):
    result = await controller.analyze(provider_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
