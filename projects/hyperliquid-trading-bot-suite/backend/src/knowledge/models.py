"""
Pydantic models for the knowledge base and trading system.
These models define the structure for API requests/responses and data validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from pydantic.types import StrictFloat, StrictInt

from ..types import (
    EntryType, PatternType, Timeframe, MarketCycle, 
    OrderSide, TradeOutcome, ExitReason, SourceType
)


class ContentSource(BaseModel):
    """Source information for strategy rules."""
    type: SourceType
    ref: str = Field(..., description="File path, URL, or identifier")
    timestamp: Optional[float] = Field(None, description="Timestamp in seconds for video content")
    page_number: Optional[int] = Field(None, description="Page number for PDF content")


class PatternCondition(BaseModel):
    """Conditions that must be met for a pattern to be valid."""
    type: PatternType
    timeframe: Timeframe 
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pattern-specific parameters like wickRatio, closePosition, etc."
    )
    required: bool = Field(default=True, description="Whether this condition is required or optional")
    
    @validator('params')
    def validate_params(cls, v):
        """Validate that params contain reasonable values."""
        # Add specific validation based on pattern type if needed
        return v


class TimeframeAlignment(BaseModel):
    """Defines required alignment between timeframes for confluence."""
    higher_tf: Timeframe = Field(..., description="Higher timeframe that sets bias")
    lower_tf: Timeframe = Field(..., description="Lower timeframe for entry")
    bias_required: str = Field(..., description="Required bias on higher TF (bullish/bearish/neutral)")
    entry_pattern: str = Field(..., description="Required entry pattern on lower TF")
    

class RiskParameters(BaseModel):
    """Risk management parameters for a strategy."""
    risk_percent: StrictFloat = Field(2.0, ge=0.1, le=10.0, description="Risk per trade as % of account")
    tp_levels: List[StrictFloat] = Field(
        default=[1.0, 2.0], 
        description="Take profit levels in R multiples"
    )
    sl_distance: str = Field(..., description="Stop loss distance (e.g., 'below_low', '20_pips', '0.5%')")
    max_concurrent: StrictInt = Field(3, ge=1, le=10, description="Max concurrent positions")
    
    @validator('tp_levels')
    def validate_tp_levels(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one TP level required")
        if not all(level > 0 for level in v):
            raise ValueError("All TP levels must be positive")
        if sorted(v) != v:
            raise ValueError("TP levels must be in ascending order")
        return v


class StrategyRule(BaseModel):
    """Core strategy rule definition."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    source: ContentSource
    entry_type: EntryType
    conditions: List[PatternCondition] = Field(..., min_items=1)
    confluence_required: List[TimeframeAlignment] = Field(default_factory=list)
    risk_params: RiskParameters
    confidence: StrictFloat = Field(0.5, ge=0.0, le=1.0, description="Strategy confidence based on backtesting")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    trade_count: StrictInt = Field(0, ge=0, description="Number of times this rule has been used")
    win_rate: Optional[StrictFloat] = Field(None, ge=0.0, le=1.0, description="Historical win rate")
    avg_r_multiple: Optional[StrictFloat] = Field(None, description="Average R multiple return")
    description: Optional[str] = Field(None, max_length=1000, description="Human-readable strategy description")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CandleData(BaseModel):
    """OHLCV candle data."""
    timestamp: datetime
    open: StrictFloat
    high: StrictFloat  
    low: StrictFloat
    close: StrictFloat
    volume: StrictFloat
    timeframe: Timeframe
    
    @validator('high', 'low', 'close')
    def validate_price_relationships(cls, v, values):
        if 'open' in values:
            open_price = values['open']
            if v <= 0:
                raise ValueError("Prices must be positive")
        return v


class PriceActionSnapshot(BaseModel):
    """Snapshot of price action context at trade time."""
    timeframes: Dict[str, List[CandleData]] = Field(
        description="Candle data for each timeframe (last N candles)"
    )
    structure_notes: List[str] = Field(
        default_factory=list,
        description="Market structure observations (BOS, ChoCH, etc.)"
    )
    zone_interactions: List[str] = Field(
        default_factory=list, 
        description="Support/resistance zone interactions"
    )
    market_cycle: Optional[MarketCycle] = Field(None, description="Identified market cycle phase")
    confluence_score: Optional[StrictFloat] = Field(
        None, ge=0.0, le=1.0, 
        description="Overall confluence score for the setup"
    )


