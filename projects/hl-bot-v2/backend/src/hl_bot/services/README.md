# Services Module

## Overview

The services module contains business logic components for the HL Trading Bot. Each service is designed to be independent, testable, and follows best practices from the skills library.

## Components

### LLM Client (`llm_client.py`)

High-level wrapper around the Anthropic Claude API with production-ready features:

**Features:**
- ✅ Rate limiting with token bucket algorithm (respects API limits)
- ✅ In-memory caching for deterministic calls (temperature=0)
- ✅ Structured output support using Pydantic schemas
- ✅ Image analysis with Claude Vision
- ✅ Automatic retry logic for transient errors
- ✅ Token estimation and text truncation
- ✅ Comprehensive error handling

**Usage Example:**

```python
from hl_bot.services import LLMClient

# Initialize client (uses ANTHROPIC_API_KEY env var)
llm = LLMClient(
    rate_limit_per_minute=50,  # Leave headroom vs actual limit
    timeout=120.0,
)

# Basic text generation
response = await llm.generate(
    system="You are a trading analyst",
    user_message="Analyze this setup...",
    model=LLMClient.MODEL_SONNET,  # or MODEL_HAIKU, MODEL_OPUS
    temperature=0.0,  # Deterministic
)

# Structured output with Pydantic validation
from pydantic import BaseModel

class Analysis(BaseModel):
    sentiment: str
    confidence: float

result = await llm.generate_structured(
    system="Analyze market sentiment",
    user_message="BTC broke resistance at $50k",
    response_model=Analysis,
)

# Image analysis
analysis = await llm.analyze_image(
    system="You are a chart analyst",
    user_message="Identify patterns in this chart",
    image_url="https://example.com/chart.png",
)
```

**Model Selection:**
- `MODEL_HAIKU` - Fast, cheap. Use for: classification, extraction, simple Q&A
- `MODEL_SONNET` - Balanced (default). Use for: analysis, code generation, most tasks  
- `MODEL_OPUS` - Most capable. Use for: complex reasoning, critical decisions

**Cost Optimization:**
- Always use the cheapest model that meets requirements
- Cache is automatic for `temperature=0`
- Truncate long inputs with `truncate_to_fit()`

---

### Strategy Extractor (`strategy_extractor.py`)

Converts unstructured educational content (YouTube transcripts, PDFs, images) into structured `StrategyRule` objects using LLM parsing.

**Features:**
- ✅ Extract multiple strategies from raw text
- ✅ Analyze chart images with Claude Vision
- ✅ Versioned prompt management (inline defaults + optional files)
- ✅ Confidence scoring based on completeness
- ✅ Validation against Pydantic schemas
- ✅ Graceful handling of partial/invalid strategies

**Usage Example:**

```python
from hl_bot.services import StrategyExtractor

extractor = StrategyExtractor()

# Extract from text (YouTube transcript, PDF content, etc.)
strategies = await extractor.extract_from_text(
    content="Trading strategy: Buy LE candle at support...",
    source_type="youtube",
    source_id="https://youtube.com/watch?v=abc123",
)

for extracted in strategies:
    strategy_rule = extracted.rule
    confidence = extracted.confidence  # 0.0-1.0
    
    print(f"Strategy: {strategy_rule.name}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Entry conditions: {len(strategy_rule.entry_conditions)}")

# Extract from chart images
strategies = await extractor.extract_from_images(
    image_urls=["https://example.com/chart1.png", "https://example.com/chart2.png"],
    context_text="Additional context from video",
    source_type="youtube",
    source_id="https://youtube.com/watch?v=abc123",
)
```

**Output Schema:**

Each extracted strategy includes:
- `name`: Strategy name
- `description`: Human-readable explanation
- `timeframes`: List of timeframes (5m, 15m, etc.)
- `market_phase`: drive/range/liquidity
- `entry_conditions`: Structured conditions (field/operator/value)
- `exit_rules`: TP levels, breakeven, trailing stop
- `risk_params`: Risk per trade, max positions, max daily loss
- `source`: Metadata about where it came from
- `effectiveness_score`: Updated by learning loop

**Entry Condition Operators:**
- `eq` / `ne`: equals / not equals
- `gt` / `gte` / `lt` / `lte`: comparisons
- `in`: value in list
- `contains`: string contains

**Confidence Scoring:**

Automatically calculated based on:
- Name and description quality (clarity, detail)
- Number of timeframes specified
- Number and detail of entry conditions
- Completeness of exit rules
- Presence of risk parameters

Higher confidence = more complete and actionable strategy.

---

### Prompt Management

The `PromptManager` class handles versioned prompts:

**Default behavior:**
- Inline prompts stored in `strategy_extractor.py`
- No external files needed

**Optional file-based prompts:**
```python
from pathlib import Path

manager = PromptManager(prompts_dir=Path("prompts/"))

# Loads from prompts/extract_strategy.txt if exists
# Falls back to inline default if not
prompt = manager.get("extract_strategy", content="...")
```

**Template variables:**
```python
prompt = manager.get(
    "analyze_chart",
    timeframe="5m",
    symbol="BTC-USD"
)
# Uses Python's string.Template for substitution
```

---

## Configuration

### Environment Variables

Required:
```bash
ANTHROPIC_API_KEY=your-api-key-here
```

Optional (for custom prompts):
```bash
PROMPTS_DIR=/path/to/prompts
```

### Rate Limiting

Default: **50 requests/minute** (leaving 30-50% headroom)

Adjust based on your API tier:
```python
llm = LLMClient(rate_limit_per_minute=80)  # For higher tier
```

---

## Testing

Comprehensive unit tests cover:
- Rate limiter (basic + concurrent requests)
- Cache behavior (hit/miss, key sensitivity)
- LLM generation (success, errors, structured output)
- Strategy extraction (text, images, partial invalid)
- Confidence calculation
- Prompt management

Run tests:
```bash
poetry run pytest tests/unit/test_llm_client.py -v
poetry run pytest tests/unit/test_strategy_extractor.py -v
```

---

## Architecture Decisions

### Why separate LLM client from extractor?

**Single Responsibility:** 
- `LLMClient` = API communication, rate limiting, caching
- `StrategyExtractor` = Domain logic, prompt engineering, validation

This separation allows:
- Testing extractors with mock LLM clients
- Reusing LLM client for other tasks (trade reasoning, learning loop)
- Swapping LLM providers without changing domain logic

### Why in-memory cache?

**Fast and simple:**
- Deterministic calls (`temperature=0`) always return same output
- No external dependencies (Redis, disk)
- Cache resets on restart (acceptable for development)

For production, consider:
- Redis for persistent cache across instances
- Cache TTL for strategies that might evolve
- Cache warming for common queries

### Why structured output?

**Type safety and validation:**
- Pydantic models enforce schema at API boundary
- Invalid LLM output fails fast with clear errors
- No manual JSON parsing and validation
- Self-documenting schemas

---

## Future Enhancements

**Planned:**
- [ ] Persistent cache (Redis)
- [ ] Prompt versioning and A/B testing
- [ ] Token usage tracking and cost monitoring
- [ ] Streaming responses for real-time UI updates
- [ ] Tool use / function calling for trade analysis
- [ ] Batch extraction for large document sets

**Considerations:**
- **Don't** use LLM in hot path (pattern detection)
- **Do** use LLM for reasoning and learning
- Keep prompts versioned and tested
- Monitor API costs per operation type

---

## References

- [Anthropic Claude API Docs](https://docs.anthropic.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- Skills: `llm_integration.md`, `data_engineering.md`
- Types: `src/hl_bot/types.py`
