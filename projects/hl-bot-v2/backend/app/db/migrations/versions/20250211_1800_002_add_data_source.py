"""Add data source column to OHLCV data.

Revision ID: 002_add_data_source
Revises: 001_initial_schema
Create Date: 2025-02-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source column to ohlcv_data table."""
    # Add source column with default 'csv' for existing data
    op.add_column(
        'ohlcv_data',
        sa.Column(
            'source',
            sa.String(20),
            nullable=False,
            server_default='csv'
        )
    )
    
    # Add index for source queries
    op.create_index(
        'idx_ohlcv_source',
        'ohlcv_data',
        ['source']
    )
    
    # Add composite index for source + symbol + timeframe queries
    op.create_index(
        'idx_ohlcv_source_symbol_tf',
        'ohlcv_data',
        ['source', 'symbol', 'timeframe', 'timestamp']
    )
    
    # Add check constraint for valid source values
    op.create_check_constraint(
        'valid_source',
        'ohlcv_data',
        "source IN ('hyperliquid', 'csv')"
    )


def downgrade() -> None:
    """Remove source column from ohlcv_data table."""
    op.drop_constraint('valid_source', 'ohlcv_data', type_='check')
    op.drop_index('idx_ohlcv_source_symbol_tf', table_name='ohlcv_data')
    op.drop_index('idx_ohlcv_source', table_name='ohlcv_data')
    op.drop_column('ohlcv_data', 'source')
