"""Candle pattern detection for trading analysis.

Detects various candlestick patterns used in technical analysis and trading strategies.
All detections are deterministic and based on price action structure.
"""
from dataclasses import dataclass
from enum import StrEnum
from typing import List, Optional
from app.core.market.data import Candle


class CandlePatternType(StrEnum):
    """Types of detected candle patterns."""
    # Core patterns from requirements
    LE_CANDLE = "le_candle"  # Liquidity Engine - strong directional move
    SMALL_WICK = "small_wick"  # Minimal wicks, strong momentum
    STEEPER_WICK = "steeper_wick"  # Long wick, rejection pattern
    CELERY = "celery"  # Narrow body, long wicks on both sides
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    
    # Additional common patterns
    DOJI = "doji"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    INVERTED_HAMMER = "inverted_hammer"
    HANGING_MAN = "hanging_man"
    PIN_BAR_BULLISH = "pin_bar_bullish"
    PIN_BAR_BEARISH = "pin_bar_bearish"
    STRONG_BULLISH = "strong_bullish"
    STRONG_BEARISH = "strong_bearish"
    INSIDE_BAR = "inside_bar"
    OUTSIDE_BAR = "outside_bar"


class PatternSignal(StrEnum):
    """Signal direction for pattern."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    REVERSAL = "reversal"


@dataclass
class DetectedPattern:
    """Represents a detected candle pattern.
    
    Attributes:
        pattern_type: Type of pattern detected
        signal: Bullish/bearish/neutral signal
        strength: Pattern strength score (0.0 - 1.0)
        candle_index: Index of the pattern candle in the sequence
        description: Human-readable pattern description
        metadata: Additional pattern-specific data
    """
    pattern_type: CandlePatternType
    signal: PatternSignal
    strength: float  # 0.0 - 1.0
    candle_index: int
    description: str
    metadata: dict


class CandlePatternDetector:
    """Detects candlestick patterns in price data.
    
    Implements pattern detection following trading systems best practices:
    - Deterministic, no ML or guesswork
    - Configurable thresholds for flexibility
    - Returns strength scores for pattern quality
    - Validates patterns against historical context
    """
    
    def __init__(
        self,
        wick_threshold: float = 0.3,
        body_threshold: float = 0.6,
        engulfing_threshold: float = 0.95,
        doji_threshold: float = 0.1,
    ):
        """Initialize pattern detector with thresholds.
        
        Args:
            wick_threshold: Min/max wick size as ratio of total range (default: 0.3)
            body_threshold: Min body size as ratio of total range (default: 0.6)
            engulfing_threshold: Min body coverage for engulfing (default: 0.95)
            doji_threshold: Max body size for doji as ratio of range (default: 0.1)
        """
        self.wick_threshold = wick_threshold
        self.body_threshold = body_threshold
        self.engulfing_threshold = engulfing_threshold
        self.doji_threshold = doji_threshold
    
    def detect_all_patterns(self, candles: List[Candle]) -> List[DetectedPattern]:
        """Detect all patterns in a candle sequence.
        
        Args:
            candles: List of Candle objects in chronological order
            
        Returns:
            List of DetectedPattern objects, one per detected pattern
            
        Example:
            >>> detector = CandlePatternDetector()
            >>> patterns = detector.detect_all_patterns(candles)
            >>> for pattern in patterns:
            ...     print(f"{pattern.pattern_type}: {pattern.signal} ({pattern.strength:.2f})")
        """
        if not candles:
            return []
        
        patterns = []
        
        # Single candle patterns (check all candles)
        for i, candle in enumerate(candles):
            patterns.extend(self._detect_single_candle_patterns(candle, i))
        
        # Multi-candle patterns (need at least 2 candles)
        if len(candles) >= 2:
            for i in range(1, len(candles)):
                patterns.extend(
                    self._detect_multi_candle_patterns(candles, i)
                )
        
        return patterns
    
    def _detect_single_candle_patterns(
        self, candle: Candle, index: int
    ) -> List[DetectedPattern]:
        """Detect patterns that can be identified from a single candle."""
        patterns = []
        
        # LE Candle (Liquidity Engine) - strong directional move
        if pattern := self._detect_le_candle(candle, index):
            patterns.append(pattern)
        
        # Small Wick - minimal rejection, strong momentum
        if pattern := self._detect_small_wick(candle, index):
            patterns.append(pattern)
        
        # Steeper Wick - long wick rejection
        if pattern := self._detect_steeper_wick(candle, index):
            patterns.append(pattern)
        
        # Celery - narrow body with long wicks
        if pattern := self._detect_celery(candle, index):
            patterns.append(pattern)
        
        # Doji
        if pattern := self._detect_doji(candle, index):
            patterns.append(pattern)
        
        # Hammer / Shooting Star
        if pattern := self._detect_hammer_shooting_star(candle, index):
            patterns.append(pattern)
        
        # Pin Bars
        if pattern := self._detect_pin_bar(candle, index):
            patterns.append(pattern)
        
        # Strong Directional
        if pattern := self._detect_strong_directional(candle, index):
            patterns.append(pattern)
        
        return patterns
    
    def _detect_multi_candle_patterns(
        self, candles: List[Candle], index: int
    ) -> List[DetectedPattern]:
        """Detect patterns that require multiple candles."""
        patterns = []
        
        current = candles[index]
        previous = candles[index - 1]
        
        # Engulfing patterns
        if pattern := self._detect_engulfing(previous, current, index):
            patterns.append(pattern)
        
        # Inside/Outside bars
        if pattern := self._detect_inside_outside_bar(previous, current, index):
            patterns.append(pattern)
        
        return patterns
    
    def _detect_le_candle(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Liquidity Engine candle - strong directional move.
        
        Characteristics:
        - Large body (>60% of range)
        - Small wicks (<20% of range each)
        - Strong momentum in one direction
        """
        if candle.total_range == 0:
            return None
        
        body_ratio = candle.body_size / candle.total_range
        upper_wick_ratio = candle.wick_size_upper / candle.total_range
        lower_wick_ratio = candle.wick_size_lower / candle.total_range
        
        # Large body, small wicks
        if body_ratio > self.body_threshold and \
           upper_wick_ratio < 0.2 and lower_wick_ratio < 0.2:
            
            signal = PatternSignal.BULLISH if candle.is_bullish else PatternSignal.BEARISH
            strength = min(body_ratio, 1.0)  # Stronger with larger body
            
            return DetectedPattern(
                pattern_type=CandlePatternType.LE_CANDLE,
                signal=signal,
                strength=strength,
                candle_index=index,
                description=f"LE Candle: Strong {signal} momentum, {body_ratio:.1%} body",
                metadata={
                    "body_ratio": body_ratio,
                    "upper_wick_ratio": upper_wick_ratio,
                    "lower_wick_ratio": lower_wick_ratio,
                }
            )
        
        return None
    
    def _detect_small_wick(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Small Wick candle - minimal rejection.
        
        Characteristics:
        - Very small wicks (<10% of range on one or both sides)
        - Strong price acceptance
        """
        if candle.total_range == 0:
            return None
        
        upper_wick_ratio = candle.wick_size_upper / candle.total_range
        lower_wick_ratio = candle.wick_size_lower / candle.total_range
        
        # At least one wick must be very small
        min_wick = min(upper_wick_ratio, lower_wick_ratio)
        
        if min_wick < 0.1:
            signal = PatternSignal.BULLISH if candle.is_bullish else PatternSignal.BEARISH
            strength = 1.0 - min_wick  # Stronger with smaller wick
            
            return DetectedPattern(
                pattern_type=CandlePatternType.SMALL_WICK,
                signal=signal,
                strength=strength,
                candle_index=index,
                description=f"Small Wick: Clean {signal} move, minimal rejection",
                metadata={
                    "upper_wick_ratio": upper_wick_ratio,
                    "lower_wick_ratio": lower_wick_ratio,
                }
            )
        
        return None
    
    def _detect_steeper_wick(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Steeper Wick - long wick indicating rejection.
        
        Characteristics:
        - One wick is >50% of total range
        - Indicates rejection at that price level
        """
        if candle.total_range == 0:
            return None
        
        upper_wick_ratio = candle.wick_size_upper / candle.total_range
        lower_wick_ratio = candle.wick_size_lower / candle.total_range
        
        # Long upper wick = bearish rejection
        if upper_wick_ratio > 0.5:
            return DetectedPattern(
                pattern_type=CandlePatternType.STEEPER_WICK,
                signal=PatternSignal.BEARISH,
                strength=min(upper_wick_ratio, 1.0),
                candle_index=index,
                description=f"Steeper Wick: Upper wick rejection ({upper_wick_ratio:.1%})",
                metadata={
                    "wick_ratio": upper_wick_ratio,
                    "direction": "upper",
                }
            )
        
        # Long lower wick = bullish rejection
        if lower_wick_ratio > 0.5:
            return DetectedPattern(
                pattern_type=CandlePatternType.STEEPER_WICK,
                signal=PatternSignal.BULLISH,
                strength=min(lower_wick_ratio, 1.0),
                candle_index=index,
                description=f"Steeper Wick: Lower wick rejection ({lower_wick_ratio:.1%})",
                metadata={
                    "wick_ratio": lower_wick_ratio,
                    "direction": "lower",
                }
            )
        
        return None
    
    def _detect_celery(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Celery pattern - narrow body with long wicks on both sides.
        
        Characteristics:
        - Small body (<20% of range)
        - Long wicks on both sides (>30% each)
        - Indicates indecision or equilibrium
        """
        if candle.total_range == 0:
            return None
        
        body_ratio = candle.body_size / candle.total_range
        upper_wick_ratio = candle.wick_size_upper / candle.total_range
        lower_wick_ratio = candle.wick_size_lower / candle.total_range
        
        if body_ratio < 0.2 and \
           upper_wick_ratio > self.wick_threshold and \
           lower_wick_ratio > self.wick_threshold:
            
            # Strength based on wick symmetry and body smallness
            wick_balance = 1.0 - abs(upper_wick_ratio - lower_wick_ratio)
            body_strength = 1.0 - (body_ratio / 0.2)
            strength = (wick_balance + body_strength) / 2
            
            return DetectedPattern(
                pattern_type=CandlePatternType.CELERY,
                signal=PatternSignal.NEUTRAL,
                strength=strength,
                candle_index=index,
                description=f"Celery: Narrow body ({body_ratio:.1%}), long wicks both sides",
                metadata={
                    "body_ratio": body_ratio,
                    "upper_wick_ratio": upper_wick_ratio,
                    "lower_wick_ratio": lower_wick_ratio,
                }
            )
        
        return None
    
    def _detect_engulfing(
        self, previous: Candle, current: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Bullish/Bearish Engulfing patterns.
        
        Characteristics:
        - Current candle body completely engulfs previous candle body
        - Reversal pattern
        """
        # Bullish Engulfing: bearish candle followed by bullish that engulfs it
        if previous.is_bearish and current.is_bullish:
            prev_body_low = min(previous.open, previous.close)
            prev_body_high = max(previous.open, previous.close)
            curr_body_low = min(current.open, current.close)
            curr_body_high = max(current.open, current.close)
            
            if curr_body_low <= prev_body_low and curr_body_high >= prev_body_high:
                # Calculate coverage ratio
                coverage = current.body_size / previous.body_size if previous.body_size > 0 else 0
                
                if coverage >= self.engulfing_threshold:
                    strength = min(coverage / 2.0, 1.0)  # Cap at 1.0
                    
                    return DetectedPattern(
                        pattern_type=CandlePatternType.BULLISH_ENGULFING,
                        signal=PatternSignal.BULLISH,
                        strength=strength,
                        candle_index=index,
                        description=f"Bullish Engulfing: {coverage:.1%} coverage",
                        metadata={
                            "coverage_ratio": coverage,
                            "previous_body": previous.body_size,
                            "current_body": current.body_size,
                        }
                    )
        
        # Bearish Engulfing: bullish candle followed by bearish that engulfs it
        if previous.is_bullish and current.is_bearish:
            prev_body_low = min(previous.open, previous.close)
            prev_body_high = max(previous.open, previous.close)
            curr_body_low = min(current.open, current.close)
            curr_body_high = max(current.open, current.close)
            
            if curr_body_low <= prev_body_low and curr_body_high >= prev_body_high:
                coverage = current.body_size / previous.body_size if previous.body_size > 0 else 0
                
                if coverage >= self.engulfing_threshold:
                    strength = min(coverage / 2.0, 1.0)
                    
                    return DetectedPattern(
                        pattern_type=CandlePatternType.BEARISH_ENGULFING,
                        signal=PatternSignal.BEARISH,
                        strength=strength,
                        candle_index=index,
                        description=f"Bearish Engulfing: {coverage:.1%} coverage",
                        metadata={
                            "coverage_ratio": coverage,
                            "previous_body": previous.body_size,
                            "current_body": current.body_size,
                        }
                    )
        
        return None
    
    def _detect_doji(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Doji pattern - indecision candle.
        
        Characteristics:
        - Very small body (<10% of range by default)
        - Can have wicks of any size
        - Indicates indecision or potential reversal
        """
        if candle.total_range == 0:
            return None
        
        body_ratio = candle.body_size / candle.total_range
        
        if body_ratio < self.doji_threshold:
            strength = 1.0 - (body_ratio / self.doji_threshold)
            
            return DetectedPattern(
                pattern_type=CandlePatternType.DOJI,
                signal=PatternSignal.NEUTRAL,
                strength=strength,
                candle_index=index,
                description=f"Doji: Indecision, {body_ratio:.2%} body",
                metadata={
                    "body_ratio": body_ratio,
                }
            )
        
        return None
    
    def _detect_hammer_shooting_star(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Hammer and Shooting Star patterns.
        
        Hammer: Bullish reversal with long lower wick
        Shooting Star: Bearish reversal with long upper wick
        Inverted Hammer: Bullish with long upper wick
        Hanging Man: Bearish with long lower wick
        """
        if candle.total_range == 0:
            return None
        
        body_ratio = candle.body_size / candle.total_range
        upper_wick_ratio = candle.wick_size_upper / candle.total_range
        lower_wick_ratio = candle.wick_size_lower / candle.total_range
        
        # Small body required for all these patterns
        if body_ratio > 0.3:
            return None
        
        # Hammer: Long lower wick (>2x body), small upper wick
        if lower_wick_ratio > 0.6 and upper_wick_ratio <= 0.15:
            strength = min(lower_wick_ratio, 1.0)
            return DetectedPattern(
                pattern_type=CandlePatternType.HAMMER,
                signal=PatternSignal.BULLISH,
                strength=strength,
                candle_index=index,
                description=f"Hammer: Bullish reversal, {lower_wick_ratio:.1%} lower wick",
                metadata={
                    "lower_wick_ratio": lower_wick_ratio,
                    "body_ratio": body_ratio,
                }
            )
        
        # Shooting Star: Long upper wick (>2x body), small lower wick
        if upper_wick_ratio > 0.6 and lower_wick_ratio <= 0.15:
            strength = min(upper_wick_ratio, 1.0)
            return DetectedPattern(
                pattern_type=CandlePatternType.SHOOTING_STAR,
                signal=PatternSignal.BEARISH,
                strength=strength,
                candle_index=index,
                description=f"Shooting Star: Bearish reversal, {upper_wick_ratio:.1%} upper wick",
                metadata={
                    "upper_wick_ratio": upper_wick_ratio,
                    "body_ratio": body_ratio,
                }
            )
        
        # Inverted Hammer: Long upper wick, at support
        if upper_wick_ratio > 0.5 and lower_wick_ratio < 0.2 and body_ratio < 0.2:
            strength = min(upper_wick_ratio, 1.0)
            return DetectedPattern(
                pattern_type=CandlePatternType.INVERTED_HAMMER,
                signal=PatternSignal.BULLISH,
                strength=strength,
                candle_index=index,
                description=f"Inverted Hammer: {upper_wick_ratio:.1%} upper wick",
                metadata={
                    "upper_wick_ratio": upper_wick_ratio,
                    "body_ratio": body_ratio,
                }
            )
        
        # Hanging Man: Long lower wick, at resistance
        if lower_wick_ratio > 0.5 and upper_wick_ratio < 0.2 and body_ratio < 0.2:
            strength = min(lower_wick_ratio, 1.0)
            return DetectedPattern(
                pattern_type=CandlePatternType.HANGING_MAN,
                signal=PatternSignal.BEARISH,
                strength=strength,
                candle_index=index,
                description=f"Hanging Man: {lower_wick_ratio:.1%} lower wick",
                metadata={
                    "lower_wick_ratio": lower_wick_ratio,
                    "body_ratio": body_ratio,
                }
            )
        
        return None
    
    def _detect_pin_bar(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Pin Bar patterns - strong rejection with long wick.
        
        Similar to hammer/shooting star but with slightly different criteria.
        Pin bars are strong reversal signals.
        """
        if candle.total_range == 0:
            return None
        
        body_ratio = candle.body_size / candle.total_range
        upper_wick_ratio = candle.wick_size_upper / candle.total_range
        lower_wick_ratio = candle.wick_size_lower / candle.total_range
        
        # Pin bar needs small body and one dominant wick
        if body_ratio > 0.25:
            return None
        
        # Bullish Pin Bar: Long lower wick
        if lower_wick_ratio > 0.65 and lower_wick_ratio > (upper_wick_ratio * 3):
            strength = min(lower_wick_ratio, 1.0)
            return DetectedPattern(
                pattern_type=CandlePatternType.PIN_BAR_BULLISH,
                signal=PatternSignal.BULLISH,
                strength=strength,
                candle_index=index,
                description=f"Bullish Pin Bar: Strong lower rejection ({lower_wick_ratio:.1%})",
                metadata={
                    "wick_ratio": lower_wick_ratio,
                    "body_ratio": body_ratio,
                }
            )
        
        # Bearish Pin Bar: Long upper wick
        if upper_wick_ratio > 0.65 and upper_wick_ratio > (lower_wick_ratio * 3):
            strength = min(upper_wick_ratio, 1.0)
            return DetectedPattern(
                pattern_type=CandlePatternType.PIN_BAR_BEARISH,
                signal=PatternSignal.BEARISH,
                strength=strength,
                candle_index=index,
                description=f"Bearish Pin Bar: Strong upper rejection ({upper_wick_ratio:.1%})",
                metadata={
                    "wick_ratio": upper_wick_ratio,
                    "body_ratio": body_ratio,
                }
            )
        
        return None
    
    def _detect_strong_directional(
        self, candle: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect strong directional candles - momentum indicators.
        
        Characteristics:
        - Large body (>70% of range)
        - Minimal wicks
        - Strong momentum
        """
        if candle.total_range == 0:
            return None
        
        body_ratio = candle.body_size / candle.total_range
        
        if body_ratio > 0.7:
            signal = PatternSignal.BULLISH if candle.is_bullish else PatternSignal.BEARISH
            strength = min(body_ratio, 1.0)
            
            pattern_type = (
                CandlePatternType.STRONG_BULLISH if candle.is_bullish
                else CandlePatternType.STRONG_BEARISH
            )
            
            return DetectedPattern(
                pattern_type=pattern_type,
                signal=signal,
                strength=strength,
                candle_index=index,
                description=f"Strong {signal} candle: {body_ratio:.1%} body",
                metadata={
                    "body_ratio": body_ratio,
                }
            )
        
        return None
    
    def _detect_inside_outside_bar(
        self, previous: Candle, current: Candle, index: int
    ) -> Optional[DetectedPattern]:
        """Detect Inside and Outside bars.
        
        Inside Bar: Current candle's range is within previous candle's range
        Outside Bar: Current candle's range engulfs previous candle's range
        """
        # Inside Bar: consolidation pattern
        if current.high <= previous.high and current.low >= previous.low:
            # Strength based on how much smaller the inside bar is
            size_ratio = current.total_range / previous.total_range if previous.total_range > 0 else 0
            strength = 1.0 - size_ratio  # Smaller inside bar = stronger pattern
            
            return DetectedPattern(
                pattern_type=CandlePatternType.INSIDE_BAR,
                signal=PatternSignal.NEUTRAL,
                strength=strength,
                candle_index=index,
                description=f"Inside Bar: Consolidation, {size_ratio:.1%} of previous range",
                metadata={
                    "size_ratio": size_ratio,
                    "previous_range": previous.total_range,
                    "current_range": current.total_range,
                }
            )
        
        # Outside Bar: expansion/breakout pattern
        if current.high > previous.high and current.low < previous.low:
            size_ratio = current.total_range / previous.total_range if previous.total_range > 0 else 0
            strength = min(size_ratio / 2.0, 1.0)  # Cap at 1.0
            
            signal = PatternSignal.BULLISH if current.is_bullish else PatternSignal.BEARISH
            
            return DetectedPattern(
                pattern_type=CandlePatternType.OUTSIDE_BAR,
                signal=signal,
                strength=strength,
                candle_index=index,
                description=f"Outside Bar: Expansion, {size_ratio:.1%} of previous range",
                metadata={
                    "size_ratio": size_ratio,
                    "previous_range": previous.total_range,
                    "current_range": current.total_range,
                }
            )
        
        return None
    
    def get_patterns_at_index(
        self, candles: List[Candle], index: int
    ) -> List[DetectedPattern]:
        """Get all patterns detected at a specific candle index.
        
        Useful for real-time pattern detection as new candles form.
        
        Args:
            candles: List of candles
            index: Index to check for patterns
            
        Returns:
            List of patterns detected at that index
        """
        all_patterns = self.detect_all_patterns(candles)
        return [p for p in all_patterns if p.candle_index == index]
    
    def filter_patterns(
        self,
        patterns: List[DetectedPattern],
        min_strength: float = 0.0,
        pattern_types: Optional[List[CandlePatternType]] = None,
        signals: Optional[List[PatternSignal]] = None,
    ) -> List[DetectedPattern]:
        """Filter patterns by criteria.
        
        Args:
            patterns: List of patterns to filter
            min_strength: Minimum strength threshold (0.0 - 1.0)
            pattern_types: List of pattern types to include (None = all)
            signals: List of signals to include (None = all)
            
        Returns:
            Filtered list of patterns
        """
        filtered = patterns
        
        # Filter by strength
        filtered = [p for p in filtered if p.strength >= min_strength]
        
        # Filter by pattern type
        if pattern_types:
            filtered = [p for p in filtered if p.pattern_type in pattern_types]
        
        # Filter by signal
        if signals:
            filtered = [p for p in filtered if p.signal in signals]
        
        return filtered
