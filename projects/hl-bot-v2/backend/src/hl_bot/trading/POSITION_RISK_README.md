# Position and Risk Management System

**Status:** ✅ Complete  
**Last Updated:** 2025-02-11

## Overview

Production-ready position tracking and risk management for trading systems. Built with paranoid levels of safety, defense-in-depth validation, and comprehensive audit logging.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Trading System                            │
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐ │
│  │   Order     │───▶│ Risk Manager │───▶│   Exchange     │ │
│  │  Request    │    │  (Pre-Trade  │    │    Gateway     │ │
│  └─────────────┘    │   Checks)    │    └────────┬───────┘ │
│                     └──────────────┘              │         │
│                                                   │         │
│                                         ┌─────────▼────────┐│
│                                         │  Order Fill      ││
│                                         └─────────┬────────┘│
│                                                   │         │
│  ┌──────────────────────────────────────────────▼────────┐ │
│  │            Position Tracker                           │ │
│  │  - Track fills (NOT exchange polling)                │ │
│  │  - Calculate P&L                                     │ │
│  │  - Track MAE/MFE                                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │             Audit Logger                              │  │
│  │  - Immutable append-only logs                        │  │
│  │  - All orders, fills, risk events                   │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Risk Manager (`risk_manager.py`)

**Purpose:** Validate every order against risk limits BEFORE execution.

**Key Features:**
- Pre-trade risk checks (all must pass)
- Circuit breaker for consecutive losses/errors
- Order rate limiting
- Price sanity checks (prevent fat-finger errors)
- Daily loss limits
- Position size limits
- Exposure limits

**Usage:**

```python
from decimal import Decimal
from hl_bot.trading import RiskManager, RiskConfig, AuditLogger

# Configure risk limits
config = RiskConfig(
    max_order_notional=Decimal("1000"),     # $1000 max per order
    max_daily_loss=Decimal("500"),          # Stop after $500 loss
    max_positions=5,                        # Max 5 open positions
    max_price_deviation=Decimal("0.05"),    # 5% max from market
    max_consecutive_losses=3,               # Circuit breaker
)

# Initialize risk manager
audit = AuditLogger("./logs/audit")
risk = RiskManager(
    config=config,
    audit_logger=audit,
    initial_balance=Decimal("10000"),
)

# Check order before submission
from hl_bot.types import OrderRequest, OrderSide, OrderType

order = OrderRequest(
    symbol="BTC-USD",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=0.01,
    price=50000,
)

# Update market price for sanity checks
risk.update_market_price("BTC-USD", Decimal("50000"))

# Run risk checks
result = await risk.check_order(order, current_positions)

if result.approved:
    # Safe to submit order
    await exchange.place_order(order)
else:
    # Order rejected
    logger.warning(f"Order rejected: {result.reason}")
```

**Risk Checks Performed:**

1. **Order Size Check**
   - Absolute notional limit
   - Percentage of account limit

2. **Position Limit Check**
   - Max number of positions
   - Don't open new position if at limit

3. **Daily Loss Limit**
   - Absolute daily loss limit
   - Percentage daily loss limit
   - Stops trading if breached

4. **Exposure Limit**
   - Total notional exposure across all positions
   - Percentage of account exposure

5. **Price Sanity Check**
   - Reject orders with prices far from market
   - Prevents fat-finger errors

6. **Order Rate Limit**
   - Max orders per minute per symbol
   - Prevents spam/bugs

7. **Circuit Breaker**
   - Trips on consecutive losses
   - Trips on consecutive errors
   - Requires manual reset after cooldown

### 2. Position Tracker (`position_tracker.py`)

**Purpose:** Track positions from order fills (NOT by polling exchange).

**Key Features:**
- Update positions from fills in real-time
- Calculate average entry price
- Track unrealized and realized P&L
- Track MAE (Max Adverse Excursion)
- Track MFE (Max Favorable Excursion)
- Handle position flips (long → short)
- Full audit trail

**Usage:**

