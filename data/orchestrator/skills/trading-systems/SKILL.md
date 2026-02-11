---
name: trading-systems
description: >
  Build reliable, production-grade algorithmic trading systems with proper risk management,
  exchange connectivity, order lifecycle management, position tracking, and real-time market
  data processing. Trigger this skill for any task involving trading bots, exchange APIs,
  order management, position tracking, risk controls, market data, price feeds, portfolio
  management, or quantitative trading strategies.
triggers:
  - trading
  - trade
  - exchange
  - order
  - position
  - portfolio
  - market data
  - price feed
  - websocket
  - tick
  - candle
  - ohlcv
  - hyperliquid
  - binance
  - dex
  - perp
  - futures
  - leverage
  - liquidation
  - pnl
  - slippage
  - spread
  - hedge
  - strategy
  - backtest
  - signal
  - indicator
  - risk
  - stop loss
  - take profit
---

# Trading Systems Excellence

Trading systems handle real money. Every bug is a potential financial loss. Build with paranoid levels of validation, defense-in-depth risk controls, and the assumption that everything — the exchange, the network, your own code — will fail at the worst possible moment.

## Core Principles

1. **Safety over speed** — A missed trade costs nothing. A bad trade costs everything. Every order passes through risk checks before reaching the exchange.
2. **Audit everything** — Every order, fill, position change, and risk event is logged with full context. You must be able to reconstruct exactly what happened and why.
3. **Fail closed** — When something goes wrong, cancel orders and flatten positions. Never fail into an unknown state.

## Architecture

### System Components
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Market Data │────▶│   Strategy   │────▶│    Order     │
│   Handler    │     │   Engine     │     │   Manager    │
└──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                     │
       │            ┌──────▼───────┐      ┌──────▼──────┐
       │            │    Risk      │      │   Exchange   │
       │            │   Manager    │      │   Gateway    │
       │            └──────────────┘      └─────────────┘
       │                                        │
       └────────────────────────────────────────┘
                    ┌──────────────┐
                    │  Position    │
                    │  Tracker     │
                    └──────────────┘
```

### Separation of Concerns
```python
# Each component has ONE job:
# - MarketDataHandler: normalize and distribute market data
# - StrategyEngine: generate signals from market data
# - RiskManager: validate orders against risk limits
# - OrderManager: manage order lifecycle (place, cancel, track)
# - ExchangeGateway: communicate with exchange API
# - PositionTracker: track positions, P&L, exposure
```

## Exchange Connectivity

### Rate Limiting
```python
import asyncio
import time
from collections import deque


class ExchangeRateLimiter:
    """Respect exchange rate limits — getting banned kills your bot."""

    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()

            # Remove expired timestamps
            while self._timestamps and self._timestamps[0] < now - self._window:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_requests:
                # Wait until the oldest request expires
                wait = self._timestamps[0] + self._window - now
                await asyncio.sleep(wait)
                self._timestamps.popleft()

            self._timestamps.append(time.monotonic())


# Leave 20-30% headroom — never hit the actual limit
rate_limiter = ExchangeRateLimiter(
    max_requests=70,    # Exchange allows 100/min
    window_seconds=60,
)
```

### WebSocket Connection
```python
import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed


class MarketDataFeed:
    """Resilient WebSocket connection with automatic reconnection."""

    def __init__(self, url: str, subscriptions: list[str]):
        self._url = url
        self._subscriptions = subscriptions
        self._callbacks: list[callable] = []
        self._running = False

    def on_message(self, callback: callable) -> None:
        self._callbacks.append(callback)

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                async with websockets.connect(self._url) as ws:
                    # Subscribe to channels
                    for sub in self._subscriptions:
                        await ws.send(json.dumps(sub))

                    # Process messages
                    async for raw_message in ws:
                        message = json.loads(raw_message)
                        for callback in self._callbacks:
                            try:
                                await callback(message)
                            except Exception as e:
                                logger.error("Callback error", error=str(e))

            except ConnectionClosed:
                logger.warning("WebSocket disconnected, reconnecting...")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error("WebSocket error", error=str(e))
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False
```

### REST API Client
```python
import httpx
from typing import Any


class ExchangeClient:
    """Exchange API client with retries, rate limiting, and error handling."""

    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self._base_url = base_url
        self._api_key = api_key
        self._api_secret = api_secret
        self._rate_limiter = ExchangeRateLimiter(70, 60)

    async def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        max_retries: int = 3,
    ) -> dict:
        await self._rate_limiter.acquire()

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    headers = self._sign_request(method, path, data)
                    response = await client.request(
                        method, f"{self._base_url}{path}",
                        json=data, headers=headers,
                    )

                    if response.status_code == 429:
                        wait = float(response.headers.get("Retry-After", 5))
                        logger.warning("Rate limited", wait=wait)
                        await asyncio.sleep(wait)
                        continue

                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise RuntimeError("Unreachable")

    async def place_order(self, order: dict) -> dict:
        return await self._request("POST", "/v1/orders", data=order)

    async def cancel_order(self, order_id: str) -> dict:
        return await self._request("DELETE", f"/v1/orders/{order_id}")

    async def get_positions(self) -> list[dict]:
        return await self._request("GET", "/v1/positions")
