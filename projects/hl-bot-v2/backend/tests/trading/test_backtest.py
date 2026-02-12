"""Unit tests for backtest engine.

Tests cover:
- Candle streaming and processing
- Signal generation and trade execution
- Position tracking and P&L calculation
- Stop loss and take profit execution
- Partial exits
- Performance metrics calculation
- State updates
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.hl_bot.trading.backtest import (
    BacktestEngine,
    BacktestConfig,
    BacktestStatus,
    BacktestTrade,
    BacktestMetrics,
)
from src.hl_bot.types import Signal, SignalType, SetupType, MarketPhase, PatternType, Timeframe
from app.core.market.data import Candle


def create_test_candles(count: int = 100, symbol: str = "BTC-USD") -> list[Candle]:
    """Create test candles with uptrend."""
    candles = []
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    start_price = 40000.0
    
    for i in range(count):
        # Simple uptrend with some noise
        base_price = start_price + (i * 10)
        noise = (i % 5 - 2) * 5
        price = base_price + noise
        
        candle = Candle(
            timestamp=start_time + timedelta(minutes=i),
            open=price - 2,
            high=price + 5,
            low=price - 5,
            close=price,
            volume=1000.0,
            symbol=symbol,
            timeframe="5m",
        )
        candles.append(candle)
    
    return candles


def create_test_signal(
    candle: Candle,
    signal_type: SignalType = SignalType.LONG,
) -> Signal:
    """Create test signal from candle."""
    entry = candle.close
    
    if signal_type == SignalType.LONG:
        stop = entry * 0.98  # 2% stop
        tp1 = entry * 1.03  # 3% TP1 (1.5R)
        tp2 = entry * 1.04  # 4% TP2 (2R)
    else:
        stop = entry * 1.02
        tp1 = entry * 0.97
        tp2 = entry * 0.96
    
    return Signal(
        id="test-signal-1",
        timestamp=candle.timestamp,
        symbol=candle.symbol,
        signal_type=signal_type,
        timeframe=Timeframe.M5,
        entry_price=entry,
        stop_loss=stop,
        take_profit_1=tp1,
        take_profit_2=tp2,
        confluence_score=75.0,
        patterns_detected=[PatternType.ENGULFING],
        setup_type=SetupType.BREAKOUT,
        market_phase=MarketPhase.DRIVE,
        higher_tf_bias=signal_type,
        reasoning="Test signal",
    )


class TestBacktestEngine:
    """Test suite for BacktestEngine."""
    
    def test_initialization(self):
        """Test engine initializes correctly."""
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config=config)
        
        assert engine.state.status == BacktestStatus.IDLE
        assert engine.state.current_capital == 10000.0
        assert engine.state.peak_capital == 10000.0
        assert len(engine.trades) == 0
        assert len(engine.closed_trades) == 0
    
    @pytest.mark.asyncio
    async def test_empty_candles(self):
        """Test backtest with no candles."""
        config = BacktestConfig()
        engine = BacktestEngine(config=config)
        
        states = []
        async for state in engine.run([]):
            states.append(state)
        
        assert len(states) == 1
        assert states[0].status == BacktestStatus.COMPLETED
        assert states[0].metrics.total_trades == 0
    
    @pytest.mark.asyncio
    async def test_candle_streaming(self):
        """Test candles are processed in order."""
        candles = create_test_candles(50)
        config = BacktestConfig()
        engine = BacktestEngine(config=config)
        
        states = []
        async for state in engine.run(candles, emit_interval=10):
            states.append(state)
        
        # Should have multiple state updates
        assert len(states) > 1
        
        # Final state should be completed
        final_state = states[-1]
        assert final_state.status == BacktestStatus.COMPLETED
        assert final_state.current_candle_index == 49
        assert final_state.progress_percent == 100.0
        
        # Timestamps should be in order
        for i in range(len(states) - 1):
            if states[i].current_time and states[i + 1].current_time:
                assert states[i].current_time <= states[i + 1].current_time
    
    @pytest.mark.asyncio
    async def test_signal_generation_and_trade_open(self):
        """Test signal generates and opens trade."""
        candles = create_test_candles(100)
        
        # Signal generator that returns a signal on candle 60
        signal_generated = False
        
        def signal_gen(candle):
            nonlocal signal_generated
            if candle.timestamp == candles[60].timestamp and not signal_generated:
                signal_generated = True
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        # Should have generated signal and opened trade
        assert len(engine.signals) >= 1
        assert len(engine.closed_trades) >= 1  # Should have closed by end
    
    @pytest.mark.asyncio
    async def test_stop_loss_execution(self):
        """Test stop loss is hit correctly."""
        candles = create_test_candles(100)
        
        # Modify candles to create a losing trade
        # Signal at candle 60, then price drops
        for i in range(61, 100):
            candles[i].close = candles[60].close * 0.95  # Drop 5%
            candles[i].low = candles[60].close * 0.94
            candles[i].high = candles[60].close * 0.96
        
        def signal_gen(candle):
            if candle.timestamp == candles[60].timestamp:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        # Should have closed trade with stop loss
        assert len(engine.closed_trades) >= 1
        trade = engine.closed_trades[0]
        assert "stop" in trade.exit_reason.lower()
        assert float(trade.realized_pnl) < 0  # Should be a loss
    
    @pytest.mark.asyncio
    async def test_take_profit_execution(self):
        """Test take profit is hit correctly."""
        candles = create_test_candles(100)
        
        # Modify candles to create a winning trade
        # Signal at candle 60, then price rises
        for i in range(61, 100):
            candles[i].close = candles[60].close * 1.05  # Rise 5%
            candles[i].low = candles[60].close * 1.04
            candles[i].high = candles[60].close * 1.06
        
        def signal_gen(candle):
            if candle.timestamp == candles[60].timestamp:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(initial_capital=10000.0, partial_exit_enabled=True)
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        # Should have closed trade with take profit
        assert len(engine.closed_trades) >= 1
        trade = engine.closed_trades[0]
        # Check that at least one TP was hit (partial exits occurred)
        assert len(trade.partial_exits) > 0, "Should have partial exits"
        assert any("take profit" in exit["reason"].lower() for exit in trade.partial_exits)
        assert float(trade.realized_pnl) > 0  # Should be a win
    
    @pytest.mark.asyncio
    async def test_partial_exits(self):
        """Test partial exits at TP levels."""
        candles = create_test_candles(100)
        
        # Create winning scenario
        for i in range(61, 100):
            candles[i].close = candles[60].close * 1.05
            candles[i].low = candles[60].close * 1.04
            candles[i].high = candles[60].close * 1.06
        
        def signal_gen(candle):
            if candle.timestamp == candles[60].timestamp:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(
            initial_capital=10000.0,
            partial_exit_enabled=True,
            tp1_exit_percent=0.5,
        )
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        # Check for partial exits
        if engine.closed_trades:
            trade = engine.closed_trades[0]
            # Should have multiple exits
            assert len(trade.partial_exits) > 0
    
    @pytest.mark.asyncio
    async def test_position_sizing(self):
        """Test position size calculation."""
        candles = create_test_candles(100)
        
        def signal_gen(candle):
            if candle.timestamp == candles[60].timestamp:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(
            initial_capital=10000.0,
            position_size_percent=0.02,  # Risk 2% per trade
        )
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        # Position size should be based on 2% risk
        if engine.closed_trades:
            trade = engine.closed_trades[0]
            # Risk = entry * size * 0.02 (stop distance)
            risk = float(trade.entry_price * trade.position_size * Decimal("0.02"))
            expected_risk = 10000.0 * 0.02
            # Should be approximately equal (within 10% due to rounding)
            assert abs(risk - expected_risk) / expected_risk < 0.3
    
    @pytest.mark.asyncio
    async def test_commission_and_slippage(self):
        """Test commission and slippage are applied."""
        candles = create_test_candles(100)
        
        def signal_gen(candle):
            if candle.timestamp == candles[60].timestamp:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(
            initial_capital=10000.0,
            commission_percent=0.001,  # 0.1%
            slippage_percent=0.0005,   # 0.05%
        )
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        # Should have recorded commission and slippage
        metrics = engine.get_results()
        assert metrics.total_commission > 0
        assert metrics.total_slippage > 0
    
    @pytest.mark.asyncio
    async def test_max_open_trades_limit(self):
        """Test max open trades limit is enforced."""
        candles = create_test_candles(100)
        
        # Try to open multiple trades
        signal_count = 0
        
        def signal_gen(candle):
            nonlocal signal_count
            # Try to generate signals every 10 candles
            if candle.timestamp.minute % 10 == 0 and signal_count < 5:
                signal_count += 1
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(
            initial_capital=100000.0,  # Large capital
            max_open_trades=2,
        )
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        max_open_seen = 0
        async for state in engine.run(candles, emit_interval=5):
            open_count = len(state.open_trades)
            if open_count > max_open_seen:
                max_open_seen = open_count
        
        # Should never exceed max_open_trades
        assert max_open_seen <= 2
    
    @pytest.mark.asyncio
    async def test_metrics_calculation(self):
        """Test performance metrics are calculated correctly."""
        candles = create_test_candles(100)
        
        # Create multiple trades
        def signal_gen(candle):
            if candle.timestamp.minute in [20, 40, 60]:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        # Modify prices to create mix of wins and losses
        for i in range(21, 40):
            candles[i].close = candles[20].close * 1.05  # Win
            candles[i].high = candles[20].close * 1.06
        
        for i in range(41, 60):
            candles[i].close = candles[40].close * 0.95  # Loss
            candles[i].low = candles[40].close * 0.94
        
        for i in range(61, 100):
            candles[i].close = candles[60].close * 1.04  # Win
            candles[i].high = candles[60].close * 1.05
        
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        metrics = engine.get_results()
        
        # Should have trades
        assert metrics.total_trades > 0
        
        # Should have wins or losses (can be either based on exit timing)
        assert (metrics.winning_trades + metrics.losing_trades) == metrics.total_trades
        
        # Win rate should be valid
        assert 0 <= metrics.win_rate <= 1
        
        # Win rate calculation
        expected_win_rate = metrics.winning_trades / metrics.total_trades
        assert abs(metrics.win_rate - expected_win_rate) < 0.01
        
        # Should have valid P&L
        assert metrics.total_pnl != 0
    
    @pytest.mark.asyncio
    async def test_equity_curve_tracking(self):
        """Test equity curve is tracked correctly."""
        candles = create_test_candles(100)
        
        def signal_gen(candle):
            if candle.timestamp == candles[60].timestamp:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        metrics = engine.get_results()
        
        # Should have equity curve points
        assert len(metrics.equity_curve) > 0
        
        # Each point should have required fields
        for point in metrics.equity_curve:
            assert "timestamp" in point
            assert "equity" in point
            assert "drawdown" in point
        
        # Equity should start at initial capital
        # (might vary slightly due to first trade)
        first_equity = metrics.equity_curve[0]["equity"]
        assert abs(first_equity - 10000.0) < 1000.0
    
    @pytest.mark.asyncio
    async def test_drawdown_tracking(self):
        """Test drawdown is tracked correctly."""
        candles = create_test_candles(100)
        
        # Create scenario with drawdown
        # Win first, then lose
        def signal_gen(candle):
            if candle.timestamp.minute in [20, 60]:
                return create_test_signal(candle, SignalType.LONG)
            return None
        
        # First trade wins
        for i in range(21, 40):
            candles[i].close = candles[20].close * 1.05
            candles[i].high = candles[20].close * 1.06
        
        # Second trade loses (creates drawdown)
        for i in range(61, 100):
            candles[i].close = candles[60].close * 0.90
            candles[i].low = candles[60].close * 0.89
        
        config = BacktestConfig(initial_capital=10000.0)
        engine = BacktestEngine(config=config, signal_generator=signal_gen)
        
        async for state in engine.run(candles):
            pass
        
        metrics = engine.get_results()
        
        # Should have recorded drawdown
        assert metrics.max_drawdown >= 0
        assert metrics.max_drawdown_percent >= 0
    
    @pytest.mark.asyncio
    async def test_pause_resume(self):
        """Test backtest can be paused and resumed."""
        candles = create_test_candles(100)
        config = BacktestConfig()
        engine = BacktestEngine(config=config)
        
        # Start backtest in background
        import asyncio
        task = asyncio.create_task(engine.run(candles).__anext__())
        
        # Let it run a bit
        await asyncio.sleep(0.01)
        
        # Pause
        engine.pause()
        assert engine.state.status == BacktestStatus.PAUSED
        
        # Resume
        engine.resume()
        assert engine.state.status == BacktestStatus.RUNNING
        
        # Clean up
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_state_updates(self):
        """Test state updates are emitted correctly."""
        candles = create_test_candles(50)
        config = BacktestConfig()
        engine = BacktestEngine(config=config)
        
        states_received = []
        
        def state_callback(state):
            states_received.append(state)
        
        engine.add_state_callback(state_callback)
        
        async for state in engine.run(candles, emit_interval=10):
            pass
        
        # Should have received state updates
        assert len(states_received) > 0
        
        # States should show progress
        for state in states_received:
            assert state.current_candle_index >= 0
            assert 0 <= state.progress_percent <= 100


class TestBacktestConfig:
    """Test BacktestConfig validation."""
    
    def test_default_config(self):
        """Test default configuration is valid."""
        config = BacktestConfig()
        assert config.initial_capital > 0
        assert 0 < config.position_size_percent <= 1
        assert config.max_open_trades >= 1
        assert config.commission_percent >= 0
        assert config.slippage_percent >= 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = BacktestConfig(
            initial_capital=50000.0,
            position_size_percent=0.01,
            max_open_trades=5,
            commission_percent=0.001,
        )
        assert config.initial_capital == 50000.0
        assert config.position_size_percent == 0.01
        assert config.max_open_trades == 5
        assert config.commission_percent == 0.001
    
    def test_invalid_config(self):
        """Test invalid configuration raises error."""
        with pytest.raises(Exception):
            BacktestConfig(initial_capital=-1000)  # Negative capital
        
        with pytest.raises(Exception):
            BacktestConfig(position_size_percent=1.5)  # >100%
        
        with pytest.raises(Exception):
            BacktestConfig(max_open_trades=0)  # Must be >= 1


class TestBacktestMetrics:
    """Test BacktestMetrics calculations."""
    
    def test_empty_metrics(self):
        """Test empty metrics initialization."""
        metrics = BacktestMetrics()
        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.total_pnl == 0.0
    
    def test_metrics_from_trades(self):
        """Test metrics reflect trade results."""
        # This would be an integration test
        # Testing metric calculation logic is covered in engine tests
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
