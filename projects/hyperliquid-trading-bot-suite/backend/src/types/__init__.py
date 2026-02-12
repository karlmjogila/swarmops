"""Core types for the Hyperliquid Trading Bot Suite."""

from enum import Enum
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import uuid


# ===== TRADING ENUMS =====

class OrderSide(str, Enum):
    """Order side enum with normalized values."""
    LONG = "long"   # Primary for going long / buying
    SHORT = "short"  # Primary for going short / selling
    
    # Keep BUY/SELL as aliases that map to same underlying values
    BUY = "long"    # Alias for LONG (same value)
    SELL = "short"  # Alias for SHORT (same value)
    
    @classmethod
    def normalize(cls, value: str) -> 'OrderSide':
        """Normalize any order side string to the canonical form."""
        value_lower = value.lower()
        if value_lower in ('buy', 'long'):
            return cls.LONG
        elif value_lower in ('sell', 'short'):
            return cls.SHORT
        else:
            raise ValueError(f"Invalid OrderSide value: {value}")
    
    def is_long(self) -> bool:
        """Check if this side represents a long/buy position."""
        return self.value == "long"
    
    def is_short(self) -> bool:
        """Check if this side represents a short/sell position."""
        return self.value == "short"
    
    def opposite(self) -> 'OrderSide':
        """Get the opposite side."""
        return OrderSide.SHORT if self.is_long() else OrderSide.LONG


# Alias for TradeDirection (for backward compatibility)
class TradeDirection(str, Enum):
    """Trade direction enum (alias for OrderSide)."""
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    """Order type enum."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TradingMode(str, Enum):
    """Trading mode enum."""
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"


class Timeframe(str, Enum):
    """Timeframe enum."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    H12 = "12h"
    D1 = "1d"
    W1 = "1w"


# ===== STRATEGY ENUMS =====

class EntryType(str, Enum):
    """Entry pattern types."""
    LE = "le"  # Liquidity Engulf candle
    SMALL_WICK = "small_wick"
    STEEPER_WICK = "steeper_wick"
    CELERY = "celery"  # Celery play
    BREAKOUT = "breakout"
    FAKEOUT = "fakeout"
    ONION = "onion"  # Range extremes


class PatternType(str, Enum):
    """Pattern condition types."""
    CANDLE = "candle"
    STRUCTURE = "structure"
    ZONE = "zone"
    CYCLE = "cycle"
    CONFLUENCE = "confluence"


class MarketCycle(str, Enum):
    """Market cycle phases."""
    DRIVE = "drive"  # Strong momentum
    RANGE = "range"  # Consolidation/equilibrium
    LIQUIDITY = "liquidity"  # Stop hunts, sweeps


class ExitReason(str, Enum):
    """Trade exit reasons."""
    TP1 = "tp1"  # Take profit 1
    TP2 = "tp2"  # Take profit 2
    TP3 = "tp3"  # Take profit 3
    STOP_LOSS = "stop_loss"
    BREAKEVEN = "breakeven"
    MOMENTUM = "momentum"  # Momentum-based exit
    TIME_STOP = "time_stop"
    MANUAL = "manual"


class TradeOutcome(str, Enum):
    """Trade outcome classification."""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"


class SourceType(str, Enum):
    """Content source types."""
    PDF = "pdf"
    VIDEO = "video"
    MANUAL = "manual"
    SYSTEM = "system"


# ===== CORE DATA MODELS =====

@dataclass
class CandleData:
    """Represents OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: Timeframe
    
    @property
    def body_size(self) -> float:
        """Size of candle body."""
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        """Size of upper wick."""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Size of lower wick."""
        return min(self.open, self.close) - self.low
    
    @property
    def total_range(self) -> float:
        """Total candle range (high - low)."""
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        """True if candle is bullish."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """True if candle is bearish."""
        return self.close < self.open


@dataclass
class PatternCondition:
    """Represents a pattern detection condition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: PatternType = PatternType.CANDLE
    timeframe: Timeframe = Timeframe.M15
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    
    def __post_init__(self):
        """Validate condition parameters."""
        if not isinstance(self.params, dict):
            self.params = {}


@dataclass
class TimeframeAlignment:
    """Represents multi-timeframe alignment requirements."""
    higher_tf: Timeframe
    lower_tf: Timeframe
    required_confluence: float  # 0.0 to 1.0 confidence score
    bias_direction: Optional[OrderSide] = None


@dataclass
class RiskParameters:
    """Risk management parameters."""
    risk_percent: float = 2.0  # % of account to risk
    tp_levels: List[float] = field(default_factory=lambda: [1.0, 2.0])  # R multiples
    sl_distance: str = "structure"  # or absolute value
    max_concurrent_positions: int = 3
    daily_loss_limit_percent: float = 6.0


