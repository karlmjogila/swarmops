"""
Tests for Backtest Statistics Module

Comprehensive test suite for the backtest statistics calculator.
Tests all statistical calculations including trade stats, risk metrics,
and strategy analysis.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from src.backtest.statistics import (
    BacktestStatisticsCalculator,
    ComprehensiveStatistics,
    TradeStatistics,
    ReturnStatistics,
    RiskStatistics,
    StrategyStatistics
)
from src.types import (
    TradeRecord, TradeOutcome, OrderSide, ExitReason,
    BacktestResult, BacktestConfig, Timeframe
)


# ===== FIXTURES =====

@pytest.fixture
def sample_trades() -> List[TradeRecord]:
    """Create sample trades for testing."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    trades = [
        # Winning trade
        TradeRecord(
            id="trade_1",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=50000.0,
            entry_time=base_time,
            quantity=0.1,
            initial_stop_loss=49000.0,
            current_stop_loss=49000.0,
            take_profit_levels=[52000.0, 54000.0, 56000.0],
            exit_price=52000.0,
            exit_time=base_time + timedelta(hours=2),
            exit_reason=ExitReason.TP1,
            pnl_absolute=200.0,
            pnl_r_multiple=2.0,
            outcome=TradeOutcome.WIN,
            reasoning="Test trade 1"
        ),
        # Losing trade
        TradeRecord(
            id="trade_2",
            asset="ETH-USD",
            direction=OrderSide.SHORT,
            entry_price=3000.0,
            entry_time=base_time + timedelta(hours=3),
            quantity=1.0,
            initial_stop_loss=3100.0,
            current_stop_loss=3100.0,
            take_profit_levels=[2900.0, 2800.0],
            exit_price=3100.0,
            exit_time=base_time + timedelta(hours=5),
            exit_reason=ExitReason.STOP_LOSS,
            pnl_absolute=-100.0,
            pnl_r_multiple=-1.0,
            outcome=TradeOutcome.LOSS,
            reasoning="Test trade 2"
        ),
        # Winning trade
        TradeRecord(
            id="trade_3",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=51000.0,
            entry_time=base_time + timedelta(hours=6),
            quantity=0.1,
            initial_stop_loss=50000.0,
            current_stop_loss=50000.0,
            take_profit_levels=[54000.0],
            exit_price=54000.0,
            exit_time=base_time + timedelta(hours=8),
            exit_reason=ExitReason.TP1,
            pnl_absolute=300.0,
            pnl_r_multiple=3.0,
            outcome=TradeOutcome.WIN,
            reasoning="Test trade 3"
        ),
        # Winning trade
        TradeRecord(
            id="trade_4",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=52000.0,
            entry_time=base_time + timedelta(hours=9),
            quantity=0.1,
            initial_stop_loss=51000.0,
            current_stop_loss=51000.0,
            take_profit_levels=[53000.0],
            exit_price=53000.0,
            exit_time=base_time + timedelta(hours=10),
            exit_reason=ExitReason.TP1,
            pnl_absolute=100.0,
            pnl_r_multiple=1.0,
            outcome=TradeOutcome.WIN,
            reasoning="Test trade 4"
        ),
        # Losing trade
        TradeRecord(
            id="trade_5",
            asset="ETH-USD",
            direction=OrderSide.SHORT,
            entry_price=3100.0,
            entry_time=base_time + timedelta(hours=11),
            quantity=1.0,
            initial_stop_loss=3200.0,
            current_stop_loss=3200.0,
            take_profit_levels=[3000.0],
            exit_price=3200.0,
            exit_time=base_time + timedelta(hours=12),
            exit_reason=ExitReason.STOP_LOSS,
            pnl_absolute=-100.0,
            pnl_r_multiple=-1.0,
            outcome=TradeOutcome.LOSS,
            reasoning="Test trade 5"
        ),
    ]
    
    return trades


