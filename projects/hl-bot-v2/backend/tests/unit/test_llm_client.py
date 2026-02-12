"""Unit tests for LLM client."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIError, RateLimitError
from pydantic import BaseModel

from hl_bot.services.llm_client import LLMCache, LLMClient, RateLimiter


class MockResponse(BaseModel):
    """Mock Pydantic response for testing."""

    name: str
    value: int


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(max_requests=2, window_seconds=1.0)

    # First two requests should be instant
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < 0.1, "First two requests should be instant"

    # Third request should wait
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed >= 0.9, "Third request should wait ~1 second"


@pytest.mark.asyncio
async def test_rate_limiter_concurrent():
    """Test rate limiter with concurrent requests."""
    limiter = RateLimiter(max_requests=3, window_seconds=1.0)

    async def make_request():
        await limiter.acquire()
        return True

    # Launch 5 concurrent requests (should be serialized to max 3/sec)
    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[make_request() for _ in range(5)])
    elapsed = asyncio.get_event_loop().time() - start

    assert len(results) == 5
    assert elapsed >= 1.0, "Should take at least 1 second for 5 requests with limit of 3"


def test_llm_cache_basic():
    """Test basic cache functionality."""
    cache = LLMCache()

    model = "test-model"
    messages = [{"role": "user", "content": "test"}]
    system = "test system"
    response = "cached response"

    # Cache miss
    assert cache.get(model, messages, system) is None

    # Store
    cache.set(model, messages, system, response)

    # Cache hit
    assert cache.get(model, messages, system) == response


def test_llm_cache_key_sensitivity():
    """Test that cache keys are sensitive to parameter changes."""
    cache = LLMCache()

    model = "test-model"
    messages = [{"role": "user", "content": "test"}]
    system = "test system"

    cache.set(model, messages, system, "response1")

    # Different messages
    different_messages = [{"role": "user", "content": "different"}]
    assert cache.get(model, different_messages, system) is None

    # Different system
    assert cache.get(model, messages, "different system") is None

    # Different model
    assert cache.get("different-model", messages, system) is None


@pytest.mark.asyncio
async def test_llm_client_initialization():
    """Test LLM client initialization."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        client = LLMClient()
        assert client is not None


@pytest.mark.asyncio
async def test_llm_client_generate_success():
    """Test successful text generation."""
    with patch("hl_bot.services.llm_client.AsyncAnthropic") as mock_anthropic:
        # Mock response
        mock_content = MagicMock()
        mock_content.text = "Generated response"

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        # Mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")
        result = await client.generate(
            system="Test system",
            user_message="Test message",
            use_cache=False,  # Disable cache for testing
        )

        assert result == "Generated response"
        mock_client_instance.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_llm_client_generate_with_cache():
    """Test that caching works for deterministic calls."""
    with patch("hl_bot.services.llm_client.AsyncAnthropic") as mock_anthropic:
        # Mock response
        mock_content = MagicMock()
        mock_content.text = "Cached response"

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        # Mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")

        # First call
        result1 = await client.generate(
            system="Test",
            user_message="Test",
            temperature=0.0,
            use_cache=True,
        )

        # Second call (should use cache)
        result2 = await client.generate(
            system="Test",
            user_message="Test",
            temperature=0.0,
            use_cache=True,
        )

        assert result1 == result2 == "Cached response"
        # Should only call API once
        assert mock_client_instance.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_llm_client_rate_limit_error():
    """Test handling of rate limit errors."""
    with patch("hl_bot.services.llm_client.AsyncAnthropic") as mock_anthropic:
        # Mock a rate limit error with proper constructor
        mock_response = MagicMock()
        mock_response.status_code = 429
        error = RateLimitError("Rate limited", response=mock_response, body={})
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(side_effect=error)
        mock_anthropic.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")

        with pytest.raises(RateLimitError):
            await client.generate(
                system="Test",
                user_message="Test",
                use_cache=False,
            )


@pytest.mark.asyncio
async def test_llm_client_api_error():
    """Test handling of API errors."""
    with patch("hl_bot.services.llm_client.AsyncAnthropic") as mock_anthropic:
        # Mock an API error with proper constructor
        mock_request = MagicMock()
        error = APIError("API error", request=mock_request, body={})
        
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(side_effect=error)
        mock_anthropic.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")

        with pytest.raises(APIError):
            await client.generate(
                system="Test",
                user_message="Test",
                use_cache=False,
            )


@pytest.mark.asyncio
async def test_llm_client_structured_output():
    """Test structured output generation."""
    with patch("hl_bot.services.llm_client.AsyncAnthropic") as mock_anthropic:
        # Mock response with valid JSON
        mock_content = MagicMock()
        mock_content.text = '{"name": "Test", "value": 42}'

        mock_response = MagicMock()
        mock_response.content = [mock_content]

        # Mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")
        result = await client.generate_structured(
            system="Test",
            user_message="Test",
            response_model=MockResponse,
        )

        assert isinstance(result, MockResponse)
        assert result.name == "Test"
        assert result.value == 42


@pytest.mark.asyncio
async def test_llm_client_structured_output_invalid():
    """Test structured output with invalid response."""
    with patch("hl_bot.services.llm_client.AsyncAnthropic") as mock_anthropic:
        # Mock response with invalid JSON
        mock_content = MagicMock()
        mock_content.text = '{"name": "Test"}'  # Missing required 'value' field

        mock_response = MagicMock()
        mock_response.content = [mock_content]

        # Mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client_instance

        client = LLMClient(api_key="test-key")

        with pytest.raises(ValueError, match="Invalid model output"):
            await client.generate_structured(
                system="Test",
                user_message="Test",
                response_model=MockResponse,
            )


def test_estimate_tokens():
    """Test token estimation."""
    client = LLMClient(api_key="test-key")

    # Rough estimate: 4 chars per token
    text = "a" * 400
    estimated = client.estimate_tokens(text)
    assert estimated == 100


def test_truncate_to_fit_tail():
    """Test text truncation with tail strategy."""
    client = LLMClient(api_key="test-key")

    text = "a" * 1000
    truncated = client.truncate_to_fit(text, max_tokens=100, strategy="tail")

    assert len(truncated) <= 400 + 50  # ~100 tokens + overhead
    assert truncated.startswith("...[truncated]...")
    assert truncated.endswith("a" * 10)


def test_truncate_to_fit_head():
    """Test text truncation with head strategy."""
    client = LLMClient(api_key="test-key")

    text = "a" * 1000
    truncated = client.truncate_to_fit(text, max_tokens=100, strategy="head")

    assert len(truncated) <= 400 + 50
    assert truncated.startswith("a" * 10)
    assert truncated.endswith("...[truncated]...")


def test_truncate_to_fit_middle():
    """Test text truncation with middle strategy."""
    client = LLMClient(api_key="test-key")

    text = "a" * 1000
    truncated = client.truncate_to_fit(text, max_tokens=100, strategy="middle")

    assert len(truncated) <= 400 + 50
    assert "...[truncated]..." in truncated
