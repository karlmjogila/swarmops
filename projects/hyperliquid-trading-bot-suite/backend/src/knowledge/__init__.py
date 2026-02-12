"""
Knowledge base module for the Hyperliquid Trading Bot Suite.
Contains data models, repository layer, caching, semantic search, and business logic.
"""

from .models import (
    ContentSource,
    PatternCondition,
    TimeframeAlignment,
    RiskParameters,
    StrategyRule,
    CandleData,
    PriceActionSnapshot,
    TradeRecord,
    LearningEntry,
    StrategyPerformance,
    BacktestConfig,
    BacktestResult,
    IngestPDFRequest,
    IngestVideoRequest,
    IngestionResponse,
)

from .repository import (
    StrategyRuleRepository,
    TradeRecordRepository,
    LearningRepository,
    KnowledgeBaseRepository,
)

from .cache import (
    CacheManager,
    CacheKeys,
    CacheTTL,
    cache_manager,
    get_cache_manager,
)

from .semantic_search import (
    EmbeddingGenerator,
    SemanticSearch,
)

__all__ = [
    # Pydantic models
    "ContentSource",
    "PatternCondition", 
    "TimeframeAlignment",
    "RiskParameters",
    "StrategyRule",
    "CandleData",
    "PriceActionSnapshot",
    "TradeRecord",
    "LearningEntry",
    "StrategyPerformance",
    "BacktestConfig",
    "BacktestResult",
    "IngestPDFRequest",
    "IngestVideoRequest",
    "IngestionResponse",
    
    # Repository classes
    "StrategyRuleRepository",
    "TradeRecordRepository",
    "LearningRepository", 
    "KnowledgeBaseRepository",
    
    # Caching
    "CacheManager",
    "CacheKeys",
    "CacheTTL",
    "cache_manager",
    "get_cache_manager",
    
    # Semantic Search
    "EmbeddingGenerator",
    "SemanticSearch",
]
