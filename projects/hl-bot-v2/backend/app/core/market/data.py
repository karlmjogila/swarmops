"""OHLCV data utilities and manipulation functions.

Provides helper functions for working with OHLCV data including
validation, conversion, and common calculations.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Candle:
    """OHLCV candle data structure.
    
    Lightweight data class for passing candle data around.
    Separate from database model to avoid coupling business logic to SQLAlchemy.
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str
    
    @property
    def body_size(self) -> float:
        """Calculate candle body size (absolute difference between open and close)."""
        return abs(self.close - self.open)
    
    @property
    def wick_size_upper(self) -> float:
        """Calculate upper wick size."""
        return self.high - max(self.open, self.close)
    
    @property
    def wick_size_lower(self) -> float:
        """Calculate lower wick size."""
        return min(self.open, self.close) - self.low
    
    @property
    def total_range(self) -> float:
        """Calculate total candle range (high - low)."""
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)."""
        return self.close < self.open
    
    def is_doji(self, threshold: float = 0.1) -> bool:
        """Check if candle is a doji (body size < threshold% of range).
        
        Args:
            threshold: Body size threshold as fraction of total range (default: 10%)
        """
        if self.total_range == 0:
            return True
        return (self.body_size / self.total_range) < threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert candle to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
        }


def validate_ohlcv(
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> tuple[bool, Optional[str]]:
    """Validate OHLCV data for consistency.
    
    Args:
        open_price: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Volume
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> valid, error = validate_ohlcv(100, 105, 95, 102, 1000)
        >>> if not valid:
        ...     print(f"Invalid data: {error}")
    """
    # Check for negative or zero prices
    if any(price <= 0 for price in [open_price, high, low, close]):
        return False, "Prices must be positive"
    
    # Check volume is non-negative
    if volume < 0:
        return False, "Volume cannot be negative"
    
    # Check high vs low relationship first (most fundamental)
    if low > high:
        return False, f"Low ({low}) cannot be greater than high ({high})"
    
    # Check low is lowest
    if low > min(open_price, close):
        return False, f"Low ({low}) must be <= open and close"
    
    # Check high is highest
    if high < max(open_price, close):
        return False, f"High ({high}) must be >= open and close"
    
    return True, None


def from_db_model(db_candle) -> Candle:
    """Convert database OHLCVData model to Candle dataclass.
    
    Args:
        db_candle: SQLAlchemy OHLCVData instance
        
    Returns:
        Candle dataclass instance
    """
    return Candle(
        timestamp=db_candle.timestamp,
        open=db_candle.open,
        high=db_candle.high,
        low=db_candle.low,
        close=db_candle.close,
        volume=db_candle.volume,
        symbol=db_candle.symbol,
        timeframe=db_candle.timeframe,
    )


def to_db_dict(candle: Candle) -> Dict[str, Any]:
    """Convert Candle dataclass to dict for database insertion.
    
    Args:
        candle: Candle dataclass instance
        
    Returns:
        Dict suitable for OHLCVRepository.insert_candle()
    """
    return {
        "symbol": candle.symbol,
        "timeframe": candle.timeframe,
        "timestamp": candle.timestamp,
        "open_price": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
    }


def calculate_price_change(candle: Candle) -> tuple[float, float]:
    """Calculate price change for a candle.
    
    Args:
        candle: Candle dataclass
        
    Returns:
        Tuple of (absolute_change, percent_change)
    """
    change = candle.close - candle.open
    percent_change = (change / candle.open) * 100 if candle.open != 0 else 0.0
    return change, percent_change


def calculate_typical_price(candle: Candle) -> float:
    """Calculate typical price (HLC/3).
    
    Args:
        candle: Candle dataclass
        
    Returns:
        Typical price
    """
    return (candle.high + candle.low + candle.close) / 3


def calculate_hlc_avg(candles: List[Candle]) -> float:
    """Calculate average of high, low, close across multiple candles.
    
    Useful for calculating pivot points and support/resistance levels.
    
    Args:
        candles: List of Candle dataclass instances
        
    Returns:
        Average HLC value
    """
    if not candles:
        return 0.0
    
    total = sum((c.high + c.low + c.close) for c in candles)
    return total / (len(candles) * 3)


def find_highest_candle(candles: List[Candle]) -> Optional[Candle]:
    """Find candle with the highest high.
    
    Args:
        candles: List of Candle dataclass instances
        
    Returns:
        Candle with highest high, or None if list is empty
    """
    if not candles:
        return None
    return max(candles, key=lambda c: c.high)


def find_lowest_candle(candles: List[Candle]) -> Optional[Candle]:
    """Find candle with the lowest low.
    
    Args:
        candles: List of Candle dataclass instances
        
    Returns:
        Candle with lowest low, or None if list is empty
    """
    if not candles:
        return None
    return min(candles, key=lambda c: c.low)


def calculate_average_volume(candles: List[Candle]) -> float:
    """Calculate average volume across candles.
    
    Args:
        candles: List of Candle dataclass instances
        
    Returns:
        Average volume
    """
    if not candles:
        return 0.0
    return sum(c.volume for c in candles) / len(candles)


def is_volume_spike(candle: Candle, average_volume: float, threshold: float = 2.0) -> bool:
    """Check if candle has volume spike above average.
    
    Args:
        candle: Candle to check
        average_volume: Average volume to compare against
        threshold: Multiplier threshold (default: 2.0 = 200% of average)
        
    Returns:
        True if volume is above threshold * average
    """
    if average_volume == 0:
        return False
    return candle.volume > (average_volume * threshold)


def normalize_timestamp(timestamp: datetime) -> datetime:
    """Ensure timestamp has UTC timezone.
    
    Args:
        timestamp: DateTime to normalize
        
    Returns:
        DateTime with UTC timezone
    """
    if timestamp.tzinfo is None:
        # Assume UTC if no timezone
        return timestamp.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return timestamp.astimezone(timezone.utc)


def align_timestamp_to_timeframe(timestamp: datetime, timeframe: str) -> datetime:
    """Align timestamp to the start of its candle period.
    
    For example, 15:07:23 with timeframe "5m" -> 15:05:00
    
    Args:
        timestamp: Timestamp to align
        timeframe: Timeframe string (e.g., "5m", "1h")
        
    Returns:
        Aligned timestamp
        
    Raises:
        ValueError: If timeframe format is invalid
    """
    # Parse timeframe
    if timeframe.endswith('m'):
        minutes = int(timeframe[:-1])
        aligned_minute = (timestamp.minute // minutes) * minutes
        return timestamp.replace(minute=aligned_minute, second=0, microsecond=0)
    elif timeframe.endswith('h'):
        hours = int(timeframe[:-1])
        aligned_hour = (timestamp.hour // hours) * hours
        return timestamp.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    elif timeframe.endswith('d'):
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unsupported timeframe format: {timeframe}")


def get_timeframe_minutes(timeframe: str) -> int:
    """Convert timeframe string to minutes.
    
    Args:
        timeframe: Timeframe string (e.g., "5m", "1h", "1d")
        
    Returns:
        Number of minutes in the timeframe
        
    Raises:
        ValueError: If timeframe format is invalid
    """
    if timeframe.endswith('m'):
        return int(timeframe[:-1])
    elif timeframe.endswith('h'):
        return int(timeframe[:-1]) * 60
    elif timeframe.endswith('d'):
        return int(timeframe[:-1]) * 1440
    else:
        raise ValueError(f"Unsupported timeframe format: {timeframe}")
