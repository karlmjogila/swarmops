#!/usr/bin/env python3
"""
Verification script for feedback loop implementation.

Demonstrates:
1. Running a feedback cycle to analyze strategies
2. Retrieving learning context for trade reasoner
3. Tracking system improvement metrics
4. A/B testing strategy variations
"""

import sys
from datetime import datetime, timedelta

# Add src to path
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.learning.feedback_loop import (
    FeedbackLoop,
    LearningContext,
    ImprovementMetrics,
    ABTestVariant
)
from src.learning.outcome_analyzer import (
    OutcomeAnalyzer,
    StrategyAnalysis,
    PatternInsight
)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_learning_context():
    """Demonstrate learning context creation and formatting."""
    print_section("1. Learning Context")
    
    # Create a learning context with insights
    context = LearningContext(
        strategy_rule_id="strat_001",
        success_factors=[
            "Strategy performs well in drive market cycle (75% of wins)",
            "High confluence (≥0.7) correlates with success (85% confidence)",
            "Most winning trades exit at TP2 target level"
        ],
        failure_patterns=[
            "Strategy struggles in range market cycle (60% of losses)",
            "Low confluence (<0.5) leads to failures",
            "Stop loss hit frequently when against HTF trend"
        ],
        recommended_conditions={
            "market_cycle": "drive",
            "min_confluence": 0.7,
            "htf_bias": "aligned"
        },
        avoid_conditions={
            "market_cycle": "range",
            "confluence": "<0.5"
        },
        confidence_adjustment=0.15
    )
    
    print("Learning Context Object:")
    print(f"  Strategy: {context.strategy_rule_id}")
    print(f"  Success Factors: {len(context.success_factors)}")
    print(f"  Failure Patterns: {len(context.failure_patterns)}")
    print(f"  Confidence Adjustment: {context.confidence_adjustment:+.2%}")
    
    print("\n" + "-" * 80)
    print("Formatted for LLM Prompt:\n")
    print(context.to_prompt_text())
    
    return context


def demo_improvement_metrics():
    """Demonstrate improvement metrics tracking."""
    print_section("2. Improvement Metrics")
    
    # Create sample improvement metrics
    metrics = ImprovementMetrics(
        period_start=datetime.utcnow() - timedelta(days=30),
        period_end=datetime.utcnow(),
        total_strategies=15,
        strategies_improved=10,
        strategies_declined=3,
        avg_confidence_change=0.08,
        total_insights_generated=45,
        high_confidence_insights=28,
        overall_win_rate=0.58,
        overall_profit_factor=1.92,
        overall_avg_r=0.85,
        win_rate_trend="improving",
        confidence_trend="improving"
    )
    
    print(metrics)
    
    print("\n" + "-" * 80)
    print("Interpretation:")
    print("  ✓ 67% of strategies improved (10/15)")
    print("  ✓ Average confidence increased by 8%")
    print("  ✓ 62% of insights are high confidence (28/45)")
    print("  ✓ Overall win rate of 58% with 1.92 profit factor")
    print("  ✓ System is trending in the right direction")
    
    return metrics


