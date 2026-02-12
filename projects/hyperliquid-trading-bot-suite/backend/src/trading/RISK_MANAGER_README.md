# Risk Manager Documentation

## Overview

The Risk Manager is a comprehensive risk management system for the Hyperliquid Trading Bot Suite. It provides account-level risk controls, position validation, real-time monitoring, and automated circuit breakers to protect capital.

## Features

### 🛡️ Core Risk Management

- **Pre-trade Validation**: Validate trades against all risk criteria before execution
- **Position Sizing**: Automatic position size calculation based on risk percentage
- **Daily Loss Limits**: Enforce maximum daily loss thresholds
- **Drawdown Protection**: Monitor and respond to account drawdown
- **Correlation Awareness**: Track exposure across correlated assets
- **Loss Streak Detection**: Identify and respond to consecutive losing trades

### 📊 Real-time Monitoring

- **P&L Tracking**: Real-time tracking of realized and unrealized P&L
- **Asset Exposure**: Monitor position exposure across all assets
- **Risk Metrics**: Continuous calculation of risk metrics and statistics
- **Circuit Breakers**: Automated trading halts on risk limit breaches

### 🔄 Trading States

The risk manager operates in different states based on current risk levels:

- **ACTIVE**: Normal trading operations
- **REDUCED**: Reduced position sizes (triggered at 75% of daily loss limit)
- **HALT**: No new positions allowed (triggered at daily loss limit or loss streak)
- **EMERGENCY**: Close all positions (triggered at emergency threshold)

### 📈 Risk Levels

Risk checks are categorized by severity:

- **LOW**: All checks passed, normal operations
- **MEDIUM**: Some warnings present, proceed with caution
- **HIGH**: Approaching limits, reduced trading recommended
- **CRITICAL**: Limits breached, immediate action required

## Configuration

### Risk Limits

Configure risk limits via the `RiskLimits` class:

```python
from src.trading import RiskLimits

risk_limits = RiskLimits(
    # Daily limits
    max_daily_loss_percent=6.0,              # Max 6% daily loss
    max_daily_loss_absolute=None,            # Optional absolute limit
    
    # Position limits
    max_concurrent_positions=3,              # Max 3 positions at once
    max_position_size_percent=10.0,          # Max 10% of account per position
    
    # Per-trade risk
    default_risk_percent=2.0,                # Default 2% risk per trade
    max_risk_per_trade_percent=3.0,          # Never exceed 3% per trade
    
    # Correlation limits
    max_correlated_exposure_percent=15.0,    # Max 15% in correlated assets
    
    # Drawdown limits
    max_drawdown_percent=15.0,               # Stop at 15% drawdown
    
    # Leverage limits
    max_leverage=5.0,
    default_leverage=1.0,
    
    # Cooldown periods
    loss_streak_limit=3,                     # Halt after 3 consecutive losses
    cooldown_after_daily_limit_hours=24,
    
    # Emergency stops
    max_slippage_percent=1.0,
    emergency_close_threshold_percent=10.0   # Emergency close if >10% loss
)
```

## Usage

### Basic Setup

```python
from src.trading import HyperliquidClient, PositionManager, RiskManager, RiskLimits

# Initialize components
client = HyperliquidClient(api_key="key", secret_key="secret", testnet=True)
position_manager = PositionManager(client)

# Create risk manager with custom limits
risk_limits = RiskLimits(max_daily_loss_percent=6.0)
risk_manager = RiskManager(client, position_manager, risk_limits)

# Initialize and start monitoring
await risk_manager.initialize()
await risk_manager.start_monitoring()
await position_manager.start_monitoring()
```

### Trade Validation

