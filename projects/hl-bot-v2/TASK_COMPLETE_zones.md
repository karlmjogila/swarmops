# Task Complete: Support/Resistance Zone Detection

**Task ID:** zones  
**Status:** ✅ COMPLETE  
**Completed:** 2025-02-11

---

## Summary

Implemented comprehensive support and resistance zone detection for the hl-bot-v2 trading system. The implementation identifies key price zones where institutional orders cluster, providing more realistic support/resistance areas than exact price levels.

## Implementation Details

### Location
- **Module:** `/backend/app/core/patterns/zones.py`
- **Exports:** `/backend/app/core/patterns/__init__.py`
- **Tests:** `/backend/tests/core/patterns/test_zones.py` (14 tests, all passing)

### Features Implemented

#### 1. **Zone Detection Methods**

**Swing-Based Zones:**
- Identifies zones around swing highs (resistance) and lows (support)
- Configurable zone width as percentage of price
- Tracks all touches and reactions to each zone

**Touch-Based Zones:**
- Detects zones where price repeatedly bounced via wick rejections
- Clusters nearby touch points into coherent zones
- Uses long wick ratios (>30%) as rejection signals

**Zone Merging:**
- Automatically merges overlapping or nearby zones
- Configurable merge threshold (default 0.5%)
- Prevents duplicate zones at similar price levels

#### 2. **Zone Characteristics**

**Zone Types:**
- `SUPPORT`: Price bounces upward from zone
- `RESISTANCE`: Price bounces downward from zone
- `SUPPORT_RESISTANCE`: Flipped zone (support becomes resistance or vice versa)

**Zone Strength:**
- `WEAK`: 1-2 touches
- `MODERATE`: 3-4 touches
- `STRONG`: 5+ touches
- `MAJOR`: Significant historical level with high volume

**Touch Tracking:**
- Records every time price tests a zone
- Tracks bounce vs breakout outcomes
- Volume analysis for each touch
- Calculates bounce rate (success rate)

#### 3. **Zone Analysis Methods**

**Key Metrics:**
- **Touch Count**: Number of times zone was tested
- **Bounce Rate**: Percentage of touches that resulted in bounce (0-1)
- **Volume Profile**: Average volume relative to market average
- **Zone Width**: Thickness of the zone in price terms
- **Strength Score**: Composite score (0-1) based on multiple factors

**Filtering & Search:**
- `find_nearest_zones()`: Find zones closest to current price
- `get_active_zones()`: Filter zones that are currently relevant
- `analyze_zones()`: Comprehensive analysis with categorization

#### 4. **Smart Features**

**Zone Validation:**
- Minimum touch requirements (default: 2)
- Distance-based clustering for similar price levels
- Volume-weighted strength calculation
- Recency scoring for recently tested zones

**Price Queries:**
- `contains_price()`: Check if price is within zone (with buffer)
- `distance_to_zone()`: Calculate distance to nearest edge
- `calculate_strength_score()`: Multi-factor strength evaluation

### Data Structures

```python
@dataclass
class ZoneTouch:
    """Single test of a zone."""
    candle: Candle
    price: float
    is_bounce: bool  # True if bounced, False if broke through
    volume_ratio: float

@dataclass
class SupportResistanceZone:
    """A support or resistance zone."""
    zone_type: ZoneType
    top: float
    bottom: float
    strength: ZoneStrength
    touches: List[ZoneTouch]
    first_touch: datetime
    last_touch: datetime
    broken: bool
    volume_profile: float
    
    @property
    def midpoint(self) -> float
    @property
    def zone_width(self) -> float
    @property
    def touch_count(self) -> int
    @property
    def bounce_count(self) -> int
    @property
    def bounce_rate(self) -> float
    
    def contains_price(price, buffer=0.0) -> bool
    def distance_to_zone(price) -> float
    def calculate_strength_score() -> float
```

### SupportResistanceDetector API

```python
detector = SupportResistanceDetector(
    min_touches=2,              # Minimum touches to establish zone
    zone_merge_threshold=0.005, # 0.5% price range to merge zones
    zone_width_pct=0.002,       # 0.2% default zone width
    lookback_window=100,        # Candles to analyze
    touch_proximity_pct=0.003   # 0.3% to consider a touch
)

# Detect all zones
zones = detector.detect_zones(candles)

# Comprehensive analysis
analysis = detector.analyze_zones(candles, current_price=110.0)
# Returns:
# - zones: All detected zones
# - support_zones: Support zones only
# - resistance_zones: Resistance zones only
# - nearest_support/resistance: Closest zones to current price
# - zone_strength_distribution: Breakdown by strength

# Find nearest zones
nearest = detector.find_nearest_zones(
    zones, 
    current_price=110.0,
    max_distance_pct=0.05,  # Within 5%
    zone_types=[ZoneType.SUPPORT]  # Optional filter
)

# Get currently active zones
active = detector.get_active_zones(
    zones,
    current_price=110.0,
    lookback_touches=3
)
```

### Configuration Examples

**Day Trading (Tight Zones):**
```python
detector = SupportResistanceDetector(
    min_touches=2,
    zone_width_pct=0.001,      # Tighter zones (0.1%)
    lookback_window=50,         # Shorter history
    touch_proximity_pct=0.002   # Closer touches
)
```

