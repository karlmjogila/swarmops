"""Hyperliquid historical data fetcher service.

Fetches OHLCV candle data from Hyperliquid API and stores it in TimescaleDB.
Supports incremental syncing, rate limiting, and multiple timeframes.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import StrEnum
from typing import Optional, List, Dict, Any, Callable

import httpx


logger = logging.getLogger(__name__)


class HyperliquidInterval(StrEnum):
    """Supported Hyperliquid candle intervals."""
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"
    H8 = "8h"
    H12 = "12h"
    D1 = "1d"
    D3 = "3d"
    W1 = "1w"
    M1_MONTH = "1M"


# Mapping from our timeframe format to Hyperliquid's
TIMEFRAME_MAP = {
    "1m": HyperliquidInterval.M1,
    "3m": HyperliquidInterval.M3,
    "5m": HyperliquidInterval.M5,
    "15m": HyperliquidInterval.M15,
    "30m": HyperliquidInterval.M30,
    "1h": HyperliquidInterval.H1,
    "2h": HyperliquidInterval.H2,
    "4h": HyperliquidInterval.H4,
    "8h": HyperliquidInterval.H8,
    "12h": HyperliquidInterval.H12,
    "1d": HyperliquidInterval.D1,
    "3d": HyperliquidInterval.D3,
    "1w": HyperliquidInterval.W1,
    "1M": HyperliquidInterval.M1_MONTH,
}


# Timeframe duration in milliseconds (for pagination)
TIMEFRAME_MS = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,  # Approximate
}


@dataclass
class Candle:
    """Represents a single OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int = 0
    
    @classmethod
    def from_hyperliquid(cls, data: Dict[str, Any]) -> "Candle":
        """Create Candle from Hyperliquid API response.
        
        Response format:
        {
            "t": 1681923600000,  # start time (ms)
            "T": 1681924499999,  # end time (ms)
            "o": "29295.0",      # open
            "h": "29309.0",      # high
            "l": "29250.0",      # low
            "c": "29258.0",      # close
            "v": "0.98639",      # volume
            "n": 189,           # number of trades
            "s": "BTC",         # symbol
            "i": "15m",         # interval
        }
        """
        return cls(
            timestamp=datetime.fromtimestamp(data["t"] / 1000, tz=timezone.utc),
            open=float(data["o"]),
            high=float(data["h"]),
            low=float(data["l"]),
            close=float(data["c"]),
            volume=float(data["v"]),
            trades=int(data.get("n", 0)),
        )


@dataclass
class SyncProgress:
    """Track sync progress for reporting."""
    symbol: str
    timeframe: str
    candles_fetched: int = 0
    candles_inserted: int = 0
    batches_processed: int = 0
    oldest_candle: Optional[datetime] = None
    newest_candle: Optional[datetime] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None
    
    @property
    def duration_seconds(self) -> float:
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "candles_fetched": self.candles_fetched,
            "candles_inserted": self.candles_inserted,
            "batches_processed": self.batches_processed,
            "oldest_candle": self.oldest_candle.isoformat() if self.oldest_candle else None,
            "newest_candle": self.newest_candle.isoformat() if self.newest_candle else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "is_complete": self.is_complete,
            "error": self.error,
        }


