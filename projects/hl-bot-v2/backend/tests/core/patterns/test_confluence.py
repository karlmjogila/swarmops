"""Tests for multi-timeframe confluence scoring."""
import pytest
from datetime import datetime, timezone
from typing import List

from app.core.market.data import Candle
from app.core.patterns.confluence import (
    MultiTimeframeConfluenceScorer,
    ConfluenceSignal,
    score_confluence,
)
from app.core.patterns.candles import PatternSignal


def create_test_candles(
    count: int,
    symbol: str = "BTC-USD",
    timeframe: str = "5m",
    start_price: float = 100.0,
    trend: str = "bullish",
) -> List[Candle]:
    """Helper to create test candle data.
    
    Args:
        count: Number of candles to create
        symbol: Trading symbol
        timeframe: Timeframe string
        start_price: Starting price
        trend: "bullish", "bearish", or "sideways"
    """
    from datetime import timedelta
    candles = []
    current_price = start_price
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 5)
        
        if trend == "bullish":
            # Uptrend
            open_price = current_price
            close = current_price + 1.0
            high = close + 0.5
            low = open_price - 0.3
            current_price = close
        elif trend == "bearish":
            # Downtrend
            open_price = current_price
            close = current_price - 1.0
            high = open_price + 0.3
            low = close - 0.5
            current_price = close
        else:
            # Sideways
            open_price = current_price
            close = current_price + (0.5 if i % 2 == 0 else -0.5)
            high = max(open_price, close) + 0.3
            low = min(open_price, close) - 0.3
            current_price = close
        
        candles.append(Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=1000.0,
            symbol=symbol,
            timeframe=timeframe,
        ))
    
    return candles


class TestMultiTimeframeConfluenceScorer:
    """Tests for MultiTimeframeConfluenceScorer."""
    
    def test_initialization(self):
        """Test scorer can be initialized."""
        scorer = MultiTimeframeConfluenceScorer()
        assert scorer is not None
        assert scorer.pattern_detector is not None
        assert scorer.structure_analyzer is not None
        assert scorer.zone_detector is not None
    
    def test_analyze_single_timeframe(self):
        """Test analyzing a single timeframe."""
        scorer = MultiTimeframeConfluenceScorer()
        candles = create_test_candles(50, trend="bullish")
        
        analysis = scorer.analyze_timeframe(candles, "5m")
        
        assert analysis.timeframe == "5m"
        assert analysis.candles == candles
        assert analysis.patterns is not None
        assert analysis.swings is not None
        assert analysis.structure_breaks is not None
        assert analysis.zones is not None
    
    def test_score_confluence_bullish_alignment(self):
        """Test scoring when all timeframes are bullish."""
        scorer = MultiTimeframeConfluenceScorer()
        
        # Create bullish candles for multiple timeframes
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m"),
            "15m": create_test_candles(50, trend="bullish", timeframe="15m"),
            "1h": create_test_candles(25, trend="bullish", timeframe="1h"),
        }
        
        score = scorer.score_confluence(mtf_data, "15m")
        
        assert score.overall_score >= 0.0
        assert score.overall_score <= 100.0
        assert score.signal in [
            ConfluenceSignal.BULLISH,
            ConfluenceSignal.STRONG_BULLISH,
            ConfluenceSignal.NEUTRAL,
        ]
        assert "5m" in score.timeframe_scores
        assert "15m" in score.timeframe_scores
        assert "1h" in score.timeframe_scores
        assert score.dominant_timeframe in ["5m", "15m", "1h"]
    
    def test_score_confluence_bearish_alignment(self):
        """Test scoring when all timeframes are bearish."""
        scorer = MultiTimeframeConfluenceScorer()
        
        mtf_data = {
            "5m": create_test_candles(100, trend="bearish", timeframe="5m"),
            "15m": create_test_candles(50, trend="bearish", timeframe="15m"),
            "1h": create_test_candles(25, trend="bearish", timeframe="1h"),
        }
        
        score = scorer.score_confluence(mtf_data, "15m")
        
        assert score.overall_score >= 0.0
        assert score.overall_score <= 100.0
        assert score.signal in [
            ConfluenceSignal.BEARISH,
            ConfluenceSignal.STRONG_BEARISH,
            ConfluenceSignal.NEUTRAL,
        ]
    
    def test_score_confluence_mixed_signals(self):
        """Test scoring when timeframes have mixed signals."""
        scorer = MultiTimeframeConfluenceScorer()
        
        # Mixed: bullish 5m, bearish 15m, sideways 1h
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m", start_price=100),
            "15m": create_test_candles(50, trend="bearish", timeframe="15m", start_price=110),
            "1h": create_test_candles(25, trend="sideways", timeframe="1h", start_price=105),
        }
        
        score = scorer.score_confluence(mtf_data, "15m")
        
        assert score.overall_score >= 0.0
        assert score.overall_score <= 100.0
        # With mixed signals, score should be lower
        assert score.overall_score < 80.0
        # Should have some conflicting timeframes
        assert len(score.conflicting_timeframes) >= 0
    
    def test_score_confluence_custom_weights(self):
        """Test scoring with custom timeframe weights."""
        scorer = MultiTimeframeConfluenceScorer()
        
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m"),
            "15m": create_test_candles(50, trend="bullish", timeframe="15m"),
        }
        
        # Give higher weight to 5m
        custom_weights = {"5m": 2.0, "15m": 1.0}
        
        score = scorer.score_confluence(mtf_data, "15m", custom_weights)
        
        assert score.overall_score >= 0.0
        assert score.overall_score <= 100.0
    
    def test_agreement_percentage(self):
        """Test agreement percentage calculation."""
        scorer = MultiTimeframeConfluenceScorer()
        
        # All bullish
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m"),
            "15m": create_test_candles(50, trend="bullish", timeframe="15m"),
            "1h": create_test_candles(25, trend="bullish", timeframe="1h"),
        }
        
        score = scorer.score_confluence(mtf_data, "15m")
        
        # Agreement should be high when all timeframes agree
        assert score.agreement_percentage >= 0.0
        assert score.agreement_percentage <= 100.0
    
    def test_empty_data_raises_error(self):
        """Test that empty data raises appropriate error."""
        scorer = MultiTimeframeConfluenceScorer()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            scorer.score_confluence({}, "15m")
    
    def test_missing_analysis_timeframe_raises_error(self):
        """Test error when analysis timeframe not in data."""
        scorer = MultiTimeframeConfluenceScorer()
        
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m"),
        }
        
        with pytest.raises(ValueError, match="not in data"):
            scorer.score_confluence(mtf_data, "15m")
    
    def test_confluence_score_serialization(self):
        """Test ConfluenceScore can be serialized to dict."""
        scorer = MultiTimeframeConfluenceScorer()
        
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m"),
            "15m": create_test_candles(50, trend="bullish", timeframe="15m"),
        }
        
        score = scorer.score_confluence(mtf_data, "15m")
        score_dict = score.to_dict()
        
        assert isinstance(score_dict, dict)
        assert "overall_score" in score_dict
        assert "signal" in score_dict
        assert "pattern_alignment" in score_dict
        assert "structure_alignment" in score_dict
        assert "zone_alignment" in score_dict
        assert "timeframe_scores" in score_dict
        assert "agreement_percentage" in score_dict


