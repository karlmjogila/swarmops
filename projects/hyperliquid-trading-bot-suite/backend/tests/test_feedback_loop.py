"""
Tests for feedback loop module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import List

from src.learning.feedback_loop import (
    FeedbackLoop,
    LearningContext,
    ImprovementMetrics,
    ABTestVariant,
    run_feedback_cycle
)
from src.learning.outcome_analyzer import (
    StrategyAnalysis,
    PatternInsight
)
from src.types import (
    TradeOutcome,
    OrderSide,
    MarketCycle,
    EntryType
)
from src.knowledge.models import (
    StrategyRule,
    TradeRecord,
    LearningEntry,
    ContentSource,
    SourceType,
    RiskParameters
)


@pytest.fixture
def sample_strategy():
    """Create a sample strategy rule."""
    return StrategyRule(
        id="strat_001",
        name="LE Breakout 4H/15M",
        source=ContentSource(
            type=SourceType.PDF,
            ref="test.pdf",
            timestamp=None
        ),
        entry_type=EntryType.LE_CANDLE,
        conditions=[],
        confluence_required=[],
        risk_params=RiskParameters(
            risk_percent=2.0,
            tp_levels=[1.5, 2.0],
            sl_distance="swing_low"
        ),
        confidence=0.5,
        description="Test strategy"
    )


@pytest.fixture
def sample_trades():
    """Create sample trade records."""
    trades = []
    
    # 7 winning trades
    for i in range(7):
        trades.append(TradeRecord(
            id=f"trade_win_{i}",
            strategy_rule_id="strat_001",
            asset="BTC-USD",
            direction=OrderSide.BUY,
            entry_price=50000.0,
            entry_time=datetime.utcnow() - timedelta(days=i),
            exit_price=51500.0,
            exit_time=datetime.utcnow() - timedelta(days=i, hours=2),
            outcome=TradeOutcome.WIN,
            pnl_r_multiple=1.5,
            reasoning="Test win"
        ))
    
    # 3 losing trades
    for i in range(3):
        trades.append(TradeRecord(
            id=f"trade_loss_{i}",
            strategy_rule_id="strat_001",
            asset="BTC-USD",
            direction=OrderSide.BUY,
            entry_price=50000.0,
            entry_time=datetime.utcnow() - timedelta(days=i+7),
            exit_price=49500.0,
            exit_time=datetime.utcnow() - timedelta(days=i+7, hours=2),
            outcome=TradeOutcome.LOSS,
            pnl_r_multiple=-1.0,
            reasoning="Test loss"
        ))
    
    return trades


@pytest.fixture
def sample_analysis(sample_strategy):
    """Create a sample strategy analysis."""
    analysis = StrategyAnalysis(
        strategy_rule_id=sample_strategy.id,
        strategy_name=sample_strategy.name,
        total_trades=10,
        win_rate=70.0,
        avg_r_multiple=0.75,
        profit_factor=2.1,
        old_confidence=0.5,
        new_confidence=0.65,
        confidence_change=0.15
    )
    
    # Add success pattern
    analysis.success_patterns.append(
        PatternInsight(
            pattern_type="success_factor",
            description="Strategy performs well in drive market cycle",
            confidence=0.85,
            supporting_trades=["trade_win_0", "trade_win_1"],
            market_conditions={"market_cycle": "drive"},
            impact_score=0.75
        )
    )
    
    # Add failure pattern
    analysis.failure_patterns.append(
        PatternInsight(
            pattern_type="failure_pattern",
            description="Strategy struggles with low confluence (<0.5)",
            confidence=0.75,
            supporting_trades=["trade_loss_0", "trade_loss_1"],
            market_conditions={"max_confluence": 0.5},
            impact_score=0.60
        )
    )
    
    analysis.recommendations = [
        "Excellent win rate - strategy is well-calibrated",
        "Strategy performs best in drive market cycle"
    ]
    
    return analysis


class TestFeedbackLoop:
    """Test FeedbackLoop class."""
    
    def test_initialization(self):
        """Test feedback loop initialization."""
        loop = FeedbackLoop(
            session=Mock(),
            min_trades_for_update=10,
            confidence_update_threshold=0.05
        )
        
        assert loop.min_trades_for_update == 10
        assert loop.confidence_update_threshold == 0.05
        assert loop.outcome_analyzer is not None
    
    def test_learning_context_creation(self):
        """Test learning context creation."""
        context = LearningContext(
            strategy_rule_id="strat_001",
            success_factors=["Works well in trending markets"],
            failure_patterns=["Fails in choppy conditions"],
            recommended_conditions={"market_cycle": "drive"},
            avoid_conditions={"market_cycle": "range"},
            confidence_adjustment=0.1
        )
        
        assert len(context.success_factors) == 1
        assert len(context.failure_patterns) == 1
        assert context.confidence_adjustment == 0.1
        
        # Test prompt text generation
        prompt = context.to_prompt_text()
        assert "success factors" in prompt.lower()
        assert "failure patterns" in prompt.lower()
        assert "trending markets" in prompt
    
    def test_learning_context_empty(self):
        """Test learning context with no learnings."""
        context = LearningContext(strategy_rule_id="strat_001")
        
        prompt = context.to_prompt_text()
        assert "no specific learnings" in prompt.lower()
    
    def test_should_update_confidence(self):
        """Test confidence update decision logic."""
        loop = FeedbackLoop(
            session=Mock(),
            min_trades_for_update=10,
            confidence_update_threshold=0.05
        )
        
        # Should update: sufficient trades and change
        analysis = Mock(
            total_trades=15,
            confidence_change=0.10
        )
        assert loop._should_update_confidence(analysis, force=False)
        
        # Should not update: insufficient trades
        analysis = Mock(
            total_trades=5,
            confidence_change=0.10
        )
        assert not loop._should_update_confidence(analysis, force=False)
        
        # Should not update: insufficient change
        analysis = Mock(
            total_trades=15,
            confidence_change=0.02
        )
        assert not loop._should_update_confidence(analysis, force=False)
        
        # Should update: force flag
        analysis = Mock(
            total_trades=5,
            confidence_change=0.02
        )
        assert loop._should_update_confidence(analysis, force=True)
    
    def test_determine_trend(self):
        """Test trend determination."""
        loop = FeedbackLoop(session=Mock())
        
        assert loop._determine_trend(0.10) == "improving"
        assert loop._determine_trend(-0.10) == "declining"
        assert loop._determine_trend(0.01) == "stable"
    
    def test_ab_variant_creation(self):
        """Test A/B test variant creation."""
        loop = FeedbackLoop(session=Mock())
        
        variant = loop.create_ab_variant(
            base_strategy_id="strat_001",
            variant_name="Higher Confluence",
            modifications={"min_confluence": 0.7}
        )
        
        assert variant.base_strategy_id == "strat_001"
        assert variant.variant_name == "Higher Confluence"
        assert variant.modifications["min_confluence"] == 0.7
        assert variant.is_active
        
        # Create another variant
        variant2 = loop.create_ab_variant(
            base_strategy_id="strat_001",
            variant_name="Stricter Entry",
            modifications={"min_pattern_score": 0.8}
        )
        
        assert len(loop._ab_variants["strat_001"]) == 2
    
    def test_ab_variant_stats_update(self):
        """Test A/B variant statistics update."""
        loop = FeedbackLoop(session=Mock())
        
        variant = loop.create_ab_variant(
            base_strategy_id="strat_001",
            variant_name="Test Variant",
            modifications={}
        )
        
        loop.update_ab_variant_stats(
            variant_id=variant.variant_id,
            trade_count=30,
            win_rate=0.65,
            avg_r_multiple=1.2
        )
        
        updated = loop._ab_variants["strat_001"][0]
        assert updated.trade_count == 30
        assert updated.win_rate == 0.65
        assert updated.avg_r_multiple == 1.2
        assert updated.confidence > 0  # Should be calculated
    
    def test_select_best_variant(self):
        """Test selecting best A/B variant."""
        loop = FeedbackLoop(session=Mock(), min_trades_for_update=10)
        
        # Create variants
        variant1 = loop.create_ab_variant(
            base_strategy_id="strat_001",
            variant_name="Variant A",
            modifications={}
        )
        
        variant2 = loop.create_ab_variant(
            base_strategy_id="strat_001",
            variant_name="Variant B",
            modifications={}
        )
        
        # Update stats (variant B performs better)
        loop.update_ab_variant_stats(
            variant_id=variant1.variant_id,
            trade_count=30,
            win_rate=0.55,
            avg_r_multiple=0.8
        )
        
        loop.update_ab_variant_stats(
            variant_id=variant2.variant_id,
            trade_count=30,
            win_rate=0.70,
            avg_r_multiple=1.5
        )
        
        # Select best
        best = loop.select_best_variant("strat_001", min_trades=30)
        
        assert best is not None
        assert best.variant_name == "Variant B"
        assert best.win_rate == 0.70
    
    def test_select_best_variant_insufficient_data(self):
        """Test selecting best variant with insufficient data."""
        loop = FeedbackLoop(session=Mock())
        
        variant = loop.create_ab_variant(
            base_strategy_id="strat_001",
            variant_name="Variant A",
            modifications={}
        )
        
        # Only 5 trades
        loop.update_ab_variant_stats(
            variant_id=variant.variant_id,
            trade_count=5,
            win_rate=0.80,
            avg_r_multiple=2.0
        )
        
        # Should return None (need 30 trades)
        best = loop.select_best_variant("strat_001", min_trades=30)
        assert best is None


class TestImprovementMetrics:
    """Test ImprovementMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating improvement metrics."""
        metrics = ImprovementMetrics(
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 2, 1),
            total_strategies=10,
            strategies_improved=7,
            strategies_declined=2,
            avg_confidence_change=0.08,
            total_insights_generated=25,
            high_confidence_insights=15,
            overall_win_rate=0.58,
            overall_profit_factor=1.85,
            overall_avg_r=0.95,
            win_rate_trend="improving",
            confidence_trend="improving"
        )
        
        assert metrics.total_strategies == 10
        assert metrics.strategies_improved == 7
        assert metrics.win_rate_trend == "improving"
        
        # Test string representation
        metrics_str = str(metrics)
        assert "10" in metrics_str  # total strategies
        assert "7 improved" in metrics_str
        assert "improving" in metrics_str.lower()


class TestABTestVariant:
    """Test ABTestVariant dataclass."""
    
    def test_variant_creation(self):
        """Test creating A/B test variant."""
        variant = ABTestVariant(
            variant_id="strat_001_variant_1",
            base_strategy_id="strat_001",
            variant_name="Higher Confluence",
            modifications={"min_confluence": 0.7}
        )
        
        assert variant.variant_id == "strat_001_variant_1"
        assert variant.is_active
        assert variant.trade_count == 0
        assert variant.confidence == 0.5
        assert "min_confluence" in variant.modifications


class TestConvenienceFunction:
    """Test convenience function."""
    
    @patch('src.learning.feedback_loop.FeedbackLoop')
    def test_run_feedback_cycle(self, mock_feedback_loop_class):
        """Test run_feedback_cycle convenience function."""
        # Setup mock
        mock_instance = Mock()
        mock_feedback_loop_class.return_value.__enter__ = Mock(return_value=mock_instance)
        mock_feedback_loop_class.return_value.__exit__ = Mock(return_value=False)
        
        mock_instance.run_feedback_cycle.return_value = []
        
        # Call convenience function
        result = run_feedback_cycle(
            strategy_ids=["strat_001"],
            force_update=True
        )
        
        # Verify
        assert result == []
        mock_instance.run_feedback_cycle.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
