"""
Tests for Confluence Scorer

Comprehensive test suite covering all scoring components and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from src.detection.confluence_scorer import (
    ConfluenceScorer, TimeframeContext, ConfluenceScore
)
from src.types import (
    CandleData, PatternDetection, Timeframe, OrderSide, MarketCycle, EntryType
)


# ===== Test Fixtures =====

@pytest.fixture
def scorer():
    """Create a ConfluenceScorer instance."""
    return ConfluenceScorer()


@pytest.fixture
def sample_candles():
    """Generate sample candle data."""
    base_time = datetime(2024, 1, 1, 0, 0)
    candles = []
    
    for i in range(100):
        candles.append(CandleData(
            timestamp=base_time + timedelta(minutes=15 * i),
            open=100.0 + i * 0.5,
            high=102.0 + i * 0.5,
            low=99.0 + i * 0.5,
            close=101.0 + i * 0.5,
            volume=1000.0,
            timeframe=Timeframe.M15,
        ))
    
    return candles


@pytest.fixture
def bullish_le_pattern():
    """Create a bullish LE pattern."""
    return PatternDetection(
        pattern_type=EntryType.LE,
        timeframe=Timeframe.M15,
        asset="BTC-USD",
        confidence=0.85,
        pattern_data={'bias': 'bullish'},
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def bearish_le_pattern():
    """Create a bearish LE pattern."""
    return PatternDetection(
        pattern_type=EntryType.LE,
        timeframe=Timeframe.M15,
        asset="BTC-USD",
        confidence=0.78,
        pattern_data={'bias': 'bearish'},
        timestamp=datetime.utcnow(),
    )


# ===== Scoring Component Tests =====

class TestPatternScoring:
    """Test pattern scoring component."""
    
    def test_single_pattern_score(self, scorer, sample_candles, bullish_le_pattern):
        """Test scoring with a single pattern."""
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        # Pattern score should match pattern confidence
        assert result.pattern_score >= bullish_le_pattern.confidence * 0.9
        assert result.entry_bias == OrderSide.LONG
        assert len(result.entry_patterns) == 1
    
    def test_multiple_confirming_patterns(self, scorer, sample_candles, bullish_le_pattern):
        """Test boost for multiple patterns with same bias."""
        pattern2 = PatternDetection(
            pattern_type=EntryType.SMALL_WICK,
            timeframe=Timeframe.M15,
            asset="BTC-USD",
            confidence=0.75,
            pattern_data={'bias': 'bullish'},
            timestamp=datetime.utcnow(),
        )
        
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern, pattern2],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        # Should get boost for multiple confirming patterns
        assert result.pattern_score > bullish_le_pattern.confidence
        assert "Multiple" in ' '.join(result.confluence_factors)
    
    def test_no_patterns(self, scorer, sample_candles):
        """Test handling of no patterns detected."""
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert result.pattern_score == 0.0
        assert "No patterns detected" in ' '.join(result.warnings)


class TestStructureScoring:
    """Test market structure scoring component."""
    
    def test_htf_trend_alignment(self, scorer, sample_candles, bullish_le_pattern):
        """Test scoring when HTF trend aligns with entry bias."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        h4_ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.85,
        )
        
        contexts = {
            Timeframe.M15: m15_ctx,
            Timeframe.H4: h4_ctx,
        }
        
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4,
        )
        
        assert result.structure_score > 0.5
        assert any("HTF" in f and "trend" in f for f in result.confluence_factors)
    
    def test_htf_trend_conflict(self, scorer, sample_candles, bullish_le_pattern):
        """Test penalty when HTF trend conflicts with entry bias."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        h4_ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.SHORT,  # Conflicts with bullish pattern
            trend_strength=0.75,
        )
        
        contexts = {
            Timeframe.M15: m15_ctx,
            Timeframe.H4: h4_ctx,
        }
        
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4,
        )
        
        assert any("against HTF trend" in w for w in result.warnings)
    
    def test_recent_bos_aligned(self, scorer, sample_candles, bullish_le_pattern):
        """Test boost for recent BOS in same direction."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
            recent_bos=OrderSide.LONG,
        )
        
        contexts = {Timeframe.M15: m15_ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert result.structure_score > 0.3
        assert any("BOS" in f for f in result.confluence_factors)


class TestCycleScoring:
    """Test market cycle scoring component."""
    
    def test_preferred_cycle(self, scorer, sample_candles, bullish_le_pattern):
        """Test high score when pattern is in preferred cycle."""
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
            market_cycle=MarketCycle.DRIVE,  # LE prefers DRIVE
            cycle_confidence=0.80,
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert result.cycle_score >= 0.7
        assert any("preferred" in f and "cycle" in f.lower() for f in result.confluence_factors)
    
    def test_non_preferred_cycle(self, scorer, sample_candles):
        """Test lower score when pattern is in non-preferred cycle."""
        pattern = PatternDetection(
            pattern_type=EntryType.SMALL_WICK,  # Prefers DRIVE
            timeframe=Timeframe.M15,
            asset="BTC-USD",
            confidence=0.80,
            pattern_data={'bias': 'bullish'},
            timestamp=datetime.utcnow(),
        )
        
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[pattern],
            market_cycle=MarketCycle.RANGE,  # Not preferred
            cycle_confidence=0.70,
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert result.cycle_score < 0.5


class TestTimeframeAlignment:
    """Test multi-timeframe alignment scoring."""
    
    def test_strong_htf_alignment(self, scorer, sample_candles, bullish_le_pattern):
        """Test strong alignment across timeframes."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
            market_cycle=MarketCycle.DRIVE,
        )
        
        h1_ctx = TimeframeContext(
            timeframe=Timeframe.H1,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.70,
            market_cycle=MarketCycle.DRIVE,
        )
        
        h4_ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.85,
            market_cycle=MarketCycle.DRIVE,
        )
        
        contexts = {
            Timeframe.M15: m15_ctx,
            Timeframe.H1: h1_ctx,
            Timeframe.H4: h4_ctx,
        }
        
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4,
        )
        
        assert result.timeframe_alignment_score >= 0.7
        assert any("aligned" in f.lower() for f in result.confluence_factors)
    
    def test_auto_detect_htf(self, scorer, sample_candles, bullish_le_pattern):
        """Test auto-detection of higher timeframe."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        h4_ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.80,
        )
        
        contexts = {
            Timeframe.M15: m15_ctx,
            Timeframe.H4: h4_ctx,
        }
        
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
            higher_timeframe=None,  # Auto-detect
        )
        
        assert result.htf_timeframe == Timeframe.H4


