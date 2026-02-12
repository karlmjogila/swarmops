"""Initial schema with TimescaleDB hypertable for OHLCV data

Revision ID: 001
Revises: 
Create Date: 2025-02-11 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create OHLCV data table (will be converted to TimescaleDB hypertable)
    op.create_table(
        'ohlcv_data',
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('timestamp', 'symbol', 'timeframe'),
        sa.CheckConstraint('high >= low', name='valid_high_low'),
        sa.CheckConstraint('high >= open', name='valid_high_open'),
        sa.CheckConstraint('high >= close', name='valid_high_close'),
        sa.CheckConstraint('low <= open', name='valid_low_open'),
        sa.CheckConstraint('low <= close', name='valid_low_close'),
        sa.CheckConstraint('volume >= 0', name='valid_volume'),
    )
    op.create_index('idx_ohlcv_symbol_timeframe', 'ohlcv_data', ['symbol', 'timeframe', 'timestamp'])
    op.create_index('idx_ohlcv_timestamp', 'ohlcv_data', ['timestamp'])
    
    # Convert to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable('ohlcv_data', 'timestamp', 
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)
    
    # Create strategy_rules table
    op.create_table(
        'strategy_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('timeframes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('market_phase', sa.String(length=50), nullable=True),
        sa.Column('entry_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('exit_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('risk_params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effectiveness_score', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('total_trades', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.CheckConstraint('effectiveness_score >= 0 AND effectiveness_score <= 1', name='valid_effectiveness'),
        sa.CheckConstraint('total_trades >= 0', name='valid_total_trades'),
        sa.CheckConstraint('winning_trades >= 0', name='valid_winning_trades'),
        sa.CheckConstraint('winning_trades <= total_trades', name='valid_win_ratio'),
    )
    op.create_index('idx_strategy_active', 'strategy_rules', ['is_active'])
    op.create_index('idx_strategy_effectiveness', 'strategy_rules', ['effectiveness_score'])
    
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('position_size', sa.Float(), nullable=False),
        sa.Column('stop_loss', sa.Float(), nullable=False),
        sa.Column('take_profit_1', sa.Float(), nullable=False),
        sa.Column('take_profit_2', sa.Float(), nullable=True),
        sa.Column('take_profit_3', sa.Float(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('risk_reward_actual', sa.Float(), nullable=True),
        sa.Column('confluence_score', sa.Float(), nullable=True),
        sa.Column('patterns_detected', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('setup_type', sa.String(length=50), nullable=True),
        sa.Column('market_phase', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=True, server_default='backtest'),
        sa.Column('backtest_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategy_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("side IN ('long', 'short')", name='valid_side'),
        sa.CheckConstraint("status IN ('open', 'tp1_hit', 'tp2_hit', 'tp3_hit', 'stopped', 'closed')", name='valid_status'),
        sa.CheckConstraint("source IN ('backtest', 'live', 'paper')", name='valid_source'),
        sa.CheckConstraint('position_size > 0', name='valid_position_size'),
    )
    op.create_index('idx_trades_symbol', 'trades', ['symbol'])
    op.create_index('idx_trades_status', 'trades', ['status'])
    op.create_index('idx_trades_entry_time', 'trades', ['entry_time'])
    op.create_index('idx_trades_strategy', 'trades', ['strategy_id'])
    op.create_index('idx_trades_backtest_session', 'trades', ['backtest_session_id'])
    
    # Create trade_decisions table
    op.create_table(
        'trade_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('risk_assessment', sa.Text(), nullable=True),
        sa.Column('confluence_explanation', sa.Text(), nullable=True),
        sa.Column('outcome_analysis', sa.Text(), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_id'),
    )
    op.create_index('idx_decision_trade', 'trade_decisions', ['trade_id'])
    
    # Create learning_journal table
    op.create_table(
        'learning_journal',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('insight', sa.Text(), nullable=False),
        sa.Column('supporting_trades', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('sample_size', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('market_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='valid_confidence'),
        sa.CheckConstraint('sample_size >= 0', name='valid_sample_size'),
    )
    op.create_index('idx_learning_type', 'learning_journal', ['insight_type'])
    op.create_index('idx_learning_active', 'learning_journal', ['is_active'])
    op.create_index('idx_learning_confidence', 'learning_journal', ['confidence_score'])
    
    # Create market_structure table
    op.create_table(
        'market_structure',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('swing_highs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('swing_lows', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('order_blocks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('fair_value_gaps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('liquidity_pools', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_phase', sa.String(length=50), nullable=True),
        sa.Column('trend_bias', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("current_phase IN ('drive', 'range', 'liquidity')", name='valid_phase'),
        sa.CheckConstraint("trend_bias IN ('bullish', 'bearish', 'neutral')", name='valid_bias'),
    )
    op.create_index('idx_structure_symbol_tf', 'market_structure', ['symbol', 'timeframe', 'timestamp'])
    op.create_index('idx_structure_timestamp', 'market_structure', ['timestamp'])
    
    # Create zones table
    op.create_table(
        'zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('zone_type', sa.String(length=20), nullable=False),
        sa.Column('price_low', sa.Float(), nullable=False),
        sa.Column('price_high', sa.Float(), nullable=False),
        sa.Column('strength', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('touches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_touch', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('broken_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("zone_type IN ('support', 'resistance', 'demand', 'supply')", name='valid_zone_type'),
        sa.CheckConstraint('price_high >= price_low', name='valid_price_range'),
        sa.CheckConstraint('strength >= 0 AND strength <= 1', name='valid_strength'),
        sa.CheckConstraint('touches >= 0', name='valid_touches'),
    )
    op.create_index('idx_zone_symbol_tf', 'zones', ['symbol', 'timeframe'])
    op.create_index('idx_zone_active', 'zones', ['is_active'])
    op.create_index('idx_zone_type', 'zones', ['zone_type'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('zones')
    op.drop_table('market_structure')
    op.drop_table('learning_journal')
    op.drop_table('trade_decisions')
    op.drop_table('trades')
    op.drop_table('strategy_rules')
    op.drop_table('ohlcv_data')
