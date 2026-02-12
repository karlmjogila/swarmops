"""Unit tests for CSV importer.

Tests cover:
- Happy path: valid CSV import
- Validation: invalid data rejection
- Dead letter queue: invalid records logged
- Idempotency: duplicate detection
- Format support: various timestamp formats
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import io

from app.core.market.importer import (
    CSVImporter,
    TradingViewCandle,
    ImportStats,
    create_sample_csv,
)


class MockRepository:
    """Mock OHLCVRepository for testing without database."""
    
    def __init__(self):
        self.inserted_candles = []
        self.should_fail = False
    
    def bulk_insert_candles(self, candles: list, source: str = None) -> int:
        """Mock bulk insert - tracks inserted candles."""
        if self.should_fail:
            raise Exception("Database error")
        
        self.inserted_candles.extend(candles)
        return len(candles)


def test_validate_candle_happy_path():
    """Test valid candle passes validation."""
    candle = TradingViewCandle(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0,
    )
    
    assert candle.open == 50000.0
    assert candle.high == 50100.0
    assert candle.low == 49900.0
    assert candle.close == 50050.0
    assert candle.volume == 100.0


def test_validate_candle_high_must_be_highest():
    """Test validation rejects high < close."""
    with pytest.raises(Exception) as exc_info:
        TradingViewCandle(
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            open=50000.0,
            high=49900.0,  # Lower than low!
            low=50000.0,
            close=50050.0,
            volume=100.0,
        )
    
    assert "high" in str(exc_info.value).lower()


def test_validate_candle_low_must_be_lowest():
    """Test validation rejects low > close."""
    with pytest.raises(Exception) as exc_info:
        TradingViewCandle(
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            open=50000.0,
            high=50100.0,
            low=50200.0,  # Higher than high!
            close=50050.0,
            volume=100.0,
        )
    
    assert "low" in str(exc_info.value).lower()


def test_validate_candle_prices_must_be_positive():
    """Test validation rejects negative prices."""
    with pytest.raises(Exception):
        TradingViewCandle(
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            open=-50000.0,  # Negative!
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=100.0,
        )


def test_validate_candle_volume_non_negative():
    """Test validation accepts zero volume but rejects negative."""
    # Zero is OK
    candle = TradingViewCandle(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=0.0,
    )
    assert candle.volume == 0.0
    
    # Negative is not OK
    with pytest.raises(Exception):
        TradingViewCandle(
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=-100.0,
        )


def test_import_sample_csv():
    """Test importing valid CSV data."""
    csv_content = create_sample_csv()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        # All records should be valid
        assert stats.extracted == 5
        assert stats.valid == 5
        assert stats.invalid == 0
        assert stats.inserted == 5
        assert stats.duplicates == 0
        
        # Check inserted data
        assert len(repo.inserted_candles) == 5
        
        first = repo.inserted_candles[0]
        assert first["symbol"] == "BTC-USD"
        assert first["timeframe"] == "5m"
        assert first["open"] == 50000.0
        assert first["close"] == 50050.0


def test_import_csv_with_invalid_records():
    """Test CSV with mix of valid and invalid records."""
    csv_content = """time,open,high,low,close,volume
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0,100.5
2024-01-01 00:05:00,50050.0,49999.0,50000.0,50150.0,120.3
2024-01-01 00:10:00,50150.0,50250.0,50100.0,50200.0,95.7
2024-01-01 00:15:00,-1000.0,50300.0,50150.0,50250.0,110.2
2024-01-01 00:20:00,50250.0,50350.0,50200.0,50300.0,105.8"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        # Should have 5 extracted, 3 valid, 2 invalid
        assert stats.extracted == 5
        assert stats.valid == 3
        assert stats.invalid == 2
        assert stats.inserted == 3
        
        # Check DLQ file was created
        dlq_files = list(Path(tmpdir).glob("dlq-*.jsonl"))
        assert len(dlq_files) == 1


def test_import_csv_unix_timestamp():
    """Test CSV with Unix timestamps."""
    csv_content = """time,open,high,low,close,volume
1704067200,50000.0,50100.0,49900.0,50050.0,100.5
1704067500,50050.0,50200.0,50000.0,50150.0,120.3"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.extracted == 2
        assert stats.valid == 2
        assert stats.inserted == 2


def test_import_csv_iso_timestamp():
    """Test CSV with ISO format timestamps."""
    csv_content = """time,open,high,low,close,volume
