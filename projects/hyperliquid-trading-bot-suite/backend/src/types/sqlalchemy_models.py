"""SQLAlchemy database models for the Hyperliquid Trading Bot Suite."""

from typing import List
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from . import (
    OrderSide, OrderType, OrderStatus, TradingMode, Timeframe,
    EntryType, PatternType, MarketCycle, ExitReason, TradeOutcome, SourceType
)

# Create base class for all SQLAlchemy models
Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class UUIDMixin:
    """Mixin for UUID primary keys."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# ===== STRATEGY MODELS =====

class StrategyRule(Base, UUIDMixin, TimestampMixin):
    """Strategy rule database model."""
    __tablename__ = "strategy_rules"
    
    # Core fields
    name = Column(String(100), nullable=False, index=True)
    entry_type = Column(Enum(EntryType), nullable=False, index=True)
    
    # Source information
    source_type = Column(Enum(SourceType), nullable=False, default=SourceType.MANUAL)
    source_ref = Column(String(500), nullable=False, default="")
    source_timestamp = Column(Float, nullable=True)  # Video timestamp in seconds
    
    # Pattern conditions (stored as JSON)
    conditions = Column(JSONB, nullable=False, default=list)
    confluence_required = Column(JSONB, nullable=False, default=list)
    
    # Risk management parameters
    risk_params = Column(JSONB, nullable=False, default=dict)
    
    # Learning metrics
    confidence = Column(Float, nullable=False, default=0.5)
    usage_count = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=False, default=0.0)
    avg_r_multiple = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    notes = Column(Text, nullable=False, default="")
    tags = Column(JSONB, nullable=False, default=list)
    enabled = Column(Boolean, nullable=False, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    trade_records = relationship("TradeRecord", back_populates="strategy_rule")
    learning_entries = relationship("LearningEntry", back_populates="strategy_rule")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='confidence_range'),
        CheckConstraint('win_rate >= 0.0 AND win_rate <= 1.0', name='win_rate_range'),
        CheckConstraint('usage_count >= 0', name='usage_count_positive'),
        Index('idx_strategy_rules_name_type', 'name', 'entry_type'),
        Index('idx_strategy_rules_source', 'source_type', 'source_ref'),
        Index('idx_strategy_rules_enabled', 'enabled'),
    )
    
    def __repr__(self):
        return f"<StrategyRule(id={self.id}, name='{self.name}', entry_type='{self.entry_type}')>"


class LearningEntry(Base, UUIDMixin, TimestampMixin):
    """Learning entry database model."""
    __tablename__ = "learning_entries"
    
    # Foreign key
    strategy_rule_id = Column(UUID(as_uuid=True), ForeignKey("strategy_rules.id"), nullable=False, index=True)
    
    # Learning content
    insight = Column(Text, nullable=False)
    pattern_identified = Column(String(200), nullable=False, default="")
    supporting_trades = Column(JSONB, nullable=False, default=list)  # List of trade IDs
    
    # Confidence and validation
    confidence = Column(Float, nullable=False, default=0.5)
    validation_count = Column(Integer, nullable=False, default=0)
    contradiction_count = Column(Integer, nullable=False, default=0)
    
    # Context
    market_conditions = Column(JSONB, nullable=False, default=dict)
    timeframe_context = Column(JSONB, nullable=False, default=list)
    
    # Metadata
    tags = Column(JSONB, nullable=False, default=list)
    notes = Column(Text, nullable=False, default="")
    
    # Relationships
    strategy_rule = relationship("StrategyRule", back_populates="learning_entries")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='learning_confidence_range'),
        CheckConstraint('validation_count >= 0', name='validation_count_positive'),
        CheckConstraint('contradiction_count >= 0', name='contradiction_count_positive'),
        Index('idx_learning_entries_strategy', 'strategy_rule_id'),
        Index('idx_learning_entries_confidence', 'confidence'),
    )
    
    def __repr__(self):
        return f"<LearningEntry(id={self.id}, strategy_rule_id={self.strategy_rule_id})>"


# ===== TRADE MODELS =====

class TradeRecord(Base, UUIDMixin, TimestampMixin):
    """Trade record database model."""
    __tablename__ = "trade_records"
    
    # Foreign key
    strategy_rule_id = Column(UUID(as_uuid=True), ForeignKey("strategy_rules.id"), nullable=False, index=True)
    
    # Basic trade info
    asset = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(OrderSide), nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    
    # Exit information
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True, index=True)
    exit_reason = Column(Enum(ExitReason), nullable=True)
    
    # Partial exits tracking
    partial_exits = Column(JSONB, nullable=False, default=list)
    
    # Performance metrics
    outcome = Column(Enum(TradeOutcome), nullable=False, default=TradeOutcome.PENDING, index=True)
    pnl_absolute = Column(Float, nullable=False, default=0.0)
    pnl_r_multiple = Column(Float, nullable=False, default=0.0, index=True)
    fees_paid = Column(Float, nullable=False, default=0.0)
    
    # Context and reasoning
    reasoning = Column(Text, nullable=False, default="")
    price_action_context = Column(JSONB, nullable=True)  # PriceActionSnapshot as JSON
    
    # Risk management
    initial_stop_loss = Column(Float, nullable=True)
    current_stop_loss = Column(Float, nullable=True)
    take_profit_levels = Column(JSONB, nullable=False, default=list)
    
    # Metadata
    trading_mode = Column(Enum(TradingMode), nullable=False, default=TradingMode.PAPER, index=True)
    notes = Column(Text, nullable=False, default="")
    
    # Relationships
    strategy_rule = relationship("StrategyRule", back_populates="trade_records")
    orders = relationship("Order", back_populates="trade_record")
    positions = relationship("Position", back_populates="trade_record")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('entry_price > 0', name='entry_price_positive'),
        CheckConstraint('exit_price IS NULL OR exit_price > 0', name='exit_price_positive'),
        CheckConstraint('quantity > 0', name='quantity_positive'),
        CheckConstraint('fees_paid >= 0', name='fees_positive'),
        CheckConstraint('exit_time IS NULL OR exit_time >= entry_time', name='exit_after_entry'),
        Index('idx_trade_records_strategy_asset', 'strategy_rule_id', 'asset'),
        Index('idx_trade_records_time_range', 'entry_time', 'exit_time'),
        Index('idx_trade_records_outcome_mode', 'outcome', 'trading_mode'),
    )
    
    def __repr__(self):
        return f"<TradeRecord(id={self.id}, asset='{self.asset}', outcome='{self.outcome}')>"


# ===== TRADING EXECUTION MODELS =====

class Position(Base, UUIDMixin, TimestampMixin):
    """Position database model."""
    __tablename__ = "positions"
    
    # Position details
    asset = Column(String(20), nullable=False, index=True)
    size = Column(Float, nullable=False)  # Positive for long, negative for short
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    
    # P&L tracking
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    
    # Position details
    side = Column(Enum(OrderSide), nullable=False)
    leverage = Column(Float, nullable=False, default=1.0)
    margin_used = Column(Float, nullable=False, default=0.0)
    
    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    # Foreign keys
    trade_record_id = Column(UUID(as_uuid=True), ForeignKey("trade_records.id"), nullable=True, index=True)
    
    # Relationships
    trade_record = relationship("TradeRecord", back_populates="positions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('avg_price > 0', name='avg_price_positive'),
        CheckConstraint('current_price > 0', name='current_price_positive'),
        CheckConstraint('leverage > 0 AND leverage <= 100', name='leverage_range'),
        CheckConstraint('margin_used >= 0', name='margin_used_positive'),
        CheckConstraint('stop_loss IS NULL OR stop_loss > 0', name='stop_loss_positive'),
        CheckConstraint('take_profit IS NULL OR take_profit > 0', name='take_profit_positive'),
        Index('idx_positions_asset_side', 'asset', 'side'),
    )
    
    def __repr__(self):
        return f"<Position(id={self.id}, asset='{self.asset}', size={self.size})>"


class Order(Base, UUIDMixin, TimestampMixin):
    """Order database model."""
    __tablename__ = "orders"
    
    # Order details
    asset = Column(String(20), nullable=False, index=True)
    size = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # NULL for market orders
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False, default=OrderType.MARKET)
    
    # Status tracking
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)
    filled_size = Column(Float, nullable=False, default=0.0)
    avg_fill_price = Column(Float, nullable=True)
    remaining_size = Column(Float, nullable=False, default=0.0)
    
    # Order parameters
    time_in_force = Column(String(10), nullable=False, default="GTC")
    reduce_only = Column(Boolean, nullable=False, default=False)
    post_only = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign keys
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True, index=True)
    trade_record_id = Column(UUID(as_uuid=True), ForeignKey("trade_records.id"), nullable=True, index=True)
    
    # External identifiers
    exchange_order_id = Column(String(100), nullable=True, unique=True, index=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict)
    
    # Relationships
    trade_record = relationship("TradeRecord", back_populates="orders")
    trades = relationship("Trade", back_populates="order")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('size > 0', name='order_size_positive'),
        CheckConstraint('price IS NULL OR price > 0', name='order_price_positive'),
        CheckConstraint('filled_size >= 0', name='filled_size_non_negative'),
        CheckConstraint('remaining_size >= 0', name='remaining_size_non_negative'),
        CheckConstraint('filled_size <= size', name='filled_not_exceed_size'),
        CheckConstraint('avg_fill_price IS NULL OR avg_fill_price > 0', name='avg_fill_price_positive'),
        Index('idx_orders_asset_status', 'asset', 'status'),
        Index('idx_orders_exchange_id', 'exchange_order_id'),
    )
    
    def __repr__(self):
        return f"<Order(id={self.id}, asset='{self.asset}', status='{self.status}')>"


class Trade(Base, UUIDMixin):
    """Trade execution database model."""
    __tablename__ = "trades"
    
    # Foreign key
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Trade details
    asset = Column(String(20), nullable=False, index=True)
    size = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    
    # Execution info
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    fee = Column(Float, nullable=False, default=0.0)
    fee_currency = Column(String(10), nullable=False, default="USD")
    
    # Market data at execution
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    mark_price = Column(Float, nullable=True)
    
    # External identifiers
    exchange_trade_id = Column(String(100), nullable=True, unique=True, index=True)
    position_id = Column(UUID(as_uuid=True), nullable=True)  # Not FK to avoid circular references
    
    # Relationships
    order = relationship("Order", back_populates="trades")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('size > 0', name='trade_size_positive'),
        CheckConstraint('price > 0', name='trade_price_positive'),
        CheckConstraint('fee >= 0', name='trade_fee_non_negative'),
        CheckConstraint('bid IS NULL OR bid > 0', name='bid_positive'),
        CheckConstraint('ask IS NULL OR ask > 0', name='ask_positive'),
        CheckConstraint('mark_price IS NULL OR mark_price > 0', name='mark_price_positive'),
        Index('idx_trades_asset_timestamp', 'asset', 'timestamp'),
        Index('idx_trades_exchange_id', 'exchange_trade_id'),
    )
    
    def __repr__(self):
        return f"<Trade(id={self.id}, asset='{self.asset}', size={self.size}, price={self.price})>"


# ===== MARKET DATA MODELS =====

class MarketData(Base):
    """Market data database model."""
    __tablename__ = "market_data"
    
    # Composite primary key
    asset = Column(String(20), nullable=False, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, primary_key=True, default=func.now())
    
    # Price data
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    last = Column(Float, nullable=False)
    mark_price = Column(Float, nullable=True)
    
    # Volume and statistics
    volume_24h = Column(Float, nullable=False, default=0.0)
    volume_24h_usd = Column(Float, nullable=True)
    high_24h = Column(Float, nullable=False)
    low_24h = Column(Float, nullable=False)
    change_24h = Column(Float, nullable=False, default=0.0)
    change_24h_percent = Column(Float, nullable=False, default=0.0)
    
    # Funding (for perpetuals)
    funding_rate = Column(Float, nullable=True)
    next_funding_time = Column(DateTime(timezone=True), nullable=True)
    
    # Market info
    min_order_size = Column(Float, nullable=True)
    max_order_size = Column(Float, nullable=True)
    price_precision = Column(Integer, nullable=False, default=8)
    size_precision = Column(Integer, nullable=False, default=8)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('bid > 0', name='market_bid_positive'),
        CheckConstraint('ask > 0', name='market_ask_positive'),
        CheckConstraint('last > 0', name='market_last_positive'),
        CheckConstraint('ask >= bid', name='market_spread_valid'),
        CheckConstraint('high_24h >= low_24h', name='market_24h_range_valid'),
        CheckConstraint('volume_24h >= 0', name='market_volume_non_negative'),
        CheckConstraint('price_precision >= 0 AND price_precision <= 12', name='price_precision_range'),
        CheckConstraint('size_precision >= 0 AND size_precision <= 12', name='size_precision_range'),
        Index('idx_market_data_asset_time', 'asset', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<MarketData(asset='{self.asset}', last={self.last}, timestamp={self.timestamp})>"


class CandleData(Base):
    """Candle data database model."""
    __tablename__ = "candle_data"
    
    # Composite primary key
    asset = Column(String(20), nullable=False, primary_key=True)
    timeframe = Column(Enum(Timeframe), nullable=False, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0.0)
    
    # Derived fields (computed on insert/update)
    body_size = Column(Float, nullable=True)  # abs(close - open)
    upper_wick = Column(Float, nullable=True)  # high - max(open, close)
    lower_wick = Column(Float, nullable=True)  # min(open, close) - low
    total_range = Column(Float, nullable=True)  # high - low
    is_bullish = Column(Boolean, nullable=True)  # close > open
    
    # Constraints
    __table_args__ = (
        CheckConstraint('open > 0', name='candle_open_positive'),
        CheckConstraint('high > 0', name='candle_high_positive'),
        CheckConstraint('low > 0', name='candle_low_positive'),
        CheckConstraint('close > 0', name='candle_close_positive'),
        CheckConstraint('volume >= 0', name='candle_volume_non_negative'),
        CheckConstraint('high >= open', name='candle_high_vs_open'),
        CheckConstraint('high >= close', name='candle_high_vs_close'),
        CheckConstraint('low <= open', name='candle_low_vs_open'),
        CheckConstraint('low <= close', name='candle_low_vs_close'),
        CheckConstraint('high >= low', name='candle_high_vs_low'),
        Index('idx_candle_data_asset_tf', 'asset', 'timeframe'),
        Index('idx_candle_data_time_range', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<CandleData(asset='{self.asset}', tf='{self.timeframe}', timestamp={self.timestamp})>"


# ===== BACKTESTING MODELS =====

class BacktestRun(Base, UUIDMixin, TimestampMixin):
    """Backtest run database model."""
    __tablename__ = "backtest_runs"
    
    # Configuration
    name = Column(String(100), nullable=False)
    config = Column(JSONB, nullable=False)  # BacktestConfig as JSON
    
    # Date range
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Assets and strategies
    assets = Column(JSONB, nullable=False)  # List of asset symbols
    strategy_rule_ids = Column(JSONB, nullable=False)  # List of strategy rule UUIDs
    
    # Performance metrics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=False, default=0.0)
    
    # Returns
    total_return = Column(Float, nullable=False, default=0.0)
    total_return_percent = Column(Float, nullable=False, default=0.0)
    max_drawdown = Column(Float, nullable=False, default=0.0)
    max_drawdown_percent = Column(Float, nullable=False, default=0.0)
    
    # Risk metrics
    sharpe_ratio = Column(Float, nullable=False, default=0.0)
    sortino_ratio = Column(Float, nullable=False, default=0.0)
    profit_factor = Column(Float, nullable=False, default=0.0)
    
    # R-multiple statistics
    avg_r_multiple = Column(Float, nullable=False, default=0.0)
    best_r_multiple = Column(Float, nullable=False, default=0.0)
    worst_r_multiple = Column(Float, nullable=False, default=0.0)
    
    # Trade statistics
    avg_trade_duration_hours = Column(Float, nullable=False, default=0.0)
    max_consecutive_wins = Column(Integer, nullable=False, default=0)
    max_consecutive_losses = Column(Integer, nullable=False, default=0)
    
    # Status and timing
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, error
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    
    # Results
    equity_curve = Column(JSONB, nullable=False, default=list)
    error_message = Column(Text, nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('end_date > start_date', name='backtest_date_range'),
        CheckConstraint('total_trades >= 0', name='backtest_total_trades_positive'),
        CheckConstraint('winning_trades >= 0', name='backtest_winning_trades_positive'),
        CheckConstraint('losing_trades >= 0', name='backtest_losing_trades_positive'),
        CheckConstraint('win_rate >= 0.0 AND win_rate <= 1.0', name='backtest_win_rate_range'),
        CheckConstraint('duration_seconds >= 0', name='backtest_duration_positive'),
        Index('idx_backtest_runs_status', 'status'),
        Index('idx_backtest_runs_date_range', 'start_date', 'end_date'),
    )
    
    def __repr__(self):
        return f"<BacktestRun(id={self.id}, name='{self.name}', status='{self.status}')>"


# ===== INGESTION MODELS =====

class IngestionSource(Base, UUIDMixin, TimestampMixin):
    """Ingestion source database model."""
    __tablename__ = "ingestion_sources"
    
    # Source details
    source_type = Column(Enum(SourceType), nullable=False, index=True)
    source_url = Column(String(1000), nullable=False, default="")
    local_path = Column(String(500), nullable=False, default="")
    
    # Metadata
    title = Column(String(200), nullable=False, default="")
    author = Column(String(100), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    tags = Column(JSONB, nullable=False, default=list)
    
    # Processing status
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, processing, completed, error
    error_message = Column(Text, nullable=False, default="")
    
    # Content extraction results
    extracted_text = Column(Text, nullable=False, default="")
    extracted_images = Column(JSONB, nullable=False, default=list)
    
    # Processing timestamps
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    video_frames = relationship("VideoFrame", back_populates="source", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("source_url != '' OR local_path != ''", name='source_ref_required'),
        Index('idx_ingestion_sources_type_status', 'source_type', 'status'),
    )
    
    def __repr__(self):
        return f"<IngestionSource(id={self.id}, type='{self.source_type}', status='{self.status}')>"


class VideoFrame(Base, UUIDMixin):
    """Video frame database model."""
    __tablename__ = "video_frames"
    
    # Foreign key
    source_id = Column(UUID(as_uuid=True), ForeignKey("ingestion_sources.id"), nullable=False, index=True)
    
    # Frame details
    timestamp_seconds = Column(Float, nullable=False)
    frame_path = Column(String(500), nullable=False)
    perceptual_hash = Column(String(64), nullable=False, index=True)  # For deduplication
    
    # Analysis results
    description = Column(Text, nullable=False, default="")
    contains_chart = Column(Boolean, nullable=False, default=False)
    analysis_confidence = Column(Float, nullable=False, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    source = relationship("IngestionSource", back_populates="video_frames")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('timestamp_seconds >= 0', name='frame_timestamp_positive'),
        CheckConstraint('analysis_confidence >= 0.0 AND analysis_confidence <= 1.0', name='frame_confidence_range'),
        Index('idx_video_frames_source_timestamp', 'source_id', 'timestamp_seconds'),
        Index('idx_video_frames_hash', 'perceptual_hash'),
        UniqueConstraint('source_id', 'timestamp_seconds', name='unique_frame_per_timestamp'),
    )
    
    def __repr__(self):
        return f"<VideoFrame(id={self.id}, source_id={self.source_id}, timestamp={self.timestamp_seconds})>"


# ===== PATTERN DETECTION MODELS =====

class PatternDetection(Base, UUIDMixin):
    """Pattern detection database model."""
    __tablename__ = "pattern_detections"
    
    # Detection details
    pattern_type = Column(Enum(EntryType), nullable=False, index=True)
    timeframe = Column(Enum(Timeframe), nullable=False, index=True)
    asset = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    confidence = Column(Float, nullable=False)
    
    # Pattern parameters
    candle_index = Column(Integer, nullable=False, default=0)
    pattern_data = Column(JSONB, nullable=False, default=dict)
    
    # Context
    market_structure = Column(String(100), nullable=True)
    market_cycle = Column(Enum(MarketCycle), nullable=True)
    zone_interaction = Column(String(100), nullable=True)
    
    # Signal generation
    generates_signal = Column(Boolean, nullable=False, default=False)
    signal_strength = Column(Float, nullable=False, default=0.0)
    confluence_score = Column(Float, nullable=False, default=0.0)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='pattern_confidence_range'),
        CheckConstraint('signal_strength >= 0.0 AND signal_strength <= 1.0', name='pattern_signal_range'),
        CheckConstraint('confluence_score >= 0.0 AND confluence_score <= 1.0', name='pattern_confluence_range'),
        Index('idx_pattern_detections_asset_time', 'asset', 'timestamp'),
        Index('idx_pattern_detections_type_tf', 'pattern_type', 'timeframe'),
        Index('idx_pattern_detections_signal', 'generates_signal', 'signal_strength'),
    )
    
    def __repr__(self):
        return f"<PatternDetection(id={self.id}, pattern='{self.pattern_type}', asset='{self.asset}')>"


# Create all tables function
def create_all_tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


# Export all models
__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "StrategyRule",
    "LearningEntry",
    "TradeRecord",
    "Position",
    "Order",
    "Trade",
    "MarketData",
    "CandleData",
    "BacktestRun",
    "IngestionSource",
    "VideoFrame",
    "PatternDetection",
    "create_all_tables",
]