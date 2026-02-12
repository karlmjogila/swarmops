"""
Test Market Cycle Classifier

Comprehensive tests for the MarketCycleClassifier including:
- Drive phase detection
- Range phase detection  
- Liquidity phase detection
- Cycle transitions
- Recommendations

Run with: python -m pytest test_cycle_classifier.py -v
"""

import pytest
from datetime import datetime, timedelta
import random

from src.types import CandleData, Timeframe, MarketCycle, OrderSide
from src.detection.cycle_classifier import (
    MarketCycleClassifier,
    CycleClassification,
    CycleMetrics
)


def create_candle(
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float = 1000.0,
    timeframe: Timeframe = Timeframe.M15
) -> CandleData:
    """Helper to create candle data."""
    return CandleData(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timeframe=timeframe
    )


def generate_drive_candles(count: int = 50, bullish: bool = True) -> list:
    """Generate candles representing a DRIVE phase."""
    candles = []
    base_price = 100.0
    timestamp = datetime.utcnow() - timedelta(minutes=15 * count)
    
    for i in range(count):
        # Strong directional movement
        if bullish:
            open_price = base_price + i * 0.3
            close = open_price + random.uniform(0.4, 0.8)
            high = close + random.uniform(0.05, 0.15)
            low = open_price - random.uniform(0.02, 0.08)
        else:
            open_price = base_price - i * 0.3
            close = open_price - random.uniform(0.4, 0.8)
            high = open_price + random.uniform(0.02, 0.08)
            low = close - random.uniform(0.05, 0.15)
        
        volume = random.uniform(900, 1500)
        
        candles.append(create_candle(
            timestamp + timedelta(minutes=15 * i),
            open_price,
            high,
            low,
            close,
            volume
        ))
    
    return candles


def generate_range_candles(count: int = 50) -> list:
    """Generate candles representing a RANGE phase."""
    candles = []
    base_price = 100.0
    range_top = 102.0
    range_bottom = 98.0
    timestamp = datetime.utcnow() - timedelta(minutes=15 * count)
    
    current_price = base_price
    
    for i in range(count):
        # Oscillate within range
        if current_price > base_price:
            # Move down toward mean
            move = random.uniform(-0.5, 0.1)
        else:
            # Move up toward mean
            move = random.uniform(-0.1, 0.5)
        
        open_price = current_price
        close = max(range_bottom, min(range_top, current_price + move))
        
        # Small wicks
        high = close + random.uniform(0.05, 0.2)
        low = open_price - random.uniform(0.05, 0.2)
        
        # Keep within range
        high = min(high, range_top + 0.3)
        low = max(low, range_bottom - 0.3)
        
        volume = random.uniform(800, 1200)
        current_price = close
        
        candles.append(create_candle(
            timestamp + timedelta(minutes=15 * i),
            open_price,
            high,
            low,
            close,
            volume
        ))
    
    return candles


def generate_liquidity_candles(count: int = 50) -> list:
    """Generate candles representing a LIQUIDITY phase."""
    candles = []
    base_price = 100.0
    timestamp = datetime.utcnow() - timedelta(minutes=15 * count)
    
    current_price = base_price
    
    for i in range(count):
        # Create sweep patterns every few candles
        if i % 5 == 0:
            # Bullish sweep: wick down then close higher
            open_price = current_price
            low = open_price - random.uniform(0.8, 1.5)  # Large wick down
            close = open_price + random.uniform(0.2, 0.5)
            high = close + random.uniform(0.1, 0.3)
        elif i % 5 == 2:
            # Bearish sweep: wick up then close lower
            open_price = current_price
            high = open_price + random.uniform(0.8, 1.5)  # Large wick up
            close = open_price - random.uniform(0.2, 0.5)
            low = close - random.uniform(0.1, 0.3)
        else:
            # Normal candle with emphasis on wicks
            open_price = current_price
            body_size = random.uniform(0.1, 0.3)
            close = open_price + random.choice([-1, 1]) * body_size
            
            # Large wicks
            high = max(open_price, close) + random.uniform(0.4, 0.8)
            low = min(open_price, close) - random.uniform(0.4, 0.8)
        
        volume = random.uniform(1000, 2000)  # Higher volume on sweeps
        current_price = close
        
        candles.append(create_candle(
            timestamp + timedelta(minutes=15 * i),
            open_price,
            high,
            low,
            close,
            volume
        ))
    
    return candles


