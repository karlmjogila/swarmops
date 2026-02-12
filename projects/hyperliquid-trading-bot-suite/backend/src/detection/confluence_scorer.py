"""
Confluence Scorer

Multi-timeframe confluence detection engine that combines signals from:
- Candle patterns (LE, small wick, steeper wick, celery)
- Market structure (trend, BOS, ChoCH, zones)
- Market cycle (drive, range, liquidity)

The scorer implements the core trading principle: Higher timeframe bias + Lower timeframe entry.
It aggregates signals across timeframes and generates high-confidence trade signals when
multiple indicators align.

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import numpy as np

from ..types import (
    CandleData, PatternDetection, MarketStructure, Timeframe, 
    OrderSide, MarketCycle, EntryType, PriceActionSnapshot
)

from .candle_patterns import CandlePatternDetector
from .market_structure import MarketStructureAnalyzer, TrendAnalysis
from .cycle_classifier import MarketCycleClassifier, CycleClassification


@dataclass
class TimeframeAnalysis:
    """Analysis results for a single timeframe."""
    
    timeframe: Timeframe
    timestamp: datetime
    
    # Pattern detections
    patterns: List[PatternDetection] = field(default_factory=list)
    strongest_pattern: Optional[PatternDetection] = None
    
    # Market structure
    market_structure: Optional[MarketStructure] = None
    trend_direction: Optional[OrderSide] = None
    trend_strength: float = 0.0
    
    # Cycle classification
    cycle: Optional[CycleClassification] = None
    market_cycle: Optional[MarketCycle] = None
    cycle_confidence: float = 0.0
    
    # Zone interactions
    near_support: bool = False
    near_resistance: bool = False
    zone_distance: float = 0.0  # Distance to nearest zone (%)
    
    # Momentum
    momentum_score: float = 0.0
    momentum_direction: Optional[OrderSide] = None


@dataclass
class ConfluenceScore:
    """Multi-timeframe confluence scoring result."""
    
    # Overall scoring
    total_score: float = 0.0  # 0.0 to 1.0
    confidence: float = 0.0  # 0.0 to 1.0
    signal_strength: float = 0.0  # 0.0 to 1.0
    
    # Directional bias
    bias_direction: Optional[OrderSide] = None
    bias_confidence: float = 0.0
    
    # Timeframe alignment
    timeframes_aligned: int = 0
    total_timeframes: int = 0
    alignment_percentage: float = 0.0
    
    # Component scores
    pattern_score: float = 0.0
    structure_score: float = 0.0
    cycle_score: float = 0.0
    zone_score: float = 0.0
    
    # Higher TF context
    higher_tf_bias: Optional[OrderSide] = None
    higher_tf_cycle: Optional[MarketCycle] = None
    higher_tf_strength: float = 0.0
    
    # Lower TF entry
    lower_tf_pattern: Optional[EntryType] = None
    lower_tf_confidence: float = 0.0
    entry_quality: float = 0.0
    
    # Signal generation
    generates_signal: bool = False
    signal_type: str = ""  # 'long', 'short', or ''
    entry_timeframe: Optional[Timeframe] = None
    
    # Timestamp and context
    timestamp: datetime = field(default_factory=datetime.utcnow)
    asset: str = ""
    
    # Detailed breakdown
    timeframe_analyses: Dict[str, TimeframeAnalysis] = field(default_factory=dict)
    confluence_factors: List[str] = field(default_factory=list)
    warning_factors: List[str] = field(default_factory=list)


@dataclass
class SignalGeneration:
    """Generated trading signal with full context."""
    
    id: str = ""
    asset: str = ""
    direction: OrderSide = OrderSide.LONG
    entry_type: EntryType = EntryType.LE
    
    # Confluence information
    confluence_score: ConfluenceScore = field(default_factory=ConfluenceScore)
    
    # Entry parameters
    entry_price: float = 0.0
    suggested_stop_loss: Optional[float] = None
    suggested_take_profits: List[float] = field(default_factory=list)
    risk_reward_ratio: float = 0.0
    
    # Context
    price_action_snapshot: Optional[PriceActionSnapshot] = None
    reasoning: str = ""
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    priority: float = 0.0  # 0.0 to 1.0


class ConfluenceScorer:
    """
    Multi-timeframe confluence detection and signal generation engine.
    
    This is the core integration point that combines all pattern detection,
    market structure analysis, and cycle classification to generate high-probability
    trade signals based on multi-timeframe confluence.
    """
    
    def __init__(self):
        """Initialize the confluence scorer with sub-detectors."""
        
        # Initialize component detectors
        self.pattern_detector = CandlePatternDetector()
        self.structure_analyzer = MarketStructureAnalyzer()
        self.cycle_classifier = MarketCycleClassifier()
        
        # Timeframe hierarchy (from higher to lower)
        self.timeframe_hierarchy = [
            Timeframe.H4,
            Timeframe.H1,
            Timeframe.M30,
            Timeframe.M15,
            Timeframe.M5,
        ]
        
        # Confluence scoring weights
        self.weights = {
            'pattern': 0.25,      # Pattern detection weight
            'structure': 0.30,    # Market structure weight
            'cycle': 0.25,        # Cycle classification weight
            'zone': 0.20,         # Zone interaction weight
        }
        
        # Signal generation thresholds
        self.min_confluence_score = 0.60  # Minimum total confluence to generate signal
        self.min_alignment_percentage = 0.60  # Minimum TF alignment (60%)
        self.min_pattern_confidence = 0.50  # Minimum pattern confidence for entry
        
        # Timeframe designation
        self.higher_timeframes = [Timeframe.H4, Timeframe.H1]
        self.lower_timeframes = [Timeframe.M30, Timeframe.M15, Timeframe.M5]
        
        # Zone proximity threshold (percentage)
        self.zone_proximity_threshold = 0.005  # 0.5% from zone
        
        # Minimum candles required for analysis (configurable)
        self.min_candles_for_analysis = 20  # Can be overridden for different strategies
    
    def analyze_asset(
        self,
        asset: str,
        candle_data: Dict[str, List[CandleData]],
        timeframes: Optional[List[Timeframe]] = None
    ) -> ConfluenceScore:
        """
        Analyze an asset across multiple timeframes for confluence.
        
        Args:
            asset: Trading pair symbol
            candle_data: Dictionary mapping timeframe strings to candle lists
            timeframes: Specific timeframes to analyze (None = use all available)
            
        Returns:
            ConfluenceScore with complete multi-timeframe analysis
        """
        
        # Determine timeframes to analyze
        if timeframes is None:
            timeframes = [tf for tf in self.timeframe_hierarchy 
                         if tf.value in candle_data and len(candle_data[tf.value]) > 0]
        
        if not timeframes:
            return ConfluenceScore(asset=asset)
        
        # Analyze each timeframe
        tf_analyses = {}
        for tf in timeframes:
            if tf.value in candle_data:
                candles = candle_data[tf.value]
                if len(candles) >= self.min_candles_for_analysis:  # Need minimum candles for analysis
                    tf_analyses[tf.value] = self._analyze_timeframe(
                        asset=asset,
                        timeframe=tf,
                        candles=candles
                    )
        
        if not tf_analyses:
            return ConfluenceScore(asset=asset)
        
        # Calculate confluence
        confluence = self._calculate_confluence(
            asset=asset,
            timeframe_analyses=tf_analyses,
            timeframes=timeframes
        )
        
        # Determine if signal should be generated
        confluence.generates_signal = self._should_generate_signal(confluence)
        
        if confluence.generates_signal:
            confluence.signal_type = (
                'long' if confluence.bias_direction == OrderSide.LONG
                else 'short' if confluence.bias_direction == OrderSide.SHORT
                else ''
            )
        
        return confluence
    
    def _analyze_timeframe(
        self,
        asset: str,
        timeframe: Timeframe,
        candles: List[CandleData]
    ) -> TimeframeAnalysis:
        """Analyze a single timeframe comprehensively."""
        
        analysis = TimeframeAnalysis(
            timeframe=timeframe,
            timestamp=candles[-1].timestamp if candles else datetime.utcnow()
        )
        
        if len(candles) < self.min_candles_for_analysis:
            return analysis
        
        # 1. Detect candle patterns
        patterns = self.pattern_detector.detect_patterns(
            candles=candles,
            asset=asset,
            timeframe=timeframe
        )
        analysis.patterns = patterns
        
        # Find strongest pattern at current candle
        if patterns:
            current_patterns = [p for p in patterns if p.candle_index >= len(candles) - 3]
            if current_patterns:
                analysis.strongest_pattern = max(
                    current_patterns, 
                    key=lambda p: p.confidence
                )
        
        # 2. Analyze market structure
        market_structure = self.structure_analyzer.analyze_structure(
            candles=candles,
            asset=asset,
            timeframe=timeframe
        )
        analysis.market_structure = market_structure
        analysis.trend_direction = market_structure.trend_direction
        analysis.trend_strength = market_structure.trend_strength
        
        # 3. Classify market cycle
        cycle_classification = self.cycle_classifier.classify_cycle(
            candles=candles,
            timeframe=timeframe
        )
        analysis.cycle = cycle_classification
        analysis.market_cycle = cycle_classification.cycle
        analysis.cycle_confidence = cycle_classification.confidence
        
        # 4. Check zone proximity
        current_price = candles[-1].close
        analysis.near_support, analysis.near_resistance, analysis.zone_distance = \
            self._check_zone_proximity(current_price, market_structure)
        
        # 5. Calculate momentum
        analysis.momentum_score, analysis.momentum_direction = \
            self._calculate_momentum(candles)
        
        return analysis
    
    def _check_zone_proximity(
        self,
        current_price: float,
        structure: MarketStructure
    ) -> Tuple[bool, bool, float]:
        """Check if price is near support or resistance zones."""
        
        near_support = False
        near_resistance = False
        min_distance = float('inf')
        
        # Check support zones
        for zone in structure.support_zones:
            if zone.get('active', True):
                zone_price = zone.get('price_level', 0)
                distance = abs(current_price - zone_price) / current_price
                min_distance = min(min_distance, distance)
                
                if distance <= self.zone_proximity_threshold:
                    near_support = True
        
        # Check resistance zones
        for zone in structure.resistance_zones:
            if zone.get('active', True):
                zone_price = zone.get('price_level', 0)
                distance = abs(current_price - zone_price) / current_price
                min_distance = min(min_distance, distance)
                
                if distance <= self.zone_proximity_threshold:
                    near_resistance = True
        
        return near_support, near_resistance, min_distance
    
    def _calculate_momentum(
        self,
        candles: List[CandleData]
    ) -> Tuple[float, Optional[OrderSide]]:
        """Calculate momentum score and direction."""
        
        if len(candles) < 10:
            return 0.0, None
        
        # Simple momentum: price change over last N candles
        recent_candles = candles[-10:]
        price_change = recent_candles[-1].close - recent_candles[0].close
        avg_price = np.mean([c.close for c in recent_candles])
        
        momentum_score = price_change / avg_price
        
        # Normalize to -1 to 1 range
        momentum_score = np.clip(momentum_score * 100, -1.0, 1.0)
        
        # Determine direction
        if momentum_score > 0.1:
            direction = OrderSide.LONG
        elif momentum_score < -0.1:
            direction = OrderSide.SHORT
        else:
            direction = None
        
        return float(momentum_score), direction
    
    def _calculate_confluence(
        self,
        asset: str,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        timeframes: List[Timeframe]
    ) -> ConfluenceScore:
        """Calculate comprehensive confluence score."""
        
        score = ConfluenceScore(
            asset=asset,
            total_timeframes=len(timeframes),
            timeframe_analyses=timeframe_analyses
        )
        
        # 1. Determine higher TF bias
        score.higher_tf_bias, score.higher_tf_strength, score.higher_tf_cycle = \
            self._determine_higher_tf_bias(timeframe_analyses)
        
        # 2. Validate lower TF entry
        score.lower_tf_pattern, score.lower_tf_confidence, score.entry_timeframe = \
            self._find_lower_tf_entry(timeframe_analyses)
        
        # 3. Calculate component scores
        score.pattern_score = self._score_patterns(timeframe_analyses, score.higher_tf_bias)
        score.structure_score = self._score_structure(timeframe_analyses, score.higher_tf_bias)
        score.cycle_score = self._score_cycles(timeframe_analyses, score.higher_tf_bias)
        score.zone_score = self._score_zones(timeframe_analyses, score.higher_tf_bias)
        
        # 4. Calculate weighted total score
        score.total_score = (
            self.weights['pattern'] * score.pattern_score +
            self.weights['structure'] * score.structure_score +
            self.weights['cycle'] * score.cycle_score +
            self.weights['zone'] * score.zone_score
        )
        
        # 5. Calculate alignment percentage
        score.timeframes_aligned = self._count_aligned_timeframes(
            timeframe_analyses, score.higher_tf_bias
        )
        score.alignment_percentage = (
            score.timeframes_aligned / score.total_timeframes 
            if score.total_timeframes > 0 else 0.0
        )
        
        # 6. Calculate bias direction and confidence
        score.bias_direction = score.higher_tf_bias
        score.bias_confidence = score.higher_tf_strength
        
        # 7. Calculate overall confidence
        score.confidence = (
            score.total_score * 0.6 +
            score.alignment_percentage * 0.3 +
            score.bias_confidence * 0.1
        )
        
        # 8. Calculate signal strength
        score.signal_strength = (
            score.lower_tf_confidence * 0.4 +
            score.total_score * 0.4 +
            score.alignment_percentage * 0.2
        )
        
        # 9. Entry quality
        score.entry_quality = score.lower_tf_confidence
        
        # 10. Identify confluence factors
        score.confluence_factors = self._identify_confluence_factors(
            timeframe_analyses, score
        )
        score.warning_factors = self._identify_warning_factors(
            timeframe_analyses, score
        )
        
        return score
    
    def _determine_higher_tf_bias(
        self,
        analyses: Dict[str, TimeframeAnalysis]
    ) -> Tuple[Optional[OrderSide], float, Optional[MarketCycle]]:
        """Determine the higher timeframe directional bias."""
        
        # Focus on H4 and H1 for bias
        higher_tf_keys = [tf.value for tf in self.higher_timeframes]
        
        bias_votes = {OrderSide.LONG: 0.0, OrderSide.SHORT: 0.0}
        total_weight = 0.0
        cycles = []
        
        for tf_key in higher_tf_keys:
            if tf_key not in analyses:
                continue
            
            analysis = analyses[tf_key]
            weight = 2.0 if tf_key == Timeframe.H4.value else 1.0
            
            # Vote from trend direction
            if analysis.trend_direction:
                bias_votes[analysis.trend_direction] += weight * analysis.trend_strength
                total_weight += weight
            
            # Collect cycle info
            if analysis.market_cycle:
                cycles.append(analysis.market_cycle)
        
        if total_weight == 0:
            return None, 0.0, None
        
        # Determine bias
        long_score = bias_votes[OrderSide.LONG] / total_weight
        short_score = bias_votes[OrderSide.SHORT] / total_weight
        
        if long_score > short_score and long_score > 0.3:
            bias = OrderSide.LONG
            strength = long_score
        elif short_score > long_score and short_score > 0.3:
            bias = OrderSide.SHORT
            strength = short_score
        else:
            bias = None
            strength = 0.0
        
        # Dominant cycle
        dominant_cycle = max(set(cycles), key=cycles.count) if cycles else None
        
        return bias, float(strength), dominant_cycle
    
    def _find_lower_tf_entry(
        self,
        analyses: Dict[str, TimeframeAnalysis]
    ) -> Tuple[Optional[EntryType], float, Optional[Timeframe]]:
        """Find the best entry pattern on lower timeframes."""
        
        lower_tf_keys = [tf.value for tf in self.lower_timeframes]
        
        best_pattern = None
        best_confidence = 0.0
        best_timeframe = None
        
        for tf_key in lower_tf_keys:
            if tf_key not in analyses:
                continue
            
            analysis = analyses[tf_key]
            if analysis.strongest_pattern:
                pattern = analysis.strongest_pattern
                if pattern.confidence > best_confidence:
                    best_pattern = pattern.pattern_type
                    best_confidence = pattern.confidence
                    best_timeframe = Timeframe(tf_key)
        
        return best_pattern, best_confidence, best_timeframe
    
    def _score_patterns(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        bias: Optional[OrderSide]
    ) -> float:
        """Score pattern detections across timeframes."""
        
        total_score = 0.0
        count = 0
        
        for analysis in analyses.values():
            if analysis.strongest_pattern:
                pattern = analysis.strongest_pattern
                score = pattern.confidence
                
                # Bonus if pattern aligns with bias
                if bias and pattern.pattern_data.get('direction') == bias.value:
                    score *= 1.2
                
                total_score += min(score, 1.0)
                count += 1
        
        return total_score / count if count > 0 else 0.0
    
    def _score_structure(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        bias: Optional[OrderSide]
    ) -> float:
        """Score market structure alignment across timeframes."""
        
        total_score = 0.0
        count = 0
        
        for analysis in analyses.values():
            if analysis.trend_direction:
                score = analysis.trend_strength
                
                # Check alignment with bias
                if bias and analysis.trend_direction == bias:
                    score *= 1.3
                elif bias and analysis.trend_direction != bias:
                    score *= 0.5
                
                total_score += min(score, 1.0)
                count += 1
        
        return total_score / count if count > 0 else 0.0
    
    def _score_cycles(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        bias: Optional[OrderSide]
    ) -> float:
        """Score market cycle favorability."""
        
        total_score = 0.0
        count = 0
        
        for analysis in analyses.values():
            if analysis.market_cycle:
                cycle = analysis.market_cycle
                confidence = analysis.cycle_confidence
                
                # DRIVE cycles are most favorable for trend trading
                if cycle == MarketCycle.DRIVE:
                    score = confidence * 1.2
                elif cycle == MarketCycle.RANGE:
                    score = confidence * 0.7  # Lower score for range
                else:  # LIQUIDITY
                    score = confidence * 0.5  # Lowest for liquidity phase
                
                total_score += min(score, 1.0)
                count += 1
        
        return total_score / count if count > 0 else 0.0
    
    def _score_zones(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        bias: Optional[OrderSide]
    ) -> float:
        """Score zone interactions (support/resistance proximity)."""
        
        total_score = 0.0
        count = 0
        
        for analysis in analyses.values():
            # Being near a zone is good if it aligns with bias
            if bias == OrderSide.LONG and analysis.near_support:
                score = 0.8
            elif bias == OrderSide.SHORT and analysis.near_resistance:
                score = 0.8
            elif analysis.near_support or analysis.near_resistance:
                score = 0.3  # Near zone but not aligned
            else:
                # Not near any zone
                score = 0.5
            
            total_score += score
            count += 1
        
        return total_score / count if count > 0 else 0.0
    
    def _count_aligned_timeframes(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        bias: Optional[OrderSide]
    ) -> int:
        """Count how many timeframes align with the bias."""
        
        if not bias:
            return 0
        
        aligned = 0
        for analysis in analyses.values():
            if analysis.trend_direction == bias:
                aligned += 1
            elif analysis.momentum_direction == bias:
                aligned += 0.5  # Partial credit for momentum alignment
        
        return int(aligned)
    
    def _should_generate_signal(self, confluence: ConfluenceScore) -> bool:
        """Determine if confluence meets threshold for signal generation."""
        
        # Must have a bias direction
        if not confluence.bias_direction:
            return False
        
        # Must have a lower TF entry pattern
        if not confluence.lower_tf_pattern:
            return False
        
        # Check minimum thresholds
        if confluence.total_score < self.min_confluence_score:
            return False
        
        if confluence.alignment_percentage < self.min_alignment_percentage:
            return False
        
        if confluence.lower_tf_confidence < self.min_pattern_confidence:
            return False
        
        # All checks passed
        return True
    
    def _identify_confluence_factors(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        score: ConfluenceScore
    ) -> List[str]:
        """Identify what's creating confluence."""
        
        factors = []
        
        # Higher TF bias
        if score.higher_tf_bias:
            factors.append(
                f"Higher TF bias: {score.higher_tf_bias.value.upper()} "
                f"(strength: {score.higher_tf_strength:.2f})"
            )
        
        # Cycle alignment
        if score.higher_tf_cycle == MarketCycle.DRIVE:
            factors.append(f"Market in DRIVE phase (favorable for trends)")
        
        # Multi-TF alignment
        if score.alignment_percentage >= 0.75:
            factors.append(
                f"Strong multi-TF alignment ({score.timeframes_aligned}/"
                f"{score.total_timeframes} timeframes)"
            )
        
        # Entry pattern
        if score.lower_tf_pattern:
            factors.append(
                f"Entry pattern: {score.lower_tf_pattern.value.upper()} "
                f"on {score.entry_timeframe.value if score.entry_timeframe else 'N/A'} "
                f"(confidence: {score.lower_tf_confidence:.2f})"
            )
        
        # Zone interaction
        for analysis in analyses.values():
            if score.bias_direction == OrderSide.LONG and analysis.near_support:
                factors.append(f"Price near support on {analysis.timeframe.value}")
            elif score.bias_direction == OrderSide.SHORT and analysis.near_resistance:
                factors.append(f"Price near resistance on {analysis.timeframe.value}")
        
        return factors
    
    def _identify_warning_factors(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        score: ConfluenceScore
    ) -> List[str]:
        """Identify potential warning signs."""
        
        warnings = []
        
        # Low alignment
        if score.alignment_percentage < 0.50:
            warnings.append(
                f"Low timeframe alignment ({score.alignment_percentage:.0%})"
            )
        
        # Conflicting cycles
        cycles = [a.market_cycle for a in analyses.values() if a.market_cycle]
        if len(set(cycles)) > 1:
            warnings.append("Mixed market cycles across timeframes")
        
        # Range-bound market
        if score.higher_tf_cycle == MarketCycle.RANGE:
            warnings.append("Market in RANGE phase (lower trend probability)")
        
        # Liquidity phase
        if score.higher_tf_cycle == MarketCycle.LIQUIDITY:
            warnings.append("Market in LIQUIDITY phase (watch for stop hunts)")
        
        # Weak bias
        if score.higher_tf_strength < 0.4:
            warnings.append(f"Weak higher TF bias (strength: {score.higher_tf_strength:.2f})")
        
        # Conflicting trends
        trends = [a.trend_direction for a in analyses.values() if a.trend_direction]
        if len(trends) > 1:
            longs = trends.count(OrderSide.LONG)
            shorts = trends.count(OrderSide.SHORT)
            if abs(longs - shorts) <= 1:
                warnings.append("Conflicting trend directions across timeframes")
        
        return warnings
    
    def generate_signal(
        self,
        asset: str,
        candle_data: Dict[str, List[CandleData]],
        timeframes: Optional[List[Timeframe]] = None
    ) -> Optional[SignalGeneration]:
        """
        Generate a trading signal if confluence meets thresholds.
        
        Args:
            asset: Trading pair symbol
            candle_data: Dictionary mapping timeframe strings to candle lists
            timeframes: Specific timeframes to analyze
            
        Returns:
            SignalGeneration if signal should be taken, None otherwise
        """
        
        # Calculate confluence
        confluence = self.analyze_asset(asset, candle_data, timeframes)
        
        # Check if signal should be generated
        if not confluence.generates_signal:
            return None
        
        # Create signal
        signal = SignalGeneration(
            id=f"sig_{asset}_{int(datetime.utcnow().timestamp())}",
            asset=asset,
            direction=confluence.bias_direction,
            entry_type=confluence.lower_tf_pattern,
            confluence_score=confluence,
            generated_at=datetime.utcnow()
        )
        
        # Calculate entry parameters
        if confluence.entry_timeframe and confluence.entry_timeframe.value in candle_data:
            entry_candles = candle_data[confluence.entry_timeframe.value]
            if entry_candles:
                signal.entry_price = entry_candles[-1].close
                
                # Suggest stop loss and take profits
                signal.suggested_stop_loss, signal.suggested_take_profits = \
                    self._calculate_exit_levels(
                        entry_price=signal.entry_price,
                        direction=signal.direction,
                        timeframe_analyses=confluence.timeframe_analyses
                    )
                
                # Calculate risk/reward
                if signal.suggested_stop_loss and signal.suggested_take_profits:
                    risk = abs(signal.entry_price - signal.suggested_stop_loss)
                    reward = abs(signal.suggested_take_profits[0] - signal.entry_price)
                    signal.risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Create price action snapshot
        signal.price_action_snapshot = self._create_snapshot(
            asset=asset,
            candle_data=candle_data,
            confluence=confluence
        )
        
        # Generate reasoning
        signal.reasoning = self._generate_reasoning(confluence, signal)
        
        # Set priority based on signal strength
        signal.priority = confluence.signal_strength
        
        # Set expiration (signals expire after a few candles)
        if confluence.entry_timeframe:
            # Expire after 3 candles on entry timeframe
            expiry_minutes = {
                Timeframe.M5: 15,
                Timeframe.M15: 45,
                Timeframe.M30: 90,
                Timeframe.H1: 180,
                Timeframe.H4: 720,
            }.get(confluence.entry_timeframe, 60)
            
            signal.expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        return signal
    
    def _calculate_exit_levels(
        self,
        entry_price: float,
        direction: OrderSide,
        timeframe_analyses: Dict[str, TimeframeAnalysis]
    ) -> Tuple[Optional[float], List[float]]:
        """Calculate suggested stop loss and take profit levels."""
        
        # Find nearest structure point for stop loss
        stop_loss = None
        take_profits = []
        
        # Look for support/resistance zones
        for tf_key, analysis in timeframe_analyses.items():
            if not analysis.market_structure:
                continue
            
            structure = analysis.market_structure
            
            if direction == OrderSide.LONG:
                # Stop below nearest support
                for zone in structure.support_zones:
                    zone_price = zone.get('price_level', 0)
                    if zone_price < entry_price:
                        if stop_loss is None or zone_price > stop_loss:
                            stop_loss = zone_price * 0.998  # Slightly below zone
                
                # TP at resistance levels
                for zone in structure.resistance_zones:
                    zone_price = zone.get('price_level', 0)
                    if zone_price > entry_price:
                        take_profits.append(zone_price * 0.998)
            
            else:  # SHORT
                # Stop above nearest resistance
                for zone in structure.resistance_zones:
                    zone_price = zone.get('price_level', 0)
                    if zone_price > entry_price:
                        if stop_loss is None or zone_price < stop_loss:
                            stop_loss = zone_price * 1.002  # Slightly above zone
                
                # TP at support levels
                for zone in structure.support_zones:
                    zone_price = zone.get('price_level', 0)
                    if zone_price < entry_price:
                        take_profits.append(zone_price * 1.002)
        
        # Default stop loss if none found (1% from entry)
        if stop_loss is None:
            if direction == OrderSide.LONG:
                stop_loss = entry_price * 0.99
            else:
                stop_loss = entry_price * 1.01
        
        # Default take profits if none found (2R and 3R)
        if not take_profits:
            risk = abs(entry_price - stop_loss)
            if direction == OrderSide.LONG:
                take_profits = [
                    entry_price + risk * 2,
                    entry_price + risk * 3
                ]
            else:
                take_profits = [
                    entry_price - risk * 2,
                    entry_price - risk * 3
                ]
        else:
            # Sort and limit to top 2-3 levels
            if direction == OrderSide.LONG:
                take_profits = sorted(take_profits)[:3]
            else:
                take_profits = sorted(take_profits, reverse=True)[:3]
        
        return stop_loss, take_profits
    
    def _create_snapshot(
        self,
        asset: str,
        candle_data: Dict[str, List[CandleData]],
        confluence: ConfluenceScore
    ) -> PriceActionSnapshot:
        """Create a price action snapshot for the signal."""
        
        snapshot = PriceActionSnapshot(
            timestamp=datetime.utcnow(),
            market_cycle=confluence.higher_tf_cycle,
            confluence_score=confluence.total_score
        )
        
        # Add candle data for each timeframe
        for tf_key, candles in candle_data.items():
            if candles:
                # Include last 50 candles for context
                snapshot.add_timeframe_data(
                    Timeframe(tf_key),
                    candles[-50:]
                )
        
        # Add structure notes from confluence
        snapshot.structure_notes = confluence.confluence_factors
        
        # Add zone interactions
        for tf_key, analysis in confluence.timeframe_analyses.items():
            if analysis.near_support:
                snapshot.zone_interactions.append(
                    f"{tf_key}: Near support (distance: {analysis.zone_distance:.2%})"
                )
            if analysis.near_resistance:
                snapshot.zone_interactions.append(
                    f"{tf_key}: Near resistance (distance: {analysis.zone_distance:.2%})"
                )
        
        return snapshot
    
    def _generate_reasoning(
        self,
        confluence: ConfluenceScore,
        signal: SignalGeneration
    ) -> str:
        """Generate human-readable reasoning for the signal."""
        
        lines = []
        
        # Overall assessment
        lines.append(
            f"{'LONG' if signal.direction == OrderSide.LONG else 'SHORT'} signal on {signal.asset}"
        )
        lines.append(
            f"Confluence Score: {confluence.total_score:.2%} | "
            f"Confidence: {confluence.confidence:.2%} | "
            f"Signal Strength: {confluence.signal_strength:.2%}"
        )
        lines.append("")
        
        # Higher TF context
        if confluence.higher_tf_bias:
            lines.append(f"Higher TF Bias: {confluence.higher_tf_bias.value.upper()}")
            lines.append(f"  - Strength: {confluence.higher_tf_strength:.2%}")
            if confluence.higher_tf_cycle:
                lines.append(f"  - Cycle: {confluence.higher_tf_cycle.value.upper()}")
            lines.append("")
        
        # Entry pattern
        if confluence.lower_tf_pattern:
            lines.append(f"Entry Pattern: {confluence.lower_tf_pattern.value.upper()}")
            lines.append(f"  - Timeframe: {confluence.entry_timeframe.value if confluence.entry_timeframe else 'N/A'}")
            lines.append(f"  - Confidence: {confluence.lower_tf_confidence:.2%}")
            lines.append("")
        
        # Confluence factors
        if confluence.confluence_factors:
            lines.append("Confluence Factors:")
            for factor in confluence.confluence_factors:
                lines.append(f"  ✓ {factor}")
            lines.append("")
        
        # Warnings
        if confluence.warning_factors:
            lines.append("Warning Factors:")
            for warning in confluence.warning_factors:
                lines.append(f"  ⚠ {warning}")
            lines.append("")
        
        # Risk management
        if signal.suggested_stop_loss:
            lines.append(f"Entry: {signal.entry_price:.2f}")
            lines.append(f"Stop Loss: {signal.suggested_stop_loss:.2f}")
            if signal.suggested_take_profits:
                lines.append(f"Take Profits: {', '.join(f'{tp:.2f}' for tp in signal.suggested_take_profits)}")
            lines.append(f"Risk/Reward: {signal.risk_reward_ratio:.2f}R")
        
        return "\n".join(lines)


# Convenience function for quick signal generation
def generate_trading_signal(
    asset: str,
    candle_data: Dict[str, List[CandleData]],
    timeframes: Optional[List[Timeframe]] = None
) -> Optional[SignalGeneration]:
    """
    Convenience function to generate a trading signal.
    
    Args:
        asset: Trading pair symbol
        candle_data: Dictionary mapping timeframe strings to candle lists
        timeframes: Specific timeframes to analyze
        
    Returns:
        SignalGeneration if confluence is met, None otherwise
    """
    scorer = ConfluenceScorer()
    return scorer.generate_signal(asset, candle_data, timeframes)


__all__ = [
    'ConfluenceScorer',
    'ConfluenceScore',
    'TimeframeAnalysis',
    'SignalGeneration',
    'generate_trading_signal'
]
