"""Learning service - orchestrates the feedback loop.

This service connects the trade reasoner with the learning repository to:
1. Analyze trade outcomes after they close
2. Extract learnings and patterns from multiple trades
3. Update strategy effectiveness scores
4. Store insights in the learning journal

This implements the core "learning loop" that makes the system improve over time.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID

from hl_bot.repositories.learning_repository import LearningRepository
from hl_bot.services.llm_client import LLMClient
from hl_bot.services.trade_reasoner import (
    LearningInsight,
    OutcomeAnalysis,
    TradeReasoner,
)
from hl_bot.types import Candle, Trade

logger = logging.getLogger(__name__)


class LearningService:
    """Orchestrates the learning feedback loop.
    
    Connects trade analysis with persistent learning storage and
    strategy effectiveness updates.
    """

    def __init__(
        self,
        learning_repo: LearningRepository,
        trade_reasoner: TradeReasoner | None = None,
        llm_client: LLMClient | None = None,
    ):
        """Initialize learning service.
        
        Args:
            learning_repo: Repository for learning journal operations
            trade_reasoner: Trade reasoner instance (creates default if not provided)
            llm_client: LLM client for reasoner (creates default if not provided)
        """
        self._repo = learning_repo
        self._reasoner = trade_reasoner or TradeReasoner(llm_client=llm_client)
        logger.info("Learning service initialized")

    # ========================================================================
    # Post-Trade Analysis
    # ========================================================================

    async def analyze_trade_outcome(
        self,
        trade: Trade,
        entry_reasoning: str,
        entry_candles: List[Candle],
        trade_candles: List[Candle],
    ) -> OutcomeAnalysis:
        """Analyze a closed trade and store learnings.
        
        This is called after a trade closes to:
        1. Get LLM analysis of what happened
        2. Store the outcome analysis in trade_decisions table
        3. Update strategy effectiveness if applicable
        
        Args:
            trade: Completed trade
            entry_reasoning: Original entry reasoning from analyze_setup()
            entry_candles: Price action at entry time
            trade_candles: Price action during the trade
            
        Returns:
            Outcome analysis from LLM
            
        Raises:
            ValueError: If analysis fails
        """
        logger.info(f"Analyzing outcome for trade {trade.id}: {trade.symbol} {trade.side.value}")
        
        # Get LLM outcome analysis
        outcome = await self._reasoner.review_outcome(
            trade=trade,
            entry_reasoning=entry_reasoning,
            entry_candles=entry_candles,
            trade_candles=trade_candles,
        )
        
        logger.info(
            f"Trade outcome analysis complete: "
            f"validity={outcome.setup_validity}, rating={outcome.performance_rating}/5, "
            f"lessons={len(outcome.lessons_learned)}"
        )
        
        # Update strategy effectiveness if this trade is linked to a strategy
        if trade.strategy_id:
            await self._update_strategy_from_trade(trade, outcome)
        
        return outcome

    async def _update_strategy_from_trade(
        self,
        trade: Trade,
        outcome: OutcomeAnalysis,
    ) -> None:
        """Update strategy effectiveness based on a single trade outcome.
        
        Args:
            trade: Completed trade
            outcome: Outcome analysis
        """
        try:
            # Get current strategy performance
            perf = self._repo.get_strategy_performance(trade.strategy_id)
            if not perf:
                logger.warning(f"Strategy {trade.strategy_id} not found for update")
                return
            
            # Calculate new effectiveness score
            # Base on win rate with adjustments for:
            # - Setup validity (invalid setups reduce effectiveness)
            # - Performance rating (execution quality)
            # - Risk/reward achieved
            
            win_rate = perf['win_rate']
            
            # Penalize invalid setups
            validity_factor = {
                'valid': 1.0,
                'edge_case': 0.9,
                'invalid': 0.7,
            }.get(outcome.setup_validity, 0.8)
            
            # Weight by performance rating
            performance_factor = outcome.performance_rating / 5.0
            
            # Combine factors
            # Effectiveness = weighted average of win rate and execution quality
            new_effectiveness = (
                0.6 * win_rate * validity_factor +
                0.4 * performance_factor
            )
            
            # Smooth the update (don't jump too quickly on single trades)
            old_effectiveness = perf['effectiveness_score']
            sample_weight = min(perf['total_trades'] / 20.0, 0.9)  # Cap at 90% old weight
            smoothed_effectiveness = (
                sample_weight * old_effectiveness +
                (1 - sample_weight) * new_effectiveness
            )
            
            # Update in database
            self._repo.update_strategy_effectiveness(
                strategy_id=trade.strategy_id,
                effectiveness_score=smoothed_effectiveness,
            )
            
            logger.info(
                f"Updated strategy {trade.strategy_id} effectiveness: "
                f"{old_effectiveness:.3f} -> {smoothed_effectiveness:.3f} "
                f"(win_rate={win_rate:.2%}, validity={outcome.setup_validity}, "
                f"rating={outcome.performance_rating}/5)"
            )
            
        except Exception as e:
            logger.error(f"Failed to update strategy effectiveness: {e}")

    # ========================================================================
    # Learning Aggregation
    # ========================================================================

    async def aggregate_learnings(
        self,
        filters: Optional[dict[str, Any]] = None,
        min_trades: int = 5,
        max_trades: int = 50,
        min_confidence: float = 0.6,
    ) -> List[LearningInsight]:
        """Aggregate learnings from multiple trades.
        
        This analyzes a batch of trades to extract patterns and insights.
        Called periodically (e.g., daily or weekly) or after significant events.
        
        Args:
            filters: Optional filters for trade selection (symbol, setup_type, etc.)
            min_trades: Minimum trades required to generate insights
            max_trades: Maximum trades to analyze
            min_confidence: Minimum confidence threshold for storing insights
            
        Returns:
            List of learning insights
        """
        logger.info(f"Aggregating learnings with filters: {filters}")
        
        # Get trade summaries
        summaries = self._repo.get_trade_summaries_for_learning(
            filters=filters,
            limit=max_trades,
        )
        
        if len(summaries) < min_trades:
            logger.warning(
                f"Insufficient trades for aggregation: {len(summaries)} < {min_trades}"
            )
            return []
        
        logger.info(f"Analyzing {len(summaries)} trades for patterns")
        
        # Get insights from LLM
        insights = await self._reasoner.aggregate_learnings(
            trade_summaries=summaries,
            min_sample_size=min_trades,
        )
        
        # Filter by confidence and store
        stored_count = 0
        high_confidence_insights = []
        
        for insight in insights:
            if insight.confidence_score >= min_confidence:
                high_confidence_insights.append(insight)
                
                # Store in database
                self._store_insight(insight)
                stored_count += 1
            else:
                logger.debug(
                    f"Skipping low-confidence insight: {insight.insight[:50]}... "
                    f"(confidence={insight.confidence_score:.2f})"
                )
        
        logger.info(
            f"Generated {len(insights)} insights, stored {stored_count} "
            f"with confidence >= {min_confidence}"
        )
        
        return high_confidence_insights

    def _store_insight(self, insight: LearningInsight) -> None:
        """Store a learning insight in the database.
        
        Args:
            insight: Learning insight from LLM
        """
        try:
            # Extract supporting trade IDs if available in market_conditions
            supporting_trades = insight.market_conditions.get('supporting_trades', [])
            
            # Convert to UUIDs if they're strings
            trade_ids = []
            for tid in supporting_trades:
                if isinstance(tid, str):
                    try:
                        trade_ids.append(UUID(tid))
                    except ValueError:
                        continue
                elif isinstance(tid, UUID):
                    trade_ids.append(tid)
            
            self._repo.create_learning_entry(
                insight_type=insight.insight_type,
                insight=insight.insight,
                supporting_trade_ids=trade_ids,
                confidence_score=insight.confidence_score,
                sample_size=insight.sample_size,
                market_conditions=insight.market_conditions,
            )
            
            logger.debug(f"Stored learning: {insight.insight[:60]}...")
            
        except Exception as e:
            logger.error(f"Failed to store insight: {e}")

    # ========================================================================
    # Learning Retrieval
    # ========================================================================

    def get_relevant_learnings(
        self,
        context: dict[str, Any],
        limit: int = 5,
    ) -> List[dict[str, Any]]:
        """Get relevant learnings for a given trading context.
        
        This can be used before taking a trade to check what we've learned
        about similar setups.
        
        Args:
            context: Context dict with symbol, setup_type, market_phase, etc.
            limit: Maximum learnings to return
            
        Returns:
            List of relevant learning entries
        """
        # Get all active learnings
        all_learnings = self._repo.get_learning_entries(
            is_active=True,
            min_confidence=0.5,
            limit=100,
        )
        
        # Score relevance based on context match
        scored_learnings = []
        
        for learning in all_learnings:
            relevance_score = self._calculate_relevance(learning, context)
            if relevance_score > 0:
                scored_learnings.append({
                    'learning': learning,
                    'relevance': relevance_score,
                })
        
        # Sort by relevance * confidence
        scored_learnings.sort(
            key=lambda x: x['relevance'] * x['learning'].confidence_score,
            reverse=True,
        )
        
        # Return top N
        results = []
        for item in scored_learnings[:limit]:
            learning = item['learning']
            results.append({
                'id': str(learning.id),
                'insight_type': learning.insight_type,
                'insight': learning.insight,
                'confidence_score': learning.confidence_score,
                'sample_size': learning.sample_size,
                'relevance': item['relevance'],
            })
        
        return results

    def _calculate_relevance(
        self,
        learning: Any,  # LearningJournal model
        context: dict[str, Any],
    ) -> float:
        """Calculate how relevant a learning is to a given context.
        
        Args:
            learning: LearningJournal database model
            context: Trading context dict
            
        Returns:
            Relevance score (0-1)
        """
        score = 0.0
        conditions = learning.market_conditions or {}
        
        # Match setup type
        if context.get('setup_type') and conditions.get('setup_type') == context['setup_type']:
            score += 0.3
        
        # Match market phase
        if context.get('market_phase') and conditions.get('market_phase') == context['market_phase']:
            score += 0.3
        
        # Match symbol
        if context.get('symbol') and conditions.get('symbol') == context['symbol']:
            score += 0.2
        
        # Match timeframe
        if context.get('timeframe') and conditions.get('timeframe') == context['timeframe']:
            score += 0.2
        
        return min(score, 1.0)

    # ========================================================================
    # Maintenance Operations
    # ========================================================================

    def prune_low_confidence_learnings(
        self,
        threshold: float = 0.3,
    ) -> int:
        """Deactivate learning entries with low confidence.
        
        Should be run periodically to keep the learning journal clean.
        
        Args:
            threshold: Confidence threshold below which to deactivate
            
        Returns:
            Number of entries deactivated
        """
        count = self._repo.deactivate_low_confidence_entries(threshold)
        logger.info(f"Deactivated {count} low-confidence learning entries (threshold={threshold})")
        return count

    def update_strategy_effectiveness_batch(
        self,
        strategy_ids: Optional[List[UUID]] = None,
    ) -> dict[str, int]:
        """Recalculate effectiveness scores for strategies.
        
        This can be run periodically to ensure effectiveness scores
        are up-to-date based on all historical trades.
        
        Args:
            strategy_ids: Optional list of strategy IDs to update (updates all if None)
            
        Returns:
            Dict with update statistics
        """
        # Implementation would query all strategies and recalculate
        # their effectiveness based on all associated trades
        # For now, this is a placeholder
        logger.info("Batch strategy effectiveness update not yet implemented")
        return {'updated': 0, 'skipped': 0}

    # ========================================================================
    # Reporting
    # ========================================================================

    def get_learning_summary(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get a summary of learnings over a time period.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Summary dict with learning statistics
        """
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get all learnings from the period
        learnings = self._repo.get_learning_entries(
            is_active=True,
        )
        
        # Filter by date
        recent_learnings = [
            l for l in learnings
            if l.created_at >= start_time
        ]
        
        # Group by type
        by_type = {}
        for learning in recent_learnings:
            insight_type = learning.insight_type
            if insight_type not in by_type:
                by_type[insight_type] = []
            by_type[insight_type].append(learning)
        
        # Calculate stats
        summary = {
            'period_days': days,
            'total_learnings': len(recent_learnings),
            'avg_confidence': (
                sum(l.confidence_score for l in recent_learnings) / len(recent_learnings)
                if recent_learnings else 0.0
            ),
            'by_type': {
                itype: {
                    'count': len(items),
                    'avg_confidence': sum(l.confidence_score for l in items) / len(items),
                    'total_sample_size': sum(l.sample_size for l in items),
                }
                for itype, items in by_type.items()
            },
            'top_insights': [
                {
                    'insight': l.insight,
                    'confidence': l.confidence_score,
                    'sample_size': l.sample_size,
                }
                for l in sorted(
                    recent_learnings,
                    key=lambda x: x.confidence_score * x.sample_size,
                    reverse=True,
                )[:5]
            ],
        }
        
        return summary
