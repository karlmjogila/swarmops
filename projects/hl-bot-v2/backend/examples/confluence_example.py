"""Example usage of multi-timeframe confluence scorer.

Demonstrates how to:
1. Load or create multi-timeframe candle data
2. Score confluence across timeframes
3. Interpret the results
4. Use for trade decision making
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import random

from app.core.market.data import Candle
from app.core.patterns.confluence import (
    MultiTimeframeConfluenceScorer,
    score_confluence,
    ConfluenceSignal,
)


def create_sample_candles(
    count: int,
    timeframe: str,
    start_time: datetime,
    base_price: float = 50000.0,
    volatility: float = 100.0,
    trend: str = "bullish",
) -> List[Candle]:
    """Create sample candle data for demonstration.
    
    Args:
        count: Number of candles to generate
        timeframe: Timeframe string (e.g., "5m", "1h")
        start_time: Starting timestamp
        base_price: Starting price level
        volatility: Price movement range
        trend: "bullish", "bearish", or "sideways"
    """
    candles = []
    current_price = base_price
    
    # Map timeframe to minutes
    tf_minutes = {
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
    }
    minutes = tf_minutes.get(timeframe, 5)
    
    for i in range(count):
        timestamp = start_time + timedelta(minutes=i * minutes)
        
        # Generate price movement based on trend
        if trend == "bullish":
            move = random.uniform(0, volatility * 1.5)
            close = current_price + move
        elif trend == "bearish":
            move = random.uniform(0, volatility * 1.5)
            close = current_price - move
        else:  # sideways
            move = random.uniform(-volatility, volatility)
            close = current_price + move
        
        # Generate OHLC around the close
        open_price = current_price
        high = max(open_price, close) + random.uniform(0, volatility * 0.3)
        low = min(open_price, close) - random.uniform(0, volatility * 0.3)
        
        candles.append(Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=random.uniform(1000, 5000),
            symbol="BTC-USD",
            timeframe=timeframe,
        ))
        
        current_price = close
    
    return candles


def example_basic_confluence_scoring():
    """Example 1: Basic confluence scoring."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Multi-Timeframe Confluence Scoring")
    print("=" * 80)
    
    # Create multi-timeframe data
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_sample_candles(50, "1h", start_time, trend="bullish"),
    }
    
    # Score confluence with 15m as analysis timeframe
    score = score_confluence(mtf_data, "15m")
    
    # Display results
    print(f"\nOverall Confluence Score: {score.overall_score:.1f}/100")
    print(f"Signal: {score.signal.value.upper()}")
    print(f"\nComponent Scores:")
    print(f"  Pattern Alignment:   {score.pattern_alignment_score:.2f}")
    print(f"  Structure Alignment: {score.structure_alignment_score:.2f}")
    print(f"  Zone Alignment:      {score.zone_alignment_score:.2f}")
    
    print(f"\nTimeframe Breakdown:")
    for tf in sorted(score.timeframe_scores.keys()):
        tf_score = score.timeframe_scores[tf]
        tf_signal = score.timeframe_signals[tf].value
        print(f"  {tf:>4}: Score={tf_score:.2f}, Signal={tf_signal}")
    
    print(f"\nDominant Timeframe: {score.dominant_timeframe}")
    print(f"Agreement: {score.agreement_percentage:.1f}%")
    
    if score.conflicting_timeframes:
        print(f"Conflicting TFs: {', '.join(score.conflicting_timeframes)}")
    else:
        print("No conflicting timeframes - strong alignment!")
    
    print()


def example_mixed_signals():
    """Example 2: Mixed signals across timeframes."""
    print("=" * 80)
    print("EXAMPLE 2: Mixed Signals - Lower vs Higher Timeframes")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Create conflicting trends
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish", volatility=50),
        "15m": create_sample_candles(100, "15m", start_time, trend="sideways", volatility=100),
        "1h": create_sample_candles(50, "1h", start_time, trend="bearish", volatility=150),
    }
    
    score = score_confluence(mtf_data, "15m")
    
    print(f"\nOverall Score: {score.overall_score:.1f}/100 - {score.signal.value.upper()}")
    print(f"\nTimeframe Signals:")
    for tf, signal in score.timeframe_signals.items():
        print(f"  {tf}: {signal.value}")
    
    print(f"\nConflicting Timeframes: {', '.join(score.conflicting_timeframes) or 'None'}")
    print(f"Agreement: {score.agreement_percentage:.1f}%")
    
    print("\n⚠️  Mixed signals suggest caution or waiting for alignment")
    print()


