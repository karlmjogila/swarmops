"""Market structure analysis module.

Identifies key market structure elements for trading:
- Swing highs and lows
- Break of Structure (BOS)
- Change of Character (CHoCH)
- Order blocks
- Fair Value Gaps (FVGs)

Based on smart money concepts and institutional order flow analysis.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

from app.core.market.data import Candle


class SwingType(Enum):
    """Type of swing point."""
    HIGH = "high"
    LOW = "low"


class StructureBreakType(Enum):
    """Type of structure break."""
    BOS = "bos"  # Break of Structure - continuation
    CHOCH = "choch"  # Change of Character - potential reversal


@dataclass
class SwingPoint:
    """Represents a swing high or low in the market.
    
    A swing point is a local extremum (peak or trough) that represents
    a significant turning point in price action.
    """
    candle: Candle
    swing_type: SwingType
    price: float  # The high or low price of the swing
    strength: int  # Number of candles confirming this swing
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.candle.timestamp.isoformat(),
            "type": self.swing_type.value,
            "price": self.price,
            "strength": self.strength,
            "symbol": self.candle.symbol,
            "timeframe": self.candle.timeframe,
        }


@dataclass
class StructureBreak:
    """Represents a break or change in market structure.
    
    BOS: Price breaks through a previous swing point in the direction of trend (continuation)
    CHoCH: Price breaks counter-trend swing point (potential reversal signal)
    """
    candle: Candle
    break_type: StructureBreakType
    broken_swing: SwingPoint
    break_price: float
    significance: float  # 0-1 score based on how clean the break was
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.candle.timestamp.isoformat(),
            "type": self.break_type.value,
            "break_price": self.break_price,
            "broken_swing_price": self.broken_swing.price,
            "significance": self.significance,
            "symbol": self.candle.symbol,
            "timeframe": self.candle.timeframe,
        }


@dataclass
class OrderBlock:
    """Represents an institutional order block.
    
    An order block is the last bearish/bullish candle before a significant move
    in the opposite direction. These zones often act as support/resistance where
    institutional orders may be resting.
    """
    candle: Candle
    is_bullish: bool  # Bullish order block (support) or bearish (resistance)
    top: float
    bottom: float
    volume: float
    strength: float  # 0-1 score based on volume and subsequent move
    tested: int  # Number of times price has revisited this zone
    
    @property
    def price_range(self) -> float:
        """Calculate the price range of the order block."""
        return self.top - self.bottom
    
    @property
    def midpoint(self) -> float:
        """Calculate the midpoint price of the order block."""
        return (self.top + self.bottom) / 2
    
    def contains_price(self, price: float) -> bool:
        """Check if a price is within this order block."""
        return self.bottom <= price <= self.top
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.candle.timestamp.isoformat(),
            "is_bullish": self.is_bullish,
            "top": self.top,
            "bottom": self.bottom,
            "midpoint": self.midpoint,
            "volume": self.volume,
            "strength": self.strength,
            "tested": self.tested,
            "symbol": self.candle.symbol,
            "timeframe": self.candle.timeframe,
        }


@dataclass
class FairValueGap:
    """Represents a Fair Value Gap (FVG) or imbalance.
    
    An FVG occurs when there's a gap between the high of candle[i-1] and 
    low of candle[i+1] (bearish) or between low of candle[i-1] and high 
    of candle[i+1] (bullish). These gaps often get filled as price returns.
    """
    start_candle: Candle
    middle_candle: Candle
    end_candle: Candle
    is_bullish: bool  # Bullish FVG (gap up) or bearish (gap down)
    top: float
    bottom: float
    filled: bool = False
    fill_percentage: float = 0.0
    
    @property
    def gap_size(self) -> float:
        """Calculate the size of the gap."""
        return self.top - self.bottom
    
    @property
    def midpoint(self) -> float:
        """Calculate the midpoint of the gap."""
        return (self.top + self.bottom) / 2
    
    def update_fill_status(self, current_price: float) -> None:
        """Update how much of the gap has been filled.
        
        Args:
            current_price: Current market price
        """
        if self.is_bullish:
            # Bullish FVG fills when price comes back down
            if current_price <= self.bottom:
                self.filled = True
                self.fill_percentage = 1.0
            elif current_price < self.top:
                self.fill_percentage = (self.top - current_price) / self.gap_size
        else:
            # Bearish FVG fills when price comes back up
            if current_price >= self.top:
                self.filled = True
                self.fill_percentage = 1.0
            elif current_price > self.bottom:
                self.fill_percentage = (current_price - self.bottom) / self.gap_size
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "start_timestamp": self.start_candle.timestamp.isoformat(),
            "middle_timestamp": self.middle_candle.timestamp.isoformat(),
            "end_timestamp": self.end_candle.timestamp.isoformat(),
            "is_bullish": self.is_bullish,
            "top": self.top,
            "bottom": self.bottom,
            "gap_size": self.gap_size,
            "midpoint": self.midpoint,
            "filled": self.filled,
            "fill_percentage": self.fill_percentage,
            "symbol": self.middle_candle.symbol,
            "timeframe": self.middle_candle.timeframe,
        }


class MarketStructureAnalyzer:
    """Analyzes market structure from OHLCV data.
    
    Provides methods to identify swing points, structure breaks, order blocks,
    and fair value gaps from a series of candles.
    
    Example:
        >>> analyzer = MarketStructureAnalyzer(lookback=5)
        >>> swings = analyzer.find_swing_points(candles)
        >>> breaks = analyzer.detect_structure_breaks(candles, swings)
        >>> order_blocks = analyzer.identify_order_blocks(candles)
        >>> fvgs = analyzer.detect_fair_value_gaps(candles)
    """
    
    def __init__(self, lookback: int = 5, min_swing_body_pct: float = 0.3):
        """Initialize the market structure analyzer.
        
        Args:
            lookback: Number of candles to look back for swing confirmation
            min_swing_body_pct: Minimum body size as % of range for valid swing
        """
        self.lookback = lookback
        self.min_swing_body_pct = min_swing_body_pct
    
    def find_swing_points(self, candles: List[Candle]) -> List[SwingPoint]:
        """Identify swing highs and lows in the candle series.
        
        A swing high is a candle whose high is greater than the highs of
        'lookback' candles before and after it. Similarly for swing lows.
        
        Args:
            candles: List of candles to analyze
            
        Returns:
            List of identified swing points
        """
        if len(candles) < (2 * self.lookback + 1):
            return []
        
        swings = []
        
        for i in range(self.lookback, len(candles) - self.lookback):
            candle = candles[i]
            
            # Check for swing high
            is_swing_high = True
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and candles[j].high >= candle.high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                # Verify candle has sufficient body (not just a wick spike)
                body_pct = candle.body_size / candle.total_range if candle.total_range > 0 else 0
                if body_pct >= self.min_swing_body_pct or candle.is_doji:
                    swings.append(SwingPoint(
                        candle=candle,
                        swing_type=SwingType.HIGH,
                        price=candle.high,
                        strength=self.lookback,
                    ))
                    continue
            
            # Check for swing low
            is_swing_low = True
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and candles[j].low <= candle.low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                # Verify candle has sufficient body
                body_pct = candle.body_size / candle.total_range if candle.total_range > 0 else 0
                if body_pct >= self.min_swing_body_pct or candle.is_doji:
                    swings.append(SwingPoint(
                        candle=candle,
                        swing_type=SwingType.LOW,
                        price=candle.low,
                        strength=self.lookback,
                    ))
        
        return swings
    
    def detect_structure_breaks(
        self, 
        candles: List[Candle], 
        swings: List[SwingPoint]
    ) -> List[StructureBreak]:
        """Detect breaks of structure (BOS) and changes of character (CHoCH).
        
        BOS: Price breaks a swing point in the direction of the trend
        CHoCH: Price breaks a swing point counter to the trend
        
        Args:
            candles: List of candles to analyze
            swings: Previously identified swing points
            
        Returns:
            List of structure breaks
        """
        if len(swings) < 3:
            return []
        
        breaks = []
        
        # Determine initial trend from first few swings
        recent_highs = [s for s in swings[:5] if s.swing_type == SwingType.HIGH]
        recent_lows = [s for s in swings[:5] if s.swing_type == SwingType.LOW]
        
        if not recent_highs or not recent_lows:
            return []
        
        # Track trend: bullish if making higher highs/lows, bearish if lower highs/lows
        is_bullish_trend = recent_highs[-1].price > recent_highs[0].price
        
        # Find candles that break swing levels
        for candle in candles:
            for swing in swings:
                # Skip if candle is before the swing
                if candle.timestamp <= swing.candle.timestamp:
                    continue
                
                # Check for breaks
                if swing.swing_type == SwingType.HIGH:
                    # Price broke above a swing high
                    if candle.close > swing.price:
                        # Determine if BOS or CHoCH
                        if is_bullish_trend:
                            # Breaking resistance in uptrend = BOS (continuation)
                            break_type = StructureBreakType.BOS
                        else:
                            # Breaking resistance in downtrend = CHoCH (potential reversal)
                            break_type = StructureBreakType.CHOCH
                            is_bullish_trend = True  # Trend may be changing
                        
                        # Calculate significance based on clean break
                        distance_above = candle.close - swing.price
                        significance = min(distance_above / swing.price, 0.02) / 0.02  # Cap at 2%
                        
                        breaks.append(StructureBreak(
                            candle=candle,
                            break_type=break_type,
                            broken_swing=swing,
                            break_price=candle.close,
                            significance=significance,
                        ))
                
                elif swing.swing_type == SwingType.LOW:
                    # Price broke below a swing low
                    if candle.close < swing.price:
                        # Determine if BOS or CHoCH
                        if not is_bullish_trend:
                            # Breaking support in downtrend = BOS (continuation)
                            break_type = StructureBreakType.BOS
                        else:
                            # Breaking support in uptrend = CHoCH (potential reversal)
                            break_type = StructureBreakType.CHOCH
                            is_bullish_trend = False  # Trend may be changing
                        
                        # Calculate significance
                        distance_below = swing.price - candle.close
                        significance = min(distance_below / swing.price, 0.02) / 0.02
                        
                        breaks.append(StructureBreak(
                            candle=candle,
                            break_type=break_type,
                            broken_swing=swing,
                            break_price=candle.close,
                            significance=significance,
                        ))
        
        return breaks
    
    def identify_order_blocks(
        self, 
        candles: List[Candle],
        min_volume_percentile: float = 0.6,
        min_move_size: float = 0.01  # 1% minimum move
    ) -> List[OrderBlock]:
        """Identify institutional order blocks.
        
        Order blocks are the last opposite-colored candle before a strong move.
        These represent areas where institutions placed orders.
        
        Args:
            candles: List of candles to analyze
            min_volume_percentile: Minimum volume percentile for order block candle
            min_move_size: Minimum move size (as fraction) to qualify as order block
            
        Returns:
            List of identified order blocks
        """
        if len(candles) < 10:
            return []
        
        # Calculate volume threshold
        volumes = [c.volume for c in candles]
        volumes.sort()
        volume_threshold = volumes[int(len(volumes) * min_volume_percentile)]
        
        order_blocks = []
        
        for i in range(1, len(candles) - 5):
            current = candles[i]
            
            # Skip low volume candles
            if current.volume < volume_threshold:
                continue
            
            # Look ahead for strong move
            next_5 = candles[i+1:i+6]
            
            if current.is_bearish:
                # Bearish order block: last red candle before bullish move
                bullish_move = sum(1 for c in next_5 if c.is_bullish) >= 4
                if bullish_move:
                    # Calculate move size
                    move_start = current.close
                    move_end = max(c.high for c in next_5)
                    move_size = (move_end - move_start) / move_start
                    
                    if move_size >= min_move_size:
                        # This is a bullish order block (support zone)
                        strength = min(move_size / 0.05, 1.0)  # Normalize to 0-1
                        
                        order_blocks.append(OrderBlock(
                            candle=current,
                            is_bullish=True,
                            top=current.high,
                            bottom=current.low,
                            volume=current.volume,
                            strength=strength,
                            tested=0,
                        ))
            
            elif current.is_bullish:
                # Bullish order block: last green candle before bearish move
                bearish_move = sum(1 for c in next_5 if c.is_bearish) >= 4
                if bearish_move:
                    # Calculate move size
                    move_start = current.close
                    move_end = min(c.low for c in next_5)
                    move_size = (move_start - move_end) / move_start
                    
                    if move_size >= min_move_size:
                        # This is a bearish order block (resistance zone)
                        strength = min(move_size / 0.05, 1.0)
                        
                        order_blocks.append(OrderBlock(
                            candle=current,
                            is_bullish=False,
                            top=current.high,
                            bottom=current.low,
                            volume=current.volume,
                            strength=strength,
                            tested=0,
                        ))
        
        # Track how many times each order block has been tested
        for ob in order_blocks:
            ob.tested = sum(
                1 for c in candles 
                if c.timestamp > ob.candle.timestamp and ob.contains_price(c.close)
            )
        
        return order_blocks
    
    def detect_fair_value_gaps(
        self, 
        candles: List[Candle],
        min_gap_size: float = 0.002  # 0.2% minimum gap
    ) -> List[FairValueGap]:
        """Detect Fair Value Gaps (FVGs) or imbalances.
        
        An FVG occurs when there's a gap in price action showing strong momentum.
        These gaps often act as magnets for price to return and "fill the gap".
        
        Args:
            candles: List of candles to analyze
            min_gap_size: Minimum gap size as fraction of price
            
        Returns:
            List of identified fair value gaps
        """
        if len(candles) < 3:
            return []
        
        fvgs = []
        
        for i in range(1, len(candles) - 1):
            prev = candles[i - 1]
            curr = candles[i]
            next_ = candles[i + 1]
            
            # Bullish FVG: gap between prev low and next high
            # (price jumped up, leaving an imbalance)
            if next_.low > prev.high:
                gap_size = next_.low - prev.high
                gap_size_pct = gap_size / curr.close
                
                if gap_size_pct >= min_gap_size:
                    fvgs.append(FairValueGap(
                        start_candle=prev,
                        middle_candle=curr,
                        end_candle=next_,
                        is_bullish=True,
                        top=next_.low,
                        bottom=prev.high,
                    ))
            
            # Bearish FVG: gap between prev high and next low
            # (price dropped sharply, leaving an imbalance)
            elif next_.high < prev.low:
                gap_size = prev.low - next_.high
                gap_size_pct = gap_size / curr.close
                
                if gap_size_pct >= min_gap_size:
                    fvgs.append(FairValueGap(
                        start_candle=prev,
                        middle_candle=curr,
                        end_candle=next_,
                        is_bullish=False,
                        top=prev.low,
                        bottom=next_.high,
                    ))
        
        # Update fill status for all FVGs based on most recent price
        if candles and fvgs:
            latest_price = candles[-1].close
            for fvg in fvgs:
                fvg.update_fill_status(latest_price)
        
        return fvgs
    
    def analyze_structure(self, candles: List[Candle]) -> dict:
        """Perform comprehensive market structure analysis.
        
        Combines all structure analysis methods into one call.
        
        Args:
            candles: List of candles to analyze
            
        Returns:
            Dictionary with all structure elements:
                - swings: List of swing points
                - breaks: List of structure breaks
                - order_blocks: List of order blocks
                - fvgs: List of fair value gaps
                - current_trend: "bullish", "bearish", or "neutral"
        """
        swings = self.find_swing_points(candles)
        breaks = self.detect_structure_breaks(candles, swings)
        order_blocks = self.identify_order_blocks(candles)
        fvgs = self.detect_fair_value_gaps(candles)
        
        # Determine current trend from recent breaks
        recent_breaks = breaks[-5:] if len(breaks) >= 5 else breaks
        if recent_breaks:
            bos_count = sum(1 for b in recent_breaks if b.break_type == StructureBreakType.BOS)
            choch_count = sum(1 for b in recent_breaks if b.break_type == StructureBreakType.CHOCH)
            
            if bos_count > choch_count:
                # More BOS = trend continuation
                last_bos = next((b for b in reversed(recent_breaks) if b.break_type == StructureBreakType.BOS), None)
                if last_bos:
                    current_trend = "bullish" if last_bos.broken_swing.swing_type == SwingType.HIGH else "bearish"
                else:
                    current_trend = "neutral"
            else:
                # More CHoCH = potential reversal/ranging
                current_trend = "neutral"
        else:
            # Fallback to swing analysis
            recent_highs = [s for s in swings[-5:] if s.swing_type == SwingType.HIGH]
            recent_lows = [s for s in swings[-5:] if s.swing_type == SwingType.LOW]
            
            if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                higher_highs = recent_highs[-1].price > recent_highs[0].price
                higher_lows = recent_lows[-1].price > recent_lows[0].price
                
                if higher_highs and higher_lows:
                    current_trend = "bullish"
                elif not higher_highs and not higher_lows:
                    current_trend = "bearish"
                else:
                    current_trend = "neutral"
            else:
                current_trend = "neutral"
        
        return {
            "swings": [s.to_dict() for s in swings],
            "breaks": [b.to_dict() for b in breaks],
            "order_blocks": [ob.to_dict() for ob in order_blocks],
            "fvgs": [fvg.to_dict() for fvg in fvgs],
            "current_trend": current_trend,
            "summary": {
                "total_swings": len(swings),
                "swing_highs": sum(1 for s in swings if s.swing_type == SwingType.HIGH),
                "swing_lows": sum(1 for s in swings if s.swing_type == SwingType.LOW),
                "bos_count": sum(1 for b in breaks if b.break_type == StructureBreakType.BOS),
                "choch_count": sum(1 for b in breaks if b.break_type == StructureBreakType.CHOCH),
                "order_blocks_count": len(order_blocks),
                "bullish_order_blocks": sum(1 for ob in order_blocks if ob.is_bullish),
                "bearish_order_blocks": sum(1 for ob in order_blocks if not ob.is_bullish),
                "fvgs_count": len(fvgs),
                "unfilled_fvgs": sum(1 for fvg in fvgs if not fvg.filled),
            }
        }
