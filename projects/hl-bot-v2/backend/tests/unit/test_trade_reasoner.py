"""Unit tests for trade reasoner service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from hl_bot.services.trade_reasoner import (
    TradeReasoner,
    SetupAnalysis,
    RiskAssessment,
    OutcomeAnalysis,
    LearningInsight,
)
from hl_bot.services.llm_client import LLMClient
from hl_bot.types import (
    Candle,
    ConfluenceScore,
    Signal,
    Trade,
    SignalType,
    Timeframe,
    PatternType,
    SetupType,
    MarketPhase,
    TradeStatus,
)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    return AsyncMock(spec=LLMClient)


@pytest.fixture
def trade_reasoner(mock_llm_client):
    """Trade reasoner instance with mocked LLM."""
    return TradeReasoner(llm_client=mock_llm_client)


@pytest.fixture
def sample_signal():
    """Sample trade signal."""
    return Signal(
        id="signal-123",
        timestamp=datetime.now(timezone.utc),
        symbol="BTC-USD",
        signal_type=SignalType.LONG,
        timeframe=Timeframe.M15,
        entry_price=50000.0,
        stop_loss=49500.0,
        take_profit_1=50500.0,
        take_profit_2=51000.0,
        take_profit_3=51500.0,
        confluence_score=75.0,
        patterns_detected=[PatternType.LE_CANDLE, PatternType.HAMMER],
        setup_type=SetupType.PULLBACK,
        market_phase=MarketPhase.DRIVE,
        higher_tf_bias=SignalType.LONG,
        reasoning="Strong uptrend with pullback to support",
    )


@pytest.fixture
def sample_candles():
    """Sample candle data."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=5)
    candles = []
    
    for i in range(20):
        candles.append(
            Candle(
                timestamp=base_time + timedelta(minutes=15 * i),
                open=50000.0 + i * 10,
                high=50100.0 + i * 10,
                low=49900.0 + i * 10,
                close=50050.0 + i * 10,
                volume=1000000.0,
                timeframe=Timeframe.M15,
                symbol="BTC-USD",
            )
        )
    
    return candles


@pytest.fixture
def sample_confluence():
    """Sample confluence score."""
    return ConfluenceScore(
        total_score=75.0,
        breakdown={
            "pattern_strength": 20.0,
            "structure_alignment": 25.0,
            "zone_proximity": 15.0,
            "htf_confluence": 15.0,
        },
        timeframes_aligned=[Timeframe.M15, Timeframe.H1, Timeframe.H4],
        higher_tf_bias=SignalType.LONG,
        reasoning="Strong multi-timeframe bullish alignment",
    )


@pytest.fixture
def sample_trade():
    """Sample completed trade."""
    return Trade(
        id="trade-123",
        signal_id="signal-123",
        symbol="BTC-USD",
        side=SignalType.LONG,
        entry_price=50000.0,
        entry_time=datetime.now(timezone.utc) - timedelta(hours=2),
        position_size=0.1,
        stop_loss=49500.0,
        take_profits=[50500.0, 51000.0, 51500.0],
        status=TradeStatus.TP1_HIT,
        exit_price=50500.0,
        exit_time=datetime.now(timezone.utc) - timedelta(hours=1),
        pnl=50.0,
        pnl_percent=1.0,
        reasoning="Strong uptrend with pullback to support",
        post_analysis=None,
        max_adverse_excursion=-100.0,
        max_favorable_excursion=600.0,
    )


