"""Pydantic models for API validation and serialization."""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, validator
from enum import Enum

from . import (
    OrderSide, OrderType, OrderStatus, TradingMode, Timeframe,
    EntryType, PatternType, MarketCycle, ExitReason, TradeOutcome, SourceType
)


# ===== BASE MODELS =====

class BaseAPIModel(BaseModel):
    """Base Pydantic model with common configuration."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True
    )


# ===== CANDLE DATA MODELS =====

class CandleDataModel(BaseAPIModel):
    """Pydantic model for candle data."""
    timestamp: datetime
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trading volume")
    timeframe: Timeframe
    
    @validator('high')
    def validate_high(cls, v, values):
        """Ensure high is the highest value."""
        if 'low' in values and v < values['low']:
            raise ValueError('High must be >= low')
        if 'open' in values and 'close' in values:
            max_oc = max(values['open'], values['close'])
            if v < max_oc:
                raise ValueError('High must be >= max(open, close)')
        return v
    
    @validator('low')
    def validate_low(cls, v, values):
        """Ensure low is the lowest value."""
        if 'open' in values and 'close' in values:
            min_oc = min(values['open'], values['close'])
            if v > min_oc:
                raise ValueError('Low must be <= min(open, close)')
        return v


# ===== STRATEGY MODELS =====

class RiskParametersModel(BaseAPIModel):
    """Risk management parameters."""
    risk_percent: float = Field(default=2.0, ge=0.1, le=10.0, description="Risk percentage per trade")
    tp_levels: List[float] = Field(default=[1.0, 2.0], description="Take profit levels in R multiples")
    sl_distance: str = Field(default="structure", description="Stop loss distance method")
    max_concurrent_positions: int = Field(default=3, ge=1, le=10, description="Maximum concurrent positions")
    daily_loss_limit_percent: float = Field(default=6.0, ge=1.0, le=20.0, description="Daily loss limit percentage")
    
    @validator('tp_levels')
    def validate_tp_levels(cls, v):
        """Validate take profit levels."""
        if not v:
            raise ValueError('At least one TP level required')
        if any(level <= 0 for level in v):
            raise ValueError('All TP levels must be positive')
        if v != sorted(v):
            raise ValueError('TP levels must be in ascending order')
        return v


class PatternConditionModel(BaseAPIModel):
    """Pattern detection condition."""
    id: Optional[str] = Field(default=None, description="Condition ID")
    type: PatternType = Field(default=PatternType.CANDLE, description="Pattern type")
    timeframe: Timeframe = Field(default=Timeframe.M15, description="Timeframe")
    params: Dict[str, Any] = Field(default_factory=dict, description="Pattern parameters")
    description: str = Field(default="", description="Human-readable description")


class TimeframeAlignmentModel(BaseAPIModel):
    """Multi-timeframe alignment requirement."""
    higher_tf: Timeframe = Field(..., description="Higher timeframe")
    lower_tf: Timeframe = Field(..., description="Lower timeframe")
    required_confluence: float = Field(..., ge=0.0, le=1.0, description="Required confluence score")
    bias_direction: Optional[OrderSide] = Field(default=None, description="Required bias direction")
    
    @validator('lower_tf')
    def validate_timeframes(cls, v, values):
        """Ensure lower TF is actually lower than higher TF."""
        if 'higher_tf' not in values:
            return v
        
        # Define timeframe hierarchy (in minutes)
        tf_minutes = {
            Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15, Timeframe.M30: 30,
            Timeframe.H1: 60, Timeframe.H4: 240, Timeframe.H12: 720,
            Timeframe.D1: 1440, Timeframe.W1: 10080
        }
        
        higher_minutes = tf_minutes.get(values['higher_tf'], 0)
        lower_minutes = tf_minutes.get(v, 0)
        
        if lower_minutes >= higher_minutes:
            raise ValueError('Lower timeframe must be smaller than higher timeframe')
        
        return v


class StrategyRuleModel(BaseAPIModel):
    """Core strategy rule definition."""
    id: Optional[str] = Field(default=None, description="Strategy rule ID")
    name: str = Field(..., min_length=1, description="Strategy name")
    entry_type: EntryType = Field(default=EntryType.LE, description="Entry pattern type")
    
    # Source information
    source_type: SourceType = Field(default=SourceType.MANUAL, description="Content source type")
    source_ref: str = Field(default="", description="Source reference (file, URL, etc.)")
    source_timestamp: Optional[float] = Field(default=None, ge=0, description="Video timestamp in seconds")
    
    # Pattern conditions
    conditions: List[PatternConditionModel] = Field(default_factory=list, description="Pattern conditions")
    confluence_required: List[TimeframeAlignmentModel] = Field(default_factory=list, description="Timeframe alignments")
    
    # Risk management
    risk_params: RiskParametersModel = Field(default_factory=RiskParametersModel, description="Risk parameters")
    
    # Learning metrics
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Strategy confidence score")
    usage_count: int = Field(default=0, ge=0, description="Usage count")
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Win rate")
    avg_r_multiple: float = Field(default=0.0, description="Average R multiple")
    
    # Metadata
    notes: str = Field(default="", description="Additional notes")
    tags: List[str] = Field(default_factory=list, description="Tags")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")
    
    # Timestamps (auto-managed by backend)
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    last_used: Optional[datetime] = Field(default=None, description="Last used timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Update timestamp")


# ===== TRADE MODELS =====

class PriceActionSnapshotModel(BaseAPIModel):
    """Price action context snapshot."""
    timestamp: datetime
    timeframes: Dict[str, List[CandleDataModel]] = Field(default_factory=dict, description="Multi-timeframe data")
    structure_notes: List[str] = Field(default_factory=list, description="Market structure notes")
    zone_interactions: List[str] = Field(default_factory=list, description="Zone interaction notes")
    market_cycle: Optional[MarketCycle] = Field(default=None, description="Market cycle phase")
    confluence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confluence score")


class TradeRecordModel(BaseAPIModel):
    """Complete trade execution record."""
    id: Optional[str] = Field(default=None, description="Trade ID")
    strategy_rule_id: str = Field(..., description="Strategy rule ID")
    
    # Basic trade info
    asset: str = Field(..., min_length=1, description="Trading asset")
    direction: OrderSide = Field(..., description="Trade direction")
    entry_price: float = Field(..., gt=0, description="Entry price")
    entry_time: datetime = Field(..., description="Entry time")
    quantity: float = Field(..., gt=0, description="Trade quantity")
    
    # Exit information
    exit_price: Optional[float] = Field(default=None, gt=0, description="Exit price")
    exit_time: Optional[datetime] = Field(default=None, description="Exit time")
    exit_reason: Optional[ExitReason] = Field(default=None, description="Exit reason")
    
    # Partial exits
    partial_exits: List[Dict[str, Any]] = Field(default_factory=list, description="Partial exit records")
    
    # Performance metrics
    outcome: TradeOutcome = Field(default=TradeOutcome.PENDING, description="Trade outcome")
    pnl_absolute: float = Field(default=0.0, description="Absolute P&L")
    pnl_r_multiple: float = Field(default=0.0, description="P&L in R multiples")
    fees_paid: float = Field(default=0.0, ge=0, description="Fees paid")
    
    # Context and reasoning
    reasoning: str = Field(default="", description="LLM trade reasoning")
    price_action_context: Optional[PriceActionSnapshotModel] = Field(default=None, description="Price action context")
    
    # Risk management
    initial_stop_loss: Optional[float] = Field(default=None, gt=0, description="Initial stop loss")
    current_stop_loss: Optional[float] = Field(default=None, gt=0, description="Current stop loss")
    take_profit_levels: List[float] = Field(default_factory=list, description="Take profit levels")
    
    # Metadata
    trading_mode: TradingMode = Field(default=TradingMode.PAPER, description="Trading mode")
    notes: str = Field(default="", description="Additional notes")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Update timestamp")


class LearningEntryModel(BaseAPIModel):
    """Knowledge base learning entry."""
    id: Optional[str] = Field(default=None, description="Learning entry ID")
    strategy_rule_id: str = Field(..., description="Related strategy rule ID")
    
    # Learning content
    insight: str = Field(..., min_length=1, description="Learning insight")
    pattern_identified: str = Field(default="", description="Identified pattern")
    supporting_trades: List[str] = Field(default_factory=list, description="Supporting trade IDs")
    
    # Confidence and validation
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Insight confidence")
    validation_count: int = Field(default=0, ge=0, description="Validation count")
    contradiction_count: int = Field(default=0, ge=0, description="Contradiction count")
    
    # Context
    market_conditions: Dict[str, Any] = Field(default_factory=dict, description="Market conditions")
    timeframe_context: List[Timeframe] = Field(default_factory=list, description="Relevant timeframes")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags")
    notes: str = Field(default="", description="Additional notes")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Update timestamp")


# ===== TRADING EXECUTION MODELS =====

class OrderModel(BaseAPIModel):
    """Trading order."""
    id: Optional[str] = Field(default=None, description="Order ID")
    
    # Order details
    asset: str = Field(..., min_length=1, description="Trading asset")
    size: float = Field(..., gt=0, description="Order size")
    price: Optional[float] = Field(default=None, gt=0, description="Order price (for limit orders)")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    
    # Status tracking
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    filled_size: float = Field(default=0.0, ge=0, description="Filled size")
    avg_fill_price: Optional[float] = Field(default=None, gt=0, description="Average fill price")
    remaining_size: float = Field(default=0.0, ge=0, description="Remaining size")
    
    # Order parameters
    time_in_force: str = Field(default="GTC", description="Time in force")
    reduce_only: bool = Field(default=False, description="Reduce only flag")
    post_only: bool = Field(default=False, description="Post only flag")
    
    # Timestamps
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Update timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    
    # Associated records
    position_id: Optional[str] = Field(default=None, description="Position ID")
    trade_record_id: Optional[str] = Field(default=None, description="Trade record ID")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PositionModel(BaseAPIModel):
    """Trading position."""
    id: Optional[str] = Field(default=None, description="Position ID")
    asset: str = Field(..., min_length=1, description="Trading asset")
    size: float = Field(..., description="Position size (positive for long, negative for short)")
    avg_price: float = Field(..., gt=0, description="Average entry price")
    current_price: float = Field(..., gt=0, description="Current market price")
    
    # P&L tracking
    unrealized_pnl: float = Field(default=0.0, description="Unrealized P&L")
    realized_pnl: float = Field(default=0.0, description="Realized P&L")
    
    # Position details
    side: OrderSide = Field(..., description="Position side")
    leverage: float = Field(default=1.0, gt=0, le=100, description="Leverage")
    margin_used: float = Field(default=0.0, ge=0, description="Margin used")
    
    # Risk management
    stop_loss: Optional[float] = Field(default=None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(default=None, gt=0, description="Take profit price")
    
    # Associated records
    trade_record_id: Optional[str] = Field(default=None, description="Trade record ID")
    
    # Timestamps
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Update timestamp")


# ===== MARKET DATA MODELS =====

class MarketDataModel(BaseAPIModel):
    """Market data for an asset."""
    asset: str = Field(..., min_length=1, description="Trading asset")
    bid: float = Field(..., gt=0, description="Bid price")
    ask: float = Field(..., gt=0, description="Ask price")
    last: float = Field(..., gt=0, description="Last traded price")
    mark_price: Optional[float] = Field(default=None, gt=0, description="Mark price")
    
    # Volume and statistics
    volume_24h: float = Field(default=0.0, ge=0, description="24h volume")
    volume_24h_usd: Optional[float] = Field(default=None, ge=0, description="24h volume in USD")
    high_24h: float = Field(..., gt=0, description="24h high")
    low_24h: float = Field(..., gt=0, description="24h low")
    change_24h: float = Field(default=0.0, description="24h change")
    change_24h_percent: float = Field(default=0.0, description="24h change percentage")
    
    # Funding (for perpetuals)
    funding_rate: Optional[float] = Field(default=None, description="Current funding rate")
    next_funding_time: Optional[datetime] = Field(default=None, description="Next funding time")
    
    # Market info
    min_order_size: Optional[float] = Field(default=None, gt=0, description="Minimum order size")
    max_order_size: Optional[float] = Field(default=None, gt=0, description="Maximum order size")
    price_precision: int = Field(default=8, ge=0, le=12, description="Price precision")
    size_precision: int = Field(default=8, ge=0, le=12, description="Size precision")
    
    timestamp: datetime = Field(..., description="Data timestamp")
    
    @validator('ask')
    def validate_ask_bid_spread(cls, v, values):
        """Ensure ask >= bid."""
        if 'bid' in values and v < values['bid']:
            raise ValueError('Ask must be >= bid')
        return v
    
    @validator('high_24h')
    def validate_high_24h(cls, v, values):
        """Ensure 24h high makes sense."""
        for price_field in ['bid', 'ask', 'last']:
            if price_field in values and v < values[price_field]:
                raise ValueError(f'24h high must be >= {price_field}')
        return v
    
    @validator('low_24h')
    def validate_low_24h(cls, v, values):
        """Ensure 24h low makes sense."""
        for price_field in ['bid', 'ask', 'last']:
            if price_field in values and v > values[price_field]:
                raise ValueError(f'24h low must be <= {price_field}')
        return v


# ===== BACKTESTING MODELS =====

class BacktestConfigModel(BaseAPIModel):
    """Backtesting configuration."""
    name: str = Field(default="Untitled Backtest", min_length=1, description="Backtest name")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    
    # Assets and timeframes
    assets: List[str] = Field(..., min_items=1, description="Assets to test")
    timeframes: List[Timeframe] = Field(..., min_items=1, description="Timeframes to analyze")
    
    # Initial conditions
    initial_balance: float = Field(default=10000.0, gt=0, description="Initial balance")
    leverage: float = Field(default=1.0, gt=0, le=100, description="Maximum leverage")
    
    # Strategy configuration
    strategy_rules: List[str] = Field(..., min_items=1, description="Strategy rule IDs")
    risk_per_trade: float = Field(default=2.0, gt=0, le=10, description="Risk per trade (%)")
    
    # Execution settings
    slippage: float = Field(default=0.001, ge=0, le=0.1, description="Slippage (%)")
    commission: float = Field(default=0.0004, ge=0, le=0.01, description="Commission (%)")
    
    # Other settings
    allow_overlapping_trades: bool = Field(default=False, description="Allow overlapping trades")
    max_concurrent_trades: int = Field(default=3, ge=1, le=10, description="Max concurrent trades")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end date is after start date."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v


class BacktestResultModel(BaseAPIModel):
    """Backtesting results."""
    config: BacktestConfigModel = Field(..., description="Backtest configuration")
    
    # Performance metrics
    total_trades: int = Field(default=0, ge=0, description="Total number of trades")
    winning_trades: int = Field(default=0, ge=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, ge=0, description="Number of losing trades")
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Win rate")
    
    # Returns
    total_return: float = Field(default=0.0, description="Total return")
    total_return_percent: float = Field(default=0.0, description="Total return percentage")
    max_drawdown: float = Field(default=0.0, le=0, description="Maximum drawdown")
    max_drawdown_percent: float = Field(default=0.0, le=0, description="Maximum drawdown percentage")
    
    # Risk metrics
    sharpe_ratio: float = Field(default=0.0, description="Sharpe ratio")
    sortino_ratio: float = Field(default=0.0, description="Sortino ratio")
    profit_factor: float = Field(default=0.0, ge=0, description="Profit factor")
    
    # R-multiple statistics
    avg_r_multiple: float = Field(default=0.0, description="Average R multiple")
    best_r_multiple: float = Field(default=0.0, description="Best R multiple")
    worst_r_multiple: float = Field(default=0.0, description="Worst R multiple")
    
    # Trade statistics
    avg_trade_duration_hours: float = Field(default=0.0, ge=0, description="Average trade duration (hours)")
    max_consecutive_wins: int = Field(default=0, ge=0, description="Maximum consecutive wins")
    max_consecutive_losses: int = Field(default=0, ge=0, description="Maximum consecutive losses")
    
    # Balance curve
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list, description="Equity curve data")
    
    # Individual trades
    trades: List[TradeRecordModel] = Field(default_factory=list, description="Individual trade records")
    
    # Timestamps
    started_at: datetime = Field(..., description="Backtest start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Backtest completion timestamp")
    duration_seconds: float = Field(default=0.0, ge=0, description="Backtest duration in seconds")


# ===== INGESTION MODELS =====

class IngestionSourceModel(BaseAPIModel):
    """Content source for strategy ingestion."""
    id: Optional[str] = Field(default=None, description="Source ID")
    source_type: SourceType = Field(..., description="Source type")
    source_url: str = Field(default="", description="Source URL")
    local_path: str = Field(default="", description="Local file path")
    
    # Metadata
    title: str = Field(default="", description="Content title")
    author: str = Field(default="", description="Content author")
    description: str = Field(default="", description="Content description")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    
    # Processing status
    status: str = Field(default="pending", description="Processing status")
    error_message: str = Field(default="", description="Error message if any")
    
    # Content extraction results
    extracted_text: str = Field(default="", description="Extracted text content")
    extracted_images: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted images")
    
    # Timestamps
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    processed_at: Optional[datetime] = Field(default=None, description="Processing completion timestamp")


# ===== API RESPONSE MODELS =====

class APIResponseModel(BaseAPIModel):
    """Standard API response wrapper."""
    success: bool = Field(default=True, description="Request success flag")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    message: str = Field(default="", description="Response message")
    error_code: Optional[str] = Field(default=None, description="Error code if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PaginatedResponseModel(BaseAPIModel):
    """Paginated API response."""
    items: List[Any] = Field(default_factory=list, description="Items in current page")
    total: int = Field(default=0, ge=0, description="Total number of items")
    page: int = Field(default=1, ge=1, description="Current page number")
    per_page: int = Field(default=50, ge=1, le=1000, description="Items per page")
    has_next: bool = Field(default=False, description="Has next page")
    has_prev: bool = Field(default=False, description="Has previous page")


# ===== REQUEST MODELS =====

class StrategyRuleCreateModel(BaseAPIModel):
    """Request model for creating a strategy rule."""
    name: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    entry_type: EntryType = Field(..., description="Entry pattern type")
    source_type: SourceType = Field(default=SourceType.MANUAL, description="Source type")
    source_ref: str = Field(default="", max_length=500, description="Source reference")
    source_timestamp: Optional[float] = Field(default=None, ge=0, description="Video timestamp")
    conditions: List[PatternConditionModel] = Field(default_factory=list, description="Pattern conditions")
    confluence_required: List[TimeframeAlignmentModel] = Field(default_factory=list, description="Timeframe alignments")
    risk_params: RiskParametersModel = Field(default_factory=RiskParametersModel, description="Risk parameters")
    notes: str = Field(default="", max_length=1000, description="Notes")
    tags: List[str] = Field(default_factory=list, description="Tags")


class StrategyRuleUpdateModel(BaseAPIModel):
    """Request model for updating a strategy rule."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Strategy name")
    entry_type: Optional[EntryType] = Field(default=None, description="Entry pattern type")
    conditions: Optional[List[PatternConditionModel]] = Field(default=None, description="Pattern conditions")
    confluence_required: Optional[List[TimeframeAlignmentModel]] = Field(default=None, description="Timeframe alignments")
    risk_params: Optional[RiskParametersModel] = Field(default=None, description="Risk parameters")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Notes")
    tags: Optional[List[str]] = Field(default=None, description="Tags")
    enabled: Optional[bool] = Field(default=None, description="Enabled flag")


