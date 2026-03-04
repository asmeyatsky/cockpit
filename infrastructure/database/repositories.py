"""
Database Persistence Layer

Architectural Intent:
- SQLAlchemy-based persistence
- Replaces in-memory repositories
- Follows port/adapter pattern
- Uses SQLite for development (no native UUID type → String(36))
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
    Integer,
    DateTime,
    Float,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.entities.agent import Agent, AgentConfig, AIProvider, AgentStatus


class Base(DeclarativeBase):
    pass


class CloudProviderModel(Base):
    __tablename__ = "cloud_providers"

    id = Column(String(36), primary_key=True)
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

    id = Column(String(36), primary_key=True)
    provider_id = Column(String(36), nullable=False)
    resource_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    state = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    arn = Column(String(500))
    metadata_ = Column("metadata", JSON, default={})
    tags = Column(JSON, default={})
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True)
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


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class SQLAlchemyCloudProviderRepository:
    def __init__(self, session: Session):
        self._session = session

    def _to_entity(self, model: CloudProviderModel) -> CloudProvider:
        return CloudProvider(
            id=UUID(model.id),
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
            id=str(provider.id),
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
            self._session.query(CloudProviderModel)
            .filter_by(id=str(provider_id))
            .first()
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
            self._session.query(CloudProviderModel)
            .filter_by(id=str(provider_id))
            .first()
        )
        if model:
            self._session.delete(model)
            self._session.commit()


class SQLAlchemyResourceRepository:
    def __init__(self, session: Session):
        self._session = session

    def _to_entity(self, model: ResourceModel) -> Resource:
        # Convert JSON dicts back to tuples of (key, value) pairs for frozen dataclass
        raw_meta = model.metadata_ or {}
        raw_tags = model.tags or {}
        return Resource(
            id=UUID(model.id),
            provider_id=UUID(model.provider_id),
            resource_type=ResourceType(model.resource_type),
            name=model.name,
            state=ResourceState(model.state),
            region=model.region,
            arn=model.arn,
            metadata=tuple(raw_meta.items()) if isinstance(raw_meta, dict) else tuple(),
            tags=tuple(raw_tags.items()) if isinstance(raw_tags, dict) else tuple(),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save(self, resource: Resource) -> Resource:
        # Convert tuples of (key, value) pairs back to dicts for JSON storage
        meta = dict(resource.metadata) if resource.metadata else {}
        tags = dict(resource.tags) if resource.tags else {}
        model = ResourceModel(
            id=str(resource.id),
            provider_id=str(resource.provider_id),
            resource_type=resource.resource_type.value,
            name=resource.name,
            state=resource.state.value,
            region=resource.region,
            arn=resource.arn,
            metadata_=meta,
            tags=tags,
        )
        self._session.merge(model)
        self._session.commit()
        return resource

    async def get_by_id(self, resource_id: UUID) -> Optional[Resource]:
        model = (
            self._session.query(ResourceModel)
            .filter_by(id=str(resource_id))
            .first()
        )
        return self._to_entity(model) if model else None

    async def get_by_provider(self, provider_id: UUID) -> list[Resource]:
        models = (
            self._session.query(ResourceModel)
            .filter_by(provider_id=str(provider_id))
            .all()
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
        model = (
            self._session.query(ResourceModel)
            .filter_by(id=str(resource_id))
            .first()
        )
        if model:
            self._session.delete(model)
            self._session.commit()


class SQLAlchemyAgentRepository:
    def __init__(self, session: Session):
        self._session = session

    def _to_entity(self, model: AgentModel) -> Agent:
        return Agent(
            id=UUID(model.id),
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
            id=str(agent.id),
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
        model = (
            self._session.query(AgentModel)
            .filter_by(id=str(agent_id))
            .first()
        )
        return self._to_entity(model) if model else None

    async def get_by_status(self, status: str) -> list[Agent]:
        models = self._session.query(AgentModel).filter_by(status=status).all()
        return [self._to_entity(m) for m in models]

    async def get_all(self) -> list[Agent]:
        models = self._session.query(AgentModel).all()
        return [self._to_entity(m) for m in models]

    async def delete(self, agent_id: UUID) -> None:
        model = (
            self._session.query(AgentModel)
            .filter_by(id=str(agent_id))
            .first()
        )
        if model:
            self._session.delete(model)
            self._session.commit()


class SQLAlchemyUserStore:
    """Persists auth users to the database."""

    def __init__(self, session: Session):
        self._session = session

    def get_all_users(self) -> dict[str, dict]:
        """Return all users as {user_id: user_dict}."""
        models = self._session.query(UserModel).all()
        return {m.id: self._to_dict(m) for m in models}

    def save_user(self, user_id: str, username: str, email: str, role: str,
                  hashed_password: str, api_key: str | None = None,
                  created_at: datetime | None = None) -> None:
        model = UserModel(
            id=user_id,
            username=username,
            email=email,
            role=role,
            hashed_password=hashed_password,
            api_key=api_key,
            created_at=created_at or datetime.now(UTC),
        )
        self._session.merge(model)
        self._session.commit()

    def find_by_username(self, username: str) -> dict | None:
        model = self._session.query(UserModel).filter_by(username=username).first()
        return self._to_dict(model) if model else None

    def find_by_api_key(self, api_key: str) -> dict | None:
        model = self._session.query(UserModel).filter_by(api_key=api_key).first()
        return self._to_dict(model) if model else None

    def update_api_key(self, user_id: str, api_key: str) -> None:
        model = self._session.query(UserModel).filter_by(id=user_id).first()
        if model:
            model.api_key = api_key
            self._session.commit()

    def _to_dict(self, model: UserModel) -> dict:
        return {
            "id": model.id,
            "username": model.username,
            "email": model.email,
            "role": model.role,
            "hashed_password": model.hashed_password,
            "api_key": model.api_key,
            "created_at": model.created_at,
        }


def create_engine_from_env():
    database_url = os.environ.get("DATABASE_URL", "sqlite:///cockpit.db")
    return create_engine(
        database_url, echo=os.environ.get("SQL_ECHO", "false") == "true"
    )


def get_session():
    engine = create_engine_from_env()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
