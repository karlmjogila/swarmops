"""
Learning Module

Provides outcome analysis and feedback loop for continuous system improvement.

Key components:
- OutcomeAnalyzer: Analyzes trade outcomes and identifies patterns
- FeedbackLoop: Applies learnings back to the system
- LearningContext: Provides context to trade reasoner
- ImprovementMetrics: Tracks system improvement over time

Author: Hyperliquid Trading Bot Suite
"""

from .outcome_analyzer import (
    OutcomeAnalyzer,
    StrategyAnalysis,
    PatternInsight
)

from .feedback_loop import (
    FeedbackLoop,
    LearningContext,
    ImprovementMetrics,
    ABTestVariant,
    run_feedback_cycle
)


__all__ = [
    # Outcome Analysis
    "OutcomeAnalyzer",
    "StrategyAnalysis",
    "PatternInsight",
    
    # Feedback Loop
    "FeedbackLoop",
    "LearningContext",
    "ImprovementMetrics",
    "ABTestVariant",
    "run_feedback_cycle",
]