class BacktestCreateModel(BaseAPIModel):
    """Request model for creating a backtest."""
    name: str = Field(..., min_length=1, max_length=100, description="Backtest name")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    assets: List[str] = Field(..., min_items=1, max_items=10, description="Assets to test")
    timeframes: List[Timeframe] = Field(..., min_items=1, description="Timeframes")
    strategy_rules: List[str] = Field(..., min_items=1, description="Strategy rule IDs")
    initial_balance: float = Field(default=10000.0, gt=0, le=1000000, description="Initial balance")
    risk_per_trade: float = Field(default=2.0, gt=0, le=10, description="Risk per trade")
    leverage: float = Field(default=1.0, gt=0, le=100, description="Leverage")
    slippage: float = Field(default=0.001, ge=0, le=0.1, description="Slippage")
    commission: float = Field(default=0.0004, ge=0, le=0.01, description="Commission")


# Export all Pydantic models
__all__ = [
    "BaseAPIModel",
    "CandleDataModel",
    "RiskParametersModel",
    "PatternConditionModel",
    "TimeframeAlignmentModel",
    "StrategyRuleModel",
    "PriceActionSnapshotModel",
    "TradeRecordModel",
    "LearningEntryModel",
    "OrderModel",
    "PositionModel",
    "MarketDataModel",
    "BacktestConfigModel",
    "BacktestResultModel",
    "IngestionSourceModel",
    "APIResponseModel",
    "PaginatedResponseModel",
    "StrategyRuleCreateModel",
    "StrategyRuleUpdateModel",
    "BacktestCreateModel",
]