**Swing Trading (Major Zones):**
```python
detector = SupportResistanceDetector(
    min_touches=3,              # More confirmation
    zone_width_pct=0.005,       # Wider zones (0.5%)
    lookback_window=200,        # Longer history
    touch_proximity_pct=0.005   # More lenient
)
```

## Testing

### Test Coverage
Created comprehensive test suite with 14 tests covering:
- Zone detection (swing-based and touch-based)
- Zone properties and calculations
- Strength classification
- Touch tracking and bounce rate
- Nearest zone finding
- Zone merging logic
- Serialization/deserialization
- Edge cases (empty data, insufficient candles)

### Run Tests
```bash
cd backend
PYTHONPATH=/opt/swarmops/projects/hl-bot-v2/backend \
  poetry run pytest tests/core/patterns/test_zones.py -v
```

**Result:** ✅ 14/14 tests passing

## Usage Examples

### Basic Usage
```python
from app.core.patterns import SupportResistanceDetector, ZoneType

# Initialize detector
detector = SupportResistanceDetector(min_touches=2)

# Detect zones from historical data
zones = detector.detect_zones(candles)

# Filter by type
support = [z for z in zones if z.zone_type == ZoneType.SUPPORT]
resistance = [z for z in zones if z.zone_type == ZoneType.RESISTANCE]

print(f"Found {len(support)} support zones")
print(f"Found {len(resistance)} resistance zones")
```

### Find Trading Opportunities
```python
# Get comprehensive analysis
current_price = candles[-1].close
analysis = detector.analyze_zones(candles, current_price)

# Check nearest support
if analysis['nearest_support']:
    zone = analysis['nearest_support']
    distance = analysis['nearest_support_distance']
    
    print(f"Nearest support at {zone['midpoint']}")
    print(f"Distance: {distance:.2f} ({distance/current_price*100:.2f}%)")
    print(f"Strength: {zone['strength']}")
    print(f"Bounce rate: {zone['bounce_rate']*100:.1f}%")
    
    # Strong support nearby = potential buy zone
    if zone['strength'] in ['strong', 'major'] and distance < current_price * 0.02:
        print("⚠️ Approaching strong support - watch for bounces!")
```

### Zone Quality Filtering
```python
# Get only high-quality zones
zones = detector.detect_zones(candles)
quality_zones = [
    z for z in zones 
    if z.calculate_strength_score() > 0.6 and
       z.bounce_rate > 0.7 and
       not z.broken
]

print(f"Found {len(quality_zones)} high-quality zones")
```

## Integration Points

### With Market Structure
```python
from app.core.patterns import MarketStructureAnalyzer, SupportResistanceDetector

# Combine structure and zones
structure_analyzer = MarketStructureAnalyzer()
zone_detector = SupportResistanceDetector()

structure = structure_analyzer.analyze_structure(candles)
zones = zone_detector.analyze_zones(candles)

# Find order blocks that align with support/resistance zones
aligned_zones = []
for ob in structure['order_blocks']:
    for zone in zones['zones']:
        # Check if order block overlaps with S/R zone
        if (zone['bottom'] <= ob['top'] and zone['top'] >= ob['bottom']):
            aligned_zones.append({
                'order_block': ob,
                'zone': zone,
                'confluence_score': zone['strength_score'] * ob['strength']
            })

print(f"Found {len(aligned_zones)} confluent zones")
```

### With Confluence Scorer (Next Task)
```python
# Zone detection feeds into confluence scoring
confluence_score = confluence_scorer.score(
    candle_pattern=pattern,
    market_structure=structure,
    zones=zones  # Zones used for confluence
)
```

## Performance

- **Zone Detection**: O(n × m) where n = candles, m = lookback
- **Touch Finding**: O(n) single pass
- **Zone Clustering**: O(t log t) where t = touch points
- **Merging**: O(z²) where z = zones (typically small)

**Benchmark (10,000 candles):**
- Zone detection: ~15ms
- Full analysis: ~20ms

## Key Design Decisions

1. **Zones vs Levels**: Implemented zones (ranges) rather than exact price levels because:
   - More realistic for institutional order clustering
   - Accounts for price volatility
   - More forgiving for entries/exits

2. **Multiple Detection Methods**: Combined swing-based and touch-based detection:
   - Swing-based: Catches obvious S/R at extremes
   - Touch-based: Catches hidden zones via wick rejections
   - Merging: Prevents duplication

3. **Touch Tracking**: Full history of every zone test:
   - Enables bounce rate calculation
   - Volume analysis at key levels
   - Historical reliability metrics

4. **Strength Classification**: Multi-factor scoring:
   - Touch count (quantity)
   - Bounce rate (quality)
   - Volume profile (institutional interest)
   - Recency (current relevance)

## Next Steps

With zones complete, the next task is:
- **Task ID:** confluence
- **Description:** Implement multi-timeframe confluence scorer
- **Dependencies:** candle-patterns, market-structure, zones (ALL READY ✅)

The confluence scorer will combine:
- Candle patterns
- Market structure (swings, BOS, CHoCH, order blocks, FVGs)
- Support/resistance zones
- Multi-timeframe alignment

---

**Task completed successfully!** ✅

All core pattern detection components now operational:
- ✅ Candle patterns
- ✅ Market structure
- ✅ Support/Resistance zones

Ready for confluence scoring implementation.
