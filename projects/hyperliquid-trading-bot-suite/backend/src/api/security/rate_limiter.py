"""
Redis-based rate limiter implementation.

Provides sliding window rate limiting for API endpoints.
"""

import time
import asyncio
from typing import Optional, Callable, Awaitable, Dict, Any
from functools import wraps
from enum import Enum

from fastapi import Request, HTTPException, status
import redis.asyncio as redis
import structlog

from ...config import settings

logger = structlog.get_logger()


class RateLimitTier(Enum):
    """Rate limit tiers for different endpoint types."""
    
    # Very strict - authentication endpoints
    AUTH = ("auth", 5, 60)  # 5 requests per minute
    
    # Strict - trading operations
    TRADING = ("trading", 10, 60)  # 10 requests per minute
    
    # Moderate - data mutations
    MUTATION = ("mutation", 30, 60)  # 30 requests per minute
    
    # Relaxed - read operations
    READ = ("read", 100, 60)  # 100 requests per minute
    
    # Very relaxed - health checks, public info
    PUBLIC = ("public", 300, 60)  # 300 requests per minute
    
    # File uploads - very strict
    UPLOAD = ("upload", 5, 3600)  # 5 uploads per hour
    
    def __init__(self, key: str, max_requests: int, window_seconds: int):
        self.key = key
        self.max_requests = max_requests
        self.window_seconds = window_seconds


class RateLimiter:
    """
    Redis-based sliding window rate limiter.
    
    Uses a sliding window algorithm for more accurate rate limiting
    compared to fixed windows.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL (uses settings if not provided)
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
        self._fallback_limits: Dict[str, Dict[str, Any]] = {}  # In-memory fallback
        self._enabled = True
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            logger.warning("Rate limiter falling back to in-memory storage")
            self._redis = None
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    def disable(self) -> None:
        """Disable rate limiting (for testing)."""
        self._enabled = False
    
    def enable(self) -> None:
        """Enable rate limiting."""
        self._enabled = True
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier for the rate limit bucket
            max_requests: Maximum requests allowed in window
            window_seconds: Size of the sliding window in seconds
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        if not self._enabled:
            return True, max_requests, 0
        
        if self._redis:
            return await self._check_redis(key, max_requests, window_seconds)
        else:
            return await self._check_memory(key, max_requests, window_seconds)
    
    async def _check_redis(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check rate limit using Redis sliding window."""
        now = time.time()
        window_start = now - window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()
        
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count >= max_requests:
            # Get oldest entry to calculate reset time
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            reset_time = int(oldest[0][1] + window_seconds - now) if oldest else window_seconds
            return False, 0, reset_time
        
        # Add new request
        await self._redis.zadd(key, {f"{now}:{id(asyncio.current_task())}": now})
        
        # Set expiry on the key
        await self._redis.expire(key, window_seconds + 1)
        
        remaining = max_requests - current_count - 1
        reset_time = window_seconds
        
        return True, remaining, reset_time
    
    async def _check_memory(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check rate limit using in-memory storage (fallback)."""
        now = time.time()
        window_start = now - window_seconds
        
        if key not in self._fallback_limits:
            self._fallback_limits[key] = {"requests": []}
        
        # Clean old entries
        self._fallback_limits[key]["requests"] = [
            ts for ts in self._fallback_limits[key]["requests"]
            if ts > window_start
        ]
        
        current_count = len(self._fallback_limits[key]["requests"])
        
        if current_count >= max_requests:
            oldest = min(self._fallback_limits[key]["requests"]) if self._fallback_limits[key]["requests"] else now
            reset_time = int(oldest + window_seconds - now)
            return False, 0, reset_time
        
        # Add new request
        self._fallback_limits[key]["requests"].append(now)
        
        remaining = max_requests - current_count - 1
        reset_time = window_seconds
        
        return True, remaining, reset_time
    
    def get_key_for_request(
        self,
        request: Request,
        tier: RateLimitTier,
        user_id: Optional[str] = None
    ) -> str:
        """
        Generate a rate limit key for a request.
        
        Args:
            request: FastAPI request
            tier: Rate limit tier
            user_id: Optional user ID for user-specific limits
            
        Returns:
            Rate limit bucket key
        """
        # Use user ID if available, otherwise use IP
        if user_id:
            identifier = f"user:{user_id}"
        else:
            # Get client IP, handling proxies
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
            identifier = f"ip:{client_ip}"
        
        return f"ratelimit:{tier.key}:{identifier}"


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        await _rate_limiter.connect()
    
    return _rate_limiter


def rate_limit(
    tier: RateLimitTier = RateLimitTier.READ,
    custom_key: Optional[Callable[[Request], str]] = None
):
    """
    Decorator/dependency for rate limiting endpoints.
    
    Args:
        tier: Rate limit tier to apply
        custom_key: Optional custom key function
        
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            request: Request,
            _: None = Depends(rate_limit(RateLimitTier.READ))
        ):
            ...
    """
    async def rate_limit_dependency(request: Request) -> None:
        limiter = await get_rate_limiter()
        
        # Get user ID from request state if available
        user_id = getattr(request.state, "user_id", None)
        
        # Generate rate limit key
        if custom_key:
            key = custom_key(request)
        else:
            key = limiter.get_key_for_request(request, tier, user_id)
        
        # Check rate limit
        allowed, remaining, reset_time = await limiter.is_allowed(
            key,
            tier.max_requests,
            tier.window_seconds
        )
        
        # Add rate limit headers to response
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_reset = reset_time
        request.state.rate_limit_limit = tier.max_requests
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                key=key,
                tier=tier.key,
                reset_time=reset_time
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {reset_time} seconds.",
                headers={
                    "X-RateLimit-Limit": str(tier.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )
    
    return rate_limit_dependency


class RateLimitMiddleware:
    """
    Global rate limiting middleware.
    
    Applies a base rate limit to all requests before endpoint-specific limits.
    """
    
    def __init__(
        self,
        app,
        global_limit: int = 1000,
        window_seconds: int = 60,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            global_limit: Global requests per window
            window_seconds: Rate limit window
            exclude_paths: Paths to exclude from rate limiting
        """
        self.app = app
        self.global_limit = global_limit
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/api/health", "/docs", "/openapi.json"]
    
    async def __call__(self, scope, receive, send):
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if path is excluded
        path = scope.get("path", "")
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Get rate limiter
        limiter = await get_rate_limiter()
        
        # Get client identifier
        headers = dict(scope.get("headers", []))
        forwarded = headers.get(b"x-forwarded-for", b"").decode()
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client = scope.get("client", ("unknown", 0))
            client_ip = client[0] if client else "unknown"
        
        key = f"ratelimit:global:ip:{client_ip}"
        
        # Check global rate limit
        allowed, remaining, reset_time = await limiter.is_allowed(
            key,
            self.global_limit,
            self.window_seconds
        )
        
        if not allowed:
            # Return 429 response
            response_headers = [
                (b"content-type", b"application/json"),
                (b"x-ratelimit-limit", str(self.global_limit).encode()),
                (b"x-ratelimit-remaining", b"0"),
                (b"x-ratelimit-reset", str(reset_time).encode()),
                (b"retry-after", str(reset_time).encode()),
            ]
            
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": response_headers,
            })
            await send({
                "type": "http.response.body",
                "body": b'{"detail": "Too many requests. Please slow down."}',
            })
            return
        
        await self.app(scope, receive, send)