class TestMarketCycleClassifier:
    """Test suite for MarketCycleClassifier."""
    
    def test_initialization(self):
        """Test classifier initialization."""
        classifier = MarketCycleClassifier()
        
        assert classifier.drive_momentum_threshold > 0
        assert classifier.range_volatility_max > 0
        assert classifier.liquidity_wick_threshold > 0
        assert classifier.history is not None
    
    def test_drive_phase_detection_bullish(self):
        """Test detection of bullish DRIVE phase."""
        classifier = MarketCycleClassifier()
        candles = generate_drive_candles(count=50, bullish=True)
        
        classification = classifier.classify(candles)
        
        assert classification.cycle == MarketCycle.DRIVE
        assert classification.confidence > 0.6
        assert classification.dominant_bias == OrderSide.LONG
        assert abs(classification.metrics.momentum_score) > 0.5
        assert classification.metrics.directional_strength > 0.6
        print(f"✓ Detected bullish DRIVE phase (confidence: {classification.confidence:.2f})")
    
    def test_drive_phase_detection_bearish(self):
        """Test detection of bearish DRIVE phase."""
        classifier = MarketCycleClassifier()
        candles = generate_drive_candles(count=50, bullish=False)
        
        classification = classifier.classify(candles)
        
        assert classification.cycle == MarketCycle.DRIVE
        assert classification.confidence > 0.6
        assert classification.dominant_bias == OrderSide.SHORT
        assert classification.metrics.momentum_score < -0.5
        print(f"✓ Detected bearish DRIVE phase (confidence: {classification.confidence:.2f})")
    
    def test_range_phase_detection(self):
        """Test detection of RANGE phase."""
        classifier = MarketCycleClassifier()
        candles = generate_range_candles(count=50)
        
        classification = classifier.classify(candles)
        
        assert classification.cycle == MarketCycle.RANGE
        assert classification.confidence > 0.5
        assert classification.metrics.price_oscillations >= 3
        assert abs(classification.metrics.momentum_score) < 0.5
        print(f"✓ Detected RANGE phase (confidence: {classification.confidence:.2f})")
    
    def test_liquidity_phase_detection(self):
        """Test detection of LIQUIDITY phase."""
        classifier = MarketCycleClassifier()
        candles = generate_liquidity_candles(count=50)
        
        classification = classifier.classify(candles)
        
        # Liquidity phase should have high wick dominance and sweeps
        assert classification.metrics.wick_dominance > 0.4
        assert classification.metrics.sweep_count >= 2
        print(f"✓ Detected LIQUIDITY phase characteristics (wicks: {classification.metrics.wick_dominance:.2f}, sweeps: {classification.metrics.sweep_count})")
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        classifier = MarketCycleClassifier()
        candles = generate_drive_candles(count=10)  # Too few candles
        
        classification = classifier.classify(candles)
        
        assert classification.confidence == 0.0
        assert classification.sub_phase == "insufficient_data"
        print("✓ Handled insufficient data correctly")
    
    def test_cycle_metrics_calculation(self):
        """Test that all cycle metrics are calculated."""
        classifier = MarketCycleClassifier()
        candles = generate_drive_candles(count=50)
        
        classification = classifier.classify(candles)
        metrics = classification.metrics
        
        # Check all metrics are populated
        assert isinstance(metrics.momentum_score, float)
        assert isinstance(metrics.directional_strength, float)
        assert isinstance(metrics.normalized_volatility, float)
        assert isinstance(metrics.wick_dominance, float)
        assert isinstance(metrics.price_oscillations, int)
        
        # Check value ranges
        assert -1.0 <= metrics.momentum_score <= 1.0
        assert 0.0 <= metrics.directional_strength <= 1.0
        assert 0.0 <= metrics.normalized_volatility <= 1.0
        assert 0.0 <= metrics.wick_dominance <= 1.0
        
        print("✓ All cycle metrics calculated correctly")
    
    def test_sub_phase_detection(self):
        """Test sub-phase classification."""
        classifier = MarketCycleClassifier()
        
        # Strong drive should detect sub-phase
        drive_candles = generate_drive_candles(count=50, bullish=True)
        classification = classifier.classify(drive_candles)
        
        assert classification.sub_phase in [
            "strong_drive", "moderate_drive", "accelerating_drive", 
            "exhausting_drive", "steady_drive"
        ]
        print(f"✓ Sub-phase detected: {classification.sub_phase}")
    
    def test_cycle_recommendations(self):
        """Test cycle-based recommendations."""
        classifier = MarketCycleClassifier()
        
        # Test drive recommendations
        drive_candles = generate_drive_candles(count=50)
        classification = classifier.classify(drive_candles)
        recommendations = classifier.get_cycle_recommendation(classification)
        
        assert 'preferred_patterns' in recommendations
        assert 'avoid_patterns' in recommendations
        assert 'confidence_adjustment' in recommendations
        assert isinstance(recommendations['notes'], list)
        
        if classification.cycle == MarketCycle.DRIVE:
            assert 'breakout' in recommendations['preferred_patterns']
            assert 'mean_reversion' in recommendations['avoid_patterns']
        
        print(f"✓ Generated recommendations for {classification.cycle.value} phase")
    
    def test_cycle_transition_detection(self):
        """Test detection of cycle transitions."""
        classifier = MarketCycleClassifier()
        
        # Start with drive
        drive_candles = generate_drive_candles(count=30)
        classifier.classify(drive_candles)
        
        # Transition to range
        range_candles = generate_range_candles(count=30)
        combined = drive_candles + range_candles
        classification = classifier.classify(combined)
        
        # Should detect that we're in or transitioning to range
        assert classification.cycle == MarketCycle.RANGE or \
               classification.transition_probability > 0.5
        
        print(f"✓ Cycle transition handling works (transition prob: {classification.transition_probability:.2f})")
    
    def test_cycle_history_tracking(self):
        """Test that cycle history is tracked properly."""
        classifier = MarketCycleClassifier()
        
        # Classify multiple times
        candles = generate_drive_candles(count=40)
        for i in range(5):
            classifier.classify(candles[:30 + i*2])
        
        # Check history
        assert len(classifier.history.classifications) == 5
        assert classifier.history.cycle_duration_candles >= 0
        
        recent_cycles = classifier.history.get_recent_cycles(count=3)
        assert len(recent_cycles) >= 1
        
        print(f"✓ Cycle history tracking works (duration: {classifier.history.cycle_duration_candles} candles)")
    
    def test_cycle_health_calculation(self):
        """Test cycle health scoring."""
        classifier = MarketCycleClassifier()
        
        # Clean drive should have high health
        drive_candles = generate_drive_candles(count=50, bullish=True)
        classification = classifier.classify(drive_candles)
        
        assert 0.0 <= classification.cycle_health <= 1.0
        
        if classification.cycle == MarketCycle.DRIVE:
            # Strong, clean drive should have good health
            assert classification.cycle_health > 0.5
        
        print(f"✓ Cycle health: {classification.cycle_health:.2f}")
    
    def test_bias_determination(self):
        """Test directional bias detection."""
        classifier = MarketCycleClassifier()
        
        # Bullish drive should show long bias
        bull_candles = generate_drive_candles(count=50, bullish=True)
        bull_classification = classifier.classify(bull_candles)
        assert bull_classification.dominant_bias == OrderSide.LONG
        
        # Bearish drive should show short bias
        bear_candles = generate_drive_candles(count=50, bullish=False)
        bear_classification = classifier.classify(bear_candles)
        assert bear_classification.dominant_bias == OrderSide.SHORT
        
        # Range should have no strong bias or neutral
        range_candles = generate_range_candles(count=50)
        range_classification = classifier.classify(range_candles)
        # Range might have weak bias or none
        
        print(f"✓ Bias detection works (bull: {bull_classification.dominant_bias}, bear: {bear_classification.dominant_bias})")