@pytest.mark.asyncio
async def test_analyze_setup_success(
    trade_reasoner, mock_llm_client, sample_signal, sample_candles, sample_confluence
):
    """Test successful setup analysis."""
    # Mock LLM response
    mock_analysis = SetupAnalysis(
        reasoning="Strong bullish setup with multi-timeframe confirmation",
        confluence_explanation="15M LE candle at 1H support with 4H uptrend intact",
        risk_assessment=RiskAssessment(
            risk_level="low",
            concerns=["Slight consolidation on 1H timeframe"],
            probability_estimate=0.65,
            position_size_recommendation="full",
            key_invalidation_levels=[49500.0, 49400.0],
        ),
        key_observations=[
            "Clean LE candle formation",
            "Support zone holding strong",
            "Volume increasing on bounce",
        ],
        market_context="Drive phase with healthy pullback to demand zone",
    )
    
    mock_llm_client.generate_structured.return_value = mock_analysis
    
    # Execute
    result = await trade_reasoner.analyze_setup(
        sample_signal, sample_candles, sample_confluence
    )
    
    # Verify
    assert result == mock_analysis
    assert result.risk_assessment.risk_level == "low"
    assert result.risk_assessment.probability_estimate == 0.65
    assert len(result.key_observations) == 3
    
    mock_llm_client.generate_structured.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_setup_high_risk(
    trade_reasoner, mock_llm_client, sample_signal, sample_candles, sample_confluence
):
    """Test setup analysis with high risk warning."""
    mock_analysis = SetupAnalysis(
        reasoning="Setup has potential but multiple concerns exist that reduce confidence in favorable outcome",
        confluence_explanation="Pattern detected but higher timeframe showing bearish divergence which conflicts with entry",
        risk_assessment=RiskAssessment(
            risk_level="high",
            concerns=[
                "Higher timeframe showing bearish divergence",
                "Major resistance overhead",
                "Low volume on recent candles",
            ],
            probability_estimate=0.35,
            position_size_recommendation="skip",
            key_invalidation_levels=[49500.0],
        ),
        key_observations=["Weak pattern formation", "Conflicting signals"],
        market_context="Uncertain phase with mixed signals across different timeframes",
    )
    
    mock_llm_client.generate_structured.return_value = mock_analysis
    
    result = await trade_reasoner.analyze_setup(
        sample_signal, sample_candles, sample_confluence
    )
    
    assert result.risk_assessment.risk_level == "high"
    assert result.risk_assessment.probability_estimate < 0.40
    assert len(result.risk_assessment.concerns) == 3


@pytest.mark.asyncio
async def test_assess_risk_pass(trade_reasoner, sample_signal):
    """Test risk assessment that passes filters."""
    analysis = SetupAnalysis(
        reasoning="Good setup with strong multi-timeframe confirmation and clear entry conditions aligned with trend",
        confluence_explanation="All timeframes aligned with bullish structure and pattern formation at key support level",
        risk_assessment=RiskAssessment(
            risk_level="low",
            concerns=[],
            probability_estimate=0.70,
            position_size_recommendation="full",
            key_invalidation_levels=[49500.0],
        ),
        key_observations=["Test observation"],
        market_context="Good conditions with clear trend and strong support levels",
    )
    
    passes = await trade_reasoner.assess_risk(sample_signal, analysis)
    assert passes is True


@pytest.mark.asyncio
async def test_assess_risk_fail_high_risk(trade_reasoner, sample_signal):
    """Test risk assessment fails on high risk level."""
    analysis = SetupAnalysis(
        reasoning="Risky setup with multiple conflicting signals that reduce confidence in positive outcome",
        confluence_explanation="Mixed signals across timeframes with higher timeframe showing opposite direction",
        risk_assessment=RiskAssessment(
            risk_level="high",
            concerns=["Major resistance"],
            probability_estimate=0.50,
            position_size_recommendation="half",
            key_invalidation_levels=[49500.0],
        ),
        key_observations=["Test observation"],
        market_context="Uncertain market conditions with choppy price action",
    )
    
    passes = await trade_reasoner.assess_risk(sample_signal, analysis)
    assert passes is False