@dataclass
class StrategyRule:
    """Core strategy rule definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entry_type: EntryType = EntryType.LE
    
    # Source information
    source_type: SourceType = SourceType.MANUAL
    source_ref: str = ""  # File path, URL, etc.
    source_timestamp: Optional[float] = None  # Video timestamp in seconds
    
    # Pattern conditions
    conditions: List[PatternCondition] = field(default_factory=list)
    confluence_required: List[TimeframeAlignment] = field(default_factory=list)
    
    # Risk management
    risk_params: RiskParameters = field(default_factory=RiskParameters)
    
    # Learning metrics
    confidence: float = 0.5  # Updated based on outcomes
    usage_count: int = 0
    win_rate: float = 0.0
    avg_r_multiple: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Additional metadata
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class PriceActionSnapshot:
    """Snapshot of price action context at a point in time."""
    timestamp: datetime
    timeframes: Dict[str, List[CandleData]] = field(default_factory=dict)
    structure_notes: List[str] = field(default_factory=list)
    zone_interactions: List[str] = field(default_factory=list)
    market_cycle: Optional[MarketCycle] = None
    confluence_score: float = 0.0
    
    def add_timeframe_data(self, timeframe: Timeframe, candles: List[CandleData]):
        """Add candle data for a timeframe."""
        self.timeframes[timeframe.value] = candles


@dataclass
class TradeRecord:
    """Complete trade execution record."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_rule_id: str = ""
    
    # Basic trade info
    asset: str = ""
    direction: OrderSide = OrderSide.LONG
    entry_price: float = 0.0
    entry_time: datetime = field(default_factory=datetime.utcnow)
    quantity: float = 0.0
    
    # Exit information
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    
    # Partial fills tracking
    partial_exits: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    outcome: TradeOutcome = TradeOutcome.PENDING
    pnl_absolute: float = 0.0
    pnl_r_multiple: float = 0.0  # P&L in R (risk) multiples
    fees_paid: float = 0.0
    
    # Context and reasoning
    reasoning: str = ""  # LLM explanation
    price_action_context: Optional[PriceActionSnapshot] = None
    
    # Risk management
    initial_stop_loss: Optional[float] = None
    current_stop_loss: Optional[float] = None
    take_profit_levels: List[float] = field(default_factory=list)
    
    # Metadata
    trading_mode: TradingMode = TradingMode.PAPER
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LearningEntry:
    """Knowledge base learning entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_rule_id: str = ""
    
    # Learning content
    insight: str = ""  # What was learned
    pattern_identified: str = ""  # Pattern that was discovered
    supporting_trades: List[str] = field(default_factory=list)  # Trade IDs
    
    # Confidence and validation
    confidence: float = 0.5
    validation_count: int = 0
    contradiction_count: int = 0
    
    # Context
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    timeframe_context: List[Timeframe] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: str = ""


# ===== TRADING EXECUTION MODELS =====

@dataclass
class Position:
    """Represents a trading position."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset: str = ""
    size: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    
    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Position details
    side: OrderSide = OrderSide.LONG
    leverage: float = 1.0
    margin_used: float = 0.0
    
    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Associated trade record
    trade_record_id: Optional[str] = None


@dataclass
class Order:
    """Represents a trading order."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Order details
    asset: str = ""
    size: float = 0.0
    price: Optional[float] = None
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    
    # Status tracking
    status: OrderStatus = OrderStatus.PENDING
    filled_size: float = 0.0
    avg_fill_price: Optional[float] = None
    remaining_size: float = 0.0
    
    # Order parameters
    time_in_force: str = "GTC"  # Good Till Cancelled
    reduce_only: bool = False
    post_only: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Associated records
    position_id: Optional[str] = None
    trade_record_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize remaining size."""
        if self.remaining_size == 0.0:
            self.remaining_size = self.size


