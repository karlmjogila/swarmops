"""
Backtest Statistics Module

Comprehensive statistics calculator for backtest results.
Calculates all performance metrics, risk-adjusted returns, trade analysis,
and provides detailed reporting capabilities.

This module provides:
- Complete performance metrics (Sharpe, Sortino, Calmar, etc.)
- Trade analysis (streaks, MFE/MAE, distribution)
- Time-based analysis (monthly, daily returns)
- Risk metrics (drawdown analysis, value at risk)
- Detailed statistical reports

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from collections import defaultdict
import statistics
from enum import Enum

from ..types import (
    BacktestResult, TradeRecord, TradeOutcome, OrderSide,
    ExitReason
)

logger = logging.getLogger(__name__)


@dataclass
class TradeStatistics:
    """Detailed trade-level statistics."""
    
    # Win/Loss breakdown
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    
    # Streaks
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_streak: int = 0
    current_streak_type: str = ""  # "win" or "loss"
    
    # P&L statistics
    total_profit: float = 0.0
    total_loss: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # R-multiple statistics
    avg_r_multiple: float = 0.0
    median_r_multiple: float = 0.0
    std_r_multiple: float = 0.0
    best_r_multiple: float = 0.0
    worst_r_multiple: float = 0.0
    
    # Expectancy
    expectancy: float = 0.0  # Average $ per trade
    expectancy_r: float = 0.0  # Average R per trade
    
    # Trade quality metrics
    profit_factor: float = 0.0  # Gross profit / Gross loss
    win_loss_ratio: float = 0.0  # Avg win / Avg loss
    kelly_criterion: float = 0.0  # Optimal position size
    
    # Duration statistics
    avg_duration_hours: float = 0.0
    avg_winning_duration_hours: float = 0.0
    avg_losing_duration_hours: float = 0.0
    shortest_trade_hours: float = 0.0
    longest_trade_hours: float = 0.0
    
    # MFE/MAE analysis
    avg_mfe: float = 0.0  # Max Favorable Excursion
    avg_mae: float = 0.0  # Max Adverse Excursion
    mfe_mae_ratio: float = 0.0


@dataclass
class ReturnStatistics:
    """Return-based statistics."""
    
    # Total returns
    total_return: float = 0.0
    total_return_percent: float = 0.0
    annualized_return: float = 0.0
    
    # Periodic returns
    daily_returns: List[float] = field(default_factory=list)
    monthly_returns: List[float] = field(default_factory=list)
    
    # Return statistics
    avg_daily_return: float = 0.0
    std_daily_return: float = 0.0
    avg_monthly_return: float = 0.0
    std_monthly_return: float = 0.0
    
    # Best/worst periods
    best_day: Dict[str, Any] = field(default_factory=dict)
    worst_day: Dict[str, Any] = field(default_factory=dict)
    best_month: Dict[str, Any] = field(default_factory=dict)
    worst_month: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskStatistics:
    """Risk metrics."""
    
    # Drawdown analysis
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    avg_drawdown: float = 0.0
    avg_drawdown_percent: float = 0.0
    max_drawdown_duration_days: float = 0.0
    recovery_time_days: float = 0.0
    
    # Drawdown periods
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Volatility
    volatility_daily: float = 0.0
    volatility_annualized: float = 0.0
    downside_deviation: float = 0.0
    
    # Value at Risk (VaR)
    var_95: float = 0.0  # 95% VaR
    var_99: float = 0.0  # 99% VaR
    cvar_95: float = 0.0  # Conditional VaR (Expected Shortfall)


@dataclass
class StrategyStatistics:
    """Strategy-specific statistics."""
    
    # Setup type breakdown
    setup_breakdown: Dict[str, int] = field(default_factory=dict)
    setup_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Direction breakdown
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    long_pnl: float = 0.0
    short_pnl: float = 0.0
    
    # Exit reason breakdown
    exit_reason_counts: Dict[str, int] = field(default_factory=dict)
    exit_reason_pnl: Dict[str, float] = field(default_factory=dict)
    
    # Time-of-day analysis
    hourly_performance: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    day_of_week_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ComprehensiveStatistics:
    """Complete statistics package."""
    
    trade_stats: TradeStatistics = field(default_factory=TradeStatistics)
    return_stats: ReturnStatistics = field(default_factory=ReturnStatistics)
    risk_stats: RiskStatistics = field(default_factory=RiskStatistics)
    strategy_stats: StrategyStatistics = field(default_factory=StrategyStatistics)
    
    # Metadata
    backtest_id: Optional[str] = None
    backtest_name: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: float = 0.0
    initial_balance: float = 0.0
    final_balance: float = 0.0


class BacktestStatisticsCalculator:
    """
    Calculates comprehensive statistics from backtest results.
    
    Provides detailed analysis of backtest performance including
    trade statistics, risk metrics, and strategy analysis.
    """
    
    def __init__(self, risk_free_rate: float = 0.0):
        """
        Initialize calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculation (default 0%)
        """
        self.risk_free_rate = risk_free_rate
        logger.info(f"BacktestStatisticsCalculator initialized with risk-free rate: {risk_free_rate}")
    
    def calculate_all_statistics(
        self,
        result: BacktestResult
    ) -> ComprehensiveStatistics:
        """
        Calculate all statistics from a backtest result.
        
        Args:
            result: BacktestResult from backtest engine
            
        Returns:
            ComprehensiveStatistics with complete analysis
        """
        logger.info(f"Calculating comprehensive statistics for {len(result.trades)} trades")
        
        stats = ComprehensiveStatistics(
            backtest_name=result.config.name,
            start_date=result.config.start_date,
            end_date=result.config.end_date,
            initial_balance=result.config.initial_balance,
            final_balance=result.config.initial_balance + result.total_return
        )
        
        # Calculate duration
        if result.config.start_date and result.config.end_date:
            stats.duration_days = (result.config.end_date - result.config.start_date).days
        
        # Calculate each category
        stats.trade_stats = self.calculate_trade_statistics(result.trades)
        stats.return_stats = self.calculate_return_statistics(
            result.equity_curve, result.config.initial_balance, stats.duration_days
        )
        stats.risk_stats = self.calculate_risk_statistics(
            result.equity_curve, stats.return_stats.daily_returns, stats.duration_days
        )
        stats.strategy_stats = self.calculate_strategy_statistics(result.trades)
        
        logger.info(
            f"Statistics calculated: {stats.trade_stats.total_trades} trades, "
            f"{stats.trade_stats.win_rate:.1f}% win rate, "
            f"{stats.risk_stats.sharpe_ratio:.2f} Sharpe"
        )
        
        return stats
    
    def calculate_trade_statistics(self, trades: List[TradeRecord]) -> TradeStatistics:
        """Calculate detailed trade statistics."""
        
        stats = TradeStatistics()
        
        if not trades:
            return stats
        
        # Basic counts
        stats.total_trades = len(trades)
        winning_trades = [t for t in trades if t.outcome == TradeOutcome.WIN]
        losing_trades = [t for t in trades if t.outcome == TradeOutcome.LOSS]
        breakeven_trades = [t for t in trades if t.outcome == TradeOutcome.BREAKEVEN]
        
        stats.winning_trades = len(winning_trades)
        stats.losing_trades = len(losing_trades)
        stats.breakeven_trades = len(breakeven_trades)
        stats.win_rate = (stats.winning_trades / stats.total_trades * 100) if stats.total_trades > 0 else 0.0
        stats.loss_rate = (stats.losing_trades / stats.total_trades * 100) if stats.total_trades > 0 else 0.0
        
        # Streaks
        streaks = self._calculate_streaks(trades)
        stats.max_consecutive_wins = streaks['max_wins']
        stats.max_consecutive_losses = streaks['max_losses']
        stats.current_streak = streaks['current_streak']
        stats.current_streak_type = streaks['current_type']
        
        # P&L statistics
        wins_pnl = [t.pnl_absolute for t in winning_trades if t.pnl_absolute is not None]
        losses_pnl = [t.pnl_absolute for t in losing_trades if t.pnl_absolute is not None]
        
        stats.total_profit = sum(wins_pnl) if wins_pnl else 0.0
        stats.total_loss = sum(losses_pnl) if losses_pnl else 0.0
        stats.avg_win = statistics.mean(wins_pnl) if wins_pnl else 0.0
        stats.avg_loss = statistics.mean(losses_pnl) if losses_pnl else 0.0
        stats.largest_win = max(wins_pnl) if wins_pnl else 0.0
        stats.largest_loss = min(losses_pnl) if losses_pnl else 0.0
        
        # R-multiple statistics
        r_multiples = [t.pnl_r_multiple for t in trades if t.pnl_r_multiple is not None]
        
        if r_multiples:
            stats.avg_r_multiple = statistics.mean(r_multiples)
            stats.median_r_multiple = statistics.median(r_multiples)
            stats.std_r_multiple = statistics.stdev(r_multiples) if len(r_multiples) > 1 else 0.0
            stats.best_r_multiple = max(r_multiples)
            stats.worst_r_multiple = min(r_multiples)
        
        # Expectancy
        all_pnl = [t.pnl_absolute for t in trades if t.pnl_absolute is not None]
        stats.expectancy = statistics.mean(all_pnl) if all_pnl else 0.0
        stats.expectancy_r = stats.avg_r_multiple
        
        # Quality metrics
        stats.profit_factor = abs(stats.total_profit / stats.total_loss) if stats.total_loss != 0 else 0.0
        stats.win_loss_ratio = abs(stats.avg_win / stats.avg_loss) if stats.avg_loss != 0 else 0.0
        
        # Kelly Criterion
        if stats.win_rate > 0 and stats.loss_rate > 0:
            win_prob = stats.win_rate / 100
            loss_prob = stats.loss_rate / 100
            stats.kelly_criterion = (win_prob * stats.win_loss_ratio - loss_prob) / stats.win_loss_ratio if stats.win_loss_ratio > 0 else 0.0
        
        # Duration statistics
        durations = []
        winning_durations = []
        losing_durations = []
        
        for trade in trades:
            if trade.entry_time and trade.exit_time:
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600
                durations.append(duration)
                
                if trade.outcome == TradeOutcome.WIN:
                    winning_durations.append(duration)
                elif trade.outcome == TradeOutcome.LOSS:
                    losing_durations.append(duration)
        
        if durations:
            stats.avg_duration_hours = statistics.mean(durations)
            stats.shortest_trade_hours = min(durations)
            stats.longest_trade_hours = max(durations)
        
        if winning_durations:
            stats.avg_winning_duration_hours = statistics.mean(winning_durations)
        
        if losing_durations:
            stats.avg_losing_duration_hours = statistics.mean(losing_durations)
        
        # MFE/MAE analysis (if available in trade records)
        # Note: This would require trade records to have MFE/MAE fields
        # For now, we'll leave these as 0.0
        
        return stats
    
    def calculate_return_statistics(
        self,
        equity_curve: List[Dict[str, Any]],
        initial_balance: float,
        duration_days: float
    ) -> ReturnStatistics:
        """Calculate return-based statistics."""
        
        stats = ReturnStatistics()
        
        if not equity_curve or len(equity_curve) < 2:
            return stats
        
        # Total return
        final_equity = equity_curve[-1]['equity']
        stats.total_return = final_equity - initial_balance
        stats.total_return_percent = (stats.total_return / initial_balance * 100) if initial_balance > 0 else 0.0
        
        # Annualized return
        if duration_days > 0:
            years = duration_days / 365.25
            stats.annualized_return = ((final_equity / initial_balance) ** (1 / years) - 1) * 100 if years > 0 else 0.0
        
        # Calculate daily returns
        daily_equity = self._aggregate_to_daily(equity_curve)
        stats.daily_returns = self._calculate_period_returns(daily_equity)
        
        if stats.daily_returns:
            stats.avg_daily_return = statistics.mean(stats.daily_returns)
            stats.std_daily_return = statistics.stdev(stats.daily_returns) if len(stats.daily_returns) > 1 else 0.0
            
            # Find best/worst days
            best_idx = stats.daily_returns.index(max(stats.daily_returns))
            worst_idx = stats.daily_returns.index(min(stats.daily_returns))
            
            stats.best_day = {
                'date': daily_equity[best_idx + 1]['timestamp'] if best_idx + 1 < len(daily_equity) else None,
                'return': max(stats.daily_returns),
                'return_pct': max(stats.daily_returns) * 100
            }
            
            stats.worst_day = {
                'date': daily_equity[worst_idx + 1]['timestamp'] if worst_idx + 1 < len(daily_equity) else None,
                'return': min(stats.daily_returns),
                'return_pct': min(stats.daily_returns) * 100
            }
        
        # Calculate monthly returns
        monthly_equity = self._aggregate_to_monthly(equity_curve)
        stats.monthly_returns = self._calculate_period_returns(monthly_equity)
        
        if stats.monthly_returns:
            stats.avg_monthly_return = statistics.mean(stats.monthly_returns)
            stats.std_monthly_return = statistics.stdev(stats.monthly_returns) if len(stats.monthly_returns) > 1 else 0.0
            
            # Find best/worst months
            best_idx = stats.monthly_returns.index(max(stats.monthly_returns))
            worst_idx = stats.monthly_returns.index(min(stats.monthly_returns))
            
            stats.best_month = {
                'date': monthly_equity[best_idx + 1]['timestamp'] if best_idx + 1 < len(monthly_equity) else None,
                'return': max(stats.monthly_returns),
                'return_pct': max(stats.monthly_returns) * 100
            }
            
            stats.worst_month = {
                'date': monthly_equity[worst_idx + 1]['timestamp'] if worst_idx + 1 < len(monthly_equity) else None,
                'return': min(stats.monthly_returns),
                'return_pct': min(stats.monthly_returns) * 100
            }
        
        return stats
    
    def calculate_risk_statistics(
        self,
        equity_curve: List[Dict[str, Any]],
        daily_returns: List[float],
        duration_days: float
    ) -> RiskStatistics:
        """Calculate risk metrics."""
        
        stats = RiskStatistics()
        
        if not equity_curve or len(equity_curve) < 2:
            return stats
        
        # Drawdown analysis
        drawdown_data = self._calculate_drawdowns(equity_curve)
        stats.max_drawdown = drawdown_data['max_drawdown']
        stats.max_drawdown_percent = drawdown_data['max_drawdown_pct']
        stats.avg_drawdown = drawdown_data['avg_drawdown']
        stats.avg_drawdown_percent = drawdown_data['avg_drawdown_pct']
        stats.max_drawdown_duration_days = drawdown_data['max_duration_days']
        stats.recovery_time_days = drawdown_data['recovery_time_days']
        stats.drawdown_periods = drawdown_data['periods']
        
        # Volatility
        if daily_returns:
            stats.volatility_daily = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.0
            stats.volatility_annualized = stats.volatility_daily * (252 ** 0.5)  # Annualized
            
            # Downside deviation (for Sortino)
            downside_returns = [r for r in daily_returns if r < self.risk_free_rate / 252]
            stats.downside_deviation = statistics.stdev(downside_returns) if len(downside_returns) > 1 else 0.0
        
        # Risk-adjusted returns
        if daily_returns and len(daily_returns) > 1:
            avg_return = statistics.mean(daily_returns)
            
            # Sharpe Ratio
            if stats.volatility_daily > 0:
                excess_return = avg_return - (self.risk_free_rate / 252)
                stats.sharpe_ratio = (excess_return / stats.volatility_daily) * (252 ** 0.5)  # Annualized
            
            # Sortino Ratio
            if stats.downside_deviation > 0:
                excess_return = avg_return - (self.risk_free_rate / 252)
                stats.sortino_ratio = (excess_return / stats.downside_deviation) * (252 ** 0.5)  # Annualized
        
        # Calmar Ratio
        if stats.max_drawdown_percent < 0 and duration_days > 0:
            years = duration_days / 365.25
            total_return = (equity_curve[-1]['equity'] / equity_curve[0]['equity'] - 1) * 100
            annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
            stats.calmar_ratio = annualized_return / abs(stats.max_drawdown_percent) if stats.max_drawdown_percent != 0 else 0.0
        
        # Value at Risk (VaR)
        if daily_returns and len(daily_returns) >= 20:  # Need sufficient data
            sorted_returns = sorted(daily_returns)
            
            # 95% VaR
            var_95_idx = int(len(sorted_returns) * 0.05)
            stats.var_95 = sorted_returns[var_95_idx] if var_95_idx < len(sorted_returns) else 0.0
            
            # 99% VaR
            var_99_idx = int(len(sorted_returns) * 0.01)
            stats.var_99 = sorted_returns[var_99_idx] if var_99_idx < len(sorted_returns) else 0.0
            
            # CVaR (Expected Shortfall) - average of worst 5%
            worst_5_pct = sorted_returns[:var_95_idx + 1]
            stats.cvar_95 = statistics.mean(worst_5_pct) if worst_5_pct else 0.0
        
        return stats
    
    def calculate_strategy_statistics(self, trades: List[TradeRecord]) -> StrategyStatistics:
        """Calculate strategy-specific statistics."""
        
        stats = StrategyStatistics()
        
        if not trades:
            return stats
        
        # Direction breakdown
        long_trades = [t for t in trades if t.direction in (OrderSide.LONG, OrderSide.BUY)]
        short_trades = [t for t in trades if t.direction in (OrderSide.SHORT, OrderSide.SELL)]
        
        stats.long_trades = len(long_trades)
        stats.short_trades = len(short_trades)
        
        if long_trades:
            long_wins = len([t for t in long_trades if t.outcome == TradeOutcome.WIN])
            stats.long_win_rate = (long_wins / len(long_trades) * 100)
            stats.long_pnl = sum(t.pnl_absolute for t in long_trades if t.pnl_absolute is not None)
        
        if short_trades:
            short_wins = len([t for t in short_trades if t.outcome == TradeOutcome.WIN])
            stats.short_win_rate = (short_wins / len(short_trades) * 100)
            stats.short_pnl = sum(t.pnl_absolute for t in short_trades if t.pnl_absolute is not None)
        
        # Exit reason breakdown
        for trade in trades:
            if trade.exit_reason:
                reason = trade.exit_reason.value if hasattr(trade.exit_reason, 'value') else str(trade.exit_reason)
                stats.exit_reason_counts[reason] = stats.exit_reason_counts.get(reason, 0) + 1
                
                if trade.pnl_absolute is not None:
                    stats.exit_reason_pnl[reason] = stats.exit_reason_pnl.get(reason, 0.0) + trade.pnl_absolute
        
        # Time-of-day analysis
        hourly_trades = defaultdict(list)
        day_of_week_trades = defaultdict(list)
        
        for trade in trades:
            if trade.entry_time:
                hour = trade.entry_time.hour
                hourly_trades[hour].append(trade)
                
                day_name = trade.entry_time.strftime("%A")
                day_of_week_trades[day_name].append(trade)
        
        # Calculate hourly performance
        for hour, hour_trades in hourly_trades.items():
            wins = len([t for t in hour_trades if t.outcome == TradeOutcome.WIN])
            total_pnl = sum(t.pnl_absolute for t in hour_trades if t.pnl_absolute is not None)
            
            stats.hourly_performance[hour] = {
                'trades': len(hour_trades),
                'wins': wins,
                'win_rate': (wins / len(hour_trades) * 100) if hour_trades else 0.0,
                'total_pnl': total_pnl
            }
        
        # Calculate day-of-week performance
        for day, day_trades in day_of_week_trades.items():
            wins = len([t for t in day_trades if t.outcome == TradeOutcome.WIN])
            total_pnl = sum(t.pnl_absolute for t in day_trades if t.pnl_absolute is not None)
            
            stats.day_of_week_performance[day] = {
                'trades': len(day_trades),
                'wins': wins,
                'win_rate': (wins / len(day_trades) * 100) if day_trades else 0.0,
                'total_pnl': total_pnl
            }
        
        return stats
    
    def update_backtest_result_with_stats(
        self,
        result: BacktestResult,
        stats: ComprehensiveStatistics
    ) -> BacktestResult:
        """
        Update BacktestResult with calculated statistics.
        
        Fills in missing fields like sortino_ratio, max_consecutive_wins, etc.
        """
        result.sortino_ratio = stats.risk_stats.sortino_ratio
        result.max_consecutive_wins = stats.trade_stats.max_consecutive_wins
        result.max_consecutive_losses = stats.trade_stats.max_consecutive_losses
        
        return result
    
    # ===== HELPER METHODS =====
    
    def _calculate_streaks(self, trades: List[TradeRecord]) -> Dict[str, Any]:
        """Calculate winning and losing streaks."""
        
        max_wins = 0
        max_losses = 0
        current_streak = 0
        current_type = ""
        
        for trade in trades:
            if trade.outcome == TradeOutcome.WIN:
                if current_type == "win":
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = "win"
                max_wins = max(max_wins, current_streak)
                
            elif trade.outcome == TradeOutcome.LOSS:
                if current_type == "loss":
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = "loss"
                max_losses = max(max_losses, current_streak)
        
        return {
            'max_wins': max_wins,
            'max_losses': max_losses,
            'current_streak': current_streak,
            'current_type': current_type
        }
    
    def _aggregate_to_daily(self, equity_curve: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate equity curve to daily granularity."""
        
        if not equity_curve:
            return []
        
        daily_data = {}
        
        for point in equity_curve:
            timestamp = point['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            date_str = timestamp.strftime("%Y-%m-%d")
            
            # Keep the last equity value for each day
            daily_data[date_str] = {
                'timestamp': timestamp.replace(hour=23, minute=59, second=59),
                'equity': point['equity']
            }
        
        # Sort by date
        return [daily_data[k] for k in sorted(daily_data.keys())]
    
    def _aggregate_to_monthly(self, equity_curve: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate equity curve to monthly granularity."""
        
        if not equity_curve:
            return []
        
        monthly_data = {}
        
        for point in equity_curve:
            timestamp = point['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            month_str = timestamp.strftime("%Y-%m")
            
            # Keep the last equity value for each month
            monthly_data[month_str] = {
                'timestamp': timestamp,
                'equity': point['equity']
            }
        
        # Sort by month
        return [monthly_data[k] for k in sorted(monthly_data.keys())]
    
    def _calculate_period_returns(self, period_data: List[Dict[str, Any]]) -> List[float]:
        """Calculate returns for periods."""
        
        if len(period_data) < 2:
            return []
        
        returns = []
        
        for i in range(1, len(period_data)):
            prev_equity = period_data[i - 1]['equity']
            curr_equity = period_data[i]['equity']
            
            if prev_equity > 0:
                period_return = (curr_equity - prev_equity) / prev_equity
                returns.append(period_return)
        
        return returns
    
    def _calculate_drawdowns(self, equity_curve: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate drawdown analysis."""
        
        if len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'avg_drawdown': 0.0,
                'avg_drawdown_pct': 0.0,
                'max_duration_days': 0.0,
                'recovery_time_days': 0.0,
                'periods': []
            }
        
        peak = equity_curve[0]['equity']
        max_dd = 0.0
        max_dd_pct = 0.0
        
        drawdowns = []
        current_dd_start = None
        current_dd_peak = peak
        
        all_dds = []
        
        for i, point in enumerate(equity_curve):
            equity = point['equity']
            timestamp = point['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Update peak
            if equity > peak:
                # Recovery - end current drawdown if any
                if current_dd_start is not None:
                    dd_duration = (timestamp - current_dd_start).total_seconds() / 86400
                    drawdowns.append({
                        'start': current_dd_start,
                        'end': timestamp,
                        'duration_days': dd_duration,
                        'peak_equity': current_dd_peak,
                        'trough_equity': peak,  # Peak is the recovery point
                        'drawdown': current_dd_peak - peak,
                        'drawdown_pct': ((current_dd_peak - peak) / current_dd_peak * 100) if current_dd_peak > 0 else 0.0
                    })
                    current_dd_start = None
                
                peak = equity
                current_dd_peak = equity
            
            # Calculate current drawdown
            dd = peak - equity
            dd_pct = (dd / peak * 100) if peak > 0 else 0.0
            
            # Track all drawdowns
            if dd > 0:
                all_dds.append(dd)
            
            # Start new drawdown period
            if dd > 0 and current_dd_start is None:
                current_dd_start = timestamp
                current_dd_peak = peak
            
            # Update max drawdown
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        # Calculate averages
        avg_dd = statistics.mean(all_dds) if all_dds else 0.0
        avg_dd_pct = (avg_dd / peak * 100) if peak > 0 else 0.0
        
        # Max duration
        max_duration = max([d['duration_days'] for d in drawdowns]) if drawdowns else 0.0
        
        # Recovery time (most recent drawdown)
        recovery_time = drawdowns[-1]['duration_days'] if drawdowns else 0.0
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'avg_drawdown': avg_dd,
            'avg_drawdown_pct': avg_dd_pct,
            'max_duration_days': max_duration,
            'recovery_time_days': recovery_time,
            'periods': drawdowns
        }


# Export
__all__ = [
    "TradeStatistics",
    "ReturnStatistics",
    "RiskStatistics",
    "StrategyStatistics",
    "ComprehensiveStatistics",
    "BacktestStatisticsCalculator"
]
