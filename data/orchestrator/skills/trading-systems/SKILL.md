---
name: trading-systems
description: >
  Build reliable, production-grade algorithmic trading systems with proper risk management,
  exchange connectivity, order lifecycle management, position tracking, and real-time market
  data processing. Covers backtesting, multi-strategy management, execution optimization,
  and market data normalization. Trigger this skill for any task involving trading bots,
  exchange APIs, order management, position tracking, risk controls, market data, price feeds,
  portfolio management, quantitative trading strategies, backtesting, or execution algorithms.
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
  - simulation
  - paper trading
  - multi-strategy
  - portfolio optimization
  - execution
---

# Trading Systems Excellence

Trading systems handle real money. Every bug is a potential financial loss. Build with paranoid levels of validation, defense-in-depth risk controls, and the assumption that everything — the exchange, the network, your own code — will fail at the worst possible moment.

## Core Principles

1. **Safety over speed** — A missed trade costs nothing. A bad trade costs everything. Every order passes through risk checks before reaching the exchange.
2. **Audit everything** — Every order, fill, position change, and risk event is logged with full context. You must be able to reconstruct exactly what happened and why.
3. **Fail closed** — When something goes wrong, cancel orders and flatten positions. Never fail into an unknown state.

## Architecture

### Backing Services as Attached Resources (12-Factor IV)

Exchanges, databases, message queues, and data feeds are *attached resources* — swappable via configuration, never hardcoded. A deploy should be able to switch from Binance to Hyperliquid, or from PostgreSQL to TimescaleDB, by changing a connection URL.

```python
from pydantic_settings import BaseSettings


class TradingConfig(BaseSettings):
    """All backing services configured via environment variables."""

    # Exchange — swap providers without code changes
    exchange_ws_url: str = "wss://api.exchange.com/ws"
    exchange_rest_url: str = "https://api.exchange.com"
    exchange_api_key: str
    exchange_api_secret: str

    # Database — attached resource, not embedded state
    db_url: str = "postgresql+asyncpg://localhost:5432/trading"

    # Message queue — decouple components via broker
    mq_url: str = "amqp://guest:guest@localhost:5672/"

    # Market data feed — independent service
    market_data_url: str = "wss://feed.provider.com/v1"

    model_config = {"env_prefix": "TRADING_"}


# Usage: every component receives its backing service via DI
config = TradingConfig()  # reads from TRADING_EXCHANGE_WS_URL, etc.
```

### System Components
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Market Data │────>│   Strategy   │────>│    Order     │
│   Handler    │     │   Engine     │     │   Manager    │
└──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                     │
       │            ┌──────v───────┐      ┌──────v──────┐
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
import logging
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


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
                                logger.error("Callback error", exc_info=e)

            except ConnectionClosed:
                logger.warning("WebSocket disconnected, reconnecting...")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error("WebSocket error", exc_info=e)
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
                        logger.warning("Rate limited, waiting %s seconds", wait)
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

    def __init__(self, exchange: ExchangeClient, risk_manager: "RiskManager"):
        self._exchange = exchange
        self._risk = risk_manager
        self._orders: dict[str, Order] = {}

    async def submit(self, order: Order) -> Order:
        # Risk check BEFORE sending to exchange
        risk_check = self._risk.check_order(order)
        if not risk_check.approved:
            order.status = OrderStatus.REJECTED
            order.error = risk_check.reason
            logger.warning("Order rejected by risk: %s", risk_check.reason)
            return order

        try:
            result = await self._exchange.place_order(order.model_dump())
            order.exchange_id = result["id"]
            order.status = OrderStatus.SUBMITTED
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.error = str(e)
            logger.error("Order submission failed: %s", e)

        self._orders[order.id] = order
        return order

    async def cancel_all(self, reason: str) -> None:
        """Emergency: cancel all active orders."""
        logger.warning("Cancelling all orders: %s", reason)
        active = [o for o in self._orders.values() if o.is_active]

        results = await asyncio.gather(
            *[self._exchange.cancel_order(o.exchange_id) for o in active if o.exchange_id],
            return_exceptions=True,
        )

        for order, result in zip(active, results):
            if isinstance(result, Exception):
                logger.error("Cancel failed for %s: %s", order.id, result)
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

    def __init__(self, config: "RiskConfig"):
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

    def __init__(self, config: "RiskConfig"):
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
        logger.critical("CIRCUIT BREAKER TRIPPED: %s", reason)
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

    def update_from_fill(self, fill: "Fill") -> None:
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

        logger.info("Position updated: %s qty=%s", symbol, self._positions[symbol].quantity)

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

    async def log_order_filled(self, order: Order, fill: "Fill") -> None:
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

