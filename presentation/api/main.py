"""
FastAPI Web Application

Architectural Intent:
- REST API for Cockpit platform
- Follows presentation layer patterns
- WebSocket support for real-time updates
- JWT authentication enforced on all /api endpoints
- CORS restricted to configured origins
"""

import os
import logging
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, constr
from typing import Optional
from uuid import UUID
import json
import asyncio

from infrastructure.config.dependency_injection import get_container
from infrastructure.auth import get_auth_service, get_authorization_service, TokenData, Permission
from presentation.api.controllers import (
    CloudProviderController,
    ResourceController,
    AgentController,
    CostController,
)
from application.services.copilot_service import get_copilot_service

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cockpit API",
    description="Agentic Cloud Modernization Platform",
    version="1.0.0",
)


@app.on_event("startup")
async def create_default_admin():
    """Create a default admin user for development."""
    from infrastructure.auth import Role
    auth = get_auth_service()
    if not auth._users:
        auth.create_user("admin", "admin@cockpit.local", "admin", role=Role.ADMIN)
        logger.info("Created default admin user (admin/admin) — change in production!")

# 3.3: CORS — restricted to configured origins (defaults to localhost dev)
ALLOWED_ORIGINS = os.environ.get(
    "COCKPIT_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3005"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# 3.6: Simple in-memory rate limiter
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 120  # per window


async def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _rate_limit_store[client_ip].append(now)


# 3.2: Auth dependency
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenData]:
    """Extract and validate JWT token. Returns None for unauthenticated requests."""
    if not credentials:
        return None
    auth_service = get_auth_service()
    token_data = auth_service.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token_data