class TradeRecord(BaseModel):
    """Complete trade record with all details."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    strategy_rule_id: str = Field(..., description="Reference to the strategy rule used")
    asset: str = Field(..., description="Trading pair (e.g., 'ETH-USD')")
    direction: OrderSide
    entry_price: StrictFloat = Field(..., gt=0)
    entry_time: datetime
    exit_price: Optional[StrictFloat] = Field(None, gt=0)
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    outcome: TradeOutcome = Field(default=TradeOutcome.PENDING)
    pnl_r: Optional[StrictFloat] = Field(None, description="P&L in R multiples")
    pnl_usd: Optional[StrictFloat] = Field(None, description="P&L in USD")
    position_size: StrictFloat = Field(..., gt=0, description="Position size")
    stop_loss: Optional[StrictFloat] = Field(None, gt=0)
    take_profit_levels: List[StrictFloat] = Field(default_factory=list)
    fees_usd: Optional[StrictFloat] = Field(None, ge=0, description="Total fees paid")
    reasoning: str = Field(..., description="LLM explanation for the trade")
    price_action_context: PriceActionSnapshot
    confidence: StrictFloat = Field(..., ge=0.0, le=1.0, description="Trade confidence at entry")
    is_backtest: bool = Field(default=False, description="Whether this is a backtested trade")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('exit_price')
    def validate_exit_price(cls, v, values):
        if v is not None and 'entry_price' in values:
            if v <= 0:
                raise ValueError("Exit price must be positive")
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LearningEntry(BaseModel):
    """Learning insights from trade outcomes."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    strategy_rule_id: Optional[str] = Field(None, description="Related strategy rule")
    insight: str = Field(..., min_length=10, max_length=1000, description="Key learning insight")
    supporting_trades: List[str] = Field(
        default_factory=list, 
        description="Trade IDs that support this insight"
    )
    confidence: StrictFloat = Field(..., ge=0.0, le=1.0, description="Confidence in this insight")
    impact_type: str = Field(
        ..., 
        description="Type of impact (success_factor, failure_pattern, market_condition)"
    )
    market_conditions: Optional[Dict[str, Any]] = Field(
        None, 
        description="Market conditions when this insight applies"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: Optional[datetime] = Field(None)
    validation_count: StrictInt = Field(0, ge=0, description="Number of times this insight was validated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StrategyPerformance(BaseModel):
    """Performance metrics for a strategy rule."""
    strategy_rule_id: str
    total_trades: StrictInt = Field(ge=0)
    winning_trades: StrictInt = Field(ge=0)
    losing_trades: StrictInt = Field(ge=0)
    win_rate: StrictFloat = Field(ge=0.0, le=1.0)
    avg_r_multiple: StrictFloat
    profit_factor: Optional[StrictFloat] = Field(None, ge=0)
    max_consecutive_losses: StrictInt = Field(ge=0)
    max_drawdown: StrictFloat = Field(ge=0.0, le=1.0)
    total_pnl_r: StrictFloat
    total_pnl_usd: Optional[StrictFloat] = None
    sharpe_ratio: Optional[StrictFloat] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('winning_trades', 'losing_trades')
    def validate_trade_counts(cls, v, values):
        if 'total_trades' in values and v > values['total_trades']:
            raise ValueError("Winning/losing trades cannot exceed total trades")
        return v


class BacktestConfig(BaseModel):
    """Configuration for backtesting runs."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    start_date: datetime
    end_date: datetime
    initial_balance: StrictFloat = Field(..., gt=0)
    strategy_rule_ids: List[str] = Field(..., min_items=1)
    assets: List[str] = Field(..., min_items=1)
    timeframes: List[Timeframe] = Field(..., min_items=1)
    risk_per_trade: StrictFloat = Field(2.0, ge=0.1, le=10.0)
    max_concurrent_positions: StrictInt = Field(3, ge=1, le=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v


class BacktestResult(BaseModel):
    """Results from a backtest run."""
    backtest_config_id: str
    total_trades: StrictInt = Field(ge=0)
    winning_trades: StrictInt = Field(ge=0)
    losing_trades: StrictInt = Field(ge=0) 
    win_rate: StrictFloat = Field(ge=0.0, le=1.0)
    total_return: StrictFloat
    max_drawdown: StrictFloat = Field(ge=0.0, le=1.0)
    profit_factor: Optional[StrictFloat] = Field(None, ge=0)
    sharpe_ratio: Optional[StrictFloat] = None
    sortino_ratio: Optional[StrictFloat] = None
    calmar_ratio: Optional[StrictFloat] = None
    final_balance: StrictFloat = Field(..., gt=0)
    trades: List[TradeRecord] = Field(default_factory=list)
    equity_curve: List[Dict[str, Union[datetime, float]]] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: Optional[StrictFloat] = Field(None, ge=0)


# Request/Response models for API endpoints
class IngestPDFRequest(BaseModel):
    """Request model for PDF ingestion."""
    file_path: str = Field(..., description="Path to the PDF file")
    strategy_name: Optional[str] = Field(None, description="Override strategy name")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class IngestVideoRequest(BaseModel):
    """Request model for video ingestion."""
    url: str = Field(..., description="YouTube URL or playlist")
    strategy_name: Optional[str] = Field(None, description="Override strategy name") 
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    extract_frames: bool = Field(default=True, description="Whether to extract video frames")


class IngestionResponse(BaseModel):
    """Response model for ingestion operations."""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    strategy_rules_created: List[str] = Field(default_factory=list)
    message: Optional[str] = Field(None, description="Status message")
    created_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "ContentSource",
    "PatternCondition", 
    "TimeframeAlignment",
    "RiskParameters",
    "StrategyRule",
    "CandleData",
    "PriceActionSnapshot", 
    "TradeRecord",
    "LearningEntry",
    "StrategyPerformance",
    "BacktestConfig",
    "BacktestResult",
    "IngestPDFRequest",
    "IngestVideoRequest",
    "IngestionResponse",
]