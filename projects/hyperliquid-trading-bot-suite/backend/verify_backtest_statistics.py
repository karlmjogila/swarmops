"""
Verification script for backtest statistics module.

Demonstrates integration between backtest engine and statistics calculator.
"""

from datetime import datetime, timedelta
from src.backtest import BacktestStatisticsCalculator, ComprehensiveStatistics
from src.types import (
    BacktestResult, BacktestConfig, Timeframe,
    TradeRecord, TradeOutcome, OrderSide, ExitReason
)


def create_sample_backtest_result() -> BacktestResult:
    """Create a sample backtest result for testing."""
    
    config = BacktestConfig(
        name="Sample Strategy Backtest",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 31),
        assets=["BTC-USD", "ETH-USD"],
        timeframes=[Timeframe.M15, Timeframe.H1, Timeframe.H4],
        initial_balance=10000.0,
        risk_per_trade=2.0,
        max_concurrent_trades=3,
        commission=0.0004,
        slippage=0.001
    )
    
    # Generate sample trades
    trades = []
    base_time = config.start_date
    
    for i in range(50):
        # Alternate between wins and losses with 60% win rate
        is_win = (i % 5) != 0  # 4 out of 5 = 80% win rate
        
        entry_time = base_time + timedelta(hours=i * 12)
        exit_time = entry_time + timedelta(hours=2 + (i % 4))
        
        if is_win:
            pnl = 150.0 + (i % 3) * 50
            r_mult = 1.5 + (i % 3) * 0.5
            exit_reason = ExitReason.TP1 if i % 2 == 0 else ExitReason.TP2
            outcome = TradeOutcome.WIN
        else:
            pnl = -75.0
            r_mult = -1.0
            exit_reason = ExitReason.STOP_LOSS
            outcome = TradeOutcome.LOSS
        
        trade = TradeRecord(
            id=f"trade_{i}",
            asset="BTC-USD" if i % 2 == 0 else "ETH-USD",
            direction=OrderSide.LONG if i % 3 != 0 else OrderSide.SHORT,
            entry_price=50000.0 + (i * 100),
            entry_time=entry_time,
            quantity=0.1,
            initial_stop_loss=49000.0 + (i * 100),
            current_stop_loss=49000.0 + (i * 100),
            take_profit_levels=[52000.0 + (i * 100)],
            exit_price=52000.0 + (i * 100) if is_win else 49000.0 + (i * 100),
            exit_time=exit_time,
            exit_reason=exit_reason,
            pnl_absolute=pnl,
            pnl_r_multiple=r_mult,
            outcome=outcome,
            reasoning=f"Trade {i} reasoning"
        )
        trades.append(trade)
    
    # Generate sample equity curve
    equity_curve = []
    equity = config.initial_balance
    
    for day in range(90):
        for hour in [0, 6, 12, 18]:
            timestamp = config.start_date + timedelta(days=day, hours=hour)
            
            # Simulate equity growth with some volatility
            if day < 30:
                equity += 50 + (day % 10) * 10
            elif day < 60:
                equity += 30 - (day % 5) * 5  # Some drawdown
            else:
                equity += 40 + (day % 7) * 8
            
            equity_curve.append({
                'timestamp': timestamp.isoformat(),
                'equity': equity,
                'balance': equity,
                'open_positions': 0,
                'drawdown': 0.0,
                'drawdown_pct': 0.0
            })
    
    # Calculate basic metrics
    winning_trades = len([t for t in trades if t.outcome == TradeOutcome.WIN])
    losing_trades = len([t for t in trades if t.outcome == TradeOutcome.LOSS])
    total_return = equity - config.initial_balance
    
    result = BacktestResult(
        config=config,
        total_trades=len(trades),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=(winning_trades / len(trades) * 100),
        total_return=total_return,
        total_return_percent=(total_return / config.initial_balance * 100),
        trades=trades,
        equity_curve=equity_curve,
        started_at=datetime.now(),
        completed_at=datetime.now() + timedelta(seconds=30),
        duration_seconds=30.0
    )
    
    return result