```python
from hl_bot.trading import PositionTracker, Fill, AuditLogger
from hl_bot.types import OrderSide
from decimal import Decimal

# Initialize tracker
audit = AuditLogger("./logs/audit")
tracker = PositionTracker(audit)

# Process order fill
fill = Fill(
    id="fill-123",
    order_id="order-456",
    symbol="BTC-USD",
    side=OrderSide.BUY,
    quantity=Decimal("0.1"),
    price=Decimal("50000"),
    fee=Decimal("5"),
)

# Update position from fill
position = await tracker.update_from_fill(fill)

print(f"Position: {position.quantity} {position.symbol}")
print(f"Entry: ${position.entry_price}")
print(f"P&L: ${position.unrealized_pnl}")

# Update market price
tracker.update_market_price("BTC-USD", Decimal("52000"))

# Get updated position
position = tracker.get_position("BTC-USD")
print(f"Unrealized P&L: ${position.unrealized_pnl}")
print(f"MAE: ${position.max_adverse_excursion}")
print(f"MFE: ${position.max_favorable_excursion}")

# Get all positions
positions = tracker.get_all_positions()
total_exposure = tracker.get_total_exposure()
total_pnl = tracker.get_total_unrealized_pnl()
```

**Position Lifecycle:**

1. **Open:** First fill creates position
2. **Increase:** Same-side fill averages entry price
3. **Decrease:** Opposite-side fill reduces position (realizes P&L)
4. **Close:** Position fully closed (moved to closed_positions)
5. **Flip:** Opposite-side fill larger than position (close + open opposite)

### 3. Risk Configuration (`risk_config.py`)

**Purpose:** Centralized risk parameters (never hardcode limits).

**Configuration Options:**

```python
from hl_bot.trading import RiskConfig
from decimal import Decimal

config = RiskConfig(
    # Position sizing
    max_position_size_usd=Decimal("1000"),          # Max $1000 per position
    max_position_size_percent=Decimal("0.1"),       # Max 10% of account
    
    # Order limits
    max_order_notional=Decimal("5000"),             # Max $5000 per order
    max_open_orders=10,                             # Max 10 open orders
    
    # Loss limits
    max_daily_loss=Decimal("500"),                  # Max $500 loss per day
    max_daily_loss_percent=Decimal("0.05"),         # Max 5% account loss per day
    max_consecutive_losses=3,                       # Circuit breaker threshold
    
    # Exposure limits
    max_total_exposure=Decimal("10000"),            # Max $10k total exposure
    max_exposure_percent=Decimal("0.5"),            # Max 50% account exposure
    max_positions=5,                                # Max 5 open positions
    
    # Price validation
    max_price_deviation=Decimal("0.05"),            # 5% max from market
    max_slippage_percent=Decimal("0.01"),           # 1% max slippage
    
    # Circuit breaker
    max_consecutive_errors=5,                       # Trip after 5 errors
    circuit_breaker_cooldown_minutes=30,            # 30 min cooldown
    
    # Rate limiting
    max_orders_per_minute=10,                       # 10 orders/min per symbol
)

# Load from file
config = RiskConfig.from_file("risk_config.json")

# Load from environment variables
# Prefix: RISK_MAX_DAILY_LOSS=500
config = RiskConfig()
```

## Integration Example

Complete trading loop with position and risk management:

```python
import asyncio
from decimal import Decimal
from hl_bot.trading import (
    HyperliquidClient,
    RiskManager,
    RiskConfig,
    PositionTracker,
    Fill,
    AuditLogger,
)
from hl_bot.types import OrderRequest, OrderSide, OrderType

async def trading_loop():
    # Initialize components
    audit = AuditLogger("./logs/audit")
    
    config = RiskConfig(
        max_daily_loss=Decimal("100"),
        max_positions=3,
    )
    
    risk = RiskManager(
        config=config,
        audit_logger=audit,
        initial_balance=Decimal("10000"),
    )
    
    tracker = PositionTracker(audit)
    
    exchange = HyperliquidClient(
        private_key=os.getenv("PRIVATE_KEY"),
        testnet=True,
        audit_log_dir="./logs/audit",
    )
    
    # Update account balance
    account = await exchange.get_account_state()
    risk.update_account(
        balance=Decimal(str(account["balance"])),
        equity=Decimal(str(account["equity"])),
    )
    
    # Create order
    order = OrderRequest(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.01,
        price=50000,
    )
    
    # Update market price
    market_data = await exchange.get_market_data("BTC-USD")
    risk.update_market_price("BTC-USD", Decimal(str(market_data["price"])))
    
    # Check risk
    positions = tracker.get_all_positions()
    risk_result = await risk.check_order(order, [p.to_position() for p in positions])
    
    if not risk_result.approved:
        print(f"Order rejected: {risk_result.reason}")
        return
    
    # Submit order
    try:
        submitted_order = await exchange.place_order(order)
        risk.record_success()
        
        # Simulate fill (in reality, listen to WebSocket)
        fill = Fill(
            id=f"fill-{submitted_order.id}",
            order_id=submitted_order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=Decimal(str(order.quantity)),
            price=Decimal(str(order.price)),
            fee=Decimal("5"),
        )
        
        # Update position
        position = await tracker.update_from_fill(fill)
        print(f"Position opened: {position.quantity} @ ${position.entry_price}")
        
    except Exception as e:
        risk.record_error(e)
        print(f"Order failed: {e}")
        
        if risk._state.circuit_breaker_tripped:
            print("CIRCUIT BREAKER TRIPPED - STOPPING TRADING")
            await exchange.cancel_all_orders(reason="circuit_breaker")
            return

# Run
asyncio.run(trading_loop())
```

