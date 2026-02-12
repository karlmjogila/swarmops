"""Strategies API endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from hl_bot.types import (
    Condition,
    ExitRules,
    MarketPhase,
    RiskParams,
    Source,
    StrategyRule,
    Timeframe,
)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class StrategyListResponse(BaseModel):
    """Response for strategy list endpoint."""

    strategies: List[StrategyRule]
    total: int


class StrategyUpdateRequest(BaseModel):
    """Request to update strategy properties."""

    enabled: bool | None = None
    effectiveness_score: float | None = None


# ============================================================================
# Mock Data - Replace with database queries
# ============================================================================

MOCK_STRATEGIES: dict[str, StrategyRule] = {
    "strat-001": StrategyRule(
        id="strat-001",
        name="Breakout + Higher TF Bias",
        description="Trade breakouts of consolidation zones when aligned with higher timeframe trend. Look for LE candles or steeper wicks closing beyond the range.",
        timeframes=[Timeframe.M15, Timeframe.H1, Timeframe.H4],
        market_phase=MarketPhase.DRIVE,
        entry_conditions=[
            Condition(
                field="pattern",
                operator="in",
                value=["le_candle", "steeper_wick"],
                description="LE candle or steeper wick pattern detected",
            ),
            Condition(
                field="higher_tf_trend",
                operator="eq",
                value="bullish",
                description="4H timeframe showing bullish structure",
            ),
            Condition(
                field="consolidation_break",
                operator="eq",
                value=True,
                description="Price breaks above consolidation range",
            ),
            Condition(
                field="confluence_score",
                operator="gte",
                value=70,
                description="Multi-timeframe confluence >= 70%",
            ),
        ],
        exit_rules=ExitRules(
            tp1_percent=1.5,
            tp1_position_percent=0.5,
            tp2_percent=2.5,
            tp3_percent=4.0,
            move_to_breakeven_at=1.0,
            trailing_stop=True,
            trailing_stop_trigger=2.0,
        ),
        risk_params=RiskParams(
            risk_percent=0.02,
            max_positions=3,
            max_correlation=0.7,
            max_daily_loss=0.06,
        ),
        source=Source(
            source_type="youtube",
            source_id="yt-video-12345",
            extracted_at=datetime(2025, 2, 10, 10, 30),
            confidence=0.85,
        ),
        effectiveness_score=0.78,
        total_trades=45,
        winning_trades=32,
        enabled=True,
        created_at=datetime(2025, 2, 10, 10, 35),
        updated_at=datetime(2025, 2, 11, 14, 20),
    ),
    "strat-002": StrategyRule(
        id="strat-002",
        name="Range Fade",
        description="Fade extremes in ranging markets. Enter on rejection patterns at support/resistance with tight stops.",
        timeframes=[Timeframe.M30, Timeframe.H1],
        market_phase=MarketPhase.RANGE,
        entry_conditions=[
            Condition(
                field="market_phase",
                operator="eq",
                value="range",
                description="Market in consolidation/range phase",
            ),
            Condition(
                field="at_zone_edge",
                operator="eq",
                value=True,
                description="Price at support or resistance zone",
            ),
            Condition(
                field="pattern",
                operator="in",
                value=["pinbar", "hammer", "shooting_star"],
                description="Rejection pattern at zone edge",
            ),
            Condition(
                field="zone_strength",
                operator="gte",
                value=0.6,
                description="Zone has been tested 3+ times",
            ),
        ],
        exit_rules=ExitRules(
            tp1_percent=1.0,
            tp1_position_percent=0.6,
            tp2_percent=2.0,
            tp3_percent=None,
            move_to_breakeven_at=0.8,
            trailing_stop=False,
            trailing_stop_trigger=None,
        ),
        risk_params=RiskParams(
            risk_percent=0.015,
            max_positions=5,
            max_correlation=0.5,
            max_daily_loss=0.05,
        ),
        source=Source(
            source_type="pdf",
            source_id="trading-strategy-ebook.pdf",
            extracted_at=datetime(2025, 2, 9, 16, 45),
            confidence=0.92,
        ),
        effectiveness_score=0.65,
        total_trades=67,
        winning_trades=41,
        enabled=True,
        created_at=datetime(2025, 2, 9, 17, 0),
        updated_at=datetime(2025, 2, 10, 8, 15),
    ),
    "strat-003": StrategyRule(
        id="strat-003",
        name="Liquidity Grab Reversal",
        description="Trade reversals after liquidity grabs (stop hunts). Wait for price to sweep obvious highs/lows then reverse with momentum.",
        timeframes=[Timeframe.M15, Timeframe.M30, Timeframe.H1],
        market_phase=MarketPhase.LIQUIDITY,
        entry_conditions=[
            Condition(
                field="liquidity_sweep",
                operator="eq",
                value=True,
                description="Price swept obvious high/low (stop hunt)",
            ),
            Condition(
                field="strong_reversal",
                operator="eq",
                value=True,
                description="Strong reversal candle after sweep",
            ),
            Condition(
                field="pattern",
                operator="in",
                value=["engulfing", "outside_bar"],
                description="Reversal pattern confirmation",
            ),
            Condition(
                field="time_since_sweep",
                operator="lte",
                value=3,
                description="Enter within 3 candles of sweep",
            ),
        ],
        exit_rules=ExitRules(
            tp1_percent=2.0,
            tp1_position_percent=0.4,
            tp2_percent=3.5,
            tp3_percent=5.0,
            move_to_breakeven_at=1.5,
            trailing_stop=True,
            trailing_stop_trigger=2.5,
        ),
        risk_params=RiskParams(
            risk_percent=0.025,
            max_positions=2,
            max_correlation=0.6,
            max_daily_loss=0.07,
        ),
        source=Source(
            source_type="youtube",
            source_id="yt-video-67890",
            extracted_at=datetime(2025, 2, 8, 12, 20),
            confidence=0.88,
        ),
        effectiveness_score=0.82,
        total_trades=38,
        winning_trades=29,
        enabled=True,
        created_at=datetime(2025, 2, 8, 12, 30),
        updated_at=datetime(2025, 2, 11, 9, 45),
    ),
    "strat-004": StrategyRule(
        id="strat-004",
        name="Failed Strategy Example",
        description="This is an experimental strategy that hasn't performed well. Disabled for review.",
        timeframes=[Timeframe.M5, Timeframe.M15],
        market_phase=MarketPhase.DRIVE,
        entry_conditions=[
            Condition(
                field="pattern",
                operator="eq",
                value="inside_bar",
                description="Inside bar pattern",
            ),
            Condition(
                field="volume_spike",
                operator="gte",
                value=1.5,
                description="Volume 1.5x average",
            ),
        ],
        exit_rules=ExitRules(
            tp1_percent=1.0,
            tp1_position_percent=0.5,
            tp2_percent=2.0,
            tp3_percent=None,
            move_to_breakeven_at=0.5,
            trailing_stop=False,
            trailing_stop_trigger=None,
        ),
        risk_params=RiskParams(
            risk_percent=0.01,
            max_positions=2,
            max_correlation=0.8,
            max_daily_loss=0.03,
        ),
        source=Source(
            source_type="manual",
            source_id="manual-entry-001",
            extracted_at=datetime(2025, 2, 5, 14, 0),
            confidence=0.5,
        ),
        effectiveness_score=0.35,
        total_trades=52,
        winning_trades=18,
        enabled=False,
        created_at=datetime(2025, 2, 5, 14, 15),
        updated_at=datetime(2025, 2, 7, 16, 30),
    ),
}


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies(
    enabled: bool | None = None,
    market_phase: MarketPhase | None = None,
    min_effectiveness: float | None = None,
) -> StrategyListResponse:
    """
    List all strategies with optional filters.

    Args:
        enabled: Filter by enabled status
        market_phase: Filter by market phase
        min_effectiveness: Minimum effectiveness score (0-1)

    Returns:
        List of strategies matching filters
    """
    strategies = list(MOCK_STRATEGIES.values())

    # Apply filters
    if enabled is not None:
        strategies = [s for s in strategies if s.enabled == enabled]

    if market_phase is not None:
        strategies = [s for s in strategies if s.market_phase == market_phase]

    if min_effectiveness is not None:
        strategies = [s for s in strategies if s.effectiveness_score >= min_effectiveness]

    return StrategyListResponse(
        strategies=strategies,
        total=len(strategies),
    )


@router.get("/strategies/{strategy_id}", response_model=StrategyRule)
async def get_strategy(strategy_id: str) -> StrategyRule:
    """
    Get a single strategy by ID.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Strategy details

    Raises:
        HTTPException: If strategy not found
    """
    if strategy_id not in MOCK_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )

    return MOCK_STRATEGIES[strategy_id]


@router.patch("/strategies/{strategy_id}", response_model=StrategyRule)
async def update_strategy(
    strategy_id: str, update: StrategyUpdateRequest
) -> StrategyRule:
    """
    Update strategy properties (e.g., enable/disable).

    Args:
        strategy_id: Strategy identifier
        update: Fields to update

    Returns:
        Updated strategy

    Raises:
        HTTPException: If strategy not found
    """
    if strategy_id not in MOCK_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )

    strategy = MOCK_STRATEGIES[strategy_id]

    # Update fields if provided
    if update.enabled is not None:
        strategy = strategy.model_copy(update={"enabled": update.enabled})

    if update.effectiveness_score is not None:
        strategy = strategy.model_copy(
            update={"effectiveness_score": update.effectiveness_score}
        )

    # Update timestamp
    strategy = strategy.model_copy(update={"updated_at": datetime.utcnow()})

    # Save back (in real implementation, this would be a database update)
    MOCK_STRATEGIES[strategy_id] = strategy

    return strategy


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(strategy_id: str) -> None:
    """
    Delete a strategy.

    Args:
        strategy_id: Strategy identifier

    Raises:
        HTTPException: If strategy not found
    """
    if strategy_id not in MOCK_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )

    del MOCK_STRATEGIES[strategy_id]
