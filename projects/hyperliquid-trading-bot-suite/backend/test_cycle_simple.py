"""
Simple test for Market Cycle Classifier
"""

from datetime import datetime, timedelta
import random

from src.types import CandleData, Timeframe, MarketCycle, OrderSide
from src.detection.cycle_classifier import MarketCycleClassifier


def create_candle(timestamp, open_price, high, low, close, volume=1000.0):
    """Helper to create candle data."""
    return CandleData(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timeframe=Timeframe.M15
    )


def generate_strong_bullish_drive(count=60):
    """Generate very strong bullish drive."""
    candles = []
    base_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=15 * count)
    
    for i in range(count):
        # Strong consistent upward movement
        open_price = base_price + i * 1.0  # Much stronger movement
        close = open_price + random.uniform(0.8, 1.2)  # Strong bullish bodies
        high = close + random.uniform(0.05, 0.1)  # Small upper wick
        low = open_price - random.uniform(0.01, 0.05)  # Tiny lower wick
        
        volume = random.uniform(1000, 2000)
        
        candles.append(create_candle(
            timestamp + timedelta(minutes=15 * i),
            open_price,
            high,
            low,
            close,
            volume
        ))
    
    return candles


def main():
    print("=" * 70)
    print("MARKET CYCLE CLASSIFIER - Simple Test")
    print("=" * 70)
    
    classifier = MarketCycleClassifier()
    
    # Test 1: Strong bullish drive
    print("\n📊 Test 1: Strong Bullish Drive")
    print("-" * 70)
    
    candles = generate_strong_bullish_drive(count=60)
    classification = classifier.classify(candles)
    
    print(f"\n🎯 Classification Result:")
    print(f"   Cycle: {classification.cycle.value}")
    print(f"   Confidence: {classification.confidence:.2%}")
    print(f"   Sub-phase: {classification.sub_phase}")
    print(f"   Dominant Bias: {classification.dominant_bias}")
    print(f"   Cycle Health: {classification.cycle_health:.2%}")
    print(f"   Transition Probability: {classification.transition_probability:.2%}")
    
    print(f"\n📈 Key Metrics:")
    m = classification.metrics
    print(f"   Momentum Score: {m.momentum_score:.3f}")
    print(f"   Momentum Acceleration: {m.momentum_acceleration:.3f}")
    print(f"   Directional Strength: {m.directional_strength:.3f}")
    print(f"   Normalized Volatility: {m.normalized_volatility:.3f}")
    print(f"   Structure Breaks: {m.structure_breaks}")
    print(f"   Higher Highs: {m.higher_highs_count}")
    print(f"   Lower Lows: {m.lower_lows_count}")
    print(f"   Wick Dominance: {m.wick_dominance:.3f}")
    print(f"   Sweep Count: {m.sweep_count}")
    print(f"   Price Oscillations: {m.price_oscillations}")
    print(f"   Mean Reversion Strength: {m.mean_reversion_strength:.3f}")
    
    # Get recommendations
    print(f"\n💡 Recommendations:")
    recommendations = classifier.get_cycle_recommendation(classification)
    print(f"   Preferred Patterns: {', '.join(recommendations['preferred_patterns'])}")
    print(f"   Avoid Patterns: {', '.join(recommendations['avoid_patterns'])}")
    print(f"   Confidence Adjustment: {recommendations['confidence_adjustment']:.2f}x")
    for note in recommendations['notes']:
        print(f"   ℹ️  {note}")
    
    # Verify price action
    print(f"\n📉 Price Action Verification:")
    print(f"   Start Price: {candles[0].close:.2f}")
    print(f"   End Price: {candles[-1].close:.2f}")
    print(f"   Total Move: +{candles[-1].close - candles[0].close:.2f} ({((candles[-1].close / candles[0].close - 1) * 100):.1f}%)")
    print(f"   Bullish Candles: {sum(1 for c in candles if c.is_bullish)}/{len(candles)}")
    
    print("\n" + "=" * 70)
    
    # Show scoring breakdown
    print("\n🔍 Detailed Scoring Breakdown:")
    print("-" * 70)
    
    # We'll manually call the scoring methods to see what's happening
    drive_score = classifier._score_drive_phase(m, candles)
    range_score = classifier._score_range_phase(m, candles)
    liquidity_score = classifier._score_liquidity_phase(m, candles)
    
    print(f"   DRIVE Score: {drive_score:.3f}")
    print(f"   RANGE Score: {range_score:.3f}")
    print(f"   LIQUIDITY Score: {liquidity_score:.3f}")
    print(f"   Winner: {max([('DRIVE', drive_score), ('RANGE', range_score), ('LIQUIDITY', liquidity_score)], key=lambda x: x[1])[0]}")
    
    print("\n" + "=" * 70)
    
    if classification.cycle == MarketCycle.DRIVE:
        print("✅ SUCCESS: Correctly identified DRIVE phase!")
    else:
        print(f"⚠️  UNEXPECTED: Detected {classification.cycle.value} instead of DRIVE")
        print(f"   This might be due to threshold tuning needed.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