class HyperliquidDataFetcher:
    """Fetches historical OHLCV data from Hyperliquid API.
    
    Features:
    - Supports all standard timeframes
    - Automatic pagination (max 500 candles per request)
    - Rate limiting (respects Hyperliquid's limits)
    - Incremental sync support
    - Progress callbacks for UI updates
    """
    
    # API limits
    MAX_CANDLES_PER_REQUEST = 500
    RATE_LIMIT_REQUESTS_PER_MIN = 100
    RATE_LIMIT_DELAY = 0.7  # seconds between requests (for safety)
    REQUEST_TIMEOUT = 30.0
    MAX_RETRIES = 3
    
    # Only most recent 5000 candles are available per Hyperliquid docs
    MAX_HISTORICAL_CANDLES = 5000
    
    def __init__(
        self,
        base_url: str = "https://api.hyperliquid.xyz",
        testnet: bool = False,
    ):
        """Initialize the data fetcher.
        
        Args:
            base_url: Hyperliquid API base URL
            testnet: Use testnet API
        """
        if testnet:
            self.base_url = "https://api.hyperliquid-testnet.xyz"
        else:
            self.base_url = base_url
        
        self._last_request_time = 0.0
    
    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        import time
        
        now = time.time()
        elapsed = now - self._last_request_time
        
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        
        self._last_request_time = time.time()
    
    async def _request(
        self,
        data: Dict[str, Any],
        max_retries: int = MAX_RETRIES,
    ) -> Any:
        """Make a POST request to the Hyperliquid info endpoint.
        
        Args:
            data: Request body
            max_retries: Max retry attempts
            
        Returns:
            Response JSON
        """
        await self._rate_limit()
        
        url = f"{self.base_url}/info"
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        url,
                        json=data,
                        headers={"Content-Type": "application/json"},
                    )
                    
                    if response.status_code == 429:
                        # Rate limited - wait and retry
                        retry_after = float(response.headers.get("Retry-After", 5))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return response.json()
            
            except httpx.TimeoutException:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Request timeout, retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    logger.warning(f"Server error {e.response.status_code}, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception("Max retries exceeded")
    
    async def get_available_coins(self) -> List[str]:
        """Get list of all available trading pairs on Hyperliquid.
        
        Returns:
            List of coin symbols (e.g., ["BTC", "ETH", "SOL", ...])
        """
        data = await self._request({"type": "meta"})
        
        if "universe" not in data:
            return []
        
        coins = []
        for asset in data["universe"]:
            name = asset.get("name")
            if name and not asset.get("isDelisted", False):
                coins.append(name)
        
        return coins
    
    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Candle]:
        """Fetch candle data for a single time range.
        
        Note: Max 500 candles per request (Hyperliquid limit).
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            interval: Candle interval (e.g., "5m", "1h")
            start_time: Start time (default: as far back as available)
            end_time: End time (default: now)
            
        Returns:
            List of Candle objects
        """
        # Validate interval
        if interval not in TIMEFRAME_MAP:
            raise ValueError(f"Invalid interval: {interval}. Valid: {list(TIMEFRAME_MAP.keys())}")
        
        hl_interval = TIMEFRAME_MAP[interval]
        
        # Set defaults
        now = datetime.now(timezone.utc)
        if end_time is None:
            end_time = now
        if start_time is None:
            # Default: fetch as much as possible (5000 candles max)
            interval_ms = TIMEFRAME_MS[interval]
            start_time = end_time - timedelta(milliseconds=interval_ms * self.MAX_HISTORICAL_CANDLES)
        
        # Convert to epoch milliseconds
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        # Make request
        data = await self._request({
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": hl_interval,
                "startTime": start_ms,
                "endTime": end_ms,
            }
        })
        
        if not data:
            return []
        
        # Parse candles
        candles = [Candle.from_hyperliquid(c) for c in data]
        return sorted(candles, key=lambda c: c.timestamp)
    
    async def fetch_all_candles(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None,
    ) -> List[Candle]:
        """Fetch all available candles with automatic pagination.
        
        Handles the 500-candle per request limit by making multiple requests.
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            interval: Candle interval (e.g., "5m", "1h")
            start_time: Start time (default: as far back as available)
            end_time: End time (default: now)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all Candle objects
        """
        progress = SyncProgress(symbol=symbol, timeframe=interval)
        all_candles: List[Candle] = []
        
        # Set defaults
        now = datetime.now(timezone.utc)
        if end_time is None:
            end_time = now
        if start_time is None:
            # Start from as far back as we can (5000 candles)
            interval_ms = TIMEFRAME_MS[interval]
            start_time = end_time - timedelta(milliseconds=interval_ms * self.MAX_HISTORICAL_CANDLES)
        
        current_end = end_time
        interval_ms = TIMEFRAME_MS[interval]
        
        while current_end > start_time:
            # Calculate batch start
            batch_start = max(
                start_time,
                current_end - timedelta(milliseconds=interval_ms * self.MAX_CANDLES_PER_REQUEST)
            )
            
            try:
                candles = await self.fetch_candles(
                    symbol=symbol,
                    interval=interval,
                    start_time=batch_start,
                    end_time=current_end,
                )
            except Exception as e:
                logger.error(f"Error fetching candles: {e}")
                progress.error = str(e)
                if progress_callback:
                    progress_callback(progress)
                raise
            
            if not candles:
                # No more data available
                break
            
            all_candles.extend(candles)
            progress.candles_fetched += len(candles)
            progress.batches_processed += 1
            
            # Track time range
            if progress.oldest_candle is None or candles[0].timestamp < progress.oldest_candle:
                progress.oldest_candle = candles[0].timestamp
            if progress.newest_candle is None or candles[-1].timestamp > progress.newest_candle:
                progress.newest_candle = candles[-1].timestamp
            
            if progress_callback:
                progress_callback(progress)
            
            logger.info(
                f"Fetched {len(candles)} candles for {symbol}/{interval}, "
                f"total: {progress.candles_fetched}, oldest: {candles[0].timestamp}"
            )
            
            # Move window back
            current_end = candles[0].timestamp - timedelta(milliseconds=1)
            
            # If we got less than max, we've reached the end
            if len(candles) < self.MAX_CANDLES_PER_REQUEST:
                break
        
        # Remove duplicates and sort
        seen = set()
        unique_candles = []
        for candle in all_candles:
            key = candle.timestamp
            if key not in seen:
                seen.add(key)
                unique_candles.append(candle)
        
        unique_candles.sort(key=lambda c: c.timestamp)
        
        progress.completed_at = datetime.now(timezone.utc)
        if progress_callback:
            progress_callback(progress)
        
        return unique_candles
    
    async def fetch_incremental(
        self,
        symbol: str,
        interval: str,
        since: datetime,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None,
    ) -> List[Candle]:
        """Fetch only new candles since a given timestamp.
        
        For incremental syncs where we already have historical data.
        
        Args:
            symbol: Trading symbol
            interval: Candle interval
            since: Fetch candles after this timestamp
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of new Candle objects
        """
        return await self.fetch_all_candles(
            symbol=symbol,
            interval=interval,
            start_time=since,
            end_time=datetime.now(timezone.utc),
            progress_callback=progress_callback,
        )
