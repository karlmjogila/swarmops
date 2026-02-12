"""Pattern detection modules for market analysis.

This package provides deterministic pattern detection including:
- Market structure analysis (swings, BOS, CHoCH)
- Candle pattern recognition
- Support/resistance zones
- Multi-timeframe confluence scoring
- Trading signal generation
"""

from .candles import (
    CandlePatternType,
    PatternSignal,
    DetectedPattern,
    CandlePatternDetector,
)

from .zones import (
    ZoneType,
    ZoneStrength,
    ZoneTouch,
    SupportResistanceZone,
    SupportResistanceDetector,
)

from .confluence import (
    ConfluenceSignal,
    TimeframeAnalysis,
    ConfluenceScore,
    MultiTimeframeConfluenceScorer,
    score_confluence,
)

from .signals import (
    SignalGenerator,
    SignalGenerationConfig,
    SignalValidationResult,
    TradeLevels,
    MinimumRR,
    generate_signal,
)

__all__ = [
    # Candle patterns
    "CandlePatternType",
    "PatternSignal",
    "DetectedPattern",
    "CandlePatternDetector",
    # Support/Resistance zones
    "ZoneType",
    "ZoneStrength",
    "ZoneTouch",
    "SupportResistanceZone",
    "SupportResistanceDetector",
    # Multi-timeframe confluence
    "ConfluenceSignal",
    "TimeframeAnalysis",
    "ConfluenceScore",
    "MultiTimeframeConfluenceScorer",
    "score_confluence",
    # Signal generation
    "SignalGenerator",
    "SignalGenerationConfig",
    "SignalValidationResult",
    "TradeLevels",
    "MinimumRR",
    "generate_signal",
]
