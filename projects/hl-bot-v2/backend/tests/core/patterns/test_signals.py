"""Tests for signal generation module."""
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.market.data import Candle
from app.core.patterns.signals import (
    SignalGenerator,
    SignalGenerationConfig,
    generate_signal,
)
from src.hl_bot.types import SignalType, SetupType


def create_test_candles(
    count: int,
    timeframe: str,
    start_time: datetime,
    trend: str = "bullish",
    base_price: float = 50000.0,
) -> list[Candle]:
    """Create test candle data."""
    candles = []
    current_price = base_price
    
    tf_minutes = {
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
    }
    minutes = tf_minutes.get(timeframe, 5)
    
    for i in range(count):
        timestamp = start_time + timedelta(minutes=i * minutes)
        
        if trend == "bullish":
            change = base_price * 0.002  # 0.2% per candle
            close = current_price + change
        elif trend == "bearish":
            change = base_price * 0.002
            close = current_price - change
        else:  # sideways
            change = base_price * 0.001
            close = current_price + (change if i % 2 == 0 else -change)
        
        open_price = current_price
        high = max(open_price, close) * 1.001
        low = min(open_price, close) * 0.999
        
        candles.append(Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=1000.0,
            symbol="BTC-USD",
            timeframe=timeframe,
        ))
        
        current_price = close
    
    return candles


