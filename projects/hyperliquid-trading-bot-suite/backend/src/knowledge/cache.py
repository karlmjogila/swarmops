"""
Redis caching layer for the knowledge base repository.
Provides efficient caching for frequently accessed data.
"""

import json
import hashlib
from datetime import timedelta
from typing import Any, Optional, List, Union
from functools import wraps

import redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from ..config import settings


class CacheManager:
    """Manages Redis cache operations."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with Redis connection."""
        self.redis_url = redis_url or settings.redis_url
        self.redis_db = settings.redis_db
        self.max_connections = settings.redis_max_connections
        
        # Sync connection pool
        self._pool = redis.ConnectionPool.from_url(
            self.redis_url,
            db=self.redis_db,
            max_connections=self.max_connections,
            decode_responses=True
        )
        self._client = redis.Redis(connection_pool=self._pool)
        
    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache get error for key {key}: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL (seconds)."""
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                return self.client.setex(key, ttl, serialized)
            else:
                return self.client.set(key, serialized)
        except (RedisError, TypeError) as e:
            print(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, *keys: str) -> int:
        """Delete keys from cache."""
        try:
            return self.client.delete(*keys)
        except RedisError as e:
            print(f"Cache delete error: {e}")
            return 0
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except RedisError as e:
            print(f"Cache delete pattern error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return self.client.exists(key) > 0
        except RedisError as e:
            print(f"Cache exists error: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key."""
        try:
            return self.client.expire(key, ttl)
        except RedisError as e:
            print(f"Cache expire error: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get remaining TTL for key."""
        try:
            return self.client.ttl(key)
        except RedisError as e:
            print(f"Cache TTL error: {e}")
            return -1
    
    def flush_all(self):
        """Clear all cache (use with caution)."""
        try:
            self.client.flushdb()
        except RedisError as e:
            print(f"Cache flush error: {e}")
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        try:
            return self.client.incrby(key, amount)
        except RedisError as e:
            print(f"Cache increment error: {e}")
            return 0
    
    def get_many(self, *keys: str) -> List[Optional[Any]]:
        """Get multiple values at once."""
        try:
            values = self.client.mget(*keys)
            return [json.loads(v) if v else None for v in values]
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache get_many error: {e}")
            return [None] * len(keys)
    
    def set_many(
        self,
        mapping: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Set multiple key-value pairs."""
        try:
            serialized = {k: json.dumps(v, default=str) for k, v in mapping.items()}
            pipe = self.client.pipeline()
            pipe.mset(serialized)
            if ttl:
                for key in mapping:
                    pipe.expire(key, ttl)
            pipe.execute()
            return True
        except (RedisError, TypeError) as e:
            print(f"Cache set_many error: {e}")
            return False
    
    def close(self):
        """Close Redis connection."""
        try:
            self.client.close()
            self._pool.disconnect()
        except RedisError as e:
            print(f"Cache close error: {e}")


# Cache key generators
class CacheKeys:
    """Cache key generation helpers."""
    
    PREFIX = "trading_bot"
    
    @staticmethod
    def strategy_rule(rule_id: str) -> str:
        """Generate cache key for strategy rule."""
        return f"{CacheKeys.PREFIX}:strategy_rule:{rule_id}"
    
    @staticmethod
    def strategy_rules_list(
        entry_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> str:
        """Generate cache key for strategy rules list."""
        params = f"{entry_type}:{min_confidence}:{limit}:{offset}"
        key_hash = hashlib.md5(params.encode()).hexdigest()[:8]
        return f"{CacheKeys.PREFIX}:strategy_rules:list:{key_hash}"
    
    @staticmethod
    def trade_record(trade_id: str) -> str:
        """Generate cache key for trade record."""
        return f"{CacheKeys.PREFIX}:trade_record:{trade_id}"
    
    @staticmethod
    def open_trades(asset: Optional[str] = None) -> str:
        """Generate cache key for open trades."""
        asset_key = asset or "all"
        return f"{CacheKeys.PREFIX}:trades:open:{asset_key}"
    
    @staticmethod
    def learning_entry(entry_id: str) -> str:
        """Generate cache key for learning entry."""
        return f"{CacheKeys.PREFIX}:learning:{entry_id}"
    
    @staticmethod
    def performance_stats(strategy_rule_id: Optional[str] = None, days_back: Optional[int] = None) -> str:
        """Generate cache key for performance stats."""
        rule_key = strategy_rule_id or "all"
        days_key = days_back or "all"
        return f"{CacheKeys.PREFIX}:stats:{rule_key}:{days_key}"
    
    @staticmethod
    def similar_rules(rule_id: str, limit: int = 10) -> str:
        """Generate cache key for similar rules."""
        return f"{CacheKeys.PREFIX}:similar_rules:{rule_id}:{limit}"


# Cache TTL constants (in seconds)
class CacheTTL:
    """Cache TTL constants."""
    MINUTE = 60
    FIVE_MINUTES = 300
    FIFTEEN_MINUTES = 900
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    
    # Specific TTLs
    STRATEGY_RULE = HOUR
    TRADE_RECORD = FIFTEEN_MINUTES
    OPEN_TRADES = MINUTE
    PERFORMANCE_STATS = FIVE_MINUTES
    SIMILAR_RULES = HOUR


def cached(
    key_fn=None,
    ttl: int = CacheTTL.FIFTEEN_MINUTES,
    cache_manager: Optional[CacheManager] = None
):
    """
    Decorator for caching function results.
    
    Args:
        key_fn: Function to generate cache key from function args
        ttl: Time to live in seconds
        cache_manager: CacheManager instance (will create if not provided)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if no cache manager
            if cache_manager is None:
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                # Default key generation
                func_name = func.__name__
                args_str = str(args) + str(kwargs)
                key_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{CacheKeys.PREFIX}:{func_name}:{key_hash}"
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    return cache_manager


__all__ = [
    "CacheManager",
    "CacheKeys",
    "CacheTTL",
    "cached",
    "cache_manager",
    "get_cache_manager",
]
