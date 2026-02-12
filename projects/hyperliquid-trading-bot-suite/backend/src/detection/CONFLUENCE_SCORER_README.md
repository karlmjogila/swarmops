# Confluence Scorer

## Overview

The Confluence Scorer is the core signal generation engine of the Hyperliquid Trading Bot Suite. It implements a sophisticated multi-timeframe analysis system that combines pattern detection, market structure analysis, and cycle classification to generate high-probability trade signals.

## Core Principle

**Higher Timeframe Bias + Lower Timeframe Entry = High Probability Trade**

The confluence scorer follows the professional trading principle of:
1. Determining the directional bias from higher timeframes (4H, 1H)
2. Finding precise entry patterns on lower timeframes (15M, 5M)
3. Validating confluence across multiple factors
4. Generating signals only when alignment is strong

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  CONFLUENCE SCORER                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: Multi-Timeframe Candle Data                         │
│         (4H, 1H, 15M, 5M, etc.)                             │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  STEP 1: Analyze Each Timeframe Independently      │    │
│  │  - Pattern Detection (LE, Small Wick, etc.)        │    │
│  │  - Market Structure (Trend, BOS, Zones)            │    │
│  │  - Cycle Classification (Drive, Range, Liquidity)  │    │
│  └────────────────────────────────────────────────────┘    │
│                         │                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  STEP 2: Determine Higher Timeframe Bias           │    │
│  │  - Aggregate trend direction from higher TFs       │    │
│  │  - Weight by timeframe importance                  │    │
│  │  - Establish directional bias (LONG/SHORT/NONE)    │    │
│  └────────────────────────────────────────────────────┘    │
│                         │                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  STEP 3: Find Entry Patterns on Lower Timeframes   │    │
│  │  - Scan entry timeframe for signals                │    │
│  │  - Filter by confidence and quality                │    │
│  │  - Check pattern alignment with HTF bias           │    │
│  └────────────────────────────────────────────────────┘    │
│                         │                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  STEP 4: Calculate Confluence Score                │    │
│  │  - Pattern Quality        (20% weight)             │    │
│  │  - Trend Alignment        (25% weight)             │    │
│  │  - Cycle Compatibility    (15% weight)             │    │
│  │  - Structure Confluence   (15% weight)             │    │
│  │  - Zone Interaction       (10% weight)             │    │
│  │  - Momentum Alignment     (10% weight)             │    │
│  │  - Volume Confirmation    (5% weight)              │    │
│  └────────────────────────────────────────────────────┘    │
│                         │                                    │
│  Output: SignalGeneration                                   │
│          (with ConfluenceScore and context)                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. TimeframeAnalysis

Encapsulates complete analysis results for a single timeframe:

```python
@dataclass
class TimeframeAnalysis:
    timeframe: Timeframe
    timestamp: datetime
    
    # Pattern detections
    patterns: List[PatternDetection]
    strongest_pattern: Optional[PatternDetection]
    
    # Market structure
    trend_direction: Optional[OrderSide]
    trend_strength: float
    
    # Cycle classification
    market_cycle: Optional[MarketCycle]
    cycle_confidence: float
    
    # Zone interactions
    near_support: bool
    near_resistance: bool
    
    # Momentum
    momentum_score: float
```

### 2. ConfluenceScore

Multi-dimensional scoring of signal quality:

```python
@dataclass
class ConfluenceScore:
    # Overall metrics
    total_score: float           # 0.0 to 1.0
    confidence: float            # 0.0 to 1.0
    signal_strength: float       # 0.0 to 1.0
    
    # Directional bias
    bias_direction: Optional[OrderSide]
    bias_confidence: float
    
    # Component scores
    pattern_score: float
    structure_score: float
    cycle_score: float
    zone_score: float
    
    # Context
    higher_tf_bias: Optional[OrderSide]
    higher_tf_cycle: Optional[MarketCycle]
    entry_timeframe: Optional[Timeframe]
```

### 3. SignalGeneration

Complete trade signal with actionable details:

```python
@dataclass
class SignalGeneration:
    signal_id: str
    timestamp: datetime
    asset: str
    
    # Trade details
    direction: OrderSide
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    
    # Confluence analysis
    confluence: ConfluenceScore
    
    # Multi-timeframe context
    analyses: Dict[Timeframe, TimeframeAnalysis]
    
    # Risk metrics
    risk_reward_ratio: float
    position_size_percent: float
```

### 4. ConfluenceScorer

Main engine that orchestrates the analysis:

```python
class ConfluenceScorer:
    def __init__(
        self,
        min_confluence_score: float = 0.6,
        timeframe_weights: Optional[Dict[Timeframe, float]] = None
    ):
        # Initialize with customizable thresholds
        pass
    
    def analyze_timeframes(
        self,
        candles: Dict[Timeframe, List[CandleData]],
        asset: str
    ) -> List[TimeframeAnalysis]:
        # Analyze each timeframe independently
        pass
    
    def calculate_confluence(
        self,
        analyses: List[TimeframeAnalysis],
        entry_timeframe: Timeframe
    ) -> ConfluenceScore:
        # Calculate multi-factor confluence score
        pass
    
    def generate_signal(
        self,
        asset: str,
        candles: Dict[Timeframe, List[CandleData]],
        entry_timeframe: Timeframe = Timeframe.M15
    ) -> Optional[SignalGeneration]:
        # Complete pipeline: analyze → score → signal
        pass
```

## Usage Examples

### Basic Signal Generation

