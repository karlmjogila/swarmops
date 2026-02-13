---
name: python-backend
description: >
  Build production-grade Python backend services with modern async patterns, strict typing,
  Pydantic validation, FastAPI, SQLAlchemy, Celery task queues, Redis, Alembic migrations,
  proper error handling, and clean architecture. Trigger this skill for any task involving
  Python server-side code, FastAPI endpoints, Pydantic models, async operations, background
  tasks, database access, task queues, or Python service architecture.
triggers:
  - python
  - fastapi
  - pydantic
  - asyncio
  - pytest
  - uvicorn
  - flask
  - django
  - pip
  - poetry
  - uv
  - venv
  - virtualenv
  - celery
  - httpx
  - sqlalchemy
  - alembic
  - background task
  - task queue
---

# Python Backend Excellence

Write Python that is idiomatic, typed, and production-ready. Python's strength is clarity -- lean into it. Use `async` for I/O, type hints for safety, Pydantic for validation, and keep your code so readable that documentation is almost redundant. Every service should be stateless, disposable, and configured entirely through environment variables.

## Core Principles

1. **Type everything** -- Use type hints on every function signature, every class attribute, every variable where the type isn't obvious. `Any` is a bug.
2. **Validate at the boundary** -- Every external input (HTTP request, file, environment variable, API response) goes through Pydantic before touching your business logic.
3. **Async for I/O, sync for CPU** -- `async`/`await` for network and disk. Plain functions for computation. Never block the event loop.
4. **Dependencies in, not hardcoded** -- Declare all dependencies in `pyproject.toml` with pinned versions and a lockfile. Never `pip install` ad hoc in production.
5. **Stateless processes** -- Store nothing in-process between requests. Sessions, caches, and queues belong in external stores (Redis, PostgreSQL, S3).

## Project Structure

```
project/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point + lifespan
│       ├── config.py            # Settings via pydantic-settings
│       ├── dependencies.py      # FastAPI dependency injection
│       ├── db.py                # SQLAlchemy engine + session factory
│       ├── models/              # Pydantic models (request/response)
│       │   ├── __init__.py
│       │   └── order.py
│       ├── entities/            # SQLAlchemy ORM models
│       │   ├── __init__.py
│       │   └── order.py
│       ├── services/            # Business logic (no framework deps)
│       │   ├── __init__.py
│       │   └── order_service.py
│       ├── repositories/        # Data access layer
│       │   ├── __init__.py
│       │   └── order_repo.py
│       ├── api/                 # Route handlers
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── orders.py
│       ├── tasks/               # Celery task definitions
│       │   ├── __init__.py
│       │   └── order_tasks.py
│       ├── cache.py             # Redis client + cache utilities
│       └── utils/
│           ├── __init__.py
│           └── logging.py
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── pyproject.toml               # Single source for deps, tools, metadata
├── uv.lock                      # Pinned lockfile (or poetry.lock)
├── Dockerfile
└── .env.example
```

## Configuration

### Type-Safe Settings with pydantic-settings
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Required -- app won't start without these
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    api_key: SecretStr

    # Optional with defaults
    debug: bool = False
    port: int = Field(default=8000, ge=1024, le=65535)
    log_level: str = Field(default="info", pattern=r"^(debug|info|warning|error)$")
    max_workers: int = Field(default=4, ge=1, le=32)

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Database pool
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_pool_overflow: int = Field(default=20, ge=0, le=100)

    @property
    def is_production(self) -> bool:
        return not self.debug

    @property
    def async_database_url(self) -> str:
        """Convert postgres:// to postgresql+asyncpg:// for async driver."""
        return self.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )


# Singleton -- load once at startup
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

## Pydantic Models -- The Contract

