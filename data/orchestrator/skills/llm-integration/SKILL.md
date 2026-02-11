---
name: llm-integration
description: >
  Build production-grade LLM-powered applications with proper prompt design, structured
  output parsing, tool use, error handling, cost optimization, and evaluation patterns.
  Covers Anthropic Claude API, prompt engineering, agent architectures, RAG patterns,
  and AI safety guardrails. Trigger this skill for any task involving LLM APIs, Claude
  integration, prompt engineering, AI agents, tool use, structured outputs, embeddings,
  or any AI/ML service integration.
triggers:
  - llm
  - claude
  - anthropic
  - openai
  - gpt
  - prompt
  - ai
  - agent
  - rag
  - embedding
  - vector
  - completion
  - chat
  - model
  - inference
  - token
  - context window
  - fine-tune
  - tool use
  - function calling
  - structured output
---

# LLM Integration Excellence

LLMs are powerful but unpredictable. Build integrations that are robust against the inherent non-determinism of language models. Validate outputs, handle failures gracefully, manage costs, and never trust model output without verification for critical operations.

## Core Principles

1. **Validate, don't trust** — LLM outputs are suggestions, not facts. Always validate structured outputs against schemas, and verify critical data against ground truth.
2. **Prompt is code** — Treat prompts with the same rigor as code: version them, test them, review them. A prompt change is a behavior change.
3. **Cost is a feature** — Every API call costs money. Cache aggressively, choose the right model for the task, and measure cost per operation.

## Client Setup

### Anthropic Claude SDK
```python
from anthropic import AsyncAnthropic, APIError, RateLimitError
import os


def create_client() -> AsyncAnthropic:
    """Create an Anthropic client with sensible defaults."""
    return AsyncAnthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        max_retries=3,            # Auto-retry on 429, 500, 502, etc.
        timeout=120.0,            # 2 minutes for long-running requests
    )


# Always use the async client for production
client = create_client()
```

### Calling the API
```python
async def generate_response(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> str:
    """Basic completion with error handling."""
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    except RateLimitError:
        # SDK auto-retries, but if all retries fail:
        logger.error("Rate limited after all retries")
        raise
    except APIError as e:
        logger.error("API error", status=e.status_code, message=str(e))
        raise
```

## Prompt Engineering

### Prompt Structure
```python
# Prompts have clear sections: role, context, task, format, constraints

ANALYSIS_PROMPT = """You are a financial analyst specializing in cryptocurrency markets.

## Context
You are analyzing trading data for a portfolio management system.
Your analysis will be used to make automated trading decisions.

## Task
Analyze the following market data and provide:
1. Current market sentiment (bullish/bearish/neutral)
2. Key support and resistance levels
3. Risk assessment (low/medium/high)

## Format
Respond in JSON with this exact structure:
{
  "sentiment": "bullish" | "bearish" | "neutral",
  "support_levels": [float],
  "resistance_levels": [float],
  "risk": "low" | "medium" | "high",
  "reasoning": "string"
}

## Constraints
- Base analysis ONLY on the provided data
- Do not hallucinate price levels — derive from the data
- If data is insufficient, set risk to "high" and explain in reasoning
"""
```

### Prompt Management
```python
from pathlib import Path
from string import Template


class PromptManager:
    """Load and render prompts from files. Prompts are code — version them."""

    def __init__(self, prompts_dir: Path):
        self._dir = prompts_dir
        self._cache: dict[str, str] = {}

    def get(self, name: str, **kwargs) -> str:
        """Load a prompt template and render with variables."""
        if name not in self._cache:
            path = self._dir / f"{name}.txt"
            self._cache[name] = path.read_text()

        template = Template(self._cache[name])
        return template.safe_substitute(**kwargs)


# Usage
prompts = PromptManager(Path("prompts/"))
prompt = prompts.get("analyze_market", symbol="BTC-USD", timeframe="1h")
```

## Structured Outputs

