# Signal Generator

The signal generator module converts multi-timeframe confluence analysis into actionable trading signals with proper entry, stop loss, and take profit levels.

## Overview

**Core Principle:** Safety over speed. A missed trade costs nothing. A bad trade costs everything.

The signal generator:
- ✅ Validates confluence meets minimum thresholds
- ✅ Calculates entry, stop loss, and take profit levels
- ✅ Ensures minimum risk-reward ratios
- ✅ Places stops beyond market structure
- ✅ Aligns targets with support/resistance zones
- ✅ Provides full reasoning for every signal

## Quick Start

```python
from app.core.patterns.signals import generate_signal

# Create multi-timeframe data
mtf_data = {
    "5m": candles_5m,
    "15m": candles_15m,
    "1h": candles_1h,
}

# Generate signal
signal = generate_signal(mtf_data, "15m", "BTC-USD")

if signal:
    print(f"Signal: {signal.signal_type}")
    print(f"Entry: ${signal.entry_price:,.2f}")
    print(f"Stop: ${signal.stop_loss:,.2f}")
    print(f"TP1: ${signal.take_profit_1:,.2f}")
    print(f"TP2: ${signal.take_profit_2:,.2f}")
```

## Configuration

Customize signal generation for your trading style:

```python
from app.core.patterns.signals import (
    SignalGenerator,
    SignalGenerationConfig,
)

# Conservative configuration
config = SignalGenerationConfig(
    min_confluence_score=70.0,        # Only high-confidence setups
    min_agreement_percentage=80.0,    # Strong timeframe alignment
    min_risk_reward=3.0,              # 3:1 minimum R:R
    max_stop_loss_percent=0.02,       # 2% max stop loss
    require_higher_tf_alignment=True, # Must align with higher TF
)

generator = SignalGenerator(config=config)
signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_confluence_score` | 50.0 | Minimum confluence score (0-100) |
| `min_agreement_percentage` | 60.0 | Minimum % of timeframes agreeing |
| `require_higher_tf_alignment` | True | Require higher TF to align |
| `min_risk_reward` | 2.0 | Minimum risk-reward ratio |
| `max_stop_loss_percent` | 0.03 | Maximum stop loss (3% of entry) |
| `use_atr_stops` | True | Use ATR for dynamic stops |
| `atr_multiplier` | 1.5 | ATR multiplier for stop distance |
| `require_zone_confluence` | True | Require price near S/R zone |
| `require_structure_break` | False | Require recent structure break |

## Signal Components

### Entry Price
- Current market price
- Future: Limit orders at zone boundaries

### Stop Loss
Priority order:
1. Beyond recent swing low/high
2. Beyond nearest support/resistance zone
3. ATR-based fallback

**Validation:**
- Must invalidate the setup if hit
- Maximum distance: 3% of entry (configurable)
- Always on correct side of entry

### Take Profits
- **TP1:** Conservative (1.5R) - Take 50% off
- **TP2:** Main target (minimum R:R) - Take 30% off
- **TP3:** Extended target (1.5x TP2) - Trail remaining 20%

**Alignment:**
- TP2 aligned with resistance/support zones when possible
- TP3 only generated for high-confidence setups (>70 confluence)

### Risk-Reward Ratios

Minimum R:R based on confluence:
- High confidence (>70): 2.0:1
- Medium confidence (50-70): 2.5:1
- Low confidence (<50): 3.0:1

## Signal Output

```python
Signal(
    id="uuid",
    timestamp=datetime,
    symbol="BTC-USD",
    signal_type=SignalType.LONG,
    timeframe=Timeframe.M15,
    entry_price=50000.0,
    stop_loss=49500.0,
    take_profit_1=50750.0,
    take_profit_2=51000.0,
    take_profit_3=51500.0,
    confluence_score=75.5,
    patterns_detected=[PatternType.ENGULFING],
    setup_type=SetupType.BREAKOUT,
    market_phase=MarketPhase.DRIVE,
    higher_tf_bias=SignalType.LONG,
    reasoning="Confluence score: 75.5/100 (bullish) | ..."
)
```

## Validation Checks

Every signal passes through multiple validation layers:

### 1. Confluence Threshold
```python
if confluence_score < min_confluence_score:
    return None  # No signal
```

### 2. Timeframe Agreement
```python
if agreement_percentage < min_agreement_percentage:
    return None
```

### 3. Stop Loss Validation
```python
# LONG: stop must be below entry
# SHORT: stop must be above entry
if not valid:
    return None
```

### 4. Take Profit Validation
```python
# LONG: TPs must be above entry
# SHORT: TPs must be below entry
if not valid:
    return None
```

### 5. Risk-Reward Validation
```python
if actual_rr < minimum_rr:
    return None  # R:R too low
```

### 6. Higher Timeframe Alignment
```python
if require_higher_tf_alignment:
    if higher_tf_conflicts_with_signal:
        add_warning()  # Signal may still generate with warning
```

## Position Sizing

Use the signal's risk metrics for position sizing:

```python
if signal:
    account_balance = 10000  # $10k account
    risk_per_trade = 0.01    # 1% risk
    
    risk_dollar = account_balance * risk_per_trade  # $100
    risk_per_coin = abs(signal.entry_price - signal.stop_loss)  # $500
    
    position_size = risk_dollar / risk_per_coin  # 0.2 BTC
    notional_value = position_size * signal.entry_price  # $10,000
```

## Trade Management

Recommended exit strategy:

```python
# At TP1 (1.5R)
- Close 50% of position
- Move stop to breakeven

# At TP2 (2-3R)
- Close 30% of position
- Trail stop to lock profits

# At TP3 or trailing
- Close remaining 20%
- Or continue trailing
```

## Examples

See `examples/signal_generator_example.py` for:
- Basic signal generation
- Different risk management configs
- Bullish and bearish signals
- Mixed timeframe handling
- Position sizing calculations
- Trade management strategies

Run examples:
```bash
cd backend
poetry run python examples/signal_generator_example.py
```

## Testing

Run tests:
```bash
cd backend
poetry run pytest tests/core/patterns/test_signals.py -v
```

All tests validate:
- Signal generation logic
- Risk-reward calculations
- Stop loss placement
- Take profit placement
- Configuration options
- Edge cases and validation

## Safety Features

### Defensive Validation
- Every price level validated before signal generation
- Invalid signals return None (never throw exceptions)
- All monetary calculations use Decimal (no float precision errors)

### Risk Controls
- Maximum stop loss distance enforced
- Minimum R:R ratios enforced
- Stop loss must invalidate the setup
- No signals on low confluence

### Audit Trail
Each signal includes:
- Full reasoning string
- Confluence breakdown
- Pattern types detected
- Setup classification
- Market phase identification
- Warnings for conflicting signals

## Architecture

```
┌─────────────────┐
│ MTF Candle Data │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Confluence    │
│     Scorer      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Signal      │ ◄─── Configuration
│   Generator     │
└────────┬────────┘
         │
         ├─► Threshold Check
         ├─► Level Calculation
         ├─► Risk Validation
         └─► Signal Output
```

## Integration

### With Backtester
```python
from app.core.patterns.signals import SignalGenerator

generator = SignalGenerator()

for candle_update in backtest:
    # Update multi-timeframe data
    mtf_data = update_timeframes(candle_update)
    
    # Generate signal
    signal = generator.generate_signal(
        mtf_data,
        analysis_timeframe="15m",
        symbol=candle_update.symbol,
    )
    
    if signal:
        # Execute trade
        place_order(signal)
```

### With Live Trading
```python
# On each timeframe update
def on_candle(candle):
    mtf_data = get_multi_timeframe_data(candle.symbol)
    
    signal = generate_signal(
        mtf_data,
        analysis_timeframe="15m",
        symbol=candle.symbol,
    )
    
    if signal:
        # Risk check before execution
        if risk_manager.approve(signal):
            place_order(signal)
```

## Best Practices

### DO ✅
- Always validate signal is not None before using
- Use appropriate configuration for your strategy
- Size positions based on account risk (1-2% per trade)
- Respect higher timeframe bias
- Take partial profits at TP1 and TP2
- Move stop to breakeven after TP1

### DON'T ❌
- Don't take every signal (confluence matters)
- Don't override stop loss placement
- Don't use excessive leverage
- Don't ignore higher timeframe conflicts
- Don't risk more than 2% per trade
- Don't skip risk validation

## Anti-Patterns

**Fire-and-forget:**
```python
# ❌ Bad
signal = generate_signal(...)
place_order(signal)  # No validation!
```

```python
# ✅ Good
signal = generate_signal(...)
if signal and risk_manager.approve(signal):
    place_order(signal)
```

**Ignoring confluence:**
```python
# ❌ Bad
config = SignalGenerationConfig(min_confluence_score=20.0)  # Too low!
```

```python
# ✅ Good
config = SignalGenerationConfig(min_confluence_score=60.0)  # Reasonable
```

**Fixed stop distance:**
```python
# ❌ Bad
stop_loss = entry_price * 0.98  # Always 2%
```

```python
# ✅ Good
# Let signal generator place stop based on structure
signal = generate_signal(...)
stop_loss = signal.stop_loss  # Based on market structure
```

## Troubleshooting

**No signals generated:**
- Check confluence scores are above threshold
- Verify timeframe agreement percentage
- Review conflicting timeframes
- Lower thresholds temporarily for testing

**Signals rejected by risk validation:**
- Stop loss too wide (>3% default)
- R:R ratio below minimum
- Take profits on wrong side of entry
- Check structure and zones exist in data

**Unexpected signal direction:**
- Review confluence breakdown
- Check higher timeframe bias
- Verify pattern signals align
- Look for conflicting timeframes

## Performance

- Signal generation: <10ms typical
- Memory efficient (uses existing confluence data)
- No external API calls
- Deterministic (same data = same signal)

## Future Enhancements

- [ ] Limit order entry strategies
- [ ] Advanced zone alignment for TPs
- [ ] Dynamic R:R based on volatility
- [ ] Machine learning for TP optimization
- [ ] Backtested configuration presets
- [ ] Signal quality scoring (beyond confluence)

---

**Remember:** A missed trade costs nothing. A bad trade costs everything.
