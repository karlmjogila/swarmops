"""Core type definitions for the HL Trading Bot.

All types are fully typed with Pydantic for validation at boundaries.
Following Python Backend Excellence principles.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums - String-based for clean serialization
# ============================================================================


class Timeframe(StrEnum):
    """Supported timeframes for analysis."""

    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class MarketPhase(StrEnum):
    """Market cycle phases."""

    DRIVE = "drive"
    RANGE = "range"
    LIQUIDITY = "liquidity"


class SignalType(StrEnum):
    """Trade direction."""

    LONG = "long"
    SHORT = "short"


class PatternType(StrEnum):
    """Detected candle patterns."""

    LE_CANDLE = "le_candle"
    SMALL_WICK = "small_wick"
    STEEPER_WICK = "steeper_wick"
    CELERY = "celery"
    ENGULFING = "engulfing"
    INSIDE_BAR = "inside_bar"
    OUTSIDE_BAR = "outside_bar"
    PINBAR = "pinbar"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"


class SetupType(StrEnum):
    """Trade setup categories."""

    BREAKOUT = "breakout"
    FAKEOUT = "fakeout"
    ONION = "onion"
    PULLBACK = "pullback"
    REVERSAL = "reversal"


class TradeStatus(StrEnum):
    """Trade lifecycle states."""

    OPEN = "open"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    STOPPED = "stopped"
    BREAKEVEN = "breakeven"
    CLOSED = "closed"


class ZoneType(StrEnum):
    """Support/resistance zone types."""

    SUPPORT = "support"
    RESISTANCE = "resistance"
    DEMAND = "demand"
    SUPPLY = "supply"
    ORDER_BLOCK = "order_block"


class StructureType(StrEnum):
    """Market structure concepts."""

    SWING_HIGH = "swing_high"
    SWING_LOW = "swing_low"
    BOS = "bos"  # Break of Structure
    CHOCH = "choch"  # Change of Character
    FVG = "fvg"  # Fair Value Gap
    ORDER_BLOCK = "order_block"
    LIQUIDITY_POOL = "liquidity_pool"


class JobStatus(StrEnum):
    """Content ingestion job statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderType(StrEnum):
    """Order types for trading."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(StrEnum):
    """Order side (buy/sell)."""

    BUY = "buy"
    SELL = "sell"


# ============================================================================
# Market Data Models
# ============================================================================


class Candle(BaseModel):
    """OHLCV candle data."""

    timestamp: datetime = Field(..., description="Candle open time")
    open: float = Field(..., gt=0, description="Open price")
    high: float = Field(..., gt=0, description="High price")
    low: float = Field(..., gt=0, description="Low price")
    close: float = Field(..., gt=0, description="Close price")
    volume: float = Field(..., ge=0, description="Volume")
    timeframe: Timeframe = Field(..., description="Candle timeframe")
    symbol: str = Field(..., min_length=1, description="Trading symbol")

    @field_validator("high")
    @classmethod
    def high_must_be_highest(cls, v: float, info) -> float:
        """Validate high is the highest price."""
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        if "open" in info.data and v < info.data["open"]:
            raise ValueError("high must be >= open")
        if "close" in info.data and v < info.data["close"]:
            raise ValueError("high must be >= close")
        return v

    @field_validator("low")
    @classmethod
    def low_must_be_lowest(cls, v: float, info) -> float:
        """Validate low is the lowest price."""
        if "open" in info.data and v > info.data["open"]:
            raise ValueError("low must be <= open")
        if "close" in info.data and v > info.data["close"]:
            raise ValueError("low must be <= close")
        return v

    @property
    def body_size(self) -> float:
        """Calculate candle body size (absolute difference between open and close)."""
        return abs(self.close - self.open)

    @property
    def total_range(self) -> float:
        """Calculate total candle range (high - low)."""
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)."""
        return self.close < self.open

    def is_doji(self, threshold: float = 0.1) -> bool:
        """Check if candle is a doji (body size < threshold% of range).
        
        Args:
            threshold: Body size threshold as fraction of total range (default: 10%)
            
        Returns:
            True if candle is a doji (very small body relative to range)
        """
        if self.total_range == 0:
            return True
        return (self.body_size / self.total_range) < threshold