### Using Pydantic with Claude
```python
from pydantic import BaseModel
from anthropic import AsyncAnthropic


class MarketAnalysis(BaseModel):
    sentiment: str
    support_levels: list[float]
    resistance_levels: list[float]
    risk: str
    reasoning: str


async def analyze_market(data: str) -> MarketAnalysis:
    """Get structured analysis using JSON schema output."""
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[{"role": "user", "content": f"Analyze this data:\n{data}"}],
        system=ANALYSIS_PROMPT,
    )

    # Parse and validate
    raw = response.content[0].text
    try:
        return MarketAnalysis.model_validate_json(raw)
    except Exception as e:
        logger.error("Failed to parse LLM output", raw=raw, error=str(e))
        raise ValueError(f"Invalid model output: {e}")
```

### Structured Output with SDK
```python
from anthropic import transform_schema


async def analyze_with_schema(data: str) -> MarketAnalysis:
    """Use Anthropic's structured output for guaranteed schema compliance."""
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        system=ANALYSIS_PROMPT,
        messages=[{"role": "user", "content": f"Analyze:\n{data}"}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": transform_schema(MarketAnalysis),
            }
        },
    )

    return MarketAnalysis.model_validate_json(response.content[0].text)
```

## Tool Use / Function Calling

### Defining Tools
```python
tools = [
    {
        "name": "get_market_price",
        "description": "Get the current market price for a trading pair",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading pair (e.g., BTC-USD)",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "place_order",
        "description": "Place a trading order. Use with caution.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "number"},
                "order_type": {"type": "string", "enum": ["market", "limit"]},
                "price": {"type": "number"},
            },
            "required": ["symbol", "side", "quantity", "order_type"],
            "additionalProperties": False,
        },
    },
]
```

### Tool Use Loop
```python
async def run_agent_loop(
    user_message: str,
    tools: list[dict],
    max_iterations: int = 10,
) -> str:
    """Run a tool-use agent loop with safety limits."""
    messages = [{"role": "user", "content": user_message}]

    for iteration in range(max_iterations):
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system="You are a trading assistant. Use tools to answer questions.",
            messages=messages,
            tools=tools,
        )

        # Check if model wants to use tools
        if response.stop_reason == "tool_use":
            # Extract tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            # Add assistant response and tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Model is done — extract text response
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        elif response.stop_reason == "refusal":
            logger.warning("Model refused request")
            return "I cannot help with that request."

    logger.warning("Agent loop hit max iterations")
    return "I was unable to complete the task within the allowed steps."


async def execute_tool(name: str, params: dict) -> dict:
    """Execute a tool call. Add validation and safety checks here."""
    if name == "get_market_price":
        return await get_market_price(params["symbol"])
    elif name == "place_order":
        # CRITICAL: validate before executing financial operations
        logger.info("Tool: place_order", **params)
        return await order_service.create_order(**params)
    else:
        return {"error": f"Unknown tool: {name}"}
```

## Cost Optimization

### Model Selection
```python
# Choose the right model for the task:
#
# claude-haiku-4-5  — Fast, cheap. Use for: classification, extraction, simple Q&A
# claude-sonnet-4-5 — Balanced. Use for: analysis, code generation, most tasks
# claude-opus-4-6   — Most capable. Use for: complex reasoning, critical decisions
#
# Rule: start with the cheapest model that works, upgrade only when needed

MODEL_FOR_TASK = {
    "classify_sentiment": "claude-haiku-4-5-20251001",
    "extract_entities": "claude-haiku-4-5-20251001",
    "analyze_market": "claude-sonnet-4-5-20250929",
    "generate_report": "claude-sonnet-4-5-20250929",
    "complex_reasoning": "claude-opus-4-6",
}
```

### Caching
```python
import hashlib
import json


class LLMCache:
    """Cache deterministic LLM calls. Only for temperature=0."""

    def __init__(self):
        self._cache: dict[str, str] = {}

    def _key(self, model: str, messages: list, system: str = "") -> str:
        content = json.dumps({"model": model, "messages": messages, "system": system})
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_or_create(
        self,
        client: AsyncAnthropic,
        model: str,
        messages: list,
        system: str = "",
        **kwargs,
    ) -> str:
        key = self._key(model, messages, system)

        if key in self._cache:
            return self._cache[key]

        response = await client.messages.create(
            model=model,
            messages=messages,
            system=system,
            temperature=0,  # Required for caching to be meaningful
            **kwargs,
        )

        result = response.content[0].text
        self._cache[key] = result
        return result
```

