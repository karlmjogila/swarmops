# Pattern Detection Modules

This package provides deterministic pattern detection for technical analysis and trading strategies.

## Modules

### `candles.py` - Candlestick Pattern Detection

Detects various candlestick patterns used in trading analysis. All detections are deterministic and based on price action structure.

#### Supported Patterns

**Core Patterns (from requirements):**
- **LE Candle (Liquidity Engine)** - Strong directional move with large body (>60% of range) and small wicks
- **Small Wick** - Minimal rejection, strong price acceptance
- **Steeper Wick** - Long wick (>50% of range) indicating rejection at price level
- **Celery** - Narrow body (<20% of range) with long wicks on both sides, indicates indecision
- **Bullish/Bearish Engulfing** - Reversal patterns where current candle body engulfs previous

**Additional Classic Patterns:**
- **Doji** - Very small body (<10% of range by default), indicates indecision
- **Hammer** - Bullish reversal with long lower wick
- **Shooting Star** - Bearish reversal with long upper wick
- **Inverted Hammer** - Bullish pattern with long upper wick
- **Hanging Man** - Bearish pattern with long lower wick
- **Pin Bar (Bullish/Bearish)** - Strong rejection with very long wick (>65%)
- **Strong Directional** - Large body (>70%) indicating momentum
- **Inside Bar** - Range within previous candle, consolidation
- **Outside Bar** - Range engulfs previous candle, expansion/breakout

#### Usage

```python
from app.core.market.data import Candle
from app.core.patterns.candles import CandlePatternDetector, CandlePatternType, PatternSignal

# Create detector
detector = CandlePatternDetector()

# Detect patterns in candle sequence
patterns = detector.detect_all_patterns(candles)

# Filter patterns
strong_bullish = detector.filter_patterns(
    patterns,
    min_strength=0.7,
    signals=[PatternSignal.BULLISH]
)

# Get patterns at specific index (for real-time detection)
latest_patterns = detector.get_patterns_at_index(candles, -1)

# Custom thresholds
custom_detector = CandlePatternDetector(
    wick_threshold=0.4,      # Min/max wick size ratio
    body_threshold=0.7,      # Min body size for strong candles
    engulfing_threshold=1.0, # Min coverage for engulfing
    doji_threshold=0.05,     # Max body size for doji
)
```

#### DetectedPattern Structure

Each detected pattern includes:
- **pattern_type**: Type of pattern (CandlePatternType enum)
- **signal**: Bullish/Bearish/Neutral/Reversal
- **strength**: Pattern quality score (0.0 - 1.0)
- **candle_index**: Index in the candle sequence
- **description**: Human-readable description
- **metadata**: Pattern-specific measurements (body_ratio, wick_ratios, etc.)

#### Pattern Detection Principles

Following trading systems best practices:
1. **Deterministic** - No ML or guesswork, pure price action analysis
2. **Configurable** - Adjustable thresholds for different market conditions
3. **Scored** - Each pattern has a strength score for quality assessment
4. **Context-aware** - Patterns include metadata for multi-timeframe analysis
5. **Validated** - Comprehensive test coverage with known pattern examples

#### Testing

Run unit tests:
```bash
cd backend
PYTHONPATH=$PWD poetry run pytest tests/test_candle_patterns.py -v
```

All tests use known pattern examples to ensure accurate detection across:
- Core required patterns (LE candle, small wick, steeper wick, celery, engulfing)
- Classic reversal patterns (hammer, shooting star, pin bars)
- Momentum patterns (strong directional, LE candle)
- Consolidation patterns (doji, celery, inside bar)
- Edge cases (zero range, empty lists, single candles)
- Real-world scenarios (reversal setups, consolidation + breakout)

#### Integration

The pattern detector integrates with:
- **Market Data Layer** (`app.core.market.data.Candle`)
- **Multi-Timeframe Analysis** (for confluence scoring)
- **Signal Generator** (combines patterns with market structure)
- **Trade Reasoner** (provides pattern context for LLM analysis)

#### Performance

Pattern detection is designed for speed:
- O(n) complexity for full sequence detection
- O(1) for single candle pattern detection
- No external dependencies beyond standard library
- Can process thousands of candles per second

#### Future Enhancements

Potential additions:
- Three-candle patterns (morning star, evening star, three white soldiers)
- Volume-weighted pattern strength
- Pattern clustering and trend analysis
- Machine learning-assisted pattern quality scoring (non-blocking)