```

## Order Management

### Order Lifecycle
```python
from enum import StrEnum
from pydantic import BaseModel
from datetime import datetime


class OrderStatus(StrEnum):
    PENDING = "pending"           # Created locally, not yet sent
    SUBMITTED = "submitted"       # Sent to exchange
    OPEN = "open"                 # Confirmed on exchange order book
    PARTIALLY_FILLED = "partial"  # Some quantity filled
    FILLED = "filled"             # Fully filled
    CANCELLED = "cancelled"       # Cancelled (by us or exchange)
    REJECTED = "rejected"         # Rejected by exchange
    EXPIRED = "expired"           # Time-in-force expired
    FAILED = "failed"             # Failed to submit


class Order(BaseModel):
    id: str
    exchange_id: str | None = None
    symbol: str
    side: str
    order_type: str
    quantity: float
    filled_quantity: float = 0.0
    price: float | None = None
    avg_fill_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        )
```

### Order Manager
```python
class OrderManager:
    """Track all orders, handle fills, manage cancellations."""

    def __init__(self, exchange: ExchangeClient, risk_manager: RiskManager):
        self._exchange = exchange
        self._risk = risk_manager
        self._orders: dict[str, Order] = {}

    async def submit(self, order: Order) -> Order:
        # Risk check BEFORE sending to exchange
        risk_check = self._risk.check_order(order)
        if not risk_check.approved:
            order.status = OrderStatus.REJECTED
            order.error = risk_check.reason
            logger.warning("Order rejected by risk", reason=risk_check.reason)
            return order

        try:
            result = await self._exchange.place_order(order.model_dump())
            order.exchange_id = result["id"]
            order.status = OrderStatus.SUBMITTED
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.error = str(e)
            logger.error("Order submission failed", error=str(e))

        self._orders[order.id] = order
        return order

    async def cancel_all(self, reason: str) -> None:
        """Emergency: cancel all active orders."""
        logger.warning("Cancelling all orders", reason=reason)
        active = [o for o in self._orders.values() if o.is_active]

        results = await asyncio.gather(
            *[self._exchange.cancel_order(o.exchange_id) for o in active if o.exchange_id],
            return_exceptions=True,
        )

        for order, result in zip(active, results):
            if isinstance(result, Exception):
                logger.error("Cancel failed", order_id=order.id, error=str(result))
            else:
                order.status = OrderStatus.CANCELLED
```

## Risk Management

### Pre-Trade Risk Checks
```python
from dataclasses import dataclass


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str = ""


class RiskManager:
    """Every order must pass ALL risk checks before execution."""

    def __init__(self, config: RiskConfig):
        self._config = config
        self._daily_loss = 0.0
        self._open_orders = 0

    def check_order(self, order: Order) -> RiskCheckResult:
        checks = [
            self._check_order_size(order),
            self._check_position_limit(order),
            self._check_daily_loss_limit(),
            self._check_max_open_orders(),
            self._check_price_sanity(order),
        ]

        for result in checks:
            if not result.approved:
                return result

        return RiskCheckResult(approved=True)

    def _check_order_size(self, order: Order) -> RiskCheckResult:
        notional = order.quantity * (order.price or 0)
        if notional > self._config.max_order_notional:
            return RiskCheckResult(
                approved=False,
                reason=f"Order notional ${notional:.2f} exceeds limit ${self._config.max_order_notional:.2f}",
            )
        return RiskCheckResult(approved=True)

    def _check_daily_loss_limit(self) -> RiskCheckResult:
        if self._daily_loss >= self._config.max_daily_loss:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit reached: ${self._daily_loss:.2f}",
            )
        return RiskCheckResult(approved=True)

    def _check_price_sanity(self, order: Order) -> RiskCheckResult:
        """Reject orders with prices far from market — likely bugs."""
        if order.price is None:
            return RiskCheckResult(approved=True)

        market_price = self._get_last_price(order.symbol)
        if market_price is None:
            return RiskCheckResult(approved=False, reason="No market price available")

        deviation = abs(order.price - market_price) / market_price
        if deviation > self._config.max_price_deviation:
            return RiskCheckResult(
                approved=False,
                reason=f"Price {order.price} deviates {deviation:.1%} from market {market_price}",
            )
        return RiskCheckResult(approved=True)