@pytest.mark.asyncio
async def test_assess_risk_fail_low_probability(trade_reasoner, sample_signal):
    """Test risk assessment fails on low win probability."""
    analysis = SetupAnalysis(
        reasoning="Low probability setup with insufficient confluence across multiple timeframes to warrant entry",
        confluence_explanation="Weak alignment with only lower timeframe showing pattern while higher timeframes neutral",
        risk_assessment=RiskAssessment(
            risk_level="medium",
            concerns=["Low confluence"],
            probability_estimate=0.35,  # Below 40% threshold
            position_size_recommendation="half",
            key_invalidation_levels=[49500.0],
        ),
        key_observations=["Test observation"],
        market_context="Choppy market with no clear direction or strong levels",
    )
    
    passes = await trade_reasoner.assess_risk(sample_signal, analysis)
    assert passes is False


@pytest.mark.asyncio
async def test_assess_risk_fail_skip_recommendation(trade_reasoner, sample_signal):
    """Test risk assessment fails when LLM recommends skip."""
    analysis = SetupAnalysis(
        reasoning="Should skip this trade due to multiple concerning factors that outweigh potential reward",
        confluence_explanation="Conflicting signals across timeframes with no clear consensus on direction",
        risk_assessment=RiskAssessment(
            risk_level="medium",
            concerns=["Too many red flags"],
            probability_estimate=0.45,
            position_size_recommendation="skip",
            key_invalidation_levels=[49500.0],
        ),
        key_observations=["Test observation"],
        market_context="Risky environment with high volatility and unclear structure",
    )
    
    passes = await trade_reasoner.assess_risk(sample_signal, analysis)
    assert passes is False


@pytest.mark.asyncio
async def test_assess_risk_fail_low_confluence(trade_reasoner):
    """Test risk assessment fails on low confluence score."""
    signal = Signal(
        id="signal-low",
        timestamp=datetime.now(timezone.utc),
        symbol="BTC-USD",
        signal_type=SignalType.LONG,
        timeframe=Timeframe.M15,
        entry_price=50000.0,
        stop_loss=49500.0,
        take_profit_1=50500.0,
        take_profit_2=51000.0,
        confluence_score=35.0,  # Below 40 threshold
        patterns_detected=[PatternType.LE_CANDLE],
        setup_type=SetupType.PULLBACK,
        market_phase=MarketPhase.RANGE,
        higher_tf_bias=SignalType.LONG,
    )
    
    analysis = SetupAnalysis(
        reasoning="Low confluence setup with insufficient timeframe alignment to support entry decision confidently",
        confluence_explanation="Weak alignment with only single timeframe showing pattern and no higher timeframe support",
        risk_assessment=RiskAssessment(
            risk_level="low",
            concerns=[],
            probability_estimate=0.60,
            position_size_recommendation="full",
            key_invalidation_levels=[49500.0],
        ),
        key_observations=["Test observation"],
        market_context="Weak market structure with unclear direction and low conviction",
    )
    
    passes = await trade_reasoner.assess_risk(signal, analysis)
    assert passes is False


@pytest.mark.asyncio
async def test_review_outcome_success(
    trade_reasoner, mock_llm_client, sample_trade, sample_candles
):
    """Test successful outcome review."""
    mock_outcome = OutcomeAnalysis(
        what_happened="Trade hit TP1 as planned after brief pullback and continued upward momentum as expected",
        what_worked=[
            "Entry timing was excellent",
            "Pattern played out as expected",
            "Risk management worked perfectly",
        ],
        what_didnt_work=["Could have taken partial profits earlier"],
        lessons_learned=[
            "LE candle at support is reliable in drive phase",
            "Patience during initial pullback pays off",
        ],
        setup_validity="valid",
        performance_rating=4,
    )
    
    mock_llm_client.generate_structured.return_value = mock_outcome
    
    result = await trade_reasoner.review_outcome(
        sample_trade,
        "Strong uptrend with pullback to support",
        sample_candles,
        sample_candles[:10],
    )
    
    assert result == mock_outcome
    assert result.setup_validity == "valid"
    assert result.performance_rating == 4
    assert len(result.lessons_learned) == 2


