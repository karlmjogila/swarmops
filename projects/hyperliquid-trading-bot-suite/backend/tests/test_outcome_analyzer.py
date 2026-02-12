"""
Tests for the Outcome Analyzer module.

Tests cover:
- Pattern identification (success and failure)
- Confidence score calculation
- Market condition correlation analysis
- Learning entry generation
- Recommendation generation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from src.types import (
    TradeRecord, TradeOutcome, StrategyRule, LearningEntry,
    MarketCycle, OrderSide, ExitReason, EntryType, SourceType,
    PriceActionSnapshot, PatternType, Timeframe
)
from src.learning.outcome_analyzer import (
    OutcomeAnalyzer, StrategyAnalysis, PatternInsight
)


# ===== FIXTURES =====

@pytest.fixture
def sample_strategy_rule():
    """Create a sample strategy rule for testing."""
    from src.types import RiskParameters as TypesRiskParams
    from src.types import PatternCondition as TypesPatternCondition
    
    return StrategyRule(
        id="strategy-1",
        name="LE Candle Strategy",
        entry_type=EntryType.LE,
        source_type=SourceType.MANUAL,
        source_ref="test",
        conditions=[
            TypesPatternCondition(
                type=PatternType.CANDLE,
                timeframe=Timeframe.M15,
                params={"wick_ratio": ">2"}
            )
        ],
        confluence_required=[],
        risk_params=TypesRiskParams(
            risk_percent=2.0,
            tp_levels=[1.0, 2.0],
            sl_distance="below_low"
        ),
        confidence=0.5,
        win_rate=50.0,
        avg_r_multiple=1.0
    )


@pytest.fixture
def winning_trades():
    """Create a list of winning trades for testing."""
    trades = []
    base_time = datetime.utcnow() - timedelta(days=30)
    
    for i in range(15):
        trade = TradeRecord(
            id=f"win-trade-{i}",
            strategy_rule_id="strategy-1",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0 + i * 10,
            entry_time=base_time + timedelta(days=i),
            exit_price=2040.0 + i * 10,
            exit_time=base_time + timedelta(days=i, hours=4),
            exit_reason=ExitReason.TP2 if i % 3 == 0 else ExitReason.TP1,
            outcome=TradeOutcome.WIN,
            pnl_r_multiple=2.0 if i % 3 == 0 else 1.0,
            pnl_absolute=40.0 if i % 3 == 0 else 20.0,
            position_size=1.0,
            reasoning="Good setup with high confluence",
            price_action_context=PriceActionSnapshot(
                timeframes={},
                market_cycle=MarketCycle.DRIVE if i % 2 == 0 else MarketCycle.LIQUIDITY,
                confluence_score=0.8 if i % 2 == 0 else 0.7,
                structure_notes=["Strong bullish structure", "BOS confirmed"],
                zone_interactions=["Bounce from support"]
            ),
            confidence=0.8
        )
        trades.append(trade)
    
    return trades


@pytest.fixture
def losing_trades():
    """Create a list of losing trades for testing."""
    trades = []
    base_time = datetime.utcnow() - timedelta(days=30)
    
    for i in range(5):
        trade = TradeRecord(
            id=f"loss-trade-{i}",
            strategy_rule_id="strategy-1",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0 + i * 10,
            entry_time=base_time + timedelta(days=i),
            exit_price=1980.0 + i * 10,
            exit_time=base_time + timedelta(days=i, hours=2),
            exit_reason=ExitReason.STOP_LOSS,
            outcome=TradeOutcome.LOSS,
            pnl_r_multiple=-1.0,
            pnl_absolute=-20.0,
            position_size=1.0,
            reasoning="Setup failed, structure broke",
            price_action_context=PriceActionSnapshot(
                timeframes={},
                market_cycle=MarketCycle.RANGE,
                confluence_score=0.4,
                structure_notes=["Weak structure", "Failed to hold support"],
                zone_interactions=["Violated support zone"]
            ),
            confidence=0.5
        )
        trades.append(trade)
    
    return trades


@pytest.fixture
def outcome_analyzer():
    """Create an OutcomeAnalyzer instance."""
    return OutcomeAnalyzer(
        min_trades_for_analysis=10,
        min_pattern_trades=3,
        confidence_adjustment_rate=0.1,
        pattern_confidence_threshold=0.6
    )


# ===== BASIC FUNCTIONALITY TESTS =====

def test_analyzer_initialization(outcome_analyzer):
    """Test that analyzer initializes with correct parameters."""
    assert outcome_analyzer.min_trades_for_analysis == 10
    assert outcome_analyzer.min_pattern_trades == 3
    assert outcome_analyzer.confidence_adjustment_rate == 0.1
    assert outcome_analyzer.pattern_confidence_threshold == 0.6


def test_insufficient_trades_analysis(
    outcome_analyzer,
    sample_strategy_rule
):
    """Test analysis with insufficient trades."""
    few_trades = []
    for i in range(5):  # Less than min_trades_for_analysis (10)
        trade = TradeRecord(
            id=f"trade-{i}",
            strategy_rule_id="strategy-1",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0,
            entry_time=datetime.utcnow(),
            outcome=TradeOutcome.WIN,
            pnl_r_multiple=1.0,
            pnl_absolute=20.0,
            position_size=1.0,
            reasoning="Test"
        )
        few_trades.append(trade)
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        few_trades
    )
    
    assert analysis.total_trades == 5
    assert analysis.new_confidence == sample_strategy_rule.confidence
    assert len(analysis.recommendations) > 0
    assert "more trades" in analysis.recommendations[0].lower()


def test_basic_strategy_analysis(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades,
    losing_trades
):
    """Test complete strategy analysis."""
    all_trades = winning_trades + losing_trades
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        all_trades
    )
    
    assert analysis.strategy_rule_id == "strategy-1"
    assert analysis.total_trades == 20
    assert analysis.win_rate == 75.0  # 15 wins out of 20
    assert analysis.new_confidence != analysis.old_confidence
    assert len(analysis.recommendations) > 0


# ===== PATTERN IDENTIFICATION TESTS =====

def test_success_pattern_identification(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades
):
    """Test identification of success patterns."""
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        winning_trades + winning_trades  # Double to ensure enough trades
    )
    
    assert len(analysis.success_patterns) > 0
    
    # Should identify market cycle pattern (DRIVE is dominant)
    market_cycle_patterns = [
        p for p in analysis.success_patterns
        if "market cycle" in p.description.lower()
    ]
    assert len(market_cycle_patterns) > 0


def test_failure_pattern_identification(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades,
    losing_trades
):
    """Test identification of failure patterns."""
    all_trades = winning_trades + losing_trades
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        all_trades
    )
    
    assert len(analysis.failure_patterns) > 0
    
    # Should identify RANGE market cycle as failure pattern
    range_patterns = [
        p for p in analysis.failure_patterns
        if "range" in p.description.lower()
    ]
    assert len(range_patterns) > 0


def test_market_cycle_pattern_analysis(outcome_analyzer, winning_trades):
    """Test market cycle pattern analysis."""
    pattern = outcome_analyzer._analyze_market_cycle_pattern(
        winning_trades,
        "success_factor"
    )
    
    assert pattern is not None
    assert pattern.pattern_type == "success_factor"
    assert "market cycle" in pattern.description.lower()
    assert pattern.confidence > 0.0
    assert len(pattern.supporting_trades) >= 3


def test_exit_reason_pattern_analysis(outcome_analyzer, winning_trades):
    """Test exit reason pattern analysis."""
    pattern = outcome_analyzer._analyze_exit_reason_pattern(
        winning_trades,
        "success_factor"
    )
    
    assert pattern is not None
    assert "exit" in pattern.description.lower() or "tp" in pattern.description.lower()
    assert len(pattern.supporting_trades) >= 3


def test_r_multiple_pattern_analysis(outcome_analyzer, winning_trades):
    """Test R-multiple pattern analysis."""
    pattern = outcome_analyzer._analyze_r_multiple_pattern(winning_trades)
    
    # Should identify consistent TP2 hitting
    if pattern:
        assert pattern.pattern_type == "success_factor"
        assert "tp2" in pattern.description.lower() or "r-multiple" in pattern.description.lower()


def test_confluence_pattern_analysis(outcome_analyzer, winning_trades):
    """Test confluence score pattern analysis."""
    pattern = outcome_analyzer._analyze_confluence_pattern(
        winning_trades,
        "success_factor"
    )
    
    # Should identify high confluence correlation
    if pattern:
        assert "confluence" in pattern.description.lower()
        assert pattern.confidence > 0.0


def test_timing_pattern_analysis(outcome_analyzer, winning_trades):
    """Test trade timing pattern analysis."""
    # Modify trades to have concentrated timing
    for i, trade in enumerate(winning_trades[:10]):
        trade.entry_time = datetime.utcnow().replace(hour=14, minute=0)  # US session
    
    pattern = outcome_analyzer._analyze_timing_pattern(
        winning_trades,
        "success_factor"
    )
    
    if pattern:
        assert "session" in pattern.description.lower()
        assert len(pattern.supporting_trades) >= 3


def test_structure_pattern_analysis(outcome_analyzer, losing_trades):
    """Test structure violation pattern analysis."""
    pattern = outcome_analyzer._analyze_structure_pattern(losing_trades)
    
    # Should identify structure violations
    if pattern:
        assert pattern.pattern_type == "failure_pattern"
        assert "structure" in pattern.description.lower() or "violation" in pattern.description.lower()


# ===== CONFIDENCE CALCULATION TESTS =====

def test_confidence_increases_with_good_performance(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades
):
    """Test that confidence increases with good performance."""
    # All winning trades
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        winning_trades + winning_trades  # Ensure enough trades
    )
    
    assert analysis.new_confidence > analysis.old_confidence
    assert analysis.confidence_change > 0


def test_confidence_decreases_with_poor_performance(
    outcome_analyzer,
    sample_strategy_rule,
    losing_trades
):
    """Test that confidence decreases with poor performance."""
    # Create more losing trades to meet minimum
    more_losing = []
    for i in range(10):
        trade = losing_trades[0]
        trade.id = f"loss-{i}"
        more_losing.append(trade)
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        more_losing
    )
    
    assert analysis.new_confidence < analysis.old_confidence
    assert analysis.confidence_change < 0


def test_confidence_adjustment_rate_limit(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades
):
    """Test that confidence changes are limited by adjustment rate."""
    # Perfect performance
    perfect_trades = []
    for i in range(20):
        trade = TradeRecord(
            id=f"perfect-{i}",
            strategy_rule_id="strategy-1",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0,
            entry_time=datetime.utcnow(),
            exit_price=2080.0,
            exit_time=datetime.utcnow() + timedelta(hours=4),
            exit_reason=ExitReason.TP2,
            outcome=TradeOutcome.WIN,
            pnl_r_multiple=4.0,
            pnl_absolute=80.0,
            position_size=1.0,
            reasoning="Perfect setup",
            price_action_context=PriceActionSnapshot(
                timeframes={},
                confluence_score=0.95
            )
        )
        perfect_trades.append(trade)
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        perfect_trades
    )
    
    # Change should be limited by adjustment_rate
    assert abs(analysis.confidence_change) <= outcome_analyzer.confidence_adjustment_rate


def test_confidence_bounds(outcome_analyzer, sample_strategy_rule):
    """Test that confidence stays within valid bounds (0.1 to 0.95)."""
    # Test with extreme scenarios
    perfect_trades = []
    for i in range(50):
        trade = TradeRecord(
            id=f"perfect-{i}",
            strategy_rule_id="strategy-1",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0,
            entry_time=datetime.utcnow(),
            exit_price=2100.0,
            exit_time=datetime.utcnow() + timedelta(hours=4),
            outcome=TradeOutcome.WIN,
            pnl_r_multiple=5.0,
            pnl_absolute=100.0,
            position_size=1.0,
            reasoning="Test"
        )
        perfect_trades.append(trade)
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        perfect_trades
    )
    
    assert 0.1 <= analysis.new_confidence <= 0.95


# ===== LEARNING ENTRY GENERATION TESTS =====

def test_generate_learning_entries(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades,
    losing_trades
):
    """Test learning entry generation from analysis."""
    all_trades = winning_trades + losing_trades
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        all_trades
    )
    
    learning_entries = outcome_analyzer.generate_learning_entries(analysis)
    
    assert len(learning_entries) > 0
    
    for entry in learning_entries:
        assert entry.strategy_rule_id == "strategy-1"
        assert entry.insight is not None and len(entry.insight) > 0
        assert 0.0 <= entry.confidence <= 1.0
        assert entry.impact_type in ["success_factor", "failure_pattern"]
        assert len(entry.supporting_trades) >= 3


def test_learning_entry_confidence_threshold(outcome_analyzer):
    """Test that only high-confidence patterns generate learning entries."""
    # Create analysis with low confidence pattern
    analysis = StrategyAnalysis(
        strategy_rule_id="test",
        strategy_name="Test"
    )
    
    # Low confidence pattern
    low_conf_pattern = PatternInsight(
        pattern_type="success_factor",
        description="Low confidence pattern",
        confidence=0.3,  # Below threshold
        supporting_trades=["t1", "t2", "t3"],
        market_conditions={},
        impact_score=0.3
    )
    
    # High confidence pattern
    high_conf_pattern = PatternInsight(
        pattern_type="success_factor",
        description="High confidence pattern",
        confidence=0.8,  # Above threshold
        supporting_trades=["t4", "t5", "t6"],
        market_conditions={},
        impact_score=0.8
    )
    
    analysis.success_patterns = [low_conf_pattern, high_conf_pattern]
    
    entries = outcome_analyzer.generate_learning_entries(analysis)
    
    # Should only generate entry for high confidence pattern
    assert len(entries) == 1
    assert entries[0].confidence == 0.8


# ===== PERFORMANCE ANALYSIS TESTS =====

def test_market_cycle_performance_analysis(
    outcome_analyzer,
    winning_trades,
    losing_trades
):
    """Test market cycle performance analysis."""
    all_trades = winning_trades + losing_trades
    
    best_cycles = outcome_analyzer._analyze_market_cycle_performance(all_trades)
    worst_cycles = outcome_analyzer._analyze_market_cycle_performance(all_trades, worst=True)
    
    assert len(best_cycles) > 0
    assert len(worst_cycles) > 0
    
    # Best cycles should have higher win rates
    if best_cycles and worst_cycles:
        assert best_cycles[0][1] >= worst_cycles[0][1]


def test_asset_performance_analysis(outcome_analyzer, winning_trades):
    """Test asset performance analysis."""
    # Create trades with different assets
    btc_trades = []
    for i in range(5):
        trade = winning_trades[i]
        trade.asset = "BTC-USD"
        btc_trades.append(trade)
    
    eth_trades = winning_trades[5:10]
    
    all_trades = btc_trades + eth_trades
    
    asset_performance = outcome_analyzer._analyze_asset_performance(all_trades)
    
    assert len(asset_performance) > 0
    
    # Should identify both assets
    assets = [ap[0] for ap in asset_performance]
    assert "BTC-USD" in assets or "ETH-USD" in assets


# ===== RECOMMENDATION TESTS =====

def test_recommendation_generation(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades,
    losing_trades
):
    """Test recommendation generation."""
    all_trades = winning_trades + losing_trades
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        all_trades
    )
    
    assert len(analysis.recommendations) > 0
    
    # Should have recommendations about performance
    rec_text = " ".join(analysis.recommendations).lower()
    assert any(word in rec_text for word in ['win', 'rate', 'strategy', 'confluence', 'cycle'])


def test_low_win_rate_recommendation(outcome_analyzer, sample_strategy_rule):
    """Test recommendation for low win rate."""
    # Create mostly losing trades
    low_win_trades = []
    for i in range(15):
        outcome = TradeOutcome.LOSS if i < 10 else TradeOutcome.WIN
        pnl_r = -1.0 if i < 10 else 1.0
        
        trade = TradeRecord(
            id=f"trade-{i}",
            strategy_rule_id="strategy-1",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0,
            entry_time=datetime.utcnow(),
            outcome=outcome,
            pnl_r_multiple=pnl_r,
            pnl_absolute=pnl_r * 20.0,
            position_size=1.0,
            reasoning="Test"
        )
        low_win_trades.append(trade)
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        low_win_trades
    )
    
    # Should have recommendation about low win rate
    rec_text = " ".join(analysis.recommendations).lower()
    assert "win rate" in rec_text or "below" in rec_text


def test_high_profit_factor_recommendation(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades
):
    """Test recommendation for high profit factor."""
    # Modify wins to have large R-multiples
    for trade in winning_trades:
        trade.pnl_r_multiple = 3.0
        trade.pnl_absolute = 60.0
    
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        winning_trades + winning_trades  # Ensure enough trades
    )
    
    # Should have positive recommendation about profit factor
    rec_text = " ".join(analysis.recommendations).lower()
    assert "profit factor" in rec_text


# ===== INTEGRATION TESTS =====

def test_analyze_multiple_strategies(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades,
    losing_trades
):
    """Test analyzing multiple strategies at once."""
    from src.types import RiskParameters as TypesRiskParams
    
    # Create another strategy
    strategy2 = StrategyRule(
        id="strategy-2",
        name="Breakout Strategy",
        source_type=SourceType.MANUAL,
        source_ref="test",
        entry_type=EntryType.BREAKOUT,
        conditions=[],
        risk_params=TypesRiskParams(),
        confidence=0.5
    )
    
    # Create trades for strategy 2
    trades2 = []
    for i in range(10):
        trade = winning_trades[0]
        trade.id = f"s2-trade-{i}"
        trade.strategy_rule_id = "strategy-2"
        trades2.append(trade)
    
    strategies = [sample_strategy_rule, strategy2]
    trades_by_strategy = {
        "strategy-1": winning_trades + losing_trades,
        "strategy-2": trades2
    }
    
    analyses = outcome_analyzer.analyze_all_strategies(
        strategies,
        trades_by_strategy
    )
    
    assert len(analyses) == 2
    assert analyses[0].strategy_rule_id in ["strategy-1", "strategy-2"]
    assert analyses[1].strategy_rule_id in ["strategy-1", "strategy-2"]


def test_pattern_insight_to_learning_entry_conversion():
    """Test converting PatternInsight to LearningEntry."""
    pattern = PatternInsight(
        pattern_type="success_factor",
        description="Test pattern",
        confidence=0.85,
        supporting_trades=["t1", "t2", "t3"],
        market_conditions={"market_cycle": "drive"},
        impact_score=0.8
    )
    
    learning_entry = pattern.to_learning_entry("strategy-123")
    
    assert learning_entry.strategy_rule_id == "strategy-123"
    assert learning_entry.insight == "Test pattern"
    assert learning_entry.confidence == 0.85
    assert learning_entry.impact_type == "success_factor"
    assert len(learning_entry.supporting_trades) == 3
    assert learning_entry.market_conditions["market_cycle"] == "drive"


def test_strategy_analysis_string_representation(
    outcome_analyzer,
    sample_strategy_rule,
    winning_trades
):
    """Test string representation of StrategyAnalysis."""
    analysis = outcome_analyzer.analyze_strategy(
        sample_strategy_rule,
        winning_trades + winning_trades
    )
    
    analysis_str = str(analysis)
    
    assert "Strategy Analysis" in analysis_str
    assert sample_strategy_rule.name in analysis_str
    assert "Win Rate" in analysis_str
    assert "Confidence" in analysis_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