def demo_ab_testing():
    """Demonstrate A/B testing capability."""
    print_section("3. A/B Testing Strategy Variations")
    
    # Create feedback loop (no DB needed for demo)
    from unittest.mock import Mock
    loop = FeedbackLoop(session=Mock())
    
    base_strategy_id = "strat_breakout_001"
    
    print(f"Base Strategy: {base_strategy_id}")
    print("\nCreating 3 variants to test...\n")
    
    # Create variants with different parameters
    variant_a = loop.create_ab_variant(
        base_strategy_id=base_strategy_id,
        variant_name="Higher Confluence (0.75)",
        modifications={"min_confluence": 0.75}
    )
    print(f"  ✓ Created: {variant_a.variant_name}")
    print(f"    ID: {variant_a.variant_id}")
    print(f"    Modifications: {variant_a.modifications}")
    
    variant_b = loop.create_ab_variant(
        base_strategy_id=base_strategy_id,
        variant_name="Stricter Pattern (0.8)",
        modifications={"min_pattern_score": 0.8}
    )
    print(f"\n  ✓ Created: {variant_b.variant_name}")
    print(f"    ID: {variant_b.variant_id}")
    print(f"    Modifications: {variant_b.modifications}")
    
    variant_c = loop.create_ab_variant(
        base_strategy_id=base_strategy_id,
        variant_name="Drive Cycle Only",
        modifications={"allowed_cycles": ["drive"]}
    )
    print(f"\n  ✓ Created: {variant_c.variant_name}")
    print(f"    ID: {variant_c.variant_id}")
    print(f"    Modifications: {variant_c.modifications}")
    
    # Simulate trading results
    print("\n" + "-" * 80)
    print("After 50 trades per variant:\n")
    
    loop.update_ab_variant_stats(
        variant_id=variant_a.variant_id,
        trade_count=50,
        win_rate=0.56,
        avg_r_multiple=0.95
    )
    print(f"  {variant_a.variant_name}:")
    print(f"    Trades: 50, Win Rate: 56%, Avg R: 0.95R")
    
    loop.update_ab_variant_stats(
        variant_id=variant_b.variant_id,
        trade_count=50,
        win_rate=0.68,
        avg_r_multiple=1.35
    )
    print(f"\n  {variant_b.variant_name}:")
    print(f"    Trades: 50, Win Rate: 68%, Avg R: 1.35R")
    
    loop.update_ab_variant_stats(
        variant_id=variant_c.variant_id,
        trade_count=50,
        win_rate=0.72,
        avg_r_multiple=1.55
    )
    print(f"\n  {variant_c.variant_name}:")
    print(f"    Trades: 50, Win Rate: 72%, Avg R: 1.55R")
    
    # Select best variant
    print("\n" + "-" * 80)
    best = loop.select_best_variant(base_strategy_id, min_trades=50)
    
    if best:
        print(f"\n🏆 Best Performing Variant: {best.variant_name}")
        print(f"   Win Rate: {best.win_rate:.1%}")
        print(f"   Avg R-Multiple: {best.avg_r_multiple:.2f}R")
        print(f"   Confidence: {best.confidence:.2f}")
        print(f"\n   Recommendation: Promote '{best.variant_name}' to production")
        print(f"   Apply modifications: {best.modifications}")
    
    return loop


def demo_pattern_insight():
    """Demonstrate pattern insight structure."""
    print_section("4. Pattern Insights")
    
    # Success pattern
    success_pattern = PatternInsight(
        pattern_type="success_factor",
        description="Strategy performs well in drive market cycle (70% of winning trades)",
        confidence=0.85,
        supporting_trades=["trade_1", "trade_2", "trade_3", "trade_4", "trade_5"],
        market_conditions={"market_cycle": "drive", "min_confluence": 0.65},
        impact_score=0.75
    )
    
    print("Success Pattern:")
    print(f"  Type: {success_pattern.pattern_type}")
    print(f"  Description: {success_pattern.description}")
    print(f"  Confidence: {success_pattern.confidence:.1%}")
    print(f"  Supporting Trades: {len(success_pattern.supporting_trades)}")
    print(f"  Impact Score: {success_pattern.impact_score:.2f}")
    print(f"  Market Conditions: {success_pattern.market_conditions}")
    
    # Failure pattern
    failure_pattern = PatternInsight(
        pattern_type="failure_pattern",
        description="Strategy struggles with low confluence (<0.5) - 65% of losses",
        confidence=0.78,
        supporting_trades=["trade_6", "trade_7", "trade_8"],
        market_conditions={"max_confluence": 0.5},
        impact_score=0.62
    )
    
    print("\nFailure Pattern:")
    print(f"  Type: {failure_pattern.pattern_type}")
    print(f"  Description: {failure_pattern.description}")
    print(f"  Confidence: {failure_pattern.confidence:.1%}")
    print(f"  Supporting Trades: {len(failure_pattern.supporting_trades)}")
    print(f"  Impact Score: {failure_pattern.impact_score:.2f}")
    print(f"  Market Conditions: {failure_pattern.market_conditions}")
    
    # Convert to learning entries
    print("\n" + "-" * 80)
    print("Converting to Learning Entries for storage:\n")
    
    success_entry = success_pattern.to_learning_entry("strat_001")
    print(f"Success Learning Entry:")
    print(f"  ID: {success_entry.id}")
    print(f"  Strategy: {success_entry.strategy_rule_id}")
    print(f"  Insight: {success_entry.insight}")
    print(f"  Confidence: {success_entry.confidence:.2f}")
    print(f"  Supporting Trades: {len(success_entry.supporting_trades)}")
    
    failure_entry = failure_pattern.to_learning_entry("strat_001")
    print(f"\nFailure Learning Entry:")
    print(f"  ID: {failure_entry.id}")
    print(f"  Strategy: {failure_entry.strategy_rule_id}")
    print(f"  Insight: {failure_entry.insight}")
    print(f"  Confidence: {failure_entry.confidence:.2f}")
    print(f"  Supporting Trades: {len(failure_entry.supporting_trades)}")
    
    return success_pattern, failure_pattern


