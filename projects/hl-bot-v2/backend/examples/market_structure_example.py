#!/usr/bin/env python3
"""Example usage of the Market Structure Analyzer.

Demonstrates how to:
1. Load candle data
2. Analyze market structure (swings, BOS, CHoCH, order blocks, FVGs)
3. Interpret the results for trading decisions
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from datetime import datetime, timedelta
from app.core.market.data import Candle
from app.core.patterns import MarketStructureAnalyzer


def create_sample_candles() -> list[Candle]:
    """Create sample candle data for demonstration.
    
    Simulates a bullish trend with:
    - Clear swing points
    - A break of structure
    - An order block
    - A fair value gap
    """
    base_time = datetime(2024, 1, 1, 0, 0)
    candles = []
    
    # Create uptrend with swing points
    prices = [
        (100, 102, 99, 101),   # Bullish
        (101, 103, 100, 102),  # Bullish
        (102, 104, 101, 103),  # Bullish
        (103, 102, 100, 101),  # Bearish - Swing High at 104
        (101, 103, 100, 102),  # Bullish
        (102, 105, 101, 104),  # Bullish - Swing Low at 100
        (104, 106, 103, 105),  # Bullish
        (105, 104, 102, 103),  # Bearish - Order Block
        (103, 109, 103, 108),  # Strong bullish move - FVG created
        (108, 110, 107, 109),  # Bullish continuation
        (109, 112, 108, 111),  # Bullish - BOS (breaking swing high)
        (111, 113, 110, 112),  # Bullish
        (112, 111, 109, 110),  # Bearish
        (110, 112, 109, 111),  # Bullish
        (111, 114, 110, 113),  # Bullish
    ]
    
    for i, (open_, high, low, close) in enumerate(prices):
        candles.append(Candle(
            symbol="BTCUSD",
            timeframe="1h",
            timestamp=base_time + timedelta(hours=i),
            open=float(open_),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=1000000.0 + (i * 50000),
        ))
    
    return candles


def main():
    """Run market structure analysis example."""
    print("=" * 70)
    print("Market Structure Analysis Example")
    print("=" * 70)
    print()
    
    # Create sample data
    candles = create_sample_candles()
    print(f"📊 Loaded {len(candles)} candles")
    print(f"   Symbol: {candles[0].symbol}")
    print(f"   Timeframe: {candles[0].timeframe}")
    print(f"   Period: {candles[0].timestamp} to {candles[-1].timestamp}")
    print()
    
    # Initialize analyzer
    analyzer = MarketStructureAnalyzer(
        lookback=2,  # Look 2 candles back/forward for swings
        min_swing_body_pct=0.3
    )
    
    # Perform comprehensive analysis
    print("🔍 Analyzing market structure...")
    analysis = analyzer.analyze_structure(candles)
    print()
    
    # Display results
    print("=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)
    print()
    
    # Summary
    summary = analysis["summary"]
    print("📈 SUMMARY")
    print(f"   Current Trend: {analysis['current_trend'].upper()}")
    print(f"   Total Swings: {summary['total_swings']} ({summary['swing_highs']} highs, {summary['swing_lows']} lows)")
    print(f"   Structure Breaks: {summary['bos_count']} BOS, {summary['choch_count']} CHoCH")
    print(f"   Order Blocks: {summary['order_blocks_count']} ({summary['bullish_order_blocks']} bullish, {summary['bearish_order_blocks']} bearish)")
    print(f"   Fair Value Gaps: {summary['fvgs_count']} ({summary['unfilled_fvgs']} unfilled)")
    print()
    
    # Swing Points
    if analysis["swings"]:
        print("🎯 SWING POINTS")
        for swing in analysis["swings"][:5]:  # Show first 5
            print(f"   {swing['type'].upper()}: ${swing['price']:.2f} @ {swing['timestamp']}")
        if len(analysis["swings"]) > 5:
            print(f"   ... and {len(analysis['swings']) - 5} more")
        print()
    
    # Structure Breaks
    if analysis["breaks"]:
        print("💥 STRUCTURE BREAKS")
        for brk in analysis["breaks"][:5]:
            print(f"   {brk['type'].upper()}: ${brk['break_price']:.2f} @ {brk['timestamp']}")
            print(f"      Broke: ${brk['broken_swing_price']:.2f}, Significance: {brk['significance']:.2f}")
        if len(analysis["breaks"]) > 5:
            print(f"   ... and {len(analysis['breaks']) - 5} more")
        print()
    
    # Order Blocks
    if analysis["order_blocks"]:
        print("📦 ORDER BLOCKS")
        for ob in analysis["order_blocks"]:
            direction = "BULLISH (Support)" if ob["is_bullish"] else "BEARISH (Resistance)"
            print(f"   {direction}: ${ob['bottom']:.2f} - ${ob['top']:.2f}")
            print(f"      Midpoint: ${ob['midpoint']:.2f}, Strength: {ob['strength']:.2f}, Tested: {ob['tested']}x")
        print()
    
    # Fair Value Gaps
    if analysis["fvgs"]:
        print("⚡ FAIR VALUE GAPS")
        for fvg in analysis["fvgs"]:
            direction = "BULLISH" if fvg["is_bullish"] else "BEARISH"
            status = f"FILLED ({fvg['fill_percentage']:.0%})" if fvg["filled"] else f"UNFILLED ({fvg['fill_percentage']:.0%})"
            print(f"   {direction}: ${fvg['bottom']:.2f} - ${fvg['top']:.2f} ({status})")
            print(f"      Gap Size: ${fvg['gap_size']:.2f}, Midpoint: ${fvg['midpoint']:.2f}")
        print()
    
    # Trading Insights
    print("=" * 70)
    print("💡 TRADING INSIGHTS")
    print("=" * 70)
    print()
    
    if analysis["current_trend"] == "bullish":
        print("✅ BULLISH TREND DETECTED")
        print("   → Look for long opportunities on pullbacks")
        if analysis["order_blocks"]:
            bullish_obs = [ob for ob in analysis["order_blocks"] if ob["is_bullish"]]
            if bullish_obs:
                best_ob = max(bullish_obs, key=lambda x: x["strength"])
                print(f"   → Strong support at ${best_ob['bottom']:.2f} - ${best_ob['top']:.2f}")
        if analysis["fvgs"]:
            unfilled_bullish = [fvg for fvg in analysis["fvgs"] if fvg["is_bullish"] and not fvg["filled"]]
            if unfilled_bullish:
                print(f"   → Watch for price to fill {len(unfilled_bullish)} bullish FVG(s)")
    
    elif analysis["current_trend"] == "bearish":
        print("❌ BEARISH TREND DETECTED")
        print("   → Look for short opportunities on rallies")
        if analysis["order_blocks"]:
            bearish_obs = [ob for ob in analysis["order_blocks"] if not ob["is_bullish"]]
            if bearish_obs:
                best_ob = max(bearish_obs, key=lambda x: x["strength"])
                print(f"   → Strong resistance at ${best_ob['bottom']:.2f} - ${best_ob['top']:.2f}")
    
    else:
        print("⚠️  NEUTRAL / RANGING MARKET")
        print("   → Wait for clear structure before entering")
        print("   → Watch for CHoCH signals indicating potential trend change")
    
    print()
    print("=" * 70)
    print("✅ Analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
