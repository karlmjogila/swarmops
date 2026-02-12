"""Example: Running a backtest with the BacktestEngine.

This example demonstrates:
1. Loading candle data
2. Creating a signal generator
3. Running a backtest with streaming
4. Analyzing results

Run with: python -m examples.backtest_example
"""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.hl_bot.trading.backtest import (
    BacktestEngine,
    BacktestConfig,
    BacktestStatus,
    run_backtest,
)
from src.hl_bot.types import Signal, SignalType, SetupType, MarketPhase, PatternType, Timeframe
from app.core.market.data import Candle


def create_sample_candles(count: int = 200, start_price: float = 40000.0) -> list[Candle]:
    """Create sample candle data with realistic price movement.
    
    Args:
        count: Number of candles to generate
        start_price: Starting price
        
    Returns:
        List of candles with simulated price movement
    """
    candles = []
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    price = start_price
    
    # Simulate price movement with trend and noise
    for i in range(count):
        # Add trend (slight uptrend)
        trend = 5 if i < count // 2 else -3
        
        # Add noise
        import random
        noise = random.uniform(-10, 10)
        
        # Update price
        price = price + trend + noise
        
        # Ensure positive
        price = max(price, 1000)
        
        # Create OHLCV with realistic spread
        spread = price * 0.001  # 0.1% spread
        
        candle = Candle(
            timestamp=start_time + timedelta(minutes=i * 5),
            open=price - spread / 2,
            high=price + spread,
            low=price - spread,
            close=price,
            volume=random.uniform(800, 1200),
            symbol="BTC-USD",
            timeframe="5m",
        )
        
        candles.append(candle)
    
    return candles


def simple_signal_generator(candle: Candle) -> Signal | None:
    """Simple signal generator for demonstration.
    
    This is a naive strategy for example purposes only!
    Real strategies should use proper technical analysis.
    
    Args:
        candle: Current candle
        
    Returns:
        Signal if conditions met, None otherwise
    """
    import random
    
    # Simple condition: Random signals for demonstration
    # In real use, this would analyze patterns, structure, zones, etc.
    if random.random() < 0.05:  # 5% chance of signal
        signal_type = SignalType.LONG if random.random() > 0.5 else SignalType.SHORT
        
        entry = candle.close
        
        if signal_type == SignalType.LONG:
            stop = entry * 0.98  # 2% stop
            tp1 = entry * 1.03   # 3% TP1 (1.5R)
            tp2 = entry * 1.04   # 4% TP2 (2R)
        else:
            stop = entry * 1.02
            tp1 = entry * 0.97
            tp2 = entry * 0.96
        
        return Signal(
            id=f"signal-{candle.timestamp.timestamp()}",
            timestamp=candle.timestamp,
            symbol=candle.symbol,
            signal_type=signal_type,
            timeframe=Timeframe.M5,
            entry_price=entry,
            stop_loss=stop,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confluence_score=random.uniform(60, 85),
            patterns_detected=[PatternType.ENGULFING],
            setup_type=SetupType.BREAKOUT,
            market_phase=MarketPhase.DRIVE,
            higher_tf_bias=signal_type,
            reasoning="Example signal - random generation for demo",
        )
    
    return None


async def example_basic_backtest():
    """Example 1: Basic backtest with default config."""
    print("=" * 60)
    print("Example 1: Basic Backtest")
    print("=" * 60)
    
    # Create sample data
    candles = create_sample_candles(200)
    print(f"Created {len(candles)} candles")
    print(f"Date range: {candles[0].timestamp} to {candles[-1].timestamp}")
    print(f"Price range: ${candles[0].close:.2f} to ${candles[-1].close:.2f}")
    print()
    
    # Run backtest
    print("Running backtest...")
    metrics = await run_backtest(
        candles=candles,
        signal_generator=simple_signal_generator,
    )
    
    # Print results
    print("\nResults:")
    print(f"  Total Trades: {metrics.total_trades}")
    print(f"  Win Rate: {metrics.win_rate:.1%}")
    print(f"  Total P&L: ${metrics.total_pnl:.2f} ({metrics.total_pnl_percent:.2f}%)")
    print(f"  Average Win: ${metrics.average_win:.2f}")
    print(f"  Average Loss: ${metrics.average_loss:.2f}")
    print(f"  Profit Factor: {metrics.profit_factor:.2f}")
    print(f"  Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_percent:.2f}%)")
    print(f"  Commission Paid: ${metrics.total_commission:.2f}")
    print()


async def example_custom_config():
    """Example 2: Backtest with custom configuration."""
    print("=" * 60)
    print("Example 2: Custom Configuration")
    print("=" * 60)
    
    # Create config with custom parameters
    config = BacktestConfig(
        initial_capital=50000.0,
        position_size_percent=0.01,  # Risk 1% per trade (conservative)
        max_open_trades=3,
        commission_percent=0.0006,
        slippage_percent=0.0001,
        partial_exit_enabled=True,
        tp1_exit_percent=0.5,  # Exit 50% at TP1
    )
    
    print(f"Initial Capital: ${config.initial_capital:,.2f}")
    print(f"Position Size: {config.position_size_percent:.1%} risk per trade")
    print(f"Max Open Trades: {config.max_open_trades}")
    print()
    
    # Create data
    candles = create_sample_candles(200)
    
    # Run backtest
    print("Running backtest with custom config...")
    metrics = await run_backtest(
        candles=candles,
        signal_generator=simple_signal_generator,
        config=config,
    )
    
    # Print results
    print("\nResults:")
    print(f"  Total Trades: {metrics.total_trades}")
    print(f"  Win Rate: {metrics.win_rate:.1%}")
    print(f"  Total P&L: ${metrics.total_pnl:.2f} ({metrics.total_pnl_percent:.2f}%)")
    print(f"  Profit Factor: {metrics.profit_factor:.2f}")
    print(f"  Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_percent:.2f}%)")
    print()