class Zone(BaseModel):
    """Support/resistance or demand/supply zone."""

    price_low: float = Field(..., gt=0)
    price_high: float = Field(..., gt=0)
    zone_type: ZoneType
    strength: float = Field(..., ge=0, le=1, description="Zone strength 0-1")
    touches: int = Field(default=0, ge=0, description="Number of touches")
    last_touch: datetime | None = Field(default=None)
    timeframe: Timeframe

    @field_validator("price_high")
    @classmethod
    def high_must_exceed_low(cls, v: float, info) -> float:
        """Validate price_high > price_low."""
        if "price_low" in info.data and v <= info.data["price_low"]:
            raise ValueError("price_high must be > price_low")
        return v


class MarketStructure(BaseModel):
    """Market structure element."""

    structure_type: StructureType
    price: float = Field(..., gt=0)
    timestamp: datetime
    timeframe: Timeframe
    strength: float = Field(..., ge=0, le=1)
    metadata: dict[str, str | float | int] = Field(default_factory=dict)


# ============================================================================
# Pattern Detection
# ============================================================================


class PatternDetection(BaseModel):
    """Detected pattern with metadata."""

    pattern_type: PatternType
    timestamp: datetime
    timeframe: Timeframe
    candle_index: int = Field(..., ge=0)
    confidence: float = Field(..., ge=0, le=1)
    metadata: dict[str, str | float | int] = Field(default_factory=dict)


class ConfluenceScore(BaseModel):
    """Multi-timeframe confluence analysis."""

    total_score: float = Field(..., ge=0, le=100)
    breakdown: dict[str, float] = Field(
        ..., description="Component scores (patterns, structure, zones, etc.)"
    )
    timeframes_aligned: list[Timeframe]
    higher_tf_bias: SignalType
    reasoning: str = Field(..., min_length=1)


# ============================================================================
# Trading Signals & Trades
# ============================================================================


class Signal(BaseModel):
    """Trading signal with full context."""

    id: str = Field(..., min_length=1)
    timestamp: datetime
    symbol: str = Field(..., min_length=1)
    signal_type: SignalType
    timeframe: Timeframe
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit_1: float = Field(..., gt=0)
    take_profit_2: float = Field(..., gt=0)
    take_profit_3: float | None = Field(default=None, gt=0)
    confluence_score: float = Field(..., ge=0, le=100)
    patterns_detected: list[PatternType]
    setup_type: SetupType
    market_phase: MarketPhase
    higher_tf_bias: SignalType
    reasoning: str | None = Field(default=None, description="LLM explanation")

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss(cls, v: float, info) -> float:
        """Validate stop loss is on correct side of entry."""
        if "signal_type" not in info.data or "entry_price" not in info.data:
            return v

        signal_type = info.data["signal_type"]
        entry = info.data["entry_price"]

        if signal_type == SignalType.LONG and v >= entry:
            raise ValueError("LONG stop loss must be < entry price")
        if signal_type == SignalType.SHORT and v <= entry:
            raise ValueError("SHORT stop loss must be > entry price")

        return v

    @field_validator("take_profit_1", "take_profit_2")
    @classmethod
    def validate_take_profits(cls, v: float, info) -> float:
        """Validate take profits are on correct side of entry."""
        if "signal_type" not in info.data or "entry_price" not in info.data:
            return v

        signal_type = info.data["signal_type"]
        entry = info.data["entry_price"]

        if signal_type == SignalType.LONG and v <= entry:
            raise ValueError("LONG take profit must be > entry price")
        if signal_type == SignalType.SHORT and v >= entry:
            raise ValueError("SHORT take profit must be < entry price")

        return v


class Trade(BaseModel):
    """Executed trade with full lifecycle."""

    id: str = Field(..., min_length=1)
    signal_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: SignalType
    entry_price: float = Field(..., gt=0)
    entry_time: datetime
    position_size: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profits: list[float] = Field(..., min_length=1)
    status: TradeStatus
    exit_price: float | None = Field(default=None, gt=0)
    exit_time: datetime | None = Field(default=None)
    pnl: float | None = Field(default=None)
    pnl_percent: float | None = Field(default=None)
    reasoning: str = Field(..., min_length=1, description="Entry reasoning")
    post_analysis: str | None = Field(default=None, description="Exit analysis")
    max_adverse_excursion: float | None = Field(default=None)
    max_favorable_excursion: float | None = Field(default=None)


