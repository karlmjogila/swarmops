# Trade Reasoner

The Trade Reasoner uses Claude LLM to generate human-readable explanations for trading signals. It takes the output from the confluence scorer and produces detailed reasoning about why a trade should be taken, using the language of price action and market structure.

## Overview

When the pattern detection engine generates a high-confidence signal, the Trade Reasoner:

1. **Gathers Context** - Collects multi-timeframe candle data and analysis
2. **Queries Claude** - Sends structured prompt with signal and market context
3. **Parses Response** - Extracts structured reasoning into TradeReasoning object
4. **Returns Explanation** - Provides human-readable trade reasoning

## Key Features

- **Multi-Timeframe Context** - Incorporates analysis from all timeframes
- **Structured Output** - Returns well-organized reasoning with specific sections
- **Professional Language** - Uses proper trading terminology (BOS, ChoCH, zones, etc.)
- **Risk Assessment** - Identifies risks and explains mitigation strategies
- **Trade Plan** - Explains entry, stop loss, take profit, and position management
- **Fallback Mode** - Generates basic reasoning if LLM call fails

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TRADE REASONER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: SignalGeneration + Multi-TF Candle Data            │
│         ↓                                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │  Context Preparation                         │          │
│  │  - Extract signal details                    │          │
│  │  - Aggregate timeframe analyses              │          │
│  │  - Format recent candles                     │          │
│  │  - Include confluence factors                │          │
│  └──────────────────────────────────────────────┘          │
│         ↓                                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │  Prompt Generation                           │          │
│  │  - System prompt (trader persona)            │          │
│  │  - User prompt (signal + context)            │          │
│  └──────────────────────────────────────────────┘          │
│         ↓                                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │  Claude API Call                             │          │
│  │  - Model: claude-3-sonnet (for speed)       │          │
│  │  - Temperature: 0.3 (natural but consistent)│          │
│  │  - Max tokens: 2000                          │          │
│  └──────────────────────────────────────────────┘          │
│         ↓                                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │  Response Parsing                            │          │
│  │  - Extract JSON from response                │          │
│  │  - Validate structure                        │          │
│  │  - Fallback if parsing fails                 │          │
│  └──────────────────────────────────────────────┘          │
│         ↓                                                   │
│  Output: TradeReasoning (structured explanation)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Models

### TradeReasoning

Complete structured reasoning output:

```python
class TradeReasoning(BaseModel):
    # Core reasoning
    setup_description: str          # Setup in price action terms
    why_now: str                    # Why this specific entry moment
    confluence_factors: List[str]   # Factors supporting the trade
    expected_price_action: str      # Expected movement
    
    # Risk assessment
    risks: List[str]                # Key risks
    risk_mitigation: str            # How risks are addressed
    
    # Trade plan
    entry_rationale: str            # Entry justification
    stop_loss_rationale: str        # SL placement logic
    take_profit_rationale: str      # TP level reasoning
    position_management: str        # How to manage position
    
    # Context
    market_context: str             # HTF bias and structure
    cycle_phase: str                # Market cycle implications
    
    # Summary
    confidence_explanation: str     # Why this confidence level
    one_sentence_summary: str       # Concise trade thesis
    
    # Metadata
    generated_at: datetime
    model_used: str
    token_count: Optional[int]
```

## Usage

### Basic Usage

```python
from trading.trade_reasoner import TradeReasoner, explain_trade
from detection.confluence_scorer import ConfluenceScorer

# Initialize
reasoner = TradeReasoner()

# Generate signal with confluence scorer
scorer = ConfluenceScorer()
signal = scorer.generate_signal(asset, candle_data)

# Generate reasoning
reasoning = await reasoner.generate_reasoning(
    signal=signal,
    candle_data=candle_data,
    timeframe_analyses=analyses
)

# Access structured output
print(reasoning.one_sentence_summary)
print("\nConfluence Factors:")
for factor in reasoning.confluence_factors:
    print(f"  - {factor}")
```

### Convenience Function

```python
from trading.trade_reasoner import explain_trade

# One-line reasoning generation
reasoning = await explain_trade(signal, candle_data, analyses)
```

### Display Formatting

```python
from trading.trade_reasoner import format_reasoning_for_display

# Format for human-readable display
formatted = format_reasoning_for_display(reasoning)
print(formatted)
```

Output:
```
================================================================================
TRADE REASONING
================================================================================

📊 LONG LE setup with 78% multi-timeframe confluence at $2,055 demand zone

SETUP DESCRIPTION:
Strong bullish structure on 4H with higher highs and higher lows. Price has 
pulled back to 4H demand zone at $2,050 with 15M LE candle showing rejection 
and commitment to the upside.

WHY NOW:
15M LE candle with 70% close in upper third, confirming bulls taking control 
at the demand zone. Volume increasing on the bullish candle.

CONFLUENCE FACTORS:
  1. 4H shows strong bullish trend with higher highs and higher lows
  2. 1H confirmed break of structure above key resistance
  3. 15M LE candle with 70% close in upper third
  4. Price interacting with 4H demand zone at $2,050
  5. Market in drive phase with strong momentum

...
```

## Integration Points

### With Confluence Scorer

