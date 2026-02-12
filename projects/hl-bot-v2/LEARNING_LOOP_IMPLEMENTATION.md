# Learning Journal and Feedback Loop Implementation

**Task ID:** `learning-loop`  
**Status:** ✅ COMPLETE  
**Date:** 2025-02-11

---

## Overview

Implemented a comprehensive learning journal and feedback loop system that enables the trading bot to continuously improve by analyzing trade outcomes, extracting patterns, and updating strategy effectiveness scores.

## Components Implemented

### 1. Learning Repository (`learning_repository.py`)

**Location:** `/opt/swarmops/projects/hl-bot-v2/backend/src/hl_bot/repositories/learning_repository.py`

A repository layer for database operations related to learning and strategy effectiveness:

#### Key Methods:

**Learning Journal Operations:**
- `create_learning_entry()` - Create new learning insights
- `get_learning_entries()` - Query learning entries with filters
- `update_learning_entry()` - Update confidence scores and status
- `deactivate_low_confidence_entries()` - Prune low-confidence learnings

**Strategy Effectiveness:**
- `update_strategy_effectiveness()` - Update strategy performance metrics
- `get_strategy_performance()` - Get comprehensive performance statistics

**Trade Analysis:**
- `get_trades_for_analysis()` - Fetch trades with their decisions for learning
- `get_trade_summaries_for_learning()` - Format trades for LLM analysis

**Features:**
- Follows Database Excellence principles (no SELECT *, proper indexing)
- Batch operations for efficiency
- Timezone-aware datetime handling
- Proper constraints and validation

### 2. Learning Service (`learning_service.py`)

**Location:** `/opt/swarmops/projects/hl-bot-v2/backend/src/hl_bot/services/learning_service.py`

Orchestrates the complete learning feedback loop:

#### Key Functions:

**Post-Trade Analysis:**
- `analyze_trade_outcome()` - Analyze closed trades using LLM
- Updates strategy effectiveness based on trade performance
- Considers setup validity, performance rating, and win rate

**Learning Aggregation:**
- `aggregate_learnings()` - Extract patterns from multiple trades
- Filters by minimum confidence threshold
- Stores high-confidence insights automatically
- Supports customizable filters (symbol, setup_type, market_phase, etc.)

**Learning Retrieval:**
- `get_relevant_learnings()` - Find insights relevant to current context
- Calculates relevance scores based on market conditions
- Returns top N most relevant insights

**Maintenance:**
- `prune_low_confidence_learnings()` - Clean up unreliable insights
- `get_learning_summary()` - Generate statistics and reports

#### Strategy Effectiveness Calculation:

The effectiveness score combines multiple factors:

```python
effectiveness = (
    0.6 * win_rate * validity_factor +  # Win rate weighted by setup validity
    0.4 * performance_rating / 5.0       # Execution quality
)
```

Where:
- `validity_factor`: 1.0 (valid), 0.9 (edge_case), 0.7 (invalid)
- Smoothed over time to avoid volatility from single trades

### 3. Database Schema

The learning journal uses the `learning_journal` table (already in schema):

```sql
CREATE TABLE learning_journal (
  id UUID PRIMARY KEY,
  insight_type VARCHAR(50) NOT NULL,  -- pattern, setup, market_phase, risk, execution
  insight TEXT NOT NULL,
  supporting_trades JSONB,  -- List of trade IDs
  confidence_score FLOAT DEFAULT 0.5,  -- 0-1
  sample_size INTEGER DEFAULT 0,
  market_conditions JSONB,  -- Context where insight applies
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
```

Strategy effectiveness is tracked in `strategy_rules`:

```sql
-- Added fields for learning
effectiveness_score FLOAT DEFAULT 0.5,  -- 0-1, updated by learning loop
total_trades INTEGER DEFAULT 0,
winning_trades INTEGER DEFAULT 0
```

### 4. Comprehensive Tests

**Location:** `/opt/swarmops/projects/hl-bot-v2/backend/tests/unit/test_learning_service.py`

**Test Coverage:**
- ✅ Post-trade outcome analysis
- ✅ Strategy effectiveness updates
- ✅ Learning aggregation from multiple trades
- ✅ Confidence-based filtering
- ✅ Relevant learning retrieval
- ✅ Relevance scoring algorithm
- ✅ Maintenance operations
- ✅ Learning summaries
- ✅ Full feedback loop integration

