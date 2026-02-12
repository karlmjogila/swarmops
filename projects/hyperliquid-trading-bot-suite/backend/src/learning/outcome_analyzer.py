"""
Outcome Analyzer Module

Analyzes trade outcomes to identify patterns, generate insights, and update 
strategy confidence scores. This is the core learning component that makes 
the system improve over time.

Key capabilities:
- Analyze trade performance by strategy
- Identify success and failure patterns
- Generate actionable learning insights
- Update strategy confidence scores
- Detect market condition correlations
- Track improvement over time

Author: Hyperliquid Trading Bot Suite
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from ..types import (
    TradeRecord, TradeOutcome, LearningEntry, StrategyRule,
    MarketCycle, OrderSide, ExitReason
)
from ..knowledge.models import StrategyPerformance
from ..backtest.statistics import (
    BacktestStatisticsCalculator, TradeStatistics, ComprehensiveStatistics
)

logger = logging.getLogger(__name__)


@dataclass
class PatternInsight:
    """Represents an identified pattern in trade outcomes."""
    pattern_type: str  # "success_factor" or "failure_pattern"
    description: str
    confidence: float  # 0.0 to 1.0
    supporting_trades: List[str]  # Trade IDs
    market_conditions: Dict[str, Any]
    impact_score: float  # How much this pattern affects outcomes
    
    def to_learning_entry(self, strategy_rule_id: str) -> LearningEntry:
        """Convert to a LearningEntry model."""
        return LearningEntry(
            strategy_rule_id=strategy_rule_id,
            insight=self.description,
            pattern_identified=self.pattern_type,
            supporting_trades=self.supporting_trades,
            confidence=self.confidence,
            market_conditions=self.market_conditions,
            created_at=datetime.utcnow(),
            validation_count=len(self.supporting_trades)
        )


@dataclass
class StrategyAnalysis:
    """Complete analysis of a strategy's performance."""
    strategy_rule_id: str
    strategy_name: str
    
    # Performance metrics
    total_trades: int = 0
    win_rate: float = 0.0
    avg_r_multiple: float = 0.0
    profit_factor: float = 0.0
    
    # Confidence adjustment
    old_confidence: float = 0.5
    new_confidence: float = 0.5
    confidence_change: float = 0.0
    
    # Insights
    success_patterns: List[PatternInsight] = field(default_factory=list)
    failure_patterns: List[PatternInsight] = field(default_factory=list)
    
    # Context correlations
    best_market_cycles: List[Tuple[MarketCycle, float]] = field(default_factory=list)
    worst_market_cycles: List[Tuple[MarketCycle, float]] = field(default_factory=list)
    best_timeframes: List[Tuple[str, float]] = field(default_factory=list)
    best_assets: List[Tuple[str, float]] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Strategy Analysis: {self.strategy_name}",
            f"  Trades: {self.total_trades}",
            f"  Win Rate: {self.win_rate:.1f}%",
            f"  Avg R: {self.avg_r_multiple:.2f}",
            f"  Confidence: {self.old_confidence:.2f} → {self.new_confidence:.2f} ({self.confidence_change:+.2f})",
            f"  Success Patterns: {len(self.success_patterns)}",
            f"  Failure Patterns: {len(self.failure_patterns)}",
        ]
        
        if self.recommendations:
            lines.append("  Recommendations:")
            for rec in self.recommendations:
                lines.append(f"    - {rec}")
        
        return "\n".join(lines)


