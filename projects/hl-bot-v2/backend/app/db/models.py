"""SQLAlchemy database models."""
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, 
    ForeignKey, CheckConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class OHLCVData(Base):
    """
    OHLCV candlestick data - TimescaleDB hypertable.
    
    This table stores historical price data across multiple timeframes.
    Optimized for time-series queries using TimescaleDB.
    
    Sources:
    - 'hyperliquid': Data fetched from Hyperliquid API
    - 'csv': Data imported from CSV files
    """
    __tablename__ = "ohlcv_data"
    
    # Primary key: composite of timestamp, symbol, timeframe, and source
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False)
    timeframe = Column(String(10), primary_key=True, nullable=False)  # "5m", "15m", "1h", etc.
    source = Column(String(20), primary_key=True, nullable=False, default='csv')  # "hyperliquid", "csv"
    
    # OHLCV fields
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('high >= low', name='valid_high_low'),
        CheckConstraint('high >= open', name='valid_high_open'),
        CheckConstraint('high >= close', name='valid_high_close'),
        CheckConstraint('low <= open', name='valid_low_open'),
        CheckConstraint('low <= close', name='valid_low_close'),
        CheckConstraint('volume >= 0', name='valid_volume'),
        CheckConstraint("source IN ('hyperliquid', 'csv')", name='valid_source'),
        # Indexes for common queries
        Index('idx_ohlcv_symbol_timeframe', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_ohlcv_timestamp', 'timestamp'),
        Index('idx_ohlcv_source', 'source'),
        Index('idx_ohlcv_source_symbol_tf', 'source', 'symbol', 'timeframe', 'timestamp'),
    )


class DataSyncState(Base):
    """
    Track sync state for Hyperliquid historical data.
    
    Stores the last successful sync timestamp per symbol/timeframe combination
    to support incremental syncs.
    """
    __tablename__ = "data_sync_state"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identification
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    source = Column(String(50), nullable=False, default='hyperliquid')  # 'hyperliquid', 'csv', etc.
    
    # Sync state
    last_sync_timestamp = Column(DateTime(timezone=True))  # Last candle timestamp synced
    last_sync_at = Column(DateTime(timezone=True))  # When we last ran the sync
    oldest_timestamp = Column(DateTime(timezone=True))  # Oldest candle we have
    newest_timestamp = Column(DateTime(timezone=True))  # Newest candle we have
    candle_count = Column(Integer, default=0)
    
    # Sync status
    is_syncing = Column(Boolean, default=False)
    sync_error = Column(Text)  # Last error message if any
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sync_state_symbol_tf', 'symbol', 'timeframe', 'source', unique=True),
        Index('idx_sync_state_syncing', 'is_syncing'),
    )


class StrategyRule(Base):
    """
    Trading strategy rules extracted from content or manually created.
    """
    __tablename__ = "strategy_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    
    # Strategy parameters (stored as JSONB for flexibility)
    timeframes = Column(JSONB, nullable=False)  # ["5m", "15m", "1h"]
    market_phase = Column(String(50))  # "range", "drive", "liquidity"
    entry_conditions = Column(JSONB, nullable=False)
    exit_rules = Column(JSONB, nullable=False)
    risk_params = Column(JSONB, nullable=False)
    
    # Source tracking
    source_type = Column(String(50))  # "youtube", "pdf", "manual"
    source_url = Column(Text)
    source_metadata = Column(JSONB)
    
    # Learning metrics
    effectiveness_score = Column(Float, default=0.5)  # 0-1, updated by learning loop
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trades = relationship("Trade", back_populates="strategy", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('effectiveness_score >= 0 AND effectiveness_score <= 1', name='valid_effectiveness'),
        CheckConstraint('total_trades >= 0', name='valid_total_trades'),
        CheckConstraint('winning_trades >= 0', name='valid_winning_trades'),
        CheckConstraint('winning_trades <= total_trades', name='valid_win_ratio'),
        Index('idx_strategy_active', 'is_active'),
        Index('idx_strategy_effectiveness', 'effectiveness_score'),
    )


