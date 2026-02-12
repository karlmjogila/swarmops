# Learning Loop - Quick Start Guide

## Overview

The learning loop enables the trading bot to continuously improve by analyzing trade outcomes and extracting patterns.

## Components

### 1. LearningRepository
**File:** `src/hl_bot/repositories/learning_repository.py`

Database operations for learning journal and strategy effectiveness.

```python
from hl_bot.repositories.learning_repository import LearningRepository

repo = LearningRepository(db_session)

# Get performance stats
perf = repo.get_strategy_performance(strategy_id)
print(f"Win rate: {perf['win_rate']:.2%}")

# Get trade summaries for analysis
summaries = repo.get_trade_summaries_for_learning(
    filters={'symbol': 'BTC-USD'},
    limit=50
)
```

### 2. LearningService
**File:** `src/hl_bot/services/learning_service.py`

Orchestrates the complete feedback loop.

```python
from hl_bot.services.learning_service import LearningService

service = LearningService(learning_repo=repo)

# 1. Analyze individual trade
outcome = await service.analyze_trade_outcome(
    trade=closed_trade,
    entry_reasoning="LE candle at support",
    entry_candles=entry_candles,
    trade_candles=trade_candles,
)

# 2. Aggregate insights from multiple trades
insights = await service.aggregate_learnings(
    filters={'market_phase': 'range'},
    min_trades=5,
    min_confidence=0.7,
)

# 3. Get relevant learnings for current context
relevant = service.get_relevant_learnings(
    context={'setup_type': 'pullback', 'market_phase': 'range'},
    limit=5,
)
```

## Workflow

### Post-Trade Analysis
```
Trade Closes → LLM Analysis → Update Strategy Effectiveness → Store Learnings
```

### Pattern Extraction (Periodic)
```
Fetch Trades → Aggregate with LLM → Filter by Confidence → Store Insights
```

### Apply Learnings
```
New Signal → Get Relevant Insights → Adjust Decision → Execute Trade
```

## Database Tables

### learning_journal
Stores aggregated insights from multiple trades.

| Column | Type | Description |
|--------|------|-------------|
| insight_type | VARCHAR(50) | pattern, setup, market_phase, risk, execution |
| insight | TEXT | The learning/insight |
| confidence_score | FLOAT | 0-1, reliability of insight |
| sample_size | INT | Number of trades analyzed |
| market_conditions | JSONB | Context where insight applies |

### strategy_rules (learning fields)
Tracks strategy performance.

| Column | Type | Description |
|--------|------|-------------|
| effectiveness_score | FLOAT | 0-1, updated by learning loop |
| total_trades | INT | Total trades executed |
| winning_trades | INT | Number of winning trades |

## Integration Example

### With Backtest Runner

```python
async def on_trade_closed(trade: Trade):
    """Called when a trade closes during backtest."""
    
    # Get price action data
    entry_candles = get_candles_at_entry(trade)
    trade_candles = get_candles_during_trade(trade)
    
    # Analyze outcome
    outcome = await learning_service.analyze_trade_outcome(
        trade=trade,
        entry_reasoning=trade.reasoning,
        entry_candles=entry_candles,
        trade_candles=trade_candles,
    )
    
    # Store in trade_decisions table
    await store_trade_decision(
        trade_id=trade.id,
        reasoning=trade.reasoning,
        outcome_analysis=outcome.what_happened,
        lessons_learned=outcome.lessons_learned,
    )
    
    logger.info(
        f"Trade analyzed: {outcome.setup_validity}, "
        f"rating={outcome.performance_rating}/5"
    )
```

### Periodic Learning Aggregation

```python
# Run daily/weekly as a scheduled job
async def aggregate_recent_learnings():
    """Extract patterns from recent trades."""
    
    insights = await learning_service.aggregate_learnings(
        filters={
            'start_time': datetime.now() - timedelta(days=7),
        },
        min_trades=10,
        min_confidence=0.7,
    )
    
    logger.info(f"Generated {len(insights)} new insights")
    
    # Prune low confidence entries
    pruned = learning_service.prune_low_confidence_learnings(
        threshold=0.3
    )
    
    logger.info(f"Deactivated {pruned} low-confidence entries")
    
    # Generate summary
    summary = learning_service.get_learning_summary(days=30)
    
    return {
        'insights': len(insights),
        'pruned': pruned,
        'summary': summary,
    }
```

## Testing

Run the comprehensive test suite:

```bash
cd backend
poetry run pytest tests/unit/test_learning_service.py -v
```

All 13 tests should pass ✅

## Maintenance

### Prune Low Confidence Learnings
```python
# Run weekly
count = learning_service.prune_low_confidence_learnings(threshold=0.3)
```

### Get Learning Summary
```python
summary = learning_service.get_learning_summary(days=30)
print(f"Total: {summary['total_learnings']}")
print(f"Avg confidence: {summary['avg_confidence']:.2%}")
```

## Next Steps

1. **Integrate with Backtest Runner** - Auto-analyze trades as they close
2. **Create API Endpoints** - Expose learning functionality to frontend
3. **Build UI Components** - Display insights and summaries
4. **Schedule Aggregation** - Daily/weekly pattern extraction
5. **Add Metrics** - Track learning effectiveness over time

## Files

- **Repository:** `src/hl_bot/repositories/learning_repository.py`
- **Service:** `src/hl_bot/services/learning_service.py`
- **Tests:** `tests/unit/test_learning_service.py`
- **Models:** Already in `app/db/models.py`
- **Documentation:** `LEARNING_LOOP_IMPLEMENTATION.md`

---

**Status:** ✅ Implementation Complete  
**Tests:** 13/13 Passing  
**Ready for:** Integration with Backtest Runner