class TestZoneScoring:
    """Test zone interaction scoring."""
    
    def test_long_from_support(self, scorer, sample_candles, bullish_le_pattern):
        """Test boost for long entry from support zone."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
            in_support_zone=True,
            zone_strength=0.75,
            zone_type='support',
        )
        
        contexts = {Timeframe.M15: m15_ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert result.zone_score > 0.6
        assert any("support" in f.lower() for f in result.confluence_factors)
    
    def test_short_from_resistance(self, scorer, sample_candles, bearish_le_pattern):
        """Test boost for short entry from resistance zone."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bearish_le_pattern],
            in_resistance_zone=True,
            zone_strength=0.80,
            zone_type='resistance',
        )
        
        contexts = {Timeframe.M15: m15_ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert result.zone_score > 0.6
        assert any("resistance" in f.lower() for f in result.confluence_factors)
    
    def test_zone_conflict(self, scorer, sample_candles, bullish_le_pattern):
        """Test penalty for entering long at resistance."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
            in_resistance_zone=True,
            zone_strength=0.70,
            zone_type='resistance',
        )
        
        contexts = {Timeframe.M15: m15_ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        assert any("resistance" in w.lower() for w in result.warnings)


class TestSignalGeneration:
    """Test signal generation logic."""
    
    def test_excellent_confluence_generates_signal(self, scorer, sample_candles):
        """Test that excellent confluence generates a signal."""
        pattern = PatternDetection(
            pattern_type=EntryType.LE,
            timeframe=Timeframe.M15,
            asset="BTC-USD",
            confidence=0.90,
            pattern_data={'bias': 'bullish'},
            timestamp=datetime.utcnow(),
        )
        
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[pattern],
            market_cycle=MarketCycle.DRIVE,
            cycle_confidence=0.85,
            in_support_zone=True,
            zone_strength=0.80,
            recent_bos=OrderSide.LONG,
        )
        
        h4_ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.90,
            market_cycle=MarketCycle.DRIVE,
            cycle_confidence=0.88,
        )
        
        contexts = {
            Timeframe.M15: m15_ctx,
            Timeframe.H4: h4_ctx,
        }
        
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4,
        )
        
        assert result.generates_signal is True
        assert result.signal_quality in ['strong', 'excellent']
        assert result.total_score >= 0.65
    
    def test_poor_confluence_no_signal(self, scorer, sample_candles, bullish_le_pattern):
        """Test that poor confluence doesn't generate a signal."""
        m15_ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
            market_cycle=MarketCycle.RANGE,  # Non-preferred
            cycle_confidence=0.50,
        )
        
        h4_ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
            trend_direction=OrderSide.SHORT,  # Conflicting
            trend_strength=0.60,
        )
        
        contexts = {
            Timeframe.M15: m15_ctx,
            Timeframe.H4: h4_ctx,
        }
        
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4,
        )
        
        assert result.generates_signal is False
        assert result.total_score < 0.50