@pytest.fixture
def sample_equity_curve() -> List[dict]:
    """Create sample equity curve for testing."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    initial_balance = 10000.0
    
    curve = []
    equity = initial_balance
    
    # Simulate a trading period with ups and downs
    for day in range(30):
        for hour in range(0, 24, 6):  # 4 points per day
            timestamp = base_time + timedelta(days=day, hours=hour)
            
            # Simulate some volatility
            if day < 10:
                equity += 100  # Uptrend
            elif day < 15:
                equity -= 50  # Drawdown
            elif day < 25:
                equity += 80  # Recovery and growth
            else:
                equity += 20  # Slower growth
            
            curve.append({
                'timestamp': timestamp.isoformat(),
                'equity': equity,
                'balance': equity,
                'open_positions': 0,
                'drawdown': 0.0,
                'drawdown_pct': 0.0
            })
    
    return curve


@pytest.fixture
def sample_backtest_config() -> BacktestConfig:
    """Create sample backtest config."""
    return BacktestConfig(
        name="Test Backtest",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        assets=["BTC-USD", "ETH-USD"],
        timeframes=[Timeframe.M15, Timeframe.H1],
        initial_balance=10000.0,
        risk_per_trade=2.0,
        max_concurrent_trades=3,
        commission=0.001,
        slippage=0.001
    )


@pytest.fixture
def sample_backtest_result(
    sample_backtest_config,
    sample_trades,
    sample_equity_curve
) -> BacktestResult:
    """Create sample backtest result."""
    return BacktestResult(
        config=sample_backtest_config,
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        win_rate=60.0,
        total_return=500.0,
        total_return_percent=5.0,
        max_drawdown=-200.0,
        max_drawdown_percent=-2.0,
        sharpe_ratio=1.5,
        profit_factor=3.0,
        avg_r_multiple=0.8,
        best_r_multiple=3.0,
        worst_r_multiple=-1.0,
        avg_trade_duration_hours=2.5,
        equity_curve=sample_equity_curve,
        trades=sample_trades,
        started_at=datetime(2024, 1, 1),
        completed_at=datetime(2024, 1, 31),
        duration_seconds=3600.0
    )


# ===== TRADE STATISTICS TESTS =====

def test_calculate_trade_statistics_basic_counts(sample_trades):
    """Calculates correct trade counts and win rate."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    assert stats.total_trades == 5
    assert stats.winning_trades == 3
    assert stats.losing_trades == 2
    assert stats.breakeven_trades == 0
    assert stats.win_rate == 60.0
    assert stats.loss_rate == 40.0


def test_calculate_trade_statistics_streaks(sample_trades):
    """Calculates consecutive wins and losses correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # Sequence: W, L, W, W, L -> max wins = 2, max losses = 1
    assert stats.max_consecutive_wins == 2
    assert stats.max_consecutive_losses == 1
    assert stats.current_streak == 1
    assert stats.current_streak_type == "loss"


def test_calculate_trade_statistics_pnl(sample_trades):
    """Calculates P&L statistics correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # Wins: 200, 300, 100 = 600
    # Losses: -100, -100 = -200
    assert stats.total_profit == 600.0
    assert stats.total_loss == -200.0
    assert stats.avg_win == 200.0  # (200 + 300 + 100) / 3
    assert stats.avg_loss == -100.0  # (-100 + -100) / 2
    assert stats.largest_win == 300.0
    assert stats.largest_loss == -100.0


def test_calculate_trade_statistics_r_multiples(sample_trades):
    """Calculates R-multiple statistics correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # R-multiples: 2.0, -1.0, 3.0, 1.0, -1.0
    assert stats.avg_r_multiple == 0.8  # (2 - 1 + 3 + 1 - 1) / 5
    assert stats.median_r_multiple == 1.0
    assert stats.best_r_multiple == 3.0
    assert stats.worst_r_multiple == -1.0


def test_calculate_trade_statistics_profit_factor(sample_trades):
    """Calculates profit factor correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # Profit factor = Total wins / Abs(Total losses) = 600 / 200 = 3.0
    assert stats.profit_factor == 3.0


def test_calculate_trade_statistics_win_loss_ratio(sample_trades):
    """Calculates win/loss ratio correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # Win/Loss ratio = Avg win / Abs(Avg loss) = 200 / 100 = 2.0
    assert stats.win_loss_ratio == 2.0


def test_calculate_trade_statistics_expectancy(sample_trades):
    """Calculates expectancy correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # Expectancy = (200 - 100 + 300 + 100 - 100) / 5 = 80.0
    assert stats.expectancy == 80.0
    assert stats.expectancy_r == stats.avg_r_multiple