class Trade(Base):
    """
    Individual trade records from backtests and live trading.
    """
    __tablename__ = "trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategy_rules.id', ondelete='CASCADE'))
    
    # Trade identification
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # "long", "short"
    status = Column(String(20), nullable=False, default='open')  # "open", "tp1_hit", "stopped", "closed"
    
    # Entry
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    position_size = Column(Float, nullable=False)
    
    # Risk management
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float)
    take_profit_3 = Column(Float)
    
    # Exit
    exit_price = Column(Float)
    exit_time = Column(DateTime(timezone=True))
    
    # Performance
    pnl = Column(Float)
    pnl_percent = Column(Float)
    risk_reward_actual = Column(Float)
    
    # Context
    confluence_score = Column(Float)
    patterns_detected = Column(JSONB)  # List of pattern types detected
    setup_type = Column(String(50))  # "breakout", "pullback", etc.
    market_phase = Column(String(50))
    
    # Source
    source = Column(String(20), default='backtest')  # "backtest", "live", "paper"
    backtest_session_id = Column(UUID(as_uuid=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    strategy = relationship("StrategyRule", back_populates="trades")
    decision = relationship("TradeDecision", back_populates="trade", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("side IN ('long', 'short')", name='valid_side'),
        CheckConstraint("status IN ('open', 'tp1_hit', 'tp2_hit', 'tp3_hit', 'stopped', 'closed')", name='valid_status'),
        CheckConstraint("source IN ('backtest', 'live', 'paper')", name='valid_source'),
        CheckConstraint('position_size > 0', name='valid_position_size'),
        Index('idx_trades_symbol', 'symbol'),
        Index('idx_trades_status', 'status'),
        Index('idx_trades_entry_time', 'entry_time'),
        Index('idx_trades_strategy', 'strategy_id'),
        Index('idx_trades_backtest_session', 'backtest_session_id'),
    )


class TradeDecision(Base):
    """
    LLM reasoning and decision log for each trade.
    """
    __tablename__ = "trade_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey('trades.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Pre-trade analysis
    reasoning = Column(Text)  # Why this trade was taken
    risk_assessment = Column(Text)  # Identified risks
    confluence_explanation = Column(Text)  # Multi-TF confluence breakdown
    
    # Post-trade analysis
    outcome_analysis = Column(Text)  # What happened and why
    lessons_learned = Column(Text)  # Key takeaways
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trade = relationship("Trade", back_populates="decision")
    
    __table_args__ = (
        Index('idx_decision_trade', 'trade_id'),
    )


class LearningJournal(Base):
    """
    Aggregated learnings and insights from trade outcomes.
    """
    __tablename__ = "learning_journal"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Learning content
    insight_type = Column(String(50), nullable=False)  # "pattern", "setup", "market_phase", "risk"
    insight = Column(Text, nullable=False)
    supporting_trades = Column(JSONB)  # List of trade IDs that support this insight
    
    # Metrics
    confidence_score = Column(Float, default=0.5)  # 0-1, how confident in this insight
    sample_size = Column(Integer, default=0)  # Number of trades analyzed
    
    # Context
    market_conditions = Column(JSONB)  # When this insight applies
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='valid_confidence'),
        CheckConstraint('sample_size >= 0', name='valid_sample_size'),
        Index('idx_learning_type', 'insight_type'),
        Index('idx_learning_active', 'is_active'),
        Index('idx_learning_confidence', 'confidence_score'),
    )


class MarketStructure(Base):
    """
    Cached market structure analysis per symbol and timeframe.
    """
    __tablename__ = "market_structure"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identification
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Structure elements (stored as JSONB for flexibility)
    swing_highs = Column(JSONB)  # List of swing high points
    swing_lows = Column(JSONB)  # List of swing low points
    order_blocks = Column(JSONB)  # Identified order blocks
    fair_value_gaps = Column(JSONB)  # FVG zones
    liquidity_pools = Column(JSONB)  # Liquidity zones
    
    # Current state
    current_phase = Column(String(50))  # "drive", "range", "liquidity"
    trend_bias = Column(String(10))  # "bullish", "bearish", "neutral"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("current_phase IN ('drive', 'range', 'liquidity')", name='valid_phase'),
        CheckConstraint("trend_bias IN ('bullish', 'bearish', 'neutral')", name='valid_bias'),
        Index('idx_structure_symbol_tf', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_structure_timestamp', 'timestamp'),
    )


class Zone(Base):
    """
    Support/Resistance and Supply/Demand zones.
    """
    __tablename__ = "zones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identification
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    zone_type = Column(String(20), nullable=False)  # "support", "resistance", "demand", "supply"
    
    # Price levels
    price_low = Column(Float, nullable=False)
    price_high = Column(Float, nullable=False)
    
    # Metrics
    strength = Column(Float, default=0.5)  # 0-1, zone strength
    touches = Column(Integer, default=0)  # Number of times price touched this zone
    last_touch = Column(DateTime(timezone=True))
    
    # Status
    is_active = Column(Boolean, default=True)
    broken_at = Column(DateTime(timezone=True))  # When zone was broken (if applicable)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("zone_type IN ('support', 'resistance', 'demand', 'supply')", name='valid_zone_type'),
        CheckConstraint('price_high >= price_low', name='valid_price_range'),
        CheckConstraint('strength >= 0 AND strength <= 1', name='valid_strength'),
        CheckConstraint('touches >= 0', name='valid_touches'),
        Index('idx_zone_symbol_tf', 'symbol', 'timeframe'),
        Index('idx_zone_active', 'is_active'),
        Index('idx_zone_type', 'zone_type'),
    )
