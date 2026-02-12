"""
Detection Module

Comprehensive pattern detection and market analysis components:
- Candle pattern detection
- Market structure analysis
- Market cycle classification
- Multi-timeframe confluence scoring

Author: Hyperliquid Trading Bot Suite
"""

from .candle_patterns import (
    CandlePatternDetector,
    detect_le_patterns,
    detect_all_patterns
)

from .market_structure import (
    MarketStructureAnalyzer,
    StructurePoint,
    SupportResistanceZone,
    TrendAnalysis,
    BreakOfStructure,
    ChangeOfCharacter
)

from .cycle_classifier import (
    MarketCycleClassifier,
    CycleClassification,
    CycleMetrics,
    CycleHistory
)

from .confluence_scorer import (
    ConfluenceScorer,
    ConfluenceScore,
    TimeframeAnalysis,
    SignalGeneration,
    generate_trading_signal
)

__all__ = [
    # Candle Patterns
    "CandlePatternDetector",
    "detect_le_patterns",
    "detect_all_patterns",
    
    # Market Structure
    "MarketStructureAnalyzer",
    "StructurePoint",
    "SupportResistanceZone",
    "TrendAnalysis",
    "BreakOfStructure",
    "ChangeOfCharacter",
    
    # Cycle Classification
    "MarketCycleClassifier",
    "CycleClassification",
    "CycleMetrics",
    "CycleHistory",
    
    # Confluence Scoring
    "ConfluenceScorer",
    "ConfluenceScore",
    "TimeframeAnalysis",
    "SignalGeneration",
    "generate_trading_signal"
]
