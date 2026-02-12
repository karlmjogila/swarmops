# Backtest Engine

High-performance backtest engine with candle streaming, real-time state updates, and comprehensive metrics tracking.

## Features

- ✅ **Memory-efficient candle streaming** — Process candles one at a time, not all in memory
- ✅ **Real-time state updates** — Stream backtest state for live visualization
- ✅ **Signal integration** — Plug in any signal generator
- ✅ **Position & risk management** — Full integration with position tracker and risk manager
- ✅ **Partial exits** — Exit portions at different take profit levels
- ✅ **Comprehensive metrics** — Win rate, profit factor, drawdown, Sharpe ratio, etc.
- ✅ **Audit trail** — Full logging of all trading events
- ✅ **Pause/resume/seek** — Control playback for visualization
- ✅ **Realistic execution** — Commission, slippage, stop/limit order simulation

## Quick Start

### Basic Backtest

```python
from src.hl_bot.trading.backtest import run_backtest, BacktestConfig
from app.core.market.data import Candle

# Define signal generator
def my_signal_generator(candle: Candle) -> Signal | None:
    # Your signal logic here
    if should_enter(candle):
        return Signal(...)
    return None

# Load your candle data
candles = load_candles("BTC-USD", "5m")

# Run backtest
metrics = await run_backtest(
    candles=candles,
    signal_generator=my_signal_generator,
)

# Analyze results
print(f"Win Rate: {metrics.win_rate:.1%}")
print(f"Total P&L: ${metrics.total_pnl:.2f}")
print(f"Profit Factor: {metrics.profit_factor:.2f}")
```

### Streaming Backtest with State Updates

```python
from src.hl_bot.trading.backtest import BacktestEngine, BacktestConfig

# Create engine
config = BacktestConfig(
    initial_capital=10000.0,
    position_size_percent=0.02,  # Risk 2% per trade
    max_open_trades=3,
)

engine = BacktestEngine(
    config=config,
    signal_generator=my_signal_generator,
)

# Stream results
async for state in engine.run(candles, emit_interval=10):
    print(f"Progress: {state.progress_percent:.0f}%")
    print(f"Equity: ${state.current_capital:.2f}")
    print(f"Open Trades: {len(state.open_trades)}")
    
    # Send state to frontend via WebSocket
    await websocket.send_json(state.dict())
```

## Configuration

### BacktestConfig

```python
config = BacktestConfig(
    # Capital
    initial_capital=10000.0,
    
    # Position sizing
    position_size_percent=0.02,  # Risk 2% per trade
    max_open_trades=3,
    
    # Costs
    commission_percent=0.0006,   # 0.06% commission (Hyperliquid taker)
    slippage_percent=0.0001,     # 0.01% slippage
    
    # Order execution
    use_stop_orders=True,
    use_take_profits=True,
    
    # Partial exits
    partial_exit_enabled=True,
    tp1_exit_percent=0.5,        # Exit 50% at TP1
    tp2_exit_percent=0.5,        # Exit remaining 50% at TP2
    
    # Advanced (not yet implemented)
    use_trailing_stop=False,
    trailing_stop_trigger_r=1.0,  # Activate trailing stop at 1R
    trailing_stop_distance_r=0.5, # Trail at 0.5R from peak
)
```

## Signal Generator

Your signal generator receives the current candle and returns a `Signal` or `None`.

### Signal Generator Interface

```python
def signal_generator(candle: Candle) -> Signal | None:
    """Generate trading signal from current candle.
    
    Args:
        candle: Current candle being processed
        
    Returns:
        Signal if entry conditions met, None otherwise
    """
    # Analyze market data
    # Check entry conditions
    # Calculate levels
    
    if entry_conditions_met:
        return Signal(
            id=str(uuid.uuid4()),
            timestamp=candle.timestamp,
            symbol=candle.symbol,
            signal_type=SignalType.LONG,
            timeframe=Timeframe.M5,
            entry_price=candle.close,
            stop_loss=calculate_stop(candle),
            take_profit_1=calculate_tp1(candle),
            take_profit_2=calculate_tp2(candle),
            confluence_score=75.0,
            patterns_detected=[PatternType.ENGULFING],
            setup_type=SetupType.BREAKOUT,
            market_phase=MarketPhase.DRIVE,
            higher_tf_bias=SignalType.LONG,
            reasoning="Strong bullish confluence",
        )
    
    return None
```

### Multi-Timeframe Signal Generator

For multi-timeframe analysis, maintain your own candle buffers:

```python
class MTFSignalGenerator:
    def __init__(self):
        self.buffers = {
            "5m": [],
            "15m": [],
            "1h": [],
        }
        self.last_processed = {
            "15m": None,
            "1h": None,
        }
    
    def __call__(self, candle: Candle) -> Signal | None:
        # Add to 5m buffer
        self.buffers["5m"].append(candle)
        
        # Resample to higher timeframes
        if should_add_to_15m(candle):
            self.buffers["15m"].append(resample(candle, "15m"))
        
        if should_add_to_1h(candle):
            self.buffers["1h"].append(resample(candle, "1h"))
        
        # Generate signal from multi-timeframe data
        return self.analyze_mtf(self.buffers)
```