## Backtesting Framework

Write the test for expected strategy behavior *before* implementing the strategy. This catches specification errors early and ensures the backtest engine itself is trustworthy.

### TDD: Write the Backtest Assertion First

```python
import pytest
from datetime import datetime, timezone
from decimal import Decimal


def test_mean_reversion_sells_above_upper_band():
    """
    TDD — write this test BEFORE implementing MeanReversionStrategy.
    The strategy MUST generate a sell signal when price exceeds the
    upper Bollinger Band by more than 1 standard deviation.
    """
    # Arrange — build synthetic price history that breaches upper band
    prices = [Decimal("100")] * 20  # stable baseline
    prices += [Decimal("115"), Decimal("118"), Decimal("122")]  # breakout

    candles = [
        Candle(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            open=p, high=p + 1, low=p - 1, close=p, volume=Decimal("1000"),
        )
        for p in prices
    ]

    engine = BacktestEngine(
        initial_capital=Decimal("10000"),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal("5"),
    )
    strategy = MeanReversionStrategy(window=20, num_std=2.0)

    # Act — run backtest
    result = engine.run(strategy=strategy, candles=candles)

    # Assert — strategy MUST have opened a short position
    assert len(result.trades) >= 1, "Strategy should have traded on band breach"
    assert result.trades[-1].side == "sell", "Should sell when above upper band"
    assert result.total_fees > 0, "Fees must be modeled"
    assert result.max_drawdown <= Decimal("0.05"), "Drawdown must stay within 5%"
```

### Event-Driven Backtester Architecture

```python
from dataclasses import dataclass, field
from typing import Protocol
from collections.abc import Iterator


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    symbol: str = "BTC-USD"


@dataclass
class BacktestTrade:
    timestamp: datetime
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    slippage: Decimal


@dataclass
class BacktestResult:
    trades: list[BacktestTrade]
    equity_curve: list[Decimal]
    total_return: Decimal
    max_drawdown: Decimal
    sharpe_ratio: float
    total_fees: Decimal
    win_rate: float


class Strategy(Protocol):
    """All strategies implement this interface."""
    def on_candle(self, candle: Candle) -> list[dict] | None: ...
    def reset(self) -> None: ...


class DataReplayEngine:
    """Replays historical data preserving exact chronological order."""

    def __init__(self, candles: list[Candle]):
        self._candles = sorted(candles, key=lambda c: c.timestamp)

    def replay(self) -> Iterator[Candle]:
        for candle in self._candles:
            yield candle


class BacktestEngine:
    """Event-driven backtester — NO lookahead bias, realistic fills."""

    def __init__(
        self,
        initial_capital: Decimal,
        fee_rate: Decimal = Decimal("0.001"),
        slippage_bps: Decimal = Decimal("5"),
    ):
        self._initial_capital = initial_capital
        self._fee_rate = fee_rate
        self._slippage_bps = slippage_bps

    def _apply_slippage(self, price: Decimal, side: str) -> Decimal:
        """Simulate slippage — buys fill higher, sells fill lower."""
        slip = price * self._slippage_bps / Decimal("10000")
        return price + slip if side == "buy" else price - slip

    def _apply_fee(self, notional: Decimal) -> Decimal:
        return notional * self._fee_rate

    def run(self, strategy: Strategy, candles: list[Candle]) -> BacktestResult:
        strategy.reset()
        replay = DataReplayEngine(candles)
        capital = self._initial_capital
        position = Decimal("0")
        trades: list[BacktestTrade] = []
        equity_curve: list[Decimal] = [capital]
        peak = capital

        for candle in replay.replay():
            signals = strategy.on_candle(candle)
            if not signals:
                equity_curve.append(capital + position * candle.close)
                continue

            for signal in signals:
                fill_price = self._apply_slippage(candle.close, signal["side"])
                qty = Decimal(str(signal["quantity"]))
                notional = fill_price * qty
                fee = self._apply_fee(notional)

                if signal["side"] == "buy":
                    capital -= notional + fee
                    position += qty
                else:
                    capital += notional - fee
                    position -= qty

                trades.append(BacktestTrade(
                    timestamp=candle.timestamp, symbol=candle.symbol,
                    side=signal["side"], quantity=qty,
                    price=fill_price, fee=fee,
                    slippage=fill_price - candle.close,
                ))

            current_equity = capital + position * candle.close
            equity_curve.append(current_equity)
            peak = max(peak, current_equity)

        return self._build_result(trades, equity_curve, peak)
```

