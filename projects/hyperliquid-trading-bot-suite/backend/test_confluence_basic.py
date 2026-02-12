#!/usr/bin/env python3
"""
Basic tests for Confluence Scorer - no external dependencies required
"""

from datetime import datetime, timedelta
from typing import List
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import from project's types module (not Python's built-in types)
from src.types import (
    CandleData, Timeframe, OrderSide
)
from src.detection.confluence_scorer import (
    ConfluenceScorer, TradeSignal, ConfluenceFactors
)


def create_sample_candles(count: int, timeframe: Timeframe, bullish: bool = True) -> List[CandleData]:
    """Create sample candle data for testing."""
    candles = []
    base_price = 100.0
    base_time = datetime.utcnow() - timedelta(hours=count)
    
    for i in range(count):
        if bullish:
            open_price = base_price + i * 0.5
            close_price = open_price + 0.3
            high_price = close_price + 0.2
            low_price = open_price - 0.1
        else:
            open_price = base_price - i * 0.5
            close_price = open_price - 0.3
            high_price = open_price + 0.1
            low_price = close_price - 0.2
        
        candle = CandleData(
            timestamp=base_time + timedelta(hours=i),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=1000.0 + i * 10,
            timeframe=timeframe
        )
        candles.append(candle)
    
    return candles


def main():
    print("=" * 60)
    print("Confluence Scorer - Basic Validation Tests")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test 1: Scorer Initialization
    print("\n[Test 1] Scorer Initialization")
    try:
        scorer = ConfluenceScorer()
        assert scorer.min_confluence_score == 0.65
        assert scorer.require_htf_bias == True
        assert scorer.min_signal_strength == 0.50
        print("✓ PASSED - Scorer initialized with correct defaults")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 2: Custom Parameters
    print("\n[Test 2] Custom Parameters")
    try:
        scorer = ConfluenceScorer(
            min_confluence_score=0.75,
            require_htf_bias=False,
            min_signal_strength=0.60
        )
        assert scorer.min_confluence_score == 0.75
        assert scorer.require_htf_bias == False
        print("✓ PASSED - Custom parameters set correctly")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 3: Confluence Factors
    print("\n[Test 3] Confluence Factors")
    try:
        factors = ConfluenceFactors(
            htf_ltf_direction_match=0.9,
            entry_pattern_quality=0.8,
            zone_interaction=0.7
        )
        score = factors.get_weighted_score()
        assert 0.0 <= score <= 1.0
        print(f"✓ PASSED - Confluence score: {score:.3f}")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 4: Sample Candle Generation
    print("\n[Test 4] Sample Candle Generation")
    try:
        candles = create_sample_candles(50, Timeframe.M15, bullish=True)
        assert len(candles) == 50
        assert all(isinstance(c, CandleData) for c in candles)
        assert candles[0].timeframe == Timeframe.M15
        print(f"✓ PASSED - Generated {len(candles)} sample candles")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 5: Trade Signal Creation
    print("\n[Test 5] Trade Signal Creation")
    try:
        signal = TradeSignal(
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_timeframe=Timeframe.M15,
            entry_price=50000.0,
            confluence_score=0.75
        )
        assert signal.asset == "BTC-USD"
        assert signal.direction == OrderSide.LONG
        assert signal.entry_price == 50000.0
        assert signal.confluence_score == 0.75
        print(f"✓ PASSED - Signal: {signal.direction.value} {signal.asset} @ {signal.entry_price}")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 6: Trade Signal Serialization
    print("\n[Test 6] Trade Signal Serialization")
    try:
        signal = TradeSignal(
            asset="ETH-USD",
            direction=OrderSide.SHORT,
            entry_timeframe=Timeframe.M5,
            entry_price=3000.0
        )
        signal_dict = signal.to_dict()
        assert isinstance(signal_dict, dict)
        assert signal_dict['asset'] == "ETH-USD"
        assert signal_dict['direction'] == "short"
        print("✓ PASSED - Signal serialization works")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 7: Confluence Analysis with Insufficient Data
    print("\n[Test 7] Confluence Analysis - Insufficient Data")
    try:
        scorer = ConfluenceScorer()
        h4_candles = create_sample_candles(5, Timeframe.H4, bullish=True)
        m15_candles = create_sample_candles(5, Timeframe.M15, bullish=True)
        
        multi_tf_data = {
            Timeframe.H4: h4_candles,
            Timeframe.M15: m15_candles,
        }
        
        signals = scorer.analyze_confluence(
            asset="BTC-USD",
            multi_timeframe_data=multi_tf_data,
            entry_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4
        )
        
        assert isinstance(signals, list)
        print(f"✓ PASSED - Handled insufficient data gracefully (returned {len(signals)} signals)")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 8: Confluence Analysis with Sufficient Data
    print("\n[Test 8] Confluence Analysis - Sufficient Data")
    try:
        scorer = ConfluenceScorer(
            min_confluence_score=0.50,
            require_htf_bias=False
        )
        
        h4_candles = create_sample_candles(100, Timeframe.H4, bullish=True)
        h1_candles = create_sample_candles(300, Timeframe.H1, bullish=True)
        m15_candles = create_sample_candles(500, Timeframe.M15, bullish=True)
        
        multi_tf_data = {
            Timeframe.H4: h4_candles,
            Timeframe.H1: h1_candles,
            Timeframe.M15: m15_candles,
        }
        
        signals = scorer.analyze_confluence(
            asset="ETH-USD",
            multi_timeframe_data=multi_tf_data,
            entry_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4
        )
        
        assert isinstance(signals, list)
        print(f"✓ PASSED - Analysis completed (generated {len(signals)} signals)")
        
        # Validate signal structure if any were generated
        for i, signal in enumerate(signals[:3]):  # Check first 3 signals
            assert signal.asset == "ETH-USD"
            assert 0.0 <= signal.confluence_score <= 1.0
            print(f"  Signal {i+1}: Score={signal.confluence_score:.2f}, Strength={signal.signal_strength:.2f}")
        
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 9: Missing Timeframe Handling
    print("\n[Test 9] Missing Timeframe Handling")
    try:
        scorer = ConfluenceScorer()
        m15_candles = create_sample_candles(100, Timeframe.M15, bullish=True)
        
        multi_tf_data = {
            Timeframe.M15: m15_candles,
        }
        
        signals = scorer.analyze_confluence(
            asset="BTC-USD",
            multi_timeframe_data=multi_tf_data,
            entry_timeframe=Timeframe.M15,
            higher_timeframe=Timeframe.H4  # Not in data
        )
        
        assert signals == []
        print("✓ PASSED - Correctly handled missing higher timeframe")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Test 10: Confluence Factors - Custom Weights
    print("\n[Test 10] Confluence Factors - Custom Weights")
    try:
        factors = ConfluenceFactors(
            htf_ltf_direction_match=1.0,
            entry_pattern_quality=0.5
        )
        
        custom_weights = {
            'htf_ltf_direction_match': 0.80,
            'entry_pattern_quality': 0.20,
        }
        
        score = factors.get_weighted_score(weights=custom_weights)
        assert 0.85 <= score <= 0.95
        print(f"✓ PASSED - Custom weights applied correctly (score={score:.3f})")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
