#!/usr/bin/env python3
"""Example usage of the Support/Resistance Zone Detector.

Demonstrates how to:
1. Load candle data
2. Detect support and resistance zones
3. Identify nearest zones to current price
4. Interpret zone strength and characteristics
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from datetime import datetime, timedelta
from app.core.market.data import Candle
from app.core.patterns.zones import (
    SupportResistanceDetector,
    ZoneType,
    ZoneStrength,
)


def create_sample_candles() -> list[Candle]:
    """Create sample candle data with clear support/resistance zones.
    
    Simulates price action with:
    - A strong support zone around 100
    - A resistance zone around 110
    - Multiple touches of each zone
    """
    base_time = datetime(2024, 1, 1, 0, 0)
    candles = []
    
    # Create realistic price action with zones
    # Support at ~100, Resistance at ~110
    prices = [
        (105, 106, 104, 105),  # Start
        (105, 107, 104, 106),
        (106, 108, 105, 107),
        (107, 109, 106, 108),
        (108, 111, 107, 110),  # Touch resistance (110)
        (110, 111, 109, 109),  # Rejection
        (109, 110, 107, 108),
        (108, 109, 106, 107),
        (107, 108, 105, 106),
        (106, 107, 103, 104),
        (104, 105, 100, 101),  # Touch support (100)
        (101, 103, 100, 102),  # Bounce from support
        (102, 104, 101, 103),
        (103, 105, 102, 104),
        (104, 106, 103, 105),
        (105, 107, 104, 106),
        (106, 108, 105, 107),
        (107, 110, 106, 109),
        (109, 111, 108, 110),  # Touch resistance again
        (110, 111, 108, 109),  # Rejection
        (109, 110, 107, 108),
        (108, 109, 106, 107),
        (107, 108, 104, 105),
        (105, 106, 102, 103),
        (103, 104, 100, 101),  # Touch support again
        (101, 104, 100, 103),  # Strong bounce
        (103, 106, 102, 105),
        (105, 108, 104, 107),
        (107, 110, 106, 109),
        (109, 112, 108, 111),  # Break resistance!
        (111, 113, 110, 112),  # Old resistance becomes support
        (112, 114, 111, 113),
        (113, 115, 112, 114),
        (114, 116, 113, 115),
        (115, 117, 114, 116),
    ]
    
    for i, (open_, high, low, close) in enumerate(prices):
        # Add some volume variation
        volume = 1000000.0 + (i * 50000)
        # Higher volume at zone touches
        if low <= 101 or high >= 110:
            volume *= 1.8
        
        candles.append(Candle(
            symbol="BTCUSD",
            timeframe="1h",
            timestamp=base_time + timedelta(hours=i),
            open=float(open_),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=volume,
        ))
    
    return candles


def main():
    """Run support/resistance zone detection example."""
    print("=" * 70)
    print("Support/Resistance Zone Detection Example")
    print("=" * 70)
    print()
    
    # Create sample data
    candles = create_sample_candles()
    print(f"📊 Loaded {len(candles)} candles")
    print(f"   Symbol: {candles[0].symbol}")
    print(f"   Timeframe: {candles[0].timeframe}")
    print(f"   Period: {candles[0].timestamp} to {candles[-1].timestamp}")
    print(f"   Current Price: ${candles[-1].close:.2f}")
    print()
    
    # Initialize detector
    detector = SupportResistanceDetector(
        min_touches=2,  # Minimum 2 touches to establish a zone
        zone_merge_threshold=0.005,  # Merge zones within 0.5%
        zone_width_pct=0.002,  # Zone width of 0.2%
        lookback_window=100,  # Analyze last 100 candles
        touch_proximity_pct=0.003,  # 0.3% to consider a touch
    )
    
    # Perform comprehensive analysis
    print("🔍 Detecting support and resistance zones...")
    analysis = detector.analyze_zones(candles)
    print()
    
    # Display results
    print("=" * 70)
    print("ZONE ANALYSIS RESULTS")
    print("=" * 70)
    print()
    
    # Summary
    print("📈 SUMMARY")
    print(f"   Total Zones: {analysis['total_zones']}")
    print(f"   Support Zones: {analysis['support_count']}")
    print(f"   Resistance Zones: {analysis['resistance_count']}")
    print(f"   Current Price: ${analysis['current_price']:.2f}")
    print()
    
    # Zone strength distribution
    dist = analysis['zone_strength_distribution']
    print("💪 ZONE STRENGTH DISTRIBUTION")
    print(f"   Weak: {dist['weak']}")
    print(f"   Moderate: {dist['moderate']}")
    print(f"   Strong: {dist['strong']}")
    print(f"   Major: {dist['major']}")
    print()
    
    # Support Zones
    if analysis["support_zones"]:
        print("🛡️  SUPPORT ZONES (Price Floors)")
        print("-" * 70)
        for zone in analysis["support_zones"][:5]:  # Show top 5
            print(f"   ${zone['bottom']:.2f} - ${zone['top']:.2f} (Midpoint: ${zone['midpoint']:.2f})")
            print(f"      Strength: {zone['strength'].upper()} (Score: {zone['strength_score']:.2f})")
            print(f"      Touches: {zone['touch_count']} | Bounces: {zone['bounce_count']} ({zone['bounce_rate']:.0%} success)")
            print(f"      Volume Profile: {zone['volume_profile']:.2f}x average")
            
            # Show recent touches
            if zone['touches']:
                recent_touches = zone['touches'][-3:]  # Last 3 touches
                print(f"      Recent Touches:")
                for touch in recent_touches:
                    status = "✅ Bounced" if touch['is_bounce'] else "❌ Broke"
                    print(f"         {touch['timestamp'][:19]}: ${touch['price']:.2f} {status}")
            print()
        if len(analysis["support_zones"]) > 5:
            print(f"   ... and {len(analysis['support_zones']) - 5} more support zones")
        print()
    
    # Resistance Zones
    if analysis["resistance_zones"]:
        print("🚧 RESISTANCE ZONES (Price Ceilings)")
        print("-" * 70)
        for zone in analysis["resistance_zones"][:5]:  # Show top 5
            print(f"   ${zone['bottom']:.2f} - ${zone['top']:.2f} (Midpoint: ${zone['midpoint']:.2f})")
            print(f"      Strength: {zone['strength'].upper()} (Score: {zone['strength_score']:.2f})")
            print(f"      Touches: {zone['touch_count']} | Bounces: {zone['bounce_count']} ({zone['bounce_rate']:.0%} success)")
            print(f"      Volume Profile: {zone['volume_profile']:.2f}x average")
            
            # Show recent touches
            if zone['touches']:
                recent_touches = zone['touches'][-3:]  # Last 3 touches
                print(f"      Recent Touches:")
                for touch in recent_touches:
                    status = "✅ Rejected" if touch['is_bounce'] else "❌ Broke"
                    print(f"         {touch['timestamp'][:19]}: ${touch['price']:.2f} {status}")
            print()
        if len(analysis["resistance_zones"]) > 5:
            print(f"   ... and {len(analysis['resistance_zones']) - 5} more resistance zones")
        print()
    
    # Nearest Zones
    print("🎯 NEAREST ZONES TO CURRENT PRICE")
    print("-" * 70)
    
    if analysis["nearest_support"]:
        print(f"   SUPPORT BELOW:")
        zone = analysis["nearest_support"]
        distance = analysis["nearest_support_distance"]
        distance_pct = (distance / analysis["current_price"]) * 100
        print(f"      ${zone['bottom']:.2f} - ${zone['top']:.2f}")
        print(f"      Distance: ${distance:.2f} ({distance_pct:.2f}% below)")
        print(f"      Strength: {zone['strength'].upper()} | Touches: {zone['touch_count']}")
        print()
    else:
        print("   No nearby support zones found")
        print()
    
    if analysis["nearest_resistance"]:
        print(f"   RESISTANCE ABOVE:")
        zone = analysis["nearest_resistance"]
        distance = analysis["nearest_resistance_distance"]
        distance_pct = (distance / analysis["current_price"]) * 100
        print(f"      ${zone['bottom']:.2f} - ${zone['top']:.2f}")
        print(f"      Distance: ${distance:.2f} ({distance_pct:.2f}% above)")
        print(f"      Strength: {zone['strength'].upper()} | Touches: {zone['touch_count']}")
        print()
    else:
        print("   No nearby resistance zones found")
        print()
    
    # Trading Insights
    print("=" * 70)
    print("💡 TRADING INSIGHTS")
    print("=" * 70)
    print()
    
    current_price = analysis["current_price"]
    
    if analysis["nearest_support"] and analysis["nearest_resistance"]:
        support = analysis["nearest_support"]
        resistance = analysis["nearest_resistance"]
        
        print("📍 CURRENT POSITION")
        print(f"   Price is trading between:")
        print(f"   • Support: ${support['midpoint']:.2f} ({support['strength']})")
        print(f"   • Resistance: ${resistance['midpoint']:.2f} ({resistance['strength']})")
        print()
        
        # Calculate position in range
        range_size = resistance['midpoint'] - support['midpoint']
        position_in_range = (current_price - support['midpoint']) / range_size
        
        print("🎪 TRADING STRATEGY")
        if position_in_range < 0.3:
            print("   ✅ NEAR SUPPORT - Potential LONG opportunity")
            print(f"      Entry: Around ${support['top']:.2f}")
            print(f"      Stop Loss: Below ${support['bottom']:.2f}")
            print(f"      Target: ${resistance['bottom']:.2f}")
        elif position_in_range > 0.7:
            print("   ⚠️  NEAR RESISTANCE - Potential SHORT opportunity or take profits")
            print(f"      Entry: Around ${resistance['bottom']:.2f}")
            print(f"      Stop Loss: Above ${resistance['top']:.2f}")
            print(f"      Target: ${support['top']:.2f}")
        else:
            print("   ⏸️  MID-RANGE - Wait for better position")
            print(f"      Wait for price to reach support (${support['midpoint']:.2f}) or resistance (${resistance['midpoint']:.2f})")
        print()
        
        # Risk/Reward
        long_rr = (resistance['midpoint'] - support['top']) / (support['top'] - support['bottom'])
        print("💰 RISK/REWARD ANALYSIS")
        print(f"   Long from support: {long_rr:.2f}:1 R/R")
        print()
    
    # Zone Quality Assessment
    if analysis["zones"]:
        strong_zones = [z for z in analysis["zones"] if z['strength'] in ['strong', 'major']]
        if strong_zones:
            print("⭐ HIGH-QUALITY ZONES")
            print(f"   {len(strong_zones)} strong/major zones identified")
            print("   These zones have:")
            print("   • Multiple successful bounces")
            print("   • High volume confirmation")
            print("   • Recent price action validation")
            print()
            
            print("   Recommended approach:")
            print("   1. Wait for price to approach these zones")
            print("   2. Look for confirmation (wick rejection, volume spike)")
            print("   3. Enter in the direction of the bounce")
            print("   4. Use zone boundaries for stop loss placement")
        
        weak_zones = [z for z in analysis["zones"] if z['strength'] == 'weak']
        if weak_zones:
            print()
            print("⚠️  WEAK ZONES")
            print(f"   {len(weak_zones)} weak zones detected")
            print("   • Use with caution - fewer confirmations")
            print("   • Wait for additional confluence")
            print("   • Tighter stops recommended")
    
    print()
    print("=" * 70)
    print("✅ Zone analysis complete!")
    print("=" * 70)
    print()
    print("💡 TIP: Combine zone analysis with market structure and candle patterns")
    print("    for highest-probability trade setups!")
    print()


if __name__ == "__main__":
    main()
