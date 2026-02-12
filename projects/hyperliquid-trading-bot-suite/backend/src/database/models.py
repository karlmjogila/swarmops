"""
SQLAlchemy database models for the Hyperliquid Trading Bot Suite.
These models define the database schema and relationships.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, 
    String, Text, JSON, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from ..types import (
    EntryType, PatternType, Timeframe, MarketCycle,
    TradeDirection, TradeOutcome, ExitReason, SourceType
)

Base = declarative_base()


class TimestampMixin:
    """Mixin for adding timestamp fields."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class StrategyRuleDB(Base, TimestampMixin):
    """Database model for strategy rules."""
    __tablename__ = 'strategy_rules'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(200), nullable=False, index=True)
    
    # Source information
    source_type = Column(String(20), nullable=False)  # SourceType enum
    source_ref = Column(String(500), nullable=False)
    source_timestamp = Column(Float, nullable=True)  # For video content
    source_page_number = Column(Integer, nullable=True)  # For PDF content
    
    # Strategy details
    entry_type = Column(String(20), nullable=False, index=True)  # EntryType enum
    conditions = Column(JSON, nullable=False)  # List of PatternCondition dicts
    confluence_required = Column(JSON, default=list)  # List of TimeframeAlignment dicts
    risk_params = Column(JSON, nullable=False)  # RiskParameters dict
    
    # Performance tracking
    confidence = Column(Float, default=0.5, nullable=False)
    last_used = Column(DateTime, nullable=True)
    trade_count = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, nullable=True)
    avg_r_multiple = Column(Float, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), default=list)
    
    # Relationships
    trades = relationship("TradeRecordDB", back_populates="strategy_rule")
    learning_entries = relationship("LearningEntryDB", back_populates="strategy_rule")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_confidence_range'),
        CheckConstraint('trade_count >= 0', name='check_trade_count_positive'),
        CheckConstraint('win_rate IS NULL OR (win_rate >= 0 AND win_rate <= 1)', name='check_win_rate_range'),
        Index('idx_strategy_entry_type', 'entry_type'),
        Index('idx_strategy_source_type', 'source_type'),
        Index('idx_strategy_confidence', 'confidence'),
    )

    @validates('source_type')
    def validate_source_type(self, key, source_type):
        if source_type not in [e.value for e in SourceType]:
            raise ValueError(f"Invalid source_type: {source_type}")
        return source_type

    @validates('entry_type')
    def validate_entry_type(self, key, entry_type):
        if entry_type not in [e.value for e in EntryType]:
            raise ValueError(f"Invalid entry_type: {entry_type}")
        return entry_type


class TradeRecordDB(Base, TimestampMixin):
    """Database model for trade records."""
    __tablename__ = 'trade_records'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    strategy_rule_id = Column(String, ForeignKey('strategy_rules.id'), nullable=False, index=True)
    
    # Trade details
    asset = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # TradeDirection enum
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    exit_reason = Column(String(20), nullable=True)  # ExitReason enum
    outcome = Column(String(20), default=TradeOutcome.PENDING.value, nullable=False, index=True)
    
    # P&L and sizing
    pnl_r = Column(Float, nullable=True)  # P&L in R multiples
    pnl_usd = Column(Float, nullable=True)  # P&L in USD
    position_size = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit_levels = Column(ARRAY(Float), default=list)
    fees_usd = Column(Float, nullable=True)
    
    # Context and reasoning
    reasoning = Column(Text, nullable=False)
    price_action_context = Column(JSON, nullable=False)  # PriceActionSnapshot dict
    confidence = Column(Float, nullable=False)
    
    # Metadata
    is_backtest = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    strategy_rule = relationship("StrategyRuleDB", back_populates="trades")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('entry_price > 0', name='check_entry_price_positive'),
        CheckConstraint('exit_price IS NULL OR exit_price > 0', name='check_exit_price_positive'),
        CheckConstraint('position_size > 0', name='check_position_size_positive'),
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_trade_confidence_range'),
        CheckConstraint('fees_usd IS NULL OR fees_usd >= 0', name='check_fees_positive'),
        Index('idx_trade_asset_time', 'asset', 'entry_time'),
        Index('idx_trade_outcome_backtest', 'outcome', 'is_backtest'),
        Index('idx_trade_direction_time', 'direction', 'entry_time'),
    )

    @validates('direction')
    def validate_direction(self, key, direction):
        if direction not in [e.value for e in TradeDirection]:
            raise ValueError(f"Invalid direction: {direction}")
        return direction

    @validates('outcome')
    def validate_outcome(self, key, outcome):
        if outcome not in [e.value for e in TradeOutcome]:
            raise ValueError(f"Invalid outcome: {outcome}")
        return outcome

    @validates('exit_reason')
    def validate_exit_reason(self, key, exit_reason):
        if exit_reason is not None and exit_reason not in [e.value for e in ExitReason]:
            raise ValueError(f"Invalid exit_reason: {exit_reason}")
        return exit_reason