class TestConvenienceMethod:
    """Test the analyze_multi_timeframe convenience method."""
    
    def test_convenience_method(self, scorer, sample_candles, bullish_le_pattern):
        """Test the convenience method works correctly."""
        result = scorer.analyze_multi_timeframe(
            asset="BTC-USD",
            candles_by_tf={
                Timeframe.M15: sample_candles,
                Timeframe.H4: sample_candles,
            },
            patterns_by_tf={
                Timeframe.M15: [bullish_le_pattern],
                Timeframe.H4: [],
            },
            structure_by_tf={
                Timeframe.M15: {
                    'trend_direction': OrderSide.LONG,
                    'trend_strength': 0.70,
                },
                Timeframe.H4: {
                    'trend_direction': OrderSide.LONG,
                    'trend_strength': 0.85,
                },
            },
            cycle_by_tf={
                Timeframe.M15: (MarketCycle.DRIVE, 0.75),
                Timeframe.H4: (MarketCycle.DRIVE, 0.82),
            },
            entry_timeframe=Timeframe.M15,
        )
        
        assert isinstance(result, ConfluenceScore)
        assert result.asset == "BTC-USD"
        assert result.entry_timeframe == Timeframe.M15
        assert len(result.timeframes_analyzed) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_single_timeframe_only(self, scorer, sample_candles, bullish_le_pattern):
        """Test with only a single timeframe."""
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        # Should still score, but with neutral timeframe alignment
        assert isinstance(result, ConfluenceScore)
        assert result.timeframe_alignment_score == 0.5
    
    def test_missing_primary_timeframe(self, scorer, sample_candles):
        """Test handling of missing primary timeframe."""
        ctx = TimeframeContext(
            timeframe=Timeframe.H4,
            candles=sample_candles,
            patterns=[],
        )
        
        contexts = {Timeframe.H4: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,  # Not in contexts
        )
        
        assert any("not in contexts" in w for w in result.warnings)
        assert result.total_score == 0.0
    
    def test_empty_candles(self, scorer, bullish_le_pattern):
        """Test with empty candle list."""
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=[],
            patterns=[bullish_le_pattern],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        # Should still work (scoring doesn't directly use candles)
        assert isinstance(result, ConfluenceScore)


class TestConfigurationCustomization:
    """Test scorer configuration customization."""
    
    def test_custom_weights(self, scorer, sample_candles, bullish_le_pattern):
        """Test that custom weights affect scoring."""
        # Increase pattern weight
        scorer.weights['pattern'] = 0.50
        scorer.weights['structure'] = 0.20
        scorer.weights['cycle'] = 0.10
        scorer.weights['timeframe'] = 0.15
        scorer.weights['zone'] = 0.05
        
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        # With higher pattern weight, total score should be closer to pattern score
        assert abs(result.total_score - result.pattern_score * 0.5) < 0.3
    
    def test_custom_thresholds(self, scorer, sample_candles, bullish_le_pattern):
        """Test custom signal generation thresholds."""
        # Set very high thresholds
        scorer.min_total_score = 0.95
        scorer.min_pattern_score = 0.90
        
        ctx = TimeframeContext(
            timeframe=Timeframe.M15,
            candles=sample_candles,
            patterns=[bullish_le_pattern],
        )
        
        contexts = {Timeframe.M15: ctx}
        result = scorer.score_confluence(
            asset="BTC-USD",
            timeframe_contexts=contexts,
            primary_timeframe=Timeframe.M15,
        )
        
        # Should not generate signal due to high thresholds
        assert result.generates_signal is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