@pytest.mark.asyncio
async def test_review_outcome_invalid_setup(
    trade_reasoner, mock_llm_client, sample_candles
):
    """Test outcome review for invalid setup."""
    losing_trade = Trade(
        id="trade-loss",
        signal_id="signal-loss",
        symbol="BTC-USD",
        side=SignalType.LONG,
        entry_price=50000.0,
        entry_time=datetime.now(timezone.utc) - timedelta(hours=2),
        position_size=0.1,
        stop_loss=49500.0,
        take_profits=[50500.0, 51000.0],
        status=TradeStatus.STOPPED,
        exit_price=49500.0,
        exit_time=datetime.now(timezone.utc) - timedelta(hours=1),
        pnl=-50.0,
        pnl_percent=-1.0,
        reasoning="Thought it was a breakout",
        max_adverse_excursion=-500.0,
        max_favorable_excursion=50.0,
    )
    
    mock_outcome = OutcomeAnalysis(
        what_happened="Trade stopped out immediately as price reversed, revealing this was a fakeout breakout setup",
        what_worked=["Stop loss prevented larger loss"],
        what_didnt_work=[
            "Failed to identify fakeout setup",
            "Ignored bearish divergence on HTF",
            "Entry was too aggressive",
        ],
        lessons_learned=[
            "Check HTF for divergence before entry",
            "Wait for confirmation on breakouts",
        ],
        setup_validity="invalid",
        performance_rating=2,
    )
    
    mock_llm_client.generate_structured.return_value = mock_outcome
    
    result = await trade_reasoner.review_outcome(
        losing_trade,
        "Thought it was a breakout",
        sample_candles,
        sample_candles[:5],
    )
    
    assert result.setup_validity == "invalid"
    assert result.performance_rating == 2
    assert len(result.what_didnt_work) >= 3


@pytest.mark.asyncio
async def test_aggregate_learnings_success(trade_reasoner, mock_llm_client):
    """Test successful learning aggregation."""
    trade_summaries = [
        {
            "symbol": "BTC-USD",
            "setup": "LE Candle at support",
            "outcome": "TP1 hit",
            "pnl_percent": 1.0,
            "market_phase": "drive",
        },
        {
            "symbol": "ETH-USD",
            "setup": "LE Candle at support",
            "outcome": "TP2 hit",
            "pnl_percent": 2.5,
            "market_phase": "drive",
        },
        {
            "symbol": "BTC-USD",
            "setup": "LE Candle at support",
            "outcome": "Stopped out",
            "pnl_percent": -1.0,
            "market_phase": "range",
        },
    ]
    
    mock_response = """[
        {
            "insight_type": "pattern",
            "insight": "LE candle setups in drive phase have 67% win rate vs 33% in range",
            "confidence_score": 0.7,
            "sample_size": 3,
            "market_conditions": {"phase": "drive", "pattern": "le_candle"}
        }
    ]"""
    
    mock_llm_client.generate.return_value = mock_response
    
    result = await trade_reasoner.aggregate_learnings(trade_summaries)
    
    assert len(result) == 1
    assert result[0].insight_type == "pattern"
    assert result[0].sample_size == 3
    assert result[0].confidence_score == 0.7


@pytest.mark.asyncio
async def test_aggregate_learnings_insufficient_data(trade_reasoner):
    """Test learning aggregation with insufficient data."""
    trade_summaries = [
        {"symbol": "BTC-USD", "outcome": "win"},
    ]
    
    result = await trade_reasoner.aggregate_learnings(trade_summaries, min_sample_size=3)
    
    assert len(result) == 0


@pytest.mark.asyncio
async def test_format_candles(trade_reasoner, sample_candles):
    """Test candle formatting for prompts."""
    formatted = trade_reasoner._format_candles(sample_candles[:5])
    
    assert "Time | Open | High | Low | Close | Volume" in formatted
    assert "50000.00" in formatted
    assert len(formatted.split("\n")) == 7  # Header + separator + 5 candles


