"""Unit tests for multi-timeframe data alignment."""
import pytest
from datetime import datetime, timezone, timedelta
from app.core.market.data import Candle
from app.core.market.timeframes import (
    TimeframeResampler,
    resample_candles,
    create_multi_timeframe_view,
    get_aligned_candle,
    get_lookback_candles,
    align_multi_timeframe_data,
    validate_timeframe_hierarchy,
    get_candle_at_time,
    get_timeframe_multiplier,
    generate_timeframe_sequence,
    is_timeframe_complete,
)


@pytest.fixture
def sample_5m_candles():
    """Create sample 5-minute candles for testing."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles = []
    
    # Create 12 candles (1 hour of 5m data)
    for i in range(12):
        timestamp = base_time + timedelta(minutes=i * 5)
        candles.append(
            Candle(
                timestamp=timestamp,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0 + (i * 10),
                symbol="BTC-USD",
                timeframe="5m",
            )
        )
    
    return candles


@pytest.fixture
def sample_15m_candles():
    """Create sample 15-minute candles for testing."""
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles = []
    
    # Create 4 candles (1 hour of 15m data)
    for i in range(4):
        timestamp = base_time + timedelta(minutes=i * 15)
        candles.append(
            Candle(
                timestamp=timestamp,
                open=100.0 + (i * 3),
                high=105.0 + (i * 3),
                low=95.0 + (i * 3),
                close=102.0 + (i * 3),
                volume=3030.0,  # Sum of 3 x 5m candles
                symbol="BTC-USD",
                timeframe="15m",
            )
        )
    
    return candles


class TestTimeframeResampler:
    """Test the TimeframeResampler class."""
    
    def test_resample_5m_to_15m(self, sample_5m_candles):
        """Test resampling 5m candles to 15m."""
        resampler = TimeframeResampler()
        result = resampler.resample(sample_5m_candles, "5m", "15m")
        
        # Should get 4 x 15m candles from 12 x 5m candles
        assert len(result) == 4
        assert all(c.timeframe == "15m" for c in result)
        
        # Check first 15m candle (aggregates first 3 x 5m candles)
        first = result[0]
        assert first.open == 100.0  # First candle's open
        assert first.high == 107.0  # Max high from first 3 candles (105, 106, 107)
        assert first.low == 95.0    # Min low from first 3 candles (95, 96, 97)
        assert first.close == 104.0 # Last candle's close (third candle)
        assert first.volume == 3030.0  # Sum of volumes: 1000 + 1010 + 1020
    
    def test_resample_5m_to_1h(self, sample_5m_candles):
        """Test resampling 5m candles to 1h."""
        resampler = TimeframeResampler()
        result = resampler.resample(sample_5m_candles, "5m", "1h")
        
        # Should get 1 x 1h candle from 12 x 5m candles
        assert len(result) == 1
        assert result[0].timeframe == "1h"
        
        # Check aggregated values
        candle = result[0]
        assert candle.open == 100.0   # First candle
        assert candle.high == 116.0   # Max high
        assert candle.low == 95.0     # Min low
        assert candle.close == 113.0  # Last candle
        # Volume should be sum of all 12 candles
        expected_volume = sum(1000 + (i * 10) for i in range(12))
        assert candle.volume == expected_volume
    
    def test_resample_same_timeframe(self, sample_5m_candles):
        """Test resampling to same timeframe returns copy."""
        resampler = TimeframeResampler()
        result = resampler.resample(sample_5m_candles, "5m", "5m")
        
        assert len(result) == len(sample_5m_candles)
        assert result is not sample_5m_candles  # Should be a copy
    
    def test_resample_to_smaller_timeframe_raises_error(self, sample_15m_candles):
        """Test that resampling to smaller timeframe raises ValueError."""
        resampler = TimeframeResampler()
        
        with pytest.raises(ValueError, match="Cannot resample to smaller timeframe"):
            resampler.resample(sample_15m_candles, "15m", "5m")
    
    def test_resample_empty_candles(self):
        """Test resampling empty candle list."""
        resampler = TimeframeResampler()
        result = resampler.resample([], "5m", "15m")
        
        assert result == []
    
    def test_resample_preserves_symbol(self, sample_5m_candles):
        """Test that symbol is preserved during resampling."""
        resampler = TimeframeResampler()
        result = resampler.resample(sample_5m_candles, "5m", "15m")
        
        assert all(c.symbol == "BTC-USD" for c in result)


class TestResampleCandlesFunction:
    """Test the convenience resample_candles function."""
    
    def test_resample_candles_convenience(self, sample_5m_candles):
        """Test convenience function works same as class method."""
        result = resample_candles(sample_5m_candles, "5m", "15m")
        
        assert len(result) == 4
        assert all(c.timeframe == "15m" for c in result)


class TestCreateMultiTimeframeView:
    """Test multi-timeframe view creation."""
    
    def test_create_mtf_view(self, sample_5m_candles):
        """Test creating multi-timeframe view."""
        result = create_multi_timeframe_view(
            sample_5m_candles,
            "5m",
            ["5m", "15m", "1h"]
        )
        
        assert "5m" in result
        assert "15m" in result
        assert "1h" in result
        
        assert len(result["5m"]) == 12
        assert len(result["15m"]) == 4
        assert len(result["1h"]) == 1
    
    def test_mtf_view_includes_base_timeframe(self, sample_5m_candles):
        """Test that base timeframe is included unchanged."""
        result = create_multi_timeframe_view(
            sample_5m_candles,
            "5m",
            ["5m", "15m"]
        )
        
        # Base timeframe should be a copy, not resampled
        assert len(result["5m"]) == len(sample_5m_candles)


class TestGetAlignedCandle:
    """Test getting aligned candles."""
    
    def test_get_aligned_candle_exact_match(self, sample_15m_candles):
        """Test getting candle with exact timestamp match."""
        target_time = datetime(2024, 1, 1, 10, 15, tzinfo=timezone.utc)
        candle = get_aligned_candle(sample_15m_candles, target_time, "15m")
        
        assert candle is not None
        assert candle.timestamp == target_time
    
    def test_get_aligned_candle_within_period(self, sample_15m_candles):
        """Test getting candle with timestamp within period."""
        # 10:17 should align to 10:15 candle
        target_time = datetime(2024, 1, 1, 10, 17, tzinfo=timezone.utc)
        candle = get_aligned_candle(sample_15m_candles, target_time, "15m")
        
        assert candle is not None
        assert candle.timestamp == datetime(2024, 1, 1, 10, 15, tzinfo=timezone.utc)
    
    def test_get_aligned_candle_not_found(self, sample_15m_candles):
        """Test getting candle that doesn't exist."""
        target_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candle = get_aligned_candle(sample_15m_candles, target_time, "15m")
        
        assert candle is None