def example_trade_decision():
    """Example 3: Using confluence for trade decisions."""
    print("=" * 80)
    print("EXAMPLE 3: Trade Decision Making with Confluence")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Strong bullish setup
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish", volatility=30),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish", volatility=50),
        "1h": create_sample_candles(50, "1h", start_time, trend="bullish", volatility=80),
        "4h": create_sample_candles(25, "4h", start_time, trend="bullish", volatility=120),
    }
    
    scorer = MultiTimeframeConfluenceScorer()
    score = scorer.score_confluence(mtf_data, "15m")
    
    print(f"\nConfluence Score: {score.overall_score:.1f}/100")
    print(f"Signal: {score.signal.value.upper()}")
    print(f"Agreement: {score.agreement_percentage:.1f}%")
    
    # Trade decision logic
    print("\n" + "=" * 40)
    print("TRADE DECISION FRAMEWORK:")
    print("=" * 40)
    
    if score.overall_score >= 70 and score.agreement_percentage >= 75:
        risk = "1.5-2.0%"
        confidence = "High"
        action = "TAKE TRADE"
        color = "🟢"
    elif score.overall_score >= 50 and score.agreement_percentage >= 60:
        risk = "1.0%"
        confidence = "Medium"
        action = "Consider trade (reduced size)"
        color = "🟡"
    elif score.overall_score >= 30:
        risk = "0%"
        confidence = "Low"
        action = "WAIT for better setup"
        color = "🟠"
    else:
        risk = "0%"
        confidence = "Very Low"
        action = "NO TRADE - conflicting signals"
        color = "🔴"
    
    print(f"\n{color} Action: {action}")
    print(f"Confidence: {confidence}")
    print(f"Suggested Risk: {risk} of account")
    
    if score.conflicting_timeframes:
        print(f"\n⚠️  Warning: Conflicts on {', '.join(score.conflicting_timeframes)}")
    
    print()


def example_custom_weights():
    """Example 4: Custom timeframe weighting."""
    print("=" * 80)
    print("EXAMPLE 4: Custom Timeframe Weights")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_sample_candles(50, "1h", start_time, trend="sideways"),
    }
    
    scorer = MultiTimeframeConfluenceScorer()
    
    # Default weights (higher TF gets more weight)
    print("\nScenario A: Default Weights (Higher TF priority)")
    score_default = scorer.score_confluence(mtf_data, "15m")
    print(f"Score: {score_default.overall_score:.1f}/100")
    
    # Custom: Give more weight to lower timeframes (scalping style)
    print("\nScenario B: Lower TF Priority (Scalping)")
    custom_weights = {"5m": 2.5, "15m": 2.0, "1h": 1.0}
    score_scalp = scorer.score_confluence(mtf_data, "15m", custom_weights)
    print(f"Score: {score_scalp.overall_score:.1f}/100")
    
    # Custom: Higher TF priority (swing trading)
    print("\nScenario C: Higher TF Priority (Swing Trading)")
    custom_weights = {"5m": 1.0, "15m": 1.5, "1h": 3.0}
    score_swing = scorer.score_confluence(mtf_data, "15m", custom_weights)
    print(f"Score: {score_swing.overall_score:.1f}/100")
    
    print("\n💡 Adjust weights based on your trading style!")
    print()


def example_real_time_monitoring():
    """Example 5: Real-time confluence monitoring."""
    print("=" * 80)
    print("EXAMPLE 5: Real-Time Confluence Monitoring")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Simulate evolving market conditions
    print("\nMonitoring BTC-USD confluence over time...\n")
    
    for hour in range(3):
        # Simulate market evolution
        if hour == 0:
            trend = "sideways"
            print(f"Hour {hour}: Market ranging")
        elif hour == 1:
            trend = "bullish"
            print(f"Hour {hour}: Bullish breakout starting")
        else:
            trend = "bullish"
            print(f"Hour {hour}: Strong bullish trend")
        
        # Generate current data
        mtf_data = {
            "5m": create_sample_candles(200, "5m", start_time, trend=trend),
            "15m": create_sample_candles(100, "15m", start_time, trend=trend),
            "1h": create_sample_candles(50, "1h", start_time, trend=trend),
        }
        
        score = score_confluence(mtf_data, "15m")
        
        # Display key metrics
        signal_emoji = {
            ConfluenceSignal.STRONG_BULLISH: "🚀",
            ConfluenceSignal.BULLISH: "📈",
            ConfluenceSignal.NEUTRAL: "➡️",
            ConfluenceSignal.BEARISH: "📉",
            ConfluenceSignal.STRONG_BEARISH: "💥",
        }
        
        emoji = signal_emoji.get(score.signal, "❓")
        print(f"  {emoji} Score: {score.overall_score:>5.1f}/100 | "
              f"Signal: {score.signal.value:>15} | "
              f"Agreement: {score.agreement_percentage:>5.1f}%")
        
        start_time += timedelta(hours=1)
    
    print("\n💡 Monitor confluence changes to catch emerging setups!")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "MULTI-TIMEFRAME CONFLUENCE SCORER EXAMPLES" + " " * 21 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    examples = [
        example_basic_confluence_scoring,
        example_mixed_signals,
        example_trade_decision,
        example_custom_weights,
        example_real_time_monitoring,
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"❌ Error in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 80)
    print("Examples complete! Check the code to see how it works.")
    print("=" * 80)


if __name__ == "__main__":
    main()