class OutcomeAnalyzer:
    """
    Analyzes trade outcomes to extract learning insights.
    
    This is the core learning engine that makes the system improve over time.
    It analyzes both successful and failed trades to identify patterns,
    correlations with market conditions, and generates actionable insights.
    """
    
    def __init__(
        self,
        min_trades_for_analysis: int = 10,
        min_pattern_trades: int = 3,
        confidence_adjustment_rate: float = 0.1,
        pattern_confidence_threshold: float = 0.6
    ):
        """
        Initialize the outcome analyzer.
        
        Args:
            min_trades_for_analysis: Minimum trades needed before analyzing strategy
            min_pattern_trades: Minimum trades to consider a pattern significant
            confidence_adjustment_rate: Max adjustment to strategy confidence per analysis
            pattern_confidence_threshold: Minimum confidence to generate learning entry
        """
        self.min_trades_for_analysis = min_trades_for_analysis
        self.min_pattern_trades = min_pattern_trades
        self.confidence_adjustment_rate = confidence_adjustment_rate
        self.pattern_confidence_threshold = pattern_confidence_threshold
        
        self.stats_calculator = BacktestStatisticsCalculator(risk_free_rate=0.0)
        
        logger.info(
            f"OutcomeAnalyzer initialized: "
            f"min_trades={min_trades_for_analysis}, "
            f"min_pattern={min_pattern_trades}, "
            f"adjust_rate={confidence_adjustment_rate}"
        )
    
    def analyze_strategy(
        self,
        strategy_rule: StrategyRule,
        trades: List[TradeRecord],
        existing_learnings: Optional[List[LearningEntry]] = None
    ) -> StrategyAnalysis:
        """
        Analyze all trades for a specific strategy and generate insights.
        
        Args:
            strategy_rule: The strategy rule being analyzed
            trades: All trades executed with this strategy
            existing_learnings: Previous learning entries (to avoid duplicates)
            
        Returns:
            StrategyAnalysis with complete analysis and recommendations
        """
        logger.info(
            f"Analyzing strategy '{strategy_rule.name}' "
            f"with {len(trades)} trades"
        )
        
        analysis = StrategyAnalysis(
            strategy_rule_id=strategy_rule.id,
            strategy_name=strategy_rule.name,
            old_confidence=strategy_rule.confidence
        )
        
        # Need minimum trades for meaningful analysis
        if len(trades) < self.min_trades_for_analysis:
            logger.info(
                f"Insufficient trades ({len(trades)}) for analysis "
                f"(minimum: {self.min_trades_for_analysis})"
            )
            analysis.total_trades = len(trades)
            analysis.new_confidence = strategy_rule.confidence
            analysis.recommendations.append(
                f"Need {self.min_trades_for_analysis - len(trades)} more trades for meaningful analysis"
            )
            return analysis
        
        # Calculate basic statistics
        trade_stats = self.stats_calculator.calculate_trade_statistics(trades)
        
        analysis.total_trades = trade_stats.total_trades
        analysis.win_rate = trade_stats.win_rate
        analysis.avg_r_multiple = trade_stats.avg_r_multiple
        analysis.profit_factor = trade_stats.profit_factor
        
        # Identify success patterns
        winning_trades = [t for t in trades if t.outcome == TradeOutcome.WIN]
        if winning_trades:
            analysis.success_patterns = self._identify_success_patterns(
                winning_trades, existing_learnings
            )
            logger.info(f"Identified {len(analysis.success_patterns)} success patterns")
        
        # Identify failure patterns
        losing_trades = [t for t in trades if t.outcome == TradeOutcome.LOSS]
        if losing_trades:
            analysis.failure_patterns = self._identify_failure_patterns(
                losing_trades, existing_learnings
            )
            logger.info(f"Identified {len(analysis.failure_patterns)} failure patterns")
        
        # Analyze market condition correlations
        analysis.best_market_cycles = self._analyze_market_cycle_performance(trades)
        analysis.worst_market_cycles = self._analyze_market_cycle_performance(
            trades, worst=True
        )
        analysis.best_timeframes = self._analyze_timeframe_performance(trades)
        analysis.best_assets = self._analyze_asset_performance(trades)
        
        # Calculate new confidence score
        analysis.new_confidence = self._calculate_new_confidence(
            strategy_rule.confidence,
            trade_stats,
            analysis.success_patterns,
            analysis.failure_patterns
        )
        analysis.confidence_change = analysis.new_confidence - analysis.old_confidence
        
        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(
            analysis, trade_stats
        )
        
        logger.info(
            f"Strategy analysis complete: {analysis.win_rate:.1f}% win rate, "
            f"confidence {analysis.old_confidence:.2f} → {analysis.new_confidence:.2f}"
        )
        
        return analysis
    
    def analyze_all_strategies(
        self,
        strategies: List[StrategyRule],
        trades_by_strategy: Dict[str, List[TradeRecord]],
        existing_learnings: Optional[Dict[str, List[LearningEntry]]] = None
    ) -> List[StrategyAnalysis]:
        """
        Analyze all strategies and their trades.
        
        Args:
            strategies: List of strategy rules
            trades_by_strategy: Dict mapping strategy_rule_id to trades
            existing_learnings: Dict mapping strategy_rule_id to learning entries
            
        Returns:
            List of StrategyAnalysis objects
        """
        logger.info(f"Analyzing {len(strategies)} strategies")
        
        analyses = []
        
        for strategy in strategies:
            trades = trades_by_strategy.get(strategy.id, [])
            learnings = existing_learnings.get(strategy.id, []) if existing_learnings else None
            
            analysis = self.analyze_strategy(strategy, trades, learnings)
            analyses.append(analysis)
        
        logger.info(f"Completed analysis of {len(analyses)} strategies")
        return analyses
    
    def generate_learning_entries(
        self,
        analysis: StrategyAnalysis
    ) -> List[LearningEntry]:
        """
        Generate learning entries from strategy analysis.
        
        Args:
            analysis: Completed strategy analysis
            
        Returns:
            List of LearningEntry objects ready to be stored
        """
        entries = []
        
        # Generate entries for success patterns
        for pattern in analysis.success_patterns:
            if pattern.confidence >= self.pattern_confidence_threshold:
                entry = pattern.to_learning_entry(analysis.strategy_rule_id)
                entries.append(entry)
        
        # Generate entries for failure patterns
        for pattern in analysis.failure_patterns:
            if pattern.confidence >= self.pattern_confidence_threshold:
                entry = pattern.to_learning_entry(analysis.strategy_rule_id)
                entries.append(entry)
        
        logger.info(
            f"Generated {len(entries)} learning entries for strategy "
            f"'{analysis.strategy_name}'"
        )
        
        return entries
    
    # ===== PATTERN IDENTIFICATION =====
    
    def _identify_success_patterns(
        self,
        winning_trades: List[TradeRecord],
        existing_learnings: Optional[List[LearningEntry]]
    ) -> List[PatternInsight]:
        """Identify patterns common to successful trades."""
        
        patterns = []
        
        # Pattern 1: Market cycle correlation
        cycle_pattern = self._analyze_market_cycle_pattern(
            winning_trades, "success_factor"
        )
        if cycle_pattern:
            patterns.append(cycle_pattern)
        
        # Pattern 2: Exit reason success
        exit_pattern = self._analyze_exit_reason_pattern(
            winning_trades, "success_factor"
        )
        if exit_pattern:
            patterns.append(exit_pattern)
        
        # Pattern 3: R-multiple consistency
        r_pattern = self._analyze_r_multiple_pattern(winning_trades)
        if r_pattern:
            patterns.append(r_pattern)
        
        # Pattern 4: Confluence score correlation
        confluence_pattern = self._analyze_confluence_pattern(
            winning_trades, "success_factor"
        )
        if confluence_pattern:
            patterns.append(confluence_pattern)
        
        # Pattern 5: Trade timing
        timing_pattern = self._analyze_timing_pattern(
            winning_trades, "success_factor"
        )
        if timing_pattern:
            patterns.append(timing_pattern)
        
        return [p for p in patterns if p is not None]
    
    def _identify_failure_patterns(
        self,
        losing_trades: List[TradeRecord],
        existing_learnings: Optional[List[LearningEntry]]
    ) -> List[PatternInsight]:
        """Identify patterns common to failed trades."""
        
        patterns = []
        
        # Pattern 1: Market cycle failures
        cycle_pattern = self._analyze_market_cycle_pattern(
            losing_trades, "failure_pattern"
        )
        if cycle_pattern:
            patterns.append(cycle_pattern)
        
        # Pattern 2: Stop loss frequency
        sl_pattern = self._analyze_exit_reason_pattern(
            losing_trades, "failure_pattern"
        )
        if sl_pattern:
            patterns.append(sl_pattern)
        
        # Pattern 3: Low confluence correlation
        confluence_pattern = self._analyze_confluence_pattern(
            losing_trades, "failure_pattern"
        )
        if confluence_pattern:
            patterns.append(confluence_pattern)
        
        # Pattern 4: Timing issues
        timing_pattern = self._analyze_timing_pattern(
            losing_trades, "failure_pattern"
        )
        if timing_pattern:
            patterns.append(timing_pattern)
        
        # Pattern 5: Structure violations
        structure_pattern = self._analyze_structure_pattern(losing_trades)
        if structure_pattern:
            patterns.append(structure_pattern)
        
        return [p for p in patterns if p is not None]
    
    # ===== PATTERN ANALYZERS =====
    
    def _analyze_market_cycle_pattern(
        self,
        trades: List[TradeRecord],
        pattern_type: str
    ) -> Optional[PatternInsight]:
        """Analyze market cycle correlation with outcomes."""
        
        if len(trades) < self.min_pattern_trades:
            return None
        
        # Count trades by market cycle
        cycle_counts = defaultdict(int)
        cycle_trades = defaultdict(list)
        
        for trade in trades:
            if trade.price_action_context and trade.price_action_context.market_cycle:
                cycle = trade.price_action_context.market_cycle
                cycle_counts[cycle] += 1
                cycle_trades[cycle].append(trade.id)
        
        if not cycle_counts:
            return None
        
        # Find dominant cycle
        dominant_cycle = max(cycle_counts.items(), key=lambda x: x[1])
        cycle_name = dominant_cycle[0].value if hasattr(dominant_cycle[0], 'value') else str(dominant_cycle[0])
        count = dominant_cycle[1]
        
        # Need significant representation
        if count < self.min_pattern_trades:
            return None
        
        percentage = (count / len(trades)) * 100
        confidence = min(0.95, percentage / 100)
        
        if pattern_type == "success_factor":
            description = (
                f"Strategy performs well in {cycle_name} market cycle "
                f"({percentage:.0f}% of winning trades)"
            )
        else:
            description = (
                f"Strategy struggles in {cycle_name} market cycle "
                f"({percentage:.0f}% of losing trades)"
            )
        
        return PatternInsight(
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            supporting_trades=cycle_trades[dominant_cycle[0]],
            market_conditions={"market_cycle": cycle_name},
            impact_score=confidence * (count / len(trades))
        )
    
    def _analyze_exit_reason_pattern(
        self,
        trades: List[TradeRecord],
        pattern_type: str
    ) -> Optional[PatternInsight]:
        """Analyze exit reason patterns."""
        
        if len(trades) < self.min_pattern_trades:
            return None
        
        exit_counts = defaultdict(int)
        exit_trades = defaultdict(list)
        
        for trade in trades:
            if trade.exit_reason:
                reason = trade.exit_reason.value if hasattr(trade.exit_reason, 'value') else str(trade.exit_reason)
                exit_counts[reason] += 1
                exit_trades[reason].append(trade.id)
        
        if not exit_counts:
            return None
        
        dominant_exit = max(exit_counts.items(), key=lambda x: x[1])
        exit_name = dominant_exit[0]
        count = dominant_exit[1]
        
        if count < self.min_pattern_trades:
            return None
        
        percentage = (count / len(trades)) * 100
        confidence = min(0.90, percentage / 100)
        
        if pattern_type == "success_factor":
            description = (
                f"Most winning trades exit at {exit_name} "
                f"({percentage:.0f}% of wins)"
            )
        else:
            description = (
                f"Most losing trades exit at {exit_name} "
                f"({percentage:.0f}% of losses)"
            )
        
        return PatternInsight(
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            supporting_trades=exit_trades[exit_name],
            market_conditions={"dominant_exit_reason": exit_name},
            impact_score=confidence * (count / len(trades))
        )
    
    def _analyze_r_multiple_pattern(
        self,
        winning_trades: List[TradeRecord]
    ) -> Optional[PatternInsight]:
        """Analyze R-multiple consistency in winning trades."""
        
        if len(winning_trades) < self.min_pattern_trades:
            return None
        
        r_multiples = [
            t.pnl_r_multiple for t in winning_trades 
            if t.pnl_r_multiple is not None and t.pnl_r_multiple > 0
        ]
        
        if len(r_multiples) < self.min_pattern_trades:
            return None
        
        avg_r = statistics.mean(r_multiples)
        
        # Count trades hitting TP2 (R > 1.5)
        tp2_trades = [t.id for t in winning_trades if t.pnl_r_multiple and t.pnl_r_multiple >= 1.5]
        tp2_percentage = (len(tp2_trades) / len(winning_trades)) * 100
        
        if tp2_percentage >= 40:  # At least 40% hitting TP2
            confidence = min(0.85, tp2_percentage / 100)
            description = (
                f"Strategy consistently hits TP2+ ({tp2_percentage:.0f}% of wins), "
                f"average R-multiple: {avg_r:.2f}R"
            )
            
            return PatternInsight(
                pattern_type="success_factor",
                description=description,
                confidence=confidence,
                supporting_trades=tp2_trades,
                market_conditions={"avg_r_multiple": avg_r, "tp2_rate": tp2_percentage},
                impact_score=confidence * (avg_r / 2.0)  # Normalize by TP2 target
            )
        
        return None
    
    def _analyze_confluence_pattern(
        self,
        trades: List[TradeRecord],
        pattern_type: str
    ) -> Optional[PatternInsight]:
        """Analyze confluence score correlation."""
        
        if len(trades) < self.min_pattern_trades:
            return None
        
        # Get trades with confluence scores
        trades_with_confluence = [
            t for t in trades
            if t.price_action_context and t.price_action_context.confluence_score is not None
        ]
        
        if len(trades_with_confluence) < self.min_pattern_trades:
            return None
        
        confluence_scores = [
            t.price_action_context.confluence_score 
            for t in trades_with_confluence
        ]
        
        avg_confluence = statistics.mean(confluence_scores)
        
        # High confluence trades
        high_confluence_trades = [
            t.id for t in trades_with_confluence
            if t.price_action_context.confluence_score >= 0.7
        ]
        
        high_conf_percentage = (len(high_confluence_trades) / len(trades_with_confluence)) * 100
        
        if pattern_type == "success_factor" and high_conf_percentage >= 50:
            confidence = min(0.90, avg_confluence)
            description = (
                f"Strategy performs best with high confluence "
                f"({high_conf_percentage:.0f}% wins had confluence ≥0.7, avg: {avg_confluence:.2f})"
            )
            
            return PatternInsight(
                pattern_type=pattern_type,
                description=description,
                confidence=confidence,
                supporting_trades=high_confluence_trades,
                market_conditions={"min_confluence": 0.7, "avg_confluence": avg_confluence},
                impact_score=confidence * avg_confluence
            )
        
        elif pattern_type == "failure_pattern" and high_conf_percentage < 30:
            # Low confluence in losses
            low_confluence_trades = [
                t.id for t in trades_with_confluence
                if t.price_action_context.confluence_score < 0.5
            ]
            
            low_conf_percentage = (len(low_confluence_trades) / len(trades_with_confluence)) * 100
            
            if low_conf_percentage >= 50:
                confidence = min(0.85, low_conf_percentage / 100)
                description = (
                    f"Strategy fails with low confluence "
                    f"({low_conf_percentage:.0f}% losses had confluence <0.5, avg: {avg_confluence:.2f})"
                )
                
                return PatternInsight(
                    pattern_type=pattern_type,
                    description=description,
                    confidence=confidence,
                    supporting_trades=low_confluence_trades,
                    market_conditions={"max_confluence": 0.5, "avg_confluence": avg_confluence},
                    impact_score=confidence * (1.0 - avg_confluence)
                )
        
        return None
    
    def _analyze_timing_pattern(
        self,
        trades: List[TradeRecord],
        pattern_type: str
    ) -> Optional[PatternInsight]:
        """Analyze trade timing patterns."""
        
        if len(trades) < self.min_pattern_trades:
            return None
        
        # Analyze hour of day
        hour_counts = defaultdict(int)
        hour_trades = defaultdict(list)
        
        for trade in trades:
            if trade.entry_time:
                hour = trade.entry_time.hour
                hour_counts[hour] += 1
                hour_trades[hour].append(trade.id)
        
        if not hour_counts:
            return None
        
        # Find dominant hour range
        dominant_hour = max(hour_counts.items(), key=lambda x: x[1])
        hour = dominant_hour[0]
        count = dominant_hour[1]
        
        if count < self.min_pattern_trades:
            return None
        
        percentage = (count / len(trades)) * 100
        
        # Need significant concentration (>30%)
        if percentage < 30:
            return None
        
        confidence = min(0.80, percentage / 100)
        
        # Determine time session
        if 0 <= hour < 8:
            session = "Asian session"
        elif 8 <= hour < 16:
            session = "European session"
        else:
            session = "US session"
        
        if pattern_type == "success_factor":
            description = (
                f"Strategy performs well during {session} "
                f"(hour {hour}:00, {percentage:.0f}% of wins)"
            )
        else:
            description = (
                f"Strategy struggles during {session} "
                f"(hour {hour}:00, {percentage:.0f}% of losses)"
            )
        
        return PatternInsight(
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            supporting_trades=hour_trades[hour],
            market_conditions={"dominant_hour": hour, "session": session},
            impact_score=confidence * (percentage / 100)
        )
    
    def _analyze_structure_pattern(
        self,
        losing_trades: List[TradeRecord]
    ) -> Optional[PatternInsight]:
        """Analyze market structure violations in losing trades."""
        
        if len(losing_trades) < self.min_pattern_trades:
            return None
        
        # Look for common structure notes
        structure_violations = defaultdict(int)
        structure_trade_ids = defaultdict(list)
        
        for trade in losing_trades:
            if trade.price_action_context and trade.price_action_context.structure_notes:
                for note in trade.price_action_context.structure_notes:
                    # Look for violation keywords
                    note_lower = note.lower()
                    if any(word in note_lower for word in ['against', 'violation', 'weak', 'failed']):
                        structure_violations[note] += 1
                        structure_trade_ids[note].append(trade.id)
        
        if not structure_violations:
            return None
        
        # Find most common violation
        dominant_violation = max(structure_violations.items(), key=lambda x: x[1])
        violation_note = dominant_violation[0]
        count = dominant_violation[1]
        
        if count < self.min_pattern_trades:
            return None
        
        percentage = (count / len(losing_trades)) * 100
        confidence = min(0.85, percentage / 100)
        
        description = (
            f"Structure violation detected: '{violation_note}' "
            f"({percentage:.0f}% of losses)"
        )
        
        return PatternInsight(
            pattern_type="failure_pattern",
            description=description,
            confidence=confidence,
            supporting_trades=structure_trade_ids[violation_note],
            market_conditions={"structure_issue": violation_note},
            impact_score=confidence * (percentage / 100)
        )
    
    # ===== PERFORMANCE ANALYSIS =====
    
    def _analyze_market_cycle_performance(
        self,
        trades: List[TradeRecord],
        worst: bool = False
    ) -> List[Tuple[MarketCycle, float]]:
        """Analyze performance by market cycle."""
        
        cycle_performance = defaultdict(lambda: {'wins': 0, 'total': 0})
        
        for trade in trades:
            if trade.price_action_context and trade.price_action_context.market_cycle:
                cycle = trade.price_action_context.market_cycle
                cycle_performance[cycle]['total'] += 1
                if trade.outcome == TradeOutcome.WIN:
                    cycle_performance[cycle]['wins'] += 1
        
        # Calculate win rates
        cycle_win_rates = []
        for cycle, stats in cycle_performance.items():
            if stats['total'] >= 3:  # Need minimum trades
                win_rate = (stats['wins'] / stats['total']) * 100
                cycle_win_rates.append((cycle, win_rate))
        
        # Sort by win rate
        cycle_win_rates.sort(key=lambda x: x[1], reverse=not worst)
        
        return cycle_win_rates[:3]  # Top/bottom 3
    
    def _analyze_timeframe_performance(
        self,
        trades: List[TradeRecord]
    ) -> List[Tuple[str, float]]:
        """Analyze performance by timeframe."""
        
        # Extract timeframe from trade context
        # This would need to be enhanced based on actual data structure
        # For now, return empty list
        return []
    
    def _analyze_asset_performance(
        self,
        trades: List[TradeRecord]
    ) -> List[Tuple[str, float]]:
        """Analyze performance by asset."""
        
        asset_performance = defaultdict(lambda: {'wins': 0, 'total': 0})
        
        for trade in trades:
            asset = trade.asset
            asset_performance[asset]['total'] += 1
            if trade.outcome == TradeOutcome.WIN:
                asset_performance[asset]['wins'] += 1
        
        # Calculate win rates
        asset_win_rates = []
        for asset, stats in asset_performance.items():
            if stats['total'] >= 3:  # Need minimum trades
                win_rate = (stats['wins'] / stats['total']) * 100
                asset_win_rates.append((asset, win_rate))
        
        # Sort by win rate
        asset_win_rates.sort(key=lambda x: x[1], reverse=True)
        
        return asset_win_rates[:5]  # Top 5 assets
    
    # ===== CONFIDENCE CALCULATION =====
    
    def _calculate_new_confidence(
        self,
        old_confidence: float,
        trade_stats: TradeStatistics,
        success_patterns: List[PatternInsight],
        failure_patterns: List[PatternInsight]
    ) -> float:
        """
        Calculate updated confidence score based on performance and patterns.
        
        Confidence calculation factors:
        - Win rate (50% weight)
        - Profit factor (25% weight)
        - Average R-multiple (15% weight)
        - Pattern quality (10% weight)
        """
        
        # Base confidence from performance metrics
        win_rate_score = trade_stats.win_rate / 100.0
        
        # Profit factor normalized (1.0 = neutral, 2.0+ = excellent)
        pf_score = min(1.0, trade_stats.profit_factor / 2.0) if trade_stats.profit_factor > 0 else 0.0
        
        # R-multiple normalized (1.0 = break-even, 2.0+ = excellent)
        r_score = min(1.0, trade_stats.avg_r_multiple / 2.0) if trade_stats.avg_r_multiple > 0 else 0.0
        
        # Pattern quality score
        success_score = sum(p.impact_score for p in success_patterns) / max(1, len(success_patterns))
        failure_score = sum(p.impact_score for p in failure_patterns) / max(1, len(failure_patterns))
        pattern_score = success_score - (failure_score * 0.5)  # Failures have less weight
        pattern_score = max(0.0, min(1.0, pattern_score))
        
        # Weighted combination
        performance_confidence = (
            win_rate_score * 0.50 +
            pf_score * 0.25 +
            r_score * 0.15 +
            pattern_score * 0.10
        )
        
        # Blend with old confidence (prevents drastic swings)
        blend_factor = 0.7  # 70% new, 30% old
        new_confidence = (performance_confidence * blend_factor) + (old_confidence * (1 - blend_factor))
        
        # Apply adjustment rate limit
        max_change = self.confidence_adjustment_rate
        if abs(new_confidence - old_confidence) > max_change:
            if new_confidence > old_confidence:
                new_confidence = old_confidence + max_change
            else:
                new_confidence = old_confidence - max_change
        
        # Clamp to valid range
        return max(0.1, min(0.95, new_confidence))
    
    # ===== RECOMMENDATIONS =====
    
    def _generate_recommendations(
        self,
        analysis: StrategyAnalysis,
        trade_stats: TradeStatistics
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        
        recommendations = []
        
        # Win rate recommendations
        if analysis.win_rate < 40:
            recommendations.append(
                "Win rate below 40% - consider stricter entry criteria or higher confluence requirement"
            )
        elif analysis.win_rate > 60:
            recommendations.append(
                "Excellent win rate - strategy is well-calibrated"
            )
        
        # Profit factor recommendations
        if trade_stats.profit_factor < 1.5:
            recommendations.append(
                f"Profit factor {trade_stats.profit_factor:.2f} is low - "
                "consider adjusting TP levels or SL distance"
            )
        elif trade_stats.profit_factor > 2.5:
            recommendations.append(
                f"Strong profit factor {trade_stats.profit_factor:.2f} - "
                "strategy has good risk/reward"
            )
        
        # R-multiple recommendations
        if trade_stats.avg_r_multiple < 0.5:
            recommendations.append(
                f"Average R-multiple {trade_stats.avg_r_multiple:.2f} is low - "
                "exits may be too early or SL too wide"
            )
        
        # Pattern-based recommendations
        for pattern in analysis.failure_patterns:
            if pattern.confidence > 0.7:
                recommendations.append(
                    f"Avoid trading: {pattern.description}"
                )
        
        for pattern in analysis.success_patterns:
            if pattern.confidence > 0.7:
                recommendations.append(
                    f"Prioritize: {pattern.description}"
                )
        
        # Market cycle recommendations
        if analysis.best_market_cycles:
            best_cycle = analysis.best_market_cycles[0]
            cycle_name = best_cycle[0].value if hasattr(best_cycle[0], 'value') else str(best_cycle[0])
            recommendations.append(
                f"Strategy performs best in {cycle_name} market cycle ({best_cycle[1]:.0f}% win rate)"
            )
        
        # Asset recommendations
        if analysis.best_assets:
            best_asset = analysis.best_assets[0]
            recommendations.append(
                f"Best performing asset: {best_asset[0]} ({best_asset[1]:.0f}% win rate)"
            )
        
        # Confidence change recommendations
        if analysis.confidence_change < -0.05:
            recommendations.append(
                "Strategy confidence declining - review recent changes and market conditions"
            )
        elif analysis.confidence_change > 0.05:
            recommendations.append(
                "Strategy confidence improving - continue current approach"
            )
        
        return recommendations


# Export
__all__ = [
    "OutcomeAnalyzer",
    "StrategyAnalysis",
    "PatternInsight"
]