class TestGetLookbackCandles:
    """Test lookback candle retrieval."""
    
    def test_get_lookback_candles(self, sample_5m_candles):
        """Test getting lookback candles."""
        # Get 3 candles before index 5
        lookback = get_lookback_candles(sample_5m_candles, 5, 3)
        
        assert len(lookback) == 3
        assert lookback == sample_5m_candles[2:5]
    
    def test_get_lookback_at_start(self, sample_5m_candles):
        """Test lookback at start of data."""
        # Get 5 candles before index 2 (only 2 exist)
        lookback = get_lookback_candles(sample_5m_candles, 2, 5)
        
        assert len(lookback) == 2
        assert lookback == sample_5m_candles[0:2]
    
    def test_get_lookback_zero_periods(self, sample_5m_candles):
        """Test lookback with zero periods."""
        lookback = get_lookback_candles(sample_5m_candles, 5, 0)
        
        assert len(lookback) == 0


class TestAlignMultiTimeframeData:
    """Test multi-timeframe data alignment."""
    
    def test_align_mtf_data(self, sample_5m_candles):
        """Test aligning multi-timeframe data to reference timestamp."""
        mtf_view = create_multi_timeframe_view(
            sample_5m_candles,
            "5m",
            ["5m", "15m"]
        )
        
        # Reference time: 10:17 (within 10:15-10:20 period for both TFs)
        ref_time = datetime(2024, 1, 1, 10, 17, tzinfo=timezone.utc)
        aligned = align_multi_timeframe_data(mtf_view, ref_time)
        
        assert "5m" in aligned
        assert "15m" in aligned
        
        # 5m candle at 10:15
        assert aligned["5m"].timestamp == datetime(2024, 1, 1, 10, 15, tzinfo=timezone.utc)
        # 15m candle at 10:15
        assert aligned["15m"].timestamp == datetime(2024, 1, 1, 10, 15, tzinfo=timezone.utc)