class LearningEntryDB(Base, TimestampMixin):
    """Database model for learning insights."""
    __tablename__ = 'learning_entries'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    strategy_rule_id = Column(String, ForeignKey('strategy_rules.id'), nullable=True, index=True)
    
    # Learning content
    insight = Column(Text, nullable=False)
    supporting_trades = Column(ARRAY(String), default=list)  # Trade IDs
    confidence = Column(Float, nullable=False)
    impact_type = Column(String(50), nullable=False, index=True)
    market_conditions = Column(JSON, nullable=True)
    
    # Validation tracking
    last_validated = Column(DateTime, nullable=True)
    validation_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    strategy_rule = relationship("StrategyRuleDB", back_populates="learning_entries")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_learning_confidence_range'),
        CheckConstraint('validation_count >= 0', name='check_validation_count_positive'),
        CheckConstraint('LENGTH(insight) >= 10', name='check_insight_min_length'),
        Index('idx_learning_impact_confidence', 'impact_type', 'confidence'),
    )


class CandleDataDB(Base):
    """Database model for candle/price data."""
    __tablename__ = 'candle_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False) 
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('open > 0', name='check_open_positive'),
        CheckConstraint('high > 0', name='check_high_positive'),
        CheckConstraint('low > 0', name='check_low_positive'),
        CheckConstraint('close > 0', name='check_close_positive'),
        CheckConstraint('volume >= 0', name='check_volume_positive'),
        CheckConstraint('high >= low', name='check_high_low_relationship'),
        CheckConstraint('high >= open', name='check_high_open_relationship'),
        CheckConstraint('high >= close', name='check_high_close_relationship'),
        CheckConstraint('low <= open', name='check_low_open_relationship'),
        CheckConstraint('low <= close', name='check_low_close_relationship'),
        UniqueConstraint('asset', 'timeframe', 'timestamp', name='unique_candle'),
        Index('idx_candle_asset_timeframe_time', 'asset', 'timeframe', 'timestamp'),
    )

    @validates('timeframe')
    def validate_timeframe(self, key, timeframe):
        if timeframe not in [e.value for e in Timeframe]:
            raise ValueError(f"Invalid timeframe: {timeframe}")
        return timeframe


class BacktestConfigDB(Base, TimestampMixin):
    """Database model for backtest configurations."""
    __tablename__ = 'backtest_configs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(200), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Float, nullable=False)
    
    # Configuration
    strategy_rule_ids = Column(ARRAY(String), nullable=False)
    assets = Column(ARRAY(String), nullable=False)
    timeframes = Column(ARRAY(String), nullable=False)
    risk_per_trade = Column(Float, default=2.0, nullable=False)
    max_concurrent_positions = Column(Integer, default=3, nullable=False)
    
    # Relationships
    results = relationship("BacktestResultDB", back_populates="config")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('end_date > start_date', name='check_backtest_date_range'),
        CheckConstraint('initial_balance > 0', name='check_initial_balance_positive'),
        CheckConstraint('risk_per_trade > 0 AND risk_per_trade <= 100', name='check_risk_per_trade_range'),
        CheckConstraint('max_concurrent_positions > 0', name='check_max_positions_positive'),
        CheckConstraint('ARRAY_LENGTH(strategy_rule_ids, 1) > 0', name='check_strategy_rules_not_empty'),
        CheckConstraint('ARRAY_LENGTH(assets, 1) > 0', name='check_assets_not_empty'),
    )