```

### Circuit Breaker
```python
class CircuitBreaker:
    """Stop trading when things go wrong."""

    def __init__(self, config: RiskConfig):
        self._config = config
        self._consecutive_errors = 0
        self._tripped = False

    def record_success(self) -> None:
        self._consecutive_errors = 0

    def record_error(self, error: Exception) -> None:
        self._consecutive_errors += 1
        if self._consecutive_errors >= self._config.max_consecutive_errors:
            self.trip(f"Consecutive errors: {self._consecutive_errors}")

    def trip(self, reason: str) -> None:
        self._tripped = True
        logger.critical("CIRCUIT BREAKER TRIPPED", reason=reason)
        # Trigger emergency shutdown

    @property
    def is_tripped(self) -> bool:
        return self._tripped
```

## Position Tracking

```python
class Position(BaseModel):
    symbol: str
    side: str          # "long" or "short"
    quantity: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    leverage: float = 1.0

    def update_price(self, price: float) -> None:
        self.current_price = price
        multiplier = 1 if self.side == "long" else -1
        self.unrealized_pnl = (
            (price - self.entry_price) * self.quantity * multiplier
        )


class PositionTracker:
    """Single source of truth for all positions."""

    def __init__(self):
        self._positions: dict[str, Position] = {}

    def update_from_fill(self, fill: Fill) -> None:
        """Update positions from order fills — not from exchange polling."""
        symbol = fill.symbol
        pos = self._positions.get(symbol)

        if pos is None:
            self._positions[symbol] = Position(
                symbol=symbol,
                side="long" if fill.side == "buy" else "short",
                quantity=fill.quantity,
                entry_price=fill.price,
            )
        else:
            # Handle position increase, decrease, or flip
            self._apply_fill(pos, fill)

        logger.info(
            "Position updated",
            symbol=symbol,
            quantity=self._positions.get(symbol, {}).quantity,
        )

    def get_total_exposure(self) -> float:
        """Total absolute notional exposure across all positions."""
        return sum(
            abs(p.quantity * p.current_price)
            for p in self._positions.values()
        )
```

## Audit Trail

```python
import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """Immutable, append-only log of all trading events."""

    def __init__(self, log_dir: Path):
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    async def log_event(self, event_type: str, data: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **data,
        }
        line = json.dumps(entry) + "\n"

        # Daily log files for easy rotation
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"audit-{date_str}.jsonl"

        async with aiofiles.open(log_file, "a") as f:
            await f.write(line)

    # Log every significant event
    async def log_order_submitted(self, order: Order) -> None:
        await self.log_event("order_submitted", order.model_dump())

    async def log_order_filled(self, order: Order, fill: Fill) -> None:
        await self.log_event("order_filled", {
            "order": order.model_dump(),
            "fill": fill.model_dump(),
        })

    async def log_risk_rejection(self, order: Order, reason: str) -> None:
        await self.log_event("risk_rejection", {
            "order": order.model_dump(),
            "reason": reason,
        })

    async def log_circuit_breaker(self, reason: str) -> None:
        await self.log_event("circuit_breaker", {"reason": reason})
```

## Decimal Precision

```python
from decimal import Decimal, ROUND_DOWN


# NEVER use float for financial calculations
# Floating point: 0.1 + 0.2 = 0.30000000000000004
# Decimal:        Decimal("0.1") + Decimal("0.2") = Decimal("0.3")

def round_quantity(quantity: Decimal, step_size: Decimal) -> Decimal:
    """Round to exchange's lot size."""
    return (quantity / step_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * step_size


def round_price(price: Decimal, tick_size: Decimal) -> Decimal:
    """Round to exchange's tick size."""
    return (price / tick_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick_size


# Exchange-specific precision
symbol_info = {
    "BTC-USD": {"tick_size": Decimal("0.1"), "lot_size": Decimal("0.001")},
    "ETH-USD": {"tick_size": Decimal("0.01"), "lot_size": Decimal("0.01")},
}
```

## Quality Checklist

- [ ] Every order passes through risk checks before submission
- [ ] Daily loss limit enforced and cannot be bypassed
- [ ] Circuit breaker trips on consecutive errors
- [ ] All orders, fills, and risk events are audit-logged
- [ ] WebSocket reconnects automatically on disconnect
- [ ] Rate limiter enforced on all exchange API calls (with headroom)
- [ ] Positions tracked from fills (not just exchange polling)
- [ ] Decimal arithmetic for all financial calculations (no float)
- [ ] Graceful shutdown cancels all open orders
- [ ] Price sanity checks prevent fat-finger orders
- [ ] Order lifecycle tracked from creation to final state
- [ ] No hardcoded API keys — use environment variables

## Anti-Patterns

- Using `float` for money (`0.1 + 0.2 != 0.3`)
- No risk checks ("just send the order")
- Fire-and-forget orders (no tracking of fills or status)
- Polling exchange for position state instead of tracking fills locally
- No circuit breaker — system keeps trading during failures
- Logging only successful trades (you need to see failures too)
- Ignoring rate limits until you get banned
- Single point of failure (no reconnection logic)
- Testing on mainnet with real money first
- Hardcoded position sizes or risk limits (use configuration)
- No daily loss limit — a bug can drain your account
- Trusting exchange WebSocket data without validation