```python
# Pattern detection generates signal
scorer = ConfluenceScorer()
signal = scorer.generate_signal(asset, candle_data)

if signal.generates_signal:
    # Trade reasoner explains why
    reasoning = await reasoner.generate_reasoning(
        signal, candle_data
    )
    
    # Log to trade history
    trade_record = TradeRecord(
        strategy_rule_id=signal.matched_rule_id,
        asset=signal.asset,
        direction=signal.direction,
        entry_price=signal.entry_price,
        reasoning=reasoning.one_sentence_summary,
        detailed_reasoning=reasoning.dict()
    )
```

### With Backtest Engine

```python
# During backtest replay
for candle in historical_data:
    signal = scorer.check_for_signal(candle)
    
    if signal:
        # Generate reasoning for backtested trade
        reasoning = await reasoner.generate_reasoning(
            signal, get_multi_tf_context(candle.timestamp)
        )
        
        # Store in backtest results
        backtest_trade = {
            'signal': signal,
            'reasoning': reasoning,
            'timestamp': candle.timestamp
        }
```

### With Live Trading

```python
# Real-time signal processing
async def process_live_signal(signal: SignalGeneration):
    # Generate reasoning BEFORE executing
    reasoning = await reasoner.generate_reasoning(
        signal, live_candle_data
    )
    
    # Review reasoning (could include human review step)
    if reasoning.confidence_score > 0.7:
        # Execute trade
        position = await execute_trade(signal)
        
        # Log reasoning with trade
        await store_trade_with_reasoning(
            position, signal, reasoning
        )
```

## Configuration

Settings are loaded from `config.py`:

```python
# Claude configuration
claude_reasoning_model: str = "claude-3-sonnet-20240229"
claude_max_tokens: int = 2000
claude_temperature: float = 0.3
anthropic_api_key: str  # From environment
```

Override with custom settings:

```python
from config import Settings

custom_settings = Settings(
    claude_reasoning_model="claude-3-opus-20240229",  # Use Opus for better quality
    claude_temperature=0.2  # More deterministic
)

reasoner = TradeReasoner(settings=custom_settings)
```

## Prompt Engineering

### System Prompt

Establishes the LLM's role as an expert price action trader:
- Multi-timeframe analysis expertise
- Professional trading terminology
- Focus on structure, cycles, confluence
- Risk-aware reasoning

### User Prompt

Provides structured input:
1. Signal overview (direction, entry, stops, targets)
2. Multi-timeframe market context
3. Confluence factors and warnings
4. Specific output format requirements

The prompt is designed to elicit:
- Specific price levels and observations
- Professional technical analysis language
- Risk assessment alongside bullish/bearish case
- Actionable trade management guidance

## Error Handling

### Fallback Reasoning

If Claude API fails or response parsing fails:

```python
# Automatic fallback to rule-based reasoning
reasoning = reasoner._create_fallback_reasoning(response, signal)

# Still returns TradeReasoning object
# Uses signal data to populate fields
# Logs warning for monitoring
```

### Exception Handling

```python
try:
    reasoning = await reasoner.generate_reasoning(signal, candle_data)
except TradeReasoningError as e:
    logger.error(f"Reasoning failed: {e}")
    # Handle error (use fallback, skip trade, etc.)
```

## Performance

- **Latency**: ~1-3 seconds per reasoning generation (Claude Sonnet)
- **Tokens**: ~500-1500 tokens per request (input + output)
- **Cost**: ~$0.003-$0.008 per reasoning (Sonnet pricing)
- **Caching**: Context preparation reusable across multiple reasoning calls

## Best Practices

1. **Always include timeframe_analyses** - Richer context = better reasoning
2. **Log all reasoning** - Critical for learning and improvement
3. **Review reasoning patterns** - Identify what Claude focuses on
4. **A/B test prompts** - Iterate on prompt engineering
5. **Monitor fallback rate** - Track API failures
6. **Validate structured output** - Ensure all fields populated

## Examples

See `trade_reasoner_example.py` for complete working examples:

```bash
cd backend/src/trading
python -m trading.trade_reasoner_example
```

Examples included:
1. Basic trade reasoning generation
2. Using TradeReasoner instance directly
3. SHORT signal reasoning
4. Error handling and fallbacks

## Testing

```python
# Unit tests
pytest backend/tests/trading/test_trade_reasoner.py

# Integration tests with real API
pytest backend/tests/trading/test_trade_reasoner_integration.py --api-key=$ANTHROPIC_API_KEY
```

## Future Enhancements

- **Strategy Matching** - Query knowledge base for similar historical setups
- **Learning Integration** - Include past trade outcomes in context
- **Multi-Model Support** - Allow switching between Claude/GPT/local models
- **Reasoning Templates** - Cache common reasoning patterns
- **Confidence Scoring** - LLM rates its own reasoning confidence
- **Adversarial Reasoning** - Generate both bull and bear cases

## Related Components

- **ConfluenceScorer** (`detection/confluence_scorer.py`) - Generates signals
- **StrategyExtractor** (`ingestion/strategy_extractor.py`) - Extracts rules from content
- **TradeRecord** (`knowledge/models.py`) - Stores trades with reasoning
- **RiskManager** (`trading/risk_manager.py`) - Validates trade parameters

---

**Status**: ✅ Complete and production-ready

**Last Updated**: 2025-02-11

**Maintainer**: Hyperliquid Trading Bot Suite Team
