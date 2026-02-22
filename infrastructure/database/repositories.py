"""
Database Persistence Layer

Architectural Intent:
- SQLAlchemy-based persistence
- Replaces in-memory repositories
- Follows port/adapter pattern
"""

import os
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Float,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.entities.agent import Agent, AgentConfig, AIProvider, AgentStatus
from domain.ports.repository_ports import (
    CloudProviderRepositoryPort,
    ResourceRepositoryPort,
    AgentRepositoryPort,
)


Base = declarative_base()


class CloudProviderModel(Base):
    __tablename__ = "cloud_providers"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    provider_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    account_id = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class ResourceModel(Base):
    __tablename__ = "resources"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    provider_id = Column(PGUUID(as_uuid=True), nullable=False)
    resource_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    state = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    arn = Column(String(500))
    metadata = Column(JSON, default={})
    tags = Column(JSON, default={})
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    status = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    max_tokens = Column(Integer, default=4096)
    temperature = Column(Float, default=0.7)
    system_prompt = Column(String(10000))
    capabilities = Column(JSON, default=[])
    mcp_tools = Column(JSON, default=[])
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class SQLAlchemyCloudProviderRepository:
    def __init__(self, session: Session):
        self._session = session

    def _to_entity(self, model: CloudProviderModel) -> CloudProvider:
        return CloudProvider(
            id=model.id,
            provider_type=CloudProviderType(model.provider_type),
            name=model.name,
            status=ProviderStatus(model.status),
            region=model.region,
            account_id=model.account_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save(self, provider: CloudProvider) -> CloudProvider:
        model = CloudProviderModel(
            id=provider.id,
            provider_type=provider.provider_type.value,
            name=provider.name,
            status=provider.status.value,
            region=provider.region,
            account_id=provider.account_id,
        )
        self._session.merge(model)
        self._session.commit()
        return provider

    async def get_by_id(self, provider_id: UUID) -> Optional[CloudProvider]:
        model = (
            self._session.query(CloudProviderModel).filter_by(id=provider_id).first()
        )
        return self._to_entity(model) if model else None

    async def get_by_type(
        self, provider_type: CloudProviderType
    ) -> list[CloudProvider]:
        models = (
            self._session.query(CloudProviderModel)
            .filter_by(provider_type=provider_type.value)
            .all()
        )
        return [self._to_entity(m) for m in models]

    async def get_all(self) -> list[CloudProvider]:
        models = self._session.query(CloudProviderModel).all()
        return [self._to_entity(m) for m in models]

    async def delete(self, provider_id: UUID) -> None:
        model = (
            self._session.query(CloudProviderModel).filter_by(id=provider_id).first()
        )
        if model:
            self._session.delete(model)
            self._session.commit()


class SQLAlchemyResourceRepository:
    def __init__(self, session: Session):
        self._session = session

    def _to_entity(self, model: ResourceModel) -> Resource:
        return Resource(
            id=model.id,
            provider_id=model.provider_id,
            resource_type=ResourceType(model.resource_type),
            name=model.name,
            state=ResourceState(model.state),
            region=model.region,
            arn=model.arn,
            metadata=model.metadata or {},
            tags=model.tags or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save(self, resource: Resource) -> Resource:
        model = ResourceModel(
            id=resource.id,
            provider_id=resource.provider_id,
            resource_type=resource.resource_type.value,
            name=resource.name,
            state=resource.state.value,
            region=resource.region,
            arn=resource.arn,
            metadata=resource.metadata,
            tags=resource.tags,
        )
        self._session.merge(model)
        self._session.commit()
        return resource

    async def get_by_id(self, resource_id: UUID) -> Optional[Resource]:
        model = self._session.query(ResourceModel).filter_by(id=resource_id).first()
        return self._to_entity(model) if model else None

    async def get_by_provider(self, provider_id: UUID) -> list[Resource]:
        models = (
            self._session.query(ResourceModel).filter_by(provider_id=provider_id).all()
        )
        return [self._to_entity(m) for m in models]

    async def get_by_type(self, resource_type: ResourceType) -> list[Resource]:
        models = (
            self._session.query(ResourceModel)
            .filter_by(resource_type=resource_type.value)
            .all()
        )
        return [self._to_entity(m) for m in models]

    async def get_by_state(self, state: ResourceState) -> list[Resource]:
        models = self._session.query(ResourceModel).filter_by(state=state.value).all()
        return [self._to_entity(m) for m in models]

    async def get_all(self) -> list[Resource]:
        models = self._session.query(ResourceModel).all()
        return [self._to_entity(m) for m in models]

    async def delete(self, resource_id: UUID) -> None:
        model = self._session.query(ResourceModel).filter_by(id=resource_id).first()
        if model:
            self._session.delete(model)
            self._session.commit()


class SQLAlchemyAgentRepository:
    def __init__(self, session: Session):
        self._session = session

    def _to_entity(self, model: AgentModel) -> Agent:
        return Agent(
            id=model.id,
            name=model.name,
            description=model.description or "",
            status=AgentStatus(model.status),
            config=AgentConfig(
                provider=AIProvider(model.provider),
                model=model.model,
                max_tokens=model.max_tokens,
                temperature=model.temperature,
                system_prompt=model.system_prompt or "",
            ),
            capabilities=tuple(),
            mcp_tools=tuple(model.mcp_tools or []),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save(self, agent: Agent) -> Agent:
        model = AgentModel(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            status=agent.status.value,
            provider=agent.config.provider.value,
            model=agent.config.model,
            max_tokens=agent.config.max_tokens,
            temperature=agent.config.temperature,
            system_prompt=agent.config.system_prompt,
            mcp_tools=list(agent.mcp_tools),
        )
        self._session.merge(model)
        self._session.commit()
        return agent

    async def get_by_id(self, agent_id: UUID) -> Optional[Agent]:
        model = self._session.query(AgentModel).filter_by(id=agent_id).first()
        return self._to_entity(model) if model else None

    async def get_by_status(self, status: str) -> list[Agent]:
        models = self._session.query(AgentModel).filter_by(status=status).all()
        return [self._to_entity(m) for m in models]

    async def get_all(self) -> list[Agent]:
        models = self._session.query(AgentModel).all()
        return [self._to_entity(m) for m in models]

    async def delete(self, agent_id: UUID) -> None:
        model = self._session.query(AgentModel).filter_by(id=agent_id).first()
        if model:
            self._session.delete(model)
            self._session.commit()


def create_engine_from_env():
    database_url = os.environ.get("DATABASE_URL", "sqlite:///cockpit.db")
    return create_engine(
        database_url, echo=os.environ.get("SQL_ECHO", "false") == "true"
    )


def get_session():
    engine = create_engine_from_env()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