### Walk-Forward Optimization

```python
class WalkForwardOptimizer:
    """
    Prevent overfitting by splitting data into in-sample (train)
    and out-of-sample (test) windows that roll forward in time.
    """

    def __init__(
        self,
        candles: list[Candle],
        in_sample_days: int = 90,
        out_of_sample_days: int = 30,
    ):
        self._candles = candles
        self._is_days = in_sample_days
        self._oos_days = out_of_sample_days

    def run(self, strategy_factory, param_grid: list[dict]) -> list[dict]:
        results = []
        windows = self._generate_windows()

        for in_sample, out_of_sample in windows:
            # Optimize on in-sample
            best_params = self._optimize(strategy_factory, param_grid, in_sample)

            # Validate on out-of-sample — the only result that matters
            strategy = strategy_factory(**best_params)
            engine = BacktestEngine(initial_capital=Decimal("10000"))
            oos_result = engine.run(strategy=strategy, candles=out_of_sample)

            results.append({
                "params": best_params,
                "in_sample_return": self._get_return(strategy_factory, best_params, in_sample),
                "out_of_sample_return": oos_result.total_return,
                "out_of_sample_sharpe": oos_result.sharpe_ratio,
            })

        return results
```

## Multi-Strategy Management

### Strategy Registry Pattern

```python
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """All strategies register via this interface."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def on_candle(self, candle: Candle) -> list[dict] | None: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def required_symbols(self) -> list[str]: ...


class StrategyRegistry:
    """
    Central registry for all active strategies.
    Strategies register themselves; the orchestrator routes data to them.
    """

    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}
        self._enabled: set[str] = set()

    def register(self, strategy: BaseStrategy) -> None:
        self._strategies[strategy.name()] = strategy
        logger.info("Strategy registered: %s", strategy.name())

    def enable(self, name: str) -> None:
        if name not in self._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        self._enabled.add(name)

    def disable(self, name: str) -> None:
        self._enabled.discard(name)

    def active_strategies(self) -> list[BaseStrategy]:
        return [s for n, s in self._strategies.items() if n in self._enabled]

    def route_candle(self, candle: Candle) -> list[dict]:
        """Fan out market data to all active strategies, collect signals."""
        all_signals = []
        for strategy in self.active_strategies():
            if candle.symbol in strategy.required_symbols():
                signals = strategy.on_candle(candle)
                if signals:
                    for sig in signals:
                        sig["strategy"] = strategy.name()
                    all_signals.extend(signals)
        return all_signals
```

### Capital Allocation and Correlation-Aware Risk

```python
import numpy as np


class CapitalAllocator:
    """
    Allocate capital across strategies based on performance and correlation.
    Strategies that are correlated get less combined allocation.
    """

    def __init__(self, total_capital: Decimal, max_strategy_pct: float = 0.30):
        self._total = total_capital
        self._max_pct = max_strategy_pct

    def allocate(
        self,
        strategy_returns: dict[str, list[float]],
        weights: dict[str, float] | None = None,
    ) -> dict[str, Decimal]:
        """
        Allocate capital with correlation penalty.
        Correlated strategies share risk budget.
        """
        names = list(strategy_returns.keys())

        if weights is None:
            weights = {n: 1.0 / len(names) for n in names}

        # Build correlation matrix
        returns_matrix = np.array([strategy_returns[n] for n in names])
        if returns_matrix.shape[1] < 2:
            # Not enough data — equal allocation
            alloc = Decimal(str(1 / len(names)))
            return {n: self._total * alloc for n in names}

        corr = np.corrcoef(returns_matrix)

        # Penalize correlated strategies
        adjusted: dict[str, float] = {}
        for i, name in enumerate(names):
            avg_corr = np.mean([abs(corr[i][j]) for j in range(len(names)) if j != i])
            penalty = 1.0 - (avg_corr * 0.5)  # 50% correlation = 25% reduction
            adjusted[name] = weights[name] * penalty

        # Normalize and cap
        total_weight = sum(adjusted.values())
        allocations = {}
        for name in names:
            pct = min(adjusted[name] / total_weight, self._max_pct)
            allocations[name] = self._total * Decimal(str(pct))

        return allocations
```

## Market Data Normalization

### Multi-Exchange Data Alignment