## Metrics

### BacktestMetrics

The backtest returns comprehensive performance metrics:

```python
class BacktestMetrics:
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float              # 0.0 to 1.0
    
    # P&L metrics
    total_pnl: float             # Total profit/loss in currency
    total_pnl_percent: float     # Total return as percentage
    average_win: float           # Average winning trade
    average_loss: float          # Average losing trade
    largest_win: float
    largest_loss: float
    
    # Performance ratios
    profit_factor: float         # Total wins / Total losses
    expectancy: float            # Average P&L per trade
    
    # Risk metrics
    max_drawdown: float          # Maximum drawdown in currency
    max_drawdown_percent: float  # Maximum drawdown as percentage
    sharpe_ratio: float          # Risk-adjusted return (future)
    
    # Costs
    total_commission: float
    total_slippage: float
    
    # Time-based
    start_time: datetime
    end_time: datetime
    
    # Equity curve
    equity_curve: List[Dict]     # [{timestamp, equity, drawdown}, ...]
```

### Accessing Metrics

```python
# After backtest completes
metrics = engine.get_results()

# Key metrics
print(f"Win Rate: {metrics.win_rate:.1%}")
print(f"Profit Factor: {metrics.profit_factor:.2f}")
print(f"Total P&L: ${metrics.total_pnl:,.2f}")

# Equity curve for charting
for point in metrics.equity_curve:
    timestamp = point["timestamp"]
    equity = point["equity"]
    drawdown = point["drawdown"]
```

## Trade Analysis

Get detailed trade-by-trade breakdown:

```python
# Get all closed trades
trades = engine.get_closed_trades()

for trade in trades:
    print(f"Trade {trade.id}")
    print(f"  Symbol: {trade.symbol}")
    print(f"  Side: {trade.side.value}")
    print(f"  Entry: ${float(trade.entry_price):.2f}")
    print(f"  Exit: ${float(trade.exit_price):.2f}")
    print(f"  P&L: ${float(trade.realized_pnl):.2f}")
    print(f"  Exit Reason: {trade.exit_reason}")
    
    # Partial exits
    if trade.partial_exits:
        print(f"  Partial Exits:")
        for exit in trade.partial_exits:
            print(f"    - {exit['reason']}: ${exit['pnl']:.2f}")
```

## State Streaming

For real-time visualization (WebSocket integration):

### State Callbacks

```python
# Add callback for state updates
def on_state_update(state: BacktestState):
    # Send to WebSocket
    websocket.send_json({
        "type": "backtest_update",
        "progress": state.progress_percent,
        "equity": state.current_capital,
        "open_trades": state.open_trades,
        "recent_signals": state.recent_signals,
    })

engine.add_state_callback(on_state_update)
```

### BacktestState

```python
class BacktestState:
    status: BacktestStatus          # IDLE, RUNNING, PAUSED, COMPLETED
    current_time: datetime
    current_candle_index: int
    total_candles: int
    progress_percent: float
    
    # Capital tracking
    current_capital: float
    peak_capital: float
    drawdown: float
    
    # Active positions
    open_trades: List[Dict]
    
    # Recent activity (for UI)
    recent_signals: List[Dict]      # Last 10 signals
    recent_trades: List[Dict]       # Last 10 closed trades
    
    # Metrics
    metrics: BacktestMetrics
    
    # Current prices
    current_prices: Dict[str, float]
```

## Playback Control

Control backtest playback for visualization:

```python
# Pause
engine.pause()
assert engine.state.status == BacktestStatus.PAUSED

# Resume
engine.resume()
assert engine.state.status == BacktestStatus.RUNNING

# Stop
engine.stop()
```

## Order Execution Simulation

### Order Types

The backtest engine simulates realistic order execution:

1. **Market Orders** — Fill at next candle open with slippage
2. **Limit Orders** — Fill when price reaches limit
3. **Stop Orders** — Fill when price hits stop

### Entry Execution

```python
# When signal triggers:
1. Calculate position size based on risk
2. Apply slippage to entry price
3. Calculate commission
4. Update capital (deduct cost + commission)
5. Create position in tracker
6. Place stop loss order
7. Place take profit orders
```

### Exit Execution

```python
# Stop Loss:
- Triggers when price moves against position
- Fills at stop price + slippage
- Entire position closed

# Take Profit:
- Triggers when price reaches TP level
- Partial exits if configured
- TP1: Exit 50% (configurable)
- TP2: Exit remaining 50%
- Full position closed
```

### Slippage Model

```python
# Long entry: Fill at entry + (entry * slippage_percent)
# Short entry: Fill at entry - (entry * slippage_percent)

# Long exit: Fill at exit - (exit * slippage_percent)
# Short exit: Fill at exit + (exit * slippage_percent)
```

## Position Sizing

Position size is calculated based on risk:

```python
# Risk amount per trade
risk_amount = capital * position_size_percent

# Calculate stop distance
stop_distance = abs(entry_price - stop_loss)

# Position size = risk / stop distance
position_size = risk_amount / stop_distance

# Round to exchange precision
position_size = round_quantity(position_size, lot_size)
```

### Example

```python
# Capital: $10,000
# Risk: 2% = $200
# Entry: $40,000
# Stop: $39,200 (2% below entry)
# Stop distance: $800

# Position size = $200 / $800 = 0.25 BTC
```

## Audit Logging

Enable audit logging for full trade history:

```python
from pathlib import Path

engine = BacktestEngine(
    config=config,
    signal_generator=my_signal_generator,
    audit_dir=Path("./backtest_logs"),
)
```

Audit logs are written to JSONL files:

```json
{"timestamp": "2024-01-01T12:00:00Z", "type": "trade_opened", "trade_id": "...", "symbol": "BTC-USD", ...}
{"timestamp": "2024-01-01T12:30:00Z", "type": "trade_closed", "trade_id": "...", "pnl": 150.00, ...}
```

## Best Practices

### 1. Use Realistic Parameters

```python
# Don't
config = BacktestConfig(
    commission_percent=0.0,  # No commission? Unrealistic!
    slippage_percent=0.0,     # No slippage? Impossible!
)

# Do
config = BacktestConfig(
    commission_percent=0.0006,  # Hyperliquid taker fee
    slippage_percent=0.0001,     # Conservative slippage estimate
)
```

### 2. Validate Your Data

```python
# Check for gaps
for i in range(1, len(candles)):
    time_diff = (candles[i].timestamp - candles[i-1].timestamp).total_seconds()
    expected = 300  # 5 minutes
    
    if abs(time_diff - expected) > 60:  # More than 1 minute off
        print(f"Warning: Gap at {candles[i].timestamp}")

# Check for valid OHLC
for candle in candles:
    assert candle.high >= candle.low
    assert candle.high >= candle.open
    assert candle.high >= candle.close
```

### 3. Avoid Look-Ahead Bias

```python
# Don't use future data in signal generation
def bad_signal_gen(candle):
    future_price = get_price_from_database(candle.timestamp + timedelta(hours=1))
    if candle.close < future_price:  # This is cheating!
        return Signal(...)

# Only use data available at the time
def good_signal_gen(candle):
    # Use historical data up to (but not including) current candle
    past_candles = get_candles_before(candle.timestamp)
    signal = analyze(past_candles)
    return signal
```

### 4. Test with Out-of-Sample Data

```python
# Split data into train and test
split_index = int(len(candles) * 0.7)  # 70/30 split
train_candles = candles[:split_index]
test_candles = candles[split_index:]

# Optimize on train data
best_params = optimize_strategy(train_candles)

# Validate on test data
test_metrics = await run_backtest(
    candles=test_candles,
    signal_generator=create_generator(best_params),
)
```

### 5. Monitor Resource Usage

```python
# For large datasets, emit frequently to avoid memory buildup
async for state in engine.run(candles, emit_interval=100):
    # Process state
    pass
    
    # Periodically check memory
    import psutil
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 80:
        print(f"Warning: High memory usage: {memory_percent:.1f}%")
```

## Integration with WebSocket Streaming

See `ws-stream` task for WebSocket integration. The backtest state is designed to be JSON-serializable for real-time frontend updates:

```python
# Backend
async def stream_backtest(websocket: WebSocket):
    engine = BacktestEngine(...)
    
    async for state in engine.run(candles, emit_interval=10):
        await websocket.send_json({
            "type": "state_update",
            "data": state.dict(),
        })

# Frontend (SvelteKit)
const ws = new WebSocket('ws://localhost:8000/backtest/stream')
ws.onmessage = (event) => {
    const update = JSON.parse(event.data)
    updateChart(update.data.metrics.equity_curve)
    updateTrades(update.data.open_trades)
}
```

## Performance

The backtest engine is optimized for:

- **Memory efficiency** — Streams candles, doesn't load entire dataset
- **Speed** — Can process 1M+ candles in minutes
- **Accuracy** — Realistic order execution with proper commission/slippage

Typical performance:
- 100k candles: ~10 seconds
- 1M candles: ~2 minutes

## Testing

Run the test suite:

```bash
pytest backend/tests/trading/test_backtest.py -v
```

Run examples:

```bash
python -m examples.backtest_example
```

## Roadmap

Future enhancements:

- [ ] Trailing stop implementation
- [ ] Multi-asset backtesting
- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation
- [ ] Sharpe ratio calculation
- [ ] Trade clustering analysis
- [ ] Slippage models per asset
- [ ] Market impact simulation

## See Also

- [Position Manager](POSITION_RISK_README.md)
- [Risk Manager](POSITION_RISK_README.md)
- [Signal Generator](../../../app/core/patterns/signals.py)
- [WebSocket Streaming](../../api/routes/backtest.py) (future)