class TestValidateTimeframeHierarchy:
    """Test timeframe hierarchy validation."""
    
    def test_valid_hierarchy(self):
        """Test valid ascending hierarchy."""
        assert validate_timeframe_hierarchy(["5m", "15m", "1h", "4h"]) is True
    
    def test_invalid_hierarchy(self):
        """Test invalid hierarchy."""
        assert validate_timeframe_hierarchy(["1h", "5m", "15m"]) is False
    
    def test_equal_timeframes(self):
        """Test hierarchy with equal timeframes."""
        assert validate_timeframe_hierarchy(["15m", "15m"]) is True
    
    def test_single_timeframe(self):
        """Test single timeframe is valid."""
        assert validate_timeframe_hierarchy(["5m"]) is True
    
    def test_empty_list(self):
        """Test empty list is valid."""
        assert validate_timeframe_hierarchy([]) is True


class TestGetCandleAtTime:
    """Test efficient candle retrieval."""
    
    def test_get_candle_at_time(self, sample_15m_candles):
        """Test getting candle at specific time."""
        target_time = datetime(2024, 1, 1, 10, 15, tzinfo=timezone.utc)
        candle = get_candle_at_time(sample_15m_candles, target_time, "15m")
        
        assert candle is not None
        assert candle.timestamp == target_time
    
    def test_get_candle_at_time_not_found(self, sample_15m_candles):
        """Test getting candle that doesn't exist."""
        target_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        candle = get_candle_at_time(sample_15m_candles, target_time, "15m")
        
        assert candle is None


class TestGetTimeframeMultiplier:
    """Test timeframe multiplier calculation."""
    
    def test_5m_to_15m(self):
        """Test 5m to 15m multiplier."""
        assert get_timeframe_multiplier("5m", "15m") == 3
    
    def test_5m_to_1h(self):
        """Test 5m to 1h multiplier."""
        assert get_timeframe_multiplier("5m", "1h") == 12
    
    def test_15m_to_1h(self):
        """Test 15m to 1h multiplier."""
        assert get_timeframe_multiplier("15m", "1h") == 4
    
    def test_1h_to_4h(self):
        """Test 1h to 4h multiplier."""
        assert get_timeframe_multiplier("1h", "4h") == 4
    
    def test_same_timeframe(self):
        """Test same timeframe multiplier is 1."""
        assert get_timeframe_multiplier("5m", "5m") == 1
    
    def test_invalid_target_smaller(self):
        """Test error when target is smaller than source."""
        with pytest.raises(ValueError, match="cannot be smaller"):
            get_timeframe_multiplier("1h", "5m")


