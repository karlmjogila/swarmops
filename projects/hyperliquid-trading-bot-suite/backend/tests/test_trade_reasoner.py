"""
Tests for Trade Reasoner

Tests both LLM-based and rule-based reasoning modes.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os

from src.trading.trade_reasoner import TradeReasoner, TradeReasoning
from src.detection.confluence_scorer import ConfluenceScore, TimeframeContext
from src.types import (
    OrderSide, Timeframe, EntryType, MarketCycle, PatternType, TradeOutcome
)
from src.knowledge.models import StrategyRule, RiskParameters, ContentSource, SourceType


@pytest.fixture
def mock_strategy_rule():
    """Create a mock strategy rule."""
    return StrategyRule(
        id="test-strategy-1",
        name="Test LE Strategy",
        source=ContentSource(
            type=SourceType.MANUAL,
            ref="test",
            timestamp=None
        ),
        entry_type=EntryType.LE,
        conditions=[],
        confluence_required=[],
        risk_params=RiskParameters(
            risk_percent=2.0,
            tp_levels=[1.5, 2.5, 3.5],
            sl_distance="structure",
            max_concurrent_positions=3,
            daily_loss_limit_percent=6.0
        ),
        confidence=0.75,
        description="Test strategy",
        enabled=True,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_confluence_score():
    """Create a mock confluence score."""
    return ConfluenceScore(
        total_score=0.78,
        confidence=0.72,
        signal_quality="strong",
        pattern_score=0.85,
        structure_score=0.75,
        cycle_score=0.70,
        timeframe_alignment_score=0.80,
        zone_score=0.80,
        generates_signal=True,
        entry_bias=OrderSide.LONG,
        entry_timeframe=Timeframe.M15,
        entry_patterns=[],
        htf_bias=OrderSide.LONG,
        htf_timeframe=Timeframe.H4,
        htf_trend_strength=0.73,
        alignment_details={},
        warnings=[],
        confluence_factors=[
            "Higher timeframe bullish bias",
            "Strong entry pattern detected",
            "Price at support zone"
        ],
        timestamp=datetime.utcnow(),
        asset="BTC",
        timeframes_analyzed=[Timeframe.H4, Timeframe.M15]
    )


@pytest.fixture
def mock_timeframe_contexts():
    """Create mock timeframe contexts."""
    from src.types import CandleData
    
    # Create mock candle data
    now = datetime.utcnow()
    candles = []
    for i in range(20):
        candles.append(CandleData(
            timestamp=now - timedelta(minutes=15 * (20 - i)),
            open=50000 + i * 10,
            high=50100 + i * 10,
            low=49900 + i * 10,
            close=50050 + i * 10,
            volume=1000,
            timeframe=Timeframe.M15
        ))
    
    return {
        Timeframe.H4: TimeframeContext(
            timeframe=Timeframe.H4,
            candles=candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.73,
            market_cycle=MarketCycle.DRIVE,
            cycle_confidence=0.80,
            in_support_zone=False,
            in_resistance_zone=False,
            near_structure_break=False,
            zone_strength=0.0
        ),
        Timeframe.M15: TimeframeContext(
            timeframe=Timeframe.M15,
            candles=candles,
            patterns=[],
            trend_direction=OrderSide.LONG,
            trend_strength=0.65,
            market_cycle=MarketCycle.DRIVE,
            cycle_confidence=0.70,
            in_support_zone=True,
            in_resistance_zone=False,
            near_structure_break=False,
            zone_strength=0.75
        )
    }


@pytest.fixture
def mock_strategy_repository(mock_strategy_rule):
    """Create a mock strategy repository."""
    repo = Mock()
    repo.get_all.return_value = [mock_strategy_rule]
    return repo


class TestTradeReasonerRuleBased:
    """Test trade reasoner in rule-based mode (no LLM)."""
    
    def test_initialization_without_llm(self):
        """Test initializing reasoner without LLM."""
        reasoner = TradeReasoner(use_llm=False)
        assert reasoner.use_llm is False
        assert reasoner.min_confidence_for_entry == 0.55
        assert reasoner.min_confluence_score == 0.50
    
    def test_analyze_setup_good_confluence(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test analyzing a good setup with high confluence."""
        reasoner = TradeReasoner(use_llm=False)
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Should recommend entry
        assert reasoning.should_enter is True
        assert reasoning.confidence > 0.6
        assert reasoning.entry_bias == OrderSide.LONG
        assert reasoning.matched_strategy_id == "test-strategy-1"
        assert "BTC" in reasoning.explanation
        assert len(reasoning.suggested_targets) > 0
        assert reasoning.suggested_stop_loss is not None
    
    def test_analyze_setup_low_confluence(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test analyzing a setup with low confluence."""
        reasoner = TradeReasoner(use_llm=False)
        
        # Lower the confluence score
        mock_confluence_score.total_score = 0.35
        mock_confluence_score.generates_signal = False
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Should reject entry
        assert reasoning.should_enter is False
        assert "below minimum threshold" in reasoning.explanation.lower()
    
    def test_analyze_setup_no_matching_strategy(
        self,
        mock_confluence_score,
        mock_timeframe_contexts
    ):
        """Test analyzing a setup with no matching strategy."""
        reasoner = TradeReasoner(use_llm=False)
        
        # Empty repository
        empty_repo = Mock()
        empty_repo.get_all.return_value = []
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=empty_repo,
            current_price=50000.0
        )
        
        # Should reject entry
        assert reasoning.should_enter is False
        assert "no matching strategy" in reasoning.explanation.lower()
    
    def test_risk_level_calculation_long(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test risk level calculation for long trade."""
        reasoner = TradeReasoner(use_llm=False)
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Check stop loss is below entry
        assert reasoning.suggested_stop_loss < 50000.0
        
        # Check targets are above entry
        for target in reasoning.suggested_targets:
            assert target > 50000.0
        
        # Check R:R ratio is positive
        assert reasoning.risk_reward_ratio > 1.0
    
    def test_risk_level_calculation_short(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test risk level calculation for short trade."""
        reasoner = TradeReasoner(use_llm=False)
        
        # Change to short bias
        mock_confluence_score.entry_bias = OrderSide.SHORT
        mock_confluence_score.htf_bias = OrderSide.SHORT
        mock_timeframe_contexts[Timeframe.H4].trend_direction = OrderSide.SHORT
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Check stop loss is above entry
        assert reasoning.suggested_stop_loss > 50000.0
        
        # Check targets are below entry
        for target in reasoning.suggested_targets:
            assert target < 50000.0
    
    def test_create_trade_record(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test creating a trade record from reasoning."""
        reasoner = TradeReasoner(use_llm=False)
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        trade = reasoner.create_trade_record(
            reasoning=reasoning,
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            entry_price=50000.0,
            quantity=0.1
        )
        
        # Verify trade record
        assert trade.asset == "BTC"
        assert trade.direction == OrderSide.LONG
        assert trade.entry_price == 50000.0
        assert trade.quantity == 0.1
        assert trade.strategy_rule_id == "test-strategy-1"
        assert trade.outcome == TradeOutcome.PENDING
        assert trade.reasoning == reasoning.explanation
        assert trade.price_action_context is not None
        assert len(trade.take_profit_levels) > 0


class TestTradeReasonerLLM:
    """Test trade reasoner with LLM mode (mocked)."""
    
    @pytest.mark.skipif(
        os.getenv("ANTHROPIC_API_KEY") is None,
        reason="No Anthropic API key available"
    )
    def test_initialization_with_llm(self):
        """Test initializing reasoner with LLM."""
        reasoner = TradeReasoner(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            use_llm=True
        )
        assert reasoner.use_llm is True
        assert reasoner.client is not None
    
    @patch('src.trading.trade_reasoner.Anthropic')
    def test_llm_reasoning_generation(
        self,
        mock_anthropic,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test LLM reasoning generation with mocked API."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="This is a strong long setup on BTC with excellent confluence. "
                          "Key factors: Higher timeframe bullish trend, quality entry pattern, "
                          "and price at support. Main risk: Break below support invalidates. "
                          "Expected behavior: Rally toward targets if structure holds.")
        ]
        
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        reasoner = TradeReasoner(
            anthropic_api_key="test-key",
            use_llm=True
        )
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Verify LLM was called
        assert mock_client.messages.create.called
        
        # Verify reasoning contains LLM response
        assert "strong long setup" in reasoning.explanation.lower() or "btc" in reasoning.explanation.lower()
        assert reasoning.should_enter is True
    
    @patch('src.trading.trade_reasoner.Anthropic')
    def test_llm_fallback_on_error(
        self,
        mock_anthropic,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test fallback to rule-based when LLM fails."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client
        
        reasoner = TradeReasoner(
            anthropic_api_key="test-key",
            use_llm=True
        )
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Should still work with rule-based fallback
        assert reasoning.explanation != ""
        assert reasoning.should_enter is True


class TestTradeReasonerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_missing_timeframe_context(
        self,
        mock_confluence_score,
        mock_strategy_repository
    ):
        """Test handling of missing timeframe contexts."""
        reasoner = TradeReasoner(use_llm=False)
        
        # Empty contexts
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts={},
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Should not crash
        assert reasoning is not None
        # Risk levels may not be calculated
        assert reasoning.suggested_stop_loss is None or reasoning.suggested_stop_loss == 0
    
    def test_confluence_score_warnings(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_repository
    ):
        """Test handling of confluence score warnings."""
        reasoner = TradeReasoner(use_llm=False)
        
        # Add warnings
        mock_confluence_score.warnings = [
            "Weak market structure",
            "Unfavorable cycle phase"
        ]
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=mock_strategy_repository,
            current_price=50000.0
        )
        
        # Confidence should be reduced
        assert reasoning.confidence < 0.75
        # Warnings should be captured
        assert len(reasoning.risks) > 0
    
    def test_disabled_strategy(
        self,
        mock_confluence_score,
        mock_timeframe_contexts,
        mock_strategy_rule
    ):
        """Test handling of disabled strategy."""
        reasoner = TradeReasoner(use_llm=False)
        
        # Disable strategy
        mock_strategy_rule.enabled = False
        
        repo = Mock()
        repo.get_all.return_value = [mock_strategy_rule]
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=mock_confluence_score,
            timeframe_contexts=mock_timeframe_contexts,
            strategy_repository=repo,
            current_price=50000.0
        )
        
        # Should not enter disabled strategy
        assert reasoning.should_enter is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
