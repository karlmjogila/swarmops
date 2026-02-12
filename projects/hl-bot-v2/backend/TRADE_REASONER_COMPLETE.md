# Trade Reasoner Implementation - COMPLETE ✅

**Task ID:** trade-reasoner  
**Date:** 2026-02-11  
**Status:** ✅ COMPLETE

---

## 📋 Overview

Implemented a comprehensive trade reasoning LLM component that provides intelligent analysis of trade setups, risk assessment, and post-trade learning. The system uses Claude for reasoning while maintaining safety through validation and guardrails.

## 🎯 Implementation Summary

### Core Components

#### 1. **TradeReasoner Service** (`src/hl_bot/services/trade_reasoner.py`)

Main service class providing four key functions:

- **`analyze_setup()`** - Pre-trade analysis with reasoning and risk assessment
- **`assess_risk()`** - Guardrail function to filter high-risk setups
- **`review_outcome()`** - Post-trade analysis extracting lessons learned
- **`aggregate_learnings()`** - Pattern recognition across multiple trades

#### 2. **Structured Output Models**

Using Pydantic for validated LLM responses:

- `RiskAssessment` - Risk level, concerns, probability, position sizing
- `SetupAnalysis` - Complete pre-trade analysis
- `OutcomeAnalysis` - Post-trade review with lessons
- `LearningInsight` - Aggregated insights from trade patterns

#### 3. **Prompt Management**

- `ReasonerPromptManager` - Version-controlled prompt templates
- Three main prompts: `analyze_setup`, `review_outcome`, `aggregate_learnings`
- Clear structure: role, context, task, format, constraints
- Supports file-based overrides for customization

## 🔑 Key Features

### Pre-Trade Analysis
```python
analysis = await reasoner.analyze_setup(
    signal=signal,
    recent_candles=candles,
    confluence_score=confluence,
)
# Returns: reasoning, confluence breakdown, risk assessment, key observations
```

### Risk Guardrails
```python
passes = await reasoner.assess_risk(signal, analysis)
# Hard filters:
# - High risk level → reject
# - Win probability < 40% → reject
# - LLM recommends skip → reject
# - Confluence score < 40 → reject
```

### Post-Trade Learning
```python
outcome = await reasoner.review_outcome(
    trade=trade,
    entry_reasoning=reasoning,
    entry_candles=entry_candles,
    trade_candles=trade_candles,
)
# Returns: what happened, what worked/didn't, lessons, validity rating
```

### Learning Aggregation
```python
insights = await reasoner.aggregate_learnings(
    trade_summaries=summaries,
    min_sample_size=3,
)
# Extracts patterns like:
# "LE candle setups in drive phase have 65% win rate vs 45% in range"
```

## 🧪 Test Coverage

**Location:** `tests/unit/test_trade_reasoner.py`

- ✅ 20 comprehensive unit tests (all passing)
- ✅ Setup analysis (success + high risk scenarios)
- ✅ Risk assessment filters (all failure paths)
- ✅ Outcome review (win + loss scenarios)
- ✅ Learning aggregation
- ✅ Helper functions (formatting, validation, parsing)
- ✅ Error handling (LLM failures, invalid data)

```bash
poetry run pytest tests/unit/test_trade_reasoner.py -v
# Result: 20 passed in 0.41s
```

## 📊 Quality Checklist

Following **LLM Integration Excellence** principles:

- [x] API key from environment variable (via LLMClient)
- [x] Error handling for all LLM calls (rate limits, timeouts, server errors)
- [x] Structured outputs validated against Pydantic models
- [x] Prompts stored as constants with file override support
- [x] Model selection appropriate for task (Sonnet by default)
- [x] Temperature settings: 0.1 for slight variation in explanations
- [x] Token budget managed (truncation for long inputs via LLMClient)
- [x] Tool execution validated (risk assessment guardrails)
- [x] Financial operations validated after LLM generation
- [x] Comprehensive test coverage with edge cases
- [x] Cost tracking via LLMClient rate limiter
- [x] Guardrails: probability capping, invalidation level validation

## 🔒 Safety Features

### 1. **Input Validation**
- Pydantic models enforce data structure
- Price levels validated against signal data
- Probability estimates capped at 90% (prevents overconfidence)

### 2. **Output Guardrails**
- Risk assessment filters reject dangerous setups
- Invalidation levels checked for reasonableness
- Minimum string lengths ensure substantive analysis

### 3. **Error Handling**
- All LLM calls wrapped in try-except
- Graceful degradation on failures
- Detailed logging for debugging

## 📁 File Structure

```
backend/
├── src/hl_bot/services/
│   └── trade_reasoner.py          # Main service (689 lines)
├── tests/unit/
│   └── test_trade_reasoner.py     # Test suite (603 lines)
└── TRADE_REASONER_COMPLETE.md     # This file
```

## 🔗 Integration Points

### Database Models (already exist)
- `TradeDecision` - Stores reasoning, risk assessment, outcome analysis
- `LearningJournal` - Stores aggregated insights
- `Trade` - Links to decision via relationship

### Services Used
- `LLMClient` - Handles all Claude API communication
  - Rate limiting (50 req/min with headroom)
  - Caching for deterministic calls (temperature=0)
  - Structured output with `generate_structured()`
  - Error handling and retries

