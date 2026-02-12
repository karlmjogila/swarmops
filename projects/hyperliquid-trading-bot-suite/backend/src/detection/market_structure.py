"""
Market Structure Analyzer

Implements comprehensive market structure analysis for identifying trends, support/resistance zones,
break of structure (BOS), change of character (CHOCH), and market cycle phases.
Core component of the pattern detection engine.

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Optional, Dict, Any, Tuple, NamedTuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import asdict, dataclass
from collections import defaultdict

from ..types import (
    CandleData, MarketStructure, Timeframe, OrderSide, MarketCycle,
    PatternCondition, PatternType
)


@dataclass
class StructurePoint:
    """Represents a significant structure point (swing high/low)."""
    timestamp: datetime
    price: float
    candle_index: int
    point_type: str  # 'high' or 'low'
    strength: float  # 0.0 to 1.0
    confirmed: bool = False
    broken: bool = False
    break_timestamp: Optional[datetime] = None


@dataclass  
class SupportResistanceZone:
    """Represents a support or resistance zone."""
    price_level: float
    zone_type: str  # 'support' or 'resistance'
    strength: float  # Based on number of touches and reactions
    first_touch: datetime
    last_touch: datetime
    touch_count: int
    zone_width: float  # Price range of the zone
    active: bool = True
    broken: bool = False


@dataclass
class TrendAnalysis:
    """Trend analysis results."""
    direction: Optional[OrderSide]
    strength: float  # 0.0 to 1.0
    duration_candles: int
    start_timestamp: datetime
    confidence: float
    slope: float  # Price change per candle
    momentum: float  # Recent momentum score


@dataclass
class BreakOfStructure:
    """Break of structure event."""
    timestamp: datetime
    price: float
    candle_index: int
    break_type: str  # 'bos_high' or 'bos_low'
    previous_structure: StructurePoint
    strength: float
    volume_confirmation: bool


@dataclass
class ChangeOfCharacter:
    """Change of character event."""
    timestamp: datetime
    price: float  
    candle_index: int
    from_trend: OrderSide
    to_trend: OrderSide
    trigger_break: BreakOfStructure
    confidence: float


class MarketStructureAnalyzer:
    """Advanced market structure analysis engine."""
    
    def __init__(self):
        """Initialize analyzer with default parameters."""
        
        # Structure detection parameters
        self.swing_detection_periods = 5  # Minimum periods for swing confirmation
        self.structure_confirmation_periods = 3  # Periods to confirm structure break
        self.min_structure_strength = 0.4  # Minimum strength for valid structure points
        
        # Zone detection parameters  
        self.zone_touch_threshold = 0.002  # 0.2% price tolerance for zone touches
        self.min_zone_touches = 2  # Minimum touches to create a zone
        self.zone_strength_decay = 0.95  # How much zone strength decays over time
        self.max_zone_age_hours = 168  # Max age for zones (1 week)
        
        # Trend analysis parameters
        self.trend_confirmation_periods = 10  # Periods needed to confirm trend
        self.trend_strength_lookback = 20  # Lookback for trend strength calculation
        self.momentum_periods = 5  # Periods for momentum calculation
        
        # Market cycle parameters
        self.drive_momentum_threshold = 0.7  # Momentum needed for drive phase
        self.range_volatility_threshold = 0.3  # Max volatility for range phase  
        self.liquidity_wick_ratio = 2.0  # Wick ratio indicating liquidity events
        
    def analyze_structure(
        self,
        candles: List[CandleData],
        asset: str,
        timeframe: Timeframe,
        min_periods: int = 50
    ) -> MarketStructure:
        """
        Perform comprehensive market structure analysis.
        
        Args:
            candles: List of candle data in chronological order
            asset: Trading asset symbol  
            timeframe: Timeframe being analyzed
            min_periods: Minimum number of candles required
            
        Returns:
            MarketStructure object with complete analysis
        """
        if len(candles) < min_periods:
            return self._empty_structure(asset, timeframe)
            
        # 1. Detect swing highs and lows
        structure_points = self._detect_structure_points(candles)
        
        # 2. Identify support and resistance zones
        sr_zones = self._identify_zones(candles, structure_points)
        
        # 3. Analyze current trend
        trend_analysis = self._analyze_trend(candles, structure_points)
        
        # 4. Detect break of structure events
        bos_events = self._detect_break_of_structure(candles, structure_points)
        
        # 5. Detect change of character events  
        choch_events = self._detect_change_of_character(candles, bos_events, trend_analysis)
        
        # 6. Determine current market cycle
        market_cycle = self._determine_market_cycle(candles, trend_analysis, bos_events)
        
        # 7. Calculate confluence scores
        confluence_data = self._calculate_confluence(candles, sr_zones, structure_points)
        
        # Build market structure result
        return MarketStructure(
            asset=asset,
            timeframe=timeframe,
            timestamp=candles[-1].timestamp if candles else datetime.utcnow(),
            
            # Structure points converted to dict format
            higher_highs=[asdict(p) for p in structure_points if p.point_type == 'high'],
            lower_lows=[asdict(p) for p in structure_points if p.point_type == 'low'],
            
            # Support/resistance zones
            support_zones=[asdict(z) for z in sr_zones if z.zone_type == 'support' and z.active],
            resistance_zones=[asdict(z) for z in sr_zones if z.zone_type == 'resistance' and z.active],
            
            # Trend information
            trend_direction=trend_analysis.direction,
            trend_strength=trend_analysis.strength,
            
            # Most recent structure breaks
            last_bos=asdict(bos_events[-1]) if bos_events else None,
            last_choch=asdict(choch_events[-1]) if choch_events else None,
        )
    
    def _detect_structure_points(self, candles: List[CandleData]) -> List[StructurePoint]:
        """Detect significant swing highs and lows."""
        structure_points = []
        
        for i in range(self.swing_detection_periods, len(candles) - self.swing_detection_periods):
            current = candles[i]
            
            # Check for swing high
            is_swing_high = True
            for j in range(i - self.swing_detection_periods, i + self.swing_detection_periods + 1):
                if j != i and candles[j].high >= current.high:
                    is_swing_high = False
                    break
                    
            if is_swing_high:
                strength = self._calculate_structure_strength(candles, i, 'high')
                if strength >= self.min_structure_strength:
                    structure_points.append(StructurePoint(
                        timestamp=current.timestamp,
                        price=current.high,
                        candle_index=i,
                        point_type='high',
                        strength=strength
                    ))
            
            # Check for swing low
            is_swing_low = True
            for j in range(i - self.swing_detection_periods, i + self.swing_detection_periods + 1):
                if j != i and candles[j].low <= current.low:
                    is_swing_low = False
                    break
                    
            if is_swing_low:
                strength = self._calculate_structure_strength(candles, i, 'low')
                if strength >= self.min_structure_strength:
                    structure_points.append(StructurePoint(
                        timestamp=current.timestamp,
                        price=current.low,
                        candle_index=i,
                        point_type='low',
                        strength=strength
                    ))
        
        # Sort by timestamp
        structure_points.sort(key=lambda x: x.timestamp)
        
        # Mark confirmed structure points
        self._confirm_structure_points(structure_points, candles)
        
        return structure_points
    
    def _calculate_structure_strength(self, candles: List[CandleData], index: int, point_type: str) -> float:
        """Calculate the strength of a structure point based on various factors."""
        if index < self.swing_detection_periods or index >= len(candles) - self.swing_detection_periods:
            return 0.0
            
        current = candles[index]
        strength_factors = []
        
        # Factor 1: Volume confirmation (higher volume = stronger)
        avg_volume = np.mean([c.volume for c in candles[max(0, index-10):index+11]])
        if avg_volume > 0:
            volume_factor = min(current.volume / avg_volume, 2.0) / 2.0
            strength_factors.append(volume_factor * 0.3)
        
        # Factor 2: Price deviation from nearby candles
        nearby_prices = []
        for i in range(max(0, index-self.swing_detection_periods), 
                      min(len(candles), index+self.swing_detection_periods+1)):
            if i != index:
                nearby_prices.append(candles[i].high if point_type == 'high' else candles[i].low)
        
        if nearby_prices:
            target_price = current.high if point_type == 'high' else current.low
            avg_nearby = np.mean(nearby_prices)
            if avg_nearby > 0:
                deviation_factor = abs(target_price - avg_nearby) / avg_nearby
                strength_factors.append(min(deviation_factor * 2, 1.0) * 0.4)
        
        # Factor 3: Wick size (longer rejection wicks = stronger structure)
        if point_type == 'high':
            wick_size = current.upper_wick
        else:
            wick_size = current.lower_wick
            
        if current.total_range > 0:
            wick_factor = min(wick_size / current.total_range, 0.8)
            strength_factors.append(wick_factor * 0.3)
        
        return min(sum(strength_factors), 1.0)
    
    def _confirm_structure_points(self, structure_points: List[StructurePoint], candles: List[CandleData]):
        """Mark structure points as confirmed based on subsequent price action."""
        for point in structure_points:
            # Check if structure held for confirmation periods
            start_index = point.candle_index + 1
            end_index = min(len(candles), start_index + self.structure_confirmation_periods)
            
            held = True
            for i in range(start_index, end_index):
                if point.point_type == 'high' and candles[i].high > point.price:
                    held = False
                    break
                elif point.point_type == 'low' and candles[i].low < point.price:
                    held = False
                    break
            
            point.confirmed = held
    
    def _identify_zones(self, candles: List[CandleData], structure_points: List[StructurePoint]) -> List[SupportResistanceZone]:
        """Identify support and resistance zones based on structure points and price reactions."""
        zones = []
        price_levels = defaultdict(list)
        
        # Group structure points by similar price levels
        for point in structure_points:
            # Find existing price level within tolerance
            found_level = None
            for level in price_levels.keys():
                if abs(point.price - level) / level <= self.zone_touch_threshold:
                    found_level = level
                    break
            
            if found_level:
                price_levels[found_level].append(point)
            else:
                price_levels[point.price] = [point]
        
        # Create zones from price levels with sufficient touches
        for level, points in price_levels.items():
            if len(points) >= self.min_zone_touches:
                # Determine zone type based on points
                high_points = [p for p in points if p.point_type == 'high']
                low_points = [p for p in points if p.point_type == 'low']
                
                zone_type = 'resistance' if len(high_points) >= len(low_points) else 'support'
                
                # Calculate zone properties
                prices = [p.price for p in points]
                zone_width = max(prices) - min(prices)
                
                # Calculate zone strength
                touch_strength = min(len(points) / 5.0, 1.0) * 0.4
                point_strength = np.mean([p.strength for p in points]) * 0.4
                time_factor = self._calculate_zone_time_factor(points) * 0.2
                zone_strength = touch_strength + point_strength + time_factor
                
                zones.append(SupportResistanceZone(
                    price_level=level,
                    zone_type=zone_type,
                    strength=min(zone_strength, 1.0),
                    first_touch=min(p.timestamp for p in points),
                    last_touch=max(p.timestamp for p in points),
                    touch_count=len(points),
                    zone_width=zone_width,
                    active=True
                ))
        
        # Update zone status based on recent price action
        self._update_zone_status(zones, candles)
        
        return zones
    
    def _calculate_zone_time_factor(self, points: List[StructurePoint]) -> float:
        """Calculate time-based factor for zone strength."""
        if len(points) < 2:
            return 0.5
            
        # Zones with longer duration get higher score
        duration = max(p.timestamp for p in points) - min(p.timestamp for p in points)
        duration_hours = duration.total_seconds() / 3600
        
        # Normalize to 0-1 scale (max benefit at 24 hours)
        return min(duration_hours / 24.0, 1.0)
    
    def _update_zone_status(self, zones: List[SupportResistanceZone], candles: List[CandleData]):
        """Update zone active/broken status based on recent price action."""
        current_time = candles[-1].timestamp if candles else datetime.utcnow()
        
        for zone in zones:
            # Check if zone is too old
            age_hours = (current_time - zone.last_touch).total_seconds() / 3600
            if age_hours > self.max_zone_age_hours:
                zone.active = False
                continue
                
            # Check if zone was broken by recent price action
            for candle in candles[-20:]:  # Check last 20 candles
                if zone.zone_type == 'resistance' and candle.close > zone.price_level + zone.zone_width:
                    zone.broken = True
                    zone.active = False
                    break
                elif zone.zone_type == 'support' and candle.close < zone.price_level - zone.zone_width:
                    zone.broken = True
                    zone.active = False
                    break
    
    def _analyze_trend(self, candles: List[CandleData], structure_points: List[StructurePoint]) -> TrendAnalysis:
        """Analyze overall trend direction and strength."""
        if len(candles) < self.trend_confirmation_periods:
            return TrendAnalysis(
                direction=None,
                strength=0.0,
                duration_candles=0,
                start_timestamp=candles[0].timestamp if candles else datetime.utcnow(),
                confidence=0.0,
                slope=0.0,
                momentum=0.0
            )
        
        # Get recent structure points for trend analysis
        recent_highs = [p for p in structure_points if p.point_type == 'high'][-5:]
        recent_lows = [p for p in structure_points if p.point_type == 'low'][-5:]
        
        # Calculate trend based on higher highs/lower lows
        trend_direction = None
        trend_strength = 0.0
        confidence = 0.0
        
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # Check for higher highs and higher lows (uptrend)
            higher_highs = all(recent_highs[i].price > recent_highs[i-1].price 
                             for i in range(1, len(recent_highs)))
            higher_lows = all(recent_lows[i].price > recent_lows[i-1].price 
                            for i in range(1, len(recent_lows)))
            
            # Check for lower highs and lower lows (downtrend)
            lower_highs = all(recent_highs[i].price < recent_highs[i-1].price 
                            for i in range(1, len(recent_highs)))
            lower_lows = all(recent_lows[i].price < recent_lows[i-1].price 
                           for i in range(1, len(recent_lows)))
            
            if higher_highs and higher_lows:
                trend_direction = OrderSide.LONG
                trend_strength = 0.8
                confidence = 0.9
            elif lower_highs and lower_lows:
                trend_direction = OrderSide.SHORT
                trend_strength = 0.8
                confidence = 0.9
            elif higher_highs or higher_lows:
                trend_direction = OrderSide.LONG
                trend_strength = 0.5
                confidence = 0.6
            elif lower_highs or lower_lows:
                trend_direction = OrderSide.SHORT
                trend_strength = 0.5
                confidence = 0.6
        
        # Calculate price slope over trend lookback period
        lookback_candles = candles[-self.trend_strength_lookback:]
        if len(lookback_candles) >= 2:
            price_changes = []
            for i in range(1, len(lookback_candles)):
                change = (lookback_candles[i].close - lookback_candles[i-1].close) / lookback_candles[i-1].close
                price_changes.append(change)
            slope = np.mean(price_changes) if price_changes else 0.0
        else:
            slope = 0.0
        
        # Calculate momentum
        momentum = self._calculate_momentum(candles)
        
        # Duration calculation (simplified)
        duration_candles = min(len(candles), self.trend_strength_lookback)
        start_timestamp = candles[max(0, len(candles) - duration_candles)].timestamp
        
        return TrendAnalysis(
            direction=trend_direction,
            strength=trend_strength,
            duration_candles=duration_candles,
            start_timestamp=start_timestamp,
            confidence=confidence,
            slope=slope,
            momentum=momentum
        )
    
    def _calculate_momentum(self, candles: List[CandleData]) -> float:
        """Calculate recent momentum score."""
        if len(candles) < self.momentum_periods:
            return 0.0
            
        recent_candles = candles[-self.momentum_periods:]
        
        # Calculate momentum as rate of price change
        start_price = recent_candles[0].close
        end_price = recent_candles[-1].close
        
        if start_price == 0:
            return 0.0
            
        momentum_raw = (end_price - start_price) / start_price
        
        # Normalize to -1 to 1 scale
        return max(-1.0, min(1.0, momentum_raw * 10))
    
    def _detect_break_of_structure(self, candles: List[CandleData], structure_points: List[StructurePoint]) -> List[BreakOfStructure]:
        """Detect break of structure events."""
        bos_events = []
        
        # Check each structure point for breaks
        for point in structure_points:
            if not point.confirmed:
                continue
                
            # Look for breaks after the structure point
            for i in range(point.candle_index + 1, len(candles)):
                candle = candles[i]
                
                # Check for break of high structure
                if point.point_type == 'high' and candle.close > point.price:
                    volume_confirmation = self._check_volume_confirmation(candles, i)
                    
                    bos_events.append(BreakOfStructure(
                        timestamp=candle.timestamp,
                        price=candle.close,
                        candle_index=i,
                        break_type='bos_high',
                        previous_structure=point,
                        strength=point.strength,
                        volume_confirmation=volume_confirmation
                    ))
                    
                    # Mark structure as broken
                    point.broken = True
                    point.break_timestamp = candle.timestamp
                    break
                
                # Check for break of low structure  
                elif point.point_type == 'low' and candle.close < point.price:
                    volume_confirmation = self._check_volume_confirmation(candles, i)
                    
                    bos_events.append(BreakOfStructure(
                        timestamp=candle.timestamp,
                        price=candle.close,
                        candle_index=i,
                        break_type='bos_low',
                        previous_structure=point,
                        strength=point.strength,
                        volume_confirmation=volume_confirmation
                    ))
                    
                    # Mark structure as broken
                    point.broken = True
                    point.break_timestamp = candle.timestamp
                    break
        
        return bos_events
    
    def _check_volume_confirmation(self, candles: List[CandleData], index: int) -> bool:
        """Check if break is confirmed by above-average volume."""
        if index < 10:
            return False
            
        current_volume = candles[index].volume
        avg_volume = np.mean([c.volume for c in candles[max(0, index-10):index]])
        
        return current_volume > avg_volume * 1.2  # 20% above average
    
    def _detect_change_of_character(self, candles: List[CandleData], bos_events: List[BreakOfStructure], trend_analysis: TrendAnalysis) -> List[ChangeOfCharacter]:
        """Detect change of character events (trend reversals)."""
        choch_events = []
        
        if not trend_analysis.direction:
            return choch_events
        
        current_trend = trend_analysis.direction
        
        # Look for BOS events that indicate trend change
        for bos in bos_events:
            potential_choch = False
            new_trend = None
            
            # Uptrend breaking lower structure = potential downtrend
            if current_trend == OrderSide.LONG and bos.break_type == 'bos_low':
                potential_choch = True
                new_trend = OrderSide.SHORT
            
            # Downtrend breaking higher structure = potential uptrend
            elif current_trend == OrderSide.SHORT and bos.break_type == 'bos_high':
                potential_choch = True
                new_trend = OrderSide.LONG
            
            if potential_choch and new_trend:
                # Calculate confidence based on various factors
                confidence = self._calculate_choch_confidence(bos, trend_analysis)
                
                choch_events.append(ChangeOfCharacter(
                    timestamp=bos.timestamp,
                    price=bos.price,
                    candle_index=bos.candle_index,
                    from_trend=current_trend,
                    to_trend=new_trend,
                    trigger_break=bos,
                    confidence=confidence
                ))
                
                # Update current trend for subsequent analysis
                current_trend = new_trend
        
        return choch_events
    
    def _calculate_choch_confidence(self, bos: BreakOfStructure, trend_analysis: TrendAnalysis) -> float:
        """Calculate confidence score for change of character event."""
        confidence_factors = []
        
        # Factor 1: Structure strength
        confidence_factors.append(bos.strength * 0.3)
        
        # Factor 2: Volume confirmation
        if bos.volume_confirmation:
            confidence_factors.append(0.3)
        
        # Factor 3: Previous trend strength (stronger trends have stronger reversals)
        confidence_factors.append(trend_analysis.strength * 0.2)
        
        # Factor 4: Momentum divergence
        if abs(trend_analysis.momentum) < 0.3:  # Weak momentum suggests trend exhaustion
            confidence_factors.append(0.2)
        
        return min(sum(confidence_factors), 1.0)
    
    def _determine_market_cycle(self, candles: List[CandleData], trend_analysis: TrendAnalysis, bos_events: List[BreakOfStructure]) -> MarketCycle:
        """Determine current market cycle phase."""
        if len(candles) < 20:
            return MarketCycle.RANGE
        
        recent_candles = candles[-20:]
        
        # Calculate volatility and momentum
        price_changes = []
        for i in range(1, len(recent_candles)):
            change = abs(recent_candles[i].close - recent_candles[i-1].close) / recent_candles[i-1].close
            price_changes.append(change)
        
        avg_volatility = np.mean(price_changes) if price_changes else 0.0
        momentum = abs(trend_analysis.momentum)
        
        # Count recent liquidity events (large wicks)
        liquidity_events = 0
        for candle in recent_candles[-10:]:
            if candle.total_range > 0:
                upper_wick_ratio = candle.upper_wick / candle.total_range
                lower_wick_ratio = candle.lower_wick / candle.total_range
                
                if max(upper_wick_ratio, lower_wick_ratio) > 0.5:  # Large wick indicates liquidity grab
                    liquidity_events += 1
        
        # Determine cycle based on conditions
        if momentum > self.drive_momentum_threshold and trend_analysis.strength > 0.6:
            return MarketCycle.DRIVE
        elif avg_volatility < self.range_volatility_threshold and momentum < 0.4:
            return MarketCycle.RANGE
        elif liquidity_events >= 3:  # Multiple liquidity events
            return MarketCycle.LIQUIDITY
        else:
            return MarketCycle.RANGE  # Default to range
    
    def _calculate_confluence(self, candles: List[CandleData], zones: List[SupportResistanceZone], structure_points: List[StructurePoint]) -> Dict[str, Any]:
        """Calculate confluence scores for various price levels."""
        if not candles:
            return {}
        
        current_price = candles[-1].close
        confluence_data = {}
        
        # Find nearby zones and structure points
        price_tolerance = current_price * 0.01  # 1% tolerance
        
        nearby_zones = [z for z in zones if abs(z.price_level - current_price) <= price_tolerance and z.active]
        nearby_structure = [p for p in structure_points if abs(p.price - current_price) <= price_tolerance and not p.broken]
        
        # Calculate confluence score
        confluence_score = 0.0
        
        # Zone confluence
        for zone in nearby_zones:
            confluence_score += zone.strength * 0.3
        
        # Structure confluence  
        for point in nearby_structure:
            confluence_score += point.strength * 0.2
        
        confluence_data['current_confluence'] = min(confluence_score, 1.0)
        confluence_data['nearby_zones'] = len(nearby_zones)
        confluence_data['nearby_structure'] = len(nearby_structure)
        
        return confluence_data
    
    def _empty_structure(self, asset: str, timeframe: Timeframe) -> MarketStructure:
        """Return empty market structure for insufficient data."""
        return MarketStructure(
            asset=asset,
            timeframe=timeframe,
            timestamp=datetime.utcnow(),
            higher_highs=[],
            lower_lows=[],
            support_zones=[],
            resistance_zones=[],
            trend_direction=None,
            trend_strength=0.0,
            last_bos=None,
            last_choch=None
        )
    
    def get_current_bias(self, structure: MarketStructure) -> Optional[OrderSide]:
        """Get current market bias based on structure analysis."""
        return structure.trend_direction
    
    def get_key_levels(self, structure: MarketStructure, current_price: float, tolerance: float = 0.02) -> Dict[str, List[float]]:
        """Get key support and resistance levels near current price."""
        key_levels = {
            'support': [],
            'resistance': [],
            'structure_highs': [],
            'structure_lows': []
        }
        
        price_range = current_price * tolerance
        
        # Get nearby support levels
        for zone in structure.support_zones:
            zone_price = zone.get('price_level', 0)
            if abs(zone_price - current_price) <= price_range:
                key_levels['support'].append(zone_price)
        
        # Get nearby resistance levels  
        for zone in structure.resistance_zones:
            zone_price = zone.get('price_level', 0)
            if abs(zone_price - current_price) <= price_range:
                key_levels['resistance'].append(zone_price)
        
        # Get nearby structure highs
        for high in structure.higher_highs:
            high_price = high.get('price', 0)
            if abs(high_price - current_price) <= price_range:
                key_levels['structure_highs'].append(high_price)
        
        # Get nearby structure lows
        for low in structure.lower_lows:
            low_price = low.get('price', 0)
            if abs(low_price - current_price) <= price_range:
                key_levels['structure_lows'].append(low_price)
        
        # Sort levels
        for key in key_levels:
            key_levels[key].sort()
        
        return key_levels
    
    def check_structure_break(self, structure: MarketStructure, current_price: float, direction: OrderSide) -> Tuple[bool, float]:
        """
        Check if current price breaks significant structure in given direction.
        
        Returns:
            (is_break, strength) - strength is 0.0 to 1.0
        """
        if direction == OrderSide.LONG:
            # Check for break above resistance
            relevant_levels = []
            
            for zone in structure.resistance_zones:
                zone_price = zone.get('price_level', 0)
                if current_price > zone_price:
                    relevant_levels.append((zone_price, zone.get('strength', 0)))
            
            for high in structure.higher_highs:
                high_price = high.get('price', 0)
                if current_price > high_price:
                    relevant_levels.append((high_price, high.get('strength', 0)))
        
        else:  # SHORT
            # Check for break below support
            relevant_levels = []
            
            for zone in structure.support_zones:
                zone_price = zone.get('price_level', 0)
                if current_price < zone_price:
                    relevant_levels.append((zone_price, zone.get('strength', 0)))
            
            for low in structure.lower_lows:
                low_price = low.get('price', 0)
                if current_price < low_price:
                    relevant_levels.append((low_price, low.get('strength', 0)))
        
        if relevant_levels:
            # Find the strongest broken level
            max_strength = max(strength for _, strength in relevant_levels)
            return True, max_strength
        
        return False, 0.0


# Export main class and key types
__all__ = [
    "MarketStructureAnalyzer",
    "StructurePoint", 
    "SupportResistanceZone",
    "TrendAnalysis",
    "BreakOfStructure",
    "ChangeOfCharacter"
]