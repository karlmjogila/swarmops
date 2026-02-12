"""LLM client for Claude API integration.

Provides structured output generation with error handling, rate limiting,
and cost optimization. Follows LLM Integration Excellence principles.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import deque
from typing import Any, TypeVar

from anthropic import APIError, AsyncAnthropic, RateLimitError, transform_schema
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(self, max_requests: int, window_seconds: float):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self._max_requests = max_requests
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request. Blocks if rate limit exceeded."""
        async with self._lock:
            now = time.monotonic()

            # Remove expired timestamps
            while self._timestamps and self._timestamps[0] < now - self._window:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_requests:
                # Wait until the oldest request expires
                wait = self._timestamps[0] + self._window - now
                if wait > 0:
                    logger.debug(f"Rate limit reached, waiting {wait:.2f}s")
                    await asyncio.sleep(wait)
                self._timestamps.popleft()

            self._timestamps.append(time.monotonic())


class LLMCache:
    """In-memory cache for deterministic LLM calls."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def _key(self, model: str, messages: list[dict[str, Any]], system: str = "") -> str:
        """Generate cache key from request parameters."""
        content = json.dumps(
            {"model": model, "messages": messages, "system": system}, sort_keys=True
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, model: str, messages: list[dict[str, Any]], system: str = "") -> str | None:
        """Get cached response if it exists."""
        key = self._key(model, messages, system)
        return self._cache.get(key)

    def set(
        self, model: str, messages: list[dict[str, Any]], system: str, response: str
    ) -> None:
        """Store response in cache."""
        key = self._key(model, messages, system)
        self._cache[key] = response


class LLMClient:
    """High-level LLM client with structured output support."""

    # Model selection based on task complexity
    MODEL_HAIKU = "claude-haiku-4-5-20251001"
    MODEL_SONNET = "claude-sonnet-4-5-20250929"
    MODEL_OPUS = "claude-opus-4-6"

    def __init__(
        self,
        api_key: str | None = None,
        max_retries: int = 3,
        timeout: float = 120.0,
        rate_limit_per_minute: int = 50,
    ):
        """Initialize LLM client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            max_retries: Number of retries for failed requests
            timeout: Request timeout in seconds
            rate_limit_per_minute: Max requests per minute (leave headroom vs actual limit)
        """
        self._client = AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            max_retries=max_retries,
            timeout=timeout,
        )
        self._rate_limiter = RateLimiter(rate_limit_per_minute, 60.0)
        self._cache = LLMCache()
        logger.info(
            f"LLM client initialized with rate limit: {rate_limit_per_minute}/min, "
            f"timeout: {timeout}s"
        )

    async def generate(
        self,
        system: str,
        user_message: str,
        model: str = MODEL_SONNET,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        use_cache: bool = True,
    ) -> str:
        """Generate a text response.

        Args:
            system: System prompt
            user_message: User message
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0 = deterministic)
            use_cache: Whether to use cache for deterministic calls

        Returns:
            Generated text response

        Raises:
            APIError: If API call fails after retries
        """
        messages = [{"role": "user", "content": user_message}]

        # Check cache for deterministic calls
        if temperature == 0.0 and use_cache:
            cached = self._cache.get(model, messages, system)
            if cached:
                logger.debug("Cache hit for LLM request")
                return cached

        await self._rate_limiter.acquire()

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
            )

            result = response.content[0].text

            # Cache deterministic responses
            if temperature == 0.0 and use_cache:
                self._cache.set(model, messages, system, result)

            logger.debug(
                f"LLM response received: {len(result)} chars, "
                f"stop_reason={response.stop_reason}"
            )

            return result

        except RateLimitError as e:
            logger.error(f"Rate limited after all retries: {e}")
            raise
        except APIError as e:
            logger.error(f"API error: status={getattr(e, 'status_code', 'unknown')}, message={e}")
            raise

    async def generate_structured(
        self,
        system: str,
        user_message: str,
        response_model: type[T],
        model: str = MODEL_SONNET,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> T:
        """Generate a structured response using JSON schema.

        Args:
            system: System prompt
            user_message: User message
            response_model: Pydantic model for response validation
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Validated Pydantic model instance

        Raises:
            ValueError: If response doesn't match schema
            APIError: If API call fails
        """
        await self._rate_limiter.acquire()

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user_message}],
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": transform_schema(response_model),
                    }
                },
            )

            raw_json = response.content[0].text

            # Parse and validate against schema
            try:
                result = response_model.model_validate_json(raw_json)
                logger.debug(f"Successfully parsed structured output: {response_model.__name__}")
                return result
            except Exception as e:
                logger.error(
                    f"Failed to parse LLM output: {e}\nRaw output: {raw_json[:500]}"
                )
                raise ValueError(f"Invalid model output: {e}")

        except RateLimitError as e:
            logger.error(f"Rate limited after all retries: {e}")
            raise
        except APIError as e:
            logger.error(f"API error: status={getattr(e, 'status_code', 'unknown')}, message={e}")
            raise

    async def analyze_image(
        self,
        system: str,
        user_message: str,
        image_url: str,
        model: str = MODEL_SONNET,
        max_tokens: int = 4096,
    ) -> str:
        """Analyze an image with Claude Vision.

        Args:
            system: System prompt
            user_message: Text prompt about the image
            image_url: URL of the image to analyze
            model: Model to use
            max_tokens: Maximum tokens to generate

        Returns:
            Analysis text

        Raises:
            APIError: If API call fails
        """
        await self._rate_limiter.acquire()

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "url", "url": image_url}},
                            {"type": "text", "text": user_message},
                        ],
                    }
                ],
            )

            result = response.content[0].text
            logger.debug(f"Image analysis complete: {len(result)} chars")
            return result

        except APIError as e:
            logger.error(f"API error during image analysis: {e}")
            raise

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count (~4 chars per token)
        """
        return len(text) // 4

    def truncate_to_fit(
        self, text: str, max_tokens: int, strategy: str = "tail"
    ) -> str:
        """Truncate text to fit within token budget.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            strategy: Truncation strategy ("tail", "head", "middle")

        Returns:
            Truncated text
        """
        estimated = self.estimate_tokens(text)
        if estimated <= max_tokens:
            return text

        max_chars = max_tokens * 4

        if strategy == "tail":
            return "...[truncated]...\n" + text[-max_chars:]
        elif strategy == "head":
            return text[:max_chars] + "\n...[truncated]..."
        else:  # middle
            half = max_chars // 2
            return text[:half] + "\n...[truncated]...\n" + text[-half:]
