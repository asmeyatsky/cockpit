"""
FastAPI Web Application

Architectural Intent:
- REST API for Cockpit platform
- Follows presentation layer patterns
- WebSocket support for real-time updates
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
import json
import asyncio

from infrastructure.config.dependency_injection import get_container
from presentation.api.controllers import (
    CloudProviderController,
    ResourceController,
    AgentController,
    CostController,
)
from application.services.copilot_service import get_copilot_service


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


class CopilotRequest(BaseModel):
    message: str


@app.post("/api/copilot")
async def copilot_chat(request: CopilotRequest):
    """AI Co-pilot chat endpoint"""
    copilot = get_copilot_service()
    result = await copilot.process_command(request.message)
    return {
        "success": result.success,
        "message": result.message,
        "action_taken": result.action_taken,
        "data": result.data,
    }


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await manager.send_message({"type": "pong"}, websocket)
            elif message.get("type") == "subscribe"):
                event_type = message.get("event")
                await manager.send_message({
                    "type": "subscribed",
                    "event": event_type
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/copilot")
async def copilot_websocket(websocket: WebSocket):
    await websocket.accept()
    manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "message",
            "content": "Hi! I'm your AI infrastructure co-pilot. What would you like to do today?",
            "role": "assistant"
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "message":
                user_input = message.get("content", "")
                
                await websocket.send_json({
                    "type": "typing",
                    "typing": True
                })
                
                copilot = get_copilot_service()
                result = await copilot.process_command(user_input)
                
                await websocket.send_json({
                    "type": "typing",
                    "typing": False
                })
                
                await websocket.send_json({
                    "type": "message",
                    "content": result.message,
                    "role": "assistant",
                    "action_taken": result.action_taken,
                    "data": result.data
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_event(event_type: str, data: dict):
    await manager.broadcast({
        "type": "event",
        "event": event_type,
        "data": data
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