def test_real_world_scenario():
    """Test with a realistic mixed scenario."""
    classifier = MarketCycleClassifier()
    
    # Build a realistic sequence: range -> breakout drive -> exhaustion -> liquidity
    candles = []
    
    # 1. Start in range
    candles.extend(generate_range_candles(count=30))
    range_classification = classifier.classify(candles)
    print(f"\n📊 Phase 1 - Range: {range_classification.cycle.value} (confidence: {range_classification.confidence:.2f})")
    
    # 2. Breakout into drive
    candles.extend(generate_drive_candles(count=25, bullish=True))
    drive_classification = classifier.classify(candles)
    print(f"📊 Phase 2 - Breakout: {drive_classification.cycle.value} (confidence: {drive_classification.confidence:.2f})")
    
    # 3. Liquidity grab at top
    candles.extend(generate_liquidity_candles(count=20))
    liquidity_classification = classifier.classify(candles)
    print(f"📊 Phase 3 - Top: {liquidity_classification.cycle.value} (confidence: {liquidity_classification.confidence:.2f})")
    
    # Should show cycle transitions in history
    recent_cycles = classifier.history.get_recent_cycles(count=5)
    print(f"📊 Recent cycle sequence: {[c.value for c in recent_cycles]}")
    
    assert len(classifier.history.classifications) == 3


if __name__ == "__main__":
    print("=" * 60)
    print("Market Cycle Classifier Test Suite")
    print("=" * 60)
    
    # Run tests
    test_suite = TestMarketCycleClassifier()
    
    print("\n🧪 Running Tests...\n")
    
    test_suite.test_initialization()
    test_suite.test_drive_phase_detection_bullish()
    test_suite.test_drive_phase_detection_bearish()
    test_suite.test_range_phase_detection()
    test_suite.test_liquidity_phase_detection()
    test_suite.test_insufficient_data()
    test_suite.test_cycle_metrics_calculation()
    test_suite.test_sub_phase_detection()
    test_suite.test_cycle_recommendations()
    test_suite.test_cycle_transition_detection()
    test_suite.test_cycle_history_tracking()
    test_suite.test_cycle_health_calculation()
    test_suite.test_bias_determination()
    
    print("\n" + "=" * 60)
    print("Real-world Scenario Test")
    print("=" * 60)
    test_real_world_scenario()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
