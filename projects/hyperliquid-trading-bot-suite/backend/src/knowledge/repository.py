"""
Repository layer for the knowledge base.
Provides CRUD operations and business logic for strategy rules, trades, and learning.
Includes caching and semantic search capabilities.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from uuid import uuid4

from sqlalchemy import and_, desc, func, or_, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound

from ..database import get_session
from ..database.models import (
    StrategyRuleDB, TradeRecordDB, LearningEntryDB, CandleDataDB,
    BacktestConfigDB, BacktestResultDB, IngestionTaskDB
)
from .models import (
    StrategyRule, TradeRecord, LearningEntry, CandleData,
    BacktestConfig, BacktestResult, StrategyPerformance,
    ContentSource, RiskParameters, PriceActionSnapshot
)
from .cache import cache_manager, CacheKeys, CacheTTL
from .semantic_search import SemanticSearch


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._own_session = session is None
    
    @property
    def session(self) -> Session:
        """Get current session or create new one."""
        if self._session is None:
            # This will be managed by context manager
            raise RuntimeError("No session available")
        return self._session
    
    def __enter__(self):
        if self._own_session:
            self._session_manager = get_session()
            self._session = self._session_manager.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and hasattr(self, '_session_manager'):
            self._session_manager.__exit__(exc_type, exc_val, exc_tb)


class StrategyRuleRepository(BaseRepository):
    """Repository for strategy rules with caching and semantic search."""
    
    def __init__(self, session: Optional[Session] = None, use_cache: bool = True):
        super().__init__(session)
        self.use_cache = use_cache
        self._semantic_search = None
    
    @property
    def semantic_search(self) -> SemanticSearch:
        """Get semantic search instance (lazy initialization)."""
        if self._semantic_search is None:
            self._semantic_search = SemanticSearch(self.session)
        return self._semantic_search
    
    def create(self, strategy_rule: StrategyRule) -> str:
        """Create a new strategy rule."""
        db_rule = StrategyRuleDB(
            id=strategy_rule.id or str(uuid4()),
            name=strategy_rule.name,
            source_type=strategy_rule.source.type.value,
            source_ref=strategy_rule.source.ref,
            source_timestamp=strategy_rule.source.timestamp,
            source_page_number=strategy_rule.source.page_number,
            entry_type=strategy_rule.entry_type.value,
            conditions=[condition.dict() for condition in strategy_rule.conditions],
            confluence_required=[tf.dict() for tf in strategy_rule.confluence_required],
            risk_params=strategy_rule.risk_params.dict(),
            confidence=strategy_rule.confidence,
            description=strategy_rule.description,
            tags=strategy_rule.tags or []
        )
        
        self.session.add(db_rule)
        self.session.flush()
        
        # Generate embedding for semantic search
        try:
            self.semantic_search.update_rule_embedding(db_rule.id)
        except Exception as e:
            print(f"Warning: Could not generate embedding for rule {db_rule.id}: {e}")
        
        # Invalidate cache
        if self.use_cache:
            cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:strategy_rules:*")
        
        return db_rule.id
    
    def get_by_id(self, rule_id: str, use_cache: bool = True) -> Optional[StrategyRule]:
        """Get strategy rule by ID with optional caching."""
        # Try cache first
        if use_cache and self.use_cache:
            cache_key = CacheKeys.strategy_rule(rule_id)
            cached = cache_manager.get(cache_key)
            if cached:
                return StrategyRule(**cached)
        
        # Query database
        db_rule = self.session.query(StrategyRuleDB).filter_by(id=rule_id).first()
        if not db_rule:
            return None
        
        rule = self._to_pydantic(db_rule)
        
        # Cache result
        if use_cache and self.use_cache:
            cache_key = CacheKeys.strategy_rule(rule_id)
            cache_manager.set(cache_key, rule.dict(), CacheTTL.STRATEGY_RULE)
        
        return rule
    
    def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        entry_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> List[StrategyRule]:
        """Get all strategy rules with optional filtering."""
        query = self.session.query(StrategyRuleDB)
        
        if entry_type:
            query = query.filter(StrategyRuleDB.entry_type == entry_type)
        
        if min_confidence is not None:
            query = query.filter(StrategyRuleDB.confidence >= min_confidence)
        
        if tags:
            query = query.filter(StrategyRuleDB.tags.op('&&')(tags))
        
        query = query.order_by(desc(StrategyRuleDB.confidence), desc(StrategyRuleDB.win_rate))
        query = query.limit(limit).offset(offset)
        
        return [self._to_pydantic(rule) for rule in query.all()]
    
    def update_performance(
        self,
        rule_id: str,
        win_rate: float,
        avg_r_multiple: float,
        confidence: Optional[float] = None
    ) -> bool:
        """Update strategy rule performance metrics."""
        updates = {
            'win_rate': win_rate,
            'avg_r_multiple': avg_r_multiple,
            'last_used': datetime.utcnow()
        }
        
        if confidence is not None:
            updates['confidence'] = confidence
        
        result = self.session.query(StrategyRuleDB).filter_by(id=rule_id).update(updates)
        return result > 0
    
    def increment_trade_count(self, rule_id: str) -> bool:
        """Increment trade count for a strategy rule."""
        result = self.session.query(StrategyRuleDB).filter_by(id=rule_id).update({
            'trade_count': StrategyRuleDB.trade_count + 1,
            'last_used': datetime.utcnow()
        })
        return result > 0
    
    def search_by_text(self, query: str, limit: int = 20) -> List[StrategyRule]:
        """Search strategy rules by name and description."""
        search_query = self.session.query(StrategyRuleDB).filter(
            or_(
                StrategyRuleDB.name.ilike(f'%{query}%'),
                StrategyRuleDB.description.ilike(f'%{query}%')
            )
        ).order_by(desc(StrategyRuleDB.confidence)).limit(limit)
        
        return [self._to_pydantic(rule) for rule in search_query.all()]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary of all strategy rules."""
        result = self.session.query(
            func.count(StrategyRuleDB.id).label('total_rules'),
            func.avg(StrategyRuleDB.confidence).label('avg_confidence'),
            func.avg(StrategyRuleDB.win_rate).label('avg_win_rate'),
            func.sum(StrategyRuleDB.trade_count).label('total_trades')
        ).first()
        
        return {
            'total_rules': result.total_rules or 0,
            'avg_confidence': round(result.avg_confidence or 0, 3),
            'avg_win_rate': round(result.avg_win_rate or 0, 3),
            'total_trades': result.total_trades or 0
        }
    
    def find_similar_rules(
        self,
        rule_id: str,
        limit: int = 10,
        min_confidence: Optional[float] = None
    ) -> List[Tuple[StrategyRule, float]]:
        """
        Find similar strategy rules using semantic search.
        
        Args:
            rule_id: Strategy rule ID to find similar rules for
            limit: Maximum number of similar rules to return
            min_confidence: Minimum confidence score filter
            
        Returns:
            List of tuples (StrategyRule, similarity_score)
        """
        return self.semantic_search.find_similar_rules(rule_id, limit, min_confidence)
    
    def search_semantic(
        self,
        query_text: str,
        limit: int = 20,
        min_confidence: Optional[float] = None
    ) -> List[Tuple[StrategyRule, float]]:
        """
        Search for strategy rules using semantic similarity to query text.
        
        Args:
            query_text: Search query text
            limit: Maximum number of results
            min_confidence: Minimum confidence filter
            
        Returns:
            List of tuples (StrategyRule, similarity_score)
        """
        # Generate embedding for query
        embedding = self.semantic_search.embedding_generator.generate_embedding(query_text)
        if not embedding:
            return []
        
        try:
            # Search using vector similarity
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            query = text("""
                SELECT 
                    sr.*,
                    1 - (sr.embedding <=> :embedding::vector) as similarity
                FROM strategy_rules sr
                WHERE sr.embedding IS NOT NULL
            """)
            
            if min_confidence:
                query = text(str(query) + " AND sr.confidence >= :min_confidence")
            
            query = text(str(query) + """
                ORDER BY sr.embedding <=> :embedding::vector
                LIMIT :limit
            """)
            
            params = {"embedding": embedding_str, "limit": limit}
            if min_confidence:
                params["min_confidence"] = min_confidence
            
            result = self.session.execute(query, params)
            
            similar_rules = []
            for row in result:
                rule = self.semantic_search._row_to_strategy_rule(row)
                similarity = row.similarity
                similar_rules.append((rule, similarity))
            
            return similar_rules
            
        except Exception as e:
            print(f"Semantic search failed, falling back to text search: {e}")
            # Fallback to text-based search
            rules = self.search_by_text(query_text, limit)
            return [(rule, 0.5) for rule in rules]
    
    def delete(self, rule_id: str) -> bool:
        """Delete a strategy rule."""
        # Invalidate cache
        if self.use_cache:
            cache_manager.delete(CacheKeys.strategy_rule(rule_id))
            cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:strategy_rules:*")
            cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:similar_rules:{rule_id}:*")
        
        result = self.session.query(StrategyRuleDB).filter_by(id=rule_id).delete()
        return result > 0
    
    def _to_pydantic(self, db_rule: StrategyRuleDB) -> StrategyRule:
        """Convert database model to Pydantic model."""
        return StrategyRule(
            id=db_rule.id,
            name=db_rule.name,
            source=ContentSource(
                type=db_rule.source_type,
                ref=db_rule.source_ref,
                timestamp=db_rule.source_timestamp,
                page_number=db_rule.source_page_number
            ),
            entry_type=db_rule.entry_type,
            conditions=db_rule.conditions,
            confluence_required=db_rule.confluence_required,
            risk_params=RiskParameters(**db_rule.risk_params),
            confidence=db_rule.confidence,
            created_at=db_rule.created_at,
            last_used=db_rule.last_used,
            trade_count=db_rule.trade_count,
            win_rate=db_rule.win_rate,
            avg_r_multiple=db_rule.avg_r_multiple,
            description=db_rule.description,
            tags=db_rule.tags or []
        )


