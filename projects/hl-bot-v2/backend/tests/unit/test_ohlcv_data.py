"""Unit tests for OHLCV data utilities."""
import pytest
from datetime import datetime, timezone

from app.core.market.data import (
    Candle,
    validate_ohlcv,
    calculate_price_change,
    calculate_typical_price,
    find_highest_candle,
    find_lowest_candle,
    calculate_average_volume,
    is_volume_spike,
    align_timestamp_to_timeframe,
    get_timeframe_minutes,
)


@pytest.fixture
def sample_bullish_candle():
    """Create a bullish candle for testing."""
    return Candle(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=50200.0,
        low=49900.0,
        close=50150.0,
        volume=100.0,
        symbol="BTC-USD",
        timeframe="5m",
    )


@pytest.fixture
def sample_bearish_candle():
    """Create a bearish candle for testing."""
    return Candle(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=50100.0,
        low=49800.0,
        close=49850.0,
        volume=150.0,
        symbol="BTC-USD",
        timeframe="5m",
    )


def test_candle_body_size(sample_bullish_candle, sample_bearish_candle):
    """Test candle body size calculation."""
    assert sample_bullish_candle.body_size == 150.0  # |50150 - 50000|
    assert sample_bearish_candle.body_size == 150.0  # |49850 - 50000|


def test_candle_wick_sizes(sample_bullish_candle):
    """Test upper and lower wick calculations."""
    # Bullish: open=50000, close=50150, high=50200, low=49900
    assert sample_bullish_candle.wick_size_upper == 50.0  # 50200 - 50150
    assert sample_bullish_candle.wick_size_lower == 100.0  # 50000 - 49900


def test_candle_total_range(sample_bullish_candle):
    """Test total candle range calculation."""
    assert sample_bullish_candle.total_range == 300.0  # 50200 - 49900


def test_candle_is_bullish(sample_bullish_candle, sample_bearish_candle):
    """Test bullish/bearish detection."""
    assert sample_bullish_candle.is_bullish is True
    assert sample_bullish_candle.is_bearish is False
    
    assert sample_bearish_candle.is_bullish is False
    assert sample_bearish_candle.is_bearish is True


def test_candle_is_doji():
    """Test doji detection."""
    # Doji has very small body relative to range
    doji = Candle(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50001.0,  # Almost same as open
        volume=100.0,
        symbol="BTC-USD",
        timeframe="5m",
    )
    
    assert doji.is_doji() is True
    
    # Normal candle is not doji
    normal = Candle(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0,
        symbol="BTC-USD",
        timeframe="5m",
    )
    
    assert normal.is_doji() is False


def test_validate_ohlcv_valid_data():
    """Test validation with valid OHLCV data."""
    valid, error = validate_ohlcv(
        open_price=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0,
    )
    
    assert valid is True
    assert error is None


def test_validate_ohlcv_invalid_high():
    """Test validation catches invalid high price."""
    valid, error = validate_ohlcv(
        open_price=50000.0,
        high=49900.0,  # High is lower than open
        low=49900.0,
        close=50050.0,
        volume=100.0,
    )
    
    assert valid is False
    assert "High" in error


def test_validate_ohlcv_invalid_low():
    """Test validation catches invalid low price."""
    valid, error = validate_ohlcv(
        open_price=50000.0,
        high=50100.0,
        low=50200.0,  # Low is higher than high
        close=50050.0,
        volume=100.0,
    )
    
    assert valid is False
    # The validation catches the high being lower than low (High (50100.0) must be >= open, close, and low)
    assert "High" in error or "Low" in error


def test_validate_ohlcv_negative_price():
    """Test validation catches negative prices."""
    valid, error = validate_ohlcv(
        open_price=-50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0,
    )
    
    assert valid is False
    assert "positive" in error.lower()


def test_validate_ohlcv_negative_volume():
    """Test validation catches negative volume."""
    valid, error = validate_ohlcv(
        open_price=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=-100.0,
    )
    
    assert valid is False
    assert "volume" in error.lower()


def test_calculate_price_change(sample_bullish_candle, sample_bearish_candle):
    """Test price change calculation."""
    # Bullish: open=50000, close=50150
    change, percent = calculate_price_change(sample_bullish_candle)
    assert change == 150.0
    assert percent == pytest.approx(0.3, abs=0.01)  # 0.3%
    
    # Bearish: open=50000, close=49850
    change, percent = calculate_price_change(sample_bearish_candle)
    assert change == -150.0
    assert percent == pytest.approx(-0.3, abs=0.01)  # -0.3%


def test_calculate_typical_price(sample_bullish_candle):
    """Test typical price calculation."""
    # (high + low + close) / 3
    # (50200 + 49900 + 50150) / 3 = 50083.33
    typical = calculate_typical_price(sample_bullish_candle)
    assert typical == pytest.approx(50083.33, abs=0.01)


