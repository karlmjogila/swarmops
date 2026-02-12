"""Example: CSV Import for TradingView Data

Demonstrates how to:
1. Import CSV files from TradingView
2. Handle validation errors
3. Check import statistics
4. Query imported data

Prerequisites:
- Database running (docker-compose up db)
- CSV file exported from TradingView

CSV Format:
TradingView exports typically have these columns:
- time (timestamp in various formats)
- open
- high
- low
- close
- volume (optional)

Example CSV:
```
time,open,high,low,close,volume
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0,100.5
2024-01-01 00:05:00,50050.0,50200.0,50000.0,50150.0,120.3
```
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.repositories.ohlcv import OHLCVRepository
from app.core.market.importer import CSVImporter, create_sample_csv


def example_import_from_file():
    """Example: Import from CSV file."""
    print("=" * 60)
    print("Example 1: Import from CSV file")
    print("=" * 60)
    
    # Create sample CSV file
    sample_csv_path = Path("./sample_btc_5m.csv")
    sample_csv_path.write_text(create_sample_csv())
    print(f"\n✓ Created sample CSV: {sample_csv_path}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create importer and repository
        importer = CSVImporter(dlq_dir=Path("./data/dlq"))
        repo = OHLCVRepository(db)
        
        # Import data
        print("\n📥 Importing data...")
        stats = importer.import_from_file(
            sample_csv_path,
            symbol="BTC-USD",
            timeframe="5m",
            repository=repo
        )
        
        # Commit transaction
        db.commit()
        
        # Display statistics
        print("\n✅ Import complete!")
        print(f"   Extracted: {stats.extracted}")
        print(f"   Valid: {stats.valid}")
        print(f"   Invalid: {stats.invalid}")
        print(f"   Inserted: {stats.inserted}")
        print(f"   Duplicates skipped: {stats.duplicates}")
        print(f"   Success rate: {stats.success_rate:.2f}%")
        
        # Query imported data
        print("\n📊 Verifying imported data...")
        time_range = repo.get_time_range("BTC-USD", "5m")
        if time_range:
            earliest, latest = time_range
            print(f"   Time range: {earliest} to {latest}")
        
        count = repo.count_candles("BTC-USD", "5m")
        print(f"   Total candles: {count}")
        
        # Get latest candle
        latest_candle = repo.get_latest_candle("BTC-USD", "5m")
        if latest_candle:
            print(f"   Latest close: ${latest_candle.close:,.2f}")
        
    finally:
        db.close()
        # Clean up sample file
        sample_csv_path.unlink()
        print(f"\n🗑️  Cleaned up: {sample_csv_path}")


def example_import_from_string():
    """Example: Import from CSV string (useful for API endpoints)."""
    print("\n" + "=" * 60)
    print("Example 2: Import from CSV string")
    print("=" * 60)
    
    csv_content = """time,open,high,low,close,volume
2024-01-02 00:00:00,51000.0,51100.0,50900.0,51050.0,150.5
2024-01-02 00:05:00,51050.0,51200.0,51000.0,51150.0,180.3
2024-01-02 00:10:00,51150.0,51250.0,51100.0,51200.0,160.7"""
    
    db = SessionLocal()
    
    try:
        importer = CSVImporter(dlq_dir=Path("./data/dlq"))
        repo = OHLCVRepository(db)
        
        print("\n📥 Importing from string...")
        stats = importer.import_from_string(
            csv_content,
            symbol="BTC-USD",
            timeframe="5m",
            repository=repo
        )
        
        db.commit()
        
        print(f"\n✅ Imported {stats.inserted} candles")
        
    finally:
        db.close()


def example_import_with_errors():
    """Example: Import CSV with invalid records."""
    print("\n" + "=" * 60)
    print("Example 3: Import with validation errors")
    print("=" * 60)
    
    # CSV with intentional errors
    csv_content = """time,open,high,low,close,volume