### Request/Response Models
```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"


# Request model -- strict validation
class CreateOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9_-]+$")
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(..., gt=0)
    price: float | None = Field(default=None, gt=0)

    @field_validator("price")
    @classmethod
    def price_required_for_limit(cls, v: float | None, info) -> float | None:
        if info.data.get("order_type") == OrderType.LIMIT and v is None:
            raise ValueError("Price is required for limit orders")
        return v


# Response model -- controlled output
class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: OrderSide
    status: str
    quantity: float
    price: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Use separate models for create vs response -- never expose internals
```

### Discriminated Unions for Complex Types
```python
from typing import Literal, Annotated
from pydantic import Discriminator


class LimitOrder(BaseModel):
    type: Literal["limit"]
    price: float = Field(gt=0)
    time_in_force: str = "gtc"


class MarketOrder(BaseModel):
    type: Literal["market"]
    slippage_tolerance: float = Field(default=0.01, ge=0, le=0.1)


class StopOrder(BaseModel):
    type: Literal["stop"]
    trigger_price: float = Field(gt=0)
    limit_price: float | None = None


OrderParams = Annotated[
    LimitOrder | MarketOrder | StopOrder,
    Discriminator("type"),
]
```

## Async Database Patterns (SQLAlchemy)

### Engine and Session Factory
```python
# db.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from myapp.config import get_settings


class Base(DeclarativeBase):
    pass


def create_engine():
    settings = get_settings()
    return create_async_engine(
        settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_overflow,
        pool_pre_ping=True,        # Detect stale connections
        pool_recycle=300,           # Recycle connections every 5 min
        echo=settings.debug,
    )


engine = create_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

### ORM Entity
```python
# entities/order.py
import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from myapp.db import Base