### Token Management
```python
def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token for English text."""
    return len(text) // 4


def truncate_to_fit(
    text: str,
    max_tokens: int,
    strategy: str = "tail",
) -> str:
    """Truncate text to fit within token budget."""
    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text

    # Keep approximate ratio
    max_chars = max_tokens * 4
    if strategy == "tail":
        return "...[truncated]...\n" + text[-max_chars:]
    elif strategy == "head":
        return text[:max_chars] + "\n...[truncated]..."
    else:  # middle
        half = max_chars // 2
        return text[:half] + "\n...[truncated]...\n" + text[-half:]
```

## Evaluation and Testing

### Prompt Testing
```python
import pytest


@pytest.mark.asyncio
async def test_sentiment_classification():
    """Test that the model correctly classifies sentiment."""
    test_cases = [
        ("BTC just hit a new all-time high! Moon!", "bullish"),
        ("Market crashed 40% overnight, panic selling", "bearish"),
        ("Trading sideways, low volume day", "neutral"),
    ]

    for text, expected in test_cases:
        result = await classify_sentiment(text)
        assert result.sentiment == expected, (
            f"Expected {expected} for '{text}', got {result.sentiment}"
        )


@pytest.mark.asyncio
async def test_structured_output_schema():
    """Test that model output matches expected schema."""
    result = await analyze_market("BTC: $50,000, 24h change: +5%")
    assert isinstance(result, MarketAnalysis)
    assert result.sentiment in ("bullish", "bearish", "neutral")
    assert result.risk in ("low", "medium", "high")
    assert len(result.support_levels) > 0
```

### Guardrails
```python
class OutputGuardrails:
    """Validate LLM outputs before using them in production."""

    @staticmethod
    def check_no_hallucinated_data(
        output: MarketAnalysis,
        known_price: float,
    ) -> bool:
        """Verify price levels are within reasonable range of actual price."""
        all_levels = output.support_levels + output.resistance_levels
        for level in all_levels:
            deviation = abs(level - known_price) / known_price
            if deviation > 0.5:  # More than 50% from actual price
                logger.warning(
                    "Possible hallucinated price level",
                    level=level, actual=known_price,
                )
                return False
        return True

    @staticmethod
    def check_reasoning_present(output: MarketAnalysis) -> bool:
        """Ensure the model provided reasoning, not just labels."""
        return len(output.reasoning) > 20
```

## Streaming

```python
async def stream_response(
    user_message: str,
    on_text: callable,
) -> str:
    """Stream response for real-time display."""
    full_text = ""

    async with client.messages.stream(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
            await on_text(text)  # Callback for real-time display

    return full_text
```

## Quality Checklist

- [ ] API key in environment variable (not hardcoded)
- [ ] Error handling for all API calls (rate limits, timeouts, server errors)
- [ ] Structured outputs validated against Pydantic models
- [ ] Prompts stored as files or constants (not inline strings)
- [ ] Model selection appropriate for task complexity
- [ ] Temperature=0 for deterministic tasks, >0 for creative tasks
- [ ] Token budget managed (truncation for long inputs)
- [ ] Caching for repeated deterministic queries
- [ ] Tool use loop has max iteration limit
- [ ] Financial/critical operations validated after LLM generation
- [ ] Prompt tests cover expected behaviors and edge cases
- [ ] Cost tracking per operation type
- [ ] Streaming used for user-facing responses

## Anti-Patterns

- Hardcoding API keys in source code
- No retry logic (rate limits will hit you in production)
- Trusting LLM output for financial calculations (always verify)
- Inline prompt strings scattered across codebase
- Using the most expensive model for every task
- No token limit management (sending entire documents as context)
- Synchronous API calls blocking the event loop
- No timeout on API requests (can hang for minutes)
- Testing prompts only manually (no automated evaluation)
- Ignoring stop_reason (refusals, max_tokens truncation)
- Fire-and-forget tool execution without result validation
- Building complex agent loops without iteration limits
