"""Test database connection and basic operations."""
import sys
from datetime import datetime, timezone
from sqlalchemy import text

from app.db.session import engine, SessionLocal
from app.db.models import OHLCVData, StrategyRule


def test_connection():
    """Test database connection."""
    print("Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version}")
            
            # Check TimescaleDB
            result = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';"))
            ts_version = result.fetchone()[0]
            print(f"✅ TimescaleDB extension loaded: {ts_version}")
            
            # Check hypertable
            result = conn.execute(text(
                "SELECT COUNT(*) FROM timescaledb_information.hypertables WHERE hypertable_name = 'ohlcv_data';"
            ))
            count = result.fetchone()[0]
            if count > 0:
                print(f"✅ TimescaleDB hypertable 'ohlcv_data' exists")
            else:
                print(f"❌ TimescaleDB hypertable 'ohlcv_data' NOT found")
                return False
            
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_insert_ohlcv():
    """Test inserting OHLCV data."""
    print("\nTesting OHLCV data insertion...")
    db = SessionLocal()
    try:
        # Create test candle
        candle = OHLCVData(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            symbol="BTC",
            timeframe="15m",
            open=45000.0,
            high=45500.0,
            low=44800.0,
            close=45200.0,
            volume=1234.5
        )
        
        db.add(candle)
        db.commit()
        print(f"✅ Inserted OHLCV candle: BTC @ {candle.timestamp}")
        
        # Query it back
        result = db.query(OHLCVData).filter_by(
            symbol="BTC",
            timeframe="15m"
        ).first()
        
        if result:
            print(f"✅ Queried back: {result.symbol} O:{result.open} H:{result.high} L:{result.low} C:{result.close}")
        else:
            print(f"❌ Failed to query back inserted data")
            return False
            
        # Clean up
        db.delete(result)
        db.commit()
        print(f"✅ Cleaned up test data")
        
        return True
    except Exception as e:
        print(f"❌ Insert failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_insert_strategy():
    """Test inserting a strategy rule."""
    print("\nTesting strategy rule insertion...")
    db = SessionLocal()
    try:
        # Create test strategy
        strategy = StrategyRule(
            name="Test LE Candle Strategy",
            description="Test strategy using LE candle pattern at support",
            timeframes=["15m", "5m"],
            market_phase="range",
            entry_conditions={"pattern": "le_candle", "at_zone": "support"},
            exit_rules={"tp1": "1R", "tp2": "2R"},
            risk_params={"risk_percent": 2.0, "max_drawdown": 10.0},
            source_type="manual",
        )
        
        db.add(strategy)
        db.commit()
        print(f"✅ Inserted strategy: {strategy.name} (ID: {strategy.id})")
        
        # Query it back
        result = db.query(StrategyRule).filter_by(name="Test LE Candle Strategy").first()
        
        if result:
            print(f"✅ Queried back: {result.name}")
            print(f"   Timeframes: {result.timeframes}")
            print(f"   Effectiveness score: {result.effectiveness_score}")
        else:
            print(f"❌ Failed to query back inserted strategy")
            return False
            
        # Clean up
        db.delete(result)
        db.commit()
        print(f"✅ Cleaned up test data")
        
        return True
    except Exception as e:
        print(f"❌ Insert failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Database Connection & Schema Tests")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_connection),
        ("OHLCV Data Operations", test_insert_ohlcv),
        ("Strategy Rule Operations", test_insert_strategy),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Database setup is complete.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