class Portfolio(BaseModel):
    """Portfolio state snapshot."""

    balance: float = Field(..., ge=0)
    equity: float = Field(..., ge=0)
    open_positions: int = Field(..., ge=0)
    total_trades: int = Field(..., ge=0)
    winning_trades: int = Field(..., ge=0)
    losing_trades: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0, le=1)
    profit_factor: float = Field(..., ge=0)
    max_drawdown: float = Field(..., ge=0, le=1)
    sharpe_ratio: float
    total_pnl: float


# ============================================================================
# Strategy Rules
# ============================================================================


class Condition(BaseModel):
    """A single rule condition."""

    field: str = Field(..., min_length=1)
    operator: str = Field(..., pattern=r"^(eq|ne|gt|gte|lt|lte|in|contains)$")
    value: str | float | int | bool | list[str | float | int]
    description: str = Field(..., min_length=1)


class ExitRules(BaseModel):
    """Exit strategy rules."""

    tp1_percent: float = Field(..., gt=0, description="First TP as % of risk")
    tp1_position_percent: float = Field(..., gt=0, le=1, description="% to close at TP1")
    tp2_percent: float = Field(..., gt=0, description="Second TP as % of risk")
    tp3_percent: float | None = Field(default=None, gt=0, description="Optional third TP")
    move_to_breakeven_at: float = Field(
        ..., gt=0, description="Move SL to BE at this % of risk"
    )
    trailing_stop: bool = Field(default=False)
    trailing_stop_trigger: float | None = Field(default=None, gt=0)


class RiskParams(BaseModel):
    """Risk management parameters."""

    risk_percent: float = Field(..., gt=0, le=0.1, description="Risk per trade (max 10%)")
    max_positions: int = Field(..., ge=1, le=10)
    max_correlation: float = Field(
        ..., ge=0, le=1, description="Max correlation between positions"
    )
    max_daily_loss: float = Field(..., gt=0, le=0.2, description="Max daily loss (% of balance)")


class Source(BaseModel):
    """Content source metadata."""

    source_type: Literal["youtube", "pdf", "manual"]
    source_id: str = Field(..., min_length=1, description="URL or file identifier")
    extracted_at: datetime
    confidence: float = Field(..., ge=0, le=1)


