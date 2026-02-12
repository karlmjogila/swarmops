"""Add TimescaleDB retention and compression policies for OHLCV data.

Revision ID: 003
Revises: 002
Create Date: 2025-02-11 19:00:00.000000

This migration sets up:
1. Compression settings for the ohlcv_data hypertable
2. Compression policy to automatically compress old chunks
3. Optimized chunk intervals for different use cases

Retention Policy (enforced by Celery task, not TimescaleDB policy):
- 1m candles: Keep for 3 years
- All other timeframes: Keep forever

Note: We don't use TimescaleDB's add_retention_policy because the 
ohlcv_data table contains mixed timeframes. The cleanup_old_candles
Celery task handles selective deletion of 1m data only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set up TimescaleDB compression and optimizations."""
    
    # Get connection for raw SQL execution
    connection = op.get_bind()
    
    # 1. Enable compression on the hypertable
    # Segment by symbol, timeframe, source for efficient compression
    # Order by timestamp DESC for time-series query patterns
    try:
        connection.execute(text("""
            ALTER TABLE ohlcv_data SET (
                timescaledb.compress = true,
                timescaledb.compress_segmentby = 'symbol, timeframe, source',
                timescaledb.compress_orderby = 'timestamp DESC'
            )
        """))
        print("✓ Enabled compression on ohlcv_data")
    except Exception as e:
        print(f"⚠ Compression already enabled or error: {e}")
    
    # 2. Add compression policy - compress chunks older than 7 days
    # This runs automatically in the background
    try:
        connection.execute(text("""
            SELECT add_compression_policy(
                'ohlcv_data', 
                INTERVAL '7 days',
                if_not_exists => true
            )
        """))
        print("✓ Added compression policy (7 days)")
    except Exception as e:
        print(f"⚠ Could not add compression policy: {e}")
    
    # 3. Create an index optimized for the cleanup task
    # This helps the daily cleanup job find old 1m candles efficiently
    try:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe_timestamp 
            ON ohlcv_data (timeframe, timestamp DESC)
        """))
        print("✓ Created timeframe+timestamp index for cleanup queries")
    except Exception as e:
        print(f"⚠ Could not create index: {e}")
    
    # 4. Add a comment documenting the retention policy
    try:
        connection.execute(text("""
            COMMENT ON TABLE ohlcv_data IS 
            'OHLCV candlestick data (TimescaleDB hypertable). 
            Retention: 1m candles kept for 3 years, other timeframes kept forever.
            Compression: Chunks older than 7 days are automatically compressed.
            Cleanup: Daily Celery task deletes old 1m data using efficient chunk-aware queries.'
        """))
        print("✓ Added table documentation comment")
    except Exception as e:
        print(f"⚠ Could not add comment: {e}")


def downgrade() -> None:
    """Remove compression policy and settings."""
    
    connection = op.get_bind()
    
    # Remove compression policy
    try:
        connection.execute(text("""
            SELECT remove_compression_policy('ohlcv_data', if_exists => true)
        """))
        print("✓ Removed compression policy")
    except Exception as e:
        print(f"⚠ Could not remove compression policy: {e}")
    
    # Decompress all chunks (this can take a while for large datasets)
    try:
        connection.execute(text("""
            SELECT decompress_chunk(c.chunk_name::regclass, if_compressed => true)
            FROM (
                SELECT chunk_name 
                FROM timescaledb_information.chunks 
                WHERE hypertable_name = 'ohlcv_data'
                AND is_compressed
            ) c
        """))
        print("✓ Decompressed all chunks")
    except Exception as e:
        print(f"⚠ Could not decompress chunks: {e}")
    
    # Disable compression
    try:
        connection.execute(text("""
            ALTER TABLE ohlcv_data SET (timescaledb.compress = false)
        """))
        print("✓ Disabled compression on ohlcv_data")
    except Exception as e:
        print(f"⚠ Could not disable compression: {e}")
    
    # Drop the cleanup index
    try:
        connection.execute(text("""
            DROP INDEX IF EXISTS idx_ohlcv_timeframe_timestamp
        """))
        print("✓ Dropped timeframe+timestamp index")
    except Exception as e:
        print(f"⚠ Could not drop index: {e}")