class TradeRecordRepository(BaseRepository):
    """Repository for trade records with caching."""
    
    def __init__(self, session: Optional[Session] = None, use_cache: bool = True):
        super().__init__(session)
        self.use_cache = use_cache
    
    def create(self, trade_record: TradeRecord) -> str:
        """Create a new trade record."""
        db_trade = TradeRecordDB(
            id=trade_record.id or str(uuid4()),
            strategy_rule_id=trade_record.strategy_rule_id,
            asset=trade_record.asset,
            direction=trade_record.direction.value,
            entry_price=trade_record.entry_price,
            entry_time=trade_record.entry_time,
            exit_price=trade_record.exit_price,
            exit_time=trade_record.exit_time,
            exit_reason=trade_record.exit_reason.value if trade_record.exit_reason else None,
            outcome=trade_record.outcome.value,
            pnl_r=trade_record.pnl_r,
            pnl_usd=trade_record.pnl_usd,
            position_size=trade_record.position_size,
            stop_loss=trade_record.stop_loss,
            take_profit_levels=trade_record.take_profit_levels,
            fees_usd=trade_record.fees_usd,
            reasoning=trade_record.reasoning,
            price_action_context=trade_record.price_action_context.dict(),
            confidence=trade_record.confidence,
            is_backtest=trade_record.is_backtest
        )
        
        self.session.add(db_trade)
        self.session.flush()
        
        # Invalidate relevant caches
        if self.use_cache:
            cache_manager.delete(CacheKeys.open_trades(trade_record.asset))
            cache_manager.delete(CacheKeys.open_trades(None))
            cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:stats:*")
        
        return db_trade.id
    
    def get_by_id(self, trade_id: str, use_cache: bool = True) -> Optional[TradeRecord]:
        """Get trade record by ID with optional caching."""
        # Try cache first
        if use_cache and self.use_cache:
            cache_key = CacheKeys.trade_record(trade_id)
            cached = cache_manager.get(cache_key)
            if cached:
                return TradeRecord(**cached)
        
        # Query database
        db_trade = self.session.query(TradeRecordDB).filter_by(id=trade_id).first()
        if not db_trade:
            return None
        
        trade = self._to_pydantic(db_trade)
        
        # Cache result
        if use_cache and self.use_cache:
            cache_key = CacheKeys.trade_record(trade_id)
            cache_manager.set(cache_key, trade.dict(), CacheTTL.TRADE_RECORD)
        
        return trade
    
    def get_by_strategy_rule(
        self,
        strategy_rule_id: str,
        limit: int = 100,
        only_closed: bool = False
    ) -> List[TradeRecord]:
        """Get trades for a specific strategy rule."""
        query = self.session.query(TradeRecordDB).filter_by(strategy_rule_id=strategy_rule_id)
        
        if only_closed:
            query = query.filter(TradeRecordDB.exit_time.isnot(None))
        
        query = query.order_by(desc(TradeRecordDB.entry_time)).limit(limit)
        
        return [self._to_pydantic(trade) for trade in query.all()]
    
    def get_open_trades(self, asset: Optional[str] = None, use_cache: bool = True) -> List[TradeRecord]:
        """Get all open trades with optional caching."""
        # Try cache first
        if use_cache and self.use_cache:
            cache_key = CacheKeys.open_trades(asset)
            cached = cache_manager.get(cache_key)
            if cached:
                return [TradeRecord(**trade_dict) for trade_dict in cached]
        
        # Query database
        query = self.session.query(TradeRecordDB).filter(
            TradeRecordDB.outcome == 'pending'
        )
        
        if asset:
            query = query.filter(TradeRecordDB.asset == asset)
        
        query = query.order_by(TradeRecordDB.entry_time)
        
        trades = [self._to_pydantic(trade) for trade in query.all()]
        
        # Cache result
        if use_cache and self.use_cache:
            cache_key = CacheKeys.open_trades(asset)
            cache_manager.set(
                cache_key,
                [trade.dict() for trade in trades],
                CacheTTL.OPEN_TRADES
            )
        
        return trades
    
    def update_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        outcome: str,
        pnl_r: Optional[float] = None,
        pnl_usd: Optional[float] = None,
        fees_usd: Optional[float] = None
    ) -> bool:
        """Update trade exit information."""
        updates = {
            'exit_price': exit_price,
            'exit_time': datetime.utcnow(),
            'exit_reason': exit_reason,
            'outcome': outcome,
            'updated_at': datetime.utcnow()
        }
        
        if pnl_r is not None:
            updates['pnl_r'] = pnl_r
        if pnl_usd is not None:
            updates['pnl_usd'] = pnl_usd
        if fees_usd is not None:
            updates['fees_usd'] = fees_usd
        
        result = self.session.query(TradeRecordDB).filter_by(id=trade_id).update(updates)
        
        # Invalidate caches
        if result > 0 and self.use_cache:
            cache_manager.delete(CacheKeys.trade_record(trade_id))
            cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:trades:open:*")
            cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:stats:*")
        
        return result > 0
    
    def get_trades_in_period(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_rule_id: Optional[str] = None,
        asset: Optional[str] = None,
        is_backtest: Optional[bool] = None
    ) -> List[TradeRecord]:
        """Get trades within a date range."""
        query = self.session.query(TradeRecordDB).filter(
            and_(
                TradeRecordDB.entry_time >= start_date,
                TradeRecordDB.entry_time <= end_date
            )
        )
        
        if strategy_rule_id:
            query = query.filter(TradeRecordDB.strategy_rule_id == strategy_rule_id)
        
        if asset:
            query = query.filter(TradeRecordDB.asset == asset)
        
        if is_backtest is not None:
            query = query.filter(TradeRecordDB.is_backtest == is_backtest)
        
        query = query.order_by(TradeRecordDB.entry_time)
        
        return [self._to_pydantic(trade) for trade in query.all()]
    
    def get_performance_stats(
        self,
        strategy_rule_id: Optional[str] = None,
        days_back: Optional[int] = None
    ) -> StrategyPerformance:
        """Calculate performance statistics."""
        query = self.session.query(TradeRecordDB).filter(
            TradeRecordDB.exit_time.isnot(None)
        )
        
        if strategy_rule_id:
            query = query.filter(TradeRecordDB.strategy_rule_id == strategy_rule_id)
        
        if days_back:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            query = query.filter(TradeRecordDB.entry_time >= cutoff_date)
        
        trades = query.all()
        
        if not trades:
            return StrategyPerformance(
                strategy_rule_id=strategy_rule_id or "all",
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_r_multiple=0.0,
                total_pnl_r=0.0
            )
        
        winning_trades = [t for t in trades if t.outcome == 'win']
        losing_trades = [t for t in trades if t.outcome == 'loss']
        
        total_pnl_r = sum(t.pnl_r for t in trades if t.pnl_r is not None)
        avg_r_multiple = total_pnl_r / len(trades) if trades else 0
        
        # Calculate profit factor
        gross_profit = sum(t.pnl_r for t in winning_trades if t.pnl_r and t.pnl_r > 0)
        gross_loss = abs(sum(t.pnl_r for t in losing_trades if t.pnl_r and t.pnl_r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        
        return StrategyPerformance(
            strategy_rule_id=strategy_rule_id or "all",
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=len(winning_trades) / len(trades),
            avg_r_multiple=avg_r_multiple,
            profit_factor=profit_factor,
            max_consecutive_losses=self._calculate_max_consecutive_losses(trades),
            max_drawdown=self._calculate_max_drawdown(trades),
            total_pnl_r=total_pnl_r
        )
    
    def _calculate_max_consecutive_losses(self, trades: List[TradeRecordDB]) -> int:
        """Calculate maximum consecutive losses."""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in sorted(trades, key=lambda t: t.entry_time):
            if trade.outcome == 'loss':
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_max_drawdown(self, trades: List[TradeRecordDB]) -> float:
        """Calculate maximum drawdown."""
        if not trades:
            return 0.0
        
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        
        for trade in sorted(trades, key=lambda t: t.entry_time):
            if trade.pnl_r is not None:
                equity += trade.pnl_r
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / abs(peak) if peak != 0 else 0
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _to_pydantic(self, db_trade: TradeRecordDB) -> TradeRecord:
        """Convert database model to Pydantic model."""
        return TradeRecord(
            id=db_trade.id,
            strategy_rule_id=db_trade.strategy_rule_id,
            asset=db_trade.asset,
            direction=db_trade.direction,
            entry_price=db_trade.entry_price,
            entry_time=db_trade.entry_time,
            exit_price=db_trade.exit_price,
            exit_time=db_trade.exit_time,
            exit_reason=db_trade.exit_reason,
            outcome=db_trade.outcome,
            pnl_r=db_trade.pnl_r,
            pnl_usd=db_trade.pnl_usd,
            position_size=db_trade.position_size,
            stop_loss=db_trade.stop_loss,
            take_profit_levels=db_trade.take_profit_levels or [],
            fees_usd=db_trade.fees_usd,
            reasoning=db_trade.reasoning,
            price_action_context=PriceActionSnapshot(**db_trade.price_action_context),
            confidence=db_trade.confidence,
            is_backtest=db_trade.is_backtest,
            created_at=db_trade.created_at,
            updated_at=db_trade.updated_at
        )


class LearningRepository(BaseRepository):
    """Repository for learning entries."""
    
    def create(self, learning_entry: LearningEntry) -> str:
        """Create a new learning entry."""
        db_entry = LearningEntryDB(
            id=learning_entry.id or str(uuid4()),
            strategy_rule_id=learning_entry.strategy_rule_id,
            insight=learning_entry.insight,
            supporting_trades=learning_entry.supporting_trades,
            confidence=learning_entry.confidence,
            impact_type=learning_entry.impact_type,
            market_conditions=learning_entry.market_conditions
        )
        
        self.session.add(db_entry)
        self.session.flush()
        return db_entry.id
    
    def get_by_strategy_rule(self, strategy_rule_id: str) -> List[LearningEntry]:
        """Get learning entries for a strategy rule."""
        query = self.session.query(LearningEntryDB).filter_by(
            strategy_rule_id=strategy_rule_id
        ).order_by(desc(LearningEntryDB.confidence))
        
        return [self._to_pydantic(entry) for entry in query.all()]
    
    def get_high_confidence_insights(self, min_confidence: float = 0.7) -> List[LearningEntry]:
        """Get high confidence learning insights."""
        query = self.session.query(LearningEntryDB).filter(
            LearningEntryDB.confidence >= min_confidence
        ).order_by(desc(LearningEntryDB.confidence))
        
        return [self._to_pydantic(entry) for entry in query.all()]
    
    def update_validation(self, entry_id: str) -> bool:
        """Update validation timestamp and count."""
        result = self.session.query(LearningEntryDB).filter_by(id=entry_id).update({
            'last_validated': datetime.utcnow(),
            'validation_count': LearningEntryDB.validation_count + 1
        })
        return result > 0
    
    def _to_pydantic(self, db_entry: LearningEntryDB) -> LearningEntry:
        """Convert database model to Pydantic model."""
        return LearningEntry(
            id=db_entry.id,
            strategy_rule_id=db_entry.strategy_rule_id,
            insight=db_entry.insight,
            supporting_trades=db_entry.supporting_trades or [],
            confidence=db_entry.confidence,
            impact_type=db_entry.impact_type,
            market_conditions=db_entry.market_conditions,
            created_at=db_entry.created_at,
            last_validated=db_entry.last_validated,
            validation_count=db_entry.validation_count
        )


class KnowledgeBaseRepository:
    """Main repository that combines all sub-repositories."""
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.strategy_rules = StrategyRuleRepository(session)
        self.trades = TradeRecordRepository(session)
        self.learning = LearningRepository(session)
    
    def __enter__(self):
        if self.session is None:
            self._session_manager = get_session()
            self.session = self._session_manager.__enter__()
            # Update sub-repositories with the session
            self.strategy_rules._session = self.session
            self.trades._session = self.session
            self.learning._session = self.session
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_session_manager'):
            self._session_manager.__exit__(exc_type, exc_val, exc_tb)


__all__ = [
    "StrategyRuleRepository",
    "TradeRecordRepository", 
    "LearningRepository",
    "KnowledgeBaseRepository",
]