def test_calculate_trade_statistics_duration(sample_trades):
    """Calculates trade duration statistics correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(sample_trades)
    
    # Durations: 2h, 2h, 2h, 1h, 1h
    assert stats.avg_duration_hours == 1.6  # (2 + 2 + 2 + 1 + 1) / 5
    assert stats.shortest_trade_hours == 1.0
    assert stats.longest_trade_hours == 2.0


def test_calculate_trade_statistics_empty_list():
    """Handles empty trade list gracefully."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics([])
    
    assert stats.total_trades == 0
    assert stats.win_rate == 0.0
    assert stats.profit_factor == 0.0


# ===== RETURN STATISTICS TESTS =====

def test_calculate_return_statistics_total_return(sample_equity_curve):
    """Calculates total return correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_return_statistics(sample_equity_curve, 10000.0, 30.0)
    
    initial = 10000.0
    final = sample_equity_curve[-1]['equity']
    expected_return_pct = ((final - initial) / initial) * 100
    
    assert stats.total_return == final - initial
    assert abs(stats.total_return_percent - expected_return_pct) < 0.01


def test_calculate_return_statistics_annualized_return(sample_equity_curve):
    """Calculates annualized return correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_return_statistics(sample_equity_curve, 10000.0, 30.0)
    
    # Should have annualized return calculated
    assert stats.annualized_return != 0.0


def test_calculate_return_statistics_daily_returns(sample_equity_curve):
    """Calculates daily returns correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_return_statistics(sample_equity_curve, 10000.0, 30.0)
    
    # Should have daily returns
    assert len(stats.daily_returns) > 0
    assert stats.avg_daily_return != 0.0
    assert stats.std_daily_return >= 0.0


def test_calculate_return_statistics_best_worst_periods(sample_equity_curve):
    """Identifies best and worst periods correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_return_statistics(sample_equity_curve, 10000.0, 30.0)
    
    # Should have best/worst day
    assert 'date' in stats.best_day
    assert 'return' in stats.best_day
    assert 'date' in stats.worst_day
    assert 'return' in stats.worst_day


def test_calculate_return_statistics_empty_curve():
    """Handles empty equity curve gracefully."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_return_statistics([], 10000.0, 30.0)
    
    assert stats.total_return == 0.0
    assert stats.total_return_percent == 0.0


# ===== RISK STATISTICS TESTS =====

def test_calculate_risk_statistics_drawdown(sample_equity_curve):
    """Calculates drawdown metrics correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_risk_statistics(sample_equity_curve, [], 30.0)
    
    # Should have drawdown calculations
    # Drawdown is stored as positive value (magnitude of loss)
    assert stats.max_drawdown >= 0.0
    assert stats.max_drawdown_percent >= 0.0


def test_calculate_risk_statistics_sharpe_ratio():
    """Calculates Sharpe ratio correctly."""
    # Create returns with known statistics
    daily_returns = [0.01, 0.02, -0.01, 0.01, 0.02]
    
    calculator = BacktestStatisticsCalculator(risk_free_rate=0.02)  # 2% annual
    
    # Create dummy equity curve
    equity_curve = [{'timestamp': datetime.now(), 'equity': 10000.0 + i * 100} for i in range(10)]
    
    stats = calculator.calculate_risk_statistics(equity_curve, daily_returns, 30.0)
    
    # Should have Sharpe ratio calculated
    assert isinstance(stats.sharpe_ratio, float)


def test_calculate_risk_statistics_sortino_ratio():
    """Calculates Sortino ratio correctly."""
    # Returns with downside
    daily_returns = [0.02, 0.01, -0.02, -0.01, 0.03]
    
    calculator = BacktestStatisticsCalculator(risk_free_rate=0.0)
    equity_curve = [{'timestamp': datetime.now(), 'equity': 10000.0 + i * 100} for i in range(10)]
    
    stats = calculator.calculate_risk_statistics(equity_curve, daily_returns, 30.0)
    
    # Should have Sortino ratio calculated
    assert isinstance(stats.sortino_ratio, float)


