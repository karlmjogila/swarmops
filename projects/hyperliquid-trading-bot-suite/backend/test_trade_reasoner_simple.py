"""Simple test to verify trade reasoner implementation."""

import sys
import os
from datetime import datetime

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from trading.trade_reasoner import TradeReasoner, TradeReasoning
from types import OrderSide, EntryType, Timeframe, MarketCycle
from detection.confluence_scorer import ConfluenceScore, SignalGeneration

def test_basic_instantiation():
    """Test that we can create a TradeReasoner instance."""
    # Without API key (rule-based mode)
    reasoner = TradeReasoner(use_llm=False)
    assert reasoner is not None
    assert reasoner.use_llm == False
    print("✅ TradeReasoner instantiation successful (rule-based mode)")

def test_rule_based_reasoning():
    """Test rule-based reasoning generation."""
    reasoner = TradeReasoner(use_llm=False)
    
    # Create a mock signal
    confluence = ConfluenceScore(
        total_score=0.75,
        confidence=0.70,
        signal_strength=0.72,
        bias_direction=OrderSide.LONG,
        bias_confidence=0.75,
        timeframes_aligned=4,
        total_timeframes=5,
        alignment_percentage=0.80,
        pattern_score=0.70,
        structure_score=0.75,
        cycle_score=0.70,
        zone_score=0.80,
        higher_tf_bias=OrderSide.LONG,
        higher_tf_cycle=MarketCycle.DRIVE,
        higher_tf_strength=0.75,
        lower_tf_pattern=EntryType.LE,
        lower_tf_confidence=0.70,
        entry_quality=0.75,
        generates_signal=True,
        signal_type="long",
        entry_timeframe=Timeframe.M15,
        confluence_factors=[
            "4H shows bullish trend",
            "15M LE pattern detected",
            "Price at support zone"
        ],
        warning_factors=[]
    )
    
    signal = SignalGeneration(
        id="test_001",
        asset="BTC-USD",
        direction=OrderSide.LONG,
        entry_type=EntryType.LE,
        confluence_score=confluence,
        entry_price=50000.0,
        suggested_stop_loss=49500.0,
        suggested_take_profits=[50750.0, 51250.0],
        risk_reward_ratio=1.5,
        generated_at=datetime.utcnow(),
        priority=0.75
    )
    
    # Generate reasoning (sync call for testing)
    import asyncio
    reasoning = asyncio.run(reasoner.generate_reasoning(signal))
    
    assert reasoning is not None
    assert reasoning.should_enter == True
    assert reasoning.confidence == 0.70
    assert reasoning.entry_bias == OrderSide.LONG
    assert len(reasoning.explanation) > 0
    assert len(reasoning.confluence_factors) > 0
    
    print("✅ Rule-based reasoning generation successful")
    print(f"   Confidence: {reasoning.confidence:.0%}")
    print(f"   Should enter: {reasoning.should_enter}")
    print(f"   Summary: {reasoning.one_sentence_summary}")

def test_data_structures():
    """Test that data structures are properly defined."""
    reasoning = TradeReasoning()
    assert hasattr(reasoning, 'should_enter')
    assert hasattr(reasoning, 'confidence')
    assert hasattr(reasoning, 'explanation')
    assert hasattr(reasoning, 'confluence_factors')
    assert hasattr(reasoning, 'risks')
    
    print("✅ TradeReasoning data structure verified")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Testing Trade Reasoner Implementation")
    print("="*80 + "\n")
    
    try:
        test_basic_instantiation()
        test_data_structures()
        test_rule_based_reasoning()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