class TestConvenienceFunction:
    """Tests for the convenience score_confluence function."""
    
    def test_score_confluence_function(self):
        """Test the convenience function works."""
        mtf_data = {
            "5m": create_test_candles(100, trend="bullish", timeframe="5m"),
            "15m": create_test_candles(50, trend="bullish", timeframe="15m"),
        }
        
        score = score_confluence(mtf_data, "15m")
        
        assert score.overall_score >= 0.0
        assert score.overall_score <= 100.0
        assert score.signal is not None


class TestTimeframeAnalysis:
    """Tests for TimeframeAnalysis component."""
    
    def test_get_pattern_signal_score(self):
        """Test pattern signal scoring for a timeframe."""
        scorer = MultiTimeframeConfluenceScorer()
        candles = create_test_candles(50, trend="bullish")
        
        analysis = scorer.analyze_timeframe(candles, "5m")
        signal, strength = analysis.get_pattern_signal_score()
        
        assert signal in [PatternSignal.BULLISH, PatternSignal.BEARISH, PatternSignal.NEUTRAL]
        assert 0.0 <= strength <= 1.0
    
    def test_get_structure_signal(self):
        """Test structure signal for a timeframe."""
        scorer = MultiTimeframeConfluenceScorer()
        candles = create_test_candles(50, trend="bullish")
        
        analysis = scorer.analyze_timeframe(candles, "5m")
        signal, strength = analysis.get_structure_signal()
        
        assert signal in [PatternSignal.BULLISH, PatternSignal.BEARISH, PatternSignal.NEUTRAL]
        assert 0.0 <= strength <= 1.0
    
    def test_get_zone_signal(self):
        """Test zone signal for a timeframe."""
        scorer = MultiTimeframeConfluenceScorer()
        candles = create_test_candles(50, trend="bullish")
        
        analysis = scorer.analyze_timeframe(candles, "5m")
        current_price = candles[-1].close
        signal, strength = analysis.get_zone_signal(current_price)
        
        assert signal in [PatternSignal.BULLISH, PatternSignal.BEARISH, PatternSignal.NEUTRAL]
        assert 0.0 <= strength <= 1.0


class TestIntegration:
    """Integration tests with real pattern detection."""
    
    def test_end_to_end_confluence_scoring(self):
        """Test complete confluence scoring pipeline."""
        # Create realistic multi-timeframe data
        # 5m: Recent bullish move
        candles_5m = create_test_candles(100, trend="bullish", timeframe="5m", start_price=100)
        
        # 15m: Also bullish (aligned)
        candles_15m = create_test_candles(50, trend="bullish", timeframe="15m", start_price=100)
        
        # 1h: Ranging (less clear)
        candles_1h = create_test_candles(25, trend="sideways", timeframe="1h", start_price=105)
        
        mtf_data = {
            "5m": candles_5m,
            "15m": candles_15m,
            "1h": candles_1h,
        }
        
        # Score confluence
        score = score_confluence(mtf_data, "15m")
        
        # Verify result structure
        assert isinstance(score.overall_score, float)
        assert isinstance(score.signal, ConfluenceSignal)
        assert isinstance(score.pattern_alignment_score, float)
        assert isinstance(score.structure_alignment_score, float)
        assert isinstance(score.zone_alignment_score, float)
        assert isinstance(score.timeframe_scores, dict)
        assert isinstance(score.timeframe_signals, dict)
        assert isinstance(score.dominant_timeframe, str)
        assert isinstance(score.conflicting_timeframes, list)
        assert isinstance(score.agreement_percentage, float)
        
        # Verify score ranges
        assert 0.0 <= score.overall_score <= 100.0
        assert 0.0 <= score.pattern_alignment_score <= 1.0
        assert 0.0 <= score.structure_alignment_score <= 1.0
        assert 0.0 <= score.zone_alignment_score <= 1.0
        assert 0.0 <= score.agreement_percentage <= 100.0
        
        # Verify all timeframes are scored
        assert len(score.timeframe_scores) == 3
        assert "5m" in score.timeframe_scores
        assert "15m" in score.timeframe_scores
        assert "1h" in score.timeframe_scores