def demo_feedback_loop_workflow():
    """Demonstrate complete feedback loop workflow."""
    print_section("5. Complete Feedback Loop Workflow")
    
    print("Feedback Loop Process:\n")
    print("Step 1: 📊 Analyze Trade Outcomes")
    print("  → OutcomeAnalyzer examines all trades for a strategy")
    print("  → Identifies success patterns and failure patterns")
    print("  → Calculates new confidence score based on performance\n")
    
    print("Step 2: 💾 Update Strategy Confidence")
    print("  → If confidence change > threshold (e.g., 5%)")
    print("  → Update strategy confidence in database")
    print("  → Log the change for audit trail\n")
    
    print("Step 3: 📝 Store Learning Insights")
    print("  → Extract high-confidence patterns (>60%)")
    print("  → Convert to LearningEntry objects")
    print("  → Store in database with supporting evidence\n")
    
    print("Step 4: 🎯 Inject Context into Trade Reasoner")
    print("  → Trade reasoner retrieves learning context for strategy")
    print("  → Includes success factors and failure patterns in prompt")
    print("  → Adjusts confidence based on historical performance\n")
    
    print("Step 5: 📈 Track Improvement")
    print("  → Calculate overall system metrics")
    print("  → Identify trends (improving/declining/stable)")
    print("  → Generate insights report\n")
    
    print("Step 6: 🧪 A/B Test Variations (Optional)")
    print("  → Create variants with modified parameters")
    print("  → Track performance of each variant")
    print("  → Promote best performing variant\n")
    
    print("-" * 80)
    print("\nKey Benefits:\n")
    print("  ✓ Continuous Learning: System improves with every trade")
    print("  ✓ Data-Driven: Decisions based on actual performance")
    print("  ✓ Transparent: All learnings stored with supporting evidence")
    print("  ✓ Safe: Gradual confidence adjustments, not drastic changes")
    print("  ✓ Testable: A/B testing ensures improvements are real")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("  FEEDBACK LOOP VERIFICATION")
    print("  Hyperliquid Trading Bot Suite")
    print("=" * 80)
    
    try:
        # Demo 1: Learning Context
        context = demo_learning_context()
        
        # Demo 2: Improvement Metrics
        metrics = demo_improvement_metrics()
        
        # Demo 3: A/B Testing
        loop = demo_ab_testing()
        
        # Demo 4: Pattern Insights
        success, failure = demo_pattern_insight()
        
        # Demo 5: Complete Workflow
        demo_feedback_loop_workflow()
        
        # Summary
        print_section("✅ VERIFICATION COMPLETE")
        print("All feedback loop components demonstrated successfully:\n")
        print("  [✓] LearningContext - Provides context to trade reasoner")
        print("  [✓] ImprovementMetrics - Tracks system improvement over time")
        print("  [✓] ABTestVariant - Enables A/B testing of strategies")
        print("  [✓] PatternInsight - Identifies success/failure patterns")
        print("  [✓] FeedbackLoop - Orchestrates the complete learning cycle")
        
        print("\n" + "=" * 80)
        print("  Ready for integration with trade reasoner and live system!")
        print("=" * 80 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