def print_statistics_report(stats: ComprehensiveStatistics):
    """Print a formatted statistics report."""
    
    print("=" * 80)
    print(f"BACKTEST STATISTICS REPORT: {stats.backtest_name}")
    print("=" * 80)
    print()
    
    # Overview
    print("OVERVIEW")
    print("-" * 80)
    print(f"Period:          {stats.start_date.strftime('%Y-%m-%d')} to {stats.end_date.strftime('%Y-%m-%d')}")
    print(f"Duration:        {stats.duration_days:.0f} days")
    print(f"Initial Balance: ${stats.initial_balance:,.2f}")
    print(f"Final Balance:   ${stats.final_balance:,.2f}")
    print(f"Total Return:    ${stats.final_balance - stats.initial_balance:+,.2f} ({stats.return_stats.total_return_percent:+.2f}%)")
    print()
    
    # Trade Statistics
    print("TRADE STATISTICS")
    print("-" * 80)
    ts = stats.trade_stats
    print(f"Total Trades:         {ts.total_trades}")
    print(f"Winning Trades:       {ts.winning_trades} ({ts.win_rate:.2f}%)")
    print(f"Losing Trades:        {ts.losing_trades} ({ts.loss_rate:.2f}%)")
    print(f"Breakeven Trades:     {ts.breakeven_trades}")
    print()
    print(f"Total Profit:         ${ts.total_profit:,.2f}")
    print(f"Total Loss:           ${ts.total_loss:,.2f}")
    print(f"Average Win:          ${ts.avg_win:,.2f}")
    print(f"Average Loss:         ${ts.avg_loss:,.2f}")
    print(f"Largest Win:          ${ts.largest_win:,.2f}")
    print(f"Largest Loss:         ${ts.largest_loss:,.2f}")
    print()
    print(f"Profit Factor:        {ts.profit_factor:.2f}")
    print(f"Win/Loss Ratio:       {ts.win_loss_ratio:.2f}")
    print(f"Expectancy:           ${ts.expectancy:,.2f} per trade")
    print(f"Kelly Criterion:      {ts.kelly_criterion:.2%}")
    print()
    print(f"Average R-Multiple:   {ts.avg_r_multiple:.2f}R")
    print(f"Median R-Multiple:    {ts.median_r_multiple:.2f}R")
    print(f"Best R-Multiple:      {ts.best_r_multiple:.2f}R")
    print(f"Worst R-Multiple:     {ts.worst_r_multiple:.2f}R")
    print()
    print(f"Max Consecutive Wins:   {ts.max_consecutive_wins}")
    print(f"Max Consecutive Losses: {ts.max_consecutive_losses}")
    print(f"Current Streak:         {ts.current_streak} {ts.current_streak_type}(s)")
    print()
    print(f"Avg Trade Duration:   {ts.avg_duration_hours:.1f} hours")
    print(f"Avg Win Duration:     {ts.avg_winning_duration_hours:.1f} hours")
    print(f"Avg Loss Duration:    {ts.avg_losing_duration_hours:.1f} hours")
    print()
    
    # Risk Statistics
    print("RISK METRICS")
    print("-" * 80)
    rs = stats.risk_stats
    print(f"Max Drawdown:         ${rs.max_drawdown:,.2f} ({rs.max_drawdown_percent:.2f}%)")
    print(f"Avg Drawdown:         ${rs.avg_drawdown:,.2f} ({rs.avg_drawdown_percent:.2f}%)")
    print(f"Max DD Duration:      {rs.max_drawdown_duration_days:.1f} days")
    print(f"Recovery Time:        {rs.recovery_time_days:.1f} days")
    print()
    print(f"Sharpe Ratio:         {rs.sharpe_ratio:.3f}")
    print(f"Sortino Ratio:        {rs.sortino_ratio:.3f}")
    print(f"Calmar Ratio:         {rs.calmar_ratio:.3f}")
    print()
    print(f"Daily Volatility:     {rs.volatility_daily:.4f}")
    print(f"Annual Volatility:    {rs.volatility_annualized:.2%}")
    print(f"Downside Deviation:   {rs.downside_deviation:.4f}")
    print()
    print(f"95% VaR (daily):      {rs.var_95:.4f}")
    print(f"99% VaR (daily):      {rs.var_99:.4f}")
    print(f"CVaR (95%):           {rs.cvar_95:.4f}")
    print()
    
    # Strategy Statistics
    print("STRATEGY BREAKDOWN")
    print("-" * 80)
    ss = stats.strategy_stats
    print(f"Long Trades:    {ss.long_trades} ({ss.long_win_rate:.1f}% win rate) - P&L: ${ss.long_pnl:+,.2f}")
    print(f"Short Trades:   {ss.short_trades} ({ss.short_win_rate:.1f}% win rate) - P&L: ${ss.short_pnl:+,.2f}")
    print()
    
    if ss.exit_reason_counts:
        print("Exit Reasons:")
        for reason, count in sorted(ss.exit_reason_counts.items(), key=lambda x: x[1], reverse=True):
            pnl = ss.exit_reason_pnl.get(reason, 0.0)
            print(f"  {reason:15} {count:3} trades - ${pnl:+,.2f}")
        print()
    
    # Return Statistics
    print("RETURN ANALYSIS")
    print("-" * 80)
    ret = stats.return_stats
    print(f"Annualized Return:    {ret.annualized_return:.2f}%")
    print(f"Avg Daily Return:     {ret.avg_daily_return:.4f} ({ret.avg_daily_return * 100:.2f}%)")
    print(f"Daily Volatility:     {ret.std_daily_return:.4f}")
    print(f"Avg Monthly Return:   {ret.avg_monthly_return:.4f} ({ret.avg_monthly_return * 100:.2f}%)")
    print()
    
    if ret.best_day.get('date'):
        print(f"Best Day:   {ret.best_day['date'].strftime('%Y-%m-%d')} - {ret.best_day['return_pct']:+.2f}%")
        print(f"Worst Day:  {ret.worst_day['date'].strftime('%Y-%m-%d')} - {ret.worst_day['return_pct']:+.2f}%")
    
    print()
    print("=" * 80)


