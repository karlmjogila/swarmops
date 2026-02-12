"""Rate limiting for exchange API calls.

Safety-first: Never hit exchange rate limits. Getting banned kills your bot.
Leave 20-30% headroom on all limits.
"""

import asyncio
import time
from collections import deque
from typing import Final


class RateLimiter:
    """Sliding window rate limiter with automatic backoff."""

    def __init__(self, max_requests: int, window_seconds: float):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self._max_requests: Final[int] = max_requests
        self._window: Final[float] = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()
        
    async def acquire(self) -> None:
        """Acquire permission to make a request.
        
        Blocks until request can be made within rate limits.
        Thread-safe via async lock.
        """
        async with self._lock:
            now = time.monotonic()
            
            # Remove expired timestamps
            while self._timestamps and self._timestamps[0] < now - self._window:
                self._timestamps.popleft()
            
            if len(self._timestamps) >= self._max_requests:
                # Wait until the oldest request expires
                wait_time = self._timestamps[0] + self._window - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self._timestamps.popleft()
            
            self._timestamps.append(time.monotonic())
    
    def current_usage(self) -> tuple[int, int]:
        """Get current rate limit usage.
        
        Returns:
            Tuple of (current_requests, max_requests)
        """
        now = time.monotonic()
        
        # Clean old timestamps
        while self._timestamps and self._timestamps[0] < now - self._window:
            self._timestamps.popleft()
        
        return (len(self._timestamps), self._max_requests)
    
    @property
    def utilization(self) -> float:
        """Get current utilization as percentage (0-1)."""
        current, max_requests = self.current_usage()
        return current / max_requests if max_requests > 0 else 0.0
