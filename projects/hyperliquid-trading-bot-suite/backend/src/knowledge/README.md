# Knowledge Base Repository Layer

Complete repository layer for managing strategy rules, trade records, and learning insights with caching and semantic search capabilities.

## Features

✅ **CRUD Operations** - Create, Read, Update, Delete for all knowledge entities  
✅ **Redis Caching** - Intelligent caching layer for frequently accessed data  
✅ **Semantic Search** - Vector-based similarity search using pgvector  
✅ **Performance Tracking** - Automated statistics and performance metrics  
✅ **Type Safety** - Full Pydantic model validation  
✅ **Comprehensive Tests** - Unit tests for all functionality

---

## Quick Start

### Basic Usage

```python
from src.knowledge import KnowledgeBaseRepository
from src.knowledge.models import StrategyRule, ContentSource, RiskParameters
from src.types import EntryType, SourceType

# Use with context manager (recommended)
with KnowledgeBaseRepository() as kb_repo:
    # Create a strategy rule
    rule = StrategyRule(
        name="LE Pattern Strategy",
        source=ContentSource(
            type=SourceType.PDF,
            ref="/path/to/strategy.pdf"
        ),
        entry_type=EntryType.LE,
        conditions=[...],
        risk_params=RiskParameters(risk_percent=2.0),
        confidence=0.7
    )
    
    rule_id = kb_repo.strategy_rules.create(rule)
    
    # Retrieve the rule
    retrieved = kb_repo.strategy_rules.get_by_id(rule_id)
    
    # Search for similar rules
    similar = kb_repo.strategy_rules.find_similar_rules(rule_id, limit=5)
```

---

## Components

### 1. Repository Layer (`repository.py`)

Core CRUD operations with intelligent caching.

#### StrategyRuleRepository

Manages trading strategy rules.

```python
# Create
rule_id = repo.strategy_rules.create(strategy_rule)

# Read
rule = repo.strategy_rules.get_by_id(rule_id)
all_rules = repo.strategy_rules.get_all(min_confidence=0.7)

# Search
results = repo.strategy_rules.search_by_text("LE pattern")
similar = repo.strategy_rules.find_similar_rules(rule_id, limit=10)

# Update performance
repo.strategy_rules.update_performance(
    rule_id=rule_id,
    win_rate=0.65,
    avg_r_multiple=1.5
)

# Delete
repo.strategy_rules.delete(rule_id)
```

#### TradeRecordRepository

Manages trade execution records.

```python
# Create trade
trade_id = repo.trades.create(trade_record)

# Get open trades
open_trades = repo.trades.get_open_trades(asset="ETH-USD")

# Update trade exit
repo.trades.update_trade_exit(
    trade_id=trade_id,
    exit_price=2600.0,
    exit_reason="tp1",
    outcome="win",
    pnl_r=2.0
)

# Get performance stats
stats = repo.trades.get_performance_stats(
    strategy_rule_id=rule_id,
    days_back=30
)
```

#### LearningRepository

Manages learning insights from trade outcomes.

```python
# Create learning entry
entry_id = repo.learning.create(learning_entry)

# Get insights for a strategy
insights = repo.learning.get_by_strategy_rule(rule_id)

# Get high-confidence insights
high_conf = repo.learning.get_high_confidence_insights(min_confidence=0.8)

# Update validation
repo.learning.update_validation(entry_id)
```

---

### 2. Caching Layer (`cache.py`)

Redis-based caching for performance optimization.

```python
from src.knowledge.cache import cache_manager, CacheKeys, CacheTTL

# Direct cache usage
cache_manager.set("my_key", {"data": "value"}, ttl=CacheTTL.HOUR)
value = cache_manager.get("my_key")

# Cache keys
strategy_key = CacheKeys.strategy_rule(rule_id)
open_trades_key = CacheKeys.open_trades("ETH-USD")

# Cache management
cache_manager.delete_pattern("trading_bot:strategy_rules:*")
cache_manager.flush_all()  # Clear all cache (use with caution)
```

#### Cache TTLs

| Entity | Default TTL | Purpose |
|--------|-------------|---------|
| Strategy Rule | 1 hour | Rules change infrequently |
| Trade Record | 15 minutes | Trades update semi-frequently |
| Open Trades | 1 minute | Fast-changing data |
| Performance Stats | 5 minutes | Computed statistics |
| Similar Rules | 1 hour | Expensive computation |