def test_format_candles_empty(trade_reasoner):
    """Test formatting empty candle list."""
    formatted = trade_reasoner._format_candles([])
    assert formatted == "No candle data available"


@pytest.mark.asyncio
async def test_validate_risk_assessment(trade_reasoner, sample_signal):
    """Test risk assessment validation."""
    risk = RiskAssessment(
        risk_level="low",
        concerns=[],
        probability_estimate=0.65,
        position_size_recommendation="full",
        key_invalidation_levels=[49500.0, 49400.0],
    )
    
    # Should not raise
    trade_reasoner._validate_risk_assessment(risk, sample_signal)


@pytest.mark.asyncio
async def test_validate_risk_assessment_invalid_level(trade_reasoner, sample_signal):
    """Test validation fails on invalid invalidation level."""
    risk = RiskAssessment(
        risk_level="low",
        concerns=[],
        probability_estimate=0.65,
        position_size_recommendation="full",
        key_invalidation_levels=[0.0],  # Invalid: must be > 0
    )
    
    with pytest.raises(ValueError, match="Invalid invalidation level"):
        trade_reasoner._validate_risk_assessment(risk, sample_signal)


@pytest.mark.asyncio
async def test_validate_risk_assessment_caps_probability(trade_reasoner, sample_signal):
    """Test unrealistically high probability is capped."""
    risk = RiskAssessment(
        risk_level="low",
        concerns=[],
        probability_estimate=0.98,  # Too high
        position_size_recommendation="full",
        key_invalidation_levels=[49500.0],
    )
    
    trade_reasoner._validate_risk_assessment(risk, sample_signal)
    
    assert risk.probability_estimate == 0.90  # Capped


@pytest.mark.asyncio
async def test_parse_insights_response(trade_reasoner):
    """Test parsing insights from LLM response."""
    response = """[
        {
            "insight_type": "pattern",
            "insight": "LE candle setups at support in drive phase show 70% win rate with proper confluence",
            "confidence_score": 0.8,
            "sample_size": 5,
            "market_conditions": {"phase": "drive"}
        },
        {
            "insight_type": "risk",
            "insight": "Trades taken during low volume periods result in wider stop hunts before reversal",
            "confidence_score": 0.6,
            "sample_size": 3,
            "market_conditions": {}
        }
    ]"""
    
    insights = trade_reasoner._parse_insights_response(response, min_sample_size=3)
    
    assert len(insights) == 2
    assert insights[0].insight_type == "pattern"
    assert insights[1].insight_type == "risk"


@pytest.mark.asyncio
async def test_parse_insights_filters_small_samples(trade_reasoner):
    """Test insights with small samples are filtered out."""
    response = """[
        {
            "insight_type": "pattern",
            "insight": "Test insight",
            "confidence_score": 0.8,
            "sample_size": 2,
            "market_conditions": {}
        }
    ]"""
    
    insights = trade_reasoner._parse_insights_response(response, min_sample_size=3)
    
    assert len(insights) == 0  # Filtered out due to small sample


@pytest.mark.asyncio
async def test_parse_insights_handles_invalid_json(trade_reasoner):
    """Test parsing handles invalid JSON gracefully."""
    response = "not valid json"
    
    insights = trade_reasoner._parse_insights_response(response, min_sample_size=1)
    
    assert len(insights) == 0


@pytest.mark.asyncio
async def test_llm_error_handling(trade_reasoner, mock_llm_client, sample_signal, sample_candles, sample_confluence):
    """Test error handling when LLM call fails."""
    mock_llm_client.generate_structured.side_effect = Exception("API error")
    
    with pytest.raises(ValueError, match="Failed to analyze setup"):
        await trade_reasoner.analyze_setup(sample_signal, sample_candles, sample_confluence)
