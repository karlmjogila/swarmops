"""Tests for learning service and feedback loop."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

from hl_bot.services.learning_service import LearningService
from hl_bot.services.trade_reasoner import LearningInsight, OutcomeAnalysis, RiskAssessment
from hl_bot.types import Candle, SignalType, Timeframe, Trade, TradeStatus


@pytest.fixture
def mock_learning_repo():
    """Mock learning repository."""
    repo = Mock()
    
    # Mock get_strategy_performance
    repo.get_strategy_performance.return_value = {
        'strategy_id': uuid4(),
        'strategy_name': 'Test Strategy',
        'effectiveness_score': 0.65,
        'total_trades': 10,
        'winning_trades': 6,
        'win_rate': 0.6,
        'avg_pnl': 50.0,
        'total_pnl': 500.0,
    }
    
    # Mock update_strategy_effectiveness
    repo.update_strategy_effectiveness.return_value = Mock()
    
    # Mock create_learning_entry
    repo.create_learning_entry.return_value = Mock(id=uuid4())
    
    # Mock get_learning_entries
    repo.get_learning_entries.return_value = []
    
    # Mock get_trade_summaries_for_learning
    repo.get_trade_summaries_for_learning.return_value = []
    
    return repo


@pytest.fixture
def mock_trade_reasoner():
    """Mock trade reasoner."""
    reasoner = Mock()
    
    # Mock review_outcome
    async def mock_review_outcome(*args, **kwargs):
        return OutcomeAnalysis(
            what_happened="Trade hit TP1 after brief pullback from resistance zone. Price action was clean.",
            what_worked=["Entry timing was good", "Risk management worked"],
            what_didnt_work=["Could have held longer"],
            lessons_learned=["TP1 at 1R is solid in ranging markets"],
            setup_validity="valid",
            performance_rating=4,
        )
    
    reasoner.review_outcome = AsyncMock(side_effect=mock_review_outcome)
    
    # Mock aggregate_learnings
    async def mock_aggregate_learnings(*args, **kwargs):
        return [
            LearningInsight(
                insight_type="pattern",
                insight="LE candle setups at support have 65% win rate",
                confidence_score=0.75,
                sample_size=10,
                market_conditions={'market_phase': 'range'},
            ),
            LearningInsight(
                insight_type="setup",
                insight="Breakout setups work better in drive phase",
                confidence_score=0.80,
                sample_size=8,
                market_conditions={'market_phase': 'drive'},
            ),
        ]
    
    reasoner.aggregate_learnings = AsyncMock(side_effect=mock_aggregate_learnings)
    
    return reasoner


@pytest.fixture
def learning_service(mock_learning_repo, mock_trade_reasoner):
    """Learning service with mocked dependencies."""
    return LearningService(
        learning_repo=mock_learning_repo,
        trade_reasoner=mock_trade_reasoner,
    )


@pytest.fixture
def sample_trade():
    """Sample completed trade (using Mock for flexibility)."""
    trade_id = str(uuid4())
    signal_id = str(uuid4())
    strategy_id = uuid4()
    
    # Use Mock to simulate a Trade object with all needed attributes
    trade = Mock()
    trade.id = trade_id
    trade.signal_id = signal_id
    trade.strategy_id = strategy_id
    trade.symbol = "BTC-USD"
    trade.side = SignalType.LONG
    trade.status = TradeStatus.CLOSED
    trade.entry_price = 50000.0
    trade.entry_time = datetime(2025, 2, 11, 10, 0, tzinfo=timezone.utc)
    trade.position_size = 0.1
    trade.stop_loss = 49500.0
    trade.take_profits = [50500.0, 51000.0]
    trade.exit_price = 50500.0
    trade.exit_time = datetime(2025, 2, 11, 12, 0, tzinfo=timezone.utc)
    trade.pnl = 50.0
    trade.pnl_percent = 1.0
    trade.reasoning = "Strong support level with LE candle pattern"
    trade.post_analysis = None
    trade.max_adverse_excursion = -20.0
    trade.max_favorable_excursion = 60.0
    trade.confluence_score = 75.0
    trade.patterns_detected = ['le_candle', 'support']
    trade.setup_type = 'pullback'
    trade.market_phase = 'range'
    trade.source = 'backtest'
    
    return trade


@pytest.fixture
def sample_candles():
    """Sample candle data."""
    return [
        Candle(
            timestamp=datetime(2025, 2, 11, 10, i, tzinfo=timezone.utc),
            symbol="BTC-USD",
            timeframe=Timeframe.M5,
            open=50000.0 + i * 10,
            high=50020.0 + i * 10,
            low=49980.0 + i * 10,
            close=50010.0 + i * 10,
            volume=1000.0,
        )
        for i in range(10)
    ]


# ============================================================================
# Tests: Post-Trade Analysis
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_trade_outcome_success(
    learning_service,
    mock_trade_reasoner,
    mock_learning_repo,
    sample_trade,
    sample_candles,
):
    """Test successful trade outcome analysis."""
    # Analyze outcome
    outcome = await learning_service.analyze_trade_outcome(
        trade=sample_trade,
        entry_reasoning="Strong support level with LE candle",
        entry_candles=sample_candles[:5],
        trade_candles=sample_candles[5:],
    )
    
    # Verify reasoner was called
    mock_trade_reasoner.review_outcome.assert_called_once()
    
    # Verify outcome returned
    assert outcome.setup_validity == "valid"
    assert outcome.performance_rating == 4
    assert len(outcome.lessons_learned) > 0
    
    # Verify strategy effectiveness was updated
    mock_learning_repo.update_strategy_effectiveness.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_trade_outcome_no_strategy(
    learning_service,
    mock_trade_reasoner,
    mock_learning_repo,
    sample_trade,
    sample_candles,
):
    """Test outcome analysis for trade without strategy."""
    # Remove strategy ID
    sample_trade.strategy_id = None
    
    # Analyze outcome
    outcome = await learning_service.analyze_trade_outcome(
        trade=sample_trade,
        entry_reasoning="Test trade",
        entry_candles=sample_candles[:5],
        trade_candles=sample_candles[5:],
    )
    
    # Verify reasoner was called
    mock_trade_reasoner.review_outcome.assert_called_once()
    
    # Verify strategy effectiveness was NOT updated (no strategy)
    mock_learning_repo.update_strategy_effectiveness.assert_not_called()


@pytest.mark.asyncio
async def test_strategy_effectiveness_update_calculation(
    learning_service,
    mock_learning_repo,
    sample_trade,
):
    """Test strategy effectiveness score calculation."""
    # Mock outcome
    outcome = OutcomeAnalysis(
        what_happened="Trade stopped out due to brief volatility spike before reversing in our direction.",
        what_worked=["Entry was good"],
        what_didnt_work=["Stop was too tight"],
        lessons_learned=["Allow more room for volatility"],
        setup_validity="valid",
        performance_rating=3,
    )
    
    # Update strategy
    await learning_service._update_strategy_from_trade(sample_trade, outcome)
    
    # Verify update was called
    assert mock_learning_repo.update_strategy_effectiveness.called
    
    # Check that effectiveness score was calculated
    call_args = mock_learning_repo.update_strategy_effectiveness.call_args
    effectiveness = call_args.kwargs['effectiveness_score']
    
    # Should be between 0 and 1
    assert 0.0 <= effectiveness <= 1.0


# ============================================================================
# Tests: Learning Aggregation
# ============================================================================


@pytest.mark.asyncio
async def test_aggregate_learnings_success(
    learning_service,
    mock_trade_reasoner,
    mock_learning_repo,
):
    """Test successful learning aggregation."""
    # Mock trade summaries
    mock_learning_repo.get_trade_summaries_for_learning.return_value = [
        {
            'trade_id': str(uuid4()),
            'symbol': 'BTC-USD',
            'setup_type': 'pullback',
            'market_phase': 'range',
            'pnl': 50.0,
            'outcome': 'win',
        }
        for _ in range(10)
    ]
    
    # Aggregate learnings
    insights = await learning_service.aggregate_learnings(
        filters={'symbol': 'BTC-USD'},
        min_trades=5,
        min_confidence=0.7,
    )
    
    # Verify reasoner was called
    mock_trade_reasoner.aggregate_learnings.assert_called_once()
    
    # Verify insights were returned and stored
    assert len(insights) == 2  # Mock returns 2 insights
    assert mock_learning_repo.create_learning_entry.call_count == 2


@pytest.mark.asyncio
async def test_aggregate_learnings_insufficient_trades(
    learning_service,
    mock_learning_repo,
):
    """Test aggregation with insufficient trades."""
    # Mock insufficient trade summaries
    mock_learning_repo.get_trade_summaries_for_learning.return_value = [
        {'trade_id': str(uuid4()), 'outcome': 'win'}
        for _ in range(2)
    ]
    
    # Aggregate learnings
    insights = await learning_service.aggregate_learnings(
        min_trades=5,
    )
    
    # Should return empty list
    assert insights == []


@pytest.mark.asyncio
async def test_aggregate_learnings_low_confidence_filter(
    learning_service,
    mock_trade_reasoner,
    mock_learning_repo,
):
    """Test that low-confidence insights are filtered out."""
    # Mock trade summaries
    mock_learning_repo.get_trade_summaries_for_learning.return_value = [
        {'trade_id': str(uuid4()), 'outcome': 'win'}
        for _ in range(10)
    ]
    
    # Mock insights with varying confidence
    async def mock_insights(*args, **kwargs):
        return [
            LearningInsight(
                insight_type="pattern",
                insight="High confidence insight about LE candles at support levels",
                confidence_score=0.85,
                sample_size=10,
                market_conditions={},
            ),
            LearningInsight(
                insight_type="pattern",
                insight="Low confidence insight that needs more data to validate",
                confidence_score=0.45,  # Below threshold
                sample_size=5,
                market_conditions={},
            ),
        ]
    
    mock_trade_reasoner.aggregate_learnings = AsyncMock(side_effect=mock_insights)
    
    # Aggregate with high confidence threshold
    insights = await learning_service.aggregate_learnings(
        min_trades=5,
        min_confidence=0.6,
    )
    
    # Only high-confidence insight should be returned
    assert len(insights) == 1
    assert insights[0].confidence_score >= 0.6
    
    # Only high-confidence should be stored
    mock_learning_repo.create_learning_entry.assert_called_once()


# ============================================================================
# Tests: Learning Retrieval
# ============================================================================


def test_get_relevant_learnings(
    learning_service,
    mock_learning_repo,
):
    """Test retrieval of relevant learnings for a context."""
    # Mock learning entries
    mock_learning_repo.get_learning_entries.return_value = [
        Mock(
            id=uuid4(),
            insight_type='pattern',
            insight='LE candle at support works well',
            confidence_score=0.8,
            sample_size=10,
            market_conditions={
                'setup_type': 'pullback',
                'market_phase': 'range',
            },
        ),
        Mock(
            id=uuid4(),
            insight_type='setup',
            insight='Breakouts work in drive phase',
            confidence_score=0.75,
            sample_size=8,
            market_conditions={
                'setup_type': 'breakout',
                'market_phase': 'drive',
            },
        ),
    ]
    
    # Get relevant learnings for pullback in range
    context = {
        'setup_type': 'pullback',
        'market_phase': 'range',
    }
    
    learnings = learning_service.get_relevant_learnings(context, limit=5)
    
    # Should return learnings sorted by relevance
    assert len(learnings) > 0
    assert learnings[0]['relevance'] > 0


def test_calculate_relevance_exact_match(learning_service):
    """Test relevance calculation with exact match."""
    learning = Mock(
        market_conditions={
            'setup_type': 'pullback',
            'market_phase': 'range',
            'symbol': 'BTC-USD',
            'timeframe': '15m',
        }
    )
    
    context = {
        'setup_type': 'pullback',
        'market_phase': 'range',
        'symbol': 'BTC-USD',
        'timeframe': '15m',
    }
    
    relevance = learning_service._calculate_relevance(learning, context)
    
    # Perfect match should give high score
    assert relevance == 1.0


def test_calculate_relevance_partial_match(learning_service):
    """Test relevance calculation with partial match."""
    learning = Mock(
        market_conditions={
            'setup_type': 'pullback',
            'market_phase': 'range',
        }
    )
    
    context = {
        'setup_type': 'pullback',
        'market_phase': 'drive',  # Different phase
        'symbol': 'ETH-USD',
    }
    
    relevance = learning_service._calculate_relevance(learning, context)
    
    # Partial match should give lower score
    assert 0.0 < relevance < 1.0


def test_calculate_relevance_no_match(learning_service):
    """Test relevance calculation with no match."""
    learning = Mock(
        market_conditions={
            'setup_type': 'breakout',
            'market_phase': 'drive',
        }
    )
    
    context = {
        'setup_type': 'pullback',
        'market_phase': 'range',
    }
    
    relevance = learning_service._calculate_relevance(learning, context)
    
    # No match should give zero score
    assert relevance == 0.0


# ============================================================================
# Tests: Maintenance Operations
# ============================================================================


def test_prune_low_confidence_learnings(
    learning_service,
    mock_learning_repo,
):
    """Test pruning of low-confidence learnings."""
    # Mock deactivation
    mock_learning_repo.deactivate_low_confidence_entries.return_value = 5
    
    # Prune
    count = learning_service.prune_low_confidence_learnings(threshold=0.3)
    
    # Verify deactivation was called
    mock_learning_repo.deactivate_low_confidence_entries.assert_called_once_with(0.3)
    assert count == 5


def test_get_learning_summary(
    learning_service,
    mock_learning_repo,
):
    """Test learning summary generation."""
    # Mock learning entries
    now = datetime.now(timezone.utc)
    mock_learning_repo.get_learning_entries.return_value = [
        Mock(
            created_at=now,
            insight_type='pattern',
            insight='Test insight 1',
            confidence_score=0.8,
            sample_size=10,
        ),
        Mock(
            created_at=now,
            insight_type='pattern',
            insight='Test insight 2',
            confidence_score=0.75,
            sample_size=8,
        ),
        Mock(
            created_at=now,
            insight_type='setup',
            insight='Test insight 3',
            confidence_score=0.85,
            sample_size=12,
        ),
    ]
    
    # Get summary
    summary = learning_service.get_learning_summary(days=30)
    
    # Verify summary structure
    assert summary['period_days'] == 30
    assert summary['total_learnings'] == 3
    assert 'avg_confidence' in summary
    assert 'by_type' in summary
    assert 'top_insights' in summary
    
    # Verify grouping by type
    assert 'pattern' in summary['by_type']
    assert 'setup' in summary['by_type']
    assert summary['by_type']['pattern']['count'] == 2
    assert summary['by_type']['setup']['count'] == 1


# ============================================================================
# Integration Test
# ============================================================================


@pytest.mark.asyncio
async def test_full_feedback_loop(
    learning_service,
    mock_trade_reasoner,
    mock_learning_repo,
    sample_trade,
    sample_candles,
):
    """Test full feedback loop from trade outcome to learning storage."""
    # Mock multiple trades for aggregation
    mock_learning_repo.get_trade_summaries_for_learning.return_value = [
        {
            'trade_id': str(uuid4()),
            'symbol': 'BTC-USD',
            'setup_type': 'pullback',
            'market_phase': 'range',
            'pnl': 50.0,
            'outcome': 'win',
        }
        for _ in range(10)
    ]
    
    # 1. Analyze individual trade outcome
    outcome = await learning_service.analyze_trade_outcome(
        trade=sample_trade,
        entry_reasoning="Test reasoning",
        entry_candles=sample_candles[:5],
        trade_candles=sample_candles[5:],
    )
    
    # Verify individual analysis
    assert outcome is not None
    assert mock_learning_repo.update_strategy_effectiveness.called
    
    # 2. Aggregate learnings from multiple trades
    insights = await learning_service.aggregate_learnings(
        min_trades=5,
        min_confidence=0.7,
    )
    
    # Verify aggregation
    assert len(insights) > 0
    assert mock_learning_repo.create_learning_entry.called
    
    # 3. Get summary
    summary = learning_service.get_learning_summary(days=30)
    
    # Verify summary generated
    assert 'total_learnings' in summary