#### Cache Decorator

```python
from src.knowledge.cache import cached, CacheTTL

@cached(ttl=CacheTTL.FIFTEEN_MINUTES)
def expensive_computation(param):
    # ... complex logic ...
    return result
```

---

### 3. Semantic Search (`semantic_search.py`)

Vector-based similarity search using pgvector and embeddings.

#### Features

- **Vector Embeddings**: Generates embeddings for strategy rules
- **Similarity Search**: Find similar rules based on semantic meaning
- **Automatic Indexing**: Embeddings generated on rule creation
- **Fallback Mode**: Tag-based similarity when embeddings unavailable

#### Usage

```python
from src.knowledge.semantic_search import SemanticSearch

with KnowledgeBaseRepository() as kb_repo:
    # Find similar rules
    similar_rules = kb_repo.strategy_rules.find_similar_rules(
        rule_id="rule-123",
        limit=10,
        min_confidence=0.6
    )
    
    for rule, similarity_score in similar_rules:
        print(f"{rule.name}: {similarity_score:.2f}")
    
    # Semantic text search
    results = kb_repo.strategy_rules.search_semantic(
        query_text="bullish LE pattern with 4H bias",
        limit=20
    )
```

#### Embedding Generation

The system uses OpenAI's embedding API when available, with a fallback to hash-based embeddings for development:

```python
from src.knowledge.semantic_search import EmbeddingGenerator

generator = EmbeddingGenerator()
embedding = generator.generate_embedding("LE pattern on 15M timeframe")
# Returns: List[float] with 1536 dimensions
```

#### pgvector Setup

Requires PostgreSQL with pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE strategy_rules 
ADD COLUMN embedding vector(1536);

CREATE INDEX idx_strategy_embedding 
ON strategy_rules 
USING ivfflat (embedding vector_cosine_ops);
```

---

## Data Models

### StrategyRule

```python
StrategyRule(
    id="rule-123",
    name="LE Pattern Strategy",
    source=ContentSource(
        type=SourceType.PDF,
        ref="/path/to/strategy.pdf",
        page_number=10
    ),
    entry_type=EntryType.LE,
    conditions=[PatternCondition(...)],
    confluence_required=[TimeframeAlignment(...)],
    risk_params=RiskParameters(
        risk_percent=2.0,
        tp_levels=[1.0, 2.0],
        sl_distance="below_low"
    ),
    confidence=0.7,
    description="Liquidity engulf pattern",
    tags=["LE", "bullish"]
)
```

### TradeRecord

```python
TradeRecord(
    id="trade-456",
    strategy_rule_id="rule-123",
    asset="ETH-USD",
    direction=OrderSide.LONG,
    entry_price=2500.0,
    position_size=1.0,
    reasoning="Strong LE pattern with 4H bias",
    price_action_context=PriceActionSnapshot(...),
    confidence=0.75
)
```

### LearningEntry

```python
LearningEntry(
    id="learning-789",
    strategy_rule_id="rule-123",
    insight="LE patterns work better after range consolidation",
    supporting_trades=["trade-1", "trade-2"],
    confidence=0.8,
    impact_type="success_factor"
)
```

---

## Performance Optimization

### Caching Strategy

1. **Strategy Rules**: Cached for 1 hour (infrequently changed)
2. **Trade Records**: Cached for 15 minutes (moderate updates)
3. **Open Trades**: Cached for 1 minute (rapidly changing)
4. **Performance Stats**: Cached for 5 minutes (expensive computation)

### Cache Invalidation

Caches are automatically invalidated when:
- Creating new entities
- Updating existing entities
- Deleting entities
- Closing trades (invalidates open trades cache)

### Database Indexes

Optimized indexes for common queries:
- `idx_strategy_entry_type`: Fast filtering by entry type
- `idx_trade_asset_time`: Time-series trade queries
- `idx_strategy_embedding`: Vector similarity search
- `idx_learning_impact_confidence`: High-confidence insights

---

## Testing

Comprehensive unit tests in `backend/tests/test_knowledge_repository.py`.

### Running Tests

```bash
# Run all tests
pytest backend/tests/test_knowledge_repository.py -v