async def example_streaming_with_callbacks():
    """Example 3: Streaming backtest with state callbacks."""
    print("=" * 60)
    print("Example 3: Streaming with State Updates")
    print("=" * 60)
    
    # Create data
    candles = create_sample_candles(200)
    
    # Create engine
    config = BacktestConfig(initial_capital=10000.0)
    engine = BacktestEngine(config=config, signal_generator=simple_signal_generator)
    
    # Add callback for state updates
    update_count = 0
    
    def on_state_update(state):
        nonlocal update_count
        update_count += 1
    
    engine.add_state_callback(on_state_update)
    
    # Run with streaming
    print("Running backtest with streaming...")
    last_progress = 0
    
    async for state in engine.run(candles, emit_interval=20):
        # Print progress
        if state.progress_percent >= last_progress + 10:
            print(f"  Progress: {state.progress_percent:.0f}% | "
                  f"Equity: ${state.current_capital:.2f} | "
                  f"Open Trades: {len(state.open_trades)}")
            last_progress = state.progress_percent
    
    # Print final results
    metrics = engine.get_results()
    print("\nFinal Results:")
    print(f"  Total Trades: {metrics.total_trades}")
    print(f"  Win Rate: {metrics.win_rate:.1%}")
    print(f"  Total P&L: ${metrics.total_pnl:.2f}")
    print(f"  State Updates: {update_count}")
    print()


async def example_trade_analysis():
    """Example 4: Detailed trade analysis."""
    print("=" * 60)
    print("Example 4: Trade-by-Trade Analysis")
    print("=" * 60)
    
    # Create data
    candles = create_sample_candles(200)
    
    # Run backtest
    config = BacktestConfig(initial_capital=10000.0)
    engine = BacktestEngine(config=config, signal_generator=simple_signal_generator)
    
    async for state in engine.run(candles):
        pass  # Run to completion
    
    # Get closed trades
    trades = engine.get_closed_trades()
    
    print(f"\nTotal Trades: {len(trades)}")
    print("\nTrade Details:")
    print("-" * 80)
    
    for i, trade in enumerate(trades[:10], 1):  # Show first 10 trades
        pnl_sign = "+" if trade.realized_pnl >= 0 else ""
        print(f"\nTrade {i}:")
        print(f"  Symbol: {trade.symbol}")
        print(f"  Side: {trade.side.value.upper()}")
        print(f"  Entry: ${float(trade.entry_price):.2f} @ {trade.entry_time}")
        print(f"  Exit: ${float(trade.exit_price):.2f} @ {trade.exit_time}")
        print(f"  Size: {float(trade.position_size):.4f}")
        print(f"  P&L: {pnl_sign}${float(trade.realized_pnl):.2f} ({pnl_sign}{float(trade.realized_pnl_percent):.2f}%)")
        print(f"  Reason: {trade.exit_reason}")
        
        if trade.partial_exits:
            print(f"  Partial Exits: {len(trade.partial_exits)}")
            for exit in trade.partial_exits:
                print(f"    - {exit['reason']}: ${exit['pnl']:.2f}")
    
    if len(trades) > 10:
        print(f"\n... and {len(trades) - 10} more trades")
    
    print()


async def example_equity_curve():
    """Example 5: Equity curve visualization."""
    print("=" * 60)
    print("Example 5: Equity Curve")
    print("=" * 60)
    
    # Create data
    candles = create_sample_candles(200)
    
    # Run backtest
    config = BacktestConfig(initial_capital=10000.0)
    engine = BacktestEngine(config=config, signal_generator=simple_signal_generator)
    
    async for state in engine.run(candles):
        pass
    
    # Get equity curve
    metrics = engine.get_results()
    equity_curve = metrics.equity_curve
    
    print(f"\nEquity Curve Points: {len(equity_curve)}")
    print("\nSample Points:")
    print("-" * 60)
    
    # Show every 20th point
    for i, point in enumerate(equity_curve[::20]):
        timestamp = point["timestamp"]
        equity = point["equity"]
        drawdown = point["drawdown"]
        
        print(f"  {timestamp}: ${equity:.2f} (DD: ${drawdown:.2f})")
    
    # Final equity
    if equity_curve:
        final = equity_curve[-1]
        initial = 10000.0
        total_return = (final["equity"] - initial) / initial * 100
        
        print(f"\nFinal Equity: ${final['equity']:.2f}")
        print(f"Total Return: {total_return:.2f}%")
    
    print()


async def main():
    """Run all examples."""
    try:
        await example_basic_backtest()
        await example_custom_config()
        await example_streaming_with_callbacks()
        await example_trade_analysis()
        await example_equity_curve()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
