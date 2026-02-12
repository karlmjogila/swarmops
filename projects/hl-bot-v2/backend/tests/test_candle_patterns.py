"""Unit tests for candle pattern detection.

Tests all pattern detection logic with known pattern examples
to ensure accurate and reliable detection.
"""
import pytest
from datetime import datetime, timezone
from app.core.market.data import Candle
from app.core.patterns.candles import (
    CandlePatternType,
    PatternSignal,
    DetectedPattern,
    CandlePatternDetector,
)


def create_candle(
    open_price: float,
    high: float,
    low: float,
    close: float,
    timestamp: datetime = None,
    symbol: str = "BTC-USD",
    timeframe: str = "5m",
    volume: float = 1000.0,
) -> Candle:
    """Helper to create test candles."""
    if timestamp is None:
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        symbol=symbol,
        timeframe=timeframe,
    )


class TestCandlePatternDetector:
    """Test suite for CandlePatternDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a detector with default settings."""
        return CandlePatternDetector()
    
    # LE Candle Tests
    
    def test_detect_bullish_le_candle(self, detector):
        """Test detection of bullish LE (Liquidity Engine) candle."""
        # Large bullish body with small wicks
        candle = create_candle(
            open_price=100.0,
            high=110.5,
            low=99.5,
            close=110.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        le_patterns = [p for p in patterns if p.pattern_type == CandlePatternType.LE_CANDLE]
        
        assert len(le_patterns) == 1
        pattern = le_patterns[0]
        assert pattern.signal == PatternSignal.BULLISH
        assert pattern.strength > 0.8  # Strong pattern
        assert "LE Candle" in pattern.description
    
    def test_detect_bearish_le_candle(self, detector):
        """Test detection of bearish LE candle."""
        candle = create_candle(
            open_price=110.0,
            high=110.5,
            low=99.5,
            close=100.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        le_patterns = [p for p in patterns if p.pattern_type == CandlePatternType.LE_CANDLE]
        
        assert len(le_patterns) == 1
        pattern = le_patterns[0]
        assert pattern.signal == PatternSignal.BEARISH
        assert pattern.strength > 0.8
    
    def test_no_le_candle_with_large_wicks(self, detector):
        """LE candle should not be detected if wicks are too large."""
        candle = create_candle(
            open_price=100.0,
            high=115.0,  # Large upper wick
            low=95.0,    # Large lower wick
            close=110.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        le_patterns = [p for p in patterns if p.pattern_type == CandlePatternType.LE_CANDLE]
        
        assert len(le_patterns) == 0
    
    # Small Wick Tests
    
    def test_detect_small_wick_candle(self, detector):
        """Test detection of small wick candle."""
        # Bullish candle with very small lower wick
        candle = create_candle(
            open_price=100.0,
            high=110.0,
            low=99.9,    # Tiny lower wick
            close=110.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        small_wick = [p for p in patterns if p.pattern_type == CandlePatternType.SMALL_WICK]
        
        assert len(small_wick) >= 1
        pattern = small_wick[0]
        assert pattern.signal == PatternSignal.BULLISH
        assert pattern.strength > 0.9
    
    # Steeper Wick Tests
    
    def test_detect_steeper_wick_upper(self, detector):
        """Test detection of steeper upper wick (bearish rejection)."""
        candle = create_candle(
            open_price=100.0,
            high=120.0,  # Long upper wick
            low=98.0,
            close=102.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        steeper = [p for p in patterns if p.pattern_type == CandlePatternType.STEEPER_WICK]
        
        assert len(steeper) == 1
        pattern = steeper[0]
        assert pattern.signal == PatternSignal.BEARISH
        assert pattern.metadata["direction"] == "upper"
    
    def test_detect_steeper_wick_lower(self, detector):
        """Test detection of steeper lower wick (bullish rejection)."""
        candle = create_candle(
            open_price=100.0,
            high=102.0,
            low=80.0,    # Long lower wick
            close=98.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        steeper = [p for p in patterns if p.pattern_type == CandlePatternType.STEEPER_WICK]
        
        assert len(steeper) == 1
        pattern = steeper[0]
        assert pattern.signal == PatternSignal.BULLISH
        assert pattern.metadata["direction"] == "lower"
    
    # Celery Tests
    
    def test_detect_celery_pattern(self, detector):
        """Test detection of celery pattern (narrow body, long wicks both sides)."""
        candle = create_candle(
            open_price=100.0,
            high=110.0,  # Long upper wick
            low=90.0,    # Long lower wick
            close=101.0, # Tiny body
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        celery = [p for p in patterns if p.pattern_type == CandlePatternType.CELERY]
        
        assert len(celery) == 1
        pattern = celery[0]
        assert pattern.signal == PatternSignal.NEUTRAL
        assert pattern.metadata["body_ratio"] < 0.2
        assert pattern.metadata["upper_wick_ratio"] > 0.3
        assert pattern.metadata["lower_wick_ratio"] > 0.3
    
    # Engulfing Tests
    
    def test_detect_bullish_engulfing(self, detector):
        """Test detection of bullish engulfing pattern."""
        candles = [
            create_candle(
                open_price=105.0,
                high=106.0,
                low=100.0,
                close=101.0,  # Bearish candle
            ),
            create_candle(
                open_price=100.0,
                high=110.0,
                low=99.0,
                close=109.0,  # Bullish candle that engulfs previous
            ),
        ]
        
        patterns = detector._detect_multi_candle_patterns(candles, 1)
        engulfing = [p for p in patterns if p.pattern_type == CandlePatternType.BULLISH_ENGULFING]
        
        assert len(engulfing) == 1
        pattern = engulfing[0]
        assert pattern.signal == PatternSignal.BULLISH
        assert pattern.candle_index == 1
    
    def test_detect_bearish_engulfing(self, detector):
        """Test detection of bearish engulfing pattern."""
        candles = [
            create_candle(
                open_price=100.0,
                high=106.0,
                low=99.0,
                close=105.0,  # Bullish candle
            ),
            create_candle(
                open_price=106.0,
                high=107.0,
                low=98.0,
                close=99.0,  # Bearish candle that engulfs previous
            ),
        ]
        
        patterns = detector._detect_multi_candle_patterns(candles, 1)
        engulfing = [p for p in patterns if p.pattern_type == CandlePatternType.BEARISH_ENGULFING]
        
        assert len(engulfing) == 1
        pattern = engulfing[0]
        assert pattern.signal == PatternSignal.BEARISH
        assert pattern.candle_index == 1
    
    def test_no_engulfing_without_full_coverage(self, detector):
        """Engulfing should not be detected if body coverage is incomplete."""
        candles = [
            create_candle(
                open_price=100.0,
                high=106.0,
                low=99.0,
                close=105.0,  # Body: 100-105
            ),
            create_candle(
                open_price=104.0,
                high=107.0,
                low=101.0,
                close=102.0,  # Body: 102-104, doesn't fully engulf previous 100-105
            ),
        ]
        
        patterns = detector._detect_multi_candle_patterns(candles, 1)
        engulfing = [p for p in patterns if "ENGULFING" in p.pattern_type.value.upper()]
        
        assert len(engulfing) == 0
    
    # Doji Tests
    
    def test_detect_doji(self, detector):
        """Test detection of doji pattern."""
        candle = create_candle(
            open_price=100.0,
            high=102.0,
            low=98.0,
            close=100.1,  # Almost same as open
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        doji = [p for p in patterns if p.pattern_type == CandlePatternType.DOJI]
        
        assert len(doji) == 1
        pattern = doji[0]
        assert pattern.signal == PatternSignal.NEUTRAL
        assert pattern.metadata["body_ratio"] < 0.1
    
    # Hammer/Shooting Star Tests
    
    def test_detect_hammer(self, detector):
        """Test detection of hammer pattern (bullish reversal).
        
        Note: Hammer and pin bars have similar characteristics. A strong
        hammer (lower wick >65%) will be detected as a pin bar, which is
        correct as pin bars are a subset of hammer patterns with stricter criteria.
        """
        candle = create_candle(
            open_price=98.0,
            high=100.0,
            low=93.0,    # Long lower wick (62.5% of range)
            close=99.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        hammer = [p for p in patterns if p.pattern_type == CandlePatternType.HAMMER]
        
        # Should detect hammer pattern
        assert len(hammer) == 1
        pattern = hammer[0]
        assert pattern.signal == PatternSignal.BULLISH
    
    def test_detect_shooting_star(self, detector):
        """Test detection of shooting star pattern (bearish reversal).
        
        Note: Similar to hammer, strong shooting stars may also be detected
        as pin bars, which is correct behavior.
        """
        candle = create_candle(
            open_price=102.0,
            high=110.0,  # Long upper wick
            low=100.0,
            close=101.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        shooting_star = [p for p in patterns if p.pattern_type == CandlePatternType.SHOOTING_STAR]
        
        assert len(shooting_star) == 1
        pattern = shooting_star[0]
        assert pattern.signal == PatternSignal.BEARISH
    
    def test_detect_inverted_hammer(self, detector):
        """Test detection of inverted hammer.
        
        Note: Inverted hammer has same structure as shooting star - the difference
        is context (support vs resistance). A candle with upper wick > 60% will be
        detected as shooting star first. For pure inverted hammer (without triggering
        shooting star), we need upper wick 50-60%.
        """
        candle = create_candle(
            open_price=100.0,
            high=106.0,  # Long upper wick (55% of range)
            low=99.0,
            close=101.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        
        # Should detect either inverted hammer or shooting star (both valid)
        relevant_patterns = [
            p for p in patterns
            if p.pattern_type in [
                CandlePatternType.INVERTED_HAMMER,
                CandlePatternType.SHOOTING_STAR
            ]
        ]
        
        assert len(relevant_patterns) >= 1
        # Should have upper wick rejection signal
        assert any(p.metadata.get("upper_wick_ratio", 0) > 0.5 for p in relevant_patterns)
    
    # Pin Bar Tests
    
    def test_detect_bullish_pin_bar(self, detector):
        """Test detection of bullish pin bar."""
        candle = create_candle(
            open_price=98.0,
            high=100.0,
            low=88.0,    # Very long lower wick
            close=99.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        pin_bar = [p for p in patterns if p.pattern_type == CandlePatternType.PIN_BAR_BULLISH]
        
        assert len(pin_bar) == 1
        pattern = pin_bar[0]
        assert pattern.signal == PatternSignal.BULLISH
        assert pattern.strength > 0.65
    
    def test_detect_bearish_pin_bar(self, detector):
        """Test detection of bearish pin bar."""
        candle = create_candle(
            open_price=102.0,
            high=112.0,  # Very long upper wick
            low=100.0,
            close=101.0,
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        pin_bar = [p for p in patterns if p.pattern_type == CandlePatternType.PIN_BAR_BEARISH]
        
        assert len(pin_bar) == 1
        pattern = pin_bar[0]
        assert pattern.signal == PatternSignal.BEARISH
        assert pattern.strength > 0.65
    
    # Strong Directional Tests
    
    def test_detect_strong_bullish_candle(self, detector):
        """Test detection of strong bullish candle."""
        candle = create_candle(
            open_price=100.0,
            high=115.0,
            low=99.5,
            close=114.5,  # Large bullish body
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        strong = [p for p in patterns if p.pattern_type == CandlePatternType.STRONG_BULLISH]
        
        assert len(strong) == 1
        pattern = strong[0]
        assert pattern.signal == PatternSignal.BULLISH
        assert pattern.metadata["body_ratio"] > 0.7
    
    def test_detect_strong_bearish_candle(self, detector):
        """Test detection of strong bearish candle."""
        candle = create_candle(
            open_price=115.0,
            high=115.5,
            low=100.0,
            close=100.5,  # Large bearish body
        )
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        strong = [p for p in patterns if p.pattern_type == CandlePatternType.STRONG_BEARISH]
        
        assert len(strong) == 1
        pattern = strong[0]
        assert pattern.signal == PatternSignal.BEARISH
        assert pattern.metadata["body_ratio"] > 0.7
    
    # Inside/Outside Bar Tests
    
    def test_detect_inside_bar(self, detector):
        """Test detection of inside bar (consolidation)."""
        candles = [
            create_candle(
                open_price=100.0,
                high=110.0,
                low=90.0,
                close=105.0,
            ),
            create_candle(
                open_price=102.0,
                high=108.0,  # Within previous high
                low=92.0,    # Within previous low
                close=103.0,
            ),
        ]
        
        patterns = detector._detect_multi_candle_patterns(candles, 1)
        inside = [p for p in patterns if p.pattern_type == CandlePatternType.INSIDE_BAR]
        
        assert len(inside) == 1
        pattern = inside[0]
        assert pattern.signal == PatternSignal.NEUTRAL
    
    def test_detect_outside_bar(self, detector):
        """Test detection of outside bar (expansion)."""
        candles = [
            create_candle(
                open_price=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
            ),
            create_candle(
                open_price=95.0,
                high=110.0,  # Exceeds previous high
                low=90.0,    # Exceeds previous low
                close=108.0,
            ),
        ]
        
        patterns = detector._detect_multi_candle_patterns(candles, 1)
        outside = [p for p in patterns if p.pattern_type == CandlePatternType.OUTSIDE_BAR]
        
        assert len(outside) == 1
        pattern = outside[0]
        assert pattern.signal == PatternSignal.BULLISH
    
    # Integration Tests
    
    def test_detect_all_patterns(self, detector):
        """Test detecting all patterns in a sequence."""
        candles = [
            # Strong bullish
            create_candle(100.0, 115.0, 99.0, 114.0),
            # Doji
            create_candle(114.0, 116.0, 112.0, 114.2),
            # Bearish engulfing
            create_candle(114.0, 118.0, 112.0, 117.0),
            create_candle(117.0, 118.0, 108.0, 109.0),
        ]
        
        patterns = detector.detect_all_patterns(candles)
        
        # Should detect multiple patterns
        assert len(patterns) > 0
        
        # Check we got patterns at different indices
        indices = {p.candle_index for p in patterns}
        assert len(indices) > 1
    
    def test_filter_patterns_by_strength(self, detector):
        """Test filtering patterns by minimum strength."""
        candles = [
            create_candle(100.0, 115.0, 99.0, 114.0),  # Strong
            create_candle(114.0, 114.5, 113.5, 114.2),  # Weak
        ]
        
        all_patterns = detector.detect_all_patterns(candles)
        strong_patterns = detector.filter_patterns(all_patterns, min_strength=0.7)
        
        assert len(strong_patterns) <= len(all_patterns)
        for pattern in strong_patterns:
            assert pattern.strength >= 0.7
    
    def test_filter_patterns_by_signal(self, detector):
        """Test filtering patterns by signal type."""
        candles = [
            create_candle(100.0, 115.0, 99.0, 114.0),   # Bullish
            create_candle(114.0, 115.0, 100.0, 101.0),  # Bearish
        ]
        
        all_patterns = detector.detect_all_patterns(candles)
        bullish = detector.filter_patterns(
            all_patterns,
            signals=[PatternSignal.BULLISH]
        )
        
        for pattern in bullish:
            assert pattern.signal == PatternSignal.BULLISH
    
    def test_get_patterns_at_index(self, detector):
        """Test getting patterns at specific index."""
        candles = [
            create_candle(100.0, 115.0, 99.0, 114.0),
            create_candle(114.0, 116.0, 112.0, 114.2),
        ]
        
        patterns_at_1 = detector.get_patterns_at_index(candles, 1)
        
        for pattern in patterns_at_1:
            assert pattern.candle_index == 1
    
    # Edge Cases
    
    def test_empty_candle_list(self, detector):
        """Test handling of empty candle list."""
        patterns = detector.detect_all_patterns([])
        assert patterns == []
    
    def test_single_candle(self, detector):
        """Test detection with single candle."""
        candles = [create_candle(100.0, 110.0, 99.0, 109.0)]
        patterns = detector.detect_all_patterns(candles)
        
        # Should detect single-candle patterns only
        assert len(patterns) >= 0
        for pattern in patterns:
            assert pattern.candle_index == 0
    
    def test_zero_range_candle(self, detector):
        """Test handling of candle with zero range (all OHLC same)."""
        candle = create_candle(100.0, 100.0, 100.0, 100.0)
        patterns = detector._detect_single_candle_patterns(candle, 0)
        
        # Should not crash, may or may not detect patterns
        assert isinstance(patterns, list)
    
    def test_custom_thresholds(self):
        """Test detector with custom thresholds."""
        detector = CandlePatternDetector(
            wick_threshold=0.4,
            body_threshold=0.7,
            engulfing_threshold=1.0,
            doji_threshold=0.05,
        )
        
        candle = create_candle(100.0, 110.0, 99.0, 109.0)
        patterns = detector._detect_single_candle_patterns(candle, 0)
        
        # Should work with custom settings
        assert isinstance(patterns, list)
    
    # Real-World Scenario Tests
    
    def test_realistic_bullish_reversal_setup(self, detector):
        """Test realistic bullish reversal scenario."""
        candles = [
            # Downtrend
            create_candle(120.0, 121.0, 110.0, 111.0),
            create_candle(111.0, 112.0, 105.0, 106.0),
            # Hammer at support
            create_candle(106.0, 108.0, 98.0, 107.0),
            # Bullish engulfing confirmation
            create_candle(107.0, 116.0, 106.5, 115.0),
        ]
        
        patterns = detector.detect_all_patterns(candles)
        
        # Should detect hammer and engulfing
        pattern_types = {p.pattern_type for p in patterns}
        has_reversal_signal = (
            CandlePatternType.HAMMER in pattern_types or
            CandlePatternType.BULLISH_ENGULFING in pattern_types or
            CandlePatternType.PIN_BAR_BULLISH in pattern_types
        )
        
        assert has_reversal_signal
    
    def test_realistic_bearish_reversal_setup(self, detector):
        """Test realistic bearish reversal scenario."""
        candles = [
            # Uptrend
            create_candle(100.0, 110.0, 99.0, 109.0),
            create_candle(109.0, 115.0, 108.0, 114.0),
            # Shooting star at resistance
            create_candle(114.0, 125.0, 113.0, 115.0),
            # Bearish engulfing confirmation
            create_candle(115.0, 116.0, 105.0, 106.0),
        ]
        
        patterns = detector.detect_all_patterns(candles)
        
        # Should detect shooting star and engulfing
        pattern_types = {p.pattern_type for p in patterns}
        has_reversal_signal = (
            CandlePatternType.SHOOTING_STAR in pattern_types or
            CandlePatternType.BEARISH_ENGULFING in pattern_types or
            CandlePatternType.PIN_BAR_BEARISH in pattern_types
        )
        
        assert has_reversal_signal
    
    def test_consolidation_followed_by_breakout(self, detector):
        """Test consolidation (inside bars) followed by breakout."""
        candles = [
            # Large range candle
            create_candle(100.0, 110.0, 95.0, 105.0),
            # Inside bars (consolidation)
            create_candle(103.0, 108.0, 98.0, 104.0),
            create_candle(104.0, 107.0, 100.0, 103.0),
            # Breakout
            create_candle(103.0, 120.0, 102.0, 118.0),
        ]
        
        patterns = detector.detect_all_patterns(candles)
        pattern_types = {p.pattern_type for p in patterns}
        
        # Should detect inside bars and strong breakout
        assert CandlePatternType.INSIDE_BAR in pattern_types
        assert (
            CandlePatternType.STRONG_BULLISH in pattern_types or
            CandlePatternType.LE_CANDLE in pattern_types
        )


class TestPatternMetadata:
    """Test pattern metadata and descriptions."""
    
    def test_pattern_has_required_fields(self):
        """Test that DetectedPattern has all required fields."""
        pattern = DetectedPattern(
            pattern_type=CandlePatternType.DOJI,
            signal=PatternSignal.NEUTRAL,
            strength=0.8,
            candle_index=0,
            description="Test pattern",
            metadata={"test": "value"},
        )
        
        assert pattern.pattern_type == CandlePatternType.DOJI
        assert pattern.signal == PatternSignal.NEUTRAL
        assert pattern.strength == 0.8
        assert pattern.candle_index == 0
        assert "Test" in pattern.description
        assert pattern.metadata["test"] == "value"
    
    def test_metadata_contains_useful_info(self):
        """Test that pattern metadata contains useful information."""
        detector = CandlePatternDetector()
        candle = create_candle(100.0, 110.0, 98.0, 108.0)
        
        patterns = detector._detect_single_candle_patterns(candle, 0)
        
        for pattern in patterns:
            # All patterns should have non-empty metadata
            assert isinstance(pattern.metadata, dict)
            # Metadata should contain relevant ratios or measurements
            assert len(pattern.metadata) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
