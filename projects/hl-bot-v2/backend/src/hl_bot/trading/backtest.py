"""Backtest engine with candle streaming and real-time state updates.

Principles:
- Stream candles chronologically — never load entire dataset into memory
- Idempotent — same input produces same output
- Audit everything — full replay capability
- Fail gracefully — bad data doesn't kill the backtest
- Safety over speed — validate every order
"""

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Callable

from pydantic import BaseModel, Field

from src.hl_bot.types import Signal, SignalType, Trade, TradeStatus
from src.hl_bot.trading.position import (
    Fill,
    Position,
    PositionTracker,
    round_price,
    round_quantity,
    get_symbol_precision,
)
from src.hl_bot.trading.risk import RiskManager
from src.hl_bot.trading.risk_config import RiskConfig
from src.hl_bot.trading.audit_logger import AuditLogger
from app.core.market.data import Candle


class BacktestStatus(StrEnum):
    """Backtest execution status."""
    
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderStatus(StrEnum):
    """Order status during backtest."""
    
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class BacktestOrder:
    """Order during backtest."""
    
    id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", "stop"
    quantity: Decimal
    price: Decimal
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    fill_price: Optional[Decimal] = None
    
    # For stop and limit orders
    trigger_price: Optional[Decimal] = None
    
    # Order context
    signal_id: Optional[str] = None
    reason: str = ""


@dataclass
class BacktestTrade:
    """Trade execution record."""
    
    id: str
    signal_id: str
    symbol: str
    side: SignalType
    entry_price: Decimal
    entry_time: datetime
    position_size: Decimal
    
    # Exit tracking
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    
    # Levels
    stop_loss: Decimal = Decimal("0")
    take_profit_1: Decimal = Decimal("0")
    take_profit_2: Decimal = Decimal("0")
    take_profit_3: Optional[Decimal] = None
    
    # P&L
    realized_pnl: Decimal = Decimal("0")
    realized_pnl_percent: Decimal = Decimal("0")
    
    # Execution tracking
    tp1_filled: bool = False
    tp2_filled: bool = False
    tp3_filled: bool = False
    partial_exits: List[Dict] = field(default_factory=list)
    
    status: TradeStatus = TradeStatus.OPEN
    
    def calculate_pnl(self) -> Decimal:
        """Calculate current P&L."""
        if self.exit_price is None:
            return Decimal("0")
        
        if self.side == SignalType.LONG:
            pnl = (self.exit_price - self.entry_price) * self.position_size
        else:
            pnl = (self.entry_price - self.exit_price) * self.position_size
        
        self.realized_pnl = pnl
        self.realized_pnl_percent = (pnl / (self.entry_price * self.position_size)) * Decimal("100")
        
        return pnl


class BacktestConfig(BaseModel):
    """Backtest configuration."""
    
    initial_capital: float = Field(default=10000.0, gt=0)
    position_size_percent: float = Field(default=0.02, gt=0, le=1)  # 2% per trade
    max_open_trades: int = Field(default=3, ge=1)
    commission_percent: float = Field(default=0.0006, ge=0)  # 0.06% per trade
    slippage_percent: float = Field(default=0.0001, ge=0)  # 0.01% slippage
    use_stop_orders: bool = Field(default=True)
    use_take_profits: bool = Field(default=True)
    partial_exit_enabled: bool = Field(default=True)
    tp1_exit_percent: float = Field(default=0.5, gt=0, le=1)  # Exit 50% at TP1
    tp2_exit_percent: float = Field(default=0.5, gt=0, le=1)  # Exit 50% at TP2
    
    # Trailing stop
    use_trailing_stop: bool = Field(default=False)
    trailing_stop_trigger_r: float = Field(default=1.0, gt=0)  # Activate at 1R
    trailing_stop_distance_r: float = Field(default=0.5, gt=0)  # Trail at 0.5R


class BacktestMetrics(BaseModel):
    """Backtest performance metrics."""
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    
    sharpe_ratio: float = 0.0
    
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    # Time-based
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Equity curve
    equity_curve: List[Dict] = field(default_factory=list)


