# Market Cycle Classifier

## Overview

The **Market Cycle Classifier** is a sophisticated component that automatically classifies market phases into three distinct cycles:

- **DRIVE**: Strong momentum, trending price action
- **RANGE**: Consolidation, equilibrium, bounded movement
- **LIQUIDITY**: Stop hunts, sweeps, liquidity grabs

This classifier is essential for strategy selection and trade filtering, as different patterns perform better in different market phases.

## Implementation Details

### File Location
`backend/src/detection/cycle_classifier.py`

### Key Classes

#### `MarketCycleClassifier`
Main classifier class that analyzes candle data and determines the current market cycle phase.

**Key Features:**
- Multi-metric analysis (momentum, volatility, structure, liquidity, range behavior)
- Cycle transition detection
- Sub-phase classification within each main cycle
- Cycle health scoring
- Trading recommendations based on cycle

**Configuration Parameters:**
```python
# DRIVE phase thresholds
drive_momentum_threshold = 0.65
drive_directional_threshold = 0.70
drive_min_structure_breaks = 2

# RANGE phase thresholds
range_volatility_max = 0.35
range_oscillation_min = 3
range_mean_reversion_min = 0.60

# LIQUIDITY phase thresholds
liquidity_wick_threshold = 0.60
liquidity_sweep_min = 2
liquidity_false_break_min = 2
```

#### `CycleClassification`
Result object containing:
- Primary cycle classification
- Confidence score (0.0 to 1.0)
- Sub-phase identification
- Transition probability
- Dominant bias (LONG/SHORT/None)
- Cycle health score
- Comprehensive metrics

#### `CycleMetrics`
Detailed metrics used for classification:
- **Momentum**: Score, acceleration, directional strength
- **Volatility**: Normalized volatility, trend, price dispersion
- **Structure**: Higher highs/lower lows, breaks, false breaks
- **Liquidity**: Wick dominance, sweeps, reversals
- **Range**: Oscillations, mean reversion, tightness
- **Volume**: Trend, spikes

#### `CycleHistory`
Tracks historical classifications to:
- Prevent rapid phase switching
- Detect cycle transitions
- Analyze cycle sequences

## Usage Example

```python
from src.detection.cycle_classifier import MarketCycleClassifier
from src.types import CandleData, Timeframe

# Initialize classifier
classifier = MarketCycleClassifier()

# Classify current market cycle
classification = classifier.classify(candles)

print(f"Cycle: {classification.cycle}")
print(f"Confidence: {classification.confidence:.2%}")
print(f"Sub-phase: {classification.sub_phase}")
print(f"Bias: {classification.dominant_bias}")

# Get trading recommendations
recommendations = classifier.get_cycle_recommendation(classification)
print(f"Preferred patterns: {recommendations['preferred_patterns']}")
print(f"Avoid patterns: {recommendations['avoid_patterns']}")
```

## Cycle Detection Logic

### DRIVE Phase Scoring (40-100% total score)
- Strong momentum (abs > 0.65): 40% weight
- High directional strength (> 0.70): 25% weight
- Structure breaks (≥ 2): 15% weight
- Higher highs or lower lows: 10% weight
- Momentum acceleration: 10% weight

**Sub-phases:**
- `strong_drive`: Momentum > 0.85
- `moderate_drive`: Momentum > 0.70
- `accelerating_drive`: Acceleration > 0.3
- `exhausting_drive`: Acceleration < -0.3
- `steady_drive`: Normal drive conditions

### RANGE Phase Scoring (0-100% total score)
- Low volatility (< 0.35): 30% weight
- Mean reversion strength (> 0.60): 25% weight
- Price oscillations (≥ 3): 20% weight
- Range tightness: 15% weight
- Low momentum: 10% weight

**Sub-phases:**
- `tight_range`: Range tightness > 0.8
- `choppy_range`: Oscillations > 6
- `mean_reverting_range`: Mean reversion > 0.8
- `balanced_range`: Normal range conditions

### LIQUIDITY Phase Scoring (0-100% total score)
- High wick dominance (> 0.60): 30% weight
- Sweep events (≥ 2): 25% weight
- False breaks (≥ 2): 20% weight
- Reversal candles: 15% weight
- Large wicks: 10% weight