async def require_auth(
    user: Optional[TokenData] = Depends(get_current_user),
) -> TokenData:
    """Require a valid authenticated user. Use as dependency on protected endpoints."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# --- Controller factories ---

def get_provider_controller() -> CloudProviderController:
    container = get_container()
    return CloudProviderController(
        create_provider_use_case=container.create_cloud_provider_use_case(),
        connect_provider_use_case=container.create_connect_provider_use_case(),
        disconnect_provider_use_case=container.create_disconnect_provider_use_case(),
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
        activate_agent_use_case=container.create_activate_agent_use_case(),
        deactivate_agent_use_case=container.create_deactivate_agent_use_case(),
        get_agent_query=container.get_agent_query(),
        list_agents_query=container.list_agents_query(),
    )


def get_cost_controller() -> CostController:
    container = get_container()
    return CostController(
        analyze_cost_use_case=container.create_cost_analysis_use_case()
    )


# --- Request Models (with validation) ---

class CreateProviderRequest(BaseModel):
    provider_type: constr(pattern=r"^(aws|azure|gcp)$")
    name: constr(min_length=1, max_length=100)
    region: constr(min_length=1, max_length=50)
    account_id: Optional[str] = None


class CreateResourceRequest(BaseModel):
    provider_id: str
    resource_type: str
    name: constr(min_length=1, max_length=100)
    region: constr(min_length=1, max_length=50)
    config: dict = {}
    tags: Optional[dict] = None


class CreateAgentRequest(BaseModel):
    name: constr(min_length=1, max_length=100)
    description: constr(max_length=500)
    provider: str
    model: str
    system_prompt: constr(max_length=10000)
    max_tokens: int = Field(default=4096, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class CopilotRequest(BaseModel):
    message: constr(min_length=1, max_length=5000)


# --- Public endpoints ---

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


# --- Auth endpoints ---

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    auth_service = get_auth_service()
    user = auth_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_service.create_token(user)
    return {"token": token, "user": {"id": user.id, "username": user.username, "role": user.role.value}}


# --- Protected API endpoints ---

@app.post("/api/providers", dependencies=[Depends(rate_limit)])
async def create_provider(
    request: CreateProviderRequest,
    user: TokenData = Depends(require_auth),
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


@app.get("/api/providers", dependencies=[Depends(rate_limit)])
async def list_providers(
    user: TokenData = Depends(require_auth),
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.list()
    return result.data


@app.get("/api/providers/{provider_id}", dependencies=[Depends(rate_limit)])
async def get_provider(
    provider_id: str,
    user: TokenData = Depends(require_auth),
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.get(provider_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@app.post("/api/providers/{provider_id}/connect", dependencies=[Depends(rate_limit)])
async def connect_provider(
    provider_id: str,
    user: TokenData = Depends(require_auth),
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.connect(provider_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/providers/{provider_id}/disconnect", dependencies=[Depends(rate_limit)])
async def disconnect_provider(
    provider_id: str,
    user: TokenData = Depends(require_auth),
    controller: CloudProviderController = Depends(get_provider_controller),
):
    result = await controller.disconnect(provider_id)
    return result.data


@app.post("/api/resources", dependencies=[Depends(rate_limit)])
async def create_resource(
    request: CreateResourceRequest,
    user: TokenData = Depends(require_auth),
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


@app.get("/api/resources", dependencies=[Depends(rate_limit)])
async def list_resources(
    provider_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    state: Optional[str] = None,
    user: TokenData = Depends(require_auth),
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.list(provider_id, resource_type, state)
    return result.data


@app.get("/api/resources/{resource_id}", dependencies=[Depends(rate_limit)])
async def get_resource(
    resource_id: str,
    user: TokenData = Depends(require_auth),
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.get(resource_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@app.post("/api/resources/{resource_id}/start", dependencies=[Depends(rate_limit)])
async def start_resource(
    resource_id: str,
    user: TokenData = Depends(require_auth),
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.start(resource_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/resources/{resource_id}/stop", dependencies=[Depends(rate_limit)])
async def stop_resource(
    resource_id: str,
    user: TokenData = Depends(require_auth),
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.stop(resource_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/resources/{resource_id}/terminate", dependencies=[Depends(rate_limit)])
async def terminate_resource(
    resource_id: str,
    user: TokenData = Depends(require_auth),
    controller: ResourceController = Depends(get_resource_controller),
):
    result = await controller.terminate(resource_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/agents", dependencies=[Depends(rate_limit)])
async def create_agent(
    request: CreateAgentRequest,
    user: TokenData = Depends(require_auth),
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


@app.get("/api/agents", dependencies=[Depends(rate_limit)])
async def list_agents(
    user: TokenData = Depends(require_auth),
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.list()
    return result.data


@app.get("/api/agents/{agent_id}", dependencies=[Depends(rate_limit)])
async def get_agent(
    agent_id: str,
    user: TokenData = Depends(require_auth),
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.get(agent_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@app.post("/api/agents/{agent_id}/activate", dependencies=[Depends(rate_limit)])
async def activate_agent(
    agent_id: str,
    user: TokenData = Depends(require_auth),
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.activate(agent_id)
    return result.data


@app.post("/api/agents/{agent_id}/deactivate", dependencies=[Depends(rate_limit)])
async def deactivate_agent(
    agent_id: str,
    user: TokenData = Depends(require_auth),
    controller: AgentController = Depends(get_agent_controller),
):
    result = await controller.deactivate(agent_id)
    return result.data


@app.get("/api/costs/{provider_id}", dependencies=[Depends(rate_limit)])
async def analyze_costs(
    provider_id: str,
    user: TokenData = Depends(require_auth),
    controller: CostController = Depends(get_cost_controller),
):
    result = await controller.analyze(provider_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@app.post("/api/copilot", dependencies=[Depends(rate_limit)])
async def copilot_chat(
    request: CopilotRequest,
    user: TokenData = Depends(require_auth),
):
    """AI Co-pilot chat endpoint"""
    copilot = get_copilot_service(container=get_container())
    result = await copilot.process_command(request.message)
    return {
        "success": result.success,
        "message": result.message,
        "action_taken": result.action_taken,
        "data": result.data,
    }


# --- WebSocket ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


def _parse_ws_message(data: str) -> Optional[dict]:
    """3.11: Safely parse and validate WebSocket JSON."""
    try:
        message = json.loads(data)
        if not isinstance(message, dict):
            return None
        return message
    except (json.JSONDecodeError, TypeError):
        return None


async def _authenticate_ws(websocket: WebSocket) -> Optional[TokenData]:
    """3.4: Authenticate WebSocket via query param token."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return None
    auth_service = get_auth_service()
    token_data = auth_service.verify_token(token)
    if not token_data:
        await websocket.close(code=4001, reason="Invalid token")
        return None
    return token_data


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user = await _authenticate_ws(websocket)
    if not user:
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = _parse_ws_message(data)
            if not message:
                await manager.send_message({"type": "error", "detail": "Invalid JSON"}, websocket)
                continue

            if message.get("type") == "ping":
                await manager.send_message({"type": "pong"}, websocket)
            elif message.get("type") == "subscribe":
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
    user = await _authenticate_ws(websocket)
    if not user:
        return
    await manager.connect(websocket)

    try:
        await websocket.send_json({
            "type": "message",
            "content": "Hi! I'm your AI infrastructure co-pilot. What would you like to do today?",
            "role": "assistant"
        })

        while True:
            data = await websocket.receive_text()
            message = _parse_ws_message(data)
            if not message:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            if message.get("type") == "message":
                user_input = message.get("content", "").strip()
                if not user_input or len(user_input) > 5000:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "Message must be 1-5000 characters"
                    })
                    continue

                await websocket.send_json({
                    "type": "typing",
                    "typing": True
                })

                # 2.13: Pass conversation history for context
                history = message.get("history", [])
                copilot = get_copilot_service(container=get_container())
                result = await copilot.process_command(user_input, history=history)

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
