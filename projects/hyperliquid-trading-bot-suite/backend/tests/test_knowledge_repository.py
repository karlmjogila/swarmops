"""
Unit tests for the knowledge base repository layer.
Tests CRUD operations, caching, and semantic search functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

# SQLAlchemy imports handled in conftest.py

from src.database.models import Base, StrategyRuleDB, TradeRecordDB, LearningEntryDB
from src.knowledge.repository import (
    StrategyRuleRepository,
    TradeRecordRepository,
    LearningRepository,
    KnowledgeBaseRepository
)
from src.knowledge.models import (
    StrategyRule,
    TradeRecord,
    LearningEntry,
    ContentSource,
    RiskParameters,
    PriceActionSnapshot,
    PatternCondition,
    TimeframeAlignment
)
from src.types import (
    EntryType,
    PatternType,
    Timeframe,
    SourceType,
    OrderSide,
    TradeOutcome,
    ExitReason
)


# Test fixtures are imported from conftest.py


@pytest.fixture
def strategy_rule_repo(test_session):
    """Create strategy rule repository with test session."""
    repo = StrategyRuleRepository(session=test_session, use_cache=False)
    # Mock semantic search for SQLite compatibility
    repo._semantic_search = Mock()
    repo._semantic_search.update_rule_embedding = Mock(return_value=None)
    return repo


@pytest.fixture
def trade_repo(test_session):
    """Create trade record repository with test session."""
    return TradeRecordRepository(session=test_session, use_cache=False)


@pytest.fixture
def learning_repo(test_session):
    """Create learning repository with test session."""
    return LearningRepository(session=test_session)


@pytest.fixture
def sample_strategy_rule():
    """Create sample strategy rule for testing."""
    return StrategyRule(
        id=str(uuid4()),
        name="Test LE Strategy",
        source=ContentSource(
            type=SourceType.PDF,
            ref="/path/to/strategy.pdf",
            page_number=10
        ),
        entry_type=EntryType.LE,
        conditions=[
            PatternCondition(
                type=PatternType.CANDLE,
                timeframe=Timeframe.M15,
                params={"wickRatio": ">2", "closePosition": "upper_third"}
            )
        ],
        confluence_required=[
            TimeframeAlignment(
                higher_tf=Timeframe.H4,
                lower_tf=Timeframe.M15,
                bias_required="bullish",
                entry_pattern="LE"
            )
        ],
        risk_params=RiskParameters(
            risk_percent=2.0,
            tp_levels=[1.0, 2.0],
            sl_distance="below_low"
        ),
        confidence=0.7,
        description="Liquidity engulf pattern on 15M with 4H bullish bias",
        tags=["LE", "bullish", "4H-15M"]
    )


@pytest.fixture
def sample_trade_record(sample_strategy_rule):
    """Create sample trade record for testing."""
    return TradeRecord(
        id=str(uuid4()),
        strategy_rule_id=sample_strategy_rule.id,
        asset="ETH-USD",
        direction=OrderSide.LONG,
        entry_price=2500.0,
        entry_time=datetime.utcnow(),
        position_size=1.0,
        stop_loss=2450.0,
        take_profit_levels=[2550.0, 2600.0],
        reasoning="Strong LE pattern on 15M with 4H bullish structure",
        price_action_context=PriceActionSnapshot(
            timeframes={},
            structure_notes=["Higher high on 4H", "Break of structure"],
            zone_interactions=["Bounced from support zone"]
        ),
        confidence=0.75,
        is_backtest=False
    )


@pytest.fixture
def sample_learning_entry(sample_strategy_rule):
    """Create sample learning entry for testing."""
    return LearningEntry(
        id=str(uuid4()),
        strategy_rule_id=sample_strategy_rule.id,
        insight="LE patterns work better when preceded by range consolidation",
        supporting_trades=[str(uuid4()), str(uuid4())],
        confidence=0.8,
        impact_type="success_factor"
    )


class TestStrategyRuleRepository:
    """Tests for StrategyRuleRepository."""
    
    def test_create_strategy_rule(self, strategy_rule_repo, sample_strategy_rule):
        """Test creating a new strategy rule."""
        rule_id = strategy_rule_repo.create(sample_strategy_rule)
        
        assert rule_id is not None
        assert rule_id == sample_strategy_rule.id
        
        # Verify rule was created in database
        retrieved = strategy_rule_repo.get_by_id(rule_id)
        assert retrieved is not None
        assert retrieved.name == sample_strategy_rule.name
        assert retrieved.entry_type == sample_strategy_rule.entry_type
        assert retrieved.confidence == sample_strategy_rule.confidence
    
    def test_get_by_id(self, strategy_rule_repo, sample_strategy_rule):
        """Test retrieving strategy rule by ID."""
        rule_id = strategy_rule_repo.create(sample_strategy_rule)
        
        retrieved = strategy_rule_repo.get_by_id(rule_id)
        
        assert retrieved is not None
        assert retrieved.id == rule_id
        assert retrieved.name == sample_strategy_rule.name
        assert len(retrieved.conditions) == len(sample_strategy_rule.conditions)
    
    def test_get_by_id_not_found(self, strategy_rule_repo):
        """Test retrieving non-existent rule."""
        result = strategy_rule_repo.get_by_id("non-existent-id")
        assert result is None
    
    def test_get_all_with_filters(self, strategy_rule_repo, sample_strategy_rule):
        """Test getting all rules with filters."""
        # Create multiple rules
        rule_id1 = strategy_rule_repo.create(sample_strategy_rule)
        
        sample_strategy_rule.id = str(uuid4())
        sample_strategy_rule.name = "Test Small Wick Strategy"
        sample_strategy_rule.entry_type = EntryType.SMALL_WICK
        sample_strategy_rule.confidence = 0.5
        rule_id2 = strategy_rule_repo.create(sample_strategy_rule)
        
        # Get all rules
        all_rules = strategy_rule_repo.get_all(limit=100)
        assert len(all_rules) == 2
        
        # Filter by entry type
        le_rules = strategy_rule_repo.get_all(entry_type=EntryType.LE.value)
        assert len(le_rules) == 1
        assert le_rules[0].entry_type == EntryType.LE
        
        # Filter by confidence
        high_conf_rules = strategy_rule_repo.get_all(min_confidence=0.6)
        assert len(high_conf_rules) == 1
        assert high_conf_rules[0].confidence >= 0.6
    
    def test_update_performance(self, strategy_rule_repo, sample_strategy_rule):
        """Test updating strategy rule performance metrics."""
        rule_id = strategy_rule_repo.create(sample_strategy_rule)
        
        # Update performance
        success = strategy_rule_repo.update_performance(
            rule_id=rule_id,
            win_rate=0.65,
            avg_r_multiple=1.5,
            confidence=0.8
        )
        
        assert success is True
        
        # Verify updates
        updated_rule = strategy_rule_repo.get_by_id(rule_id)
        assert updated_rule.win_rate == 0.65
        assert updated_rule.avg_r_multiple == 1.5
        assert updated_rule.confidence == 0.8
        assert updated_rule.last_used is not None
    
    def test_increment_trade_count(self, strategy_rule_repo, sample_strategy_rule):
        """Test incrementing trade count."""
        rule_id = strategy_rule_repo.create(sample_strategy_rule)
        
        initial_rule = strategy_rule_repo.get_by_id(rule_id)
        initial_count = initial_rule.trade_count
        
        # Increment count
        strategy_rule_repo.increment_trade_count(rule_id)
        
        updated_rule = strategy_rule_repo.get_by_id(rule_id)
        assert updated_rule.trade_count == initial_count + 1
    
    def test_search_by_text(self, strategy_rule_repo, sample_strategy_rule):
        """Test text-based search."""
        strategy_rule_repo.create(sample_strategy_rule)
        
        # Search by name
        results = strategy_rule_repo.search_by_text("LE Strategy")
        assert len(results) > 0
        assert any("LE" in rule.name for rule in results)
        
        # Search by description
        results = strategy_rule_repo.search_by_text("Liquidity engulf")
        assert len(results) > 0
    
    def test_get_performance_summary(self, strategy_rule_repo, sample_strategy_rule):
        """Test getting performance summary."""
        # Create a couple of rules
        strategy_rule_repo.create(sample_strategy_rule)
        
        sample_strategy_rule.id = str(uuid4())
        sample_strategy_rule.win_rate = 0.6
        strategy_rule_repo.create(sample_strategy_rule)
        
        summary = strategy_rule_repo.get_performance_summary()
        
        assert summary['total_rules'] == 2
        assert summary['avg_confidence'] > 0
        assert summary['total_trades'] >= 0
    
    def test_delete_strategy_rule(self, strategy_rule_repo, sample_strategy_rule):
        """Test deleting a strategy rule."""
        rule_id = strategy_rule_repo.create(sample_strategy_rule)
        
        # Verify rule exists
        assert strategy_rule_repo.get_by_id(rule_id) is not None
        
        # Delete rule
        success = strategy_rule_repo.delete(rule_id)
        assert success is True
        
        # Verify rule is deleted
        assert strategy_rule_repo.get_by_id(rule_id) is None


class TestTradeRecordRepository:
    """Tests for TradeRecordRepository."""
    
    def test_create_trade_record(self, trade_repo, sample_trade_record):
        """Test creating a new trade record."""
        trade_id = trade_repo.create(sample_trade_record)
        
        assert trade_id is not None
        assert trade_id == sample_trade_record.id
        
        # Verify trade was created
        retrieved = trade_repo.get_by_id(trade_id)
        assert retrieved is not None
        assert retrieved.asset == sample_trade_record.asset
        assert retrieved.direction == sample_trade_record.direction
    
    def test_get_by_id(self, trade_repo, sample_trade_record):
        """Test retrieving trade by ID."""
        trade_id = trade_repo.create(sample_trade_record)
        
        retrieved = trade_repo.get_by_id(trade_id)
        
        assert retrieved is not None
        assert retrieved.id == trade_id
        assert retrieved.entry_price == sample_trade_record.entry_price
    
    def test_get_open_trades(self, trade_repo, sample_trade_record):
        """Test getting open trades."""
        # Create open trade
        sample_trade_record.outcome = TradeOutcome.PENDING
        trade_id1 = trade_repo.create(sample_trade_record)
        
        # Create closed trade
        sample_trade_record.id = str(uuid4())
        sample_trade_record.outcome = TradeOutcome.WIN
        sample_trade_record.exit_price = 2600.0
        sample_trade_record.exit_time = datetime.utcnow()
        trade_id2 = trade_repo.create(sample_trade_record)
        
        # Get open trades
        open_trades = trade_repo.get_open_trades()
        
        assert len(open_trades) == 1
        assert open_trades[0].id == trade_id1
        assert open_trades[0].outcome == TradeOutcome.PENDING
    
    def test_get_open_trades_by_asset(self, trade_repo, sample_trade_record):
        """Test getting open trades filtered by asset."""
        # Create ETH trade
        sample_trade_record.outcome = TradeOutcome.PENDING
        sample_trade_record.asset = "ETH-USD"
        eth_trade_id = trade_repo.create(sample_trade_record)
        
        # Create BTC trade
        sample_trade_record.id = str(uuid4())
        sample_trade_record.asset = "BTC-USD"
        btc_trade_id = trade_repo.create(sample_trade_record)
        
        # Get ETH trades
        eth_trades = trade_repo.get_open_trades(asset="ETH-USD")
        assert len(eth_trades) == 1
        assert eth_trades[0].asset == "ETH-USD"
        
        # Get BTC trades
        btc_trades = trade_repo.get_open_trades(asset="BTC-USD")
        assert len(btc_trades) == 1
        assert btc_trades[0].asset == "BTC-USD"
    
    def test_update_trade_exit(self, trade_repo, sample_trade_record):
        """Test updating trade exit information."""
        trade_id = trade_repo.create(sample_trade_record)
        
        # Update exit
        success = trade_repo.update_trade_exit(
            trade_id=trade_id,
            exit_price=2600.0,
            exit_reason=ExitReason.TP1.value,
            outcome=TradeOutcome.WIN.value,
            pnl_r=2.0,
            pnl_usd=100.0
        )
        
        assert success is True
        
        # Verify updates
        updated_trade = trade_repo.get_by_id(trade_id)
        assert updated_trade.exit_price == 2600.0
        assert updated_trade.exit_reason == ExitReason.TP1
        assert updated_trade.outcome == TradeOutcome.WIN
        assert updated_trade.pnl_r == 2.0
        assert updated_trade.pnl_usd == 100.0
        assert updated_trade.exit_time is not None
    
    def test_get_by_strategy_rule(self, trade_repo, sample_trade_record):
        """Test getting trades by strategy rule."""
        rule_id = sample_trade_record.strategy_rule_id
        
        # Create multiple trades for the same strategy
        trade_id1 = trade_repo.create(sample_trade_record)
        
        sample_trade_record.id = str(uuid4())
        trade_id2 = trade_repo.create(sample_trade_record)
        
        # Create trade for different strategy
        sample_trade_record.id = str(uuid4())
        sample_trade_record.strategy_rule_id = str(uuid4())
        trade_id3 = trade_repo.create(sample_trade_record)
        
        # Get trades for specific strategy
        strategy_trades = trade_repo.get_by_strategy_rule(rule_id)
        
        assert len(strategy_trades) == 2
        assert all(trade.strategy_rule_id == rule_id for trade in strategy_trades)
    
    def test_get_trades_in_period(self, trade_repo, sample_trade_record):
        """Test getting trades within a date range."""
        now = datetime.utcnow()
        
        # Create trade yesterday
        sample_trade_record.entry_time = now - timedelta(days=1)
        trade_id1 = trade_repo.create(sample_trade_record)
        
        # Create trade today
        sample_trade_record.id = str(uuid4())
        sample_trade_record.entry_time = now
        trade_id2 = trade_repo.create(sample_trade_record)
        
        # Create trade tomorrow (future)
        sample_trade_record.id = str(uuid4())
        sample_trade_record.entry_time = now + timedelta(days=1)
        trade_id3 = trade_repo.create(sample_trade_record)
        
        # Get trades from yesterday to today
        trades = trade_repo.get_trades_in_period(
            start_date=now - timedelta(days=2),
            end_date=now + timedelta(hours=1)
        )
        
        assert len(trades) == 2
        assert all(
            now - timedelta(days=2) <= trade.entry_time <= now + timedelta(hours=1)
            for trade in trades
        )
    
    def test_get_performance_stats(self, trade_repo, sample_trade_record):
        """Test calculating performance statistics."""
        rule_id = sample_trade_record.strategy_rule_id
        
        # Create winning trades
        sample_trade_record.outcome = TradeOutcome.WIN
        sample_trade_record.exit_time = datetime.utcnow()
        sample_trade_record.pnl_r = 2.0
        trade_repo.create(sample_trade_record)
        
        sample_trade_record.id = str(uuid4())
        trade_repo.create(sample_trade_record)
        
        # Create losing trade
        sample_trade_record.id = str(uuid4())
        sample_trade_record.outcome = TradeOutcome.LOSS
        sample_trade_record.pnl_r = -1.0
        trade_repo.create(sample_trade_record)
        
        # Get stats
        stats = trade_repo.get_performance_stats(strategy_rule_id=rule_id)
        
        assert stats.total_trades == 3
        assert stats.winning_trades == 2
        assert stats.losing_trades == 1
        assert stats.win_rate == pytest.approx(2 / 3, 0.01)
        assert stats.avg_r_multiple == pytest.approx(1.0, 0.01)
        assert stats.profit_factor is not None


class TestLearningRepository:
    """Tests for LearningRepository."""
    
    def test_create_learning_entry(self, learning_repo, sample_learning_entry):
        """Test creating a new learning entry."""
        entry_id = learning_repo.create(sample_learning_entry)
        
        assert entry_id is not None
        assert entry_id == sample_learning_entry.id
    
    def test_get_by_strategy_rule(self, learning_repo, sample_learning_entry):
        """Test getting learning entries by strategy rule."""
        rule_id = sample_learning_entry.strategy_rule_id
        
        # Create multiple entries for the same strategy
        learning_repo.create(sample_learning_entry)
        
        sample_learning_entry.id = str(uuid4())
        sample_learning_entry.insight = "Another learning insight"
        learning_repo.create(sample_learning_entry)
        
        # Get entries
        entries = learning_repo.get_by_strategy_rule(rule_id)
        
        assert len(entries) == 2
        assert all(entry.strategy_rule_id == rule_id for entry in entries)
    
    def test_get_high_confidence_insights(self, learning_repo, sample_learning_entry):
        """Test getting high confidence learning insights."""
        # Create high confidence entry
        sample_learning_entry.confidence = 0.9
        learning_repo.create(sample_learning_entry)
        
        # Create low confidence entry
        sample_learning_entry.id = str(uuid4())
        sample_learning_entry.confidence = 0.3
        learning_repo.create(sample_learning_entry)
        
        # Get high confidence insights
        high_conf = learning_repo.get_high_confidence_insights(min_confidence=0.7)
        
        assert len(high_conf) == 1
        assert high_conf[0].confidence >= 0.7
    
    def test_update_validation(self, learning_repo, sample_learning_entry):
        """Test updating learning entry validation."""
        entry_id = learning_repo.create(sample_learning_entry)
        
        # Update validation
        success = learning_repo.update_validation(entry_id)
        assert success is True
        
        # Verify validation count increased
        entries = learning_repo.get_by_strategy_rule(sample_learning_entry.strategy_rule_id)
        entry = next(e for e in entries if e.id == entry_id)
        assert entry.validation_count == 1
        assert entry.last_validated is not None


class TestKnowledgeBaseRepository:
    """Tests for integrated KnowledgeBaseRepository."""
    
    def test_context_manager(self, test_db_engine):
        """Test using repository with context manager."""
        with KnowledgeBaseRepository() as kb_repo:
            # Repository should be accessible
            assert kb_repo.strategy_rules is not None
            assert kb_repo.trades is not None
            assert kb_repo.learning is not None
    
    def test_integrated_workflow(
        self,
        strategy_rule_repo,
        trade_repo,
        learning_repo,
        sample_strategy_rule,
        sample_trade_record,
        sample_learning_entry
    ):
        """Test complete workflow with all repositories."""
        
        # Create strategy rule
        rule_id = strategy_rule_repo.create(sample_strategy_rule)
        assert rule_id is not None
        
        # Create trade using that rule
        sample_trade_record.strategy_rule_id = rule_id
        trade_id = trade_repo.create(sample_trade_record)
        assert trade_id is not None
        
        # Create learning entry for the strategy
        sample_learning_entry.strategy_rule_id = rule_id
        learning_id = learning_repo.create(sample_learning_entry)
        assert learning_id is not None
        
        # Verify all are connected
        rule = strategy_rule_repo.get_by_id(rule_id)
        trades = trade_repo.get_by_strategy_rule(rule_id)
        learnings = learning_repo.get_by_strategy_rule(rule_id)
        
        assert rule is not None
        assert len(trades) == 1
        assert len(learnings) == 1
        assert trades[0].strategy_rule_id == rule.id
        assert learnings[0].strategy_rule_id == rule.id


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
