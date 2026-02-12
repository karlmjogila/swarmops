"""Learning journal repository.

Repository for learning journal entries and strategy effectiveness updates.
Follows Database Excellence principles: specific queries, proper constraints,
batch operations where beneficial.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Import from existing app structure
import sys
sys.path.insert(0, '/opt/swarmops/projects/hl-bot-v2/backend')
from app.db.models import LearningJournal, StrategyRule, Trade, TradeDecision


class LearningRepository:
    """Repository for learning journal and strategy effectiveness updates.
    
    Manages the persistence of learning insights and tracks strategy performance.
    """

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self._db = db

    # ========================================================================
    # Learning Journal Operations
    # ========================================================================

    def create_learning_entry(
        self,
        insight_type: str,
        insight: str,
        supporting_trade_ids: List[UUID],
        confidence_score: float,
        sample_size: int,
        market_conditions: Optional[dict[str, Any]] = None,
    ) -> LearningJournal:
        """Create a new learning journal entry.
        
        Args:
            insight_type: Type of insight (pattern, setup, market_phase, risk, execution)
            insight: The learning/insight text
            supporting_trade_ids: List of trade IDs supporting this insight
            confidence_score: Confidence score (0-1)
            sample_size: Number of trades analyzed
            market_conditions: Optional market conditions context
            
        Returns:
            Created learning journal entry
        """
        entry = LearningJournal(
            insight_type=insight_type,
            insight=insight,
            supporting_trades=[str(tid) for tid in supporting_trade_ids],
            confidence_score=confidence_score,
            sample_size=sample_size,
            market_conditions=market_conditions or {},
            is_active=True,
        )
        
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)
        
        return entry

    def get_learning_entries(
        self,
        insight_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        is_active: Optional[bool] = True,
        limit: Optional[int] = None,
    ) -> List[LearningJournal]:
        """Get learning journal entries with filters.
        
        Args:
            insight_type: Optional filter by insight type
            min_confidence: Optional minimum confidence score
            is_active: Optional filter by active status (default: True)
            limit: Optional limit on results
            
        Returns:
            List of learning journal entries
        """
        query = self._db.query(LearningJournal)
        
        if insight_type:
            query = query.filter(LearningJournal.insight_type == insight_type)
        
        if min_confidence is not None:
            query = query.filter(LearningJournal.confidence_score >= min_confidence)
        
        if is_active is not None:
            query = query.filter(LearningJournal.is_active == is_active)
        
        # Order by confidence and recency
        query = query.order_by(
            desc(LearningJournal.confidence_score),
            desc(LearningJournal.created_at),
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def get_learning_entry(self, entry_id: UUID) -> Optional[LearningJournal]:
        """Get a specific learning entry by ID.
        
        Args:
            entry_id: Learning journal entry ID
            
        Returns:
            Learning entry or None if not found
        """
        return self._db.query(LearningJournal).filter(
            LearningJournal.id == entry_id
        ).first()

    def update_learning_entry(
        self,
        entry_id: UUID,
        confidence_score: Optional[float] = None,
        sample_size: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[LearningJournal]:
        """Update a learning journal entry.
        
        Args:
            entry_id: Learning journal entry ID
            confidence_score: Optional new confidence score
            sample_size: Optional new sample size
            is_active: Optional new active status
            
        Returns:
            Updated entry or None if not found
        """
        entry = self.get_learning_entry(entry_id)
        if not entry:
            return None
        
        if confidence_score is not None:
            entry.confidence_score = confidence_score
        if sample_size is not None:
            entry.sample_size = sample_size
        if is_active is not None:
            entry.is_active = is_active
        
        entry.updated_at = datetime.now(timezone.utc)
        
        self._db.commit()
        self._db.refresh(entry)
        
        return entry

    def deactivate_low_confidence_entries(self, threshold: float = 0.3) -> int:
        """Deactivate learning entries with low confidence.
        
        Args:
            threshold: Confidence threshold below which to deactivate
            
        Returns:
            Number of entries deactivated
        """
        stmt = (
            update(LearningJournal)
            .where(
                and_(
                    LearningJournal.confidence_score < threshold,
                    LearningJournal.is_active == True,
                )
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        
        result = self._db.execute(stmt)
        self._db.commit()
        
        return result.rowcount

    # ========================================================================
    # Strategy Effectiveness Operations
    # ========================================================================

    def update_strategy_effectiveness(
        self,
        strategy_id: UUID,
        effectiveness_score: float,
        total_trades: Optional[int] = None,
        winning_trades: Optional[int] = None,
    ) -> Optional[StrategyRule]:
        """Update strategy effectiveness metrics.
        
        Args:
            strategy_id: Strategy rule ID
            effectiveness_score: New effectiveness score (0-1)
            total_trades: Optional total trades count
            winning_trades: Optional winning trades count
            
        Returns:
            Updated strategy or None if not found
        """
        strategy = self._db.query(StrategyRule).filter(
            StrategyRule.id == strategy_id
        ).first()
        
        if not strategy:
            return None
        
        strategy.effectiveness_score = max(0.0, min(1.0, effectiveness_score))
        
        if total_trades is not None:
            strategy.total_trades = total_trades
        if winning_trades is not None:
            strategy.winning_trades = winning_trades
        
        strategy.updated_at = datetime.now(timezone.utc)
        
        self._db.commit()
        self._db.refresh(strategy)
        
        return strategy

    def get_strategy_performance(self, strategy_id: UUID) -> Optional[dict[str, Any]]:
        """Get comprehensive performance metrics for a strategy.
        
        Args:
            strategy_id: Strategy rule ID
            
        Returns:
            Performance metrics dict or None if strategy not found
        """
        strategy = self._db.query(StrategyRule).filter(
            StrategyRule.id == strategy_id
        ).first()
        
        if not strategy:
            return None
        
        # Get trade statistics from database
        trades_query = self._db.query(Trade).filter(
            and_(
                Trade.strategy_id == strategy_id,
                Trade.status.in_(['closed', 'stopped', 'tp1_hit', 'tp2_hit', 'tp3_hit']),
            )
        )
        
        total_trades = trades_query.count()
        
        # Count winning trades (positive P&L)
        winning_trades = trades_query.filter(Trade.pnl > 0).count()
        
        # Calculate average P&L
        avg_pnl = self._db.query(func.avg(Trade.pnl)).filter(
            and_(
                Trade.strategy_id == strategy_id,
                Trade.status.in_(['closed', 'stopped', 'tp1_hit', 'tp2_hit', 'tp3_hit']),
                Trade.pnl.isnot(None),
            )
        ).scalar() or 0.0
        
        # Calculate total P&L
        total_pnl = self._db.query(func.sum(Trade.pnl)).filter(
            and_(
                Trade.strategy_id == strategy_id,
                Trade.status.in_(['closed', 'stopped', 'tp1_hit', 'tp2_hit', 'tp3_hit']),
                Trade.pnl.isnot(None),
            )
        ).scalar() or 0.0
        
        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy.name,
            'effectiveness_score': strategy.effectiveness_score,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0.0,
            'avg_pnl': float(avg_pnl),
            'total_pnl': float(total_pnl),
        }

    # ========================================================================
    # Trade Analysis Operations
    # ========================================================================

    def get_trades_for_analysis(
        self,
        symbol: Optional[str] = None,
        setup_type: Optional[str] = None,
        market_phase: Optional[str] = None,
        min_confluence: Optional[float] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> List[tuple[Trade, Optional[TradeDecision]]]:
        """Get trades with their decisions for learning analysis.
        
        Args:
            symbol: Optional filter by symbol
            setup_type: Optional filter by setup type
            market_phase: Optional filter by market phase
            min_confluence: Optional minimum confluence score
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Optional limit on results
            
        Returns:
            List of (Trade, TradeDecision) tuples
        """
        query = (
            self._db.query(Trade, TradeDecision)
            .outerjoin(TradeDecision, Trade.id == TradeDecision.trade_id)
            .filter(
                Trade.status.in_(['closed', 'stopped', 'tp1_hit', 'tp2_hit', 'tp3_hit'])
            )
        )
        
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        if setup_type:
            query = query.filter(Trade.setup_type == setup_type)
        if market_phase:
            query = query.filter(Trade.market_phase == market_phase)
        if min_confluence:
            query = query.filter(Trade.confluence_score >= min_confluence)
        if start_time:
            query = query.filter(Trade.entry_time >= start_time)
        if end_time:
            query = query.filter(Trade.entry_time <= end_time)
        
        query = query.order_by(desc(Trade.entry_time))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def get_trade_summaries_for_learning(
        self,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[dict[str, Any]]:
        """Get trade summaries formatted for learning aggregation.
        
        Args:
            filters: Optional filters dict (symbol, setup_type, etc.)
            limit: Maximum trades to return
            
        Returns:
            List of trade summary dicts suitable for LLM analysis
        """
        filters = filters or {}
        
        trades_with_decisions = self.get_trades_for_analysis(
            symbol=filters.get('symbol'),
            setup_type=filters.get('setup_type'),
            market_phase=filters.get('market_phase'),
            min_confluence=filters.get('min_confluence'),
            start_time=filters.get('start_time'),
            end_time=filters.get('end_time'),
            limit=limit,
        )
        
        summaries = []
        for trade, decision in trades_with_decisions:
            summary = {
                'trade_id': str(trade.id),
                'symbol': trade.symbol,
                'side': trade.side,
                'setup_type': trade.setup_type,
                'market_phase': trade.market_phase,
                'confluence_score': trade.confluence_score,
                'patterns': trade.patterns_detected,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'pnl_percent': trade.pnl_percent,
                'status': trade.status,
                'outcome': 'win' if trade.pnl and trade.pnl > 0 else 'loss',
            }
            
            if decision:
                summary['reasoning'] = decision.reasoning
                summary['outcome_analysis'] = decision.outcome_analysis
                summary['lessons_learned'] = decision.lessons_learned
            
            summaries.append(summary)
        
        return summaries

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def create_learning_entries_batch(
        self,
        entries: List[dict[str, Any]],
    ) -> int:
        """Create multiple learning entries efficiently.
        
        Args:
            entries: List of entry dicts with required fields
            
        Returns:
            Number of entries created
        """
        if not entries:
            return 0
        
        # Add timestamps
        now = datetime.now(timezone.utc)
        for entry in entries:
            entry.setdefault('created_at', now)
            entry.setdefault('updated_at', now)
            entry.setdefault('is_active', True)
        
        stmt = insert(LearningJournal).values(entries)
        
        result = self._db.execute(stmt)
        self._db.commit()
        
        return result.rowcount