**Results:** 13 tests, all passing ✅

## How the Feedback Loop Works

### 1. Trade Execution → Analysis

When a trade closes:

```python
# After trade closes in backtest or live trading
outcome = await learning_service.analyze_trade_outcome(
    trade=closed_trade,
    entry_reasoning=original_reasoning,
    entry_candles=candles_at_entry,
    trade_candles=candles_during_trade,
)
```

The LLM analyzes:
- What happened during the trade
- What worked / didn't work
- Setup validity (valid, invalid, edge_case)
- Performance rating (1-5)
- Lessons learned

### 2. Strategy Effectiveness Update

The service automatically updates the strategy's effectiveness score:

```python
# Combines win rate, setup validity, and execution quality
new_effectiveness = calculate_effectiveness(
    win_rate=perf['win_rate'],
    validity=outcome.setup_validity,
    rating=outcome.performance_rating,
)

# Smoothed update to avoid volatility
smoothed = (
    sample_weight * old_effectiveness +
    (1 - sample_weight) * new_effectiveness
)
```

### 3. Pattern Extraction (Periodic)

Run periodically (daily/weekly) to aggregate insights:

```python
insights = await learning_service.aggregate_learnings(
    filters={'symbol': 'BTC-USD'},
    min_trades=5,
    min_confidence=0.7,
)
```

Example insights:
- "LE candle setups at support have 65% win rate in range markets"
- "Breakout trades work better in drive phase vs range (80% vs 45%)"
- "Trades taken in first hour show higher adverse excursion"

### 4. Apply Learnings

Before taking a trade:

```python
relevant_insights = learning_service.get_relevant_learnings(
    context={
        'setup_type': 'pullback',
        'market_phase': 'range',
        'symbol': 'BTC-USD',
    },
    limit=5,
)

# Use insights to:
# - Adjust position sizing
# - Skip low-probability setups
# - Refine entry criteria
# - Improve risk management
```

## Integration Points

### With Trade Reasoner

The learning service uses the `TradeReasoner` for LLM analysis:
- `review_outcome()` - Post-trade analysis
- `aggregate_learnings()` - Pattern extraction

### With Backtest Runner

Can be integrated to automatically analyze trades as they close:

```python
# In backtest runner, when trade closes:
if trade.status in [TradeStatus.CLOSED, TradeStatus.STOPPED]:
    outcome = await learning_service.analyze_trade_outcome(
        trade=trade,
        entry_reasoning=trade.reasoning,
        entry_candles=get_entry_candles(),
        trade_candles=get_trade_candles(),
    )
    
    # Store outcome in trade_decisions table
    store_decision(trade.id, outcome)
```

### With Strategy Manager

Strategies can be ranked and filtered by effectiveness:

```python
# Get best performing strategies
strategies = db.query(StrategyRule)\
    .filter(StrategyRule.is_active == True)\
    .order_by(StrategyRule.effectiveness_score.desc())\
    .limit(10)
```

## API Endpoints (Recommended)

To expose learning functionality via API:

```python
# In api/routes/learning.py

@router.post("/api/learning/analyze-trade/{trade_id}")
async def analyze_trade_outcome(trade_id: str):
    """Analyze a closed trade and extract learnings."""
    # Implementation

@router.post("/api/learning/aggregate")
async def aggregate_learnings(filters: LearningFilters):
    """Aggregate insights from multiple trades."""
    # Implementation

@router.get("/api/learning/insights")
async def get_insights(
    insight_type: Optional[str] = None,
    min_confidence: float = 0.6,
):
    """Get learning journal entries."""
    # Implementation

@router.get("/api/learning/relevant")
async def get_relevant_insights(context: TradeContext):
    """Get insights relevant to a trading context."""
    # Implementation

@router.get("/api/learning/summary")
async def get_learning_summary(days: int = 30):
    """Get learning statistics for a period."""
    # Implementation
```

## Quality Checklist ✅