2024-01-01T00:00:00Z,50000.0,50100.0,49900.0,50050.0,100.5
2024-01-01T00:05:00Z,50050.0,50200.0,50000.0,50150.0,120.3"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.extracted == 2
        assert stats.valid == 2
        assert stats.inserted == 2


def test_import_csv_no_volume():
    """Test CSV without volume column."""
    csv_content = """time,open,high,low,close
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0
2024-01-01 00:05:00,50050.0,50200.0,50000.0,50150.0"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.extracted == 2
        assert stats.valid == 2
        assert stats.inserted == 2
        
        # Volume should default to 0.0
        assert repo.inserted_candles[0]["volume"] == 0.0


def test_import_csv_missing_required_columns():
    """Test CSV with missing required columns."""
    csv_content = """time,open,close
2024-01-01 00:00:00,50000.0,50050.0"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        with pytest.raises(ValueError) as exc_info:
            importer.import_from_string(
                csv_content,
                "BTC-USD",
                "5m",
                repo
            )
        
        assert "missing required columns" in str(exc_info.value).lower()


def test_import_csv_empty_file():
    """Test importing empty CSV file."""
    csv_content = "time,open,high,low,close,volume\n"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.extracted == 0
        assert stats.inserted == 0


def test_import_csv_case_insensitive_headers():
    """Test CSV with different case headers."""
    csv_content = """TIME,OPEN,HIGH,LOW,CLOSE,VOLUME
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0,100.5"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.extracted == 1
        assert stats.valid == 1
        assert stats.inserted == 1


def test_import_csv_whitespace_handling():
    """Test CSV with extra whitespace."""
    csv_content = """time , open , high , low , close , volume
2024-01-01 00:00:00 , 50000.0 , 50100.0 , 49900.0 , 50050.0 , 100.5 """
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.extracted == 1
        assert stats.valid == 1
        assert stats.inserted == 1


def test_import_stats_success_rate():
    """Test ImportStats success_rate calculation."""
    stats = ImportStats(
        run_id="test",
        symbol="BTC-USD",
        timeframe="5m",
        extracted=100,
        valid=95,
        invalid=5,
    )
    
    assert stats.success_rate == 95.0
    
    # Zero extracted should not crash
    stats_empty = ImportStats(
        run_id="test",
        symbol="BTC-USD",
        timeframe="5m",
        extracted=0,
    )
    assert stats_empty.success_rate == 0.0


def test_timestamp_alignment():
    """Test that timestamps are aligned to timeframe boundaries."""
    csv_content = """time,open,high,low,close,volume
2024-01-01 00:07:23,50000.0,50100.0,49900.0,50050.0,100.5"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_string(
            csv_content,
            "BTC-USD",
            "5m",
            repo
        )
        
        # Timestamp should be aligned to 00:05:00
        inserted = repo.inserted_candles[0]
        assert inserted["timestamp"].minute == 5
        assert inserted["timestamp"].second == 0


def test_import_from_file():
    """Test importing from actual file."""
    csv_content = create_sample_csv()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write CSV to file
        csv_file = Path(tmpdir) / "test.csv"
        csv_file.write_text(csv_content)
        
        # Import from file
        importer = CSVImporter(dlq_dir=Path(tmpdir))
        repo = MockRepository()
        
        stats = importer.import_from_file(
            csv_file,
            "BTC-USD",
            "5m",
            repo
        )
        
        assert stats.inserted == 5


def test_parse_timestamp_formats():
    """Test various timestamp formats are parsed correctly."""
    importer = CSVImporter()
    
    # Unix timestamp (seconds)
    ts1 = importer._parse_timestamp("1704067200")
    assert ts1.year == 2024
    assert ts1.month == 1
    assert ts1.day == 1
    
    # Unix timestamp (milliseconds)
    ts2 = importer._parse_timestamp("1704067200000")
    assert ts2.year == 2024
    
    # ISO format with T
    ts3 = importer._parse_timestamp("2024-01-01T00:00:00")
    assert ts3.year == 2024
    
    # TradingView format (space)
    ts4 = importer._parse_timestamp("2024-01-01 00:00:00")
    assert ts4.year == 2024
    
    # ISO with Z
    ts5 = importer._parse_timestamp("2024-01-01T00:00:00Z")
    assert ts5.year == 2024
    
    # Invalid format
    with pytest.raises(ValueError):
        importer._parse_timestamp("invalid-timestamp")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