```python
from datetime import datetime, timezone
from enum import StrEnum


class Exchange(StrEnum):
    BINANCE = "binance"
    HYPERLIQUID = "hyperliquid"
    COINBASE = "coinbase"


# Canonical symbol mapping — every exchange has different naming
SYMBOL_MAP: dict[Exchange, dict[str, str]] = {
    Exchange.BINANCE:     {"BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT"},
    Exchange.HYPERLIQUID: {"BTC-USD": "BTC",     "ETH-USD": "ETH"},
    Exchange.COINBASE:    {"BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD"},
}


def to_canonical_symbol(exchange: Exchange, raw_symbol: str) -> str:
    """Map exchange-specific symbol to canonical form."""
    reverse_map = {v: k for k, v in SYMBOL_MAP[exchange].items()}
    if raw_symbol not in reverse_map:
        raise ValueError(f"Unknown symbol {raw_symbol} on {exchange}")
    return reverse_map[raw_symbol]


def to_exchange_symbol(exchange: Exchange, canonical: str) -> str:
    """Map canonical symbol to exchange-specific form."""
    return SYMBOL_MAP[exchange][canonical]
```

### Timestamp Normalization

```python
class TimestampNormalizer:
    """
    ALL timestamps are UTC. No exceptions.
    Exchanges return timestamps in different formats — normalize immediately.
    """

    @staticmethod
    def normalize(raw: int | float | str, exchange: Exchange) -> datetime:
        if isinstance(raw, str):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)

        # Binance uses milliseconds, others may use seconds
        if isinstance(raw, (int, float)):
            if raw > 1e12:
                return datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
            return datetime.fromtimestamp(raw, tz=timezone.utc)

        raise ValueError(f"Cannot parse timestamp: {raw}")
```

### Data Quality Checks

```python
@dataclass
class QualityReport:
    gaps: list[tuple[datetime, datetime]]
    outliers: list[Candle]
    total_candles: int
    missing_pct: float


class DataQualityChecker:
    """Catch bad data before it reaches your strategy."""

    def __init__(self, max_gap_seconds: int = 120, outlier_std: float = 5.0):
        self._max_gap = max_gap_seconds
        self._outlier_std = outlier_std

    def check(self, candles: list[Candle]) -> QualityReport:
        if len(candles) < 2:
            return QualityReport([], [], len(candles), 0.0)

        sorted_candles = sorted(candles, key=lambda c: c.timestamp)
        gaps = self._find_gaps(sorted_candles)
        outliers = self._find_outliers(sorted_candles)
        expected = self._expected_count(sorted_candles)
        missing_pct = (expected - len(candles)) / expected if expected > 0 else 0.0

        return QualityReport(
            gaps=gaps, outliers=outliers,
            total_candles=len(candles), missing_pct=missing_pct,
        )

    def _find_gaps(self, candles: list[Candle]) -> list[tuple[datetime, datetime]]:
        gaps = []
        for i in range(1, len(candles)):
            delta = (candles[i].timestamp - candles[i - 1].timestamp).total_seconds()
            if delta > self._max_gap:
                gaps.append((candles[i - 1].timestamp, candles[i].timestamp))
        return gaps

    def _find_outliers(self, candles: list[Candle]) -> list[Candle]:
        prices = [float(c.close) for c in candles]
        mean = sum(prices) / len(prices)
        std = (sum((p - mean) ** 2 for p in prices) / len(prices)) ** 0.5
        if std == 0:
            return []
        return [c for c in candles if abs(float(c.close) - mean) > self._outlier_std * std]
```

## Execution Optimization

### TWAP Execution

```python
class TWAPExecutor:
    """
    Time-Weighted Average Price — split a large order into equal
    slices executed at fixed intervals to reduce market impact.
    """

    def __init__(
        self,
        exchange: ExchangeClient,
        risk_manager: RiskManager,
        total_quantity: Decimal,
        symbol: str,
        side: str,
        duration_seconds: int,
        num_slices: int,
    ):
        self._exchange = exchange
        self._risk = risk_manager
        self._total_qty = total_quantity
        self._symbol = symbol
        self._side = side
        self._interval = duration_seconds / num_slices
        self._slice_qty = total_quantity / num_slices
        self._filled: Decimal = Decimal("0")

    async def execute(self) -> list[dict]:
        fills = []
        remaining = self._total_qty

        while remaining > Decimal("0"):
            qty = min(self._slice_qty, remaining)
            try:
                result = await self._exchange.place_order({
                    "symbol": self._symbol,
                    "side": self._side,
                    "type": "limit",
                    "quantity": str(qty),
                })
                fills.append(result)
                remaining -= qty
                self._filled += qty
            except Exception as e:
                logger.error("TWAP slice failed: %s", e)

            if remaining > Decimal("0"):
                await asyncio.sleep(self._interval)

        return fills
```

### VWAP Execution

