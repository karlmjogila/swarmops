#!/usr/bin/env python3
"""CLI tool for syncing historical data from Hyperliquid.

Supported Timeframes:
    1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M

Usage:
    # Sync a single symbol/timeframe
    python scripts/sync_data.py sync BTC 5m
    
    # Full sync (all available history)
    python scripts/sync_data.py sync BTC 5m --full
    
    # Sync multiple symbols with specific timeframes
    python scripts/sync_data.py bulk BTC ETH SOL --timeframes 1m 5m 1h 4h 1d
    
    # Sync all timeframes (default: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
    python scripts/sync_data.py bulk BTC ETH --full
    
    # Sync all available symbols with all timeframes
    python scripts/sync_data.py all
    
    # List available symbols
    python scripts/sync_data.py symbols
    
    # Show sync status
    python scripts/sync_data.py status
    
    # Show local data summary
    python scripts/sync_data.py available
"""
import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.data_sync import DataSyncService, SyncMode, SyncProgress
from app.db.repositories.ohlcv import OHLCVRepository


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


def format_candles(count: int) -> str:
    """Format candle count."""
    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1000000:.1f}M"


def progress_callback(progress: SyncProgress):
    """Print progress updates."""
    status = "✅" if progress.is_complete else "⏳"
    print(
        f"\r{status} {progress.symbol}/{progress.timeframe}: "
        f"{format_candles(progress.candles_fetched)} candles, "
        f"{progress.batches_processed} batches, "
        f"{format_duration(progress.duration_seconds)}",
        end="",
        flush=True,
    )
    if progress.is_complete:
        print()


async def cmd_sync(args):
    """Sync a single symbol/timeframe."""
    db = SessionLocal()
    try:
        service = DataSyncService(db, testnet=args.testnet)
        mode = SyncMode.FULL if args.full else SyncMode.INCREMENTAL
        
        print(f"🔄 Syncing {args.symbol}/{args.timeframe} ({mode.value})...")
        
        result = await service.sync(
            symbol=args.symbol,
            timeframe=args.timeframe,
            mode=mode,
            progress_callback=progress_callback,
        )
        
        if result.success:
            print(f"\n✅ Sync complete!")
            print(f"   Candles fetched: {result.candles_fetched}")
            print(f"   Candles inserted: {result.candles_inserted}")
            if result.oldest_candle:
                print(f"   Range: {result.oldest_candle} to {result.newest_candle}")
            print(f"   Duration: {format_duration(result.duration_seconds)}")
        else:
            print(f"\n❌ Sync failed: {result.error}")
            return 1
    finally:
        db.close()
    return 0


async def cmd_bulk(args):
    """Sync multiple symbols."""
    db = SessionLocal()
    try:
        service = DataSyncService(db, testnet=args.testnet)
        mode = SyncMode.FULL if args.full else SyncMode.INCREMENTAL
        timeframes = args.timeframes or ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        
        total = len(args.symbols) * len(timeframes)
        print(f"🔄 Syncing {len(args.symbols)} symbols × {len(timeframes)} timeframes = {total} combinations")
        print(f"   Symbols: {', '.join(args.symbols)}")
        print(f"   Timeframes: {', '.join(timeframes)}")
        print()
        
        def bulk_progress(symbol: str, timeframe: str, progress: SyncProgress):
            progress_callback(progress)
        
        results = await service.sync_multiple(
            symbols=args.symbols,
            timeframes=timeframes,
            mode=mode,
            progress_callback=bulk_progress,
        )
        
        successful = sum(1 for r in results if r.success)
        total_candles = sum(r.candles_inserted for r in results)
        
        print(f"\n📊 Results:")
        print(f"   Successful: {successful}/{len(results)}")
        print(f"   Total candles inserted: {format_candles(total_candles)}")
        
        # Show failures
        failures = [r for r in results if not r.success]
        if failures:
            print(f"\n❌ Failures:")
            for r in failures:
                print(f"   {r.symbol}/{r.timeframe}: {r.error}")
    finally:
        db.close()
    return 0


async def cmd_all(args):
    """Sync all available symbols."""
    db = SessionLocal()
    try:
        service = DataSyncService(db, testnet=args.testnet)
        
        print("📋 Fetching available symbols from Hyperliquid...")
        symbols = await service.get_available_symbols()
        print(f"   Found {len(symbols)} symbols")
        
        if args.limit:
            symbols = symbols[:args.limit]
            print(f"   Limiting to first {args.limit}: {', '.join(symbols)}")
        
        # Use bulk sync
        args.symbols = symbols
        return await cmd_bulk(args)
    finally:
        db.close()