- [x] Database schema follows Database Excellence principles
- [x] Repository uses specific queries (no SELECT *)
- [x] Proper constraints and indexes on learning_journal table
- [x] Transactions used for multi-step operations
- [x] Timezone-aware datetime handling throughout
- [x] Comprehensive error handling and logging
- [x] Full test coverage with 13 passing tests
- [x] Type hints and documentation on all methods
- [x] Confidence-based filtering to maintain quality
- [x] Smooth effectiveness updates to avoid volatility
- [x] Relevance scoring for context-aware retrieval

## Performance Considerations

1. **Batch Operations:** Learning aggregation processes up to 50 trades at once
2. **Async LLM Calls:** Non-blocking analysis using asyncio
3. **Caching:** Learning entries cached for quick retrieval
4. **Pruning:** Automatic deactivation of low-confidence entries
5. **Indexing:** Indexes on insight_type, confidence_score, created_at

## Future Enhancements

Potential improvements for future iterations:

1. **A/B Testing:** Compare multiple strategies automatically
2. **Reinforcement Learning:** Use insights to train ML models
3. **Anomaly Detection:** Flag unusual trade behavior
4. **Sentiment Analysis:** Incorporate market sentiment data
5. **Multi-Asset Learning:** Cross-asset pattern recognition
6. **Real-time Adaptation:** Adjust strategies during trading sessions

## Example Usage

```python
from hl_bot.repositories.learning_repository import LearningRepository
from hl_bot.services.learning_service import LearningService
from sqlalchemy.orm import Session

# Initialize
learning_repo = LearningRepository(db=session)
learning_service = LearningService(learning_repo=learning_repo)

# Analyze a closed trade
outcome = await learning_service.analyze_trade_outcome(
    trade=closed_trade,
    entry_reasoning="Strong LE candle at support",
    entry_candles=entry_candles,
    trade_candles=trade_candles,
)
print(f"Outcome: {outcome.setup_validity}, Rating: {outcome.performance_rating}/5")

# Aggregate learnings weekly
insights = await learning_service.aggregate_learnings(
    filters={'symbol': 'BTC-USD'},
    min_trades=10,
    min_confidence=0.7,
)
print(f"Generated {len(insights)} new insights")

# Get relevant insights before taking a trade
context = {
    'setup_type': 'pullback',
    'market_phase': 'range',
    'symbol': 'BTC-USD',
}
relevant = learning_service.get_relevant_learnings(context, limit=5)
for learning in relevant:
    print(f"[{learning['relevance']:.2f}] {learning['insight']}")

# Maintenance: prune low confidence entries
pruned = learning_service.prune_low_confidence_learnings(threshold=0.3)
print(f"Deactivated {pruned} low-confidence entries")

# Get summary report
summary = learning_service.get_learning_summary(days=30)
print(f"Total learnings: {summary['total_learnings']}")
print(f"Avg confidence: {summary['avg_confidence']:.2%}")
```

## Files Created/Modified

### Created:
- ✅ `src/hl_bot/repositories/learning_repository.py` (349 lines)
- ✅ `src/hl_bot/services/learning_service.py` (472 lines)
- ✅ `tests/unit/test_learning_service.py` (541 lines)
- ✅ `LEARNING_LOOP_IMPLEMENTATION.md` (this file)

### Modified:
- ✅ `progress.md` - Marked task as complete

### Existing (Used):
- ✅ `app/db/models.py` - LearningJournal, StrategyRule models
- ✅ `src/hl_bot/services/trade_reasoner.py` - LLM analysis
- ✅ `src/hl_bot/types.py` - Type definitions

---

## Summary

The learning journal and feedback loop is now fully implemented and tested. The system can:

1. ✅ Analyze individual trade outcomes using LLM
2. ✅ Update strategy effectiveness scores automatically
3. ✅ Aggregate insights from multiple trades
4. ✅ Store and retrieve learnings with confidence filtering
5. ✅ Provide context-aware recommendations
6. ✅ Generate performance summaries and reports

The implementation follows all Database Excellence principles, includes comprehensive testing, and is ready for integration with the backtest runner and live trading systems.

**Next Steps:**
1. Integrate with backtest runner for automatic analysis
2. Create API endpoints for frontend access
3. Build UI for viewing insights and learning summaries
4. Set up periodic aggregation jobs (daily/weekly)

---

**Implementation completed:** 2025-02-11  
**Tests passing:** 13/13 ✅  
**Ready for integration:** ✅