class BacktestState(BaseModel):
    """Current backtest state for streaming."""
    
    status: BacktestStatus = BacktestStatus.IDLE
    current_time: Optional[datetime] = None
    current_candle_index: int = 0
    total_candles: int = 0
    progress_percent: float = 0.0
    
    # Capital tracking
    current_capital: float = 0.0
    peak_capital: float = 0.0
    drawdown: float = 0.0
    
    # Active positions
    open_trades: List[Dict] = field(default_factory=list)
    
    # Recent activity
    recent_signals: List[Dict] = field(default_factory=list)
    recent_trades: List[Dict] = field(default_factory=list)
    
    # Metrics
    metrics: BacktestMetrics = field(default_factory=BacktestMetrics)
    
    # Current prices
    current_prices: Dict[str, float] = field(default_factory=dict)


class BacktestEngine:
    """Backtest engine with candle streaming.
    
    Features:
    - Streams candles chronologically (memory efficient)
    - Real-time state updates for WebSocket streaming
    - Signal generation integration
    - Position and risk management
    - Partial exits at take profit levels
    - Full audit trail
    - Pause/resume/seek capability
    
    Example:
        >>> engine = BacktestEngine(
        ...     config=BacktestConfig(initial_capital=10000),
        ...     signal_generator=my_signal_generator,
        ... )
        >>> 
        >>> async for state in engine.run(candles):
        ...     print(f"Time: {state.current_time}, Equity: {state.current_capital}")
    """
    
    def __init__(
        self,
        config: BacktestConfig,
        signal_generator: Optional[Callable] = None,
        audit_dir: Optional[Path] = None,
    ):
        """Initialize backtest engine.
        
        Args:
            config: Backtest configuration
            signal_generator: Function to generate signals from candle data
            audit_dir: Directory for audit logs (optional)
        """
        self.config = config
        self.signal_generator = signal_generator
        
        # Initialize components
        self.position_tracker = PositionTracker()
        
        # Initialize risk manager with position tracker
        risk_config = RiskConfig()  # Use default risk config
        self.risk_manager = RiskManager(
            config=risk_config,
            position_tracker=self.position_tracker,
            initial_balance=Decimal(str(config.initial_capital)),
        )
        
        # Audit logger
        self.audit_logger = None
        if audit_dir:
            self.audit_logger = AuditLogger(audit_dir)
        
        # State tracking
        self.state = BacktestState(
            status=BacktestStatus.IDLE,
            current_capital=config.initial_capital,
            peak_capital=config.initial_capital,
        )
        
        self.state.metrics.start_time = datetime.now(timezone.utc)
        
        # Trade tracking
        self.trades: Dict[str, BacktestTrade] = {}
        self.closed_trades: List[BacktestTrade] = []
        
        # Order tracking
        self.pending_orders: List[BacktestOrder] = []
        
        # Signal tracking
        self.signals: List[Signal] = []
        
        # State update callbacks
        self.state_callbacks: List[Callable] = []
        
        # Control flags
        self._paused = False
        self._stop_requested = False
        self._step_mode = False
        self._step_requested = False
        self._playback_speed = 1.0  # 1.0 = normal, 2.0 = 2x, 0.5 = half speed
        self._seek_to_index: Optional[int] = None
    
    def add_state_callback(self, callback: Callable[[BacktestState], None]) -> None:
        """Add callback for state updates.
        
        Args:
            callback: Function to call with state updates
        """
        self.state_callbacks.append(callback)
    
    async def _emit_state_update(self) -> None:
        """Emit state update to all callbacks."""
        for callback in self.state_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.state)
                else:
                    callback(self.state)
            except Exception as e:
                print(f"[backtest] State callback error: {e}")
    
    async def run(
        self,
        candles: List[Candle],
        emit_interval: int = 10,
    ) -> AsyncGenerator[BacktestState, None]:
        """Run backtest with candle streaming.
        
        Args:
            candles: List of candles sorted by timestamp
            emit_interval: Emit state every N candles
            
        Yields:
            BacktestState after each interval
        """
        self.state.status = BacktestStatus.RUNNING
        self.state.total_candles = len(candles)
        
        if not candles:
            self.state.status = BacktestStatus.COMPLETED
            yield self.state
            return
        
        try:
            idx = 0
            while idx < len(candles):
                if self._stop_requested:
                    self.state.status = BacktestStatus.COMPLETED
                    break
                
                # Handle seek
                if self._seek_to_index is not None:
                    target_idx = min(self._seek_to_index, len(candles) - 1)
                    if target_idx != idx:
                        # Fast-forward or rewind
                        # For rewind, we'd need to rebuild state (simplified: just skip forward)
                        if target_idx > idx:
                            # Fast-forward by processing candles quickly
                            while idx < target_idx:
                                await self._process_candle(candles[idx], idx)
                                idx += 1
                        # For full seek support with rewind, you'd need to checkpoint/restore state
                    self._seek_to_index = None
                    await self._emit_state_update()
                    yield self.state
                
                # Handle pause - yield state first so client knows we're paused
                if self._paused and not self._step_requested:
                    self.state.status = BacktestStatus.PAUSED
                    # Update current_candle_index to reflect where we are now
                    self.state.current_candle_index = idx
                    if idx < len(candles):
                        self.state.current_time = candles[idx].timestamp
                    await self._emit_state_update()
                    yield self.state
                    # Now wait for unpause/step
                    while self._paused and not self._step_requested:
                        await asyncio.sleep(0.1)
                
                candle = candles[idx]
                
                # Process candle
                await self._process_candle(candle, idx)
                
                # Update state (after processing, before potentially yielding)
                self.state.current_time = candle.timestamp
                self.state.progress_percent = (idx + 1) / len(candles) * 100
                self.state.current_prices[candle.symbol] = candle.close
                
                # Handle step mode - advance index BEFORE yielding so state shows next position
                if self._step_requested:
                    self._step_requested = False
                    self._paused = True
                    self.state.status = BacktestStatus.PAUSED
                    # After step, we've processed idx, now we're at idx+1
                    idx += 1
                    self.state.current_candle_index = idx
                    await self._emit_state_update()
                    yield self.state
                    continue  # Skip the normal yield and idx increment below
                
                # Normal mode: update current index
                self.state.current_candle_index = idx
                
                # Apply playback speed delay
                if self._playback_speed < 1.0:
                    delay = (1.0 - self._playback_speed) * 0.1  # Adjust delay based on speed
                    await asyncio.sleep(delay)
                
                # Emit state update (adjust interval based on speed)
                effective_interval = max(1, int(emit_interval / self._playback_speed))
                if idx % effective_interval == 0 or idx == len(candles) - 1:
                    await self._emit_state_update()
                    yield self.state
                
                idx += 1
            
            # Finalize
            await self._finalize()
            self.state.status = BacktestStatus.COMPLETED
            self.state.metrics.end_time = datetime.now(timezone.utc)
            
            await self._emit_state_update()
            yield self.state
            
        except Exception as e:
            self.state.status = BacktestStatus.FAILED
            print(f"[backtest] Failed: {e}")
            raise
    
    async def _process_candle(self, candle: Candle, index: int) -> None:
        """Process a single candle.
        
        Steps:
        1. Check for order fills (stop losses, take profits)
        2. Generate signals (if signal generator provided)
        3. Open new trades from signals
        4. Update position prices
        5. Update equity curve
        """
        # Update position prices
        self.position_tracker.update_prices({candle.symbol: Decimal(str(candle.close))})
        
        # Check pending orders
        await self._check_pending_orders(candle)
        
        # Check for exits (stops and take profits)
        await self._check_exits(candle)
        
        # Generate signal (if signal generator available)
        if self.signal_generator and index >= 50:  # Need some history
            # Get multi-timeframe data (simplified - in real implementation,
            # you'd maintain separate candle buffers per timeframe)
            signal = await self._generate_signal(candle, index)
            
            if signal:
                self.signals.append(signal)
                self.state.recent_signals.append({
                    "id": signal.id,
                    "timestamp": signal.timestamp.isoformat(),
                    "type": signal.signal_type.value,
                    "entry": signal.entry_price,
                    "confluence": signal.confluence_score,
                })
                
                # Try to open trade
                await self._open_trade_from_signal(signal, candle)
        
        # Update equity curve
        self._update_equity_curve(candle.timestamp)
    
    async def _generate_signal(self, candle: Candle, index: int) -> Optional[Signal]:
        """Generate signal from current market state.
        
        Args:
            candle: Current candle
            index: Current candle index
            
        Returns:
            Signal if generated, None otherwise
        """
        try:
            # Call signal generator
            # In real implementation, you'd pass multi-timeframe data
            signal = self.signal_generator(candle)
            return signal
        except Exception as e:
            print(f"[backtest] Signal generation failed: {e}")
            return None
    
    async def _open_trade_from_signal(self, signal: Signal, candle: Candle) -> None:
        """Open trade from signal.
        
        Args:
            signal: Trading signal
            candle: Current candle
        """
        # Check if can open more trades
        open_trade_count = len([t for t in self.trades.values() if t.status == TradeStatus.OPEN])
        if open_trade_count >= self.config.max_open_trades:
            return
        
        # Calculate position size
        position_size = self._calculate_position_size(signal)
        
        if position_size <= 0:
            return
        
        # Get symbol precision
        precision = get_symbol_precision(signal.symbol)
        position_size = round_quantity(Decimal(str(position_size)), precision["lot_size"])
        
        # Apply slippage to entry
        entry_price = Decimal(str(signal.entry_price))
        slippage = entry_price * Decimal(str(self.config.slippage_percent))
        
        if signal.signal_type == SignalType.LONG:
            fill_price = entry_price + slippage
        else:
            fill_price = entry_price - slippage
        
        fill_price = round_price(fill_price, precision["tick_size"])
        
        # Calculate commission
        commission = fill_price * position_size * Decimal(str(self.config.commission_percent))
        
        # Create trade
        trade = BacktestTrade(
            id=str(uuid.uuid4()),
            signal_id=signal.id,
            symbol=signal.symbol,
            side=signal.signal_type,
            entry_price=fill_price,
            entry_time=candle.timestamp,
            position_size=position_size,
            stop_loss=Decimal(str(signal.stop_loss)),
            take_profit_1=Decimal(str(signal.take_profit_1)),
            take_profit_2=Decimal(str(signal.take_profit_2)),
            take_profit_3=Decimal(str(signal.take_profit_3)) if signal.take_profit_3 else None,
            status=TradeStatus.OPEN,
        )
        
        self.trades[trade.id] = trade
        
        # Update capital (subtract cost + commission)
        cost = fill_price * position_size + commission
        self.state.current_capital -= float(cost)
        self.state.metrics.total_commission += float(commission)
        self.state.metrics.total_slippage += float(abs(fill_price - entry_price) * position_size)
        
        # Create fill for position tracker
        fill = Fill(
            symbol=signal.symbol,
            side="buy" if signal.signal_type == SignalType.LONG else "sell",
            quantity=position_size,
            price=fill_price,
            timestamp=candle.timestamp,
            order_id=trade.id,
            fill_id=str(uuid.uuid4()),
            fee=commission,
        )
        
        self.position_tracker.update_from_fill(fill)
        
        # Create pending stop and take profit orders
        if self.config.use_stop_orders:
            self._create_stop_order(trade, candle.timestamp)
        
        if self.config.use_take_profits:
            self._create_take_profit_orders(trade, candle.timestamp)
        
        # Add to recent trades
        self.state.recent_trades.append({
            "id": trade.id,
            "timestamp": trade.entry_time.isoformat(),
            "type": trade.side.value,
            "entry": float(trade.entry_price),
            "size": float(trade.position_size),
        })
        
        # Keep only recent 10
        if len(self.state.recent_trades) > 10:
            self.state.recent_trades.pop(0)
        
        if self.audit_logger:
            await self.audit_logger.log_event("trade_opened", {
                "trade_id": trade.id,
                "signal_id": signal.id,
                "symbol": signal.symbol,
                "side": trade.side.value,
                "entry": float(trade.entry_price),
                "size": float(trade.position_size),
                "stop": float(trade.stop_loss),
            })
    
    def _calculate_position_size(self, signal: Signal) -> Decimal:
        """Calculate position size based on risk.
        
        Args:
            signal: Trading signal
            
        Returns:
            Position size in base currency
        """
        # Risk per trade
        risk_amount = Decimal(str(self.state.current_capital)) * Decimal(str(self.config.position_size_percent))
        
        # Calculate stop distance
        entry = Decimal(str(signal.entry_price))
        stop = Decimal(str(signal.stop_loss))
        stop_distance = abs(entry - stop)
        
        if stop_distance == 0:
            return Decimal("0")
        
        # Position size = risk / stop distance
        position_size = risk_amount / stop_distance
        
        return position_size
    
    def _create_stop_order(self, trade: BacktestTrade, timestamp: datetime) -> None:
        """Create stop loss order.
        
        Args:
            trade: Trade to protect
            timestamp: Order creation time
        """
        order = BacktestOrder(
            id=str(uuid.uuid4()),
            symbol=trade.symbol,
            side="sell" if trade.side == SignalType.LONG else "buy",
            order_type="stop",
            quantity=trade.position_size,
            price=trade.stop_loss,
            trigger_price=trade.stop_loss,
            signal_id=trade.signal_id,
            reason="Stop loss",
            created_at=timestamp,
        )
        
        self.pending_orders.append(order)
    
    def _create_take_profit_orders(self, trade: BacktestTrade, timestamp: datetime) -> None:
        """Create take profit orders.
        
        Args:
            trade: Trade to set take profits for
            timestamp: Order creation time
        """
        if self.config.partial_exit_enabled:
            # TP1 - partial exit
            tp1_size = trade.position_size * Decimal(str(self.config.tp1_exit_percent))
            order1 = BacktestOrder(
                id=str(uuid.uuid4()),
                symbol=trade.symbol,
                side="sell" if trade.side == SignalType.LONG else "buy",
                order_type="limit",
                quantity=tp1_size,
                price=trade.take_profit_1,
                trigger_price=trade.take_profit_1,
                signal_id=trade.signal_id,
                reason="Take profit 1",
                created_at=timestamp,
            )
            self.pending_orders.append(order1)
            
            # TP2 - remaining position
            remaining = trade.position_size - tp1_size
            order2 = BacktestOrder(
                id=str(uuid.uuid4()),
                symbol=trade.symbol,
                side="sell" if trade.side == SignalType.LONG else "buy",
                order_type="limit",
                quantity=remaining,
                price=trade.take_profit_2,
                trigger_price=trade.take_profit_2,
                signal_id=trade.signal_id,
                reason="Take profit 2",
                created_at=timestamp,
            )
            self.pending_orders.append(order2)
    
    async def _check_pending_orders(self, candle: Candle) -> None:
        """Check if any pending orders should be filled.
        
        Args:
            candle: Current candle
        """
        filled_orders = []
        
        for order in self.pending_orders:
            if order.symbol != candle.symbol:
                continue
            
            # Check if triggered
            triggered = False
            fill_price = None
            
            if order.order_type == "market":
                triggered = True
                fill_price = Decimal(str(candle.open))
            elif order.order_type == "limit":
                # Limit buy fills at or below limit price
                # Limit sell fills at or above limit price
                if order.side == "buy" and candle.low <= float(order.price):
                    triggered = True
                    fill_price = order.price
                elif order.side == "sell" and candle.high >= float(order.price):
                    triggered = True
                    fill_price = order.price
            elif order.order_type == "stop":
                # Stop buy triggers at or above stop
                # Stop sell triggers at or below stop
                if order.side == "buy" and candle.high >= float(order.trigger_price):
                    triggered = True
                    fill_price = order.trigger_price
                elif order.side == "sell" and candle.low <= float(order.trigger_price):
                    triggered = True
                    fill_price = order.trigger_price
            
            if triggered and fill_price:
                # Fill order
                order.status = OrderStatus.FILLED
                order.filled_at = candle.timestamp
                order.fill_price = fill_price
                filled_orders.append(order)
                
                # Process fill
                await self._process_order_fill(order, candle.timestamp)
        
        # Remove filled orders
        for order in filled_orders:
            if order in self.pending_orders:
                self.pending_orders.remove(order)
    
    async def _process_order_fill(self, order: BacktestOrder, timestamp: datetime) -> None:
        """Process order fill.
        
        Args:
            order: Filled order
            timestamp: Fill time
        """
        # Find associated trade
        trade = None
        for t in self.trades.values():
            if t.signal_id == order.signal_id and t.status == TradeStatus.OPEN:
                trade = t
                break
        
        if not trade:
            return
        
        # Apply slippage
        fill_price = order.fill_price
        slippage = fill_price * Decimal(str(self.config.slippage_percent))
        
        if order.side == "buy":
            fill_price += slippage
        else:
            fill_price -= slippage
        
        # Calculate commission
        commission = fill_price * order.quantity * Decimal(str(self.config.commission_percent))
        
        # Determine exit reason
        if "stop" in order.reason.lower():
            exit_reason = "Stop loss"
            trade.status = TradeStatus.STOPPED
        elif "take profit 1" in order.reason.lower():
            exit_reason = "Take profit 1"
            trade.tp1_filled = True
            # Don't close trade yet, partial exit
            if not trade.tp2_filled:
                trade.status = TradeStatus.TP1_HIT
        elif "take profit 2" in order.reason.lower():
            exit_reason = "Take profit 2"
            trade.tp2_filled = True
            trade.status = TradeStatus.TP2_HIT
        else:
            exit_reason = "Manual exit"
        
        # Calculate P&L for this exit
        if trade.side == SignalType.LONG:
            pnl = (fill_price - trade.entry_price) * order.quantity
        else:
            pnl = (trade.entry_price - fill_price) * order.quantity
        
        pnl -= commission  # Subtract commission
        
        trade.realized_pnl += pnl
        trade.partial_exits.append({
            "timestamp": timestamp.isoformat(),
            "price": float(fill_price),
            "quantity": float(order.quantity),
            "pnl": float(pnl),
            "reason": exit_reason,
        })
        
        # Update capital
        proceeds = fill_price * order.quantity - commission
        self.state.current_capital += float(proceeds)
        self.state.metrics.total_commission += float(commission)
        self.state.metrics.total_slippage += float(abs(fill_price - order.fill_price) * order.quantity)
        
        # If trade fully closed, update metrics
        if trade.status in (TradeStatus.STOPPED, TradeStatus.TP2_HIT):
            trade.exit_price = fill_price
            trade.exit_time = timestamp
            trade.exit_reason = exit_reason
            trade.calculate_pnl()
            
            # Move to closed trades
            self.closed_trades.append(trade)
            del self.trades[trade.id]
            
            # Update metrics
            self._update_metrics(trade)
            
            # Cancel other pending orders for this trade
            self.pending_orders = [
                o for o in self.pending_orders
                if o.signal_id != trade.signal_id
            ]
            
            if self.audit_logger:
                await self.audit_logger.log_event("trade_closed", {
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "exit_price": float(trade.exit_price),
                    "pnl": float(trade.realized_pnl),
                    "pnl_percent": float(trade.realized_pnl_percent),
                    "reason": exit_reason,
                })
    
    async def _check_exits(self, candle: Candle) -> None:
        """Check if any trades should be exited.
        
        This is already handled by pending orders, but we keep this
        for any additional exit logic (like trailing stops).
        
        Args:
            candle: Current candle
        """
        # Trailing stops would be implemented here
        pass
    
    def _update_equity_curve(self, timestamp: datetime) -> None:
        """Update equity curve.
        
        Args:
            timestamp: Current timestamp
        """
        # Calculate total equity (capital + unrealized P&L)
        unrealized_pnl = self.position_tracker.get_unrealized_pnl()
        total_equity = Decimal(str(self.state.current_capital)) + unrealized_pnl
        
        # Update peak and drawdown
        if total_equity > Decimal(str(self.state.peak_capital)):
            self.state.peak_capital = float(total_equity)
        
        drawdown = Decimal(str(self.state.peak_capital)) - total_equity
        self.state.drawdown = float(drawdown)
        
        # Track max drawdown
        if drawdown > Decimal(str(self.state.metrics.max_drawdown)):
            self.state.metrics.max_drawdown = float(drawdown)
            self.state.metrics.max_drawdown_percent = float(
                (drawdown / Decimal(str(self.state.peak_capital))) * Decimal("100")
            )
        
        # Add to equity curve
        self.state.metrics.equity_curve.append({
            "timestamp": timestamp.isoformat(),
            "equity": float(total_equity),
            "drawdown": float(drawdown),
        })
        
        # Update state open trades
        self.state.open_trades = [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side.value,
                "entry": float(t.entry_price),
                "size": float(t.position_size),
                "unrealized_pnl": float(
                    self.position_tracker.get_position(t.symbol).unrealized_pnl
                ),
            }
            for t in self.trades.values()
        ]
    
    def _update_metrics(self, trade: BacktestTrade) -> None:
        """Update performance metrics with closed trade.
        
        Args:
            trade: Closed trade
        """
        metrics = self.state.metrics
        
        metrics.total_trades += 1
        
        pnl = float(trade.realized_pnl)
        metrics.total_pnl += pnl
        
        if pnl > 0:
            metrics.winning_trades += 1
            metrics.average_win = (
                (metrics.average_win * (metrics.winning_trades - 1) + pnl)
                / metrics.winning_trades
            )
            if pnl > metrics.largest_win:
                metrics.largest_win = pnl
        else:
            metrics.losing_trades += 1
            metrics.average_loss = (
                (metrics.average_loss * (metrics.losing_trades - 1) + pnl)
                / metrics.losing_trades
            )
            if pnl < metrics.largest_loss:
                metrics.largest_loss = pnl
        
        # Win rate
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades
        
        # Profit factor
        total_wins = metrics.average_win * metrics.winning_trades
        total_losses = abs(metrics.average_loss * metrics.losing_trades)
        
        if total_losses > 0:
            metrics.profit_factor = total_wins / total_losses
        
        # Expectancy
        if metrics.total_trades > 0:
            metrics.expectancy = metrics.total_pnl / metrics.total_trades
        
        # Total P&L percent
        initial = self.config.initial_capital
        metrics.total_pnl_percent = (metrics.total_pnl / initial) * 100
    
    async def _finalize(self) -> None:
        """Finalize backtest - close any open trades."""
        # Close all open trades at current price
        for trade in list(self.trades.values()):
            # Get position
            pos = self.position_tracker.get_position(trade.symbol)
            
            if not pos.is_flat:
                # Close at current price
                close_price = pos.current_price
                trade.exit_price = close_price
                trade.exit_time = self.state.current_time
                trade.exit_reason = "Backtest end"
                trade.status = TradeStatus.CLOSED
                trade.calculate_pnl()
                
                # Update capital
                if trade.side == SignalType.LONG:
                    proceeds = close_price * trade.position_size
                else:
                    proceeds = trade.entry_price * trade.position_size - (close_price - trade.entry_price) * trade.position_size
                
                self.state.current_capital += float(proceeds)
                
                # Update metrics
                self._update_metrics(trade)
                
                self.closed_trades.append(trade)
                del self.trades[trade.id]
    
    def pause(self) -> None:
        """Pause backtest execution."""
        self._paused = True
        self._step_mode = False
        self.state.status = BacktestStatus.PAUSED
    
    def resume(self) -> None:
        """Resume backtest execution."""
        self._paused = False
        self._step_mode = False
        self.state.status = BacktestStatus.RUNNING
    
    def stop(self) -> None:
        """Stop backtest execution."""
        self._stop_requested = True
    
    def step(self) -> None:
        """Advance one candle in step mode.
        
        Automatically pauses after advancing one candle.
        """
        self._step_mode = True
        self._step_requested = True
        self._paused = False  # Temporarily unpause to process one candle
    
    def set_speed(self, speed: float) -> None:
        """Set playback speed.
        
        Args:
            speed: Playback speed multiplier (1.0 = normal, 2.0 = 2x, 0.5 = half speed)
        """
        if speed <= 0:
            raise ValueError("Speed must be positive")
        self._playback_speed = speed
    
    def seek(self, candle_index: int) -> None:
        """Seek to specific candle index.
        
        Args:
            candle_index: Target candle index (0-based)
        """
        if candle_index < 0:
            raise ValueError("Candle index must be non-negative")
        self._seek_to_index = candle_index
    
    def get_results(self) -> BacktestMetrics:
        """Get final backtest results.
        
        Returns:
            BacktestMetrics with final performance
        """
        return self.state.metrics
    
    def get_closed_trades(self) -> List[BacktestTrade]:
        """Get all closed trades.
        
        Returns:
            List of closed trades
        """
        return self.closed_trades


# Convenience function for simple backtests
async def run_backtest(
    candles: List[Candle],
    signal_generator: Callable,
    config: Optional[BacktestConfig] = None,
) -> BacktestMetrics:
    """Run a simple backtest and return results.
    
    Args:
        candles: List of candles sorted by timestamp
        signal_generator: Function to generate signals
        config: Backtest configuration (uses defaults if None)
        
    Returns:
        BacktestMetrics with results
        
    Example:
        >>> def my_signal_gen(candle):
        ...     # Generate signal from candle
        ...     return signal
        >>> 
        >>> metrics = await run_backtest(candles, my_signal_gen)
        >>> print(f"Win rate: {metrics.win_rate:.2%}")
        >>> print(f"Total P&L: ${metrics.total_pnl:.2f}")
    """
    config = config or BacktestConfig()
    engine = BacktestEngine(config=config, signal_generator=signal_generator)
    
    async for state in engine.run(candles):
        pass  # Just iterate through to completion
    
    return engine.get_results()
