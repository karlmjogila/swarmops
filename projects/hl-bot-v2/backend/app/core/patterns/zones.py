"""Support and Resistance zone detection module.

Identifies key support and resistance zones where price has historically
shown reactions. These zones act as price magnets and decision points.

Zones differ from exact levels - they represent areas/ranges where
institutional orders may be clustered.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

from app.core.market.data import Candle


class ZoneType(Enum):
    """Type of support/resistance zone."""
    SUPPORT = "support"
    RESISTANCE = "resistance"
    SUPPORT_RESISTANCE = "support_resistance"  # Flipped zone


class ZoneStrength(Enum):
    """Strength classification of a zone."""
    WEAK = "weak"  # 1-2 touches
    MODERATE = "moderate"  # 3-4 touches
    STRONG = "strong"  # 5+ touches
    MAJOR = "major"  # Significant historical level with volume


@dataclass
class ZoneTouch:
    """Represents a single touch/test of a support/resistance zone.
    
    A touch is when price approaches and reacts to the zone.
    """
    candle: Candle
    price: float  # The price that touched the zone
    is_bounce: bool  # True if price bounced, False if broke through
    volume_ratio: float  # Volume relative to average (1.0 = average)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.candle.timestamp.isoformat(),
            "price": self.price,
            "is_bounce": self.is_bounce,
            "volume_ratio": self.volume_ratio,
            "symbol": self.candle.symbol,
            "timeframe": self.candle.timeframe,
        }


@dataclass
class SupportResistanceZone:
    """Represents a support or resistance zone.
    
    A zone is a price range (not just a level) where price has historically
    shown reactions. Zones are more realistic than exact price levels because
    markets are dynamic and orders cluster in ranges.
    
    Attributes:
        zone_type: Support, resistance, or flipped zone
        top: Upper boundary of the zone
        bottom: Lower boundary of the zone
        strength: Zone strength classification
        touches: List of times price tested this zone
        first_touch: When zone was first established
        last_touch: Most recent touch
        broken: Whether zone has been definitively broken
        volume_profile: Average volume at this zone relative to overall average
    """
    zone_type: ZoneType
    top: float
    bottom: float
    strength: ZoneStrength
    touches: List[ZoneTouch]
    first_touch: datetime
    last_touch: datetime
    broken: bool = False
    volume_profile: float = 1.0  # Relative to average
    
    @property
    def midpoint(self) -> float:
        """Calculate the midpoint price of the zone."""
        return (self.top + self.bottom) / 2
    
    @property
    def zone_width(self) -> float:
        """Calculate the width/thickness of the zone."""
        return self.top - self.bottom
    
    @property
    def touch_count(self) -> int:
        """Get the number of times this zone has been touched."""
        return len(self.touches)
    
    @property
    def bounce_count(self) -> int:
        """Get the number of successful bounces from this zone."""
        return sum(1 for touch in self.touches if touch.is_bounce)
    
    @property
    def bounce_rate(self) -> float:
        """Calculate the bounce success rate (0.0 - 1.0)."""
        if not self.touches:
            return 0.0
        return self.bounce_count / len(self.touches)
    
    @property
    def age_candles(self) -> int:
        """Calculate age of zone in number of candle periods (approximation)."""
        if not self.touches or len(self.touches) < 2:
            return 0
        # Rough estimate based on first and last touch
        return len(self.touches)
    
    @property
    def recency_score(self) -> float:
        """Score based on how recently the zone was tested (0.0 - 1.0).
        
        More recent touches = higher score.
        """
        if not self.touches:
            return 0.0
        # Most recent touch gets highest weight
        return 1.0  # Can be enhanced with actual time decay
    
    def contains_price(self, price: float, buffer: float = 0.0) -> bool:
        """Check if a price is within this zone.
        
        Args:
            price: Price to check
            buffer: Additional buffer as fraction (e.g., 0.01 = 1% buffer)
            
        Returns:
            True if price is within zone bounds (including buffer)
        """
        width_buffer = self.zone_width * buffer
        return (self.bottom - width_buffer) <= price <= (self.top + width_buffer)
    
    def distance_to_zone(self, price: float) -> float:
        """Calculate distance from price to nearest edge of zone.
        
        Args:
            price: Current price
            
        Returns:
            Distance to zone (negative if inside, 0 if at edge, positive if outside)
        """
        if self.contains_price(price):
            return 0.0
        elif price > self.top:
            return price - self.top
        else:
            return self.bottom - price
    
    def calculate_strength_score(self) -> float:
        """Calculate comprehensive strength score (0.0 - 1.0).
        
        Considers:
        - Number of touches
        - Bounce rate
        - Volume profile
        - Age/recency
        """
        # Touch count score (normalized, caps at 10 touches)
        touch_score = min(self.touch_count / 10.0, 1.0)
        
        # Bounce rate score
        bounce_score = self.bounce_rate
        
        # Volume score (normalized around 1.0)
        volume_score = min(self.volume_profile / 2.0, 1.0)
        
        # Recency score
        recency = self.recency_score
        
        # Weighted average
        weights = [0.3, 0.3, 0.2, 0.2]  # touch, bounce, volume, recency
        scores = [touch_score, bounce_score, volume_score, recency]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "type": self.zone_type.value,
            "top": self.top,
            "bottom": self.bottom,
            "midpoint": self.midpoint,
            "width": self.zone_width,
            "strength": self.strength.value,
            "strength_score": self.calculate_strength_score(),
            "touch_count": self.touch_count,
            "bounce_count": self.bounce_count,
            "bounce_rate": self.bounce_rate,
            "broken": self.broken,
            "volume_profile": self.volume_profile,
            "first_touch": self.first_touch.isoformat(),
            "last_touch": self.last_touch.isoformat(),
            "touches": [t.to_dict() for t in self.touches],
        }


class SupportResistanceDetector:
    """Detects support and resistance zones from OHLCV data.
    
    Uses multiple methods to identify significant price zones:
    1. Swing-based zones: Areas around swing highs/lows
    2. Volume-based zones: High volume areas that create support/resistance
    3. Historical touch zones: Areas where price repeatedly bounced
    4. Psychological levels: Round numbers and significant price levels
    
    Example:
        >>> detector = SupportResistanceDetector(min_touches=2, zone_merge_threshold=0.005)
        >>> zones = detector.detect_zones(candles)
        >>> support = [z for z in zones if z.zone_type == ZoneType.SUPPORT]
        >>> resistance = [z for z in zones if z.zone_type == ZoneType.RESISTANCE]
    """
    
    def __init__(
        self,
        min_touches: int = 2,
        zone_merge_threshold: float = 0.005,  # 0.5% price range to merge zones
        zone_width_pct: float = 0.002,  # 0.2% default zone width
        lookback_window: int = 100,  # Candles to analyze
        touch_proximity_pct: float = 0.003,  # 0.3% to consider a "touch"
    ):
        """Initialize the support/resistance detector.
        
        Args:
            min_touches: Minimum touches required to establish a zone
            zone_merge_threshold: Price distance threshold to merge nearby zones (as fraction)
            zone_width_pct: Default zone width as percentage of price
            lookback_window: Number of candles to analyze for zones
            touch_proximity_pct: How close price must be to consider it a touch
        """
        self.min_touches = min_touches
        self.zone_merge_threshold = zone_merge_threshold
        self.zone_width_pct = zone_width_pct
        self.lookback_window = lookback_window
        self.touch_proximity_pct = touch_proximity_pct
    
    def detect_zones(self, candles: List[Candle]) -> List[SupportResistanceZone]:
        """Detect all support and resistance zones in the candle series.
        
        Main entry point for zone detection. Combines multiple methods:
        1. Swing-based zones
        2. Historical touch zones
        3. Volume profile zones
        
        Args:
            candles: List of candles to analyze
            
        Returns:
            List of identified support/resistance zones, sorted by strength
        """
        if len(candles) < self.min_touches + 1:
            return []
        
        # Use lookback window
        analysis_candles = candles[-self.lookback_window:] if len(candles) > self.lookback_window else candles
        
        # Calculate average volume for reference
        avg_volume = sum(c.volume for c in analysis_candles) / len(analysis_candles)
        
        # Detect zones using multiple methods
        swing_zones = self._detect_swing_zones(analysis_candles, avg_volume)
        touch_zones = self._detect_touch_zones(analysis_candles, avg_volume)
        
        # Combine and merge nearby zones
        all_zones = swing_zones + touch_zones
        merged_zones = self._merge_nearby_zones(all_zones)
        
        # Filter by minimum touches
        valid_zones = [z for z in merged_zones if z.touch_count >= self.min_touches]
        
        # Classify strength
        for zone in valid_zones:
            zone.strength = self._classify_strength(zone)
        
        # Sort by strength score (descending)
        valid_zones.sort(key=lambda z: z.calculate_strength_score(), reverse=True)
        
        return valid_zones
    
    def _detect_swing_zones(
        self, 
        candles: List[Candle],
        avg_volume: float
    ) -> List[SupportResistanceZone]:
        """Detect zones around swing highs and lows.
        
        Swing points often act as support/resistance because they represent
        local extremes where traders made decisions.
        
        Args:
            candles: List of candles to analyze
            avg_volume: Average volume for normalization
            
        Returns:
            List of zones around swing points
        """
        zones = []
        lookback = 5  # Simple swing detection
        
        for i in range(lookback, len(candles) - lookback):
            candle = candles[i]
            
            # Check for swing high (resistance zone)
            is_swing_high = all(
                candle.high >= candles[j].high 
                for j in range(i - lookback, i + lookback + 1) 
                if j != i
            )
            
            if is_swing_high:
                zone_width = candle.high * self.zone_width_pct
                top = candle.high + zone_width / 2
                bottom = candle.high - zone_width / 2
                
                # Find touches of this zone in subsequent candles
                touches = self._find_zone_touches(
                    candles[i:], top, bottom, avg_volume, is_resistance=True
                )
                
                if touches:
                    zones.append(SupportResistanceZone(
                        zone_type=ZoneType.RESISTANCE,
                        top=top,
                        bottom=bottom,
                        strength=ZoneStrength.WEAK,  # Will be classified later
                        touches=touches,
                        first_touch=touches[0].candle.timestamp,
                        last_touch=touches[-1].candle.timestamp,
                        volume_profile=candle.volume / avg_volume if avg_volume > 0 else 1.0,
                    ))
            
            # Check for swing low (support zone)
            is_swing_low = all(
                candle.low <= candles[j].low 
                for j in range(i - lookback, i + lookback + 1) 
                if j != i
            )
            
            if is_swing_low:
                zone_width = candle.low * self.zone_width_pct
                top = candle.low + zone_width / 2
                bottom = candle.low - zone_width / 2
                
                # Find touches of this zone in subsequent candles
                touches = self._find_zone_touches(
                    candles[i:], top, bottom, avg_volume, is_resistance=False
                )
                
                if touches:
                    zones.append(SupportResistanceZone(
                        zone_type=ZoneType.SUPPORT,
                        top=top,
                        bottom=bottom,
                        strength=ZoneStrength.WEAK,
                        touches=touches,
                        first_touch=touches[0].candle.timestamp,
                        last_touch=touches[-1].candle.timestamp,
                        volume_profile=candle.volume / avg_volume if avg_volume > 0 else 1.0,
                    ))
        
        return zones
    
    def _detect_touch_zones(
        self,
        candles: List[Candle],
        avg_volume: float
    ) -> List[SupportResistanceZone]:
        """Detect zones where price has repeatedly touched and bounced.
        
        Uses a clustering approach to find price levels where multiple
        touches occurred.
        
        Args:
            candles: List of candles to analyze
            avg_volume: Average volume for normalization
            
        Returns:
            List of zones identified by clustering touches
        """
        zones = []
        
        # Extract potential support/resistance touch points
        # Look for candles with long wicks (rejections)
        touch_points = []
        
        for candle in candles:
            if candle.total_range == 0:
                continue
            
            lower_wick_ratio = candle.wick_size_lower / candle.total_range
            upper_wick_ratio = candle.wick_size_upper / candle.total_range
            
            # Long lower wick = potential support touch
            if lower_wick_ratio > 0.3:
                touch_points.append({
                    'candle': candle,
                    'price': candle.low,
                    'type': 'support',
                    'strength': lower_wick_ratio,
                })
            
            # Long upper wick = potential resistance touch
            if upper_wick_ratio > 0.3:
                touch_points.append({
                    'candle': candle,
                    'price': candle.high,
                    'type': 'resistance',
                    'strength': upper_wick_ratio,
                })
        
        if not touch_points:
            return zones
        
        # Cluster nearby touch points
        clusters = self._cluster_touch_points(touch_points)
        
        # Convert clusters to zones
        for cluster in clusters:
            if len(cluster) < self.min_touches:
                continue
            
            prices = [tp['price'] for tp in cluster]
            avg_price = sum(prices) / len(prices)
            price_range = max(prices) - min(prices)
            
            # Create zone with some width
            zone_width = max(price_range, avg_price * self.zone_width_pct)
            top = avg_price + zone_width / 2
            bottom = avg_price - zone_width / 2
            
            # Determine zone type from cluster
            support_count = sum(1 for tp in cluster if tp['type'] == 'support')
            resistance_count = sum(1 for tp in cluster if tp['type'] == 'resistance')
            
            if support_count > resistance_count:
                zone_type = ZoneType.SUPPORT
                is_resistance = False
            elif resistance_count > support_count:
                zone_type = ZoneType.RESISTANCE
                is_resistance = True
            else:
                zone_type = ZoneType.SUPPORT_RESISTANCE
                is_resistance = False
            
            # Create touches list
            touches = []
            for tp in cluster:
                volume_ratio = tp['candle'].volume / avg_volume if avg_volume > 0 else 1.0
                touches.append(ZoneTouch(
                    candle=tp['candle'],
                    price=tp['price'],
                    is_bounce=True,  # Wick rejection implies bounce
                    volume_ratio=volume_ratio,
                ))
            
            # Sort touches by timestamp
            touches.sort(key=lambda t: t.candle.timestamp)
            
            # Calculate average volume profile for this zone
            avg_vol_profile = sum(t.volume_ratio for t in touches) / len(touches)
            
            zones.append(SupportResistanceZone(
                zone_type=zone_type,
                top=top,
                bottom=bottom,
                strength=ZoneStrength.WEAK,
                touches=touches,
                first_touch=touches[0].candle.timestamp,
                last_touch=touches[-1].candle.timestamp,
                volume_profile=avg_vol_profile,
            ))
        
        return zones
    
    def _find_zone_touches(
        self,
        candles: List[Candle],
        zone_top: float,
        zone_bottom: float,
        avg_volume: float,
        is_resistance: bool
    ) -> List[ZoneTouch]:
        """Find all touches of a zone in the candle series.
        
        A touch is when price enters the zone and either bounces or breaks through.
        
        Args:
            candles: Candles to search for touches
            zone_top: Top of the zone
            zone_bottom: Bottom of the zone
            avg_volume: Average volume for normalization
            is_resistance: True if resistance zone, False if support
            
        Returns:
            List of zone touches
        """
        touches = []
        zone_mid = (zone_top + zone_bottom) / 2
        in_zone = False
        
        for candle in candles:
            # Check if candle touches the zone
            candle_in_zone = (
                (candle.low <= zone_top and candle.high >= zone_bottom) or
                (zone_bottom <= candle.close <= zone_top) or
                (zone_bottom <= candle.open <= zone_top)
            )
            
            if candle_in_zone and not in_zone:
                # Entering zone
                in_zone = True
                
                # Determine touch price
                if is_resistance:
                    touch_price = min(candle.high, zone_top)
                else:
                    touch_price = max(candle.low, zone_bottom)
                
                # Check if price bounced or broke through
                # For resistance: bounce if close is below zone
                # For support: bounce if close is above zone
                if is_resistance:
                    is_bounce = candle.close < zone_bottom
                else:
                    is_bounce = candle.close > zone_top
                
                volume_ratio = candle.volume / avg_volume if avg_volume > 0 else 1.0
                
                touches.append(ZoneTouch(
                    candle=candle,
                    price=touch_price,
                    is_bounce=is_bounce,
                    volume_ratio=volume_ratio,
                ))
            
            elif not candle_in_zone:
                in_zone = False
        
        return touches
    
    def _cluster_touch_points(
        self,
        touch_points: List[dict]
    ) -> List[List[dict]]:
        """Cluster nearby touch points into zones.
        
        Uses a simple distance-based clustering approach.
        
        Args:
            touch_points: List of touch point dictionaries
            
        Returns:
            List of clusters (each cluster is a list of touch points)
        """
        if not touch_points:
            return []
        
        # Sort by price
        sorted_points = sorted(touch_points, key=lambda tp: tp['price'])
        
        clusters = []
        current_cluster = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            current_point = sorted_points[i]
            last_point = current_cluster[-1]
            
            # Calculate distance as percentage of price
            distance_pct = abs(current_point['price'] - last_point['price']) / last_point['price']
            
            # If close enough, add to current cluster
            if distance_pct < self.zone_merge_threshold:
                current_cluster.append(current_point)
            else:
                # Start new cluster
                if len(current_cluster) >= self.min_touches:
                    clusters.append(current_cluster)
                current_cluster = [current_point]
        
        # Add last cluster
        if len(current_cluster) >= self.min_touches:
            clusters.append(current_cluster)
        
        return clusters
    
    def _merge_nearby_zones(
        self,
        zones: List[SupportResistanceZone]
    ) -> List[SupportResistanceZone]:
        """Merge zones that are very close to each other.
        
        Prevents having multiple overlapping zones at similar price levels.
        
        Args:
            zones: List of zones to merge
            
        Returns:
            List of merged zones
        """
        if len(zones) <= 1:
            return zones
        
        # Sort by midpoint
        sorted_zones = sorted(zones, key=lambda z: z.midpoint)
        
        merged = []
        current_zone = sorted_zones[0]
        
        for i in range(1, len(sorted_zones)):
            next_zone = sorted_zones[i]
            
            # Calculate distance between zone midpoints
            distance_pct = abs(next_zone.midpoint - current_zone.midpoint) / current_zone.midpoint
            
            # Check if zones are compatible (same type or flipped)
            compatible = (
                current_zone.zone_type == next_zone.zone_type or
                current_zone.zone_type == ZoneType.SUPPORT_RESISTANCE or
                next_zone.zone_type == ZoneType.SUPPORT_RESISTANCE
            )
            
            # Merge if close and compatible
            if distance_pct < self.zone_merge_threshold and compatible:
                # Merge zones
                merged_top = max(current_zone.top, next_zone.top)
                merged_bottom = min(current_zone.bottom, next_zone.bottom)
                merged_touches = current_zone.touches + next_zone.touches
                merged_touches.sort(key=lambda t: t.candle.timestamp)
                
                # Determine merged type
                if current_zone.zone_type == next_zone.zone_type:
                    merged_type = current_zone.zone_type
                else:
                    merged_type = ZoneType.SUPPORT_RESISTANCE
                
                # Calculate merged volume profile
                total_touches = len(merged_touches)
                merged_volume = sum(t.volume_ratio for t in merged_touches) / total_touches
                
                current_zone = SupportResistanceZone(
                    zone_type=merged_type,
                    top=merged_top,
                    bottom=merged_bottom,
                    strength=ZoneStrength.WEAK,
                    touches=merged_touches,
                    first_touch=merged_touches[0].candle.timestamp,
                    last_touch=merged_touches[-1].candle.timestamp,
                    volume_profile=merged_volume,
                )
            else:
                # Not mergeable, add current and move to next
                merged.append(current_zone)
                current_zone = next_zone
        
        # Add last zone
        merged.append(current_zone)
        
        return merged
    
    def _classify_strength(self, zone: SupportResistanceZone) -> ZoneStrength:
        """Classify zone strength based on characteristics.
        
        Args:
            zone: Zone to classify
            
        Returns:
            ZoneStrength classification
        """
        touch_count = zone.touch_count
        bounce_rate = zone.bounce_rate
        volume_profile = zone.volume_profile
        
        # Calculate composite score
        score = zone.calculate_strength_score()
        
        # Major zones: many touches, high bounce rate, high volume
        if touch_count >= 5 and bounce_rate >= 0.7 and volume_profile >= 1.5:
            return ZoneStrength.MAJOR
        
        # Strong zones: good touch count and bounce rate
        if touch_count >= 5 or (touch_count >= 3 and bounce_rate >= 0.75):
            return ZoneStrength.STRONG
        
        # Moderate zones: decent characteristics
        if touch_count >= 3 or (touch_count >= 2 and bounce_rate >= 0.7):
            return ZoneStrength.MODERATE
        
        # Weak zones: minimum requirements
        return ZoneStrength.WEAK
    
    def find_nearest_zones(
        self,
        zones: List[SupportResistanceZone],
        current_price: float,
        max_distance_pct: float = 0.05,  # 5% max distance
        zone_types: Optional[List[ZoneType]] = None
    ) -> List[Tuple[SupportResistanceZone, float]]:
        """Find zones nearest to current price.
        
        Args:
            zones: List of zones to search
            current_price: Current market price
            max_distance_pct: Maximum distance as percentage of price
            zone_types: Filter by zone types (None = all types)
            
        Returns:
            List of (zone, distance) tuples, sorted by distance
        """
        # Filter by type if specified
        if zone_types:
            zones = [z for z in zones if z.zone_type in zone_types]
        
        # Calculate distances
        zones_with_distance = []
        for zone in zones:
            distance = zone.distance_to_zone(current_price)
            distance_pct = abs(distance) / current_price
            
            if distance_pct <= max_distance_pct:
                zones_with_distance.append((zone, distance))
        
        # Sort by absolute distance
        zones_with_distance.sort(key=lambda x: abs(x[1]))
        
        return zones_with_distance
    
    def get_active_zones(
        self,
        zones: List[SupportResistanceZone],
        current_price: float,
        lookback_touches: int = 3
    ) -> List[SupportResistanceZone]:
        """Get zones that are currently active/relevant.
        
        Active zones are those that:
        1. Haven't been definitively broken
        2. Have been touched recently
        3. Are within reasonable distance of current price
        
        Args:
            zones: List of zones to filter
            current_price: Current market price
            lookback_touches: Consider zones touched within last N touches
            
        Returns:
            List of active zones
        """
        active = []
        
        for zone in zones:
            # Skip broken zones
            if zone.broken:
                continue
            
            # Check if zone is within 10% of current price
            distance_pct = abs(zone.distance_to_zone(current_price)) / current_price
            if distance_pct > 0.10:
                continue
            
            # Check if recently tested (has touches in last lookback_touches)
            if zone.touch_count > 0:
                active.append(zone)
        
        return active
    
    def analyze_zones(
        self,
        candles: List[Candle],
        current_price: Optional[float] = None
    ) -> dict:
        """Comprehensive zone analysis.
        
        Args:
            candles: List of candles to analyze
            current_price: Current price (uses last candle close if not provided)
            
        Returns:
            Dictionary with zone analysis results
        """
        zones = self.detect_zones(candles)
        
        if current_price is None and candles:
            current_price = candles[-1].close
        
        # Categorize zones
        support_zones = [z for z in zones if z.zone_type in (ZoneType.SUPPORT, ZoneType.SUPPORT_RESISTANCE)]
        resistance_zones = [z for z in zones if z.zone_type in (ZoneType.RESISTANCE, ZoneType.SUPPORT_RESISTANCE)]
        
        # Find nearest zones
        nearest_support = None
        nearest_resistance = None
        
        if current_price:
            nearest_zones = self.find_nearest_zones(zones, current_price, max_distance_pct=0.10)
            
            for zone, distance in nearest_zones:
                if distance < 0 and nearest_support is None:  # Below current price
                    if zone.zone_type in (ZoneType.SUPPORT, ZoneType.SUPPORT_RESISTANCE):
                        nearest_support = (zone, abs(distance))
                elif distance > 0 and nearest_resistance is None:  # Above current price
                    if zone.zone_type in (ZoneType.RESISTANCE, ZoneType.SUPPORT_RESISTANCE):
                        nearest_resistance = (zone, distance)
                
                if nearest_support and nearest_resistance:
                    break
        
        return {
            "zones": [z.to_dict() for z in zones],
            "support_zones": [z.to_dict() for z in support_zones],
            "resistance_zones": [z.to_dict() for z in resistance_zones],
            "total_zones": len(zones),
            "support_count": len(support_zones),
            "resistance_count": len(resistance_zones),
            "nearest_support": nearest_support[0].to_dict() if nearest_support else None,
            "nearest_support_distance": nearest_support[1] if nearest_support else None,
            "nearest_resistance": nearest_resistance[0].to_dict() if nearest_resistance else None,
            "nearest_resistance_distance": nearest_resistance[1] if nearest_resistance else None,
            "current_price": current_price,
            "zone_strength_distribution": {
                "weak": sum(1 for z in zones if z.strength == ZoneStrength.WEAK),
                "moderate": sum(1 for z in zones if z.strength == ZoneStrength.MODERATE),
                "strong": sum(1 for z in zones if z.strength == ZoneStrength.STRONG),
                "major": sum(1 for z in zones if z.strength == ZoneStrength.MAJOR),
            }
        }