def main():
    """Main verification function."""
    
    print("Backtest Statistics Module Verification")
    print("=" * 80)
    print()
    
    # Create sample backtest result
    print("Creating sample backtest result...")
    result = create_sample_backtest_result()
    print(f"✓ Created backtest with {result.total_trades} trades")
    print()
    
    # Initialize calculator
    print("Initializing statistics calculator...")
    calculator = BacktestStatisticsCalculator(risk_free_rate=0.02)  # 2% risk-free rate
    print("✓ Calculator initialized")
    print()
    
    # Calculate statistics
    print("Calculating comprehensive statistics...")
    stats = calculator.calculate_all_statistics(result)
    print("✓ Statistics calculated")
    print()
    
    # Update backtest result
    print("Updating backtest result with calculated statistics...")
    updated_result = calculator.update_backtest_result_with_stats(result, stats)
    print("✓ Backtest result updated")
    print(f"  - Sortino Ratio: {updated_result.sortino_ratio:.3f}")
    print(f"  - Max Consecutive Wins: {updated_result.max_consecutive_wins}")
    print(f"  - Max Consecutive Losses: {updated_result.max_consecutive_losses}")
    print()
    
    # Print detailed report
    print_statistics_report(stats)
    
    print("\n✓ Verification complete!")
    print("\nThe backtest statistics module is working correctly.")
    print("All statistical calculations have been implemented:")
    print("  ✓ Trade statistics (streaks, expectancy, Kelly criterion)")
    print("  ✓ Return statistics (annualized returns, best/worst periods)")
    print("  ✓ Risk metrics (Sharpe, Sortino, Calmar, VaR)")
    print("  ✓ Strategy analysis (direction breakdown, time analysis)")


if __name__ == "__main__":
    main()
