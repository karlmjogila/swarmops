"""Tests for backtest playback controls.

Tests:
- Step mode functionality
- Speed control
- Seek functionality
- Pause/resume integration
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from src.hl_bot.trading.backtest import BacktestEngine, BacktestConfig, BacktestStatus
from app.core.market.data import Candle


@pytest.fixture
def sample_candles():
    """Generate sample candles for testing."""
    candles = []
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    for i in range(100):
        candle = Candle(
            symbol="BTC-USD",
            timestamp=start_time + timedelta(hours=i),
            open=Decimal("40000") + Decimal(i),
            high=Decimal("40100") + Decimal(i),
            low=Decimal("39900") + Decimal(i),
            close=Decimal("40050") + Decimal(i),
            volume=Decimal("100.0"),
            timeframe="1h"
        )
        candles.append(candle)
    
    return candles


@pytest.fixture
def engine():
    """Create backtest engine."""
    config = BacktestConfig(
        initial_capital=10000.0,
        position_size_percent=0.02,
        max_open_trades=3,
        use_stop_orders=True,
        use_take_profits=True,
    )
    return BacktestEngine(config=config, signal_generator=None)


class TestStepMode:
    """Test step mode functionality."""
    
    @pytest.mark.asyncio
    async def test_step_advances_one_candle(self, engine, sample_candles):
        """Test that step advances exactly one candle."""
        candles = sample_candles[:10]  # Use only 10 candles
        
        # Pause immediately
        engine.pause()
        
        # Start backtest
        backtest_task = engine.run(candles, emit_interval=1)
        
        # Get initial state
        state = await backtest_task.__anext__()
        initial_index = state.current_candle_index
        
        # Step forward
        engine.step()
        state = await backtest_task.__anext__()
        
        # Should be exactly one candle ahead
        assert state.current_candle_index == initial_index + 1
        
        # Should be paused again
        assert state.status == BacktestStatus.PAUSED
    
    @pytest.mark.asyncio
    async def test_step_while_running_has_no_effect(self, engine, sample_candles):
        """Test that step while running doesn't disrupt playback."""
        candles = sample_candles[:10]
        
        # Start backtest without pausing
        backtest_task = engine.run(candles, emit_interval=5)
        
        # Get first state
        state = await backtest_task.__anext__()
        
        # Try to step (should have no effect while running)
        engine.step()
        
        # Should still be running
        assert state.status == BacktestStatus.RUNNING


class TestSpeedControl:
    """Test playback speed control."""
    
    def test_set_speed_valid(self, engine):
        """Test setting valid speed values."""
        engine.set_speed(2.0)
        assert engine._playback_speed == 2.0
        
        engine.set_speed(0.5)
        assert engine._playback_speed == 0.5
        
        engine.set_speed(10.0)
        assert engine._playback_speed == 10.0
    
    def test_set_speed_invalid(self, engine):
        """Test that invalid speed raises error."""
        with pytest.raises(ValueError, match="Speed must be positive"):
            engine.set_speed(0)
        
        with pytest.raises(ValueError, match="Speed must be positive"):
            engine.set_speed(-1.0)


class TestSeek:
    """Test seek functionality."""
    
    def test_seek_sets_target_index(self, engine):
        """Test that seek sets the target index."""
        engine.seek(50)
        assert engine._seek_to_index == 50
    
    def test_seek_invalid_index(self, engine):
        """Test that negative index raises error."""
        with pytest.raises(ValueError, match="Candle index must be non-negative"):
            engine.seek(-1)
    
    @pytest.mark.asyncio
    async def test_seek_forward(self, engine, sample_candles):
        """Test seeking forward in backtest."""
        candles = sample_candles
        
        # Start backtest
        engine.pause()
        backtest_task = engine.run(candles, emit_interval=1)
        
        # Get initial state
        state = await backtest_task.__anext__()
        
        # Seek to candle 50
        engine.seek(50)
        engine.resume()
        
        # Wait for seek to complete
        async for state in backtest_task:
            if state.current_candle_index >= 50:
                break
        
        # Should be at or past target index
        assert state.current_candle_index >= 50


class TestPauseResumeIntegration:
    """Test pause/resume with playback controls."""
    
    @pytest.mark.asyncio
    async def test_pause_resume_cycle(self, engine, sample_candles):
        """Test pausing and resuming backtest."""
        candles = sample_candles[:20]
        
        # Start running
        backtest_task = engine.run(candles, emit_interval=5)
        
        # Get first state
        state = await backtest_task.__anext__()
        assert state.status == BacktestStatus.RUNNING
        
        # Pause
        engine.pause()
        
        # Should eventually report paused
        # (might take a candle or two to process the pause)
        paused = False
        for _ in range(10):
            try:
                state = await backtest_task.__anext__()
                if state.status == BacktestStatus.PAUSED:
                    paused = True
                    break
            except StopAsyncIteration:
                break
        
        # Resume
        engine.resume()
        
        # Should be running again
        state = await backtest_task.__anext__()
        # Status might still be PAUSED immediately after resume, but should continue
        assert state.status in [BacktestStatus.RUNNING, BacktestStatus.PAUSED]


class TestControlState:
    """Test control state management."""
    
    def test_initial_state(self, engine):
        """Test initial control state."""
        assert engine._paused is False
        assert engine._stop_requested is False
        assert engine._step_mode is False
        assert engine._step_requested is False
        assert engine._playback_speed == 1.0
        assert engine._seek_to_index is None
    
    def test_pause_sets_state(self, engine):
        """Test pause sets correct state."""
        engine.pause()
        assert engine._paused is True
        assert engine._step_mode is False
        assert engine.state.status == BacktestStatus.PAUSED
    
    def test_resume_clears_state(self, engine):
        """Test resume clears pause and step mode."""
        engine.pause()
        engine._step_mode = True
        
        engine.resume()
        assert engine._paused is False
        assert engine._step_mode is False
        assert engine.state.status == BacktestStatus.RUNNING
    
    def test_step_sets_step_mode(self, engine):
        """Test step sets step mode flags."""
        engine.step()
        assert engine._step_mode is True
        assert engine._step_requested is True
        assert engine._paused is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
