"""Multi-timeframe data alignment and resampling.

Provides utilities for converting lower timeframe OHLCV data into higher timeframes.
This is essential for multi-timeframe analysis and confluence scoring.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from collections import defaultdict

from app.core.market.data import Candle, get_timeframe_minutes, align_timestamp_to_timeframe


class TimeframeResampler:
    """Resample lower timeframe candles into higher timeframes.
    
    Handles OHLCV aggregation following standard rules:
    - Open: First candle's open in the period
    - High: Maximum high in the period
    - Low: Minimum low in the period
    - Close: Last candle's close in the period
    - Volume: Sum of all volumes in the period
    
    Example:
        >>> resampler = TimeframeResampler()
        >>> candles_5m = [...]  # List of 5-minute candles
        >>> candles_15m = resampler.resample(candles_5m, "5m", "15m")
    """
    
    def resample(
        self,
        candles: List[Candle],
        source_timeframe: str,
        target_timeframe: str,
    ) -> List[Candle]:
        """Resample candles from source timeframe to target timeframe.
        
        Args:
            candles: List of candles in source timeframe (must be sorted by timestamp)
            source_timeframe: Source timeframe (e.g., "5m")
            target_timeframe: Target timeframe (e.g., "15m", "1h")
            
        Returns:
            List of resampled candles in target timeframe
            
        Raises:
            ValueError: If target timeframe is smaller than source timeframe
            ValueError: If candles list is empty
        """
        if not candles:
            return []
        
        # Validate timeframes
        source_minutes = get_timeframe_minutes(source_timeframe)
        target_minutes = get_timeframe_minutes(target_timeframe)
        
        if target_minutes < source_minutes:
            raise ValueError(
                f"Cannot resample to smaller timeframe: {source_timeframe} -> {target_timeframe}"
            )
        
        if target_minutes == source_minutes:
            # No resampling needed
            return candles.copy()
        
        # Group candles by aligned target timeframe periods
        grouped = self._group_by_timeframe(candles, target_timeframe)
        
        # Aggregate each group into a single candle
        resampled = []
        for timestamp in sorted(grouped.keys()):
            period_candles = grouped[timestamp]
            aggregated = self._aggregate_candles(period_candles, target_timeframe)
            if aggregated:
                resampled.append(aggregated)
        
        return resampled
    
    def _group_by_timeframe(
        self,
        candles: List[Candle],
        target_timeframe: str,
    ) -> Dict[datetime, List[Candle]]:
        """Group candles by aligned target timeframe periods.
        
        Args:
            candles: List of candles to group
            target_timeframe: Target timeframe for alignment
            
        Returns:
            Dict mapping aligned timestamp to list of candles in that period
        """
        grouped = defaultdict(list)
        
        for candle in candles:
            # Align timestamp to target timeframe period
            aligned_ts = align_timestamp_to_timeframe(candle.timestamp, target_timeframe)
            grouped[aligned_ts].append(candle)
        
        return grouped
    
    def _aggregate_candles(
        self,
        candles: List[Candle],
        timeframe: str,
    ) -> Optional[Candle]:
        """Aggregate a list of candles into a single candle.
        
        Args:
            candles: List of candles in the same period (must be sorted by timestamp)
            timeframe: Timeframe of the aggregated candle
            
        Returns:
            Aggregated candle or None if candles list is empty
        """
        if not candles:
            return None
        
        # Sort by timestamp to ensure correct open/close
        sorted_candles = sorted(candles, key=lambda c: c.timestamp)
        
        # OHLCV aggregation
        first_candle = sorted_candles[0]
        last_candle = sorted_candles[-1]
        
        aggregated = Candle(
            timestamp=align_timestamp_to_timeframe(first_candle.timestamp, timeframe),
            open=first_candle.open,
            high=max(c.high for c in sorted_candles),
            low=min(c.low for c in sorted_candles),
            close=last_candle.close,
            volume=sum(c.volume for c in sorted_candles),
            symbol=first_candle.symbol,
            timeframe=timeframe,
        )
        
        return aggregated


def resample_candles(
    candles: List[Candle],
    source_timeframe: str,
    target_timeframe: str,
) -> List[Candle]:
    """Convenience function to resample candles.
    
    Args:
        candles: List of candles in source timeframe
        source_timeframe: Source timeframe (e.g., "5m")
        target_timeframe: Target timeframe (e.g., "15m", "1h")
        
    Returns:
        List of resampled candles
        
    Example:
        >>> candles_5m = [...]
        >>> candles_1h = resample_candles(candles_5m, "5m", "1h")
    """
    resampler = TimeframeResampler()
    return resampler.resample(candles, source_timeframe, target_timeframe)


def create_multi_timeframe_view(
    base_candles: List[Candle],
    base_timeframe: str,
    target_timeframes: List[str],
) -> Dict[str, List[Candle]]:
    """Create a multi-timeframe view from base candles.
    
    Args:
        base_candles: Base candles (smallest timeframe)
        base_timeframe: Timeframe of base candles
        target_timeframes: List of target timeframes to generate
        
    Returns:
        Dict mapping timeframe to list of candles
        
    Example:
        >>> candles_5m = [...]
        >>> mtf_view = create_multi_timeframe_view(
        ...     candles_5m,
        ...     "5m",
        ...     ["5m", "15m", "1h", "4h"]
        ... )
        >>> # mtf_view = {"5m": [...], "15m": [...], "1h": [...], "4h": [...]}
    """
    resampler = TimeframeResampler()
    result = {}
    
    for tf in target_timeframes:
        if tf == base_timeframe:
            result[tf] = base_candles.copy()
        else:
            result[tf] = resampler.resample(base_candles, base_timeframe, tf)
    
    return result


def get_aligned_candle(
    candles: List[Candle],
    timestamp: datetime,
    timeframe: str,
) -> Optional[Candle]:
    """Get the candle that contains a specific timestamp.
    
    Args:
        candles: List of candles (must be sorted by timestamp)
        timestamp: Timestamp to find
        timeframe: Timeframe of the candles
        
    Returns:
        Candle containing the timestamp, or None if not found
        
    Example:
        >>> candles_1h = [...]
        >>> ts = datetime(2024, 1, 1, 15, 30)  # 15:30
        >>> candle = get_aligned_candle(candles_1h, ts, "1h")
        >>> # Returns the 15:00-16:00 candle
    """
    aligned_ts = align_timestamp_to_timeframe(timestamp, timeframe)
    
    for candle in candles:
        if candle.timestamp == aligned_ts:
            return candle
    
    return None


def get_lookback_candles(
    candles: List[Candle],
    current_index: int,
    lookback_periods: int,
) -> List[Candle]:
    """Get N candles before the current index (for pattern analysis).
    
    Args:
        candles: List of candles
        current_index: Current candle index
        lookback_periods: Number of periods to look back
        
    Returns:
        List of candles from [current_index - lookback_periods : current_index]
        
    Example:
        >>> candles = [c1, c2, c3, c4, c5]
        >>> lookback = get_lookback_candles(candles, 4, 2)
        >>> # Returns [c3, c4]
    """
    start_index = max(0, current_index - lookback_periods)
    return candles[start_index:current_index]


def align_multi_timeframe_data(
    mtf_data: Dict[str, List[Candle]],
    reference_timestamp: datetime,
) -> Dict[str, Optional[Candle]]:
    """Align multi-timeframe data to a reference timestamp.
    
    Given a reference timestamp, returns the corresponding candle from each timeframe.
    This is useful for confluence analysis at a specific point in time.
    
    Args:
        mtf_data: Dict mapping timeframe to list of candles
        reference_timestamp: Reference timestamp
        
    Returns:
        Dict mapping timeframe to the aligned candle
        
    Example:
        >>> mtf_data = {
        ...     "5m": [candles_5m],
        ...     "15m": [candles_15m],
        ...     "1h": [candles_1h],
        ... }
        >>> aligned = align_multi_timeframe_data(mtf_data, datetime.now())
        >>> # aligned = {"5m": candle_5m, "15m": candle_15m, "1h": candle_1h}
    """
    aligned = {}
    
    for timeframe, candles in mtf_data.items():
        aligned[timeframe] = get_aligned_candle(candles, reference_timestamp, timeframe)
    
    return aligned


def validate_timeframe_hierarchy(timeframes: List[str]) -> bool:
    """Validate that timeframes are in ascending order.
    
    Args:
        timeframes: List of timeframe strings
        
    Returns:
        True if timeframes are in ascending order (smallest to largest)
        
    Example:
        >>> validate_timeframe_hierarchy(["5m", "15m", "1h", "4h"])
        True
        >>> validate_timeframe_hierarchy(["1h", "5m", "15m"])
        False
    """
    if len(timeframes) <= 1:
        return True
    
    minutes = [get_timeframe_minutes(tf) for tf in timeframes]
    return all(minutes[i] <= minutes[i + 1] for i in range(len(minutes) - 1))


def get_candle_at_time(
    candles: List[Candle],
    target_time: datetime,
    timeframe: str,
) -> Optional[Candle]:
    """Get the candle at a specific time.
    
    More efficient than get_aligned_candle for large datasets using binary search.
    
    Args:
        candles: List of candles (must be sorted by timestamp)
        target_time: Target timestamp
        timeframe: Timeframe of candles
        
    Returns:
        Candle at target time, or None if not found
    """
    aligned_time = align_timestamp_to_timeframe(target_time, timeframe)
    
    # Binary search for efficiency
    left, right = 0, len(candles) - 1
    
    while left <= right:
        mid = (left + right) // 2
        candle = candles[mid]
        
        if candle.timestamp == aligned_time:
            return candle
        elif candle.timestamp < aligned_time:
            left = mid + 1
        else:
            right = mid - 1
    
    return None


def get_timeframe_multiplier(source_tf: str, target_tf: str) -> int:
    """Calculate how many source candles fit in one target candle.
    
    Args:
        source_tf: Source timeframe (e.g., "5m")
        target_tf: Target timeframe (e.g., "1h")
        
    Returns:
        Number of source candles per target candle
        
    Example:
        >>> get_timeframe_multiplier("5m", "1h")
        12
        >>> get_timeframe_multiplier("15m", "1h")
        4
    """
    source_minutes = get_timeframe_minutes(source_tf)
    target_minutes = get_timeframe_minutes(target_tf)
    
    if target_minutes < source_minutes:
        raise ValueError(
            f"Target timeframe ({target_tf}) cannot be smaller than source ({source_tf})"
        )
    
    return target_minutes // source_minutes


def generate_timeframe_sequence(base_tf: str, max_multiplier: int = 48) -> List[str]:
    """Generate a logical sequence of timeframes from a base timeframe.
    
    Args:
        base_tf: Base timeframe (e.g., "5m")
        max_multiplier: Maximum multiplier for largest timeframe
        
    Returns:
        List of timeframe strings in ascending order
        
    Example:
        >>> generate_timeframe_sequence("5m", 48)
        ['5m', '15m', '30m', '1h', '4h']
    """
    base_minutes = get_timeframe_minutes(base_tf)
    timeframes = [base_tf]
    
    # Common multipliers for timeframe progression
    multipliers = [3, 6, 12, 48, 288]  # 15m, 30m, 1h, 4h, 1d from 5m base
    
    for mult in multipliers:
        if mult > max_multiplier:
            break
        
        target_minutes = base_minutes * mult
        
        # Convert back to timeframe string
        if target_minutes >= 1440:
            tf = f"{target_minutes // 1440}d"
        elif target_minutes >= 60:
            tf = f"{target_minutes // 60}h"
        else:
            tf = f"{target_minutes}m"
        
        if tf not in timeframes:
            timeframes.append(tf)
    
    return timeframes


def is_timeframe_complete(
    candles: List[Candle],
    expected_count: int,
    source_tf: str,
    target_tf: str,
) -> bool:
    """Check if enough source candles exist to form complete target candles.
    
    Args:
        candles: List of source candles
        expected_count: Expected number of target candles
        source_tf: Source timeframe
        target_tf: Target timeframe
        
    Returns:
        True if enough complete periods exist
    """
    multiplier = get_timeframe_multiplier(source_tf, target_tf)
    required_candles = expected_count * multiplier
    return len(candles) >= required_candles