## Circuit Breaker

The circuit breaker is the last line of defense. It trips when:

1. **Consecutive Losses:** Max consecutive losing trades reached
2. **Consecutive Errors:** Max consecutive errors reached
3. **Manual Trip:** `risk.trip_circuit_breaker(reason)`

When tripped:
- All new orders are rejected
- System enters cooldown period
- Manual reset required after cooldown

```python
# Check if tripped
if risk._state.circuit_breaker_tripped:
    print(f"Circuit breaker tripped: {risk._state.circuit_breaker_reason}")
    
    # Cancel all orders
    await exchange.cancel_all_orders(reason="circuit_breaker")
    
    # Wait for cooldown
    await asyncio.sleep(config.circuit_breaker_cooldown_minutes * 60)
    
    # Attempt reset
    if risk.reset_circuit_breaker():
        print("Circuit breaker reset")
    else:
        print("Still in cooldown")
```

## Audit Trail

All trading events are logged to immutable, append-only files:

```
logs/audit/
  audit-2025-02-11.jsonl
  audit-2025-02-12.jsonl
```

Events logged:
- Order submissions
- Order fills
- Order cancellations
- Position updates
- Position closes
- Risk rejections
- Circuit breaker trips
- Errors

Example audit entry:

```json
{
  "timestamp": "2025-02-11T15:30:45.123456Z",
  "type": "order_submitted",
  "symbol": "BTC-USD",
  "side": "buy",
  "quantity": 0.01,
  "price": 50000,
  "order_id": "order-123"
}
```

## Testing

Comprehensive test coverage included:

```bash
# Run risk manager tests
pytest backend/tests/unit/test_risk_manager.py -v

# Run position tracker tests
pytest backend/tests/unit/test_position_tracker.py -v

# Run all tests
pytest backend/tests/unit/ -v
```

## Safety Checklist

- [x] Every order passes through risk checks
- [x] Circuit breaker trips on consecutive losses/errors
- [x] Daily loss limit enforced
- [x] Position limits enforced
- [x] Price sanity checks (prevent fat-finger)
- [x] Positions tracked from fills (not polling)
- [x] Decimal arithmetic (no float for money)
- [x] Comprehensive audit logging
- [x] All risk rejections logged
- [x] WebSocket auto-reconnection (in HyperliquidClient)
- [x] Rate limiting with headroom

## Anti-Patterns Avoided

❌ Using `float` for money calculations  
✅ Using `Decimal` for all financial math

❌ Polling exchange for positions  
✅ Tracking positions from fills locally

❌ No risk checks ("just send the order")  
✅ Every order validated before submission

❌ Hardcoded risk limits  
✅ Configurable risk parameters

❌ No circuit breaker  
✅ Automatic circuit breaker on danger patterns

❌ No audit trail  
✅ Immutable append-only audit logs

## Environment Variables

```bash
# Risk limits (optional, can use config file)
RISK_MAX_DAILY_LOSS=500
RISK_MAX_POSITIONS=5
RISK_MAX_LEVERAGE=3
RISK_MAX_CONSECUTIVE_LOSSES=3
```

## Next Steps

To integrate into backtesting:

1. Initialize `RiskManager` and `PositionTracker` in backtest runner
2. Check orders through `risk.check_order()` before "execution"
3. Update positions with `tracker.update_from_fill()` on simulated fills
4. Track daily P&L for learning loop
5. Use MAE/MFE metrics for strategy evaluation

---

**Remember:** Every bug in a trading system is a potential financial loss. Build paranoid. Test thoroughly. Fail closed.
