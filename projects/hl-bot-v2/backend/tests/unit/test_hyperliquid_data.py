"""Unit tests for Hyperliquid data fetcher."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.hyperliquid_data import (
    HyperliquidDataFetcher,
    Candle,
    SyncProgress,
    TIMEFRAME_MAP,
    TIMEFRAME_MS,
    HyperliquidInterval,
)


class TestCandle:
    """Tests for the Candle dataclass."""
    
    def test_from_hyperliquid(self):
        """Test creating Candle from Hyperliquid response."""
        data = {
            "t": 1681923600000,  # Start time
            "T": 1681924499999,  # End time
            "o": "29295.0",
            "h": "29309.0",
            "l": "29250.0",
            "c": "29258.0",
            "v": "0.98639",
            "n": 189,
            "s": "BTC",
            "i": "15m",
        }
        
        candle = Candle.from_hyperliquid(data)
        
        assert candle.timestamp == datetime(2023, 4, 19, 14, 0, 0, tzinfo=timezone.utc)
        assert candle.open == 29295.0
        assert candle.high == 29309.0
        assert candle.low == 29250.0
        assert candle.close == 29258.0
        assert candle.volume == 0.98639
        assert candle.trades == 189
    
    def test_from_hyperliquid_missing_trades(self):
        """Test Candle creation when trades field is missing."""
        data = {
            "t": 1681923600000,
            "o": "100.0",
            "h": "105.0",
            "l": "95.0",
            "c": "102.0",
            "v": "1000.0",
        }
        
        candle = Candle.from_hyperliquid(data)
        assert candle.trades == 0


class TestSyncProgress:
    """Tests for SyncProgress tracking."""
    
    def test_initial_state(self):
        """Test initial progress state."""
        progress = SyncProgress(symbol="BTC", timeframe="5m")
        
        assert progress.symbol == "BTC"
        assert progress.timeframe == "5m"
        assert progress.candles_fetched == 0
        assert progress.candles_inserted == 0
        assert progress.batches_processed == 0
        assert progress.is_complete is False
        assert progress.error is None
    
    def test_is_complete_when_completed_at_set(self):
        """Test is_complete property."""
        progress = SyncProgress(symbol="BTC", timeframe="5m")
        assert progress.is_complete is False
        
        progress.completed_at = datetime.now(timezone.utc)
        assert progress.is_complete is True
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        start = datetime.now(timezone.utc)
        progress = SyncProgress(symbol="BTC", timeframe="5m", started_at=start)
        
        # Without completion
        assert progress.duration_seconds >= 0
        
        # With completion
        progress.completed_at = start + timedelta(seconds=10)
        assert abs(progress.duration_seconds - 10) < 0.1
    
    def test_to_dict(self):
        """Test serialization to dict."""
        progress = SyncProgress(
            symbol="BTC",
            timeframe="5m",
            candles_fetched=100,
            candles_inserted=95,
        )
        
        data = progress.to_dict()
        
        assert data["symbol"] == "BTC"
        assert data["timeframe"] == "5m"
        assert data["candles_fetched"] == 100
        assert data["candles_inserted"] == 95
        assert "started_at" in data
        assert "is_complete" in data


class TestHyperliquidDataFetcher:
    """Tests for HyperliquidDataFetcher."""
    
    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance."""
        return HyperliquidDataFetcher(testnet=True)
    
    def test_init_mainnet(self):
        """Test mainnet URL."""
        fetcher = HyperliquidDataFetcher(testnet=False)
        assert "api.hyperliquid.xyz" in fetcher.base_url
    
    def test_init_testnet(self):
        """Test testnet URL."""
        fetcher = HyperliquidDataFetcher(testnet=True)
        assert "api.hyperliquid-testnet.xyz" in fetcher.base_url
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, fetcher):
        """Test rate limiting between requests."""
        import time
        
        # Make initial request timestamp
        fetcher._last_request_time = time.time()
        
        # Rate limit should add delay
        start = time.time()
        await fetcher._rate_limit()
        elapsed = time.time() - start
        
        # Should have waited approximately RATE_LIMIT_DELAY
        assert elapsed >= fetcher.RATE_LIMIT_DELAY - 0.1
    
    @pytest.mark.asyncio
    async def test_get_available_coins(self, fetcher):
        """Test fetching available coins."""
        mock_response = {
            "universe": [
                {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
                {"name": "ETH", "szDecimals": 4, "maxLeverage": 50},
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
                {"name": "OLD", "szDecimals": 0, "isDelisted": True},
            ]
        }
        
        with patch.object(fetcher, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            coins = await fetcher.get_available_coins()
            
            assert "BTC" in coins
            assert "ETH" in coins
            assert "SOL" in coins
            assert "OLD" not in coins  # Delisted
    
    @pytest.mark.asyncio
    async def test_fetch_candles(self, fetcher):
        """Test fetching candles for a time range."""
        mock_response = [
            {
                "t": 1681923600000,
                "o": "29295.0",
                "h": "29309.0",
                "l": "29250.0",
                "c": "29258.0",
                "v": "0.98639",
                "n": 189,
            },
            {
                "t": 1681924500000,
                "o": "29258.0",
                "h": "29280.0",
                "l": "29240.0",
                "c": "29270.0",
                "v": "1.5",
                "n": 200,
            },
        ]
        
        with patch.object(fetcher, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            candles = await fetcher.fetch_candles(
                symbol="BTC",
                interval="15m",
                start_time=datetime(2023, 4, 19, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2023, 4, 19, 15, 0, tzinfo=timezone.utc),
            )
            
            assert len(candles) == 2
            assert candles[0].open == 29295.0
            assert candles[1].open == 29258.0
    
    @pytest.mark.asyncio
    async def test_fetch_candles_invalid_interval(self, fetcher):
        """Test error on invalid interval."""
        with pytest.raises(ValueError, match="Invalid interval"):
            await fetcher.fetch_candles(
                symbol="BTC",
                interval="invalid",
            )
    
    @pytest.mark.asyncio
    async def test_fetch_all_candles_with_pagination(self, fetcher):
        """Test fetching all candles with pagination."""
        # Mock multiple batches
        batch1 = [
            {"t": 1681923600000 + i * 300000, "o": "100", "h": "101", "l": "99", "c": "100", "v": "1"}
            for i in range(500)
        ]
        batch2 = [
            {"t": 1681923600000 - (i + 1) * 300000, "o": "99", "h": "100", "l": "98", "c": "99", "v": "1"}
            for i in range(100)
        ]
        
        with patch.object(fetcher, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [batch1, batch2, []]
            
            progress_updates = []
            def track_progress(progress: SyncProgress):
                progress_updates.append(progress.candles_fetched)
            
            candles = await fetcher.fetch_all_candles(
                symbol="BTC",
                interval="5m",
                progress_callback=track_progress,
            )
            
            # Should have removed duplicates and merged
            assert len(candles) <= 600
            assert len(progress_updates) >= 2
    
    @pytest.mark.asyncio
    async def test_fetch_incremental(self, fetcher):
        """Test incremental fetch."""
        mock_response = [
            {"t": 1681923600000, "o": "100", "h": "101", "l": "99", "c": "100", "v": "1"},
        ]
        
        since = datetime(2023, 4, 19, 14, 0, tzinfo=timezone.utc)
        
        with patch.object(fetcher, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            candles = await fetcher.fetch_incremental(
                symbol="BTC",
                interval="5m",
                since=since,
            )
            
            # Verify the request was made with correct time range
            call_args = mock_request.call_args[0][0]
            assert call_args["req"]["startTime"] >= int(since.timestamp() * 1000)


class TestTimeframeMappings:
    """Test timeframe mappings are correct."""
    
    def test_all_timeframes_have_mapping(self):
        """Ensure all standard timeframes are mapped."""
        expected = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"]
        for tf in expected:
            assert tf in TIMEFRAME_MAP
    
    def test_all_timeframes_have_ms(self):
        """Ensure all timeframes have duration in MS."""
        for tf in TIMEFRAME_MAP:
            assert tf in TIMEFRAME_MS
            assert TIMEFRAME_MS[tf] > 0
    
    def test_timeframe_ms_values(self):
        """Test specific timeframe durations."""
        assert TIMEFRAME_MS["1m"] == 60 * 1000
        assert TIMEFRAME_MS["5m"] == 5 * 60 * 1000
        assert TIMEFRAME_MS["1h"] == 60 * 60 * 1000
        assert TIMEFRAME_MS["1d"] == 24 * 60 * 60 * 1000