def test_calculate_risk_statistics_volatility():
    """Calculates volatility correctly."""
    daily_returns = [0.01, -0.01, 0.02, -0.02, 0.01]
    
    calculator = BacktestStatisticsCalculator()
    equity_curve = [{'timestamp': datetime.now(), 'equity': 10000.0} for _ in range(10)]
    
    stats = calculator.calculate_risk_statistics(equity_curve, daily_returns, 30.0)
    
    assert stats.volatility_daily > 0.0
    assert stats.volatility_annualized > 0.0


def test_calculate_risk_statistics_var():
    """Calculates Value at Risk correctly."""
    # Create sufficient data points for VaR
    daily_returns = [0.01 * (i % 5 - 2) for i in range(100)]
    
    calculator = BacktestStatisticsCalculator()
    equity_curve = [{'timestamp': datetime.now(), 'equity': 10000.0} for _ in range(100)]
    
    stats = calculator.calculate_risk_statistics(equity_curve, daily_returns, 100.0)
    
    # Should have VaR calculated
    assert stats.var_95 <= 0.0  # VaR should be negative
    assert stats.var_99 <= stats.var_95  # 99% VaR should be worse than 95%


# ===== STRATEGY STATISTICS TESTS =====

def test_calculate_strategy_statistics_direction_breakdown(sample_trades):
    """Calculates direction breakdown correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_strategy_statistics(sample_trades)
    
    # 3 long, 2 short
    assert stats.long_trades == 3
    assert stats.short_trades == 2
    
    # Long: 3 wins out of 3 = 100%
    assert stats.long_win_rate == 100.0
    
    # Short: 0 wins out of 2 = 0%
    assert stats.short_win_rate == 0.0


def test_calculate_strategy_statistics_exit_reasons(sample_trades):
    """Calculates exit reason breakdown correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_strategy_statistics(sample_trades)
    
    # 3 TP1, 2 STOP_LOSS
    assert stats.exit_reason_counts['tp1'] == 3
    assert stats.exit_reason_counts['stop_loss'] == 2


def test_calculate_strategy_statistics_time_analysis(sample_trades):
    """Calculates time-based analysis correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_strategy_statistics(sample_trades)
    
    # Should have hourly and day-of-week performance
    assert len(stats.hourly_performance) > 0
    assert len(stats.day_of_week_performance) > 0


# ===== COMPREHENSIVE STATISTICS TESTS =====

def test_calculate_all_statistics(sample_backtest_result):
    """Calculates all statistics correctly."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_all_statistics(sample_backtest_result)
    
    assert isinstance(stats, ComprehensiveStatistics)
    assert isinstance(stats.trade_stats, TradeStatistics)
    assert isinstance(stats.return_stats, ReturnStatistics)
    assert isinstance(stats.risk_stats, RiskStatistics)
    assert isinstance(stats.strategy_stats, StrategyStatistics)
    
    # Should have metadata
    assert stats.backtest_name == "Test Backtest"
    assert stats.initial_balance == 10000.0
    assert stats.duration_days == 30.0


def test_update_backtest_result_with_stats(sample_backtest_result):
    """Updates BacktestResult with calculated statistics."""
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_all_statistics(sample_backtest_result)
    
    updated_result = calculator.update_backtest_result_with_stats(
        sample_backtest_result, stats
    )
    
    # Should have missing fields filled in
    assert updated_result.sortino_ratio == stats.risk_stats.sortino_ratio
    assert updated_result.max_consecutive_wins == stats.trade_stats.max_consecutive_wins
    assert updated_result.max_consecutive_losses == stats.trade_stats.max_consecutive_losses


def test_calculator_with_custom_risk_free_rate():
    """Uses custom risk-free rate for calculations."""
    calculator = BacktestStatisticsCalculator(risk_free_rate=0.05)
    
    assert calculator.risk_free_rate == 0.05


# ===== EDGE CASE TESTS =====

def test_handles_single_trade():
    """Handles single trade correctly."""
    single_trade = [
        TradeRecord(
            id="trade_1",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=50000.0,
            entry_time=datetime.now(),
            quantity=0.1,
            initial_stop_loss=49000.0,
            current_stop_loss=49000.0,
            take_profit_levels=[52000.0],
            exit_price=52000.0,
            exit_time=datetime.now() + timedelta(hours=1),
            exit_reason=ExitReason.TP1,
            pnl_absolute=200.0,
            pnl_r_multiple=2.0,
            outcome=TradeOutcome.WIN
        )
    ]
    
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(single_trade)
    
    assert stats.total_trades == 1
    assert stats.win_rate == 100.0
    assert stats.std_r_multiple == 0.0  # Only one data point