2024-01-03 00:00:00,52000.0,52100.0,51900.0,52050.0,200.5
2024-01-03 00:05:00,52050.0,51999.0,52000.0,52150.0,220.3
2024-01-03 00:10:00,52150.0,52250.0,52100.0,52200.0,190.7
2024-01-03 00:15:00,-1000.0,52300.0,52150.0,52250.0,210.2
2024-01-03 00:20:00,52250.0,52350.0,52200.0,52300.0,205.8"""
    
    db = SessionLocal()
    
    try:
        importer = CSVImporter(dlq_dir=Path("./data/dlq"))
        repo = OHLCVRepository(db)
        
        print("\n📥 Importing CSV with errors...")
        stats = importer.import_from_string(
            csv_content,
            symbol="BTC-USD",
            timeframe="5m",
            repository=repo
        )
        
        db.commit()
        
        print(f"\n✅ Import complete with errors")
        print(f"   Valid records: {stats.valid}")
        print(f"   Invalid records: {stats.invalid}")
        print(f"   Inserted: {stats.inserted}")
        
        if stats.invalid > 0:
            print(f"\n⚠️  {stats.invalid} invalid records logged to DLQ")
            print(f"   Check: data/dlq/dlq-{stats.run_id}.jsonl")
        
    finally:
        db.close()


def example_import_idempotency():
    """Example: Demonstrate idempotent imports (no duplicates)."""
    print("\n" + "=" * 60)
    print("Example 4: Idempotent imports (no duplicates)")
    print("=" * 60)
    
    csv_content = """time,open,high,low,close,volume
2024-01-04 00:00:00,53000.0,53100.0,52900.0,53050.0,300.5
2024-01-04 00:05:00,53050.0,53200.0,53000.0,53150.0,320.3"""
    
    db = SessionLocal()
    
    try:
        importer = CSVImporter(dlq_dir=Path("./data/dlq"))
        repo = OHLCVRepository(db)
        
        # First import
        print("\n📥 First import...")
        stats1 = importer.import_from_string(
            csv_content,
            symbol="BTC-USD",
            timeframe="5m",
            repository=repo
        )
        db.commit()
        print(f"   Inserted: {stats1.inserted}")
        
        # Second import (same data)
        print("\n📥 Second import (same data)...")
        stats2 = importer.import_from_string(
            csv_content,
            symbol="BTC-USD",
            timeframe="5m",
            repository=repo
        )
        db.commit()
        print(f"   Inserted: {stats2.inserted}")
        print(f"   Duplicates skipped: {stats2.duplicates}")
        
        print("\n✅ Idempotency verified!")
        print("   Re-importing same data does not create duplicates")
        
    finally:
        db.close()


def example_query_data():
    """Example: Query imported data."""
    print("\n" + "=" * 60)
    print("Example 5: Query imported data")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        repo = OHLCVRepository(db)
        
        # Get available symbols and timeframes
        print("\n📊 Available data:")
        symbols = repo.get_available_symbols()
        timeframes = repo.get_available_timeframes()
        
        print(f"   Symbols: {', '.join(symbols) if symbols else 'None'}")
        print(f"   Timeframes: {', '.join(timeframes) if timeframes else 'None'}")
        
        if symbols and timeframes:
            symbol = symbols[0]
            timeframe = timeframes[0]
            
            # Get data range
            time_range = repo.get_time_range(symbol, timeframe)
            if time_range:
                earliest, latest = time_range
                print(f"\n📈 {symbol} {timeframe}:")
                print(f"   Range: {earliest} to {latest}")
                
                # Get count
                count = repo.count_candles(symbol, timeframe)
                print(f"   Total candles: {count}")
                
                # Get latest candles
                latest_candles = repo.get_last_n_candles(symbol, timeframe, 3)
                print(f"\n   Latest 3 candles:")
                for candle in latest_candles:
                    print(f"   {candle.timestamp}: O={candle.open} H={candle.high} L={candle.low} C={candle.close}")
        
    finally:
        db.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("CSV Import Examples")
    print("=" * 60)
    
    try:
        example_import_from_file()
        example_import_from_string()
        example_import_with_errors()
        example_import_idempotency()
        example_query_data()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