async def cmd_symbols(args):
    """List available Hyperliquid symbols."""
    db = SessionLocal()
    try:
        service = DataSyncService(db, testnet=args.testnet)
        
        print("📋 Fetching available symbols from Hyperliquid...")
        symbols = await service.get_available_symbols()
        
        print(f"\n✅ Found {len(symbols)} symbols:\n")
        
        # Print in columns
        cols = 6
        for i in range(0, len(symbols), cols):
            row = symbols[i:i + cols]
            print("   " + "  ".join(f"{s:8}" for s in row))
    finally:
        db.close()
    return 0


async def cmd_status(args):
    """Show sync status for all tracked pairs."""
    db = SessionLocal()
    try:
        service = DataSyncService(db)
        statuses = service.get_all_sync_statuses()
        
        if not statuses:
            print("📋 No data has been synced yet.")
            print("   Run: python scripts/sync_data.py sync BTC 5m")
            return 0
        
        print(f"📊 Sync Status ({len(statuses)} combinations)\n")
        print(f"{'Symbol':<8} {'TF':<6} {'Candles':>10} {'Oldest':<12} {'Newest':<12} {'Last Sync':<20} {'Status':<10}")
        print("-" * 90)
        
        for s in sorted(statuses, key=lambda x: (x.symbol, x.timeframe)):
            oldest = s.oldest_candle.strftime("%Y-%m-%d") if s.oldest_candle else "N/A"
            newest = s.newest_candle.strftime("%Y-%m-%d") if s.newest_candle else "N/A"
            last_sync = s.last_sync_at.strftime("%Y-%m-%d %H:%M") if s.last_sync_at else "Never"
            status = "🔄 Syncing" if s.is_syncing else ("❌ Error" if s.last_error else "✅ OK")
            
            print(f"{s.symbol:<8} {s.timeframe:<6} {s.candle_count:>10,} {oldest:<12} {newest:<12} {last_sync:<20} {status:<10}")
    finally:
        db.close()
    return 0


async def cmd_available(args):
    """Show summary of available local data."""
    db = SessionLocal()
    try:
        service = DataSyncService(db)
        data = service.get_available_data()
        
        if not data["symbols"]:
            print("📋 No data available locally.")
            print("   Run: python scripts/sync_data.py sync BTC 5m")
            return 0
        
        print(f"📊 Available Local Data\n")
        print(f"Symbols ({len(data['symbols'])}): {', '.join(data['symbols'])}")
        print(f"Timeframes ({len(data['timeframes'])}): {', '.join(data['timeframes'])}")
        print()
        
        if data["details"]:
            print(f"{'Symbol':<8} {'TF':<6} {'Candles':>10} {'From':<12} {'To':<12}")
            print("-" * 50)
            for d in sorted(data["details"], key=lambda x: (x["symbol"], x["timeframe"])):
                oldest = d["oldest"][:10] if d["oldest"] else "N/A"
                newest = d["newest"][:10] if d["newest"] else "N/A"
                print(f"{d['symbol']:<8} {d['timeframe']:<6} {d['candle_count']:>10,} {oldest:<12} {newest:<12}")
    finally:
        db.close()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Hyperliquid Historical Data Sync Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--testnet", action="store_true", help="Use Hyperliquid testnet")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync a single symbol/timeframe")
    sync_parser.add_argument("symbol", help="Trading symbol (e.g., BTC)")
    sync_parser.add_argument("timeframe", help="Candle timeframe (e.g., 5m, 1h)")
    sync_parser.add_argument("--full", action="store_true", help="Full sync (all history)")
    
    # bulk command
    bulk_parser = subparsers.add_parser("bulk", help="Sync multiple symbols")
    bulk_parser.add_argument("symbols", nargs="+", help="Trading symbols")
    bulk_parser.add_argument("--timeframes", nargs="+", help="Timeframes (default: 5m,15m,30m,1h,4h,1d)")
    bulk_parser.add_argument("--full", action="store_true", help="Full sync")
    
    # all command
    all_parser = subparsers.add_parser("all", help="Sync all available symbols")
    all_parser.add_argument("--timeframes", nargs="+", help="Timeframes to sync")
    all_parser.add_argument("--limit", type=int, help="Limit number of symbols")
    all_parser.add_argument("--full", action="store_true", help="Full sync")
    
    # symbols command
    subparsers.add_parser("symbols", help="List available Hyperliquid symbols")
    
    # status command
    subparsers.add_parser("status", help="Show sync status")
    
    # available command
    subparsers.add_parser("available", help="Show available local data")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Run appropriate command
    commands = {
        "sync": cmd_sync,
        "bulk": cmd_bulk,
        "all": cmd_all,
        "symbols": cmd_symbols,
        "status": cmd_status,
        "available": cmd_available,
    }
    
    try:
        return asyncio.run(commands[args.command](args))
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
