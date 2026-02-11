---
name: python-backend
description: >
  Build production-grade Python backend services with modern async patterns, strict typing,
  Pydantic validation, FastAPI, proper error handling, and clean architecture. Trigger this
  skill for any task involving Python server-side code, FastAPI endpoints, Pydantic models,
  async operations, background tasks, or Python service architecture. Also trigger when the
  task mentions pytest, asyncio, uvicorn, or any Python backend framework.
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
---

# Python Backend Excellence

Write Python that is idiomatic, typed, and production-ready. Python's strength is clarity — lean into it. Use `async` for I/O, type hints for safety, Pydantic for validation, and keep your code so readable that documentation is almost redundant.

## Core Principles

1. **Type everything** — Use type hints on every function signature, every class attribute, every variable where the type isn't obvious. `Any` is a bug.
2. **Validate at the boundary** — Every external input (HTTP request, file, environment variable, API response) goes through Pydantic before touching your business logic.
3. **Async for I/O, sync for CPU** — `async`/`await` for network and disk. Plain functions for computation. Never block the event loop.

## Project Structure

```
project/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Settings via pydantic-settings
│       ├── dependencies.py      # FastAPI dependency injection
│       ├── models/              # Pydantic models (request/response)
│       │   ├── __init__.py
│       │   └── trading.py
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
│       └── utils/               # Shared utilities
│           ├── __init__.py
│           └── logging.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── pyproject.toml
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

    # Required — app won't start without these
    database_url: str
    api_key: SecretStr

    # Optional with defaults
    debug: bool = False
    port: int = Field(default=8000, ge=1024, le=65535)
    log_level: str = Field(default="info", pattern=r"^(debug|info|warning|error)$")
    max_workers: int = Field(default=4, ge=1, le=32)

    # Computed
    @property
    def is_production(self) -> bool:
        return not self.debug


# Singleton — load once at startup
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

## Pydantic Models — The Contract

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


# Request model — strict validation
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


# Response model — controlled output
class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: OrderSide
    status: str
    quantity: float
    price: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Use separate models for create vs response — never expose internals
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

## Async Patterns

### async/await — The Default for I/O
```python
import httpx
from contextlib import asynccontextmanager


# Use httpx for async HTTP (not requests — it's synchronous)
@asynccontextmanager
async def get_http_client():
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

### Background Tasks
```python
import asyncio
from collections.abc import Callable, Awaitable


async def run_periodic(
    name: str,
    fn: Callable[[], Awaitable[None]],
    interval_seconds: float,
) -> None:
    """Run an async function periodically with error handling."""
    while True:
        try:
            await fn()
        except asyncio.CancelledError:
            raise  # Respect cancellation
        except Exception as e:
            print(f"[{name}] Error: {e}")

        await asyncio.sleep(interval_seconds)


# Start and stop with lifespan
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(
        run_periodic("watchdog", check_positions, 60)
    )
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)
```

## FastAPI Patterns

### Route Handlers
```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    settings: Settings = Depends(get_settings),
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Create a new order."""
    try:
        order = await order_service.create(request)
        return OrderResponse.model_validate(order)
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ExchangeError as e:
        raise HTTPException(status_code=502, detail="Exchange unavailable")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Get an order by ID."""
    order = await order_service.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse.model_validate(order)
```

### Dependency Injection
```python
from functools import lru_cache
from fastapi import Depends


@lru_cache
def get_settings() -> Settings:
    return Settings()


async def get_db_pool(
    settings: Settings = Depends(get_settings),
) -> asyncpg.Pool:
    # Managed elsewhere via lifespan — this is for illustration
    return app.state.db_pool


async def get_order_service(
    db: asyncpg.Pool = Depends(get_db_pool),
    settings: Settings = Depends(get_settings),
) -> OrderService:
    repo = OrderRepository(db)
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

### Async Tests
```python
import pytest
from httpx import AsyncClient, ASGITransport
from myapp.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
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

### Fixtures and Mocking
```python
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_exchange():
    exchange = AsyncMock()
    exchange.place_order.return_value = {
        "id": "order-123",
        "status": "filled",
    }
    return exchange


@pytest.fixture
def order_service(mock_exchange):
    repo = InMemoryOrderRepo()
    return OrderService(repo, mock_exchange)


@pytest.mark.asyncio
async def test_order_service_places_on_exchange(order_service, mock_exchange):
    order = await order_service.create(CreateOrderRequest(
        symbol="ETH-USD",
        side="buy",
        order_type="market",
        quantity=1.0,
    ))
    mock_exchange.place_order.assert_called_once()
    assert order.status == "filled"
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

```python
import logging
import json
from datetime import datetime


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )


class StructuredLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def info(self, message: str, **kwargs) -> None:
        self._log("info", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log("error", message, **kwargs)

    def _log(self, level: str, message: str, **kwargs) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        getattr(self._logger, level)(json.dumps(entry))


# Usage
logger = StructuredLogger("order_service")
logger.info("Order created", order_id="123", symbol="BTC-USD")
```

## Quality Checklist

- [ ] All functions have type hints (parameters and return types)
- [ ] No `Any` types — use `unknown` patterns or specific types
- [ ] All external input validated via Pydantic models
- [ ] Async used for I/O, sync for CPU-bound work
- [ ] Settings loaded via pydantic-settings (not raw os.environ)
- [ ] Custom exception hierarchy (not bare Exception)
- [ ] Tests use pytest with async support
- [ ] No blocking I/O in async functions (no `requests`, use `httpx`)
- [ ] Dependencies injected (not imported globals)
- [ ] Structured logging (JSON format for production)
- [ ] Graceful shutdown handling (lifespan context manager)
- [ ] Secrets use SecretStr (not plain strings)

## Anti-Patterns

- Using `requests` library in async code (blocks the event loop)
- `os.environ.get()` scattered throughout code (use pydantic-settings)
- Bare `except: pass` — always catch specific exceptions
- Missing type hints ("I'll add them later" — you won't)
- Business logic in route handlers (put it in services)
- Raw dicts instead of Pydantic models for API contracts
- `from typing import List, Dict, Optional` — use `list`, `dict`, `X | None` (Python 3.10+)
- Mutable default arguments (`def f(items=[])`)
- Global mutable state instead of dependency injection
- `print()` instead of `logging` in production code
- Synchronous database drivers in async applications
- Not using `__all__` in `__init__.py` (leaks internal modules)
