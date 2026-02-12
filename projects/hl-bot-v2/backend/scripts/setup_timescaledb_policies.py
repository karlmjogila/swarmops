#!/usr/bin/env python3
"""Set up TimescaleDB compression and retention policies.

This script can be run manually to set up or verify TimescaleDB policies.
It's also run automatically via the Alembic migration.

Usage:
    python scripts/setup_timescaledb_policies.py

Requirements:
    - TimescaleDB extension must be installed and enabled
    - ohlcv_data table must exist as a hypertable
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings


def setup_compression(conn):
    """Enable compression on ohlcv_data hypertable."""
    print("\n1. Setting up compression...")
    
    # Check if compression is already enabled
    result = conn.execute(text("""
        SELECT * FROM timescaledb_information.compression_settings 
        WHERE hypertable_name = 'ohlcv_data'
    """)).fetchone()
    
    if result:
        print("   ✓ Compression already enabled")
        return True
    
    # Enable compression
    try:
        conn.execute(text("""
            ALTER TABLE ohlcv_data SET (
                timescaledb.compress = true,
                timescaledb.compress_segmentby = 'symbol, timeframe, source',
                timescaledb.compress_orderby = 'timestamp DESC'
            )
        """))
        conn.commit()
        print("   ✓ Enabled compression on ohlcv_data")
        return True
    except Exception as e:
        print(f"   ✗ Failed to enable compression: {e}")
        return False


def setup_compression_policy(conn, days: int = 7):
    """Add automatic compression policy."""
    print(f"\n2. Setting up compression policy (compress after {days} days)...")
    
    # Check existing policy
    result = conn.execute(text("""
        SELECT * FROM timescaledb_information.jobs 
        WHERE hypertable_name = 'ohlcv_data' 
        AND proc_name = 'policy_compression'
    """)).fetchone()
    
    if result:
        print("   ✓ Compression policy already exists")
        return True
    
    try:
        conn.execute(text(f"""
            SELECT add_compression_policy(
                'ohlcv_data', 
                INTERVAL '{days} days',
                if_not_exists => true
            )
        """))
        conn.commit()
        print(f"   ✓ Added compression policy")
        return True
    except Exception as e:
        print(f"   ✗ Failed to add compression policy: {e}")
        return False


def create_cleanup_index(conn):
    """Create index optimized for retention cleanup."""
    print("\n3. Creating cleanup-optimized index...")
    
    try:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe_timestamp 
            ON ohlcv_data (timeframe, timestamp DESC)
        """))
        conn.commit()
        print("   ✓ Created idx_ohlcv_timeframe_timestamp")
        return True
    except Exception as e:
        print(f"   ✗ Failed to create index: {e}")
        return False


def show_hypertable_info(conn):
    """Display current hypertable configuration."""
    print("\n4. Current hypertable configuration:")
    
    # Hypertable info
    result = conn.execute(text("""
        SELECT 
            hypertable_name,
            num_chunks,
            table_bytes,
            index_bytes,
            toast_bytes,
            total_bytes,
            pg_size_pretty(total_bytes) as total_size
        FROM timescaledb_information.hypertable_size('ohlcv_data')
    """)).fetchone()
    
    if result:
        print(f"   Table: {result[0]}")
        print(f"   Chunks: {result[1]}")
        print(f"   Total size: {result[6]}")
    
    # Compression stats
    result = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE is_compressed) as compressed,
            COUNT(*) FILTER (WHERE NOT is_compressed) as uncompressed,
            COUNT(*) as total
        FROM timescaledb_information.chunks 
        WHERE hypertable_name = 'ohlcv_data'
    """)).fetchone()
    
    if result:
        print(f"   Compressed chunks: {result[0]} / {result[2]}")
        print(f"   Uncompressed chunks: {result[1]} / {result[2]}")
    
    # Scheduled jobs
    print("\n   Scheduled jobs:")
    jobs = conn.execute(text("""
        SELECT proc_name, schedule_interval, next_start
        FROM timescaledb_information.jobs 
        WHERE hypertable_name = 'ohlcv_data'
    """)).fetchall()
    
    for job in jobs:
        print(f"     - {job[0]}: interval={job[1]}, next_run={job[2]}")
    
    if not jobs:
        print("     (no scheduled jobs)")


def show_data_summary(conn):
    """Display data summary by timeframe."""
    print("\n5. Data summary by timeframe:")
    
    result = conn.execute(text("""
        SELECT 
            timeframe,
            COUNT(*) as candle_count,
            MIN(timestamp) as oldest,
            MAX(timestamp) as newest,
            COUNT(DISTINCT symbol) as symbols
        FROM ohlcv_data
        GROUP BY timeframe
        ORDER BY 
            CASE timeframe
                WHEN '1m' THEN 1
                WHEN '5m' THEN 2
                WHEN '15m' THEN 3
                WHEN '30m' THEN 4
                WHEN '1h' THEN 5
                WHEN '4h' THEN 6
                WHEN '1d' THEN 7
                WHEN '1w' THEN 8
                WHEN '1M' THEN 9
                ELSE 10
            END
    """)).fetchall()
    
    if result:
        print(f"   {'Timeframe':<10} {'Candles':>12} {'Symbols':>8} {'Oldest':<20} {'Newest':<20}")
        print("   " + "-" * 72)
        for row in result:
            oldest = row[2].strftime('%Y-%m-%d %H:%M') if row[2] else 'N/A'
            newest = row[3].strftime('%Y-%m-%d %H:%M') if row[3] else 'N/A'
            print(f"   {row[0]:<10} {row[1]:>12,} {row[4]:>8} {oldest:<20} {newest:<20}")
    else:
        print("   (no data)")


def main():
    """Main entry point."""
    print("=" * 60)
    print("TimescaleDB Policy Setup for HL-Bot OHLCV Data")
    print("=" * 60)
    
    print(f"\nConnecting to database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check if TimescaleDB is available
        result = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")).fetchone()
        if not result:
            print("\n✗ TimescaleDB extension not found! Please install it first.")
            sys.exit(1)
        print(f"\n✓ TimescaleDB version: {result[0]}")
        
        # Check if ohlcv_data is a hypertable
        result = conn.execute(text("""
            SELECT hypertable_name FROM timescaledb_information.hypertables 
            WHERE hypertable_name = 'ohlcv_data'
        """)).fetchone()
        if not result:
            print("\n✗ ohlcv_data is not a hypertable! Please run migrations first.")
            sys.exit(1)
        print("✓ ohlcv_data hypertable exists")
        
        # Set up policies
        setup_compression(conn)
        setup_compression_policy(conn, days=settings.hl_compression_after_days)
        create_cleanup_index(conn)
        show_hypertable_info(conn)
        show_data_summary(conn)
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    
    print("\nRetention Policy Summary:")
    print(f"  • 1m candles: Kept for {settings.hl_retention_1m_days} days ({settings.hl_retention_1m_days // 365} years)")
    print("  • Other timeframes (5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M): Kept FOREVER")
    print(f"\nCompression: Chunks older than {settings.hl_compression_after_days} days are compressed automatically")
    print("\nScheduled Tasks (via Celery Beat):")
    print("  • Hourly: sync_hyperliquid_hourly (fetch all timeframes)")
    print("  • Daily: cleanup_old_candles (delete 1m candles older than 3 years)")
    print("  • Weekly: run_timescaledb_maintenance (compress chunks, update stats)")


if __name__ == "__main__":
    main()