class OrderEntity(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[str] = mapped_column(String(4))
    order_type: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Repository Pattern
```python
# repositories/order_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from myapp.entities.order import OrderEntity


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, order_id: str) -> OrderEntity | None:
        result = await self._session.execute(
            select(OrderEntity).where(OrderEntity.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_by_symbol(
        self, symbol: str, *, limit: int = 50
    ) -> list[OrderEntity]:
        result = await self._session.execute(
            select(OrderEntity)
            .where(OrderEntity.symbol == symbol)
            .order_by(OrderEntity.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: OrderEntity) -> OrderEntity:
        self._session.add(entity)
        await self._session.flush()
        return entity
```

### Transaction Context Manager
```python
# dependencies.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from myapp.db import async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session that commits on success, rolls back on error."""
    async with async_session_factory() as session:
        async with session.begin():
            yield session
            # Commits automatically if no exception; rolls back otherwise
```

## Async Patterns

### async/await -- The Default for I/O
```python
import httpx
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator


# Use httpx for async HTTP (not requests -- it's synchronous)
@asynccontextmanager
async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


async def fetch_market_data(symbol: str) -> dict:
    async with get_http_client() as client:
        response = await client.get(
            f"https://api.exchange.com/v1/ticker/{symbol}"
        )
        response.raise_for_status()
        return response.json()


# Parallel execution for independent operations
import asyncio


async def load_dashboard(user_id: str) -> dict:
    positions, orders, balance = await asyncio.gather(
        fetch_positions(user_id),
        fetch_open_orders(user_id),
        fetch_balance(user_id),
    )
    return {"positions": positions, "orders": orders, "balance": balance}
```

### Concurrency Control
```python
import asyncio


class RateLimiter:
    """Limit concurrent operations and requests per second."""

    def __init__(self, max_concurrent: int = 5, requests_per_second: float = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._rate = 1.0 / requests_per_second
        self._last_request = 0.0

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        now = asyncio.get_event_loop().time()
        wait = self._rate - (now - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request = asyncio.get_event_loop().time()

    def release(self) -> None:
        self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *exc):
        self.release()


# Usage
rate_limiter = RateLimiter(max_concurrent=5, requests_per_second=10)

async def call_api(endpoint: str) -> dict:
    async with rate_limiter:
        async with get_http_client() as client:
            response = await client.get(endpoint)
            return response.json()
```

## Background Tasks and Graceful Shutdown

### FastAPI Lifespan -- Startup and Teardown
```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
import asyncio

from myapp.db import engine
from myapp.cache import redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- Startup: initialize shared resources ---
    app.state.redis = redis_pool
    periodic_task = asyncio.create_task(
        run_periodic("position_check", check_positions, interval_seconds=60)
    )

    yield  # App runs here

    # --- Shutdown: clean up everything ---
    periodic_task.cancel()
    try:
        await periodic_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    await redis_pool.aclose()


app = FastAPI(lifespan=lifespan)
```

### Fire-and-Forget with BackgroundTasks
```python
from fastapi import BackgroundTasks


async def send_order_confirmation(order_id: str, email: str) -> None:
    """Quick, non-critical work. If it fails, log and move on."""
    try:
        async with get_http_client() as client:
            await client.post(
                "https://email.internal/send",
                json={"to": email, "template": "order_confirm", "order_id": order_id},
            )
    except Exception:
        logger.error("Failed to send confirmation", order_id=order_id, email=email)


@router.post("/orders/", status_code=201)
async def create_order(
    request: CreateOrderRequest,
    background_tasks: BackgroundTasks,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = await service.create(request)
    # Fire-and-forget -- does not block the response
    background_tasks.add_task(send_order_confirmation, order.id, order.user_email)
    return OrderResponse.model_validate(order)
```

### Periodic Runner with Cancellation
```python
async def run_periodic(
    name: str,
    fn,
    interval_seconds: float,
) -> None:
    """Run an async function periodically. Respects cancellation for clean shutdown."""
    while True:
        try:
            await fn()
        except asyncio.CancelledError:
            raise  # Always re-raise -- this is how lifespan stops us
        except Exception as e:
            logger.error(f"[{name}] Error", error=str(e))
        await asyncio.sleep(interval_seconds)
```

## Celery Task Queues

### Worker Configuration
```python
# tasks/__init__.py
from celery import Celery
from myapp.config import get_settings

settings = get_settings()

celery_app = Celery(
    "myapp",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,               # Ack after completion, not receipt
    worker_prefetch_multiplier=1,       # One task at a time per worker
    task_reject_on_worker_lost=True,    # Re-queue if worker dies
    result_expires=3600,                # Expire results after 1 hour
)
```

### Task Definition with Retries
```python
# tasks/order_tasks.py
from myapp.tasks import celery_app
from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    max_retries=5,
    retry_backoff=True,           # Exponential: 1s, 2s, 4s, 8s, 16s
    retry_backoff_max=300,        # Cap at 5 minutes
    retry_jitter=True,            # Add randomness to prevent thundering herd
)
def settle_order(self, order_id: str) -> dict:
    """Settle an order with the exchange. Retries on transient failures."""
    try:
        result = exchange_client.settle(order_id)
        return {"order_id": order_id, "status": result.status}
    except PermanentError:
        # Don't retry -- this will never succeed
        return {"order_id": order_id, "status": "failed", "permanent": True}


@shared_task
def generate_daily_report(date_str: str) -> str:
    """Long-running report generation -- offload from the web process."""
    report = build_report(date_str)
    upload_to_s3(report)
    return report.url
```

### Task Chaining and Groups
```python
from celery import chain, group, chord


# Sequential pipeline: validate -> settle -> notify
pipeline = chain(
    validate_order.s(order_id),
    settle_order.s(),
    send_notification.s(user_email),
)
pipeline.apply_async()

# Parallel fan-out: settle multiple orders, then summarize
batch = chord(
    group(settle_order.s(oid) for oid in order_ids),
    summarize_settlements.s(),
)
batch.apply_async()
```

## Redis Integration

### Connection Pool and Client
```python
# cache.py
import redis.asyncio as redis
from myapp.config import get_settings


settings = get_settings()

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    decode_responses=True,
)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)
```

### Cache-Aside Pattern
```python
import json
from myapp.cache import get_redis

CACHE_TTL = 300  # 5 minutes


async def get_order_cached(order_id: str) -> OrderResponse | None:
    """Check cache first, fall back to DB, populate cache on miss."""
    r = get_redis()
    cache_key = f"order:{order_id}"

    # 1. Try cache
    cached = await r.get(cache_key)
    if cached is not None:
        return OrderResponse.model_validate_json(cached)

    # 2. Cache miss -- hit the database
    order = await order_repo.get_by_id(order_id)
    if order is None:
        return None

    # 3. Populate cache
    response = OrderResponse.model_validate(order)
    await r.setex(cache_key, CACHE_TTL, response.model_dump_json())
    return response


async def invalidate_order_cache(order_id: str) -> None:
    r = get_redis()
    await r.delete(f"order:{order_id}")
```

### Pub/Sub for Real-Time Events
```python
async def publish_order_event(event_type: str, order_id: str, data: dict) -> None:
    r = get_redis()
    message = json.dumps({"type": event_type, "order_id": order_id, **data})
    await r.publish("orders:events", message)


async def subscribe_order_events():
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("orders:events")
    async for message in pubsub.listen():
        if message["type"] == "message":
            event = json.loads(message["data"])
            await handle_order_event(event)
```

### Sorted Sets for Leaderboards / Rate Limiting
```python
async def record_request(user_id: str, window_seconds: int = 60) -> bool:
    """Sliding-window rate limiter using sorted sets. Returns True if allowed."""
    import time

    r = get_redis()
    key = f"ratelimit:{user_id}"
    now = time.time()
    window_start = now - window_seconds

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)   # Prune old entries
    pipe.zcard(key)                                 # Count current window
    pipe.zadd(key, {str(now): now})                 # Add this request
    pipe.expire(key, window_seconds)                # Auto-cleanup
    results = await pipe.execute()

    current_count = results[1]
    return current_count < 100  # 100 requests per window
```

## Alembic Migrations

### Setup
```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio

from myapp.db import Base
from myapp.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all entities so Base.metadata sees them
import myapp.entities.order  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live database connection."""
    settings = get_settings()
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    settings = get_settings()
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.async_database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Common Alembic Commands
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add orders table"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

### Manual Migration for Data Changes
```python
# alembic/versions/002_backfill_order_status.py
"""Backfill order status for legacy rows."""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"


def upgrade() -> None:
    # Data migration -- update rows, don't just change schema
    op.execute(
        sa.text("UPDATE orders SET status = 'completed' WHERE status IS NULL")
    )


def downgrade() -> None:
    pass  # Data backfills are not reversible
```

### CI Integration
```yaml
# Run migrations before deploying the new app version
# .github/workflows/deploy.yml (excerpt)
- name: Run database migrations
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: alembic upgrade head

- name: Deploy application
  run: kubectl rollout restart deployment/myapp
```

## FastAPI Patterns

### Route Handlers
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> OrderResponse:
    """Create a new order."""
    repo = OrderRepository(session)
    service = OrderService(repo, settings)
    order = await service.create(request)
    return OrderResponse.model_validate(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    """Get an order by ID."""
    repo = OrderRepository(session)
    order = await repo.get_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse.model_validate(order)
```

### Dependency Injection
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from myapp.dependencies import get_db_session
from myapp.config import get_settings, Settings


async def get_order_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> OrderService:
    repo = OrderRepository(session)
    return OrderService(repo, settings)
```

## Error Handling

### Custom Exception Hierarchy
```python
class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(AppError):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} '{identifier}' not found",
            code="NOT_FOUND",
        )