def test_handles_all_winning_trades():
    """Handles all winning trades correctly."""
    wins = [
        TradeRecord(
            id=f"trade_{i}",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=50000.0,
            entry_time=datetime.now() + timedelta(hours=i),
            quantity=0.1,
            initial_stop_loss=49000.0,
            current_stop_loss=49000.0,
            take_profit_levels=[52000.0],
            exit_price=52000.0,
            exit_time=datetime.now() + timedelta(hours=i + 1),
            exit_reason=ExitReason.TP1,
            pnl_absolute=200.0,
            pnl_r_multiple=2.0,
            outcome=TradeOutcome.WIN
        )
        for i in range(5)
    ]
    
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(wins)
    
    assert stats.total_trades == 5
    assert stats.win_rate == 100.0
    assert stats.losing_trades == 0
    assert stats.avg_loss == 0.0
    assert stats.profit_factor == 0.0  # No losses


def test_handles_all_losing_trades():
    """Handles all losing trades correctly."""
    losses = [
        TradeRecord(
            id=f"trade_{i}",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=50000.0,
            entry_time=datetime.now() + timedelta(hours=i),
            quantity=0.1,
            initial_stop_loss=49000.0,
            current_stop_loss=49000.0,
            take_profit_levels=[52000.0],
            exit_price=49000.0,
            exit_time=datetime.now() + timedelta(hours=i + 1),
            exit_reason=ExitReason.STOP_LOSS,
            pnl_absolute=-100.0,
            pnl_r_multiple=-1.0,
            outcome=TradeOutcome.LOSS
        )
        for i in range(5)
    ]
    
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(losses)
    
    assert stats.total_trades == 5
    assert stats.win_rate == 0.0
    assert stats.winning_trades == 0
    assert stats.avg_win == 0.0


def test_handles_missing_pnl_data():
    """Handles trades with missing P&L data."""
    trades = [
        TradeRecord(
            id="trade_1",
            asset="BTC-USD",
            direction=OrderSide.LONG,
            entry_price=50000.0,
            entry_time=datetime.now(),
            quantity=0.1,
            initial_stop_loss=49000.0,
            current_stop_loss=49000.0,
            take_profit_levels=[52000.0],
            pnl_absolute=None,  # Missing P&L
            pnl_r_multiple=None,
            outcome=TradeOutcome.PENDING
        )
    ]
    
    calculator = BacktestStatisticsCalculator()
    stats = calculator.calculate_trade_statistics(trades)
    
    # Should not crash
    assert stats.total_trades == 1
    assert stats.expectancy == 0.0


# ===== PERFORMANCE TESTS =====

def test_performance_with_large_dataset():
    """Handles large number of trades efficiently."""
    # Create 1000 trades
    trades = []
    for i in range(1000):
        outcome = TradeOutcome.WIN if i % 2 == 0 else TradeOutcome.LOSS
        pnl = 100.0 if outcome == TradeOutcome.WIN else -50.0
        r_mult = 2.0 if outcome == TradeOutcome.WIN else -1.0
        
        trades.append(
            TradeRecord(
                id=f"trade_{i}",
                asset="BTC-USD",
                direction=OrderSide.LONG,
                entry_price=50000.0,
                entry_time=datetime.now() + timedelta(hours=i),
                quantity=0.1,
                initial_stop_loss=49000.0,
                current_stop_loss=49000.0,
                take_profit_levels=[52000.0],
                exit_price=52000.0 if outcome == TradeOutcome.WIN else 49000.0,
                exit_time=datetime.now() + timedelta(hours=i + 1),
                exit_reason=ExitReason.TP1 if outcome == TradeOutcome.WIN else ExitReason.STOP_LOSS,
                pnl_absolute=pnl,
                pnl_r_multiple=r_mult,
                outcome=outcome
            )
        )
    
    calculator = BacktestStatisticsCalculator()
    
    import time
    start = time.time()
    stats = calculator.calculate_trade_statistics(trades)
    elapsed = time.time() - start
    
    assert stats.total_trades == 1000
    assert elapsed < 1.0  # Should complete in under 1 second
