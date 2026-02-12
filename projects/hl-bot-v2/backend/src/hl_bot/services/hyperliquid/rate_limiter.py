"""Rate limiter for exchange API calls.

Respects exchange rate limits with configurable headroom.
Getting banned kills your bot — better safe than sorry.
"""

import asyncio
import time
from collections import deque
from typing import Final


class RateLimiter:
    """Token bucket rate limiter with sliding window."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        headroom_percent: float = 0.3,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            headroom_percent: Safety margin (0.3 = 30% below limit)
        """
        # Apply headroom: if limit is 100/min, use 70/min with 30% headroom
        effective_limit = int(max_requests * (1 - headroom_percent))
        self._max_requests: Final[int] = effective_limit
        self._window: Final[float] = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request. Blocks if rate limit reached."""
        async with self._lock:
            now = time.monotonic()

            # Remove expired timestamps outside the window
            while self._timestamps and self._timestamps[0] < now - self._window:
                self._timestamps.popleft()

            # If at limit, wait until oldest request expires
            if len(self._timestamps) >= self._max_requests:
                wait_time = self._timestamps[0] + self._window - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                # Remove the expired timestamp
                self._timestamps.popleft()

            # Record this request
            self._timestamps.append(time.monotonic())

    @property
    def current_usage(self) -> int:
        """Get current number of requests in window (not thread-safe, for monitoring)."""
        now = time.monotonic()
        # Clean up expired without lock (approximate, for metrics)
        return sum(1 for ts in self._timestamps if ts >= now - self._window)

    @property
    def capacity(self) -> int:
        """Get maximum requests per window."""
        return self._max_requests
