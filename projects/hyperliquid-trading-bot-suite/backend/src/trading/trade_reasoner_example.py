"""
Trade Reasoner Usage Example

Demonstrates how to use the TradeReasoner to analyze trading setups
and generate human-readable explanations for trade decisions.

Author: Hyperliquid Trading Bot Suite
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List

# Import components
from ..types import CandleData, Timeframe, OrderSide, EntryType, MarketCycle
from ..detection.confluence_scorer import (
    ConfluenceScorer, ConfluenceScore, TimeframeAnalysis
)
from ..knowledge.repository import StrategyRuleRepository
from .trade_reasoner import TradeReasoner, analyze_trade_setup


def create_sample_candle_data(
    timeframe: Timeframe,
    num_candles: int = 100,
    base_price: float = 50000.0,
    trend: str = "up"
) -> List[CandleData]:
    """Create sample candle data for testing."""
    candles = []
    current_price = base_price
    
    for i in range(num_candles):
        timestamp = datetime.utcnow() - timedelta(hours=(num_candles - i))
        
        # Simulate price movement
        if trend == "up":
            change = (i / num_candles) * 0.05  # 5% uptrend
            volatility = 0.01
        elif trend == "down":
            change = -(i / num_candles) * 0.05  # 5% downtrend
            volatility = 0.01
        else:
            change = 0
            volatility = 0.005  # Range-bound
        
        open_price = current_price * (1 + change)
        close_price = open_price * (1 + (0.002 if trend == "up" else -0.002))
        high_price = max(open_price, close_price) * (1 + volatility)
        low_price = min(open_price, close_price) * (1 - volatility)
        volume = 1000000.0 + (i * 10000)
        
        candle = CandleData(
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timeframe=timeframe
        )
        
        candles.append(candle)
        current_price = close_price
    
    return candles


def example_1_basic_usage():
    """Example 1: Basic trade reasoner usage."""
    print("=" * 80)
    print("Example 1: Basic Trade Reasoner Usage")
    print("=" * 80)
    print()
    
    # 1. Create sample multi-timeframe data
    print("Step 1: Creating sample candle data...")
    candle_data = {
        Timeframe.H4.value: create_sample_candle_data(Timeframe.H4, 200, trend="up"),
        Timeframe.H1.value: create_sample_candle_data(Timeframe.H1, 200, trend="up"),
        Timeframe.M15.value: create_sample_candle_data(Timeframe.M15, 200, trend="up"),
    }
    print(f"  ✓ Created {len(candle_data)} timeframes")
    print()
    
    # 2. Run confluence analysis
    print("Step 2: Running confluence analysis...")
    scorer = ConfluenceScorer()
    confluence_score = scorer.analyze_asset(
        asset="BTC",
        candle_data=candle_data
    )
    print(f"  ✓ Confluence Score: {confluence_score.total_score:.2%}")
    print(f"  ✓ Bias: {confluence_score.bias_direction.value if confluence_score.bias_direction else 'None'}")
    print(f"  ✓ Pattern: {confluence_score.lower_tf_pattern.value if confluence_score.lower_tf_pattern else 'None'}")
    print()
    
    # 3. Initialize trade reasoner (rule-based mode for demo)
    print("Step 3: Initializing trade reasoner...")
    reasoner = TradeReasoner(use_llm=False)  # Use rule-based for this example
    print(f"  ✓ Reasoner initialized (mode: rule-based)")
    print()
    
    # 4. Analyze the setup
    print("Step 4: Analyzing trade setup...")
    with StrategyRuleRepository() as repo:
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence_score,
            timeframe_analyses=confluence_score.timeframe_analyses,
            strategy_repository=repo,
            current_price=52000.0
        )
    print()
    
    # 5. Display results
    print("=" * 80)
    print("TRADE ANALYSIS RESULT")
    print("=" * 80)
    print()
    print(f"Asset: {reasoning.asset}")
    print(f"Setup Type: {reasoning.setup_type}")
    print(f"Recommendation: {'ENTER TRADE' if reasoning.should_enter else 'NO ENTRY'}")
    print(f"Confidence: {reasoning.confidence:.1%}")
    print()
    
    if reasoning.should_enter:
        print(f"Direction: {reasoning.entry_bias.value.upper() if reasoning.entry_bias else 'N/A'}")
        print(f"Strategy: {reasoning.matched_strategy_name}")
        print()
        
        if reasoning.suggested_stop_loss:
            print(f"Entry Price: $52,000")
            print(f"Stop Loss: ${reasoning.suggested_stop_loss:,.2f}")
            
            if reasoning.suggested_targets:
                print(f"Take Profits:")
                for i, target in enumerate(reasoning.suggested_targets, 1):
                    print(f"  TP{i}: ${target:,.2f}")
            
            if reasoning.risk_reward_ratio:
                print(f"Risk/Reward: 1:{reasoning.risk_reward_ratio:.2f}")
            print()
    
    print("Explanation:")
    print("-" * 80)
    print(reasoning.explanation)
    print("-" * 80)
    print()
    
    if reasoning.key_confluences:
        print("Key Confluences:")
        for confluence in reasoning.key_confluences:
            print(f"  ✓ {confluence}")
        print()
    
    if reasoning.risks:
        print("Risks:")
        for risk in reasoning.risks:
            print(f"  ⚠ {risk}")
        print()


def example_2_with_llm():
    """Example 2: Using LLM reasoning (requires API key)."""
    print("=" * 80)
    print("Example 2: LLM-Powered Reasoning")
    print("=" * 80)
    print()
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠ ANTHROPIC_API_KEY not set. Skipping LLM example.")
        print("  Set API key to run this example:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        print()
        return
    
    # Create sample data
    print("Creating sample data for analysis...")
    candle_data = {
        Timeframe.H4.value: create_sample_candle_data(Timeframe.H4, 200, trend="up"),
        Timeframe.H1.value: create_sample_candle_data(Timeframe.H1, 200, trend="up"),
        Timeframe.M30.value: create_sample_candle_data(Timeframe.M30, 200, trend="up"),
        Timeframe.M15.value: create_sample_candle_data(Timeframe.M15, 200, trend="up"),
    }
    
    # Run confluence analysis
    scorer = ConfluenceScorer()
    confluence_score = scorer.analyze_asset(
        asset="ETH",
        candle_data=candle_data
    )
    
    # Initialize LLM-powered reasoner
    print("Initializing LLM reasoner (Claude Sonnet)...")
    reasoner = TradeReasoner(
        anthropic_api_key=api_key,
        model="claude-sonnet-4-20250514",
        use_llm=True
    )
    print()
    
    # Analyze with LLM
    print("Analyzing with LLM (this may take a few seconds)...")
    with StrategyRuleRepository() as repo:
        reasoning = reasoner.analyze_setup(
            asset="ETH",
            confluence_score=confluence_score,
            timeframe_analyses=confluence_score.timeframe_analyses,
            strategy_repository=repo,
            current_price=3200.0
        )
    print()
    
    # Display LLM results
    print("=" * 80)
    print("LLM ANALYSIS RESULT")
    print("=" * 80)
    print()
    print(f"Mode: {reasoning.reasoning_mode}")
    print(f"Recommendation: {'ENTER' if reasoning.should_enter else 'NO ENTRY'}")
    print(f"Confidence: {reasoning.confidence:.1%}")
    print()
    
    print("LLM Explanation:")
    print("-" * 80)
    print(reasoning.explanation)
    print("-" * 80)
    print()
    
    if reasoning.higher_tf_context:
        print("Higher TF Context:")
        print(f"  {reasoning.higher_tf_context}")
        print()
    
    if reasoning.entry_tf_context:
        print("Entry TF Context:")
        print(f"  {reasoning.entry_tf_context}")
        print()
    
    if reasoning.expected_behavior:
        print("Expected Behavior:")
        print(f"  {reasoning.expected_behavior}")
        print()


def example_3_create_trade_record():
    """Example 3: Creating a trade record from reasoning."""
    print("=" * 80)
    print("Example 3: Creating Trade Record")
    print("=" * 80)
    print()
    
    # Setup (similar to example 1)
    candle_data = {
        Timeframe.H4.value: create_sample_candle_data(Timeframe.H4, 200, trend="up"),
        Timeframe.H1.value: create_sample_candle_data(Timeframe.H1, 200, trend="up"),
        Timeframe.M15.value: create_sample_candle_data(Timeframe.M15, 200, trend="up"),
    }
    
    scorer = ConfluenceScorer()
    confluence_score = scorer.analyze_asset(asset="BTC", candle_data=candle_data)
    
    reasoner = TradeReasoner(use_llm=False)
    
    with StrategyRuleRepository() as repo:
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence_score,
            timeframe_analyses=confluence_score.timeframe_analyses,
            strategy_repository=repo,
            current_price=52000.0
        )
        
        # Create trade record if entry approved
        if reasoning.should_enter:
            print("Trade approved! Creating trade record...")
            
            trade_record = reasoner.create_trade_record(
                reasoning=reasoning,
                confluence_score=confluence_score,
                timeframe_analyses=confluence_score.timeframe_analyses,
                entry_price=52000.0,
                position_size=0.1,
                is_backtest=False
            )
            
            print()
            print("Trade Record Created:")
            print(f"  ID: {trade_record.id}")
            print(f"  Asset: {trade_record.asset}")
            print(f"  Direction: {trade_record.direction.value}")
            print(f"  Entry Price: ${trade_record.entry_price:,.2f}")
            print(f"  Position Size: {trade_record.position_size}")
            print(f"  Stop Loss: ${trade_record.stop_loss:,.2f}" if trade_record.stop_loss else "  Stop Loss: Not set")
            print(f"  Confidence: {trade_record.confidence:.1%}")
            print()
            
            # In real usage, you would save this to the database:
            # from ..knowledge.repository import TradeRecordRepository
            # with TradeRecordRepository() as trade_repo:
            #     trade_id = trade_repo.create(trade_record)
            #     print(f"Trade saved to database: {trade_id}")
        else:
            print("Trade not approved - no record created")
            print(f"Reason: {reasoning.explanation}")
    
    print()


def example_4_convenience_function():
    """Example 4: Using the convenience function."""
    print("=" * 80)
    print("Example 4: Convenience Function")
    print("=" * 80)
    print()
    
    # Create sample data
    candle_data = {
        Timeframe.H4.value: create_sample_candle_data(Timeframe.H4, 200, trend="up"),
        Timeframe.M15.value: create_sample_candle_data(Timeframe.M15, 200, trend="up"),
    }
    
    # Run confluence analysis
    scorer = ConfluenceScorer()
    confluence_score = scorer.analyze_asset(asset="SOL", candle_data=candle_data)
    
    # Use convenience function
    print("Using analyze_trade_setup convenience function...")
    with StrategyRuleRepository() as repo:
        reasoning = analyze_trade_setup(
            asset="SOL",
            confluence_score=confluence_score,
            timeframe_analyses=confluence_score.timeframe_analyses,
            strategy_repository=repo,
            current_price=100.0,
            use_llm=False
        )
    
    print()
    print(f"Result: {'ENTER' if reasoning.should_enter else 'NO ENTRY'}")
    print(f"Confidence: {reasoning.confidence:.1%}")
    print(f"Explanation: {reasoning.explanation}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("█" * 80)
    print("  TRADE REASONER EXAMPLES")
    print("█" * 80)
    print("\n")
    
    # Run examples
    try:
        example_1_basic_usage()
        input("Press Enter to continue to next example...")
        print("\n")
        
        example_2_with_llm()
        input("Press Enter to continue to next example...")
        print("\n")
        
        example_3_create_trade_record()
        input("Press Enter to continue to next example...")
        print("\n")
        
        example_4_convenience_function()
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\n\n⚠ Error running examples: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")
    print("=" * 80)
    print("Examples complete!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