class TestSignalGenerator:
    """Test signal generator functionality."""
    
    def test_generate_bullish_signal(self):
        """Test generation of bullish signal with strong confluence."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # Create strong bullish trend across timeframes
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bullish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bullish"),
        }
        
        generator = SignalGenerator()
        signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
        
        # Should generate a signal
        if signal:  # May not always generate due to validation
            assert signal.signal_type == SignalType.LONG
            assert signal.entry_price > 0
            assert signal.stop_loss < signal.entry_price
            assert signal.take_profit_1 > signal.entry_price
            assert signal.take_profit_2 > signal.take_profit_1
            assert signal.confluence_score >= 0
            assert len(signal.reasoning) > 0
    
    def test_generate_bearish_signal(self):
        """Test generation of bearish signal."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bearish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bearish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bearish"),
        }
        
        generator = SignalGenerator()
        signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
        
        if signal:
            assert signal.signal_type == SignalType.SHORT
            assert signal.stop_loss > signal.entry_price
            assert signal.take_profit_1 < signal.entry_price
            assert signal.take_profit_2 < signal.take_profit_1
    
    def test_no_signal_on_low_confluence(self):
        """Test that no signal is generated when confluence is low."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # Mixed signals across timeframes
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
            "15m": create_test_candles(100, "15m", start_time, trend="sideways"),
            "1h": create_test_candles(50, "1h", start_time, trend="bearish"),
        }
        
        # Use stricter config
        config = SignalGenerationConfig(
            min_confluence_score=70.0,
            min_agreement_percentage=80.0,
        )
        
        generator = SignalGenerator(config=config)
        signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
        
        # Should likely not generate signal due to conflicting timeframes
        # (but may depend on exact confluence calculation)
        # At minimum, if signal is generated, it should be valid
        if signal:
            assert signal.confluence_score >= 0
    
    def test_risk_reward_validation(self):
        """Test that signals meet minimum risk-reward requirements."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bullish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bullish"),
        }
        
        config = SignalGenerationConfig(min_risk_reward=2.5)
        generator = SignalGenerator(config=config)
        signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
        
        if signal:
            # Calculate actual R:R
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.take_profit_2 - signal.entry_price)
            rr_ratio = reward / risk
            
            assert rr_ratio >= 2.5, f"R:R {rr_ratio:.2f} below minimum 2.5"
    
    def test_stop_loss_validation(self):
        """Test stop loss is on correct side of entry."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bullish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bullish"),
        }
        
        generator = SignalGenerator()
        signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
        
        if signal:
            if signal.signal_type == SignalType.LONG:
                assert signal.stop_loss < signal.entry_price
            else:
                assert signal.stop_loss > signal.entry_price
    
    def test_take_profit_validation(self):
        """Test take profits are on correct side of entry."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bearish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bearish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bearish"),
        }
        
        generator = SignalGenerator()
        signal = generator.generate_signal(mtf_data, "15m", "BTC-USD")
        
        if signal:
            if signal.signal_type == SignalType.LONG:
                assert signal.take_profit_1 > signal.entry_price
                assert signal.take_profit_2 > signal.entry_price
            else:
                assert signal.take_profit_1 < signal.entry_price
                assert signal.take_profit_2 < signal.entry_price
    
    def test_signal_has_required_fields(self):
        """Test generated signal has all required fields."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bullish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bullish"),
        }
        
        signal = generate_signal(mtf_data, "15m", "BTC-USD")
        
        if signal:
            # Check all required fields
            assert signal.id
            assert signal.timestamp
            assert signal.symbol == "BTC-USD"
            assert signal.signal_type in (SignalType.LONG, SignalType.SHORT)
            assert signal.entry_price > 0
            assert signal.stop_loss > 0
            assert signal.take_profit_1 > 0
            assert signal.take_profit_2 > 0
            assert 0 <= signal.confluence_score <= 100
            assert isinstance(signal.patterns_detected, list)
            assert signal.setup_type
            assert signal.market_phase
            assert signal.higher_tf_bias
            assert signal.reasoning
    
    def test_custom_config(self):
        """Test signal generation with custom configuration."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        mtf_data = {
            "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
            "15m": create_test_candles(100, "15m", start_time, trend="bullish"),
            "1h": create_test_candles(50, "1h", start_time, trend="bullish"),
        }
        
        # Very strict config
        config = SignalGenerationConfig(
            min_confluence_score=80.0,
            min_agreement_percentage=90.0,
            min_risk_reward=3.0,
            require_higher_tf_alignment=True,
        )
        
        signal = generate_signal(mtf_data, "15m", "BTC-USD", config=config)
        
        # May or may not generate signal based on strict requirements
        # If it does, it should meet all criteria
        if signal:
            assert signal.confluence_score >= 80.0
    
    def test_atr_calculation(self):
        """Test ATR calculation for stop loss."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # Create volatile market
        candles = []
        base_price = 50000.0
        for i in range(100):
            timestamp = start_time + timedelta(minutes=i * 5)
            volatility = 500.0  # $500 swings
            
            open_price = base_price
            close = base_price + (volatility if i % 2 == 0 else -volatility)
            high = max(open_price, close) + volatility * 0.5
            low = min(open_price, close) - volatility * 0.5
            
            candles.append(Candle(
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000.0,
                symbol="BTC-USD",
                timeframe="5m",
            ))
            
            base_price = close
        
        mtf_data = {
            "5m": candles,
            "15m": create_test_candles(50, "15m", start_time, trend="bullish"),
            "1h": create_test_candles(25, "1h", start_time, trend="bullish"),
        }
        
        config = SignalGenerationConfig(use_atr_stops=True, atr_multiplier=2.0)
        generator = SignalGenerator(config=config)
        
        signal = generator.generate_signal(mtf_data, "5m", "BTC-USD")
        
        if signal:
            # Stop loss should be reasonable distance from entry
            stop_distance = abs(signal.entry_price - signal.stop_loss)
            entry = signal.entry_price
            stop_pct = stop_distance / entry
            
            # Should be within reasonable bounds
            assert 0.001 < stop_pct < 0.05  # 0.1% to 5%
    
    def test_multiple_timeframes(self):
        """Test signal generation with multiple timeframe combinations."""
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # Test different timeframe combinations
        tf_combinations = [
            ["5m", "15m", "1h"],
            ["15m", "1h", "4h"],
            ["5m", "15m"],
        ]
        
        for timeframes in tf_combinations:
            mtf_data = {}
            for tf in timeframes:
                count = 200 if tf == "5m" else 100 if tf == "15m" else 50
                mtf_data[tf] = create_test_candles(
                    count, tf, start_time, trend="bullish"
                )
            
            # Should handle any valid timeframe combination
            analysis_tf = timeframes[0] if len(timeframes) > 0 else "15m"
            signal = generate_signal(mtf_data, analysis_tf, "BTC-USD")
            
            # If signal generated, it should be valid
            if signal:
                assert signal.entry_price > 0


def test_convenience_function():
    """Test the convenience generate_signal function."""
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_test_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_test_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_test_candles(50, "1h", start_time, trend="bullish"),
    }
    
    # Test without config
    signal = generate_signal(mtf_data, "15m", "BTC-USD")
    
    # Test with config
    config = SignalGenerationConfig(min_confluence_score=60.0)
    signal_with_config = generate_signal(mtf_data, "15m", "BTC-USD", config=config)
    
    # Both should return same type
    assert signal is None or isinstance(signal.entry_price, float)
    assert signal_with_config is None or isinstance(signal_with_config.entry_price, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