```python
# Calculate position size
position_size = await risk_manager.calculate_position_size(
    asset="BTC",
    entry_price=50000.0,
    stop_loss=49500.0,
    risk_percent=2.0
)

# Validate trade
risk_check = await risk_manager.validate_trade(
    asset="BTC",
    side=OrderSide.LONG,
    size=position_size,
    entry_price=50000.0,
    stop_loss=49500.0
)

if risk_check.passed:
    print(f"✅ Trade approved: {risk_check.message}")
    if risk_check.warnings:
        for warning in risk_check.warnings:
            print(f"⚠️  {warning}")
    
    # Execute trade
    # ...
else:
    print(f"❌ Trade rejected: {risk_check.message}")
    if risk_check.suggested_size:
        print(f"💡 Suggested size: {risk_check.suggested_size}")
```

### Trade Lifecycle Management

```python
# When opening a trade
await risk_manager.on_trade_opened(trade_record, position)

# When closing a trade
await risk_manager.on_trade_closed(
    trade_record=trade_record,
    exit_price=exit_price,
    pnl=pnl,
    outcome=TradeOutcome.WIN  # or TradeOutcome.LOSS
)
```

### Risk Alerts and Callbacks

```python
def risk_alert_handler(level: RiskLevel, message: str):
    """Handle risk alerts."""
    if level == RiskLevel.CRITICAL:
        print(f"🚨 CRITICAL: {message}")
        # Send urgent notification
    elif level == RiskLevel.HIGH:
        print(f"⚠️  HIGH RISK: {message}")
        # Send warning notification

def state_change_handler(old_state: TradingState, new_state: TradingState):
    """Handle trading state changes."""
    print(f"🔄 State changed: {old_state.value} → {new_state.value}")
    if new_state == TradingState.HALT:
        print("🛑 Trading halted - review risk limits")

# Register callbacks
risk_manager.add_risk_alert_callback(risk_alert_handler)
risk_manager.add_state_change_callback(state_change_handler)
```

### Risk Reporting

```python
# Get current state
state = risk_manager.get_current_state()
print(f"Trading State: {state['trading_state']}")
print(f"Daily P&L: ${state['daily_metrics']['total_pnl']:.2f}")
print(f"Win Rate: {state['daily_metrics']['win_rate']:.1f}%")

# Get daily metrics
metrics = risk_manager.get_daily_metrics()  # Today's metrics
print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
print(f"Consecutive Losses: {risk_manager.consecutive_losses}")

# Export daily report
report = await risk_manager.export_daily_report()
# Save or send report
```

### Manual Overrides

```python
# Reset circuit breaker (use with caution)
await risk_manager.reset_circuit_breaker()

# Manual state override (extreme caution required)
await risk_manager.manual_override_state(TradingState.ACTIVE)
```

## Risk Check Process

When validating a trade, the risk manager performs these checks in order:

1. **Circuit Breaker Check**: Is trading halted due to previous risk events?
2. **Trading State Check**: Is the current trading state allowing new positions?
3. **Daily Loss Limit**: Has the daily loss limit been reached or approached?
4. **Position Count Limit**: Are we at max concurrent positions?
5. **Per-Trade Risk Limit**: Does this trade exceed maximum risk per trade?
6. **Position Size Limit**: Is the position size too large relative to account?
7. **Correlation Exposure**: Would this trade create excessive correlated exposure?
8. **Loss Streak Check**: Are we in a loss streak that requires halting?

If any check fails, the trade is rejected with a detailed reason. Some checks provide suggested adjustments (e.g., reduced position size).

## Monitoring Logic

The risk manager continuously monitors:

### Account Level
- Current balance and P&L
- Daily profit/loss percentage
- Drawdown from peak balance
- Number of active positions

### Position Level
- Individual position P&L
- Asset-specific exposure
- Correlation-based exposure
- Unrealized P&L across all positions

### Trade Statistics
- Win/loss ratio
- Consecutive losses
- Trade frequency
- Total fees paid

### Automated Actions

Based on monitoring, the risk manager automatically:

- **Transitions to REDUCED state** at 75% of daily loss limit
- **Activates HALT state** when daily loss limit reached
- **Triggers circuit breaker** on critical events
- **Sends risk alerts** through callback system
- **Closes all positions** in EMERGENCY state

## Integration with Position Manager

