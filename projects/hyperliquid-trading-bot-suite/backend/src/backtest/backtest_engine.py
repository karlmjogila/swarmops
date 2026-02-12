"""
Backtest Engine

Core backtesting engine that simulates trading strategies on historical data.
Processes multi-timeframe data, generates signals via confluence scorer,
makes trading decisions with the trade reasoner, and tracks performance metrics.

This engine provides realistic backtesting with:
- Multi-timeframe support
- Slippage and commission simulation
- Proper position sizing and risk management
- Detailed trade-by-trade analysis
- Real-time equity curve tracking

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from decimal import Decimal
import logging
from collections import defaultdict
from copy import deepcopy

from ..types import (
    CandleData, Timeframe, OrderSide, TradeOutcome, ExitReason,
    BacktestConfig, BacktestResult, TradeRecord, Position,
    PriceActionSnapshot, MarketCycle
)
from .data_loader import DataLoader, BacktestDataManager
from ..detection.confluence_scorer import ConfluenceScorer, ConfluenceScore
from ..trading.trade_reasoner import TradeReasoner, TradeReasoning
from ..knowledge.repository import StrategyRuleRepository
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SimulatedPosition:
    """Represents a simulated position during backtest."""
    id: str
    asset: str
    direction: OrderSide
    entry_price: float
    entry_time: datetime
    quantity: float
    
    # Risk management
    stop_loss: float
    take_profit_levels: List[float]
    
    # P&L tracking
    highest_price: float = 0.0
    lowest_price: float = 0.0
    current_pnl: float = 0.0
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0  # MAE
    
    # Associated trade record
    trade_record: Optional[TradeRecord] = None
    reasoning: Optional[TradeReasoning] = None
    
    # Status
    is_closed: bool = False
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None


@dataclass
class BacktestState:
    """Current state of the backtest simulation."""
    current_time: datetime
    current_balance: float
    initial_balance: float
    
    # Positions
    open_positions: List[SimulatedPosition] = field(default_factory=list)
    closed_positions: List[SimulatedPosition] = field(default_factory=list)
    
    # Equity tracking
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    peak_equity: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_commissions: float = 0.0
    
    # Daily statistics
    daily_pnl: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    daily_trades: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Risk management
    daily_loss_limit_hit: bool = False
    max_positions_reached: bool = False
    
    @property
    def total_equity(self) -> float:
        """Total equity including open position P&L."""
        open_pnl = sum(pos.current_pnl for pos in self.open_positions)
        return self.current_balance + open_pnl
    
    @property
    def available_balance(self) -> float:
        """Balance available for new trades."""
        used_margin = sum(
            pos.quantity * pos.entry_price for pos in self.open_positions
        )
        return self.current_balance - used_margin
    
    def get_date_str(self, timestamp: datetime) -> str:
        """Get date string for daily tracking."""
        return timestamp.strftime("%Y-%m-%d")


class BacktestEngine:
    """
    Core backtesting engine.
    
    Simulates trading strategies on historical data with realistic
    execution modeling including slippage, commissions, and proper
    order fill simulation.
    """
    
    def __init__(
        self,
        session: Session,
        confluence_scorer: Optional[ConfluenceScorer] = None,
        trade_reasoner: Optional[TradeReasoner] = None,
        strategy_repo: Optional[StrategyRuleRepository] = None
    ):
        """
        Initialize backtest engine.
        
        Args:
            session: Database session
            confluence_scorer: Confluence scorer instance (creates new if None)
            trade_reasoner: Trade reasoner instance (creates new if None)
            strategy_repo: Strategy rule repository (creates new if None)
        """
        self.session = session
        self.data_manager = BacktestDataManager(session)
        self.data_loader = self.data_manager.data_loader
        
        # Initialize components
        self.confluence_scorer = confluence_scorer or ConfluenceScorer()
        self.trade_reasoner = trade_reasoner or TradeReasoner(use_llm=False)
        self.strategy_repo = strategy_repo or StrategyRuleRepository(session)
        
        # State
        self.state: Optional[BacktestState] = None
        self.config: Optional[BacktestConfig] = None
        self._loaded_data: Optional[Dict[str, Dict[Timeframe, List[CandleData]]]] = None
        
        logger.info("BacktestEngine initialized")
    
    def run_backtest(self, config: BacktestConfig) -> BacktestResult:
        """
        Run a complete backtest simulation.
        
        Args:
            config: Backtest configuration
            
        Returns:
            BacktestResult with complete performance metrics
        """
        logger.info(f"Starting backtest: {config.name}")
        logger.info(f"Period: {config.start_date} to {config.end_date}")
        logger.info(f"Assets: {config.assets}")
        logger.info(f"Initial balance: ${config.initial_balance:,.2f}")
        
        start_time = datetime.utcnow()
        
        # Store config
        self.config = config
        
        # Initialize state
        self.state = BacktestState(
            current_time=config.start_date,
            current_balance=config.initial_balance,
            initial_balance=config.initial_balance,
            peak_equity=config.initial_balance
        )
        
        # Load data
        logger.info("Loading historical data...")
        prep_result = self.data_manager.prepare_backtest_data(config)
        self._loaded_data = self.data_manager._loaded_data
        
        if not self._loaded_data:
            raise ValueError("Failed to load backtest data")
        
        logger.info(f"Data loaded successfully")
        
        # Get time series for iteration
        time_series = self._generate_time_series(config)
        logger.info(f"Generated {len(time_series)} time steps")
        
        # Run simulation
        logger.info("Running backtest simulation...")
        self._run_simulation(time_series)
        
        # Generate results
        logger.info("Generating results...")
        result = self._generate_results(start_time)
        
        logger.info(f"Backtest complete: {result.total_trades} trades, "
                   f"{result.win_rate:.1f}% win rate, "
                   f"{result.total_return_percent:.2f}% return")
        
        return result
    
    def _generate_time_series(self, config: BacktestConfig) -> List[datetime]:
        """
        Generate time series for simulation.
        
        Uses the lowest timeframe to determine time step granularity.
        """
        # Find the lowest (most granular) timeframe
        timeframe_minutes = {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.M30: 30,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.H12: 720,
            Timeframe.D1: 1440,
            Timeframe.W1: 10080
        }
        
        min_minutes = min(timeframe_minutes[tf] for tf in config.timeframes)
        step = timedelta(minutes=min_minutes)
        
        # Generate time points
        time_series = []
        current = config.start_date
        
        while current <= config.end_date:
            time_series.append(current)
            current += step
        
        return time_series
    
    def _run_simulation(self, time_series: List[datetime]):
        """
        Main simulation loop.
        
        Iterates through time series, checking for signals and managing positions.
        """
        total_steps = len(time_series)
        log_interval = max(1, total_steps // 20)  # Log 20 times during backtest
        
        for i, timestamp in enumerate(time_series):
            self.state.current_time = timestamp
            
            # Log progress
            if i % log_interval == 0:
                progress = (i / total_steps) * 100
                logger.info(f"Progress: {progress:.1f}% - {timestamp} - "
                           f"Equity: ${self.state.total_equity:,.2f} - "
                           f"Open positions: {len(self.state.open_positions)}")
            
            # Check daily loss limit
            date_str = self.state.get_date_str(timestamp)
            if self._check_daily_loss_limit(date_str):
                continue
            
            # Update open positions
            self._update_open_positions(timestamp)
            
            # Check for new signals
            self._check_for_signals(timestamp)
            
            # Record equity snapshot (hourly)
            if i % 60 == 0 or i == total_steps - 1:
                self._record_equity_snapshot(timestamp)
    
    def _check_for_signals(self, timestamp: datetime):
        """
        Check for trading signals at current timestamp.
        
        Uses confluence scorer and trade reasoner to identify opportunities.
        """
        # Check if we can take more positions
        if len(self.state.open_positions) >= self.config.max_concurrent_trades:
            return
        
        # Check each asset
        for asset in self.config.assets:
            # Skip if we already have a position in this asset
            if any(pos.asset == asset for pos in self.state.open_positions):
                continue
            
            # Get multi-timeframe data at this point in time
            mtf_data = self._get_mtf_data_at_time(asset, timestamp)
            
            if not mtf_data:
                continue
            
            # Run confluence analysis
            confluence_score = self._analyze_confluence(asset, mtf_data, timestamp)
            
            # Check if score meets threshold
            if confluence_score.total_score < 0.6:  # Minimum threshold
                continue
            
            # Get trade reasoning
            reasoning = self._get_trade_reasoning(
                asset, mtf_data, confluence_score, timestamp
            )
            
            # Decide whether to enter
            if reasoning.should_enter and reasoning.confidence >= 0.6:
                self._enter_position(
                    asset, reasoning, confluence_score, mtf_data, timestamp
                )
    
    def _get_mtf_data_at_time(
        self,
        asset: str,
        timestamp: datetime
    ) -> Optional[Dict[Timeframe, List[CandleData]]]:
        """
        Get multi-timeframe data for an asset at a specific time.
        
        Returns historical candles up to (but not after) the given timestamp.
        """
        if not self._loaded_data or asset not in self._loaded_data:
            return None
        
        mtf_data = {}
        
        for timeframe in self.config.timeframes:
            candles = self.data_manager.get_candles_at_time(
                asset, timeframe, timestamp, lookback_count=200
            )
            
            if candles:
                mtf_data[timeframe] = candles
        
        return mtf_data if mtf_data else None
    
    def _analyze_confluence(
        self,
        asset: str,
        mtf_data: Dict[Timeframe, List[CandleData]],
        timestamp: datetime
    ) -> ConfluenceScore:
        """Analyze multi-timeframe confluence."""
        try:
            return self.confluence_scorer.analyze_confluence(mtf_data)
        except Exception as e:
            logger.warning(f"Confluence analysis failed for {asset} at {timestamp}: {e}")
            return ConfluenceScore()  # Return empty score
    
    def _get_trade_reasoning(
        self,
        asset: str,
        mtf_data: Dict[Timeframe, List[CandleData]],
        confluence_score: ConfluenceScore,
        timestamp: datetime
    ) -> TradeReasoning:
        """Get trade reasoning from LLM/rule-based system."""
        try:
            # Get latest candle from entry timeframe
            entry_tf = min(self.config.timeframes, key=lambda tf: self._tf_to_minutes(tf))
            latest_candle = mtf_data[entry_tf][-1] if mtf_data.get(entry_tf) else None
            
            return self.trade_reasoner.analyze_trade_opportunity(
                asset=asset,
                confluence_score=confluence_score,
                current_candle=latest_candle,
                mtf_candles=mtf_data
            )
        except Exception as e:
            logger.warning(f"Trade reasoning failed for {asset} at {timestamp}: {e}")
            return TradeReasoning(should_enter=False, confidence=0.0)
    
    def _enter_position(
        self,
        asset: str,
        reasoning: TradeReasoning,
        confluence_score: ConfluenceScore,
        mtf_data: Dict[Timeframe, List[CandleData]],
        timestamp: datetime
    ):
        """
        Enter a new position.
        
        Calculates position size based on risk, simulates execution with slippage.
        """
        # Get current price (latest candle close)
        entry_tf = min(self.config.timeframes, key=lambda tf: self._tf_to_minutes(tf))
        latest_candle = mtf_data[entry_tf][-1]
        base_price = latest_candle.close
        
        # Apply slippage
        direction = reasoning.entry_bias or confluence_score.bias_direction or OrderSide.LONG
        slippage_factor = 1 + self.config.slippage if direction == OrderSide.LONG else 1 - self.config.slippage
        entry_price = base_price * slippage_factor
        
        # Calculate stop loss
        stop_loss = self._calculate_stop_loss(
            entry_price, direction, reasoning, latest_candle
        )
        
        # Calculate position size based on risk
        quantity = self._calculate_position_size(
            entry_price, stop_loss, direction
        )
        
        if quantity <= 0:
            logger.debug(f"Skipping trade - invalid position size for {asset}")
            return
        
        # Calculate take profit levels
        take_profit_levels = self._calculate_take_profits(
            entry_price, stop_loss, direction, reasoning
        )
        
        # Create simulated position
        position_id = f"pos_{timestamp.timestamp()}_{asset}"
        
        # Create trade record
        trade_record = TradeRecord(
            id=position_id,
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            entry_time=timestamp,
            quantity=quantity,
            initial_stop_loss=stop_loss,
            current_stop_loss=stop_loss,
            take_profit_levels=take_profit_levels,
            reasoning=reasoning.explanation,
            outcome=TradeOutcome.PENDING
        )
        
        # Create position
        position = SimulatedPosition(
            id=position_id,
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            entry_time=timestamp,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit_levels=take_profit_levels,
            trade_record=trade_record,
            reasoning=reasoning,
            highest_price=entry_price,
            lowest_price=entry_price
        )
        
        # Calculate and deduct commission
        commission = quantity * entry_price * self.config.commission
        self.state.current_balance -= commission
        self.state.total_commissions += commission
        
        # Add to open positions
        self.state.open_positions.append(position)
        self.state.total_trades += 1
        
        # Update daily stats
        date_str = self.state.get_date_str(timestamp)
        self.state.daily_trades[date_str] += 1
        
        logger.info(
            f"ENTER {direction.value.upper()} {asset} @ ${entry_price:.2f} "
            f"| Size: {quantity:.4f} | SL: ${stop_loss:.2f} | "
            f"Reason: {reasoning.setup_type} | Confidence: {reasoning.confidence:.2f}"
        )
    
    def _update_open_positions(self, timestamp: datetime):
        """
        Update all open positions with current prices.
        
        Checks for stop loss, take profit hits, and updates P&L.
        """
        positions_to_close = []
        
        for position in self.state.open_positions:
            # Get current price
            current_price = self._get_current_price(position.asset, timestamp)
            
            if current_price is None:
                continue
            
            # Update price extremes
            position.highest_price = max(position.highest_price, current_price)
            position.lowest_price = min(position.lowest_price, current_price)
            
            # Calculate P&L
            if position.direction == OrderSide.LONG:
                pnl = (current_price - position.entry_price) * position.quantity
                position.max_favorable_excursion = max(
                    position.max_favorable_excursion,
                    (position.highest_price - position.entry_price) * position.quantity
                )
                position.max_adverse_excursion = min(
                    position.max_adverse_excursion,
                    (position.lowest_price - position.entry_price) * position.quantity
                )
            else:  # SHORT
                pnl = (position.entry_price - current_price) * position.quantity
                position.max_favorable_excursion = max(
                    position.max_favorable_excursion,
                    (position.entry_price - position.lowest_price) * position.quantity
                )
                position.max_adverse_excursion = min(
                    position.max_adverse_excursion,
                    (position.entry_price - position.highest_price) * position.quantity
                )
            
            position.current_pnl = pnl
            
            # Check for exit conditions
            exit_reason = self._check_exit_conditions(position, current_price)
            
            if exit_reason:
                positions_to_close.append((position, current_price, exit_reason, timestamp))
        
        # Close positions that hit exit conditions
        for position, exit_price, exit_reason, exit_time in positions_to_close:
            self._close_position(position, exit_price, exit_reason, exit_time)
    
    def _check_exit_conditions(
        self,
        position: SimulatedPosition,
        current_price: float
    ) -> Optional[ExitReason]:
        """Check if position should be closed."""
        
        # Check stop loss
        if position.direction == OrderSide.LONG:
            if current_price <= position.stop_loss:
                return ExitReason.STOP_LOSS
            
            # Check take profits
            for i, tp_level in enumerate(position.take_profit_levels):
                if current_price >= tp_level:
                    return ExitReason.TP1 if i == 0 else (
                        ExitReason.TP2 if i == 1 else ExitReason.TP3
                    )
        
        else:  # SHORT
            if current_price >= position.stop_loss:
                return ExitReason.STOP_LOSS
            
            # Check take profits
            for i, tp_level in enumerate(position.take_profit_levels):
                if current_price <= tp_level:
                    return ExitReason.TP1 if i == 0 else (
                        ExitReason.TP2 if i == 1 else ExitReason.TP3
                    )
        
        return None
    
    def _close_position(
        self,
        position: SimulatedPosition,
        exit_price: float,
        exit_reason: ExitReason,
        exit_time: datetime
    ):
        """Close a position and update state."""
        
        # Apply slippage on exit
        slippage_factor = (1 - self.config.slippage if position.direction == OrderSide.LONG 
                          else 1 + self.config.slippage)
        actual_exit_price = exit_price * slippage_factor
        
        # Calculate final P&L
        if position.direction == OrderSide.LONG:
            pnl = (actual_exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - actual_exit_price) * position.quantity
        
        # Deduct commission
        commission = position.quantity * actual_exit_price * self.config.commission
        pnl -= commission
        self.state.total_commissions += commission
        
        # Update balance
        self.state.current_balance += pnl
        
        # Update position
        position.exit_price = actual_exit_price
        position.exit_time = exit_time
        position.exit_reason = exit_reason
        position.is_closed = True
        
        # Update trade record
        if position.trade_record:
            position.trade_record.exit_price = actual_exit_price
            position.trade_record.exit_time = exit_time
            position.trade_record.exit_reason = exit_reason
            position.trade_record.pnl_absolute = pnl
            
            # Calculate R-multiple
            risk = abs(position.entry_price - position.stop_loss) * position.quantity
            position.trade_record.pnl_r_multiple = pnl / risk if risk > 0 else 0.0
            
            # Set outcome
            if pnl > 0:
                position.trade_record.outcome = TradeOutcome.WIN
                self.state.winning_trades += 1
            elif pnl < 0:
                position.trade_record.outcome = TradeOutcome.LOSS
                self.state.losing_trades += 1
            else:
                position.trade_record.outcome = TradeOutcome.BREAKEVEN
        
        # Update daily stats
        date_str = self.state.get_date_str(exit_time)
        self.state.daily_pnl[date_str] += pnl
        
        # Move to closed positions
        self.state.open_positions.remove(position)
        self.state.closed_positions.append(position)
        
        # Update drawdown tracking
        self.state.peak_equity = max(self.state.peak_equity, self.state.total_equity)
        drawdown = self.state.peak_equity - self.state.total_equity
        drawdown_pct = (drawdown / self.state.peak_equity * 100) if self.state.peak_equity > 0 else 0
        self.state.current_drawdown = drawdown
        self.state.max_drawdown = max(self.state.max_drawdown, drawdown)
        
        logger.info(
            f"CLOSE {position.direction.value.upper()} {position.asset} @ ${actual_exit_price:.2f} "
            f"| P&L: ${pnl:+.2f} ({position.trade_record.pnl_r_multiple:+.2f}R) "
            f"| Reason: {exit_reason.value} | Duration: {(exit_time - position.entry_time).total_seconds() / 3600:.1f}h"
        )
    
    def _get_current_price(self, asset: str, timestamp: datetime) -> Optional[float]:
        """Get current price for an asset at timestamp."""
        # Use the lowest timeframe for most accurate price
        entry_tf = min(self.config.timeframes, key=lambda tf: self._tf_to_minutes(tf))
        
        candles = self.data_manager.get_candles_at_time(
            asset, entry_tf, timestamp, lookback_count=1
        )
        
        if candles:
            return candles[-1].close
        
        return None
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        direction: OrderSide,
        reasoning: TradeReasoning,
        latest_candle: CandleData
    ) -> float:
        """Calculate stop loss level."""
        
        # Use suggested stop loss if available
        if reasoning.suggested_stop_loss:
            return reasoning.suggested_stop_loss
        
        # Default: Use candle low/high with buffer
        buffer = 0.002  # 0.2% buffer
        
        if direction == OrderSide.LONG:
            # Place stop below candle low
            return latest_candle.low * (1 - buffer)
        else:
            # Place stop above candle high
            return latest_candle.high * (1 + buffer)
    
    def _calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        direction: OrderSide
    ) -> float:
        """
        Calculate position size based on risk per trade.
        
        Uses the configured risk percentage to size positions.
        """
        # Calculate risk per share
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
        
        # Calculate dollar risk amount
        risk_amount = self.state.total_equity * (self.config.risk_per_trade / 100)
        
        # Calculate quantity
        quantity = risk_amount / risk_per_unit
        
        # Ensure we don't exceed available balance
        position_value = quantity * entry_price
        max_position_value = self.state.available_balance * 0.95  # Leave 5% buffer
        
        if position_value > max_position_value:
            quantity = max_position_value / entry_price
        
        return quantity
    
    def _calculate_take_profits(
        self,
        entry_price: float,
        stop_loss: float,
        direction: OrderSide,
        reasoning: TradeReasoning
    ) -> List[float]:
        """Calculate take profit levels."""
        
        # Use suggested targets if available
        if reasoning.suggested_targets:
            return reasoning.suggested_targets[:3]  # Max 3 targets
        
        # Default: Use R-multiples
        risk = abs(entry_price - stop_loss)
        r_multiples = [2.0, 3.0, 5.0]  # 2R, 3R, 5R targets
        
        take_profits = []
        for r in r_multiples:
            if direction == OrderSide.LONG:
                tp = entry_price + (risk * r)
            else:
                tp = entry_price - (risk * r)
            take_profits.append(tp)
        
        return take_profits
    
    def _check_daily_loss_limit(self, date_str: str) -> bool:
        """Check if daily loss limit has been hit."""
        daily_pnl = self.state.daily_pnl.get(date_str, 0.0)
        loss_limit = self.state.initial_balance * (self.config.daily_loss_limit_percent / 100)
        
        if daily_pnl < -loss_limit:
            if not self.state.daily_loss_limit_hit:
                logger.warning(f"Daily loss limit hit on {date_str}: ${daily_pnl:.2f}")
                self.state.daily_loss_limit_hit = True
            return True
        
        self.state.daily_loss_limit_hit = False
        return False
    
    def _record_equity_snapshot(self, timestamp: datetime):
        """Record equity snapshot for equity curve."""
        self.state.equity_curve.append({
            'timestamp': timestamp.isoformat(),
            'equity': self.state.total_equity,
            'balance': self.state.current_balance,
            'open_positions': len(self.state.open_positions),
            'drawdown': self.state.current_drawdown,
            'drawdown_pct': (self.state.current_drawdown / self.state.peak_equity * 100) 
                            if self.state.peak_equity > 0 else 0
        })
    
    def _generate_results(self, start_time: datetime) -> BacktestResult:
        """Generate final backtest results."""
        
        # Close any remaining open positions at end of backtest
        final_time = self.config.end_date
        for position in list(self.state.open_positions):
            final_price = self._get_current_price(position.asset, final_time)
            if final_price:
                self._close_position(
                    position, final_price, ExitReason.TIME_STOP, final_time
                )
        
        # Calculate metrics
        total_return = self.state.current_balance - self.state.initial_balance
        total_return_pct = (total_return / self.state.initial_balance) * 100
        
        win_rate = (self.state.winning_trades / self.state.total_trades * 100) if self.state.total_trades > 0 else 0.0
        
        # Calculate R-multiple stats
        r_multiples = [
            pos.trade_record.pnl_r_multiple 
            for pos in self.state.closed_positions 
            if pos.trade_record
        ]
        
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
        best_r = max(r_multiples) if r_multiples else 0.0
        worst_r = min(r_multiples) if r_multiples else 0.0
        
        # Calculate profit factor
        winning_pnl = sum(
            pos.trade_record.pnl_absolute 
            for pos in self.state.closed_positions 
            if pos.trade_record and pos.trade_record.outcome == TradeOutcome.WIN
        )
        
        losing_pnl = abs(sum(
            pos.trade_record.pnl_absolute 
            for pos in self.state.closed_positions 
            if pos.trade_record and pos.trade_record.outcome == TradeOutcome.LOSS
        ))
        
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else 0.0
        
        # Calculate max drawdown percentage
        max_dd_pct = (self.state.max_drawdown / self.state.initial_balance * 100) if self.state.initial_balance > 0 else 0.0
        
        # Calculate average trade duration
        trade_durations = [
            (pos.exit_time - pos.entry_time).total_seconds() / 3600
            for pos in self.state.closed_positions
            if pos.exit_time
        ]
        avg_duration = sum(trade_durations) / len(trade_durations) if trade_durations else 0.0
        
        # Calculate Sharpe ratio (simplified)
        if len(self.state.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.state.equity_curve)):
                prev_equity = self.state.equity_curve[i-1]['equity']
                curr_equity = self.state.equity_curve[i]['equity']
                ret = (curr_equity - prev_equity) / prev_equity if prev_equity > 0 else 0
                returns.append(ret)
            
            avg_return = sum(returns) / len(returns) if returns else 0
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
            sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0  # Annualized
        else:
            sharpe_ratio = 0.0
        
        # Create result
        result = BacktestResult(
            config=self.config,
            total_trades=self.state.total_trades,
            winning_trades=self.state.winning_trades,
            losing_trades=self.state.losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            total_return_percent=total_return_pct,
            max_drawdown=self.state.max_drawdown,
            max_drawdown_percent=max_dd_pct,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            avg_r_multiple=avg_r,
            best_r_multiple=best_r,
            worst_r_multiple=worst_r,
            avg_trade_duration_hours=avg_duration,
            equity_curve=self.state.equity_curve,
            trades=[pos.trade_record for pos in self.state.closed_positions if pos.trade_record],
            started_at=start_time,
            completed_at=datetime.utcnow(),
            duration_seconds=(datetime.utcnow() - start_time).total_seconds()
        )
        
        return result
    
    def _tf_to_minutes(self, timeframe: Timeframe) -> int:
        """Convert timeframe to minutes."""
        timeframe_minutes = {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.M30: 30,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.H12: 720,
            Timeframe.D1: 1440,
            Timeframe.W1: 10080
        }
        return timeframe_minutes.get(timeframe, 15)


# Export
__all__ = ["BacktestEngine", "SimulatedPosition", "BacktestState"]
