"""
Market Cycle Classifier

Implements advanced market cycle phase detection to classify markets into:
- DRIVE: Strong momentum, trending price action
- RANGE: Consolidation, equilibrium, bounded price movement  
- LIQUIDITY: Stop hunts, sweeps, liquidity grabs

This classifier is essential for strategy selection and trade filtering, as different
patterns perform better in different market phases.

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import numpy as np

from ..types import (
    CandleData, MarketCycle, Timeframe, OrderSide
)


@dataclass
class CycleMetrics:
    """Metrics used for cycle classification."""
    
    # Momentum indicators
    momentum_score: float = 0.0  # -1.0 to 1.0
    momentum_acceleration: float = 0.0
    directional_strength: float = 0.0  # 0.0 to 1.0
    
    # Volatility indicators
    normalized_volatility: float = 0.0  # 0.0 to 1.0
    volatility_trend: float = 0.0  # increasing/decreasing
    price_dispersion: float = 0.0
    
    # Structure indicators
    higher_highs_count: int = 0
    lower_lows_count: int = 0
    structure_breaks: int = 0
    false_break_count: int = 0
    
    # Liquidity indicators
    wick_dominance: float = 0.0  # 0.0 to 1.0
    large_wick_count: int = 0
    sweep_count: int = 0
    reversal_candle_count: int = 0
    
    # Range indicators
    price_oscillations: int = 0
    mean_reversion_strength: float = 0.0
    range_tightness: float = 0.0  # How tight the range is
    
    # Volume indicators
    volume_trend: float = 0.0
    volume_spikes: int = 0


@dataclass
class CycleClassification:
    """Result of market cycle classification."""
    
    # Primary classification
    cycle: MarketCycle
    confidence: float  # 0.0 to 1.0
    
    # Secondary characteristics
    sub_phase: str = ""  # e.g., "early_drive", "mature_range", "multi_sweep"
    transition_probability: float = 0.0  # Likelihood of phase change
    
    # Cycle metrics
    metrics: CycleMetrics = field(default_factory=CycleMetrics)
    
    # Historical context
    current_duration_candles: int = 0
    previous_cycle: Optional[MarketCycle] = None
    cycle_change_timestamp: Optional[datetime] = None
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Additional insights
    dominant_bias: Optional[OrderSide] = None
    cycle_health: float = 0.0  # How "clean" the cycle is (1.0 = very clean)


@dataclass
class CycleHistory:
    """Tracks history of cycle classifications."""
    
    classifications: deque = field(default_factory=lambda: deque(maxlen=100))
    current_cycle: MarketCycle = MarketCycle.RANGE
    current_cycle_start: Optional[datetime] = None
    cycle_duration_candles: int = 0
    
    def add_classification(self, classification: CycleClassification):
        """Add a new classification to history."""
        # Check for cycle transition
        if classification.cycle != self.current_cycle:
            self.current_cycle = classification.cycle
            self.current_cycle_start = classification.timestamp
            self.cycle_duration_candles = 0
        else:
            self.cycle_duration_candles += 1
        
        self.classifications.append(classification)
    
    def get_recent_cycles(self, count: int = 5) -> List[MarketCycle]:
        """Get most recent cycle phases."""
        if not self.classifications:
            return []
        
        cycles = []
        last_cycle = None
        
        for clf in reversed(self.classifications):
            if clf.cycle != last_cycle:
                cycles.append(clf.cycle)
                last_cycle = clf.cycle
                if len(cycles) >= count:
                    break
        
        return cycles


class MarketCycleClassifier:
    """Advanced market cycle phase classifier."""
    
    def __init__(self):
        """Initialize classifier with default parameters."""
        
        # DRIVE phase thresholds
        self.drive_momentum_threshold = 0.65  # Minimum momentum for drive
        self.drive_directional_threshold = 0.70  # Minimum directional strength
        self.drive_min_structure_breaks = 2  # Minimum BOS events
        
        # RANGE phase thresholds
        self.range_volatility_max = 0.35  # Maximum volatility for range
        self.range_oscillation_min = 3  # Minimum oscillations
        self.range_mean_reversion_min = 0.60  # Minimum mean reversion strength
        
        # LIQUIDITY phase thresholds
        self.liquidity_wick_threshold = 0.60  # Wick dominance threshold
        self.liquidity_sweep_min = 2  # Minimum sweeps detected
        self.liquidity_false_break_min = 2  # Minimum false breaks
        
        # Analysis periods
        self.momentum_lookback = 10  # Candles for momentum calculation
        self.volatility_lookback = 20  # Candles for volatility
        self.structure_lookback = 30  # Candles for structure analysis
        self.liquidity_lookback = 15  # Candles for liquidity events
        
        # Transition detection
        self.transition_sensitivity = 0.70  # Confidence drop threshold for transitions
        self.min_cycle_duration = 5  # Minimum candles in a cycle phase
        
        # Cycle history
        self.history = CycleHistory()
    
    def classify(
        self,
        candles: List[CandleData],
        min_periods: int = 30
    ) -> CycleClassification:
        """
        Classify current market cycle phase.
        
        Args:
            candles: List of candle data in chronological order
            min_periods: Minimum number of candles required
            
        Returns:
            CycleClassification with detailed cycle analysis
        """
        if len(candles) < min_periods:
            return self._empty_classification()
        
        # Calculate all metrics
        metrics = self._calculate_metrics(candles)
        
        # Score each cycle type
        drive_score = self._score_drive_phase(metrics, candles)
        range_score = self._score_range_phase(metrics, candles)
        liquidity_score = self._score_liquidity_phase(metrics, candles)
        
        # Determine primary cycle
        scores = {
            MarketCycle.DRIVE: drive_score,
            MarketCycle.RANGE: range_score,
            MarketCycle.LIQUIDITY: liquidity_score
        }
        
        primary_cycle = max(scores, key=scores.get)
        confidence = scores[primary_cycle]
        
        # Apply cycle stability filter (prevent rapid switching)
        # But allow initial classification (when no history exists)
        if (self.history.cycle_duration_candles < self.min_cycle_duration and 
            len(self.history.classifications) > 0):
            # Require higher confidence to switch from current cycle
            if primary_cycle != self.history.current_cycle:
                required_confidence = 0.75
                if confidence < required_confidence:
                    primary_cycle = self.history.current_cycle
                    confidence = scores[primary_cycle]
        
        # Determine sub-phase
        sub_phase = self._determine_sub_phase(primary_cycle, metrics, candles)
        
        # Calculate transition probability
        transition_prob = self._calculate_transition_probability(scores, metrics)
        
        # Determine dominant bias
        dominant_bias = self._determine_bias(metrics, candles)
        
        # Calculate cycle health
        cycle_health = self._calculate_cycle_health(primary_cycle, metrics)
        
        # Build classification result
        classification = CycleClassification(
            cycle=primary_cycle,
            confidence=confidence,
            sub_phase=sub_phase,
            transition_probability=transition_prob,
            metrics=metrics,
            current_duration_candles=self.history.cycle_duration_candles,
            previous_cycle=self.history.current_cycle if self.history.classifications else None,
            timestamp=candles[-1].timestamp if candles else datetime.utcnow(),
            dominant_bias=dominant_bias,
            cycle_health=cycle_health
        )
        
        # Update history
        self.history.add_classification(classification)
        
        return classification
    
    def _calculate_metrics(self, candles: List[CandleData]) -> CycleMetrics:
        """Calculate comprehensive cycle metrics."""
        metrics = CycleMetrics()
        
        # Momentum metrics
        metrics.momentum_score = self._calculate_momentum(candles, self.momentum_lookback)
        metrics.momentum_acceleration = self._calculate_momentum_acceleration(candles)
        metrics.directional_strength = self._calculate_directional_strength(candles)
        
        # Volatility metrics
        metrics.normalized_volatility = self._calculate_normalized_volatility(candles)
        metrics.volatility_trend = self._calculate_volatility_trend(candles)
        metrics.price_dispersion = self._calculate_price_dispersion(candles)
        
        # Structure metrics
        structure_data = self._analyze_structure(candles)
        metrics.higher_highs_count = structure_data['higher_highs']
        metrics.lower_lows_count = structure_data['lower_lows']
        metrics.structure_breaks = structure_data['breaks']
        metrics.false_break_count = structure_data['false_breaks']
        
        # Liquidity metrics
        liquidity_data = self._analyze_liquidity_events(candles)
        metrics.wick_dominance = liquidity_data['wick_dominance']
        metrics.large_wick_count = liquidity_data['large_wicks']
        metrics.sweep_count = liquidity_data['sweeps']
        metrics.reversal_candle_count = liquidity_data['reversals']
        
        # Range metrics
        range_data = self._analyze_range_behavior(candles)
        metrics.price_oscillations = range_data['oscillations']
        metrics.mean_reversion_strength = range_data['mean_reversion']
        metrics.range_tightness = range_data['tightness']
        
        # Volume metrics
        volume_data = self._analyze_volume(candles)
        metrics.volume_trend = volume_data['trend']
        metrics.volume_spikes = volume_data['spikes']
        
        return metrics
    
    def _calculate_momentum(self, candles: List[CandleData], lookback: int) -> float:
        """Calculate momentum score (-1.0 to 1.0)."""
        if len(candles) < lookback:
            return 0.0
        
        recent = candles[-lookback:]
        
        # Calculate price rate of change
        start_price = recent[0].close
        end_price = recent[-1].close
        
        if start_price == 0:
            return 0.0
        
        roc = (end_price - start_price) / start_price
        
        # Normalize to -1 to 1 (assume 5% move = max momentum)
        normalized = np.clip(roc / 0.05, -1.0, 1.0)
        
        # Apply EMA weighting (more recent candles = higher weight)
        weights = np.exp(np.linspace(-1, 0, len(recent)))
        weighted_changes = []
        
        for i in range(1, len(recent)):
            change = (recent[i].close - recent[i-1].close) / recent[i-1].close
            weighted_changes.append(change * weights[i])
        
        if weighted_changes:
            weighted_momentum = np.sum(weighted_changes) / 0.05
            # Blend raw and weighted momentum
            return (normalized * 0.4 + np.clip(weighted_momentum, -1.0, 1.0) * 0.6)
        
        return normalized
    
    def _calculate_momentum_acceleration(self, candles: List[CandleData]) -> float:
        """Calculate rate of change of momentum."""
        if len(candles) < 20:
            return 0.0
        
        # Calculate momentum at two different points
        recent_momentum = self._calculate_momentum(candles[-10:], 10)
        older_momentum = self._calculate_momentum(candles[-20:-10], 10)
        
        # Acceleration is the difference
        return recent_momentum - older_momentum
    
    def _calculate_directional_strength(self, candles: List[CandleData]) -> float:
        """Calculate directional strength (0.0 to 1.0)."""
        if len(candles) < self.momentum_lookback:
            return 0.0
        
        recent = candles[-self.momentum_lookback:]
        
        # Count directional candles
        bullish = sum(1 for c in recent if c.is_bullish)
        bearish = sum(1 for c in recent if c.is_bearish)
        total = len(recent)
        
        # Directional consistency
        consistency = max(bullish, bearish) / total if total > 0 else 0.0
        
        # Average body size (indicates conviction)
        avg_body_ratio = np.mean([
            c.body_size / c.total_range if c.total_range > 0 else 0.0
            for c in recent
        ])
        
        # Combine metrics
        return (consistency * 0.6 + avg_body_ratio * 0.4)
    
    def _calculate_normalized_volatility(self, candles: List[CandleData]) -> float:
        """Calculate normalized volatility (0.0 to 1.0)."""
        if len(candles) < self.volatility_lookback:
            return 0.0
        
        recent = candles[-self.volatility_lookback:]
        
        # Calculate ATR (Average True Range)
        true_ranges = []
        for i in range(1, len(recent)):
            tr = max(
                recent[i].high - recent[i].low,
                abs(recent[i].high - recent[i-1].close),
                abs(recent[i].low - recent[i-1].close)
            )
            true_ranges.append(tr)
        
        if not true_ranges:
            return 0.0
        
        atr = np.mean(true_ranges)
        avg_price = np.mean([c.close for c in recent])
        
        if avg_price == 0:
            return 0.0
        
        # Normalize ATR by price
        normalized_atr = (atr / avg_price) * 100  # As percentage
        
        # Scale to 0-1 (assume 2% ATR = high volatility)
        return np.clip(normalized_atr / 2.0, 0.0, 1.0)
    
    def _calculate_volatility_trend(self, candles: List[CandleData]) -> float:
        """Calculate if volatility is increasing or decreasing."""
        if len(candles) < self.volatility_lookback * 2:
            return 0.0
        
        # Split into two periods
        mid_point = len(candles) - self.volatility_lookback
        older_period = candles[mid_point - self.volatility_lookback:mid_point]
        recent_period = candles[-self.volatility_lookback:]
        
        # Calculate volatility for each period
        def period_volatility(period):
            ranges = [c.total_range for c in period]
            return np.std(ranges) if ranges else 0.0
        
        older_vol = period_volatility(older_period)
        recent_vol = period_volatility(recent_period)
        
        if older_vol == 0:
            return 0.0
        
        # Return rate of change
        return (recent_vol - older_vol) / older_vol
    
    def _calculate_price_dispersion(self, candles: List[CandleData]) -> float:
        """Calculate how dispersed prices are from the mean."""
        if len(candles) < self.volatility_lookback:
            return 0.0
        
        recent = candles[-self.volatility_lookback:]
        closes = [c.close for c in recent]
        
        mean_price = np.mean(closes)
        std_price = np.std(closes)
        
        if mean_price == 0:
            return 0.0
        
        # Coefficient of variation
        cv = (std_price / mean_price) * 100
        
        # Normalize to 0-1
        return np.clip(cv / 2.0, 0.0, 1.0)
    
    def _analyze_structure(self, candles: List[CandleData]) -> Dict[str, int]:
        """Analyze market structure for HH/LL and breaks."""
        if len(candles) < self.structure_lookback:
            return {
                'higher_highs': 0,
                'lower_lows': 0,
                'breaks': 0,
                'false_breaks': 0
            }
        
        recent = candles[-self.structure_lookback:]
        
        # Simple swing detection (3-candle pattern)
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(recent) - 2):
            # Swing high: higher than 2 candles on each side
            if (recent[i].high > recent[i-1].high and 
                recent[i].high > recent[i-2].high and
                recent[i].high > recent[i+1].high and 
                recent[i].high > recent[i+2].high):
                swing_highs.append((i, recent[i].high))
            
            # Swing low: lower than 2 candles on each side
            if (recent[i].low < recent[i-1].low and 
                recent[i].low < recent[i-2].low and
                recent[i].low < recent[i+1].low and 
                recent[i].low < recent[i+2].low):
                swing_lows.append((i, recent[i].low))
        
        # Count higher highs and lower lows
        higher_highs = 0
        for i in range(1, len(swing_highs)):
            if swing_highs[i][1] > swing_highs[i-1][1]:
                higher_highs += 1
        
        lower_lows = 0
        for i in range(1, len(swing_lows)):
            if swing_lows[i][1] < swing_lows[i-1][1]:
                lower_lows += 1
        
        # Count structure breaks (price breaking significant levels)
        breaks = 0
        false_breaks = 0
        
        if swing_highs:
            for idx, high in swing_highs[:-1]:  # Don't include most recent
                # Check if broken by subsequent candles
                for future_candle in recent[idx+1:]:
                    if future_candle.close > high:
                        breaks += 1
                        # Check if it was false break (reversed quickly)
                        next_candles = recent[idx+2:idx+7] if idx+7 < len(recent) else recent[idx+2:]
                        if any(c.close < high for c in next_candles):
                            false_breaks += 1
                        break
        
        return {
            'higher_highs': higher_highs,
            'lower_lows': lower_lows,
            'breaks': breaks,
            'false_breaks': false_breaks
        }
    
    def _analyze_liquidity_events(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Analyze liquidity events (wicks, sweeps, reversals)."""
        if len(candles) < self.liquidity_lookback:
            return {
                'wick_dominance': 0.0,
                'large_wicks': 0,
                'sweeps': 0,
                'reversals': 0
            }
        
        recent = candles[-self.liquidity_lookback:]
        
        # Calculate wick dominance
        total_wick_ratio = 0.0
        large_wick_count = 0
        
        for candle in recent:
            if candle.total_range > 0:
                wick_ratio = (candle.upper_wick + candle.lower_wick) / candle.total_range
                total_wick_ratio += wick_ratio
                
                # Large wick = wick > 50% of range
                if max(candle.upper_wick, candle.lower_wick) / candle.total_range > 0.5:
                    large_wick_count += 1
        
        wick_dominance = total_wick_ratio / len(recent) if recent else 0.0
        
        # Detect sweeps (candle wicks beyond previous high/low then closes back)
        sweep_count = 0
        
        for i in range(2, len(recent)):
            current = recent[i]
            prev_high = max(recent[i-1].high, recent[i-2].high)
            prev_low = min(recent[i-1].low, recent[i-2].low)
            
            # Bullish sweep: wicks below previous low but closes above
            if current.low < prev_low and current.close > prev_low:
                sweep_count += 1
            
            # Bearish sweep: wicks above previous high but closes below
            if current.high > prev_high and current.close < prev_high:
                sweep_count += 1
        
        # Count reversal candles (large wicks + opposite body)
        reversal_count = 0
        
        for i in range(1, len(recent)):
            current = recent[i]
            prev = recent[i-1]
            
            if current.total_range == 0:
                continue
            
            # Bullish reversal: bearish trend, large lower wick, bullish close
            if (prev.is_bearish and 
                current.lower_wick / current.total_range > 0.5 and 
                current.is_bullish):
                reversal_count += 1
            
            # Bearish reversal: bullish trend, large upper wick, bearish close
            if (prev.is_bullish and 
                current.upper_wick / current.total_range > 0.5 and 
                current.is_bearish):
                reversal_count += 1
        
        return {
            'wick_dominance': wick_dominance,
            'large_wicks': large_wick_count,
            'sweeps': sweep_count,
            'reversals': reversal_count
        }
    
    def _analyze_range_behavior(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Analyze range-bound behavior characteristics."""
        if len(candles) < self.volatility_lookback:
            return {
                'oscillations': 0,
                'mean_reversion': 0.0,
                'tightness': 0.0
            }
        
        recent = candles[-self.volatility_lookback:]
        closes = np.array([c.close for c in recent])
        
        # Calculate mean price
        mean_price = np.mean(closes)
        
        # Count oscillations around mean
        oscillations = 0
        for i in range(1, len(closes)):
            # Price crosses mean
            if (closes[i-1] < mean_price <= closes[i]) or (closes[i-1] > mean_price >= closes[i]):
                oscillations += 1
        
        # Calculate mean reversion strength
        # (how often price returns to mean after deviation)
        deviations = closes - mean_price
        mean_reversion_events = 0
        
        for i in range(1, len(deviations) - 1):
            # If price deviates then moves back toward mean
            if abs(deviations[i]) > abs(deviations[i+1]):
                if (deviations[i] > 0 and deviations[i+1] >= 0) or \
                   (deviations[i] < 0 and deviations[i+1] <= 0):
                    mean_reversion_events += 1
        
        mean_reversion_strength = mean_reversion_events / len(deviations) if len(deviations) > 0 else 0.0
        
        # Calculate range tightness
        price_range = np.max(closes) - np.min(closes)
        if mean_price > 0:
            range_pct = (price_range / mean_price) * 100
            # Tighter range = higher score (inverse relationship)
            tightness = max(0.0, 1.0 - (range_pct / 3.0))  # 3% range = 0 tightness
        else:
            tightness = 0.0
        
        return {
            'oscillations': oscillations,
            'mean_reversion': mean_reversion_strength,
            'tightness': tightness
        }
    
    def _analyze_volume(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Analyze volume characteristics."""
        if len(candles) < self.volatility_lookback:
            return {
                'trend': 0.0,
                'spikes': 0
            }
        
        recent = candles[-self.volatility_lookback:]
        volumes = np.array([c.volume for c in recent])
        
        if len(volumes) == 0:
            return {'trend': 0.0, 'spikes': 0}
        
        # Calculate volume trend using linear regression slope
        x = np.arange(len(volumes))
        if len(x) > 1:
            slope = np.polyfit(x, volumes, 1)[0]
            avg_volume = np.mean(volumes)
            volume_trend = slope / avg_volume if avg_volume > 0 else 0.0
        else:
            volume_trend = 0.0
        
        # Count volume spikes (>2x average)
        avg_volume = np.mean(volumes)
        spike_count = np.sum(volumes > avg_volume * 2.0)
        
        return {
            'trend': float(volume_trend),
            'spikes': int(spike_count)
        }
    
    def _score_drive_phase(self, metrics: CycleMetrics, candles: List[CandleData]) -> float:
        """Score likelihood of DRIVE phase (0.0 to 1.0)."""
        score = 0.0
        
        # Strong momentum (40% weight)
        if abs(metrics.momentum_score) > self.drive_momentum_threshold:
            momentum_factor = (abs(metrics.momentum_score) - self.drive_momentum_threshold) / (1.0 - self.drive_momentum_threshold)
            score += momentum_factor * 0.40
        
        # High directional strength (25% weight)
        if metrics.directional_strength > self.drive_directional_threshold:
            directional_factor = (metrics.directional_strength - self.drive_directional_threshold) / (1.0 - self.drive_directional_threshold)
            score += directional_factor * 0.25
        
        # Structure breaks indicating trend (15% weight)
        if metrics.structure_breaks >= self.drive_min_structure_breaks:
            breaks_factor = min(metrics.structure_breaks / 5.0, 1.0)
            score += breaks_factor * 0.15
        
        # Higher highs or lower lows (10% weight)
        structure_alignment = max(metrics.higher_highs_count, metrics.lower_lows_count)
        if structure_alignment > 0:
            structure_factor = min(structure_alignment / 4.0, 1.0)
            score += structure_factor * 0.10
        
        # Positive momentum acceleration (10% weight)
        if abs(metrics.momentum_acceleration) > 0.2:
            acceleration_factor = min(abs(metrics.momentum_acceleration) / 0.5, 1.0)
            score += acceleration_factor * 0.10
        
        return min(score, 1.0)
    
    def _score_range_phase(self, metrics: CycleMetrics, candles: List[CandleData]) -> float:
        """Score likelihood of RANGE phase (0.0 to 1.0)."""
        score = 0.0
        
        # Low volatility (30% weight)
        if metrics.normalized_volatility < self.range_volatility_max:
            vol_factor = 1.0 - (metrics.normalized_volatility / self.range_volatility_max)
            score += vol_factor * 0.30
        
        # Mean reversion strength (25% weight)
        if metrics.mean_reversion_strength > self.range_mean_reversion_min:
            reversion_factor = (metrics.mean_reversion_strength - self.range_mean_reversion_min) / (1.0 - self.range_mean_reversion_min)
            score += reversion_factor * 0.25
        
        # Price oscillations (20% weight)
        if metrics.price_oscillations >= self.range_oscillation_min:
            oscillation_factor = min(metrics.price_oscillations / 8.0, 1.0)
            score += oscillation_factor * 0.20
        
        # Range tightness (15% weight)
        score += metrics.range_tightness * 0.15
        
        # Low momentum (10% weight)
        low_momentum_factor = 1.0 - abs(metrics.momentum_score)
        score += low_momentum_factor * 0.10
        
        return min(score, 1.0)
    
    def _score_liquidity_phase(self, metrics: CycleMetrics, candles: List[CandleData]) -> float:
        """Score likelihood of LIQUIDITY phase (0.0 to 1.0)."""
        score = 0.0
        
        # High wick dominance (30% weight)
        if metrics.wick_dominance > self.liquidity_wick_threshold:
            wick_factor = (metrics.wick_dominance - self.liquidity_wick_threshold) / (1.0 - self.liquidity_wick_threshold)
            score += wick_factor * 0.30
        
        # Sweep events (25% weight)
        if metrics.sweep_count >= self.liquidity_sweep_min:
            sweep_factor = min(metrics.sweep_count / 5.0, 1.0)
            score += sweep_factor * 0.25
        
        # False breaks (20% weight)
        if metrics.false_break_count >= self.liquidity_false_break_min:
            false_break_factor = min(metrics.false_break_count / 4.0, 1.0)
            score += false_break_factor * 0.20
        
        # Reversal candles (15% weight)
        if metrics.reversal_candle_count > 0:
            reversal_factor = min(metrics.reversal_candle_count / 4.0, 1.0)
            score += reversal_factor * 0.15
        
        # Large wicks (10% weight)
        if metrics.large_wick_count > 0:
            large_wick_factor = min(metrics.large_wick_count / 5.0, 1.0)
            score += large_wick_factor * 0.10
        
        return min(score, 1.0)
    
    def _determine_sub_phase(self, cycle: MarketCycle, metrics: CycleMetrics, candles: List[CandleData]) -> str:
        """Determine sub-phase within the main cycle."""
        if cycle == MarketCycle.DRIVE:
            # Check momentum strength
            if abs(metrics.momentum_score) > 0.85:
                return "strong_drive"
            elif abs(metrics.momentum_score) > 0.70:
                return "moderate_drive"
            elif metrics.momentum_acceleration > 0.3:
                return "accelerating_drive"
            elif metrics.momentum_acceleration < -0.3:
                return "exhausting_drive"
            else:
                return "steady_drive"
        
        elif cycle == MarketCycle.RANGE:
            # Check range characteristics
            if metrics.range_tightness > 0.8:
                return "tight_range"
            elif metrics.price_oscillations > 6:
                return "choppy_range"
            elif metrics.mean_reversion_strength > 0.8:
                return "mean_reverting_range"
            else:
                return "balanced_range"
        
        elif cycle == MarketCycle.LIQUIDITY:
            # Check liquidity event patterns
            if metrics.sweep_count > 3:
                return "multi_sweep"
            elif metrics.false_break_count > 3:
                return "false_breakout_zone"
            elif metrics.reversal_candle_count > 2:
                return "reversal_zone"
            else:
                return "liquidity_grab"
        
        return "undefined"
    
    def _calculate_transition_probability(self, scores: Dict[MarketCycle, float], metrics: CycleMetrics) -> float:
        """Calculate probability of transitioning to a different phase."""
        current_score = scores[self.history.current_cycle]
        max_other_score = max(score for cycle, score in scores.items() 
                             if cycle != self.history.current_cycle)
        
        # High probability if another phase is scoring higher
        if max_other_score > current_score:
            return min((max_other_score - current_score) / current_score if current_score > 0 else 1.0, 1.0)
        
        # Low probability if current phase is dominant
        if current_score > 0.75:
            return 0.1
        
        # Moderate probability if scores are close
        score_difference = current_score - max_other_score
        return max(0.0, 1.0 - score_difference)
    
    def _determine_bias(self, metrics: CycleMetrics, candles: List[CandleData]) -> Optional[OrderSide]:
        """Determine dominant directional bias."""
        # Strong positive momentum = bullish bias
        if metrics.momentum_score > 0.4:
            return OrderSide.LONG
        
        # Strong negative momentum = bearish bias
        elif metrics.momentum_score < -0.4:
            return OrderSide.SHORT
        
        # Check structure alignment
        elif metrics.higher_highs_count > metrics.lower_lows_count + 1:
            return OrderSide.LONG
        
        elif metrics.lower_lows_count > metrics.higher_highs_count + 1:
            return OrderSide.SHORT
        
        # No clear bias
        return None
    
    def _calculate_cycle_health(self, cycle: MarketCycle, metrics: CycleMetrics) -> float:
        """Calculate how 'clean' or 'healthy' the current cycle is."""
        health = 0.0
        
        if cycle == MarketCycle.DRIVE:
            # Clean drive = strong momentum + directional + low false breaks
            health += min(abs(metrics.momentum_score), 1.0) * 0.4
            health += metrics.directional_strength * 0.3
            false_break_penalty = min(metrics.false_break_count * 0.1, 0.3)
            health += max(0.0, 0.3 - false_break_penalty)
        
        elif cycle == MarketCycle.RANGE:
            # Clean range = tight + mean reverting + low momentum
            health += metrics.range_tightness * 0.4
            health += metrics.mean_reversion_strength * 0.3
            health += (1.0 - abs(metrics.momentum_score)) * 0.3
        
        elif cycle == MarketCycle.LIQUIDITY:
            # Clean liquidity = clear sweeps + reversals + high wicks
            health += min(metrics.sweep_count / 4.0, 1.0) * 0.4
            health += min(metrics.reversal_candle_count / 3.0, 1.0) * 0.3
            health += metrics.wick_dominance * 0.3
        
        return min(health, 1.0)
    
    def _empty_classification(self) -> CycleClassification:
        """Return empty classification for insufficient data."""
        return CycleClassification(
            cycle=MarketCycle.RANGE,
            confidence=0.0,
            sub_phase="insufficient_data",
            transition_probability=0.0
        )
    
    def get_cycle_recommendation(self, classification: CycleClassification) -> Dict[str, Any]:
        """Get trading recommendations based on current cycle."""
        recommendations = {
            'preferred_patterns': [],
            'avoid_patterns': [],
            'confidence_adjustment': 1.0,
            'notes': []
        }
        
        if classification.cycle == MarketCycle.DRIVE:
            recommendations['preferred_patterns'] = ['breakout', 'momentum', 'trend_continuation']
            recommendations['avoid_patterns'] = ['mean_reversion', 'range_extremes']
            recommendations['confidence_adjustment'] = 1.2 if classification.cycle_health > 0.7 else 1.0
            recommendations['notes'].append(f"Strong {classification.dominant_bias.value if classification.dominant_bias else 'directional'} drive phase")
        
        elif classification.cycle == MarketCycle.RANGE:
            recommendations['preferred_patterns'] = ['mean_reversion', 'onion', 'range_extremes']
            recommendations['avoid_patterns'] = ['breakout', 'momentum']
            recommendations['confidence_adjustment'] = 1.1 if classification.metrics.range_tightness > 0.7 else 0.9
            recommendations['notes'].append("Range-bound - trade the extremes")
        
        elif classification.cycle == MarketCycle.LIQUIDITY:
            recommendations['preferred_patterns'] = ['fakeout', 'reversal', 'sweep_entry']
            recommendations['avoid_patterns'] = ['breakout', 'early_momentum']
            recommendations['confidence_adjustment'] = 0.8  # More cautious in liquidity phase
            recommendations['notes'].append("Liquidity phase - expect false moves")
        
        # Add transition warning
        if classification.transition_probability > 0.6:
            recommendations['notes'].append(f"⚠️ High transition probability ({classification.transition_probability:.1%})")
            recommendations['confidence_adjustment'] *= 0.9
        
        return recommendations


# Export main class
__all__ = [
    "MarketCycleClassifier",
    "CycleClassification",
    "CycleMetrics",
    "CycleHistory"
]
