"""
Candle Pattern Detector

Implements detection algorithms for various candle patterns used in trading strategy rules.
Supports LE candles, small wick, steeper wick, and celery play patterns.

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
from dataclasses import asdict

from ..types import (
    CandleData, PatternDetection, EntryType, Timeframe, 
    OrderSide, MarketCycle, PatternCondition
)


class CandlePatternDetector:
    """Main candle pattern detection engine."""
    
    def __init__(self):
        """Initialize the detector with default parameters."""
        self.min_confidence = 0.3
        self.lookback_periods = 20  # How many candles to look back for context
        
        # Pattern-specific parameters (can be customized)
        self.le_params = {
            'min_wick_ratio': 2.0,  # Upper wick must be >= 2x body size
            'min_close_position': 0.7,  # Close must be in upper 70% of range
            'max_body_ratio': 0.6,  # Body can't be more than 60% of total range
            'volume_confirmation': True,  # Require above-average volume
        }
        
        self.small_wick_params = {
            'max_wick_ratio': 0.3,  # Wicks must be <= 30% of body size
            'min_body_ratio': 0.6,  # Body must be >= 60% of total range
            'direction_matters': True,  # Pattern direction should align with trend
        }
        
        self.steeper_wick_params = {
            'min_wick_ratio': 1.5,  # One wick significantly larger than the other
            'wick_imbalance': 3.0,  # Ratio between long and short wick
            'min_body_size': 0.3,  # Minimum relative body size
        }
        
        self.celery_params = {
            'max_body_ratio': 0.2,  # Very small body (doji-like)
            'equal_wick_tolerance': 0.3,  # Wicks should be roughly equal
            'min_total_range': 0.5,  # Minimum volatility requirement
        }

    def detect_patterns(
        self, 
        candles: List[CandleData], 
        asset: str,
        timeframe: Timeframe,
        pattern_types: Optional[List[EntryType]] = None,
        market_cycle: Optional[MarketCycle] = None
    ) -> List[PatternDetection]:
        """
        Detect patterns in a series of candles.
        
        Args:
            candles: List of candle data (should be in chronological order)
            asset: Trading asset symbol
            timeframe: Timeframe of the candles
            pattern_types: Specific patterns to detect (None = detect all)
            market_cycle: Current market cycle context
            
        Returns:
            List of detected patterns with confidence scores
        """
        if len(candles) < 3:
            return []
            
        patterns = []
        
        # Default to detecting all pattern types
        if pattern_types is None:
            pattern_types = [EntryType.LE, EntryType.SMALL_WICK, 
                           EntryType.STEEPER_WICK, EntryType.CELERY]
        
        # Analyze each candle (except first and last few for context)
        for i in range(2, len(candles) - 1):
            current_candle = candles[i]
            
            # Get context candles
            context_start = max(0, i - self.lookback_periods)
            context_candles = candles[context_start:i+1]
            
            # Detect each requested pattern type
            for pattern_type in pattern_types:
                detection = self._detect_single_pattern(
                    current_candle=current_candle,
                    context_candles=context_candles,
                    candle_index=i,
                    pattern_type=pattern_type,
                    asset=asset,
                    timeframe=timeframe,
                    market_cycle=market_cycle
                )
                
                if detection and detection.confidence >= self.min_confidence:
                    patterns.append(detection)
        
        return patterns

    def _detect_single_pattern(
        self,
        current_candle: CandleData,
        context_candles: List[CandleData],
        candle_index: int,
        pattern_type: EntryType,
        asset: str,
        timeframe: Timeframe,
        market_cycle: Optional[MarketCycle] = None
    ) -> Optional[PatternDetection]:
        """Detect a specific pattern type at a given candle."""
        
        # Calculate candle metrics
        metrics = self._calculate_candle_metrics(current_candle, context_candles)
        
        # Dispatch to specific pattern detector
        if pattern_type == EntryType.LE:
            confidence, pattern_data = self._detect_le_candle(current_candle, metrics)
        elif pattern_type == EntryType.SMALL_WICK:
            confidence, pattern_data = self._detect_small_wick(current_candle, metrics)
        elif pattern_type == EntryType.STEEPER_WICK:
            confidence, pattern_data = self._detect_steeper_wick(current_candle, metrics)
        elif pattern_type == EntryType.CELERY:
            confidence, pattern_data = self._detect_celery_play(current_candle, metrics)
        else:
            return None
            
        if confidence < self.min_confidence:
            return None
            
        # Apply market cycle context adjustment
        if market_cycle:
            confidence = self._adjust_confidence_for_cycle(
                confidence, pattern_type, market_cycle
            )
            
        return PatternDetection(
            pattern_type=pattern_type,
            timeframe=timeframe,
            asset=asset,
            timestamp=current_candle.timestamp,
            confidence=confidence,
            candle_index=candle_index,
            pattern_data=pattern_data,
            market_cycle=market_cycle,
            generates_signal=confidence > 0.7,  # High confidence patterns generate signals
            signal_strength=min(confidence * 1.2, 1.0),  # Boost signal strength slightly
            confluence_score=0.0  # Will be set by confluence scorer
        )

    def _calculate_candle_metrics(
        self, 
        candle: CandleData, 
        context_candles: List[CandleData]
    ) -> Dict[str, float]:
        """Calculate comprehensive metrics for a candle in context."""
        
        # Basic candle metrics
        total_range = candle.total_range
        body_size = candle.body_size
        upper_wick = candle.upper_wick
        lower_wick = candle.lower_wick
        
        metrics = {
            'total_range': total_range,
            'body_size': body_size,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'body_ratio': body_size / total_range if total_range > 0 else 0,
            'upper_wick_ratio': upper_wick / body_size if body_size > 0 else float('inf'),
            'lower_wick_ratio': lower_wick / body_size if body_size > 0 else float('inf'),
            'is_bullish': candle.is_bullish,
            'is_bearish': candle.is_bearish,
        }
        
        # Close position within the range (0 = at low, 1 = at high)
        if total_range > 0:
            metrics['close_position'] = (candle.close - candle.low) / total_range
        else:
            metrics['close_position'] = 0.5
            
        # Context metrics
        if len(context_candles) > 1:
            # Average volume over context period
            volumes = [c.volume for c in context_candles[:-1]]  # Exclude current candle
            avg_volume = np.mean(volumes) if volumes else 0
            metrics['volume_ratio'] = candle.volume / avg_volume if avg_volume > 0 else 1.0
            
            # Average range over context period
            ranges = [c.total_range for c in context_candles[:-1]]
            avg_range = np.mean(ranges) if ranges else 0
            metrics['range_ratio'] = total_range / avg_range if avg_range > 0 else 1.0
            
            # Trend context (simple slope of closes)
            closes = [c.close for c in context_candles]
            if len(closes) >= 3:
                trend_slope = np.polyfit(range(len(closes)), closes, 1)[0]
                metrics['trend_slope'] = trend_slope
                metrics['trend_strength'] = abs(trend_slope) / np.mean(closes) if np.mean(closes) > 0 else 0
            else:
                metrics['trend_slope'] = 0
                metrics['trend_strength'] = 0
        else:
            metrics.update({
                'volume_ratio': 1.0,
                'range_ratio': 1.0,
                'trend_slope': 0,
                'trend_strength': 0
            })
            
        return metrics

    def _detect_le_candle(
        self, 
        candle: CandleData, 
        metrics: Dict[str, float]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Detect Liquidity Engulf (LE) candle pattern.
        
        LE candle characteristics:
        - Long upper wick (shows liquidity grab above)
        - Close in upper portion of range
        - Body not too large relative to total range
        - Preferably bullish with volume confirmation
        """
        confidence = 0.0
        pattern_data = {}
        
        params = self.le_params
        
        # Core requirements
        scores = []
        
        # 1. Upper wick requirement
        if metrics['upper_wick_ratio'] >= params['min_wick_ratio']:
            wick_score = min(metrics['upper_wick_ratio'] / (params['min_wick_ratio'] * 2), 1.0)
            scores.append(('upper_wick', wick_score, 0.3))
        else:
            return 0.0, {}  # Hard requirement
            
        # 2. Close position requirement
        if metrics['close_position'] >= params['min_close_position']:
            close_score = metrics['close_position']
            scores.append(('close_position', close_score, 0.25))
        else:
            return 0.0, {}  # Hard requirement
            
        # 3. Body size not too large
        if metrics['body_ratio'] <= params['max_body_ratio']:
            body_score = 1.0 - (metrics['body_ratio'] / params['max_body_ratio'])
            scores.append(('body_size', body_score, 0.2))
        else:
            scores.append(('body_size', 0.5, 0.2))  # Penalty but not disqualifying
            
        # 4. Volume confirmation (optional boost)
        if params['volume_confirmation'] and metrics['volume_ratio'] > 1.2:
            volume_score = min((metrics['volume_ratio'] - 1.0) / 2.0, 1.0)
            scores.append(('volume', volume_score, 0.15))
            
        # 5. Trend context (bullish LE works better in uptrend)
        if candle.is_bullish and metrics['trend_slope'] > 0:
            trend_score = min(metrics['trend_strength'] * 2, 1.0)
            scores.append(('trend_context', trend_score, 0.1))
        elif candle.is_bearish and metrics['trend_slope'] < 0:
            trend_score = min(metrics['trend_strength'] * 2, 1.0)
            scores.append(('trend_context', trend_score, 0.1))
        else:
            scores.append(('trend_context', 0.3, 0.1))  # Neutral
            
        # Calculate weighted confidence
        confidence = sum(score * weight for _, score, weight in scores)
        
        # Store pattern details
        pattern_data = {
            'upper_wick_ratio': metrics['upper_wick_ratio'],
            'close_position': metrics['close_position'],
            'body_ratio': metrics['body_ratio'],
            'volume_ratio': metrics['volume_ratio'],
            'is_bullish': candle.is_bullish,
            'scores': dict((name, score) for name, score, _ in scores)
        }
        
        return confidence, pattern_data

    def _detect_small_wick(
        self, 
        candle: CandleData, 
        metrics: Dict[str, float]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Detect Small Wick pattern.
        
        Small wick characteristics:
        - Very small wicks relative to body
        - Large body relative to total range
        - Strong directional move
        """
        confidence = 0.0
        pattern_data = {}
        
        params = self.small_wick_params
        scores = []
        
        # 1. Small wick requirement
        max_wick_ratio = max(metrics['upper_wick_ratio'], metrics['lower_wick_ratio'])
        if max_wick_ratio <= params['max_wick_ratio']:
            wick_score = 1.0 - (max_wick_ratio / params['max_wick_ratio'])
            scores.append(('small_wicks', wick_score, 0.35))
        else:
            return 0.0, {}  # Hard requirement
            
        # 2. Large body requirement
        if metrics['body_ratio'] >= params['min_body_ratio']:
            body_score = metrics['body_ratio']
            scores.append(('large_body', body_score, 0.3))
        else:
            return 0.0, {}  # Hard requirement
            
        # 3. Volume confirmation
        if metrics['volume_ratio'] > 1.1:
            volume_score = min((metrics['volume_ratio'] - 1.0) / 1.5, 1.0)
            scores.append(('volume', volume_score, 0.2))
            
        # 4. Trend alignment (if enabled)
        if params['direction_matters']:
            if (candle.is_bullish and metrics['trend_slope'] > 0) or \
               (candle.is_bearish and metrics['trend_slope'] < 0):
                trend_score = min(metrics['trend_strength'] * 3, 1.0)
                scores.append(('trend_alignment', trend_score, 0.15))
            else:
                scores.append(('trend_alignment', 0.2, 0.15))  # Penalty for fighting trend
        
        confidence = sum(score * weight for _, score, weight in scores)
        
        pattern_data = {
            'max_wick_ratio': max_wick_ratio,
            'body_ratio': metrics['body_ratio'],
            'volume_ratio': metrics['volume_ratio'],
            'is_bullish': candle.is_bullish,
            'scores': dict((name, score) for name, score, _ in scores)
        }
        
        return confidence, pattern_data

    def _detect_steeper_wick(
        self, 
        candle: CandleData, 
        metrics: Dict[str, float]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Detect Steeper Wick pattern.
        
        Steeper wick characteristics:
        - One wick significantly longer than the other
        - Moderate body size
        - Wick shows rejection from one direction
        """
        confidence = 0.0
        pattern_data = {}
        
        params = self.steeper_wick_params
        scores = []
        
        # Determine which wick is longer
        upper_wick = metrics['upper_wick']
        lower_wick = metrics['lower_wick']
        
        if upper_wick > lower_wick:
            long_wick = upper_wick
            short_wick = lower_wick
            wick_direction = 'upper'
        else:
            long_wick = lower_wick
            short_wick = upper_wick
            wick_direction = 'lower'
            
        # Calculate wick imbalance
        if short_wick > 0:
            wick_imbalance = long_wick / short_wick
        else:
            wick_imbalance = float('inf')
            
        # 1. Minimum wick size requirement
        long_wick_ratio = long_wick / metrics['body_size'] if metrics['body_size'] > 0 else float('inf')
        if long_wick_ratio >= params['min_wick_ratio']:
            wick_size_score = min(long_wick_ratio / (params['min_wick_ratio'] * 2), 1.0)
            scores.append(('wick_size', wick_size_score, 0.3))
        else:
            return 0.0, {}  # Hard requirement
            
        # 2. Wick imbalance requirement
        if wick_imbalance >= params['wick_imbalance']:
            imbalance_score = min(wick_imbalance / (params['wick_imbalance'] * 2), 1.0)
            scores.append(('wick_imbalance', imbalance_score, 0.25))
        else:
            return 0.0, {}  # Hard requirement
            
        # 3. Body size requirement
        if metrics['body_ratio'] >= params['min_body_size']:
            body_score = metrics['body_ratio']
            scores.append(('body_size', body_score, 0.2))
        else:
            scores.append(('body_size', 0.3, 0.2))  # Penalty but not disqualifying
            
        # 4. Volume confirmation
        if metrics['volume_ratio'] > 1.0:
            volume_score = min(metrics['volume_ratio'], 2.0) / 2.0
            scores.append(('volume', volume_score, 0.15))
            
        # 5. Trend context (rejection of trend is significant)
        if wick_direction == 'upper' and metrics['trend_slope'] > 0:  # Rejection of uptrend
            trend_score = min(metrics['trend_strength'] * 2, 1.0)
            scores.append(('trend_rejection', trend_score, 0.1))
        elif wick_direction == 'lower' and metrics['trend_slope'] < 0:  # Rejection of downtrend
            trend_score = min(metrics['trend_strength'] * 2, 1.0)
            scores.append(('trend_rejection', trend_score, 0.1))
        else:
            scores.append(('trend_rejection', 0.5, 0.1))  # Neutral
            
        confidence = sum(score * weight for _, score, weight in scores)
        
        pattern_data = {
            'wick_direction': wick_direction,
            'wick_imbalance': wick_imbalance,
            'long_wick_ratio': long_wick_ratio,
            'body_ratio': metrics['body_ratio'],
            'volume_ratio': metrics['volume_ratio'],
            'scores': dict((name, score) for name, score, _ in scores)
        }
        
        return confidence, pattern_data

    def _detect_celery_play(
        self, 
        candle: CandleData, 
        metrics: Dict[str, float]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Detect Celery Play pattern.
        
        Celery play characteristics:
        - Very small body (doji-like)
        - Equal or similar wicks on both sides
        - Shows indecision/equilibrium
        - Good range and volume
        """
        confidence = 0.0
        pattern_data = {}
        
        params = self.celery_params
        scores = []
        
        # 1. Small body requirement
        if metrics['body_ratio'] <= params['max_body_ratio']:
            body_score = 1.0 - (metrics['body_ratio'] / params['max_body_ratio'])
            scores.append(('small_body', body_score, 0.35))
        else:
            return 0.0, {}  # Hard requirement
            
        # 2. Equal wicks requirement
        upper_wick = metrics['upper_wick']
        lower_wick = metrics['lower_wick']
        total_wick = upper_wick + lower_wick
        
        if total_wick > 0:
            wick_balance = 1.0 - abs(upper_wick - lower_wick) / total_wick
            if wick_balance >= (1.0 - params['equal_wick_tolerance']):
                wick_score = wick_balance
                scores.append(('equal_wicks', wick_score, 0.3))
            else:
                return 0.0, {}  # Hard requirement
        else:
            return 0.0, {}  # Need some wick length
            
        # 3. Minimum volatility requirement
        if metrics['range_ratio'] >= params['min_total_range']:
            range_score = min(metrics['range_ratio'], 2.0) / 2.0
            scores.append(('volatility', range_score, 0.2))
        else:
            scores.append(('volatility', 0.3, 0.2))  # Penalty but not disqualifying
            
        # 4. Volume confirmation
        if metrics['volume_ratio'] > 1.0:
            volume_score = min(metrics['volume_ratio'], 2.0) / 2.0
            scores.append(('volume', volume_score, 0.15))
            
        confidence = sum(score * weight for _, score, weight in scores)
        
        pattern_data = {
            'body_ratio': metrics['body_ratio'],
            'wick_balance': wick_balance if 'wick_balance' in locals() else 0,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'range_ratio': metrics['range_ratio'],
            'volume_ratio': metrics['volume_ratio'],
            'scores': dict((name, score) for name, score, _ in scores)
        }
        
        return confidence, pattern_data

    def _adjust_confidence_for_cycle(
        self, 
        confidence: float, 
        pattern_type: EntryType, 
        market_cycle: MarketCycle
    ) -> float:
        """Adjust confidence based on market cycle context."""
        
        adjustments = {
            # LE patterns work well in drive and liquidity phases
            EntryType.LE: {
                MarketCycle.DRIVE: 1.1,      # Boost in trending markets
                MarketCycle.RANGE: 0.9,      # Slight penalty in ranging markets
                MarketCycle.LIQUIDITY: 1.15  # Best in liquidity phases
            },
            # Small wick patterns work best in drive phases
            EntryType.SMALL_WICK: {
                MarketCycle.DRIVE: 1.2,      # Excellent in trending markets
                MarketCycle.RANGE: 0.8,      # Poor in ranging markets
                MarketCycle.LIQUIDITY: 1.0   # Neutral in liquidity phases
            },
            # Steeper wick patterns show rejection, good in all phases
            EntryType.STEEPER_WICK: {
                MarketCycle.DRIVE: 1.0,      # Neutral in trending markets
                MarketCycle.RANGE: 1.1,      # Good in ranging markets (rejections common)
                MarketCycle.LIQUIDITY: 1.05  # Slight boost in liquidity phases
            },
            # Celery patterns show indecision, best before moves
            EntryType.CELERY: {
                MarketCycle.DRIVE: 0.9,      # Not ideal in trending markets
                MarketCycle.RANGE: 1.2,      # Excellent in ranging markets
                MarketCycle.LIQUIDITY: 0.95  # Slight penalty in liquidity phases
            }
        }
        
        adjustment = adjustments.get(pattern_type, {}).get(market_cycle, 1.0)
        return min(confidence * adjustment, 1.0)  # Cap at 1.0

    def detect_pattern_conditions(
        self, 
        candles: List[CandleData], 
        conditions: List[PatternCondition],
        asset: str
    ) -> List[PatternDetection]:
        """
        Detect patterns based on specific pattern conditions.
        
        This method allows for more granular control over pattern detection
        by accepting specific conditions with custom parameters.
        """
        patterns = []
        
        for condition in conditions:
            # Override default parameters with condition parameters
            original_params = getattr(self, f"{condition.type.value}_params", {})
            custom_params = {**original_params, **condition.params}
            setattr(self, f"{condition.type.value}_params", custom_params)
            
            # Detect patterns of this type
            condition_patterns = self.detect_patterns(
                candles=candles,
                asset=asset,
                timeframe=condition.timeframe,
                pattern_types=[condition.type]
            )
            
            # Restore original parameters
            setattr(self, f"{condition.type.value}_params", original_params)
            
            patterns.extend(condition_patterns)
            
        return patterns

    def get_pattern_summary(self, patterns: List[PatternDetection]) -> Dict[str, Any]:
        """Generate a summary of detected patterns."""
        
        summary = {
            'total_patterns': len(patterns),
            'by_type': {},
            'by_timeframe': {},
            'confidence_distribution': {
                'high': 0,    # > 0.8
                'medium': 0,  # 0.5 - 0.8
                'low': 0      # < 0.5
            },
            'signals_generated': 0
        }
        
        for pattern in patterns:
            # Count by type
            pattern_type = pattern.pattern_type.value
            summary['by_type'][pattern_type] = summary['by_type'].get(pattern_type, 0) + 1
            
            # Count by timeframe
            timeframe = pattern.timeframe.value
            summary['by_timeframe'][timeframe] = summary['by_timeframe'].get(timeframe, 0) + 1
            
            # Confidence distribution
            if pattern.confidence > 0.8:
                summary['confidence_distribution']['high'] += 1
            elif pattern.confidence > 0.5:
                summary['confidence_distribution']['medium'] += 1
            else:
                summary['confidence_distribution']['low'] += 1
                
            # Signal generation
            if pattern.generates_signal:
                summary['signals_generated'] += 1
                
        return summary


# Convenience functions for quick pattern detection

def detect_le_patterns(
    candles: List[CandleData], 
    asset: str, 
    timeframe: Timeframe,
    min_confidence: float = 0.5
) -> List[PatternDetection]:
    """Quick function to detect only LE patterns."""
    detector = CandlePatternDetector()
    detector.min_confidence = min_confidence
    
    return detector.detect_patterns(
        candles=candles,
        asset=asset,
        timeframe=timeframe,
        pattern_types=[EntryType.LE]
    )


def detect_all_patterns(
    candles: List[CandleData], 
    asset: str, 
    timeframe: Timeframe,
    min_confidence: float = 0.3
) -> List[PatternDetection]:
    """Quick function to detect all supported patterns."""
    detector = CandlePatternDetector()
    detector.min_confidence = min_confidence
    
    return detector.detect_patterns(
        candles=candles,
        asset=asset,
        timeframe=timeframe
    )


# Example usage and testing
if __name__ == "__main__":
    # This would be used for standalone testing
    print("Candle Pattern Detector initialized successfully")
    print("Supported patterns:", [e.value for e in EntryType])