**Sub-phases:**
- `multi_sweep`: Sweeps > 3
- `false_breakout_zone`: False breaks > 3
- `reversal_zone`: Reversal candles > 2
- `liquidity_grab`: Normal liquidity conditions

## Trading Recommendations

### DRIVE Phase
**Preferred Patterns:**
- Breakout trades
- Momentum entries
- Trend continuation

**Avoid:**
- Mean reversion strategies
- Range extreme trades

**Confidence Adjustment:** 1.2x (for clean drives with health > 0.7)

### RANGE Phase
**Preferred Patterns:**
- Mean reversion
- Onion plays (range extremes)
- Support/resistance bounces

**Avoid:**
- Breakout trades
- Momentum entries

**Confidence Adjustment:** 1.1x (for tight ranges), 0.9x (for loose ranges)

### LIQUIDITY Phase
**Preferred Patterns:**
- Fakeout reversals
- Reversal patterns
- Sweep entry setups

**Avoid:**
- Early breakout entries
- Momentum chasing

**Confidence Adjustment:** 0.8x (more cautious)

## Metrics Calculation

### Momentum Score (-1.0 to 1.0)
Calculates rate of price change with exponential weighting toward recent candles.
Normalized to -1 (strong bearish) to +1 (strong bullish).

### Directional Strength (0.0 to 1.0)
Measures consistency of candle direction and average body size.
High score = consistent directional candles with strong bodies.

### Normalized Volatility (0.0 to 1.0)
ATR (Average True Range) normalized by price.
Scaled where 2% ATR = 1.0 (high volatility).

### Wick Dominance (0.0 to 1.0)
Average ratio of wicks to total candle range.
High values indicate liquidity events (stop hunts).

### Mean Reversion Strength (0.0 to 1.0)
Frequency of price returning to mean after deviation.
High values indicate range-bound behavior.

## Transition Detection

The classifier calculates transition probability based on:
- Score differences between current and competing cycles
- Current cycle confidence level
- Cycle duration (prevents premature transitions)

**Minimum Cycle Duration:** 5 candles (prevents rapid switching)

**Transition Warning:** Issued when probability > 60%

## Testing

Two test files are provided:

### `test_cycle_classifier.py`
Comprehensive test suite covering:
- Drive phase detection (bullish/bearish)
- Range phase detection
- Liquidity phase detection
- Cycle transitions
- Metrics calculation
- Recommendations
- Real-world scenarios

### `test_cycle_simple.py`
Simple diagnostic test with detailed output showing:
- Classification results
- All metrics values
- Scoring breakdown
- Recommendations
- Price action verification

**Run tests:**
```bash
cd backend
source venv/bin/activate
python3 test_cycle_simple.py
```

## Integration with Trading System

The cycle classifier integrates with:

1. **Confluence Scorer**: Adjusts signal confidence based on cycle
2. **Trade Reasoner**: Includes cycle context in trade explanations
3. **Strategy Selector**: Filters strategies appropriate for current cycle
4. **Risk Manager**: Adjusts position sizing based on cycle health

## Performance Characteristics

- **Minimum Required Candles:** 30 (for reliable classification)
- **Recommended Lookback:** 50-60 candles
- **Update Frequency:** Every new candle close
- **Computational Complexity:** O(n) where n = number of candles

## Future Enhancements

Potential improvements:
- Machine learning-based cycle detection
- Volume profile integration
- Multi-timeframe cycle alignment
- Cycle prediction (not just classification)
- Custom cycle definitions per asset
- Adaptive threshold tuning

## Dependencies

- `numpy`: For numerical calculations
- `datetime`: For timestamp handling
- `collections.deque`: For efficient history tracking
- `src.types`: Core type definitions

## Exports

```python
from src.detection.cycle_classifier import (
    MarketCycleClassifier,
    CycleClassification,
    CycleMetrics,
    CycleHistory
)
```

---

**Status:** ✅ Complete and tested
**Version:** 1.0
**Author:** Hyperliquid Trading Bot Suite
**Date:** 2025-02-10
