"""
Test suite for Market Structure Analyzer

Tests the comprehensive market structure analysis functionality including
trend detection, support/resistance zones, BOS/CHOCH detection, and market cycles.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import List

from src.detection.market_structure import (
    MarketStructureAnalyzer, 
    StructurePoint,
    SupportResistanceZone,
    TrendAnalysis,
    BreakOfStructure,
    ChangeOfCharacter
)
from src.types import CandleData, Timeframe, OrderSide, MarketCycle


class TestMarketStructureAnalyzer:
    """Test cases for MarketStructureAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MarketStructureAnalyzer()
        self.base_time = datetime(2024, 1, 1, 12, 0, 0)
        
    def create_test_candles(self, count: int, trend: str = "neutral") -> List[CandleData]:
        """Create test candle data with specified trend."""
        candles = []
        base_price = 100.0
        
        for i in range(count):
            timestamp = self.base_time + timedelta(minutes=i * 15)
            
            if trend == "uptrend":
                # Create upward trending candles
                open_price = base_price + (i * 0.5) + np.random.uniform(-0.2, 0.2)
                close_price = open_price + np.random.uniform(0.1, 0.8)
                high_price = close_price + np.random.uniform(0.0, 0.3)
                low_price = open_price - np.random.uniform(0.0, 0.2)
            elif trend == "downtrend":
                # Create downward trending candles
                open_price = base_price - (i * 0.5) + np.random.uniform(-0.2, 0.2)
                close_price = open_price - np.random.uniform(0.1, 0.8)
                low_price = close_price - np.random.uniform(0.0, 0.3)
                high_price = open_price + np.random.uniform(0.0, 0.2)
            else:
                # Create ranging/neutral candles
                open_price = base_price + np.random.uniform(-1.0, 1.0)
                close_price = open_price + np.random.uniform(-0.5, 0.5)
                high_price = max(open_price, close_price) + np.random.uniform(0.0, 0.3)
                low_price = min(open_price, close_price) - np.random.uniform(0.0, 0.3)
            
            candle = CandleData(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=np.random.uniform(1000, 5000),
                timeframe=Timeframe.M15
            )
            candles.append(candle)
            
        return candles
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization with default parameters."""
        assert self.analyzer.swing_detection_periods == 5
        assert self.analyzer.min_structure_strength == 0.4
        assert self.analyzer.zone_touch_threshold == 0.002
        assert self.analyzer.trend_confirmation_periods == 10
    
    def test_insufficient_data_handling(self):
        """Test behavior with insufficient candle data."""
        # Test with empty list
        structure = self.analyzer.analyze_structure([], "BTCUSDT", Timeframe.M15)
        assert structure.asset == "BTCUSDT"
        assert structure.timeframe == Timeframe.M15
        assert len(structure.higher_highs) == 0
        assert len(structure.lower_lows) == 0
        assert structure.trend_direction is None
        
        # Test with insufficient data (less than min_periods)
        short_candles = self.create_test_candles(10)
        structure = self.analyzer.analyze_structure(short_candles, "BTCUSDT", Timeframe.M15)
        assert structure.asset == "BTCUSDT"
        assert len(structure.higher_highs) == 0
    
    def test_uptrend_detection(self):
        """Test detection of uptrend structure."""
        uptrend_candles = self.create_test_candles(100, trend="uptrend")
        
        structure = self.analyzer.analyze_structure(uptrend_candles, "BTCUSDT", Timeframe.M15)
        
        # Should detect uptrend
        assert structure.trend_direction == OrderSide.LONG
        assert structure.trend_strength > 0.0
        
        # Should have some structure points
        assert len(structure.higher_highs) > 0 or len(structure.lower_lows) > 0
    
    def test_downtrend_detection(self):
        """Test detection of downtrend structure."""
        downtrend_candles = self.create_test_candles(100, trend="downtrend")
        
        structure = self.analyzer.analyze_structure(downtrend_candles, "BTCUSDT", Timeframe.M15)
        
        # Should detect downtrend
        assert structure.trend_direction == OrderSide.SHORT
        assert structure.trend_strength > 0.0
    
    def test_ranging_market_detection(self):
        """Test detection of ranging/neutral market."""
        ranging_candles = self.create_test_candles(100, trend="neutral")
        
        structure = self.analyzer.analyze_structure(ranging_candles, "BTCUSDT", Timeframe.M15)
        
        # Should have lower trend strength for ranging markets
        # Trend direction might be None or have low confidence
        if structure.trend_direction is not None:
            assert structure.trend_strength < 0.8  # Should be less confident
    
    def test_structure_point_detection(self):
        """Test detection of swing highs and lows."""
        # Create candles with clear swings
        test_candles = []
        base_time = self.base_time
        
        # Create a pattern with clear swing high and low
        prices = [100, 101, 102, 105, 103, 101, 99, 98, 100, 102, 104]
        
        for i, price in enumerate(prices):
            candle = CandleData(
                timestamp=base_time + timedelta(minutes=i * 15),
                open=price - 0.5,
                high=price + 0.5,
                low=price - 1.0,
                close=price,
                volume=1000,
                timeframe=Timeframe.M15
            )
            test_candles.append(candle)
        
        # Add more candles to meet minimum requirement
        test_candles.extend(self.create_test_candles(50, trend="neutral"))
        
        structure_points = self.analyzer._detect_structure_points(test_candles)
        
        # Should detect some structure points
        assert len(structure_points) > 0
        
        # Check that structure points have required properties
        for point in structure_points:
            assert isinstance(point, StructurePoint)
            assert point.point_type in ['high', 'low']
            assert 0.0 <= point.strength <= 1.0
            assert isinstance(point.timestamp, datetime)
    
    def test_zone_identification(self):
        """Test support and resistance zone identification."""
        candles = self.create_test_candles(100, trend="neutral")
        structure_points = self.analyzer._detect_structure_points(candles)
        
        zones = self.analyzer._identify_zones(candles, structure_points)
        
        # Should create zones (may be empty for random data, but test structure)
        assert isinstance(zones, list)
        for zone in zones:
            assert isinstance(zone, SupportResistanceZone)
            assert zone.zone_type in ['support', 'resistance']
            assert zone.strength >= 0.0
            assert zone.touch_count >= 2  # Minimum touches to create zone
    
    def test_trend_analysis(self):
        """Test comprehensive trend analysis."""
        uptrend_candles = self.create_test_candles(100, trend="uptrend")
        structure_points = self.analyzer._detect_structure_points(uptrend_candles)
        
        trend_analysis = self.analyzer._analyze_trend(uptrend_candles, structure_points)
        
        assert isinstance(trend_analysis, TrendAnalysis)
        assert trend_analysis.direction in [None, OrderSide.LONG, OrderSide.SHORT]
        assert 0.0 <= trend_analysis.strength <= 1.0
        assert 0.0 <= trend_analysis.confidence <= 1.0
        assert trend_analysis.duration_candles > 0
        assert isinstance(trend_analysis.start_timestamp, datetime)
    
    def test_break_of_structure_detection(self):
        """Test break of structure (BOS) event detection."""
        candles = self.create_test_candles(100, trend="neutral")
        structure_points = self.analyzer._detect_structure_points(candles)
        
        bos_events = self.analyzer._detect_break_of_structure(candles, structure_points)
        
        # Should return list of BOS events (may be empty)
        assert isinstance(bos_events, list)
        for bos in bos_events:
            assert isinstance(bos, BreakOfStructure)
            assert bos.break_type in ['bos_high', 'bos_low']
            assert 0.0 <= bos.strength <= 1.0
            assert isinstance(bos.timestamp, datetime)
    
    def test_change_of_character_detection(self):
        """Test change of character (CHOCH) event detection."""
        candles = self.create_test_candles(100, trend="uptrend")
        structure_points = self.analyzer._detect_structure_points(candles)
        trend_analysis = self.analyzer._analyze_trend(candles, structure_points)
        bos_events = self.analyzer._detect_break_of_structure(candles, structure_points)
        
        choch_events = self.analyzer._detect_change_of_character(candles, bos_events, trend_analysis)
        
        # Should return list of CHOCH events (may be empty)
        assert isinstance(choch_events, list)
        for choch in choch_events:
            assert isinstance(choch, ChangeOfCharacter)
            assert choch.from_trend in [OrderSide.LONG, OrderSide.SHORT]
            assert choch.to_trend in [OrderSide.LONG, OrderSide.SHORT]
            assert choch.from_trend != choch.to_trend  # Must be different
            assert 0.0 <= choch.confidence <= 1.0
    
    def test_market_cycle_determination(self):
        """Test market cycle phase determination."""
        # Test different market conditions
        test_cases = [
            ("uptrend", "drive_expected"),
            ("downtrend", "drive_expected"), 
            ("neutral", "range_expected")
        ]
        
        for trend, expected_type in test_cases:
            candles = self.create_test_candles(100, trend=trend)
            structure_points = self.analyzer._detect_structure_points(candles)
            trend_analysis = self.analyzer._analyze_trend(candles, structure_points)
            bos_events = self.analyzer._detect_break_of_structure(candles, structure_points)
            
            market_cycle = self.analyzer._determine_market_cycle(candles, trend_analysis, bos_events)
            
            assert market_cycle in [MarketCycle.DRIVE, MarketCycle.RANGE, MarketCycle.LIQUIDITY]
    
    def test_confluence_calculation(self):
        """Test confluence score calculation."""
        candles = self.create_test_candles(100, trend="neutral")
        structure_points = self.analyzer._detect_structure_points(candles)
        zones = self.analyzer._identify_zones(candles, structure_points)
        
        confluence_data = self.analyzer._calculate_confluence(candles, zones, structure_points)
        
        assert isinstance(confluence_data, dict)
        assert 'current_confluence' in confluence_data
        assert 0.0 <= confluence_data['current_confluence'] <= 1.0
    
    def test_full_analysis_integration(self):
        """Test complete market structure analysis end-to-end."""
        candles = self.create_test_candles(100, trend="uptrend")
        
        structure = self.analyzer.analyze_structure(candles, "BTCUSDT", Timeframe.M15, min_periods=50)
        
        # Verify complete structure object
        assert structure.asset == "BTCUSDT"
        assert structure.timeframe == Timeframe.M15
        assert isinstance(structure.timestamp, datetime)
        
        # Verify structure components
        assert isinstance(structure.higher_highs, list)
        assert isinstance(structure.lower_lows, list)
        assert isinstance(structure.support_zones, list)
        assert isinstance(structure.resistance_zones, list)
        
        # Verify trend analysis
        assert structure.trend_direction in [None, OrderSide.LONG, OrderSide.SHORT]
        assert 0.0 <= structure.trend_strength <= 1.0
    
    def test_get_current_bias(self):
        """Test current market bias detection."""
        candles = self.create_test_candles(100, trend="uptrend")
        structure = self.analyzer.analyze_structure(candles, "BTCUSDT", Timeframe.M15)
        
        bias = self.analyzer.get_current_bias(structure)
        assert bias in [None, OrderSide.LONG, OrderSide.SHORT]
        assert bias == structure.trend_direction
    
    def test_get_key_levels(self):
        """Test key level identification."""
        candles = self.create_test_candles(100, trend="neutral")
        structure = self.analyzer.analyze_structure(candles, "BTCUSDT", Timeframe.M15)
        current_price = candles[-1].close
        
        key_levels = self.analyzer.get_key_levels(structure, current_price)
        
        assert isinstance(key_levels, dict)
        assert 'support' in key_levels
        assert 'resistance' in key_levels
        assert 'structure_highs' in key_levels
        assert 'structure_lows' in key_levels
        
        for level_type, levels in key_levels.items():
            assert isinstance(levels, list)
            # All levels should be sorted
            assert levels == sorted(levels)
    
    def test_check_structure_break(self):
        """Test structure break detection."""
        candles = self.create_test_candles(100, trend="neutral")
        structure = self.analyzer.analyze_structure(candles, "BTCUSDT", Timeframe.M15)
        current_price = candles[-1].close
        
        # Test break above (LONG)
        is_break_long, strength_long = self.analyzer.check_structure_break(
            structure, current_price + 2.0, OrderSide.LONG
        )
        assert isinstance(is_break_long, bool)
        assert 0.0 <= strength_long <= 1.0
        
        # Test break below (SHORT)
        is_break_short, strength_short = self.analyzer.check_structure_break(
            structure, current_price - 2.0, OrderSide.SHORT
        )
        assert isinstance(is_break_short, bool)
        assert 0.0 <= strength_short <= 1.0
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with single candle
        single_candle = [CandleData(
            timestamp=self.base_time,
            open=100.0, high=101.0, low=99.0, close=100.5,
            volume=1000, timeframe=Timeframe.M15
        )]
        
        structure = self.analyzer.analyze_structure(single_candle, "BTCUSDT", Timeframe.M15)
        assert structure.asset == "BTCUSDT"
        
        # Test with identical prices (no volatility)
        identical_candles = []
        for i in range(60):
            candle = CandleData(
                timestamp=self.base_time + timedelta(minutes=i * 15),
                open=100.0, high=100.0, low=100.0, close=100.0,
                volume=1000, timeframe=Timeframe.M15
            )
            identical_candles.append(candle)
        
        structure = self.analyzer.analyze_structure(identical_candles, "BTCUSDT", Timeframe.M15)
        # Should handle gracefully without errors
        assert isinstance(structure.trend_strength, float)


@pytest.fixture
def analyzer():
    """Provide analyzer instance for tests."""
    return MarketStructureAnalyzer()


@pytest.fixture
def sample_candles():
    """Provide sample candle data for tests."""
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    candles = []
    
    for i in range(100):
        candle = CandleData(
            timestamp=base_time + timedelta(minutes=i * 15),
            open=100.0 + np.random.uniform(-2, 2),
            high=100.0 + np.random.uniform(0, 3),
            low=100.0 + np.random.uniform(-3, 0),
            close=100.0 + np.random.uniform(-2, 2),
            volume=np.random.uniform(1000, 5000),
            timeframe=Timeframe.M15
        )
        candles.append(candle)
    
    return candles


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])