```python
class VWAPExecutor:
    """
    Volume-Weighted Average Price — distribute order according to
    historical volume profile to match the market's natural rhythm.
    """

    def __init__(
        self,
        exchange: ExchangeClient,
        total_quantity: Decimal,
        symbol: str,
        side: str,
        volume_profile: list[float],
    ):
        self._exchange = exchange
        self._total_qty = total_quantity
        self._symbol = symbol
        self._side = side
        # Normalize volume profile to weights
        total_vol = sum(volume_profile)
        self._weights = [v / total_vol for v in volume_profile]

    async def execute(self, interval_seconds: int = 60) -> list[dict]:
        fills = []
        for weight in self._weights:
            qty = self._total_qty * Decimal(str(weight))
            if qty <= Decimal("0"):
                continue
            try:
                result = await self._exchange.place_order({
                    "symbol": self._symbol,
                    "side": self._side,
                    "type": "limit",
                    "quantity": str(qty),
                })
                fills.append(result)
            except Exception as e:
                logger.error("VWAP slice failed: %s", e)
            await asyncio.sleep(interval_seconds)
        return fills
```

### Smart Order Routing

```python
class SmartOrderRouter:
    """
    Route orders to the exchange offering best execution.
    Considers price, liquidity, fees, and latency.
    """

    def __init__(self, exchanges: dict[str, ExchangeClient]):
        self._exchanges = exchanges

    async def find_best_venue(
        self, symbol: str, side: str, quantity: Decimal,
    ) -> tuple[str, Decimal]:
        """Return (exchange_name, expected_fill_price) for best execution."""
        quotes = await asyncio.gather(*[
            self._get_quote(name, ex, symbol, side, quantity)
            for name, ex in self._exchanges.items()
        ], return_exceptions=True)

        valid = [
            (name, price) for (name, price) in quotes
            if not isinstance(price, Exception) and price is not None
        ]

        if not valid:
            raise RuntimeError(f"No valid quotes for {symbol}")

        # Best price: lowest for buys, highest for sells
        if side == "buy":
            return min(valid, key=lambda x: x[1])
        return max(valid, key=lambda x: x[1])
```

### Partial Fill Handling

```python
class PartialFillTracker:
    """
    Track partially filled orders and decide whether to chase,
    cancel remainder, or wait.
    """

    def __init__(self, max_wait_seconds: int = 30, chase_threshold: float = 0.8):
        self._max_wait = max_wait_seconds
        self._chase_threshold = chase_threshold  # chase if >80% filled

    async def monitor(
        self,
        order: Order,
        exchange: ExchangeClient,
        order_manager: OrderManager,
    ) -> Order:
        start = time.monotonic()

        while order.is_active:
            elapsed = time.monotonic() - start

            if elapsed > self._max_wait:
                fill_ratio = order.filled_quantity / order.quantity
                if fill_ratio >= self._chase_threshold:
                    # Almost filled — chase the remainder at market
                    remainder_qty = order.remaining_quantity
                    await exchange.cancel_order(order.exchange_id)
                    chase_order = Order(
                        id=f"{order.id}-chase",
                        symbol=order.symbol,
                        side=order.side,
                        order_type="market",
                        quantity=remainder_qty,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    return await order_manager.submit(chase_order)
                else:
                    # Not enough fill — cancel and re-evaluate
                    await exchange.cancel_order(order.exchange_id)
                    order.status = OrderStatus.CANCELLED
                    return order

            await asyncio.sleep(1)

        return order
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
- [ ] Backing services (exchanges, DBs, queues) configurable via env vars
- [ ] Backtest written test-first — assertion before strategy implementation
- [ ] Walk-forward validation used, never in-sample results alone
- [ ] Slippage and fees modeled in every backtest
- [ ] Multi-strategy capital allocation accounts for correlation
- [ ] Market data timestamps normalized to UTC on ingestion
- [ ] Symbol mapping handles exchange-specific naming
- [ ] Data quality checks run before strategy consumption
- [ ] Execution algorithms used for large orders (TWAP/VWAP)
- [ ] Partial fills tracked and handled (chase or cancel)

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
- Backtesting with lookahead bias (using future data in signals)
- Optimizing strategy parameters without out-of-sample validation
- Ignoring slippage and fees in backtests (inflates returns by 20-50%)
- Running correlated strategies without shared risk budget
- Mixing exchange timestamp formats (some use ms, some use s)
- Sending large market orders without execution algorithms
- Ignoring partial fills — assuming orders are fully filled or not at all
- Hardcoding exchange URLs instead of treating them as attached resources
