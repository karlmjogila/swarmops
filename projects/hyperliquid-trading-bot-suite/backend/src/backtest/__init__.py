"""
Backtesting engine for the Hyperliquid Trading Bot Suite.

This module provides comprehensive backtesting capabilities including:
- Historical data loading and management
- Strategy simulation and execution
- Performance analysis and reporting
- Risk metrics calculation
- Comprehensive statistics analysis
"""

from .data_loader import DataLoader, BacktestDataManager, DataRange
from .backtest_engine import BacktestEngine, SimulatedPosition, BacktestState
from .statistics import (
    BacktestStatisticsCalculator,
    ComprehensiveStatistics,
    TradeStatistics,
    ReturnStatistics,
    RiskStatistics,
    StrategyStatistics
)

__all__ = [
    "DataLoader",
    "BacktestDataManager", 
    "DataRange",
    "BacktestEngine",
    "SimulatedPosition",
    "BacktestState",
    "BacktestStatisticsCalculator",
    "ComprehensiveStatistics",
    "TradeStatistics",
    "ReturnStatistics",
    "RiskStatistics",
    "StrategyStatistics"
]