def test_find_highest_candle():
    """Test finding candle with highest high."""
    candles = [
        Candle(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), 
               50000, 50100, 49900, 50050, 100, "BTC-USD", "5m"),
        Candle(datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
               50050, 50300, 50000, 50200, 100, "BTC-USD", "5m"),  # Highest
        Candle(datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
               50200, 50250, 50100, 50150, 100, "BTC-USD", "5m"),
    ]
    
    highest = find_highest_candle(candles)
    assert highest.high == 50300.0


def test_find_lowest_candle():
    """Test finding candle with lowest low."""
    candles = [
        Candle(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
               50000, 50100, 49900, 50050, 100, "BTC-USD", "5m"),
        Candle(datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
               50050, 50300, 49800, 50200, 100, "BTC-USD", "5m"),  # Lowest
        Candle(datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
               50200, 50250, 50100, 50150, 100, "BTC-USD", "5m"),
    ]
    
    lowest = find_lowest_candle(candles)
    assert lowest.low == 49800.0


def test_calculate_average_volume():
    """Test average volume calculation."""
    candles = [
        Candle(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
               50000, 50100, 49900, 50050, 100, "BTC-USD", "5m"),
        Candle(datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
               50050, 50300, 50000, 50200, 200, "BTC-USD", "5m"),
        Candle(datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
               50200, 50250, 50100, 50150, 300, "BTC-USD", "5m"),
    ]
    
    avg_volume = calculate_average_volume(candles)
    assert avg_volume == 200.0  # (100 + 200 + 300) / 3


def test_is_volume_spike():
    """Test volume spike detection."""
    candle_normal = Candle(
        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        50000, 50100, 49900, 50050, 100, "BTC-USD", "5m"
    )
    
    candle_spike = Candle(
        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        50000, 50100, 49900, 50050, 300, "BTC-USD", "5m"
    )
    
    average_volume = 100.0
    
    assert is_volume_spike(candle_normal, average_volume, threshold=2.0) is False
    assert is_volume_spike(candle_spike, average_volume, threshold=2.0) is True


def test_align_timestamp_to_timeframe():
    """Test timestamp alignment to timeframe boundaries."""
    # 5-minute alignment
    timestamp = datetime(2024, 1, 1, 14, 27, 35, tzinfo=timezone.utc)
    aligned = align_timestamp_to_timeframe(timestamp, "5m")
    assert aligned == datetime(2024, 1, 1, 14, 25, 0, tzinfo=timezone.utc)
    
    # 15-minute alignment
    timestamp = datetime(2024, 1, 1, 14, 27, 35, tzinfo=timezone.utc)
    aligned = align_timestamp_to_timeframe(timestamp, "15m")
    assert aligned == datetime(2024, 1, 1, 14, 15, 0, tzinfo=timezone.utc)
    
    # 1-hour alignment
    timestamp = datetime(2024, 1, 1, 14, 27, 35, tzinfo=timezone.utc)
    aligned = align_timestamp_to_timeframe(timestamp, "1h")
    assert aligned == datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
    
    # Daily alignment
    timestamp = datetime(2024, 1, 1, 14, 27, 35, tzinfo=timezone.utc)
    aligned = align_timestamp_to_timeframe(timestamp, "1d")
    assert aligned == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_get_timeframe_minutes():
    """Test converting timeframe strings to minutes."""
    assert get_timeframe_minutes("5m") == 5
    assert get_timeframe_minutes("15m") == 15
    assert get_timeframe_minutes("1h") == 60
    assert get_timeframe_minutes("4h") == 240
    assert get_timeframe_minutes("1d") == 1440


def test_get_timeframe_minutes_invalid():
    """Test that invalid timeframe raises ValueError."""
    with pytest.raises(ValueError):
        get_timeframe_minutes("5x")  # Invalid format


def test_candle_to_dict(sample_bullish_candle):
    """Test converting candle to dictionary."""
    candle_dict = sample_bullish_candle.to_dict()
    
    assert candle_dict["symbol"] == "BTC-USD"
    assert candle_dict["timeframe"] == "5m"
    assert candle_dict["open"] == 50000.0
    assert candle_dict["high"] == 50200.0
    assert candle_dict["low"] == 49900.0
    assert candle_dict["close"] == 50150.0
    assert candle_dict["volume"] == 100.0
    assert "timestamp" in candle_dict


def test_empty_list_handling():
    """Test that utility functions handle empty lists gracefully."""
    assert find_highest_candle([]) is None
    assert find_lowest_candle([]) is None
    assert calculate_average_volume([]) == 0.0