### Type Definitions
- `Signal` - Trade signal with all context
- `Trade` - Completed trade with P&L
- `Candle` - OHLCV data for context
- `ConfluenceScore` - Multi-timeframe alignment

## 🎨 Design Patterns

1. **Prompt as Code** - Templates versioned in code, file overrides supported
2. **Structured Outputs** - Always use Pydantic for validation
3. **Fail-Safe Defaults** - Conservative guardrails, reject uncertain setups
4. **Separation of Concerns** - Analysis vs filtering vs learning
5. **Async-First** - All LLM calls are async for performance

## 🚀 Usage Examples

### Basic Setup Analysis
```python
from hl_bot.services.trade_reasoner import TradeReasoner
from hl_bot.services.llm_client import LLMClient

llm = LLMClient()
reasoner = TradeReasoner(llm_client=llm)

# Analyze before taking trade
analysis = await reasoner.analyze_setup(
    signal=my_signal,
    recent_candles=recent_price_action,
    confluence_score=confluence,
)

print(f"Risk Level: {analysis.risk_assessment.risk_level}")
print(f"Win Probability: {analysis.risk_assessment.probability_estimate:.1%}")
print(f"Reasoning: {analysis.reasoning}")

# Apply guardrails
if await reasoner.assess_risk(my_signal, analysis):
    # Safe to execute trade
    execute_trade(my_signal)
else:
    # Skip this setup
    log_rejection(analysis.risk_assessment.concerns)
```

### Post-Trade Review
```python
# After trade closes
outcome = await reasoner.review_outcome(
    trade=closed_trade,
    entry_reasoning=original_analysis.reasoning,
    entry_candles=candles_at_entry,
    trade_candles=candles_during_trade,
)

print(f"Setup was: {outcome.setup_validity}")
print(f"Execution rating: {outcome.performance_rating}/5")
print(f"Lessons: {outcome.lessons_learned}")

# Store in database
save_trade_decision(outcome)
```

### Learning from Multiple Trades
```python
# Periodically aggregate learnings
trade_summaries = [
    {
        "symbol": "BTC-USD",
        "setup": "LE Candle at support",
        "outcome": "TP1 hit",
        "pnl_percent": 1.5,
        "market_phase": "drive",
    },
    # ... more trades
]

insights = await reasoner.aggregate_learnings(
    trade_summaries=trade_summaries,
    min_sample_size=5,
)

for insight in insights:
    print(f"{insight.insight_type}: {insight.insight}")
    print(f"Confidence: {insight.confidence_score:.1%} (n={insight.sample_size})")
    # Store in learning_journal table
```

## 🔄 Next Steps

This component is complete and ready for integration. To activate it:

1. **Integrate with Backtester** - Call `analyze_setup()` before trades
2. **Integrate with Position Manager** - Use `assess_risk()` as a filter
3. **Implement Learning Loop** (next task: `learning-loop`)
   - Periodic review of closed trades
   - Update `learning_journal` table
   - Adjust `effectiveness_score` on `strategy_rules`
4. **Add to Live Trading** - Optional LLM reasoning for real trades
5. **Dashboard UI** - Display reasoning and learnings

## 📈 Performance Considerations

- **Model:** Claude Sonnet (balanced speed/quality)
- **Temperature:** 0.1 (deterministic with slight variation)
- **Max Tokens:** 3000 for analysis, 2000 for learning
- **Rate Limit:** 50 req/min (via LLMClient)
- **Caching:** Automatic for temperature=0 calls
- **Cost:** ~$0.015 per setup analysis (estimated)

## ⚠️ Important Notes

1. **Not in Hot Path** - LLM reasoning is optional for live trading
2. **Validate Critical Ops** - Never trust LLM for position sizing calculations
3. **Guardrails Required** - Always use `assess_risk()` for automated trading
4. **Prompt Versioning** - Track prompt changes like code changes
5. **Test Prompt Changes** - Prompt modification = behavior modification

## 🎓 Lessons Applied

From **LLM Integration Excellence** skill:
- ✅ Structured outputs with schema validation
- ✅ Prompts as versioned templates
- ✅ Model selection by task complexity
- ✅ Cost optimization (right model, caching)
- ✅ Guardrails for financial operations
- ✅ Comprehensive testing of LLM integration

From **Trading Systems Excellence** skill:
- ✅ Safety over speed (reject uncertain setups)
- ✅ Audit everything (structured decision records)
- ✅ Fail closed (conservative filters)
- ✅ Validate before execution (risk assessment)

---

## ✅ Acceptance Criteria

- [x] `analyze_setup()` - Given signal → explains reasoning, risk assessment
- [x] `assess_risk()` - Flags concerns or low-probability setups
- [x] `review_outcome()` - After trade closes, analyzes what worked/didn't
- [x] `aggregate_learnings()` - Aggregates insights across trades
- [x] Structured outputs with Pydantic validation
- [x] Comprehensive test coverage (20 tests, all passing)
- [x] Error handling and guardrails
- [x] Follows LLM Integration Excellence principles
- [x] Ready for integration with backtester and live trading

**Status:** ✅ COMPLETE - Ready for Phase 6 Task 2 (learning-loop)

---

**Implementation Time:** ~4 hours  
**Lines of Code:** ~1,300 (service + tests)  
**Test Coverage:** 100% of public methods