The risk manager integrates seamlessly with the Position Manager:

```python
# Position manager handles trade execution
await position_manager.manage_position(position, trade_record, current_price)

# Risk manager monitors the overall account risk
# No additional integration code needed - automatic
```

Both managers run concurrent monitoring loops and communicate through:
- Shared Hyperliquid client
- Trade lifecycle callbacks
- Real-time position state updates

## Best Practices

### 1. Always Validate Before Trading
Never execute a trade without calling `validate_trade()` first.

### 2. Monitor Risk Alerts
Implement proper alert handling for CRITICAL and HIGH risk events.

### 3. Respect Circuit Breakers
Don't override circuit breakers without thoroughly reviewing what triggered them.

### 4. Review Daily Reports
Export and review daily risk reports to identify patterns and improve strategy.

### 5. Configure Limits Appropriately
Set risk limits based on your account size, strategy, and risk tolerance.

### 6. Test in Paper Mode First
Always test risk manager configuration in paper trading before going live.

## Examples

See `risk_manager_example.py` for comprehensive examples including:

- Basic usage and configuration
- Trade validation workflow
- Complete trade lifecycle
- Risk reporting and monitoring
- Circuit breaker scenarios
- Position sizing calculations

## API Reference

### RiskManager

#### Methods

- `initialize()`: Initialize with current account state
- `start_monitoring()`: Start risk monitoring loop
- `stop_monitoring()`: Stop risk monitoring loop
- `validate_trade(...)`: Validate a proposed trade
- `calculate_position_size(...)`: Calculate optimal position size
- `on_trade_opened(...)`: Handle trade opening event
- `on_trade_closed(...)`: Handle trade closing event
- `get_current_state()`: Get current risk state snapshot
- `get_daily_metrics()`: Get daily risk metrics
- `export_daily_report()`: Export comprehensive daily report
- `add_risk_alert_callback(...)`: Register risk alert handler
- `add_state_change_callback(...)`: Register state change handler
- `manual_override_state(...)`: Manually override trading state
- `reset_circuit_breaker()`: Reset circuit breaker

### RiskCheck

Result object from `validate_trade()`:

```python
@dataclass
class RiskCheck:
    passed: bool              # Whether trade is approved
    risk_level: RiskLevel     # Severity level
    message: str              # Explanation
    suggested_size: float     # Suggested adjustment (if applicable)
    warnings: List[str]       # Warning messages
```

### DailyRiskMetrics

Daily risk tracking data:

```python
@dataclass
class DailyRiskMetrics:
    date: str
    starting_balance: float
    current_balance: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    trades_executed: int
    trades_won: int
    trades_lost: int
    max_drawdown: float
    # ... additional fields
```

## Performance Considerations

- Monitoring loop runs every 5 seconds (configurable)
- Position exposure updates on each monitoring cycle
- Daily metrics cached between updates
- Callbacks executed asynchronously
- All I/O operations are async for minimal blocking

## Future Enhancements

Planned features for future versions:

- [ ] Machine learning-based risk scoring
- [ ] Advanced correlation matrix with real-time correlation calculations
- [ ] Portfolio heat maps and risk visualization
- [ ] Historical risk metric persistence to database
- [ ] Risk-adjusted position sizing based on volatility
- [ ] Integration with external risk data providers
- [ ] Multi-account risk aggregation
- [ ] Advanced stress testing and scenario analysis

## Troubleshooting

### Circuit Breaker Won't Reset

Check `circuit_breaker_until` timestamp. Circuit breaker has a cooldown period (default 24h).

### Position Size Calculation Returns 0

Verify that entry price ≠ stop loss price. Check that account balance is properly initialized.

### Risk Alerts Not Triggering

Ensure monitoring loop is started with `start_monitoring()`. Verify callbacks are registered.

### Trading State Stuck in HALT

Review what triggered the HALT state. Address the underlying issue before resetting.

## Support

For issues, questions, or feature requests related to the Risk Manager, please refer to the main project documentation or contact the development team.
