"""
Verification script for the Outcome Analyzer module.

Demonstrates the complete workflow:
1. Create sample strategy and trades
2. Analyze outcomes
3. Generate insights
4. Update confidence scores
"""

from datetime import datetime, timedelta
from src.types import (
    StrategyRule, TradeRecord, TradeOutcome, MarketCycle,
    OrderSide, ExitReason, EntryType, SourceType,
    PriceActionSnapshot, RiskParameters
)
from src.learning.outcome_analyzer import OutcomeAnalyzer


def create_sample_strategy() -> StrategyRule:
    """Create a sample strategy for testing."""
    return StrategyRule(
        id="test-strategy-001",
        name="LE Candle Drive Phase Strategy",
        entry_type=EntryType.LE,
        source_type=SourceType.MANUAL,
        source_ref="test_verification",
        conditions=[],
        risk_params=RiskParameters(
            risk_percent=2.0,
            tp_levels=[1.0, 2.0],
            sl_distance="below_low"
        ),
        confidence=0.5,
        win_rate=0.0,
        avg_r_multiple=0.0
    )


def create_sample_trades() -> list[TradeRecord]:
    """Create sample trades with realistic patterns."""
    trades = []
    base_time = datetime.utcnow() - timedelta(days=30)
    
    # Winning trades - mostly in DRIVE phase with high confluence
    for i in range(15):
        trade = TradeRecord(
            id=f"win-{i}",
            strategy_rule_id="test-strategy-001",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2000.0 + (i * 5),
            entry_time=base_time + timedelta(days=i, hours=14),  # US session
            quantity=1.0,
            exit_price=2040.0 + (i * 5) if i % 3 == 0 else 2020.0 + (i * 5),
            exit_time=base_time + timedelta(days=i, hours=18),
            exit_reason=ExitReason.TP2 if i % 3 == 0 else ExitReason.TP1,
            outcome=TradeOutcome.WIN,
            pnl_absolute=40.0 if i % 3 == 0 else 20.0,
            pnl_r_multiple=2.0 if i % 3 == 0 else 1.0,
            reasoning="Strong LE candle in drive phase with high confluence",
            price_action_context=PriceActionSnapshot(
                timestamp=base_time + timedelta(days=i),
                timeframes={},
                market_cycle=MarketCycle.DRIVE if i % 4 != 0 else MarketCycle.LIQUIDITY,
                confluence_score=0.85 if i % 4 != 0 else 0.7,
                structure_notes=[
                    "Strong bullish structure",
                    "Higher highs and higher lows",
                    "BOS confirmed on 4H"
                ],
                zone_interactions=["Bounce from demand zone"]
            )
        )
        trades.append(trade)
    
    # Losing trades - in RANGE phase with low confluence
    for i in range(5):
        trade = TradeRecord(
            id=f"loss-{i}",
            strategy_rule_id="test-strategy-001",
            asset="ETH-USD",
            direction=OrderSide.LONG,
            entry_price=2100.0 + (i * 5),
            entry_time=base_time + timedelta(days=15 + i, hours=8),  # Asian session
            quantity=1.0,
            exit_price=2080.0 + (i * 5),
            exit_time=base_time + timedelta(days=15 + i, hours=10),
            exit_reason=ExitReason.STOP_LOSS,
            outcome=TradeOutcome.LOSS,
            pnl_absolute=-20.0,
            pnl_r_multiple=-1.0,
            reasoning="Setup failed in range-bound market",
            price_action_context=PriceActionSnapshot(
                timestamp=base_time + timedelta(days=15 + i),
                timeframes={},
                market_cycle=MarketCycle.RANGE,
                confluence_score=0.45,
                structure_notes=[
                    "Weak structure",
                    "Failed to hold support",
                    "Choppy price action"
                ],
                zone_interactions=["Failed to hold demand zone"]
            )
        )
        trades.append(trade)
    
    return trades