# Run specific test class
pytest backend/tests/test_knowledge_repository.py::TestStrategyRuleRepository -v

# Run with coverage
pytest backend/tests/test_knowledge_repository.py --cov=src.knowledge
```

### Test Coverage

- ✅ CRUD operations for all entities
- ✅ Filtering and searching
- ✅ Performance metric calculations
- ✅ Cache behavior (when enabled)
- ✅ Edge cases and error handling
- ✅ Integrated workflows

---

## Configuration

Configure via environment variables in `.env`:

```bash
# Redis
REDIS_URL=redis://localhost:6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=10

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-your-api-key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/trading_bot
```

---

## Best Practices

### 1. Use Context Managers

```python
# Good ✅
with KnowledgeBaseRepository() as kb_repo:
    rule = kb_repo.strategy_rules.get_by_id(rule_id)

# Avoid ❌
kb_repo = KnowledgeBaseRepository()
rule = kb_repo.strategy_rules.get_by_id(rule_id)
# (Session not automatically closed)
```

### 2. Leverage Caching

```python
# Cache is enabled by default
rule = repo.strategy_rules.get_by_id(rule_id)  # Uses cache

# Disable cache for fresh data
rule = repo.strategy_rules.get_by_id(rule_id, use_cache=False)
```

### 3. Batch Operations

```python
# Create multiple rules efficiently
with KnowledgeBaseRepository() as kb_repo:
    for rule in strategy_rules:
        kb_repo.strategy_rules.create(rule)
    # Commit happens once when context exits
```

### 4. Update Performance Regularly

```python
# After each trade closes
stats = repo.trades.get_performance_stats(strategy_rule_id=rule_id)
repo.strategy_rules.update_performance(
    rule_id=rule_id,
    win_rate=stats.win_rate,
    avg_r_multiple=stats.avg_r_multiple,
    confidence=calculate_new_confidence(stats)
)
```

---

## API Integration Example

```python
from fastapi import APIRouter, Depends
from src.knowledge import KnowledgeBaseRepository, StrategyRule

router = APIRouter()

@router.get("/strategies/{rule_id}")
async def get_strategy(rule_id: str):
    with KnowledgeBaseRepository() as kb_repo:
        rule = kb_repo.strategy_rules.get_by_id(rule_id)
        if not rule:
            raise HTTPException(status_code=404)
        return rule

@router.get("/strategies/{rule_id}/similar")
async def get_similar_strategies(rule_id: str, limit: int = 10):
    with KnowledgeBaseRepository() as kb_repo:
        similar = kb_repo.strategy_rules.find_similar_rules(
            rule_id, 
            limit=limit
        )
        return [
            {"rule": rule, "similarity": score}
            for rule, score in similar
        ]

@router.post("/strategies")
async def create_strategy(strategy: StrategyRule):
    with KnowledgeBaseRepository() as kb_repo:
        rule_id = kb_repo.strategy_rules.create(strategy)
        return {"id": rule_id}
```

---

## Troubleshooting

### pgvector Not Available

If pgvector is not installed, semantic search falls back to tag-based similarity:

```python
# Check if pgvector is available
from src.knowledge.semantic_search import SemanticSearch
search = SemanticSearch(session)
# Will print warning if pgvector extension can't be created
```

### Redis Connection Issues

If Redis is unavailable, disable caching:

```python
repo = StrategyRuleRepository(session=session, use_cache=False)
```

### Slow Queries

1. Check database indexes are created
2. Enable query logging: `DB_ECHO=true`
3. Use caching for read-heavy operations
4. Consider read replicas for large datasets

---

## Future Enhancements

- [ ] Async repository operations
- [ ] Distributed caching with Redis Cluster
- [ ] Advanced semantic search with fine-tuned models
- [ ] Automated cache warming
- [ ] GraphQL API support
- [ ] Real-time change notifications via WebSocket
- [ ] Multi-tenant support

---

## Related Documentation

- [Database Models](../database/models.py) - SQLAlchemy ORM models
- [Pydantic Models](./models.py) - Request/response validation
- [Configuration](../config.py) - Application settings
- [API Routes](../api/routes/) - REST API endpoints

---

## License

Part of the Hyperliquid Trading Bot Suite.