class TestGenerateTimeframeSequence:
    """Test timeframe sequence generation."""
    
    def test_generate_from_5m(self):
        """Test generating sequence from 5m base."""
        sequence = generate_timeframe_sequence("5m", 48)
        
        assert "5m" in sequence
        assert "15m" in sequence
        assert "1h" in sequence
        assert sequence[0] == "5m"  # Base should be first
    
    def test_generate_respects_max_multiplier(self):
        """Test that max multiplier limits sequence."""
        sequence = generate_timeframe_sequence("5m", 12)
        
        # Should not include 4h (multiplier 48)
        assert "4h" not in sequence
        assert "1h" in sequence  # Multiplier 12 should be included


class TestIsTimeframeComplete:
    """Test timeframe completeness checking."""
    
    def test_complete_data(self, sample_5m_candles):
        """Test with complete data."""
        # 12 x 5m candles can form 4 complete 15m candles
        assert is_timeframe_complete(sample_5m_candles, 4, "5m", "15m") is True
    
    def test_incomplete_data(self, sample_5m_candles):
        """Test with incomplete data."""
        # 12 x 5m candles cannot form 5 complete 15m candles (needs 15)
        assert is_timeframe_complete(sample_5m_candles, 5, "5m", "15m") is False
    
    def test_exact_data(self, sample_5m_candles):
        """Test with exact number of candles."""
        # 12 x 5m candles can form exactly 1 complete 1h candle
        assert is_timeframe_complete(sample_5m_candles, 1, "5m", "1h") is True


class TestResamplingEdgeCases:
    """Test edge cases in resampling."""
    
    def test_resample_with_gaps(self):
        """Test resampling with time gaps in data."""
        base_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        candles = [
            Candle(
                timestamp=base_time,
                open=100.0, high=105.0, low=95.0, close=102.0,
                volume=1000.0, symbol="BTC-USD", timeframe="5m"
            ),
            # Gap: missing 10:05
            Candle(
                timestamp=base_time + timedelta(minutes=10),
                open=103.0, high=108.0, low=98.0, close=105.0,
                volume=1100.0, symbol="BTC-USD", timeframe="5m"
            ),
        ]
        
        result = resample_candles(candles, "5m", "15m")
        
        # Both candles are within same 15m period (10:00-10:15), so they aggregate
        assert len(result) == 1
        assert result[0].high == 108.0  # Max of both
        assert result[0].low == 95.0    # Min of both
        assert result[0].volume == 2100.0  # Sum of both
    
    def test_resample_single_candle(self):
        """Test resampling single candle."""
        candle = Candle(
            timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            open=100.0, high=105.0, low=95.0, close=102.0,
            volume=1000.0, symbol="BTC-USD", timeframe="5m"
        )
        
        result = resample_candles([candle], "5m", "15m")
        
        assert len(result) == 1
        # Values should be preserved
        assert result[0].open == 100.0
        assert result[0].high == 105.0
        assert result[0].low == 95.0
        assert result[0].close == 102.0
        assert result[0].volume == 1000.0
    
    def test_resample_unordered_candles(self):
        """Test resampling handles unordered candles correctly."""
        base_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        
        # Create candles out of order
        candles = [
            Candle(
                timestamp=base_time + timedelta(minutes=10),
                open=103.0, high=108.0, low=98.0, close=105.0,
                volume=1100.0, symbol="BTC-USD", timeframe="5m"
            ),
            Candle(
                timestamp=base_time,
                open=100.0, high=105.0, low=95.0, close=102.0,
                volume=1000.0, symbol="BTC-USD", timeframe="5m"
            ),
            Candle(
                timestamp=base_time + timedelta(minutes=5),
                open=102.0, high=107.0, low=97.0, close=104.0,
                volume=1050.0, symbol="BTC-USD", timeframe="5m"
            ),
        ]
        
        result = resample_candles(candles, "5m", "15m")
        
        # Should correctly aggregate despite order
        assert len(result) == 1
        assert result[0].open == 100.0  # First chronologically
        assert result[0].close == 105.0  # Last chronologically
        assert result[0].high == 108.0  # Max
        assert result[0].low == 95.0   # Min