class ExchangeError(AppError):
    def __init__(self, message: str, exchange: str):
        super().__init__(message, code="EXCHANGE_ERROR")
        self.exchange = exchange
```

### Global Exception Handler
```python
from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_map = {
        "VALIDATION_ERROR": 400,
        "NOT_FOUND": 404,
        "EXCHANGE_ERROR": 502,
    }
    return JSONResponse(
        status_code=status_map.get(exc.code, 500),
        content={"error": {"code": exc.code, "message": exc.message}},
    )
```

## Testing with pytest

### TDD Workflow -- Test First, Then Implement

Write the test before the implementation. Here is a concrete example: adding a `cancel_order` method to the service layer.

**Step 1: Write the failing test.**
```python
# tests/unit/test_order_service.py
import pytest
from unittest.mock import AsyncMock
from myapp.services.order_service import OrderService
from myapp.errors import NotFoundError


@pytest.mark.asyncio
async def test_cancel_order_sets_status_cancelled():
    """An open order should transition to cancelled and persist."""
    repo = AsyncMock()
    repo.get_by_id.return_value = make_order(status="open")
    service = OrderService(repo)

    result = await service.cancel_order("order-1")

    assert result.status == "cancelled"
    repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_order_raises_when_not_found():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = OrderService(repo)

    with pytest.raises(NotFoundError):
        await service.cancel_order("nonexistent")


