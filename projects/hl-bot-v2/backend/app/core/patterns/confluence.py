"""Multi-timeframe confluence scoring module.

Analyzes alignment of signals across multiple timeframes to determine
setup quality. Higher confluence = stronger trade setup.

Combines:
- Candle patterns across timeframes
- Market structure alignment (trend direction, BOS/CHoCH)
- Support/Resistance zone proximity
- Pattern strength and signal direction
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.core.market.data import Candle
from app.core.patterns.candles import (
    CandlePatternDetector,
    DetectedPattern,
    PatternSignal,
)
from app.core.patterns.structure import (
    MarketStructureAnalyzer,
    SwingPoint,
    StructureBreak,
    StructureBreakType,
)
from app.core.patterns.zones import (
    SupportResistanceDetector,
    SupportResistanceZone,
    ZoneType,
)


class TimeframeWeight(Enum):
    """Weight multipliers for different timeframes in confluence scoring."""
    HIGHER = 2.0  # Higher timeframes get more weight
    EQUAL = 1.5   # Equal to analysis timeframe
    LOWER = 1.0   # Lower timeframes get less weight


class ConfluenceSignal(Enum):
    """Overall directional signal from confluence analysis."""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


@dataclass
class TimeframeAnalysis:
    """Analysis results for a single timeframe.
    
    Contains all detected patterns, structure, and zones for one timeframe.
    """
    timeframe: str
    candles: List[Candle]
    patterns: List[DetectedPattern]
    swings: List[SwingPoint]
    structure_breaks: List[StructureBreak]
    zones: List[SupportResistanceZone]
    
    # Derived metrics
    trend_direction: Optional[PatternSignal] = None  # Overall trend
    recent_patterns: List[DetectedPattern] = None  # Last N candles
    active_zones: List[SupportResistanceZone] = None  # Zones near current price
    last_structure_break: Optional[StructureBreak] = None
    
    def __post_init__(self):
        """Calculate derived metrics after initialization."""
        if self.recent_patterns is None and self.patterns:
            # Get patterns from last 10 candles
            if self.candles:
                last_index = len(self.candles) - 1
                self.recent_patterns = [
                    p for p in self.patterns
                    if p.candle_index >= last_index - 10
                ]
        
        if self.active_zones is None and self.zones and self.candles:
            # Get zones near current price (within 5% distance)
            current_price = self.candles[-1].close
            self.active_zones = [
                z for z in self.zones
                if abs(z.distance_to_zone(current_price)) / current_price <= 0.05
            ]
        
        if self.last_structure_break is None and self.structure_breaks:
            self.last_structure_break = self.structure_breaks[-1]
    
    def get_pattern_signal_score(self) -> Tuple[PatternSignal, float]:
        """Calculate overall pattern signal and strength from recent patterns.
        
        Returns:
            Tuple of (signal, strength) where strength is 0.0-1.0
        """
        if not self.recent_patterns:
            return PatternSignal.NEUTRAL, 0.0
        
        # Weight patterns by strength and recency
        bullish_score = 0.0
        bearish_score = 0.0
        
        for pattern in self.recent_patterns:
            weight = pattern.strength
            
            if pattern.signal == PatternSignal.BULLISH:
                bullish_score += weight
            elif pattern.signal == PatternSignal.BEARISH:
                bearish_score += weight
        
        # Normalize by number of patterns
        total = bullish_score + bearish_score
        if total == 0:
            return PatternSignal.NEUTRAL, 0.0
        
        # Determine dominant signal
        if bullish_score > bearish_score * 1.5:
            return PatternSignal.BULLISH, bullish_score / len(self.recent_patterns)
        elif bearish_score > bullish_score * 1.5:
            return PatternSignal.BEARISH, bearish_score / len(self.recent_patterns)
        else:
            return PatternSignal.NEUTRAL, 0.5
    
    def get_structure_signal(self) -> Tuple[PatternSignal, float]:
        """Get signal from market structure analysis.
        
        Returns:
            Tuple of (signal, strength)
        """
        if not self.last_structure_break:
            return PatternSignal.NEUTRAL, 0.0
        
        break_type = self.last_structure_break.break_type
        significance = self.last_structure_break.significance
        
        # BOS in uptrend = bullish, in downtrend = bearish
        # CHoCH = potential reversal
        if break_type == StructureBreakType.BOS:
            # Determine trend from swing points
            if len(self.swings) >= 2:
                recent_swings = self.swings[-2:]
                if recent_swings[-1].price > recent_swings[0].price:
                    return PatternSignal.BULLISH, significance
                else:
                    return PatternSignal.BEARISH, significance
        elif break_type == StructureBreakType.CHOCH:
            # CHoCH suggests reversal - check which direction
            if len(self.swings) >= 1:
                last_swing = self.swings[-1]
                from app.core.patterns.structure import SwingType
                if last_swing.swing_type == SwingType.LOW:
                    return PatternSignal.BULLISH, significance * 0.8
                else:
                    return PatternSignal.BEARISH, significance * 0.8
        
        return PatternSignal.NEUTRAL, 0.0
    
    def get_zone_signal(self, current_price: float) -> Tuple[PatternSignal, float]:
        """Get signal from support/resistance zones.
        
        Args:
            current_price: Current market price
            
        Returns:
            Tuple of (signal, strength)
        """
        if not self.active_zones:
            return PatternSignal.NEUTRAL, 0.0
        
        # Find strongest zone near current price
        strongest_zone = max(self.active_zones, key=lambda z: z.calculate_strength_score())
        
        # Support zone = bullish, resistance = bearish
        if strongest_zone.zone_type == ZoneType.SUPPORT:
            # Check if price is near support
            if strongest_zone.contains_price(current_price, buffer=0.01):
                return PatternSignal.BULLISH, strongest_zone.calculate_strength_score()
        elif strongest_zone.zone_type == ZoneType.RESISTANCE:
            # Check if price is near resistance
            if strongest_zone.contains_price(current_price, buffer=0.01):
                return PatternSignal.BEARISH, strongest_zone.calculate_strength_score()
        
        return PatternSignal.NEUTRAL, 0.0


@dataclass
class ConfluenceScore:
    """Result of multi-timeframe confluence analysis.
    
    Provides overall score and breakdown by component.
    """
    overall_score: float  # 0.0 - 100.0
    signal: ConfluenceSignal
    
    # Component scores (0.0 - 1.0)
    pattern_alignment_score: float
    structure_alignment_score: float
    zone_alignment_score: float
    
    # Per-timeframe breakdown
    timeframe_scores: Dict[str, float]
    timeframe_signals: Dict[str, PatternSignal]
    
    # Details
    dominant_timeframe: str
    conflicting_timeframes: List[str]
    agreement_percentage: float  # % of timeframes agreeing on direction
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "overall_score": self.overall_score,
            "signal": self.signal.value,
            "pattern_alignment": self.pattern_alignment_score,
            "structure_alignment": self.structure_alignment_score,
            "zone_alignment": self.zone_alignment_score,
            "timeframe_scores": self.timeframe_scores,
            "timeframe_signals": {
                tf: sig.value for tf, sig in self.timeframe_signals.items()
            },
            "dominant_timeframe": self.dominant_timeframe,
            "conflicting_timeframes": self.conflicting_timeframes,
            "agreement_percentage": self.agreement_percentage,
        }


class MultiTimeframeConfluenceScorer:
    """Scores multi-timeframe alignment for trade setups.
    
    Analyzes multiple timeframes and calculates how well signals align
    across different time horizons. Higher confluence = higher probability setup.
    
    Example:
        >>> scorer = MultiTimeframeConfluenceScorer()
        >>> mtf_data = {
        ...     "5m": candles_5m,
        ...     "15m": candles_15m,
        ...     "1h": candles_1h,
        ... }
        >>> score = scorer.score_confluence(mtf_data, analysis_timeframe="15m")
        >>> print(f"Confluence: {score.overall_score:.1f}/100 - {score.signal.value}")
    """
    
    def __init__(
        self,
        pattern_detector: Optional[CandlePatternDetector] = None,
        structure_analyzer: Optional[MarketStructureAnalyzer] = None,
        zone_detector: Optional[SupportResistanceDetector] = None,
    ):
        """Initialize confluence scorer with optional custom analyzers.
        
        Args:
            pattern_detector: Custom candle pattern detector (uses default if None)
            structure_analyzer: Custom market structure analyzer (uses default if None)
            zone_detector: Custom S/R zone detector (uses default if None)
        """
        self.pattern_detector = pattern_detector or CandlePatternDetector()
        self.structure_analyzer = structure_analyzer or MarketStructureAnalyzer()
        self.zone_detector = zone_detector or SupportResistanceDetector()
    
    def analyze_timeframe(
        self,
        candles: List[Candle],
        timeframe: str,
    ) -> TimeframeAnalysis:
        """Analyze a single timeframe comprehensively.
        
        Args:
            candles: List of candles for this timeframe
            timeframe: Timeframe string (e.g., "5m", "1h")
            
        Returns:
            TimeframeAnalysis with all detected patterns and structure
        """
        # Detect all patterns
        patterns = self.pattern_detector.detect_all_patterns(candles)
        
        # Analyze market structure
        swings = self.structure_analyzer.find_swing_points(candles)
        structure_breaks = self.structure_analyzer.detect_structure_breaks(candles, swings)
        
        # Detect support/resistance zones
        zones = self.zone_detector.detect_zones(candles)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            candles=candles,
            patterns=patterns,
            swings=swings,
            structure_breaks=structure_breaks,
            zones=zones,
        )
    
    def score_confluence(
        self,
        multi_timeframe_data: Dict[str, List[Candle]],
        analysis_timeframe: str,
        timeframe_weights: Optional[Dict[str, float]] = None,
    ) -> ConfluenceScore:
        """Calculate multi-timeframe confluence score.
        
        Args:
            multi_timeframe_data: Dict mapping timeframe to list of candles
            analysis_timeframe: Primary timeframe for analysis (e.g., "15m")
            timeframe_weights: Optional custom weights per timeframe
            
        Returns:
            ConfluenceScore with overall score and breakdown
            
        Example:
            >>> mtf_data = {"5m": [...], "15m": [...], "1h": [...]}
            >>> score = scorer.score_confluence(mtf_data, "15m")
        """
        if not multi_timeframe_data:
            raise ValueError("multi_timeframe_data cannot be empty")
        
        if analysis_timeframe not in multi_timeframe_data:
            raise ValueError(f"analysis_timeframe '{analysis_timeframe}' not in data")
        
        # Analyze each timeframe
        analyses: Dict[str, TimeframeAnalysis] = {}
        for tf, candles in multi_timeframe_data.items():
            if candles:
                analyses[tf] = self.analyze_timeframe(candles, tf)
        
        if not analyses:
            raise ValueError("No valid timeframe data to analyze")
        
        # Get current price from analysis timeframe
        current_price = analyses[analysis_timeframe].candles[-1].close
        
        # Calculate component scores
        pattern_score = self._score_pattern_alignment(analyses, current_price)
        structure_score = self._score_structure_alignment(analyses)
        zone_score = self._score_zone_alignment(analyses, current_price)
        
        # Calculate per-timeframe scores with weights
        tf_scores, tf_signals = self._calculate_timeframe_scores(
            analyses, analysis_timeframe, timeframe_weights
        )
        
        # Calculate agreement metrics
        agreement_pct = self._calculate_agreement_percentage(tf_signals)
        conflicting = self._find_conflicting_timeframes(tf_signals)
        
        # Determine dominant timeframe (highest weighted score)
        dominant_tf = max(tf_scores.keys(), key=lambda tf: tf_scores[tf])
        
        # Calculate overall score (0-100)
        # Weight: patterns 40%, structure 35%, zones 25%
        overall = (
            pattern_score * 0.40 +
            structure_score * 0.35 +
            zone_score * 0.25
        ) * 100.0
        
        # Determine overall signal
        signal = self._determine_overall_signal(tf_signals, tf_scores, overall)
        
        return ConfluenceScore(
            overall_score=overall,
            signal=signal,
            pattern_alignment_score=pattern_score,
            structure_alignment_score=structure_score,
            zone_alignment_score=zone_score,
            timeframe_scores=tf_scores,
            timeframe_signals=tf_signals,
            dominant_timeframe=dominant_tf,
            conflicting_timeframes=conflicting,
            agreement_percentage=agreement_pct,
        )
    
    def _score_pattern_alignment(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        current_price: float,
    ) -> float:
        """Score how well candle patterns align across timeframes.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not analyses:
            return 0.0
        
        # Collect pattern signals from each timeframe
        signals = []
        for analysis in analyses.values():
            signal, strength = analysis.get_pattern_signal_score()
            if signal != PatternSignal.NEUTRAL:
                signals.append((signal, strength))
        
        if not signals:
            return 0.0
        
        # Calculate alignment - how many agree on direction
        bullish_strength = sum(s for sig, s in signals if sig == PatternSignal.BULLISH)
        bearish_strength = sum(s for sig, s in signals if sig == PatternSignal.BEARISH)
        
        total_strength = bullish_strength + bearish_strength
        if total_strength == 0:
            return 0.0
        
        # Alignment score based on dominant direction
        alignment = max(bullish_strength, bearish_strength) / total_strength
        
        # Average strength across aligned signals
        if bullish_strength > bearish_strength:
            avg_strength = bullish_strength / sum(1 for sig, _ in signals if sig == PatternSignal.BULLISH)
        else:
            avg_strength = bearish_strength / sum(1 for sig, _ in signals if sig == PatternSignal.BEARISH)
        
        # Combine alignment and strength
        return (alignment * 0.6 + avg_strength * 0.4)
    
    def _score_structure_alignment(
        self,
        analyses: Dict[str, TimeframeAnalysis],
    ) -> float:
        """Score market structure alignment across timeframes.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not analyses:
            return 0.0
        
        # Collect structure signals
        signals = []
        for analysis in analyses.values():
            signal, strength = analysis.get_structure_signal()
            if signal != PatternSignal.NEUTRAL:
                signals.append((signal, strength))
        
        if not signals:
            return 0.0
        
        # Calculate alignment
        bullish_count = sum(1 for sig, _ in signals if sig == PatternSignal.BULLISH)
        bearish_count = sum(1 for sig, _ in signals if sig == PatternSignal.BEARISH)
        
        total = len(signals)
        alignment = max(bullish_count, bearish_count) / total
        
        # Average significance of structure breaks
        avg_significance = sum(s for _, s in signals) / len(signals)
        
        return (alignment * 0.7 + avg_significance * 0.3)
    
    def _score_zone_alignment(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        current_price: float,
    ) -> float:
        """Score support/resistance zone alignment.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not analyses:
            return 0.0
        
        # Collect zone signals
        signals = []
        for analysis in analyses.values():
            signal, strength = analysis.get_zone_signal(current_price)
            if signal != PatternSignal.NEUTRAL and strength > 0:
                signals.append((signal, strength))
        
        if not signals:
            return 0.0
        
        # Calculate alignment
        bullish_count = sum(1 for sig, _ in signals if sig == PatternSignal.BULLISH)
        bearish_count = sum(1 for sig, _ in signals if sig == PatternSignal.BEARISH)
        
        if bullish_count + bearish_count == 0:
            return 0.0
        
        alignment = max(bullish_count, bearish_count) / (bullish_count + bearish_count)
        
        # Average zone strength
        avg_strength = sum(s for _, s in signals) / len(signals)
        
        return (alignment * 0.5 + avg_strength * 0.5)
    
    def _calculate_timeframe_scores(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        analysis_timeframe: str,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[Dict[str, float], Dict[str, PatternSignal]]:
        """Calculate individual scores and signals for each timeframe.
        
        Returns:
            Tuple of (scores_dict, signals_dict)
        """
        from app.core.market.data import get_timeframe_minutes
        
        scores = {}
        signals = {}
        
        analysis_minutes = get_timeframe_minutes(analysis_timeframe)
        
        for tf, analysis in analyses.items():
            current_price = analysis.candles[-1].close
            
            # Get component signals
            pattern_sig, pattern_str = analysis.get_pattern_signal_score()
            struct_sig, struct_str = analysis.get_structure_signal()
            zone_sig, zone_str = analysis.get_zone_signal(current_price)
            
            # Combine into timeframe score
            tf_score = (pattern_str * 0.4 + struct_str * 0.35 + zone_str * 0.25)
            
            # Apply timeframe weight
            if custom_weights and tf in custom_weights:
                weight = custom_weights[tf]
            else:
                # Auto-weight based on timeframe relative to analysis TF
                tf_minutes = get_timeframe_minutes(tf)
                if tf_minutes > analysis_minutes:
                    weight = TimeframeWeight.HIGHER.value
                elif tf_minutes == analysis_minutes:
                    weight = TimeframeWeight.EQUAL.value
                else:
                    weight = TimeframeWeight.LOWER.value
            
            scores[tf] = tf_score * weight
            
            # Determine dominant signal for this timeframe
            sig_scores = {
                pattern_sig: pattern_str,
                struct_sig: struct_str,
                zone_sig: zone_str,
            }
            dominant_sig = max(sig_scores.keys(), key=lambda s: sig_scores[s])
            signals[tf] = dominant_sig
        
        return scores, signals
    
    def _calculate_agreement_percentage(
        self,
        tf_signals: Dict[str, PatternSignal],
    ) -> float:
        """Calculate what percentage of timeframes agree on direction.
        
        Returns:
            Percentage from 0.0 to 100.0
        """
        if not tf_signals:
            return 0.0
        
        # Count bullish, bearish, neutral
        bullish = sum(1 for sig in tf_signals.values() if sig == PatternSignal.BULLISH)
        bearish = sum(1 for sig in tf_signals.values() if sig == PatternSignal.BEARISH)
        
        total = len(tf_signals)
        agreement = max(bullish, bearish) / total * 100.0
        
        return agreement
    
    def _find_conflicting_timeframes(
        self,
        tf_signals: Dict[str, PatternSignal],
    ) -> List[str]:
        """Find timeframes that conflict with the majority signal.
        
        Returns:
            List of conflicting timeframe strings
        """
        if not tf_signals:
            return []
        
        # Determine majority signal
        bullish = sum(1 for sig in tf_signals.values() if sig == PatternSignal.BULLISH)
        bearish = sum(1 for sig in tf_signals.values() if sig == PatternSignal.BEARISH)
        
        if bullish > bearish:
            majority = PatternSignal.BULLISH
        elif bearish > bullish:
            majority = PatternSignal.BEARISH
        else:
            # No clear majority
            return []
        
        # Find conflicting timeframes
        conflicting = [
            tf for tf, sig in tf_signals.items()
            if sig != PatternSignal.NEUTRAL and sig != majority
        ]
        
        return conflicting
    
    def _determine_overall_signal(
        self,
        tf_signals: Dict[str, PatternSignal],
        tf_scores: Dict[str, float],
        overall_score: float,
    ) -> ConfluenceSignal:
        """Determine the overall confluence signal.
        
        Args:
            tf_signals: Signal per timeframe
            tf_scores: Weighted score per timeframe
            overall_score: Overall confluence score (0-100)
            
        Returns:
            Overall ConfluenceSignal
        """
        # Calculate weighted bullish/bearish votes
        bullish_weight = sum(
            tf_scores[tf] for tf, sig in tf_signals.items()
            if sig == PatternSignal.BULLISH
        )
        bearish_weight = sum(
            tf_scores[tf] for tf, sig in tf_signals.items()
            if sig == PatternSignal.BEARISH
        )
        
        total_weight = bullish_weight + bearish_weight
        
        if total_weight == 0:
            return ConfluenceSignal.NEUTRAL
        
        # Determine signal based on weighted votes and score
        if bullish_weight > bearish_weight:
            ratio = bullish_weight / total_weight
            if ratio > 0.8 and overall_score > 70:
                return ConfluenceSignal.STRONG_BULLISH
            else:
                return ConfluenceSignal.BULLISH
        elif bearish_weight > bullish_weight:
            ratio = bearish_weight / total_weight
            if ratio > 0.8 and overall_score > 70:
                return ConfluenceSignal.STRONG_BEARISH
            else:
                return ConfluenceSignal.BEARISH
        else:
            return ConfluenceSignal.NEUTRAL


def score_confluence(
    multi_timeframe_data: Dict[str, List[Candle]],
    analysis_timeframe: str,
) -> ConfluenceScore:
    """Convenience function to score multi-timeframe confluence.
    
    Args:
        multi_timeframe_data: Dict mapping timeframe to candles
        analysis_timeframe: Primary analysis timeframe
        
    Returns:
        ConfluenceScore
        
    Example:
        >>> from app.core.patterns.confluence import score_confluence
        >>> mtf_data = {"5m": candles_5m, "15m": candles_15m, "1h": candles_1h}
        >>> score = score_confluence(mtf_data, "15m")
        >>> print(f"Score: {score.overall_score:.1f}/100")
    """
    scorer = MultiTimeframeConfluenceScorer()
    return scorer.score_confluence(multi_timeframe_data, analysis_timeframe)
