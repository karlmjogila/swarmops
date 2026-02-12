"""
Feedback Loop Module

Closes the learning loop by:
1. Analyzing trade outcomes via OutcomeAnalyzer
2. Updating strategy confidence scores
3. Storing learning insights
4. Providing context to trade reasoner
5. Tracking improvement metrics over time
6. Supporting A/B testing of strategy variations

This is the brain of the self-improving system. It takes what the outcome analyzer
learned and applies those insights back into the trading system to make better
decisions over time.

Author: Hyperliquid Trading Bot Suite
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session

from ..types import StrategyRule, TradeRecord, LearningEntry
from ..knowledge.repository import (
    StrategyRuleRepository, TradeRecordRepository, LearningRepository
)
from .outcome_analyzer import (
    OutcomeAnalyzer, StrategyAnalysis, PatternInsight
)
from ..database import get_session


logger = logging.getLogger(__name__)


@dataclass
class LearningContext:
    """
    Learning context to inject into trade reasoner.
    
    Contains high-confidence insights and patterns that should influence
    trade decisions.
    """
    strategy_rule_id: str
    success_factors: List[str] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    recommended_conditions: Dict[str, Any] = field(default_factory=dict)
    avoid_conditions: Dict[str, Any] = field(default_factory=dict)
    confidence_adjustment: float = 0.0  # -0.2 to +0.2
    
    def to_prompt_text(self) -> str:
        """Format learning context as text for LLM prompt."""
        lines = []
        
        if self.success_factors:
            lines.append("Known success factors for this strategy:")
            for factor in self.success_factors:
                lines.append(f"  ✓ {factor}")
        
        if self.failure_patterns:
            lines.append("\nKnown failure patterns to avoid:")
            for pattern in self.failure_patterns:
                lines.append(f"  ✗ {pattern}")
        
        if self.recommended_conditions:
            lines.append("\nRecommended conditions:")
            for key, value in self.recommended_conditions.items():
                lines.append(f"  • {key}: {value}")
        
        if self.avoid_conditions:
            lines.append("\nAvoid trading when:")
            for key, value in self.avoid_conditions.items():
                lines.append(f"  • {key}: {value}")
        
        if self.confidence_adjustment != 0:
            direction = "increased" if self.confidence_adjustment > 0 else "decreased"
            lines.append(
                f"\nStrategy confidence {direction} by "
                f"{abs(self.confidence_adjustment):.1%} based on historical performance."
            )
        
        return "\n".join(lines) if lines else "No specific learnings yet for this strategy."


@dataclass
class ImprovementMetrics:
    """Metrics tracking system improvement over time."""
    period_start: datetime
    period_end: datetime
    
    # Strategy metrics
    total_strategies: int = 0
    strategies_improved: int = 0
    strategies_declined: int = 0
    avg_confidence_change: float = 0.0
    
    # Learning metrics
    total_insights_generated: int = 0
    high_confidence_insights: int = 0
    
    # Performance metrics
    overall_win_rate: float = 0.0
    overall_profit_factor: float = 0.0
    overall_avg_r: float = 0.0
    
    # Trend indicators
    win_rate_trend: str = "stable"  # "improving", "declining", "stable"
    confidence_trend: str = "stable"
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Improvement Metrics ({self.period_start.date()} to {self.period_end.date()}):\n"
            f"  Strategies: {self.total_strategies} ({self.strategies_improved} improved, "
            f"{self.strategies_declined} declined)\n"
            f"  Avg Confidence Change: {self.avg_confidence_change:+.2%}\n"
            f"  Insights Generated: {self.total_insights_generated} "
            f"({self.high_confidence_insights} high confidence)\n"
            f"  Performance: {self.overall_win_rate:.1%} win rate, "
            f"{self.overall_profit_factor:.2f} PF, {self.overall_avg_r:.2f}R avg\n"
            f"  Trends: Win rate {self.win_rate_trend}, Confidence {self.confidence_trend}"
        )


@dataclass
class ABTestVariant:
    """A/B test variant of a strategy."""
    variant_id: str
    base_strategy_id: str
    variant_name: str
    modifications: Dict[str, Any]  # What's different from base
    trade_count: int = 0
    win_rate: float = 0.0
    avg_r_multiple: float = 0.0
    confidence: float = 0.5
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class FeedbackLoop:
    """
    Closes the learning loop by applying insights back to the system.
    
    This is the core of the self-improving mechanism. It:
    1. Periodically analyzes trade outcomes
    2. Updates strategy confidence scores
    3. Stores high-quality learning insights
    4. Provides learning context to trade reasoner
    5. Tracks improvement over time
    6. Manages A/B testing of strategy variations
    """
    
    def __init__(
        self,
        session: Optional[Session] = None,
        min_trades_for_update: int = 10,
        confidence_update_threshold: float = 0.05,
        learning_confidence_threshold: float = 0.6,
        improvement_window_days: int = 30
    ):
        """
        Initialize feedback loop.
        
        Args:
            session: Database session (or create new one)
            min_trades_for_update: Minimum trades before updating confidence
            confidence_update_threshold: Minimum change to trigger update
            learning_confidence_threshold: Minimum confidence for storing learnings
            improvement_window_days: Days to look back for improvement tracking
        """
        self._session = session
        self._own_session = session is None
        
        self.min_trades_for_update = min_trades_for_update
        self.confidence_update_threshold = confidence_update_threshold
        self.learning_confidence_threshold = learning_confidence_threshold
        self.improvement_window_days = improvement_window_days
        
        self.outcome_analyzer = OutcomeAnalyzer(
            min_trades_for_analysis=min_trades_for_update,
            pattern_confidence_threshold=learning_confidence_threshold
        )
        
        # A/B test tracking
        self._ab_variants: Dict[str, List[ABTestVariant]] = defaultdict(list)
        
        logger.info(
            f"FeedbackLoop initialized: min_trades={min_trades_for_update}, "
            f"confidence_threshold={confidence_update_threshold:.2%}, "
            f"learning_threshold={learning_confidence_threshold:.2%}"
        )
    
    def __enter__(self):
        if self._own_session:
            self._session_ctx = get_session()
            self._session = self._session_ctx.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and hasattr(self, '_session_ctx'):
            self._session_ctx.__exit__(exc_type, exc_val, exc_tb)
    
    def run_feedback_cycle(
        self,
        strategy_ids: Optional[List[str]] = None,
        force_update: bool = False
    ) -> List[StrategyAnalysis]:
        """
        Run a complete feedback cycle: analyze, update, store learnings.
        
        Args:
            strategy_ids: Specific strategies to analyze (or all if None)
            force_update: Force update even if below minimum trades
            
        Returns:
            List of StrategyAnalysis results
        """
        logger.info(
            f"Starting feedback cycle for "
            f"{len(strategy_ids) if strategy_ids else 'all'} strategies"
        )
        
        with StrategyRuleRepository(self._session) as strategy_repo, \
             TradeRecordRepository(self._session) as trade_repo, \
             LearningRepository(self._session) as learning_repo:
            
            # Get strategies to analyze
            if strategy_ids:
                strategies = [
                    strategy_repo.get_by_id(sid) 
                    for sid in strategy_ids 
                    if strategy_repo.get_by_id(sid)
                ]
            else:
                strategies = strategy_repo.get_all(limit=1000)
            
            if not strategies:
                logger.warning("No strategies found to analyze")
                return []
            
            # Gather trades for each strategy
            trades_by_strategy = {}
            existing_learnings = {}
            
            for strategy in strategies:
                trades = trade_repo.get_by_strategy_rule(strategy.id)
                trades_by_strategy[strategy.id] = trades
                
                learnings = learning_repo.get_by_strategy_rule(strategy.id)
                existing_learnings[strategy.id] = learnings
            
            # Analyze all strategies
            analyses = self.outcome_analyzer.analyze_all_strategies(
                strategies,
                trades_by_strategy,
                existing_learnings
            )
            
            # Apply learnings
            updates_count = 0
            learnings_count = 0
            
            for analysis in analyses:
                # Update confidence scores
                if self._should_update_confidence(analysis, force_update):
                    success = self._update_strategy_confidence(
                        strategy_repo, analysis
                    )
                    if success:
                        updates_count += 1
                
                # Store learning insights
                insights = self._store_learning_insights(
                    learning_repo, analysis
                )
                learnings_count += len(insights)
            
            # Commit changes
            self._session.commit()
            
            logger.info(
                f"Feedback cycle complete: {len(analyses)} strategies analyzed, "
                f"{updates_count} confidence scores updated, "
                f"{learnings_count} new insights stored"
            )
            
            return analyses
    
    def get_learning_context(
        self,
        strategy_rule_id: str,
        min_confidence: float = 0.6
    ) -> LearningContext:
        """
        Get learning context for a strategy to inject into trade reasoner.
        
        Args:
            strategy_rule_id: Strategy rule ID
            min_confidence: Minimum confidence for insights
            
        Returns:
            LearningContext with actionable insights
        """
        with LearningRepository(self._session) as learning_repo, \
             StrategyRuleRepository(self._session) as strategy_repo:
            
            # Get strategy
            strategy = strategy_repo.get_by_id(strategy_rule_id)
            if not strategy:
                logger.warning(f"Strategy {strategy_rule_id} not found")
                return LearningContext(strategy_rule_id=strategy_rule_id)
            
            # Get learning entries
            learnings = learning_repo.get_by_strategy_rule(strategy_rule_id)
            high_conf_learnings = [
                l for l in learnings 
                if l.confidence >= min_confidence
            ]
            
            context = LearningContext(strategy_rule_id=strategy_rule_id)
            
            # Separate success factors and failure patterns
            for learning in high_conf_learnings:
                if learning.impact_type == "success_factor":
                    context.success_factors.append(learning.insight)
                    
                    # Extract recommended conditions
                    if learning.market_conditions:
                        for key, value in learning.market_conditions.items():
                            if key not in context.recommended_conditions:
                                context.recommended_conditions[key] = value
                
                elif learning.impact_type == "failure_pattern":
                    context.failure_patterns.append(learning.insight)
                    
                    # Extract conditions to avoid
                    if learning.market_conditions:
                        for key, value in learning.market_conditions.items():
                            if key not in context.avoid_conditions:
                                context.avoid_conditions[key] = value
            
            # Calculate confidence adjustment based on recent performance
            # This gives a +/- adjustment to confidence scores
            if strategy.confidence > 0.7:
                context.confidence_adjustment = 0.1
            elif strategy.confidence < 0.4:
                context.confidence_adjustment = -0.1
            
            logger.debug(
                f"Learning context for {strategy.name}: "
                f"{len(context.success_factors)} success factors, "
                f"{len(context.failure_patterns)} failure patterns"
            )
            
            return context
    
    def track_improvement(
        self,
        lookback_days: Optional[int] = None
    ) -> ImprovementMetrics:
        """
        Track overall system improvement over time.
        
        Args:
            lookback_days: Days to look back (or use default window)
            
        Returns:
            ImprovementMetrics with trends and statistics
        """
        lookback = lookback_days or self.improvement_window_days
        period_start = datetime.utcnow() - timedelta(days=lookback)
        period_end = datetime.utcnow()
        
        logger.info(f"Tracking improvement over last {lookback} days")
        
        with StrategyRuleRepository(self._session) as strategy_repo, \
             TradeRecordRepository(self._session) as trade_repo, \
             LearningRepository(self._session) as learning_repo:
            
            metrics = ImprovementMetrics(
                period_start=period_start,
                period_end=period_end
            )
            
            # Get all strategies
            strategies = strategy_repo.get_all(limit=1000)
            metrics.total_strategies = len(strategies)
            
            # Calculate confidence changes
            confidence_changes = []
            for strategy in strategies:
                # Compare current confidence to baseline (0.5 is initial)
                change = strategy.confidence - 0.5
                confidence_changes.append(change)
                
                if change > 0.05:
                    metrics.strategies_improved += 1
                elif change < -0.05:
                    metrics.strategies_declined += 1
            
            if confidence_changes:
                metrics.avg_confidence_change = statistics.mean(confidence_changes)
            
            # Get recent learning insights
            all_learnings = learning_repo.get_high_confidence_insights(
                min_confidence=self.learning_confidence_threshold
            )
            recent_learnings = [
                l for l in all_learnings 
                if l.created_at >= period_start
            ]
            metrics.total_insights_generated = len(recent_learnings)
            metrics.high_confidence_insights = len([
                l for l in recent_learnings 
                if l.confidence >= 0.8
            ])
            
            # Get recent trades for performance metrics
            recent_trades = trade_repo.get_recent(
                limit=10000,
                start_date=period_start
            )
            
            if recent_trades:
                wins = [t for t in recent_trades if t.outcome.value == "win"]
                metrics.overall_win_rate = len(wins) / len(recent_trades)
                
                # Calculate profit factor
                gross_profit = sum(t.pnl_r_multiple for t in wins if t.pnl_r_multiple)
                losses = [t for t in recent_trades if t.outcome.value == "loss"]
                gross_loss = abs(sum(
                    t.pnl_r_multiple for t in losses if t.pnl_r_multiple
                ))
                
                if gross_loss > 0:
                    metrics.overall_profit_factor = gross_profit / gross_loss
                
                # Average R-multiple
                r_multiples = [
                    t.pnl_r_multiple for t in recent_trades 
                    if t.pnl_r_multiple is not None
                ]
                if r_multiples:
                    metrics.overall_avg_r = statistics.mean(r_multiples)
            
            # Determine trends
            metrics.confidence_trend = self._determine_trend(
                metrics.avg_confidence_change
            )
            
            # Win rate trend (compare to 50% baseline)
            if metrics.overall_win_rate > 0.55:
                metrics.win_rate_trend = "improving"
            elif metrics.overall_win_rate < 0.45:
                metrics.win_rate_trend = "declining"
            else:
                metrics.win_rate_trend = "stable"
            
            logger.info(f"Improvement tracking complete:\n{metrics}")
            
            return metrics
    
    def create_ab_variant(
        self,
        base_strategy_id: str,
        variant_name: str,
        modifications: Dict[str, Any]
    ) -> ABTestVariant:
        """
        Create an A/B test variant of a strategy.
        
        Args:
            base_strategy_id: Base strategy to create variant from
            variant_name: Name for the variant
            modifications: Dict of modifications (e.g., {"min_confluence": 0.7})
            
        Returns:
            ABTestVariant instance
        """
        variant = ABTestVariant(
            variant_id=f"{base_strategy_id}_variant_{len(self._ab_variants[base_strategy_id]) + 1}",
            base_strategy_id=base_strategy_id,
            variant_name=variant_name,
            modifications=modifications
        )
        
        self._ab_variants[base_strategy_id].append(variant)
        
        logger.info(
            f"Created A/B variant '{variant_name}' for strategy {base_strategy_id}"
        )
        
        return variant
    
    def update_ab_variant_stats(
        self,
        variant_id: str,
        trade_count: int,
        win_rate: float,
        avg_r_multiple: float
    ) -> None:
        """Update statistics for an A/B test variant."""
        for variants in self._ab_variants.values():
            for variant in variants:
                if variant.variant_id == variant_id:
                    variant.trade_count = trade_count
                    variant.win_rate = win_rate
                    variant.avg_r_multiple = avg_r_multiple
                    
                    # Update confidence based on performance
                    if trade_count >= self.min_trades_for_update:
                        variant.confidence = (
                            win_rate * 0.6 + 
                            min(1.0, avg_r_multiple / 2.0) * 0.4
                        )
                    
                    logger.info(
                        f"Updated A/B variant {variant_id}: "
                        f"{trade_count} trades, {win_rate:.1%} WR, "
                        f"{avg_r_multiple:.2f}R avg"
                    )
                    return
    
    def select_best_variant(
        self,
        base_strategy_id: str,
        min_trades: int = 30
    ) -> Optional[ABTestVariant]:
        """
        Select the best performing A/B variant.
        
        Args:
            base_strategy_id: Base strategy ID
            min_trades: Minimum trades required for selection
            
        Returns:
            Best variant or None if insufficient data
        """
        variants = self._ab_variants.get(base_strategy_id, [])
        
        # Filter variants with sufficient trades
        eligible = [v for v in variants if v.trade_count >= min_trades]
        
        if not eligible:
            logger.info(
                f"No A/B variants for {base_strategy_id} have {min_trades}+ trades yet"
            )
            return None
        
        # Sort by confidence (derived from performance)
        eligible.sort(key=lambda v: v.confidence, reverse=True)
        best = eligible[0]
        
        logger.info(
            f"Best A/B variant for {base_strategy_id}: '{best.variant_name}' "
            f"({best.win_rate:.1%} WR, {best.avg_r_multiple:.2f}R avg, "
            f"{best.confidence:.2f} confidence)"
        )
        
        return best
    
    # ===== PRIVATE METHODS =====
    
    def _should_update_confidence(
        self,
        analysis: StrategyAnalysis,
        force: bool
    ) -> bool:
        """Determine if strategy confidence should be updated."""
        if force:
            return True
        
        if analysis.total_trades < self.min_trades_for_update:
            return False
        
        change_magnitude = abs(analysis.confidence_change)
        if change_magnitude < self.confidence_update_threshold:
            logger.debug(
                f"Confidence change {change_magnitude:.2%} below threshold "
                f"{self.confidence_update_threshold:.2%} for {analysis.strategy_name}"
            )
            return False
        
        return True
    
    def _update_strategy_confidence(
        self,
        strategy_repo: StrategyRuleRepository,
        analysis: StrategyAnalysis
    ) -> bool:
        """Update strategy confidence score in database."""
        success = strategy_repo.update_performance(
            rule_id=analysis.strategy_rule_id,
            win_rate=analysis.win_rate,
            avg_r_multiple=analysis.avg_r_multiple,
            confidence=analysis.new_confidence
        )
        
        if success:
            logger.info(
                f"Updated {analysis.strategy_name} confidence: "
                f"{analysis.old_confidence:.2f} → {analysis.new_confidence:.2f} "
                f"({analysis.confidence_change:+.2f})"
            )
        else:
            logger.warning(
                f"Failed to update confidence for {analysis.strategy_name}"
            )
        
        return success
    
    def _store_learning_insights(
        self,
        learning_repo: LearningRepository,
        analysis: StrategyAnalysis
    ) -> List[LearningEntry]:
        """Store high-confidence learning insights."""
        stored_entries = []
        
        # Generate learning entries from analysis
        entries = self.outcome_analyzer.generate_learning_entries(analysis)
        
        # Store each entry
        for entry in entries:
            try:
                entry_id = learning_repo.create(entry)
                entry.id = entry_id
                stored_entries.append(entry)
                
                logger.debug(
                    f"Stored learning insight for {analysis.strategy_name}: "
                    f"{entry.insight[:60]}..."
                )
            except Exception as e:
                logger.error(
                    f"Failed to store learning entry: {e}"
                )
        
        if stored_entries:
            logger.info(
                f"Stored {len(stored_entries)} learning insights for "
                f"{analysis.strategy_name}"
            )
        
        return stored_entries
    
    def _determine_trend(self, value: float) -> str:
        """Determine trend direction from value."""
        if value > 0.03:
            return "improving"
        elif value < -0.03:
            return "declining"
        else:
            return "stable"


# Convenience function for running feedback cycles
def run_feedback_cycle(
    strategy_ids: Optional[List[str]] = None,
    force_update: bool = False,
    session: Optional[Session] = None
) -> List[StrategyAnalysis]:
    """
    Convenience function to run a feedback cycle.
    
    Args:
        strategy_ids: Specific strategies to analyze
        force_update: Force update even if below minimum trades
        session: Database session
        
    Returns:
        List of StrategyAnalysis results
    """
    with FeedbackLoop(session=session) as feedback_loop:
        return feedback_loop.run_feedback_cycle(
            strategy_ids=strategy_ids,
            force_update=force_update
        )


# Export
__all__ = [
    "FeedbackLoop",
    "LearningContext",
    "ImprovementMetrics",
    "ABTestVariant",
    "run_feedback_cycle"
]