@pytest.mark.asyncio
async def test_cancel_order_rejects_already_filled():
    repo = AsyncMock()
    repo.get_by_id.return_value = make_order(status="filled")
    service = OrderService(repo)

    with pytest.raises(ValueError, match="Cannot cancel a filled order"):
        await service.cancel_order("order-1")
```

**Step 2: Run tests -- they fail (Red).**

**Step 3: Write the minimal implementation to pass.**
```python
# services/order_service.py
from myapp.errors import NotFoundError


class OrderService:
    def __init__(self, repo) -> None:
        self._repo = repo

    async def cancel_order(self, order_id: str):
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        if order.status == "filled":
            raise ValueError("Cannot cancel a filled order")
        order.status = "cancelled"
        await self._repo.update(order)
        return order
```

**Step 4: Run tests -- they pass (Green). Refactor if needed.**

### Async Test Setup
```python
# conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from myapp.main import app
from myapp.db import Base
from myapp.dependencies import get_db_session


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db_session] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def make_order():
    """Factory fixture for creating test orders."""
    from myapp.entities.order import OrderEntity

    def _make(**overrides) -> OrderEntity:
        defaults = {
            "id": "order-1",
            "symbol": "BTC-USD",
            "side": "buy",
            "order_type": "limit",
            "quantity": 1.0,
            "price": 50000.0,
            "status": "open",
        }
        defaults.update(overrides)
        return OrderEntity(**defaults)

    return _make
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_create_order_e2e(client: AsyncClient):
    response = await client.post("/api/v1/orders/", json={
        "symbol": "BTC-USD",
        "side": "buy",
        "order_type": "limit",
        "quantity": 0.1,
        "price": 50000.0,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "BTC-USD"
    assert data["side"] == "buy"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_order_validates_price(client: AsyncClient):
    response = await client.post("/api/v1/orders/", json={
        "symbol": "BTC-USD",
        "side": "buy",
        "order_type": "limit",
        "quantity": 0.1,
        # Missing price for limit order
    })
    assert response.status_code == 422
```

### Parametrized Tests
```python
@pytest.mark.parametrize("side,expected", [
    ("buy", 1),
    ("sell", -1),
])
def test_side_to_sign(side: str, expected: int):
    assert side_to_sign(OrderSide(side)) == expected


@pytest.mark.parametrize("symbol,valid", [
    ("BTC-USD", True),
    ("ETH-USD", True),
    ("", False),
    ("invalid symbol!", False),
    ("A" * 21, False),
])
def test_symbol_validation(symbol: str, valid: bool):
    if valid:
        CreateOrderRequest(symbol=symbol, side="buy", order_type="market", quantity=1)
    else:
        with pytest.raises(Exception):
            CreateOrderRequest(symbol=symbol, side="buy", order_type="market", quantity=1)
```

## Logging

### Structured Logging with structlog
```python
import structlog
import logging


def setup_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog for structured, machine-readable logs."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[*shared_processors, renderer],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper()))


# Usage -- bound context follows the logger instance
logger = structlog.get_logger("order_service")
log = logger.bind(service="orders")
log.info("Order created", order_id="123", symbol="BTC-USD")
# => {"event": "Order created", "order_id": "123", "symbol": "BTC-USD",
#     "level": "info", "timestamp": "2025-...", "service": "orders"}
```

## Quality Checklist

- [ ] All functions have type hints (parameters and return types)
- [ ] No `Any` types -- use specific types or generics
- [ ] All external input validated via Pydantic models
- [ ] Async used for I/O, sync for CPU-bound work
- [ ] Settings loaded via pydantic-settings (not raw `os.environ`)
- [ ] Custom exception hierarchy (not bare `Exception`)
- [ ] Tests written before implementation (TDD red-green-refactor)
- [ ] Tests use pytest with async support and factory fixtures
- [ ] No blocking I/O in async functions (no `requests`, use `httpx`)
- [ ] Dependencies injected via FastAPI `Depends` (not imported globals)
- [ ] Structured logging (JSON format for production)
- [ ] Graceful shutdown via `lifespan` context manager
- [ ] Secrets use `SecretStr` (not plain strings)
- [ ] Database sessions scoped per request via `async_sessionmaker`
- [ ] Alembic migrations run in CI before deployment
- [ ] Celery tasks use `autoretry_for` with backoff for transient errors
- [ ] Redis cache has TTLs -- no unbounded key growth
- [ ] All dependencies in `pyproject.toml` with pinned versions and a lockfile
- [ ] App is stateless -- no in-process state between requests

## Anti-Patterns

```
BAD:  import requests                        # Blocks the event loop in async code
GOOD: import httpx                           # Use httpx.AsyncClient instead

BAD:  os.environ.get("DB_URL")              # Scattered, unvalidated, untyped
GOOD: settings.database_url                  # Centralized via pydantic-settings

BAD:  except: pass                           # Swallows every error silently
GOOD: except ConnectionError as e: log(e)    # Catch specific, log always

BAD:  def create(data: dict) -> dict         # No types, no validation, no safety
GOOD: def create(req: CreateOrderRequest)    # Pydantic validates before you touch it

BAD:  @router.post("/") ... do_business()    # Business logic in the handler
GOOD: service = OrderService(repo); ...      # Handlers delegate to services

BAD:  from typing import List, Dict, Optional  # Python 3.9 style
GOOD: list[str], dict[str, int], str | None    # Python 3.10+ built-ins

BAD:  def f(items=[])                        # Mutable default -- shared across calls
GOOD: def f(items: list[str] | None = None)  # None sentinel, create inside

BAD:  session = Session()  # module-level    # One session for entire process
GOOD: async with session_factory() as s:     # Scoped session per request

BAD:  @celery.task ... raise Exception       # Task dies permanently on first error
GOOD: @shared_task(autoretry_for=(...))      # Retry with backoff for transient errors

BAD:  await redis.set("key", value)          # No TTL -- key lives forever
GOOD: await redis.setex("key", 300, value)   # Explicit TTL prevents unbounded growth

BAD:  alembic upgrade head  # in production  # Manual step -- will be forgotten
GOOD: CI runs alembic upgrade head           # Automated, every deploy, no exceptions

BAD:  print("order created")                 # Unstructured, unsearchable
GOOD: logger.info("Order created", id=oid)   # Structured, filterable, machine-readable

BAD:  db_url = "postgres://localhost/mydb"   # Hardcoded connection string
GOOD: db_url from Settings(env_file=".env")  # Environment-driven, per 12-factor
```