@dataclass
class Trade:
    """Represents a completed trade execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    
    # Trade details
    asset: str = ""
    size: float = 0.0
    price: float = 0.0
    side: OrderSide = OrderSide.BUY
    
    # Execution info
    timestamp: datetime = field(default_factory=datetime.utcnow)
    fee: float = 0.0
    fee_currency: str = "USD"
    
    # Market data at execution
    bid: Optional[float] = None
    ask: Optional[float] = None
    mark_price: Optional[float] = None
    
    # Identifiers
    exchange_trade_id: Optional[str] = None
    position_id: Optional[str] = None


# ===== BALANCE AND ACCOUNT MODELS =====

@dataclass
class Balance:
    """Represents account balance."""
    asset: str = ""
    total: float = 0.0
    available: float = 0.0
    locked: float = 0.0
    
    # Additional balance info
    usd_value: Optional[float] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccountInfo:
    """Account information and statistics."""
    account_id: str = ""
    total_balance_usd: float = 0.0
    available_balance_usd: float = 0.0
    total_margin_used: float = 0.0
    
    # Risk metrics
    total_unrealized_pnl: float = 0.0
    daily_pnl: float = 0.0
    total_fees_paid: float = 0.0
    
    # Position info
    open_positions: int = 0
    open_orders: int = 0
    
    # Account status
    trading_enabled: bool = True
    withdrawals_enabled: bool = True
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.utcnow)


# ===== MARKET DATA MODELS =====

@dataclass
class MarketData:
    """Represents market data for an asset."""
    asset: str = ""
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    mark_price: Optional[float] = None
    
    # Volume and statistics
    volume_24h: float = 0.0
    volume_24h_usd: Optional[float] = None
    high_24h: float = 0.0
    low_24h: float = 0.0
    change_24h: float = 0.0
    change_24h_percent: float = 0.0
    
    # Funding (for perpetuals)
    funding_rate: Optional[float] = None
    next_funding_time: Optional[datetime] = None
    
    # Market info
    min_order_size: Optional[float] = None
    max_order_size: Optional[float] = None
    price_precision: int = 8
    size_precision: int = 8
    
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ===== BACKTESTING MODELS =====

@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    name: str = "Untitled Backtest"
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: datetime = field(default_factory=datetime.utcnow)
    
    # Assets and timeframes
    assets: List[str] = field(default_factory=list)
    timeframes: List[Timeframe] = field(default_factory=list)
    
    # Initial conditions
    initial_balance: float = 10000.0
    leverage: float = 1.0
    
    # Strategy configuration
    strategy_rules: List[str] = field(default_factory=list)  # Rule IDs
    risk_per_trade: float = 2.0
    
    # Execution settings
    slippage: float = 0.001  # 0.1% slippage
    commission: float = 0.0004  # 0.04% commission
    
    # Other settings
    allow_overlapping_trades: bool = False
    max_concurrent_trades: int = 3
    
    # Analysis settings (configurable for different strategies)
    min_candles_for_analysis: int = 20  # Minimum candles required per timeframe
    daily_loss_limit_percent: float = 5.0  # Daily loss limit as percentage


@dataclass
class BacktestResult:
    """Backtesting results."""
    config: BacktestConfig
    
    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Returns
    total_return: float = 0.0
    total_return_percent: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    
    # R-multiple statistics
    avg_r_multiple: float = 0.0
    best_r_multiple: float = 0.0
    worst_r_multiple: float = 0.0
    
    # Trade statistics
    avg_trade_duration_hours: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Balance curve
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    # Individual trades
    trades: List[TradeRecord] = field(default_factory=list)
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0


# ===== INGESTION MODELS =====

@dataclass
class IngestionSource:
    """Represents a content source for ingestion."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: SourceType = SourceType.PDF
    source_url: str = ""
    local_path: str = ""
    
    # Metadata
    title: str = ""
    author: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Processing status
    status: str = "pending"  # pending, processing, completed, error
    error_message: str = ""
    
    # Content extraction results
    extracted_text: str = ""
    extracted_images: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None


@dataclass
class VideoFrame:
    """Represents a frame extracted from video."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    
    # Frame details
    timestamp_seconds: float = 0.0
    frame_path: str = ""
    perceptual_hash: str = ""  # For deduplication
    
    # Analysis results
    description: str = ""
    contains_chart: bool = False
    analysis_confidence: float = 0.0
    
    # Extraction
    created_at: datetime = field(default_factory=datetime.utcnow)


# ===== API MODELS =====

@dataclass
class APIResponse:
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    error_code: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str = ""  # 'price_update', 'trade_signal', 'trade_execution', etc.
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ===== PATTERN DETECTION MODELS =====

@dataclass
class PatternDetection:
    """Represents a detected pattern."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: EntryType = EntryType.LE
    timeframe: Timeframe = Timeframe.M15
    
    # Detection details
    asset: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    
    # Pattern parameters
    candle_index: int = 0  # Index of the pattern candle
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    market_structure: Optional[str] = None
    market_cycle: Optional[MarketCycle] = None
    zone_interaction: Optional[str] = None
    
    # Signal generation
    generates_signal: bool = False
    signal_strength: float = 0.0
    confluence_score: float = 0.0


@dataclass
class MarketStructure:
    """Market structure analysis results."""
    asset: str = ""
    timeframe: Timeframe = Timeframe.H4
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Structure elements
    higher_highs: List[Dict[str, Any]] = field(default_factory=list)
    lower_lows: List[Dict[str, Any]] = field(default_factory=list)
    support_zones: List[Dict[str, Any]] = field(default_factory=list)
    resistance_zones: List[Dict[str, Any]] = field(default_factory=list)
    
    # Current bias
    trend_direction: Optional[OrderSide] = None
    trend_strength: float = 0.0
    
    # Break of structure
    last_bos: Optional[Dict[str, Any]] = None
    last_choch: Optional[Dict[str, Any]] = None


# Export all types
__all__ = [
    # Enums
    "OrderSide", "TradeDirection", "OrderType", "OrderStatus", "TradingMode", "Timeframe",
    "EntryType", "PatternType", "MarketCycle", "ExitReason", "TradeOutcome", "SourceType",
    
    # Core Data Models
    "CandleData", "PatternCondition", "TimeframeAlignment", "RiskParameters",
    "StrategyRule", "PriceActionSnapshot", "TradeRecord", "LearningEntry",
    
    # Trading Models
    "Position", "Order", "Trade", "Balance", "AccountInfo", "MarketData",
    
    # Backtesting Models
    "BacktestConfig", "BacktestResult",
    
    # Ingestion Models
    "IngestionSource", "VideoFrame",
    
    # API Models
    "APIResponse", "WebSocketMessage",
    
    # Pattern Detection Models
    "PatternDetection", "MarketStructure",
]