"""Unit tests for support/resistance zone detection.

Tests zone detection, merging, strength classification, and analysis.
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.core.market.data import Candle
from app.core.patterns.zones import (
    SupportResistanceDetector,
    ZoneType,
    ZoneStrength,
    SupportResistanceZone,
)


def create_test_candles(price_data: List[tuple], symbol: str = "BTCUSD", timeframe: str = "5m") -> List[Candle]:
    """Helper to create test candles from price tuples.
    
    Args:
        price_data: List of (open, high, low, close, volume) tuples
        symbol: Trading symbol
        timeframe: Timeframe string
        
    Returns:
        List of Candle objects
    """
    candles = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    for i, (o, h, l, c, v) in enumerate(price_data):
        timestamp = base_time + timedelta(minutes=5 * i)
        candles.append(Candle(
            timestamp=timestamp,
            open=o,
            high=h,
            low=l,
            close=c,
            volume=v,
            symbol=symbol,
            timeframe=timeframe,
        ))
    
    return candles


class TestZoneDetection:
    """Tests for basic zone detection."""
    
    def test_support_zone_detection(self):
        """Test that support zones are detected at swing lows."""
        # Create data with clear support at 100
        price_data = [
            (105, 106, 104, 105, 1000),
            (105, 106, 104, 105, 1000),
            (105, 106, 100, 101, 1500),  # Touch support
            (101, 104, 100, 103, 1000),  # Bounce
            (103, 105, 102, 104, 1000),
            (104, 106, 103, 105, 1000),
            (105, 106, 100, 102, 1500),  # Touch support again
            (102, 104, 101, 103, 1000),  # Bounce
            (103, 105, 102, 104, 1000),
            (104, 106, 103, 105, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(min_touches=2)
        
        zones = detector.detect_zones(candles)
        
        # Should detect at least one support zone
        assert len(zones) > 0
        
        # Find any support zone (detector may create zones around swing lows, not necessarily at exact level)
        support_zones = [z for z in zones if z.zone_type in (ZoneType.SUPPORT, ZoneType.SUPPORT_RESISTANCE)]
        
        assert len(support_zones) > 0, "Should detect at least one support zone"
        
        # Verify the support zone has minimum touches
        has_valid_touches = any(zone.touch_count >= 2 for zone in support_zones)
        assert has_valid_touches, "At least one support zone should have 2+ touches"
    
    def test_resistance_zone_detection(self):
        """Test that resistance zones are detected at swing highs."""
        # Create data with clear resistance at 110
        price_data = [
            (105, 106, 104, 105, 1000),
            (105, 106, 104, 105, 1000),
            (105, 110, 105, 109, 1500),  # Touch resistance
            (109, 110, 107, 108, 1000),  # Rejection
            (108, 109, 106, 107, 1000),
            (107, 108, 105, 106, 1000),
            (106, 110, 106, 109, 1500),  # Touch resistance again
            (109, 110, 107, 108, 1000),  # Rejection
            (108, 109, 106, 107, 1000),
            (107, 108, 105, 106, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(min_touches=2)
        
        zones = detector.detect_zones(candles)
        
        # Should detect at least one resistance zone
        assert len(zones) > 0
        
        # Find zone around 110
        resistance_zone = None
        for zone in zones:
            if zone.zone_type in (ZoneType.RESISTANCE, ZoneType.SUPPORT_RESISTANCE):
                if 109 <= zone.midpoint <= 111:
                    resistance_zone = zone
                    break
        
        assert resistance_zone is not None, "Should detect resistance zone around 110"
        assert resistance_zone.touch_count >= 2, "Should have at least 2 touches"
    
    def test_min_touches_filter(self):
        """Test that zones with fewer than min_touches are filtered out."""
        # Create data with one clear zone (2 touches) and one weak zone (1 touch)
        price_data = [
            (100, 101, 100, 100, 1000),  # Touch support once
            (100, 102, 100, 101, 1000),
            (101, 103, 101, 102, 1000),
            (102, 105, 102, 104, 1000),
            (104, 106, 100, 101, 1000),  # Touch support second time
            (101, 103, 101, 102, 1000),
            (102, 104, 102, 103, 1000),
            (103, 110, 103, 109, 1000),  # Touch resistance once only
            (109, 110, 107, 108, 1000),
            (108, 109, 106, 107, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(min_touches=2)
        
        zones = detector.detect_zones(candles)
        
        # All zones should have at least 2 touches
        for zone in zones:
            assert zone.touch_count >= 2, f"Zone {zone.midpoint} has only {zone.touch_count} touches"
    
    def test_zone_merging(self):
        """Test that nearby zones are merged."""
        # Create data with two very close support levels that should merge
        price_data = [
            (105, 106, 100.0, 101, 1000),  # Touch at 100.0
            (101, 103, 101, 102, 1000),
            (102, 104, 100.3, 101, 1000),  # Touch at 100.3 (very close)
            (101, 103, 101, 102, 1000),
            (102, 104, 100.1, 101, 1000),  # Touch at 100.1 (very close)
            (101, 103, 101, 102, 1000),
            (102, 105, 102, 104, 1000),
            (104, 106, 104, 105, 1000),
            (105, 107, 105, 106, 1000),
            (106, 108, 106, 107, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(
            min_touches=2,
            zone_merge_threshold=0.01  # 1% merge threshold
        )
        
        zones = detector.detect_zones(candles)
        
        # Should merge into fewer zones
        support_zones = [z for z in zones if z.zone_type in (ZoneType.SUPPORT, ZoneType.SUPPORT_RESISTANCE)]
        
        # Count zones near 100
        zones_near_100 = [z for z in support_zones if 99 <= z.midpoint <= 101]
        
        # Should have merged into 1 or 2 zones max (not 3 separate zones)
        assert len(zones_near_100) <= 2, "Should merge nearby zones"


class TestZoneCharacteristics:
    """Tests for zone characteristics and properties."""
    
    def test_bounce_rate_calculation(self):
        """Test that bounce rate is calculated correctly."""
        # Create a zone and add touches
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        candle = Candle(
            timestamp=base_time,
            open=100, high=101, low=99, close=100,
            volume=1000, symbol="BTCUSD", timeframe="5m"
        )
        
        from app.core.patterns.zones import ZoneTouch
        
        touches = [
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=1.0),
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=1.0),
            ZoneTouch(candle, 100, is_bounce=False, volume_ratio=1.0),
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=1.0),
        ]
        
        zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.MODERATE,
            touches=touches,
            first_touch=base_time,
            last_touch=base_time,
        )
        
        # 3 bounces out of 4 touches = 75%
        assert zone.bounce_rate == 0.75
        assert zone.bounce_count == 3
        assert zone.touch_count == 4
    
    def test_zone_contains_price(self):
        """Test zone price containment check."""
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.MODERATE,
            touches=[],
            first_touch=base_time,
            last_touch=base_time,
        )
        
        # Test prices within zone
        assert zone.contains_price(100.0)
        assert zone.contains_price(99.5)
        assert zone.contains_price(100.5)
        
        # Test prices outside zone
        assert not zone.contains_price(98.0)
        assert not zone.contains_price(102.0)
        
        # Test with buffer (zone width is 1.0, so 2% buffer = 0.02 extension on each side)
        # Zone extends to [99.5 - 0.02, 100.5 + 0.02] = [99.48, 100.52]
        assert zone.contains_price(99.48, buffer=0.02)
        assert zone.contains_price(100.52, buffer=0.02)
        assert not zone.contains_price(99.4, buffer=0.02)  # Just outside
        assert not zone.contains_price(100.6, buffer=0.02)  # Just outside
    
    def test_distance_to_zone(self):
        """Test distance calculation to zone."""
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.MODERATE,
            touches=[],
            first_touch=base_time,
            last_touch=base_time,
        )
        
        # Price inside zone
        assert zone.distance_to_zone(100.0) == 0.0
        
        # Price above zone
        assert zone.distance_to_zone(105.0) == 4.5
        
        # Price below zone
        assert zone.distance_to_zone(95.0) == 4.5
    
    def test_strength_score_calculation(self):
        """Test that strength score considers multiple factors."""
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        candle = Candle(
            timestamp=base_time,
            open=100, high=101, low=99, close=100,
            volume=1000, symbol="BTCUSD", timeframe="5m"
        )
        
        from app.core.patterns.zones import ZoneTouch
        
        # Strong zone: many touches, high bounce rate, high volume
        strong_touches = [
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=2.0)
            for _ in range(8)
        ]
        
        strong_zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.STRONG,
            touches=strong_touches,
            first_touch=base_time,
            last_touch=base_time,
            volume_profile=2.0,
        )
        
        # Weak zone: few touches, lower bounce rate, low volume
        weak_touches = [
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=0.5),
            ZoneTouch(candle, 100, is_bounce=False, volume_ratio=0.5),
        ]
        
        weak_zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.WEAK,
            touches=weak_touches,
            first_touch=base_time,
            last_touch=base_time,
            volume_profile=0.5,
        )
        
        strong_score = strong_zone.calculate_strength_score()
        weak_score = weak_zone.calculate_strength_score()
        
        assert strong_score > weak_score, "Strong zone should have higher score"
        assert 0.0 <= strong_score <= 1.0, "Score should be between 0 and 1"
        assert 0.0 <= weak_score <= 1.0, "Score should be between 0 and 1"


class TestZoneAnalysis:
    """Tests for comprehensive zone analysis."""
    
    def test_analyze_zones_returns_dict(self):
        """Test that analyze_zones returns proper structure."""
        price_data = [
            (100, 102, 100, 101, 1000),
            (101, 103, 101, 102, 1000),
            (102, 104, 100, 101, 1000),
            (101, 103, 101, 102, 1000),
            (102, 110, 102, 109, 1000),
            (109, 110, 107, 108, 1000),
            (108, 110, 108, 109, 1000),
            (109, 110, 107, 108, 1000),
            (108, 109, 106, 107, 1000),
            (107, 108, 105, 106, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(min_touches=2)
        
        analysis = detector.analyze_zones(candles)
        
        # Check structure
        assert "zones" in analysis
        assert "support_zones" in analysis
        assert "resistance_zones" in analysis
        assert "total_zones" in analysis
        assert "support_count" in analysis
        assert "resistance_count" in analysis
        assert "current_price" in analysis
        assert "zone_strength_distribution" in analysis
        
        # Check types
        assert isinstance(analysis["zones"], list)
        assert isinstance(analysis["total_zones"], int)
        assert isinstance(analysis["current_price"], (int, float))
    
    def test_find_nearest_zones(self):
        """Test finding zones nearest to current price."""
        price_data = [
            (90, 92, 90, 91, 1000),   # Support around 90
            (91, 93, 90, 92, 1000),
            (92, 94, 90, 91, 1000),
            (91, 95, 91, 94, 1000),
            (94, 96, 94, 95, 1000),
            (95, 97, 95, 96, 1000),
            (96, 98, 96, 97, 1000),
            (97, 110, 97, 109, 1000),  # Resistance around 110
            (109, 110, 107, 108, 1000),
            (108, 110, 108, 109, 1000),
            (109, 110, 107, 108, 1000),
            (108, 109, 105, 106, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(min_touches=2)
        
        zones = detector.detect_zones(candles)
        current_price = 105.0  # Between support and resistance
        
        nearest = detector.find_nearest_zones(zones, current_price, max_distance_pct=0.20)
        
        assert len(nearest) > 0, "Should find nearest zones"
        
        # Should be sorted by distance
        distances = [abs(dist) for _, dist in nearest]
        assert distances == sorted(distances), "Should be sorted by distance"
    
    def test_get_active_zones(self):
        """Test filtering for active zones."""
        price_data = [
            (100, 102, 100, 101, 1000),
            (101, 103, 100, 102, 1000),
            (102, 104, 100, 101, 1000),
            (101, 103, 101, 102, 1000),
            (102, 104, 102, 103, 1000),
            (103, 105, 103, 104, 1000),
            (104, 106, 104, 105, 1000),
            (105, 107, 105, 106, 1000),
            (106, 108, 106, 107, 1000),
            (107, 109, 107, 108, 1000),
        ]
        
        candles = create_test_candles(price_data)
        detector = SupportResistanceDetector(min_touches=2)
        
        zones = detector.detect_zones(candles)
        current_price = 108.0
        
        active = detector.get_active_zones(zones, current_price)
        
        # All active zones should be within reasonable distance
        for zone in active:
            distance_pct = abs(zone.distance_to_zone(current_price)) / current_price
            assert distance_pct <= 0.10, "Active zones should be within 10% of price"
            assert not zone.broken, "Active zones should not be broken"


class TestZoneStrengthClassification:
    """Tests for zone strength classification."""
    
    def test_weak_zone_classification(self):
        """Test that zones with few touches are classified as weak."""
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        candle = Candle(
            timestamp=base_time,
            open=100, high=101, low=99, close=100,
            volume=1000, symbol="BTCUSD", timeframe="5m"
        )
        
        from app.core.patterns.zones import ZoneTouch
        
        # Zone with only 2 touches
        touches = [
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=1.0),
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=1.0),
        ]
        
        zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.WEAK,
            touches=touches,
            first_touch=base_time,
            last_touch=base_time,
            volume_profile=1.0,
        )
        
        detector = SupportResistanceDetector()
        classified_strength = detector._classify_strength(zone)
        
        assert classified_strength in (ZoneStrength.WEAK, ZoneStrength.MODERATE)
    
    def test_strong_zone_classification(self):
        """Test that zones with many successful bounces are classified as strong."""
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        candle = Candle(
            timestamp=base_time,
            open=100, high=101, low=99, close=100,
            volume=1000, symbol="BTCUSD", timeframe="5m"
        )
        
        from app.core.patterns.zones import ZoneTouch
        
        # Zone with many touches and high bounce rate
        touches = [
            ZoneTouch(candle, 100, is_bounce=True, volume_ratio=1.5)
            for _ in range(6)
        ]
        
        zone = SupportResistanceZone(
            zone_type=ZoneType.SUPPORT,
            top=100.5,
            bottom=99.5,
            strength=ZoneStrength.STRONG,
            touches=touches,
            first_touch=base_time,
            last_touch=base_time,
            volume_profile=1.5,
        )
        
        detector = SupportResistanceDetector()
        classified_strength = detector._classify_strength(zone)
        
        assert classified_strength in (ZoneStrength.STRONG, ZoneStrength.MAJOR)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
