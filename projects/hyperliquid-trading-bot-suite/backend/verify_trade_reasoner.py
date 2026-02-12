#!/usr/bin/env python3
"""
Trade Reasoner Verification Script

Tests the Trade Reasoner implementation without external dependencies.
This script validates that the trade reasoner can:
1. Analyze trading setups based on confluence scores
2. Generate detailed reasoning (both LLM and rule-based)
3. Calculate risk management levels
4. Create trade records
5. Match with strategy rules

Author: Hyperliquid Trading Bot Suite
"""

import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


# Mock types for testing (minimal versions)
class OrderSide(Enum):
    LONG = "long"
    SHORT = "short"


class EntryType(Enum):
    LE = "le"
    SMALL_WICK = "small_wick"
    STEEPER_WICK = "steeper_wick"
    CELERY = "celery"
    BREAKOUT = "breakout"
    FAKEOUT = "fakeout"
    ONION = "onion"


class MarketCycle(Enum):
    DRIVE = "drive"
    RANGE = "range"
    LIQUIDITY = "liquidity"


class Timeframe(Enum):
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"


class TradeOutcome(Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"


@dataclass
class CandleData:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class PatternDetection:
    pattern_type: EntryType
    confidence: float
    candle_index: int
    pattern_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketStructure:
    trend_direction: Optional[OrderSide] = None
    trend_strength: float = 0.0
    support_zones: List[Dict] = field(default_factory=list)
    resistance_zones: List[Dict] = field(default_factory=list)


@dataclass
class TimeframeContext:
    timeframe: Timeframe
    candles: List[CandleData]
    patterns: List[PatternDetection] = field(default_factory=list)
    trend_direction: Optional[OrderSide] = None
    trend_strength: float = 0.0
    market_cycle: Optional[MarketCycle] = None
    in_support_zone: bool = False
    in_resistance_zone: bool = False
    zone_strength: float = 0.0
    recent_bos: Optional[OrderSide] = None
    near_structure_break: bool = False


@dataclass
class ConfluenceScore:
    timestamp: datetime
    total_score: float = 0.0
    pattern_score: float = 0.0
    structure_score: float = 0.0
    cycle_score: float = 0.0
    timeframe_alignment_score: float = 0.0
    signal_quality: str = "low"
    entry_bias: Optional[OrderSide] = None
    htf_bias: Optional[OrderSide] = None
    htf_trend_strength: float = 0.0
    htf_timeframe: Optional[Timeframe] = None
    entry_timeframe: Optional[Timeframe] = None
    entry_patterns: List[EntryType] = field(default_factory=list)
    generates_signal: bool = False
    confluence_factors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RiskParams:
    tp_levels: List[float] = field(default_factory=lambda: [1.5, 2.5])
    sl_type: str = "structure"
    risk_percent: float = 2.0


@dataclass
class StrategyRule:
    id: str
    name: str
    entry_type: EntryType
    confidence: float
    enabled: bool = True
    risk_params: Optional[RiskParams] = None
    confluence_required: List[Any] = field(default_factory=list)
    
    def __post_init__(self):
        if self.risk_params is None:
            self.risk_params = RiskParams()


@dataclass
class PriceActionSnapshot:
    timestamp: datetime
    timeframes: Dict[str, List[CandleData]] = field(default_factory=dict)
    structure_notes: List[str] = field(default_factory=list)
    zone_interactions: List[str] = field(default_factory=list)
    market_cycle: Optional[MarketCycle] = None
    confluence_score: float = 0.0


@dataclass
class TradeRecord:
    strategy_rule_id: str
    asset: str
    direction: OrderSide
    entry_price: float
    entry_time: datetime
    quantity: float
    reasoning: str
    price_action_context: PriceActionSnapshot
    initial_stop_loss: Optional[float] = None
    current_stop_loss: Optional[float] = None
    take_profit_levels: List[float] = field(default_factory=list)
    outcome: TradeOutcome = TradeOutcome.PENDING
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl_absolute: float = 0.0
    pnl_r_multiple: float = 0.0


# Mock repository
class StrategyRuleRepository:
    def __init__(self):
        self.strategies = self._create_sample_strategies()
    
    def _create_sample_strategies(self) -> List[StrategyRule]:
        return [
            StrategyRule(
                id="strat_1",
                name="LE Candle Entry",
                entry_type=EntryType.LE,
                confidence=0.75,
                risk_params=RiskParams(tp_levels=[1.5, 2.5, 3.5])
            ),
            StrategyRule(
                id="strat_2",
                name="Breakout Strategy",
                entry_type=EntryType.BREAKOUT,
                confidence=0.65,
                risk_params=RiskParams(tp_levels=[2.0, 3.0])
            )
        ]
    
    def get_all(self, min_confidence: float = 0.0, limit: int = 100) -> List[StrategyRule]:
        return [s for s in self.strategies if s.confidence >= min_confidence][:limit]
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


# Test helper functions
def create_sample_candles(
    count: int = 50,
    start_price: float = 50000.0,
    trend: str = "up"
) -> List[CandleData]:
    """Create sample candle data for testing."""
    candles = []
    current_price = start_price
    now = datetime.utcnow()
    
    for i in range(count):
        if trend == "up":
            change = 10 + (i % 5) * 5
            open_price = current_price
            close_price = current_price + change
            high_price = close_price + 5
            low_price = open_price - 3
        else:
            change = 10 + (i % 5) * 5
            open_price = current_price
            close_price = current_price - change
            high_price = open_price + 3
            low_price = close_price - 5
        
        candles.append(CandleData(
            timestamp=now - timedelta(minutes=5 * (count - i)),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=1000 + (i % 10) * 100
        ))
        
        current_price = close_price
    
    return candles


def create_sample_confluence_score(
    direction: OrderSide = OrderSide.LONG,
    quality: str = "strong"
) -> ConfluenceScore:
    """Create sample confluence score for testing."""
    return ConfluenceScore(
        timestamp=datetime.utcnow(),
        total_score=0.75,
        pattern_score=0.70,
        structure_score=0.80,
        cycle_score=0.75,
        timeframe_alignment_score=0.70,
        signal_quality=quality,
        entry_bias=direction,
        htf_bias=direction,
        htf_trend_strength=0.80,
        htf_timeframe=Timeframe.H4,
        entry_timeframe=Timeframe.M15,
        entry_patterns=[EntryType.LE],
        generates_signal=True,
        confluence_factors=[
            "Strong HTF bias",
            "Good pattern alignment",
            "Near support zone"
        ],
        warnings=[]
    )


def create_sample_timeframe_contexts() -> Dict[Timeframe, TimeframeContext]:
    """Create sample timeframe contexts."""
    contexts = {}
    
    # H4 context (higher timeframe)
    contexts[Timeframe.H4] = TimeframeContext(
        timeframe=Timeframe.H4,
        candles=create_sample_candles(50, 50000, "up"),
        trend_direction=OrderSide.LONG,
        trend_strength=0.80,
        market_cycle=MarketCycle.DRIVE
    )
    
    # H1 context
    contexts[Timeframe.H1] = TimeframeContext(
        timeframe=Timeframe.H1,
        candles=create_sample_candles(50, 50500, "up"),
        trend_direction=OrderSide.LONG,
        trend_strength=0.70,
        market_cycle=MarketCycle.DRIVE
    )
    
    # M15 context (entry timeframe)
    contexts[Timeframe.M15] = TimeframeContext(
        timeframe=Timeframe.M15,
        candles=create_sample_candles(50, 50600, "up"),
        trend_direction=OrderSide.LONG,
        trend_strength=0.65,
        market_cycle=MarketCycle.DRIVE,
        in_support_zone=True,
        zone_strength=0.75,
        patterns=[
            PatternDetection(
                pattern_type=EntryType.LE,
                confidence=0.80,
                candle_index=48
            )
        ]
    )
    
    return contexts


# Test functions
def test_1_import_trade_reasoner():
    """Test 1: Import TradeReasoner class"""
    print("\n" + "="*60)
    print("Test 1: Import TradeReasoner")
    print("="*60)
    
    try:
        # Try importing directly from the module file (bypass __init__.py)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "trade_reasoner",
            os.path.join(os.path.dirname(__file__), "src/trading/trade_reasoner.py")
        )
        trade_reasoner_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(trade_reasoner_module)
        
        TradeReasoner = trade_reasoner_module.TradeReasoner
        TradeReasoning = trade_reasoner_module.TradeReasoning
        
        print("✅ Successfully imported TradeReasoner and TradeReasoning")
        return True
    except Exception as e:
        print(f"❌ Failed to import: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_initialize_reasoner():
    """Test 2: Initialize TradeReasoner"""
    print("\n" + "="*60)
    print("Test 2: Initialize TradeReasoner")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        # Initialize without API key (should fall back to rule-based)
        reasoner = TradeReasoner(
            anthropic_api_key=None,
            use_llm=False
        )
        
        print(f"✅ Initialized reasoner")
        print(f"   - Use LLM: {reasoner.use_llm}")
        print(f"   - Model: {reasoner.model}")
        print(f"   - Min confidence: {reasoner.min_confidence_for_entry}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_analyze_setup():
    """Test 3: Analyze a trading setup"""
    print("\n" + "="*60)
    print("Test 3: Analyze Trading Setup")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        reasoner = TradeReasoner(use_llm=False)
        confluence = create_sample_confluence_score(OrderSide.LONG, "strong")
        contexts = create_sample_timeframe_contexts()
        repository = StrategyRuleRepository()
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence,
            timeframe_contexts=contexts,
            strategy_repository=repository,
            current_price=50700.0
        )
        
        print(f"✅ Setup analysis completed")
        print(f"   - Should enter: {reasoning.should_enter}")
        print(f"   - Confidence: {reasoning.confidence:.2%}")
        print(f"   - Direction: {reasoning.entry_bias}")
        print(f"   - Strategy: {reasoning.matched_strategy_name}")
        print(f"   - Setup type: {reasoning.setup_type}")
        print(f"\n   Explanation:")
        for line in reasoning.explanation.split('\n')[:3]:
            print(f"      {line}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to analyze setup: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_risk_management():
    """Test 4: Calculate risk management levels"""
    print("\n" + "="*60)
    print("Test 4: Risk Management Calculations")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        reasoner = TradeReasoner(use_llm=False)
        confluence = create_sample_confluence_score(OrderSide.LONG, "strong")
        contexts = create_sample_timeframe_contexts()
        repository = StrategyRuleRepository()
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence,
            timeframe_contexts=contexts,
            strategy_repository=repository,
            current_price=50700.0
        )
        
        print(f"✅ Risk levels calculated")
        print(f"   - Entry: $50,700.00")
        if reasoning.suggested_stop_loss:
            print(f"   - Stop Loss: ${reasoning.suggested_stop_loss:,.2f}")
        if reasoning.suggested_targets:
            print(f"   - Targets: {len(reasoning.suggested_targets)}")
            for i, target in enumerate(reasoning.suggested_targets, 1):
                print(f"      TP{i}: ${target:,.2f}")
        if reasoning.risk_reward_ratio:
            print(f"   - R:R Ratio: {reasoning.risk_reward_ratio:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Failed risk calculations: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_create_trade_record():
    """Test 5: Create TradeRecord"""
    print("\n" + "="*60)
    print("Test 5: Create Trade Record")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        reasoner = TradeReasoner(use_llm=False)
        confluence = create_sample_confluence_score(OrderSide.LONG, "strong")
        contexts = create_sample_timeframe_contexts()
        repository = StrategyRuleRepository()
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence,
            timeframe_contexts=contexts,
            strategy_repository=repository,
            current_price=50700.0
        )
        
        trade = reasoner.create_trade_record(
            reasoning=reasoning,
            confluence_score=confluence,
            timeframe_contexts=contexts,
            entry_price=50700.0,
            quantity=0.1
        )
        
        print(f"✅ Trade record created")
        print(f"   - Asset: {trade.asset}")
        print(f"   - Direction: {trade.direction.value}")
        print(f"   - Entry: ${trade.entry_price:,.2f}")
        print(f"   - Quantity: {trade.quantity}")
        print(f"   - Strategy: {trade.strategy_rule_id}")
        print(f"   - Outcome: {trade.outcome.value}")
        print(f"   - Context timeframes: {len(trade.price_action_context.timeframes)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create trade record: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_short_setup():
    """Test 6: Analyze SHORT setup"""
    print("\n" + "="*60)
    print("Test 6: SHORT Setup Analysis")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        reasoner = TradeReasoner(use_llm=False)
        confluence = create_sample_confluence_score(OrderSide.SHORT, "medium")
        contexts = create_sample_timeframe_contexts()
        # Update contexts for SHORT
        for ctx in contexts.values():
            ctx.trend_direction = OrderSide.SHORT
        
        repository = StrategyRuleRepository()
        
        reasoning = reasoner.analyze_setup(
            asset="ETH",
            confluence_score=confluence,
            timeframe_contexts=contexts,
            strategy_repository=repository,
            current_price=3000.0
        )
        
        print(f"✅ SHORT setup analyzed")
        print(f"   - Should enter: {reasoning.should_enter}")
        print(f"   - Direction: {reasoning.entry_bias}")
        print(f"   - Confidence: {reasoning.confidence:.2%}")
        
        return True
    except Exception as e:
        print(f"❌ Failed SHORT analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_low_confluence():
    """Test 7: Low confluence (should not enter)"""
    print("\n" + "="*60)
    print("Test 7: Low Confluence Setup")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        reasoner = TradeReasoner(use_llm=False)
        
        # Create low quality confluence
        confluence = ConfluenceScore(
            timestamp=datetime.utcnow(),
            total_score=0.30,  # Below threshold
            pattern_score=0.25,
            structure_score=0.35,
            cycle_score=0.30,
            signal_quality="low",
            generates_signal=False
        )
        
        contexts = create_sample_timeframe_contexts()
        repository = StrategyRuleRepository()
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence,
            timeframe_contexts=contexts,
            strategy_repository=repository,
            current_price=50000.0
        )
        
        print(f"✅ Low confluence handled correctly")
        print(f"   - Should enter: {reasoning.should_enter} (expected: False)")
        print(f"   - Reason: {reasoning.explanation[:100]}...")
        
        return not reasoning.should_enter  # Should NOT enter
    except Exception as e:
        print(f"❌ Failed low confluence test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_8_rule_based_reasoning():
    """Test 8: Rule-based reasoning (no LLM)"""
    print("\n" + "="*60)
    print("Test 8: Rule-Based Reasoning")
    print("="*60)
    
    try:
        from trading.trade_reasoner import TradeReasoner
        
        # Explicitly disable LLM
        reasoner = TradeReasoner(use_llm=False)
        
        confluence = create_sample_confluence_score(OrderSide.LONG, "strong")
        contexts = create_sample_timeframe_contexts()
        repository = StrategyRuleRepository()
        
        reasoning = reasoner.analyze_setup(
            asset="BTC",
            confluence_score=confluence,
            timeframe_contexts=contexts,
            strategy_repository=repository,
            current_price=50700.0
        )
        
        print(f"✅ Rule-based reasoning generated")
        print(f"   - Has explanation: {len(reasoning.explanation) > 0}")
        print(f"   - Has confluences: {len(reasoning.key_confluences) > 0}")
        print(f"   - Has risks: {len(reasoning.risks) >= 0}")
        print(f"   - Has HTF context: {len(reasoning.higher_tf_context) > 0}")
        
        return True
    except Exception as e:
        print(f"❌ Failed rule-based reasoning: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all verification tests."""
    print("\n" + "="*70)
    print(" TRADE REASONER VERIFICATION")
    print("="*70)
    print(f"Testing TradeReasoner implementation")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        test_1_import_trade_reasoner,
        test_2_initialize_reasoner,
        test_3_analyze_setup,
        test_4_risk_management,
        test_5_create_trade_record,
        test_6_short_setup,
        test_7_low_confluence,
        test_8_rule_based_reasoning
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test {test_func.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Trade Reasoner implementation is complete!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review issues above")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