class BacktestResultDB(Base, TimestampMixin):
    """Database model for backtest results."""
    __tablename__ = 'backtest_results'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    backtest_config_id = Column(String, ForeignKey('backtest_configs.id'), nullable=False, index=True)
    
    # Performance metrics
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)
    final_balance = Column(Float, nullable=False)
    
    # Detailed results
    equity_curve = Column(JSON, default=list)  # List of {timestamp, balance} points
    completed_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    
    # Relationships
    config = relationship("BacktestConfigDB", back_populates="results")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('total_trades >= 0', name='check_total_trades_positive'),
        CheckConstraint('winning_trades >= 0', name='check_winning_trades_positive'),
        CheckConstraint('losing_trades >= 0', name='check_losing_trades_positive'),
        CheckConstraint('winning_trades + losing_trades <= total_trades', name='check_trade_counts_consistent'),
        CheckConstraint('win_rate >= 0 AND win_rate <= 1', name='check_win_rate_range'),
        CheckConstraint('max_drawdown >= 0 AND max_drawdown <= 1', name='check_max_drawdown_range'),
        CheckConstraint('final_balance > 0', name='check_final_balance_positive'),
        CheckConstraint('profit_factor IS NULL OR profit_factor >= 0', name='check_profit_factor_positive'),
    )


class IngestionTaskDB(Base, TimestampMixin):
    """Database model for tracking ingestion tasks."""
    __tablename__ = 'ingestion_tasks'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    source_type = Column(String(20), nullable=False, index=True)
    source_ref = Column(String(500), nullable=False)
    status = Column(String(20), default='pending', nullable=False, index=True)
    
    # Task details
    strategy_name = Column(String(200), nullable=True)
    tags = Column(ARRAY(String), default=list)
    extract_frames = Column(Boolean, default=True, nullable=False)
    
    # Results
    strategy_rules_created = Column(ARRAY(String), default=list)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name='check_task_status'),
        Index('idx_ingestion_status_time', 'status', 'created_at'),
    )

    @validates('source_type')
    def validate_source_type(self, key, source_type):
        if source_type not in [e.value for e in SourceType]:
            raise ValueError(f"Invalid source_type: {source_type}")
        return source_type


# Create indexes for frequently queried columns
def create_additional_indexes(engine):
    """Create additional indexes for performance optimization."""
    from sqlalchemy import text
    
    # Composite indexes for common query patterns  
    indexes = [
        # Strategy rules by performance
        "CREATE INDEX IF NOT EXISTS idx_strategy_performance ON strategy_rules(confidence DESC, win_rate DESC, trade_count DESC)",
        
        # Trades by time and asset
        "CREATE INDEX IF NOT EXISTS idx_trades_time_asset ON trade_records(entry_time DESC, asset, is_backtest)",
        
        # Learning entries by validation
        "CREATE INDEX IF NOT EXISTS idx_learning_validation ON learning_entries(validation_count DESC, confidence DESC)",
        
        # Candle data for time series queries
        "CREATE INDEX IF NOT EXISTS idx_candle_timeseries ON candle_data(asset, timeframe, timestamp DESC)",
        
        # Full-text search on strategy names and descriptions (commented out due to complexity)
        # "CREATE INDEX IF NOT EXISTS idx_strategy_search ON strategy_rules USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')))",
    ]
    
    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception as e:
                print(f"Error creating index: {e}")
                conn.rollback()


__all__ = [
    "Base",
    "TimestampMixin", 
    "StrategyRuleDB",
    "TradeRecordDB",
    "LearningEntryDB",
    "CandleDataDB",
    "BacktestConfigDB",
    "BacktestResultDB",
    "IngestionTaskDB",
    "create_additional_indexes",
]