def main():
    """Run the verification."""
    print("=" * 80)
    print("Outcome Analyzer Verification")
    print("=" * 80)
    
    # Initialize analyzer
    analyzer = OutcomeAnalyzer(
        min_trades_for_analysis=10,
        min_pattern_trades=3,
        confidence_adjustment_rate=0.15,
        pattern_confidence_threshold=0.6
    )
    
    print(f"\n✓ Analyzer initialized")
    print(f"  - Min trades for analysis: {analyzer.min_trades_for_analysis}")
    print(f"  - Min pattern trades: {analyzer.min_pattern_trades}")
    print(f"  - Confidence adjustment rate: {analyzer.confidence_adjustment_rate}")
    
    # Create test data
    strategy = create_sample_strategy()
    trades = create_sample_trades()
    
    print(f"\n✓ Test data created")
    print(f"  - Strategy: {strategy.name}")
    print(f"  - Initial confidence: {strategy.confidence:.2f}")
    print(f"  - Total trades: {len(trades)}")
    print(f"  - Winning trades: {len([t for t in trades if t.outcome == TradeOutcome.WIN])}")
    print(f"  - Losing trades: {len([t for t in trades if t.outcome == TradeOutcome.LOSS])}")
    
    # Analyze strategy
    print(f"\n{'='*80}")
    print("Running Analysis...")
    print(f"{'='*80}\n")
    
    analysis = analyzer.analyze_strategy(strategy, trades)
    
    # Display results
    print(f"\n{'='*80}")
    print("Analysis Results")
    print(f"{'='*80}\n")
    
    print(f"Strategy: {analysis.strategy_name}")
    print(f"  Total Trades: {analysis.total_trades}")
    print(f"  Win Rate: {analysis.win_rate:.1f}%")
    print(f"  Average R-Multiple: {analysis.avg_r_multiple:.2f}R")
    print(f"  Profit Factor: {analysis.profit_factor:.2f}")
    
    print(f"\n  Confidence Score:")
    print(f"    Old: {analysis.old_confidence:.3f}")
    print(f"    New: {analysis.new_confidence:.3f}")
    print(f"    Change: {analysis.confidence_change:+.3f} ({(analysis.confidence_change/analysis.old_confidence*100):+.1f}%)")
    
    # Success patterns
    if analysis.success_patterns:
        print(f"\n  Success Patterns Identified: {len(analysis.success_patterns)}")
        for i, pattern in enumerate(analysis.success_patterns, 1):
            print(f"    {i}. {pattern.description}")
            print(f"       Confidence: {pattern.confidence:.2f} | Impact: {pattern.impact_score:.2f}")
            print(f"       Supporting trades: {len(pattern.supporting_trades)}")
    
    # Failure patterns
    if analysis.failure_patterns:
        print(f"\n  Failure Patterns Identified: {len(analysis.failure_patterns)}")
        for i, pattern in enumerate(analysis.failure_patterns, 1):
            print(f"    {i}. {pattern.description}")
            print(f"       Confidence: {pattern.confidence:.2f} | Impact: {pattern.impact_score:.2f}")
            print(f"       Supporting trades: {len(pattern.supporting_trades)}")
    
    # Market cycle performance
    if analysis.best_market_cycles:
        print(f"\n  Best Market Cycles:")
        for cycle, win_rate in analysis.best_market_cycles:
            cycle_name = cycle.value if hasattr(cycle, 'value') else str(cycle)
            print(f"    - {cycle_name}: {win_rate:.1f}% win rate")
    
    if analysis.worst_market_cycles:
        print(f"\n  Worst Market Cycles:")
        for cycle, win_rate in analysis.worst_market_cycles:
            cycle_name = cycle.value if hasattr(cycle, 'value') else str(cycle)
            print(f"    - {cycle_name}: {win_rate:.1f}% win rate")
    
    # Best assets
    if analysis.best_assets:
        print(f"\n  Best Performing Assets:")
        for asset, win_rate in analysis.best_assets:
            print(f"    - {asset}: {win_rate:.1f}% win rate")
    
    # Recommendations
    if analysis.recommendations:
        print(f"\n  Recommendations ({len(analysis.recommendations)}):")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"    {i}. {rec}")
    
    # Generate learning entries
    print(f"\n{'='*80}")
    print("Learning Entries")
    print(f"{'='*80}\n")
    
    learning_entries = analyzer.generate_learning_entries(analysis)
    
    print(f"Generated {len(learning_entries)} learning entries:\n")
    
    for i, entry in enumerate(learning_entries, 1):
        print(f"{i}. {entry.insight}")
        print(f"   Pattern: {entry.pattern_identified}")
        print(f"   Confidence: {entry.confidence:.2f}")
        print(f"   Supporting trades: {len(entry.supporting_trades)}")
        if entry.market_conditions:
            print(f"   Market conditions: {entry.market_conditions}")
        print()
    
    # Summary
    print(f"{'='*80}")
    print("Summary")
    print(f"{'='*80}\n")
    
    print(f"✓ Strategy '{strategy.name}' analyzed successfully")
    print(f"✓ Confidence updated: {analysis.old_confidence:.3f} → {analysis.new_confidence:.3f}")
    print(f"✓ {len(analysis.success_patterns)} success patterns identified")
    print(f"✓ {len(analysis.failure_patterns)} failure patterns identified")
    print(f"✓ {len(learning_entries)} learning entries generated")
    print(f"✓ {len(analysis.recommendations)} recommendations produced")
    
    print(f"\n{'='*80}")
    print("Verification Complete!")
    print(f"{'='*80}\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