```python
from src.detection import ConfluenceScorer
from src.types import CandleData, Timeframe

# Initialize scorer
scorer = ConfluenceScorer(min_confluence_score=0.7)

# Prepare multi-timeframe data
candles = {
    Timeframe.H4: load_candles("BTC", Timeframe.H4),
    Timeframe.H1: load_candles("BTC", Timeframe.H1),
    Timeframe.M15: load_candles("BTC", Timeframe.M15),
    Timeframe.M5: load_candles("BTC", Timeframe.M5),
}

# Generate signal
signal = scorer.generate_signal(
    asset="BTC",
    candles=candles,
    entry_timeframe=Timeframe.M15
)

if signal and signal.confluence.total_score >= 0.7:
    print(f"🎯 High-quality signal: {signal.direction.value}")
    print(f"   Confluence: {signal.confluence.total_score:.2f}")
    print(f"   Entry: ${signal.entry_price:.2f}")
    print(f"   R:R: {signal.risk_reward_ratio:.1f}")
```

### Detailed Analysis

```python
# Analyze each timeframe
analyses = scorer.analyze_timeframes(candles, "BTC")

for analysis in analyses:
    print(f"\n{analysis.timeframe.value}:")
    print(f"  Trend: {analysis.trend_direction}")
    print(f"  Cycle: {analysis.market_cycle}")
    print(f"  Patterns: {len(analysis.patterns)}")

# Calculate confluence for specific entry
confluence = scorer.calculate_confluence(
    analyses=analyses,
    entry_timeframe=Timeframe.M15
)

print(f"\nConfluence Score: {confluence.total_score:.2f}")
print(f"Pattern Score: {confluence.pattern_score:.2f}")
print(f"Structure Score: {confluence.structure_score:.2f}")
```

### Custom Weights

```python
# Customize component weights
scorer = ConfluenceScorer(
    min_confluence_score=0.65,
    timeframe_weights={
        Timeframe.H4: 0.4,   # Higher weight to 4H
        Timeframe.H1: 0.3,
        Timeframe.M15: 0.2,
        Timeframe.M5: 0.1
    }
)
```

## Confluence Factors

### 1. Pattern Quality (20%)
- Confidence of detected pattern
- Pattern type appropriateness for market conditions
- Historical performance of pattern

### 2. Trend Alignment (25%)
- Higher timeframe trend direction
- Trend strength across timeframes
- Consistency of trend signals

### 3. Cycle Compatibility (15%)
- Market cycle phase (Drive/Range/Liquidity)
- Pattern-cycle alignment
- Cycle transition probability

### 4. Structure Confluence (15%)
- Break of structure alignment
- Change of character signals
- Structure point proximity

### 5. Zone Interaction (10%)
- Support/resistance proximity
- Zone strength
- Bounce/rejection probability

### 6. Momentum Alignment (10%)
- Multi-timeframe momentum direction
- Momentum acceleration
- Momentum divergence check

### 7. Volume Confirmation (5%)
- Volume profile (increasing/spiking)
- Relative volume strength
- Volume at key levels

## Signal Quality Tiers

| Confluence Score | Quality Level | Description |
|------------------|---------------|-------------|
| 0.85 - 1.00 | Exceptional | Rare, very high probability setups |
| 0.75 - 0.84 | Excellent | Strong confluence, high confidence |
| 0.65 - 0.74 | Good | Solid setup with reasonable confluence |
| 0.50 - 0.64 | Acceptable | Meets minimum requirements |
| < 0.50 | Poor | Below threshold, signal not generated |

## Minimum Requirements

For a signal to be generated, it must meet:

1. **Minimum Confluence Score**: Default 0.6 (configurable)
2. **Higher TF Bias**: Clear directional bias from higher timeframes
3. **Entry Pattern**: Valid pattern detected on entry timeframe
4. **Direction Alignment**: Entry pattern aligns with HTF bias
5. **Cycle Check**: Pattern appropriate for current market cycle

## Performance Considerations

- **Timeframe Data**: Requires minimum 50 candles per timeframe for reliable analysis
- **Computational Load**: Full analysis takes ~100-300ms depending on data volume
- **Caching**: Uses internal caching for repeated analyses
- **Parallel Processing**: Can analyze multiple assets concurrently

## Integration Points

### With Backtesting Engine
```python
# In backtest loop
for timestamp, candles in replay_data:
    signal = scorer.generate_signal("BTC", candles)
    if signal:
        execute_backtest_trade(signal)
```

### With Live Trading
```python
# In live trading loop
while trading:
    current_candles = fetch_multi_timeframe_data("BTC")
    signal = scorer.generate_signal("BTC", current_candles)
    
    if signal and signal.confluence.total_score >= 0.75:
        place_order(signal)
```

### With Trade Reasoner
```python
# Signal enrichment with LLM reasoning
signal = scorer.generate_signal("BTC", candles)
if signal:
    reasoning = trade_reasoner.explain(signal)
    signal.reasoning_text = reasoning
```

## Testing

Run tests:
```bash
pytest tests/test_confluence_scorer.py -v
```

## Future Enhancements

- [ ] Machine learning confidence calibration
- [ ] Pattern performance tracking and adaptive weighting
- [ ] Multi-asset correlation analysis
- [ ] Real-time signal streaming
- [ ] GPU acceleration for large-scale backtesting

## References

- Pattern Detection: `candle_patterns.py`
- Market Structure: `market_structure.py`
- Cycle Classification: `cycle_classifier.py`
- Type Definitions: `../types/__init__.py`

---

**Status**: ✅ Complete and Production-Ready  
**Author**: Hyperliquid Trading Bot Suite  
**Last Updated**: February 2025
