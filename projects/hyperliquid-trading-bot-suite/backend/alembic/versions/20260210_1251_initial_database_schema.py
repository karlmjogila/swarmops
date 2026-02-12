"""Initial database schema

Revision ID: 20260210_1251
Revises: 
Create Date: 2026-02-10 12:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260210_1251'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create strategy_rules table
    op.create_table(
        'strategy_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_ref', sa.String(length=500), nullable=False),
        sa.Column('source_timestamp', sa.Float(), nullable=True),
        sa.Column('source_page_number', sa.Integer(), nullable=True),
        sa.Column('entry_type', sa.String(length=20), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('confluence_required', sa.JSON(), nullable=True),
        sa.Column('risk_params', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('trade_count', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('avg_r_multiple', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_confidence_range'),
        sa.CheckConstraint('trade_count >= 0', name='check_trade_count_positive'),
        sa.CheckConstraint('win_rate IS NULL OR (win_rate >= 0 AND win_rate <= 1)', name='check_win_rate_range'),
    )
    
    # Create indexes for strategy_rules
    op.create_index('idx_strategy_entry_type', 'strategy_rules', ['entry_type'])
    op.create_index('idx_strategy_source_type', 'strategy_rules', ['source_type'])
    op.create_index('idx_strategy_confidence', 'strategy_rules', ['confidence'])
    op.create_index(op.f('ix_strategy_rules_name'), 'strategy_rules', ['name'])

    # Create trade_records table
    op.create_table(
        'trade_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_rule_id', sa.String(), nullable=False),
        sa.Column('asset', sa.String(length=20), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('exit_reason', sa.String(length=20), nullable=True),
        sa.Column('outcome', sa.String(length=20), nullable=False),
        sa.Column('pnl_r', sa.Float(), nullable=True),
        sa.Column('pnl_usd', sa.Float(), nullable=True),
        sa.Column('position_size', sa.Float(), nullable=False),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('take_profit_levels', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('fees_usd', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('price_action_context', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('is_backtest', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_rule_id'], ['strategy_rules.id'], ),
        sa.CheckConstraint('entry_price > 0', name='check_entry_price_positive'),
        sa.CheckConstraint('exit_price IS NULL OR exit_price > 0', name='check_exit_price_positive'),
        sa.CheckConstraint('position_size > 0', name='check_position_size_positive'),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_trade_confidence_range'),
        sa.CheckConstraint('fees_usd IS NULL OR fees_usd >= 0', name='check_fees_positive'),
    )

    # Create indexes for trade_records
    op.create_index('idx_strategy_rule_id', 'trade_records', ['strategy_rule_id'])
    op.create_index('idx_trade_asset_time', 'trade_records', ['asset', 'entry_time'])
    op.create_index('idx_trade_outcome_backtest', 'trade_records', ['outcome', 'is_backtest'])
    op.create_index('idx_trade_direction_time', 'trade_records', ['direction', 'entry_time'])
    op.create_index(op.f('ix_trade_records_asset'), 'trade_records', ['asset'])
    op.create_index(op.f('ix_trade_records_entry_time'), 'trade_records', ['entry_time'])
    op.create_index(op.f('ix_trade_records_is_backtest'), 'trade_records', ['is_backtest'])
    op.create_index(op.f('ix_trade_records_outcome'), 'trade_records', ['outcome'])

    # Create learning_entries table
    op.create_table(
        'learning_entries',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_rule_id', sa.String(), nullable=True),
        sa.Column('insight', sa.Text(), nullable=False),
        sa.Column('supporting_trades', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('impact_type', sa.String(length=50), nullable=False),
        sa.Column('market_conditions', sa.JSON(), nullable=True),
        sa.Column('last_validated', sa.DateTime(), nullable=True),
        sa.Column('validation_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_rule_id'], ['strategy_rules.id'], ),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_learning_confidence_range'),
        sa.CheckConstraint('validation_count >= 0', name='check_validation_count_positive'),
        sa.CheckConstraint('LENGTH(insight) >= 10', name='check_insight_min_length'),
    )

    # Create indexes for learning_entries
    op.create_index('idx_learning_strategy_rule_id', 'learning_entries', ['strategy_rule_id'])
    op.create_index('idx_learning_impact_confidence', 'learning_entries', ['impact_type', 'confidence'])
    op.create_index(op.f('ix_learning_entries_impact_type'), 'learning_entries', ['impact_type'])

    # Create candle_data table
    op.create_table(
        'candle_data',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset', 'timeframe', 'timestamp', name='unique_candle'),
        sa.CheckConstraint('open > 0', name='check_open_positive'),
        sa.CheckConstraint('high > 0', name='check_high_positive'),
        sa.CheckConstraint('low > 0', name='check_low_positive'),
        sa.CheckConstraint('close > 0', name='check_close_positive'),
        sa.CheckConstraint('volume >= 0', name='check_volume_positive'),
        sa.CheckConstraint('high >= low', name='check_high_low_relationship'),
        sa.CheckConstraint('high >= open', name='check_high_open_relationship'),
        sa.CheckConstraint('high >= close', name='check_high_close_relationship'),
        sa.CheckConstraint('low <= open', name='check_low_open_relationship'),
        sa.CheckConstraint('low <= close', name='check_low_close_relationship'),
    )

    # Create indexes for candle_data
    op.create_index('idx_candle_asset_timeframe_time', 'candle_data', ['asset', 'timeframe', 'timestamp'])
    op.create_index(op.f('ix_candle_data_asset'), 'candle_data', ['asset'])
    op.create_index(op.f('ix_candle_data_timeframe'), 'candle_data', ['timeframe'])

    # Create backtest_configs table
    op.create_table(
        'backtest_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('initial_balance', sa.Float(), nullable=False),
        sa.Column('strategy_rule_ids', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('assets', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('timeframes', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('risk_per_trade', sa.Float(), nullable=False),
        sa.Column('max_concurrent_positions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('end_date > start_date', name='check_backtest_date_range'),
        sa.CheckConstraint('initial_balance > 0', name='check_initial_balance_positive'),
        sa.CheckConstraint('risk_per_trade > 0 AND risk_per_trade <= 100', name='check_risk_per_trade_range'),
        sa.CheckConstraint('max_concurrent_positions > 0', name='check_max_positions_positive'),
        sa.CheckConstraint('ARRAY_LENGTH(strategy_rule_ids, 1) > 0', name='check_strategy_rules_not_empty'),
        sa.CheckConstraint('ARRAY_LENGTH(assets, 1) > 0', name='check_assets_not_empty'),
    )

    # Create backtest_results table
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('backtest_config_id', sa.String(), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('total_return', sa.Float(), nullable=False),
        sa.Column('max_drawdown', sa.Float(), nullable=False),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('sortino_ratio', sa.Float(), nullable=True),
        sa.Column('calmar_ratio', sa.Float(), nullable=True),
        sa.Column('final_balance', sa.Float(), nullable=False),
        sa.Column('equity_curve', sa.JSON(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['backtest_config_id'], ['backtest_configs.id'], ),
        sa.CheckConstraint('total_trades >= 0', name='check_total_trades_positive'),
        sa.CheckConstraint('winning_trades >= 0', name='check_winning_trades_positive'),
        sa.CheckConstraint('losing_trades >= 0', name='check_losing_trades_positive'),
        sa.CheckConstraint('winning_trades + losing_trades <= total_trades', name='check_trade_counts_consistent'),
        sa.CheckConstraint('win_rate >= 0 AND win_rate <= 1', name='check_win_rate_range'),
        sa.CheckConstraint('max_drawdown >= 0 AND max_drawdown <= 1', name='check_max_drawdown_range'),
        sa.CheckConstraint('final_balance > 0', name='check_final_balance_positive'),
        sa.CheckConstraint('profit_factor IS NULL OR profit_factor >= 0', name='check_profit_factor_positive'),
    )

    # Create indexes for backtest_results
    op.create_index('idx_backtest_config_id', 'backtest_results', ['backtest_config_id'])

    # Create ingestion_tasks table
    op.create_table(
        'ingestion_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_ref', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('strategy_name', sa.String(length=200), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('extract_frames', sa.Boolean(), nullable=False),
        sa.Column('strategy_rules_created', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name='check_task_status'),
    )

    # Create indexes for ingestion_tasks
    op.create_index('idx_ingestion_source_type', 'ingestion_tasks', ['source_type'])
    op.create_index('idx_ingestion_status', 'ingestion_tasks', ['status'])
    op.create_index('idx_ingestion_status_time', 'ingestion_tasks', ['status', 'created_at'])

    # Create additional performance indexes
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_strategy_performance 
        ON strategy_rules(confidence DESC, win_rate DESC, trade_count DESC)
    ''')
    
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_trades_time_asset 
        ON trade_records(entry_time DESC, asset, is_backtest)
    ''')
    
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_learning_validation 
        ON learning_entries(validation_count DESC, confidence DESC)
    ''')
    
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_candle_timeseries 
        ON candle_data(asset, timeframe, timestamp DESC)
    ''')


def downgrade() -> None:
    """Drop all tables."""
    # Drop performance indexes first
    op.execute('DROP INDEX IF EXISTS idx_candle_timeseries')
    op.execute('DROP INDEX IF EXISTS idx_learning_validation')
    op.execute('DROP INDEX IF EXISTS idx_trades_time_asset')
    op.execute('DROP INDEX IF EXISTS idx_strategy_performance')
    
    # Drop tables in reverse dependency order
    op.drop_table('ingestion_tasks')
    op.drop_table('backtest_results')
    op.drop_table('backtest_configs')
    op.drop_table('candle_data')
    op.drop_table('learning_entries')
    op.drop_table('trade_records')
    op.drop_table('strategy_rules')