class StrategyRule(BaseModel):
    """Complete strategy rule definition."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    timeframes: list[Timeframe] = Field(..., min_length=1)
    market_phase: MarketPhase
    entry_conditions: list[Condition] = Field(..., min_length=1)
    exit_rules: ExitRules
    risk_params: RiskParams
    source: Source
    effectiveness_score: float = Field(default=0.5, ge=0, le=1)
    total_trades: int = Field(default=0, ge=0)
    winning_trades: int = Field(default=0, ge=0)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Content Ingestion
# ============================================================================


class ContentSource(BaseModel):
    """Content ingestion request."""

    content_type: Literal["youtube", "pdf"]
    url: str | None = Field(default=None, description="YouTube URL or file URL")
    file_content: bytes | None = Field(default=None, description="PDF file bytes")
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class IngestionJob(BaseModel):
    """Content processing job."""

    id: str = Field(..., min_length=1)
    content_source: ContentSource
    status: JobStatus
    progress: float = Field(default=0.0, ge=0, le=1)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None)
    extracted_strategies: list[str] = Field(
        default_factory=list, description="Strategy IDs extracted"
    )


class ExtractedStrategy(BaseModel):
    """Strategy extracted from content."""

    rule: StrategyRule
    raw_text: str = Field(..., min_length=1)
    images_analyzed: list[str] = Field(
        default_factory=list, description="Image URLs analyzed"
    )
    confidence: float = Field(..., ge=0, le=1)


# ============================================================================
# Live Trading
# ============================================================================


class OrderRequest(BaseModel):
    """Order placement request."""

    symbol: str = Field(..., min_length=1)
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(..., gt=0)
    price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    reduce_only: bool = Field(default=False)
    post_only: bool = Field(default=False)

    @field_validator("price")
    @classmethod
    def price_required_for_limit(cls, v: float | None, info) -> float | None:
        """Validate price is provided for limit orders."""
        if info.data.get("order_type") == OrderType.LIMIT and v is None:
            raise ValueError("Price is required for limit orders")
        return v


class Order(BaseModel):
    """Order response."""

    id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(..., gt=0)
    price: float | None = Field(default=None)
    stop_price: float | None = Field(default=None)
    status: str = Field(..., min_length=1)
    filled_quantity: float = Field(default=0.0, ge=0)
    average_fill_price: float | None = Field(default=None)
    created_at: datetime
    updated_at: datetime


class Position(BaseModel):
    """Open position."""

    symbol: str = Field(..., min_length=1)
    side: OrderSide
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    mark_price: float = Field(..., gt=0)
    liquidation_price: float | None = Field(default=None, gt=0)
    unrealized_pnl: float
    realized_pnl: float
    leverage: float = Field(..., gt=0)


# ============================================================================
# WebSocket Messages
# ============================================================================


class WSClientMessage(BaseModel):
    """Client -> Server WebSocket message."""

    action: Literal["subscribe", "unsubscribe", "control"]
    channel: str | None = Field(default=None)
    command: Literal["play", "pause", "step", "seek", "speed"] | None = Field(default=None)
    value: str | int | float | None = Field(default=None)


# Server -> Client messages use discriminated unions
class WSCandleMessage(BaseModel):
    """Candle update."""

    type: Literal["candle"]
    timeframe: Timeframe
    data: Candle


class WSSignalMessage(BaseModel):
    """Signal generated."""

    type: Literal["signal"]
    data: Signal


class WSTradeOpenMessage(BaseModel):
    """Trade opened."""

    type: Literal["trade_open"]
    data: Trade


class WSTradeUpdateMessage(BaseModel):
    """Trade updated."""

    type: Literal["trade_update"]
    data: Trade


class WSTradeCloseMessage(BaseModel):
    """Trade closed."""

    type: Literal["trade_close"]
    data: Trade


class WSPortfolioMessage(BaseModel):
    """Portfolio snapshot."""

    type: Literal["portfolio"]
    data: Portfolio


class WSDecisionMessage(BaseModel):
    """LLM decision reasoning."""

    type: Literal["decision"]
    trade_id: str
    reasoning: str


class WSStructureMessage(BaseModel):
    """Market structure update."""

    type: Literal["structure"]
    timeframe: Timeframe
    data: MarketStructure


class WSZoneMessage(BaseModel):
    """Zone update."""

    type: Literal["zone"]
    data: Zone


class WSErrorMessage(BaseModel):
    """Error message."""

    type: Literal["error"]
    message: str
    code: str | None = Field(default=None)


# Discriminated union of all server messages
WSServerMessage = Annotated[
    WSCandleMessage
    | WSSignalMessage
    | WSTradeOpenMessage
    | WSTradeUpdateMessage
    | WSTradeCloseMessage
    | WSPortfolioMessage
    | WSDecisionMessage
    | WSStructureMessage
    | WSZoneMessage
    | WSErrorMessage,
    Field(discriminator="type"),
]


# ============================================================================
# API Request/Response Models
# ============================================================================


class BacktestStartRequest(BaseModel):
    """Start backtest request."""

    symbol: str = Field(..., min_length=1)
    start_date: datetime
    end_date: datetime
    initial_balance: float = Field(..., gt=0)
    strategy_ids: list[str] = Field(..., min_length=1)
    timeframes: list[Timeframe] = Field(..., min_length=1)
    enable_llm_reasoning: bool = Field(default=False)


class BacktestControlRequest(BaseModel):
    """Backtest playback control."""

    command: Literal["play", "pause", "step_forward", "step_backward", "seek", "speed"]
    value: datetime | float | None = Field(default=None)


class BacktestState(BaseModel):
    """Current backtest state."""

    session_id: str
    is_running: bool
    current_time: datetime | None = Field(default=None)
    progress: float = Field(..., ge=0, le=1)
    speed: float = Field(..., gt=0)
    portfolio: Portfolio | None = Field(default=None)
    open_trades: list[Trade] = Field(default_factory=list)


class StrategyListResponse(BaseModel):
    """Strategy list response."""

    strategies: list[StrategyRule]
    total: int = Field(..., ge=0)


class TradeListResponse(BaseModel):
    """Trade list response."""

    trades: list[Trade]
    total: int = Field(..., ge=0)


class DecisionResponse(BaseModel):
    """Trade decision reasoning response."""

    trade_id: str
    reasoning: str
    timestamp: datetime
