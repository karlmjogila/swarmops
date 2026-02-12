"""
Position Manager for Hyperliquid Trading Bot Suite

Handles position management including:
- Multi-TP exit logic (TP1 at 1R, TP2 at 2R)
- Stop loss placement and updates
- Breakeven trailing activation
- Momentum-based exit detection
- Position state tracking
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field

from ..types import (
    Position, Order, OrderSide, OrderType, OrderStatus, 
    ExitReason, TradeOutcome, TradeRecord, CandleData, MarketData
)
from .hyperliquid_client import HyperliquidClient

logger = logging.getLogger(__name__)


class PositionState(str, Enum):
    """Position management states."""
    ACTIVE = "active"  # Position is open and actively managed
    PARTIAL_TP1 = "partial_tp1"  # TP1 hit, managing remainder
    PARTIAL_TP2 = "partial_tp2"  # TP2 hit, managing remainder  
    BREAKEVEN = "breakeven"  # Stop moved to breakeven
    TRAILING = "trailing"  # Actively trailing stop
    MOMENTUM_EXIT = "momentum_exit"  # Preparing momentum exit
    CLOSED = "closed"  # Position fully closed


@dataclass
class PositionManagementState:
    """Internal state tracking for position management."""
    position_id: str
    asset: str
    side: OrderSide
    entry_price: float
    original_size: float
    current_size: float
    
    # Risk management
    initial_stop_loss: float
    current_stop_loss: float
    risk_amount: float  # Dollar amount risked
    
    # Take profit levels
    tp1_price: float
    tp2_price: float
    tp1_size: float  # 50% of position
    tp2_size: float  # 50% of position
    
    # State tracking
    state: PositionState = PositionState.ACTIVE
    tp1_filled: bool = False
    tp2_filled: bool = False
    breakeven_activated: bool = False
    
    # Active orders
    stop_order_id: Optional[str] = None
    tp1_order_id: Optional[str] = None
    tp2_order_id: Optional[str] = None
    
    # Momentum tracking
    highest_profitable_price: Optional[float] = None
    momentum_exit_triggered: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate current unrealized P&L."""
        if self.side == OrderSide.LONG:
            return (current_price - self.entry_price) * self.current_size
        else:
            return (self.entry_price - current_price) * self.current_size
    
    def calculate_r_multiple(self, current_price: float) -> float:
        """Calculate current R multiple."""
        if self.risk_amount == 0:
            return 0.0
        unrealized_pnl = self.calculate_unrealized_pnl(current_price)
        return unrealized_pnl / self.risk_amount


class PositionManager:
    """
    Advanced position manager with multi-TP exits, breakeven trailing,
    and momentum-based exit detection.
    """
    
    def __init__(self, hyperliquid_client: HyperliquidClient):
        self.client = hyperliquid_client
        self.managed_positions: Dict[str, PositionManagementState] = {}
        self.active_orders: Dict[str, str] = {}  # order_id -> position_id
        
        # Configuration
        self.tp1_r_multiple = 1.0  # TP1 at 1R
        self.tp2_r_multiple = 2.0  # TP2 at 2R
        self.tp1_exit_percentage = 0.5  # Exit 50% at TP1
        self.breakeven_buffer_r = 0.1  # Move to breakeven at +0.1R
        self.momentum_exit_pullback_r = 0.3  # Exit on 0.3R pullback from highs
        
        # Callbacks
        self._position_update_callbacks: List[Callable[[str, PositionManagementState], None]] = []
        self._exit_callbacks: List[Callable[[str, ExitReason, float], None]] = []
        
        # Register for client callbacks
        self.client.add_order_callback(self._handle_order_update)
        self.client.add_position_callback(self._handle_position_update)
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_active = False
        
        # Track background tasks for proper cleanup and error handling
        self._background_tasks: set = set()
        
    async def start_monitoring(self):
        """Start position monitoring loop."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Position monitoring already active")
            return
            
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Position monitoring started")
    
    async def stop_monitoring(self):
        """Stop position monitoring loop."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all pending background tasks
        if self._background_tasks:
            logger.info(f"Cancelling {len(self._background_tasks)} pending background tasks")
            for task in self._background_tasks:
                task.cancel()
            # Wait for all tasks to complete cancellation
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()
        
        logger.info("Position monitoring stopped")
    
    async def manage_position(
        self,
        position: Position,
        trade_record: TradeRecord,
        current_price: float
    ) -> PositionManagementState:
        """
        Start managing a position with multi-TP exits and risk management.
        
        Args:
            position: The position to manage
            trade_record: Associated trade record
            current_price: Current market price
            
        Returns:
            PositionManagementState: Management state object
        """
        logger.info(f"Starting position management for {position.asset} - {position.id}")
        
        # Calculate risk and TP levels
        risk_amount = abs(trade_record.entry_price - trade_record.initial_stop_loss) * abs(position.size)
        
        if position.side == OrderSide.LONG:
            tp1_price = trade_record.entry_price + (self.tp1_r_multiple * risk_amount / abs(position.size))
            tp2_price = trade_record.entry_price + (self.tp2_r_multiple * risk_amount / abs(position.size))
        else:
            tp1_price = trade_record.entry_price - (self.tp1_r_multiple * risk_amount / abs(position.size))
            tp2_price = trade_record.entry_price - (self.tp2_r_multiple * risk_amount / abs(position.size))
        
        # Create management state
        mgmt_state = PositionManagementState(
            position_id=position.id,
            asset=position.asset,
            side=position.side,
            entry_price=trade_record.entry_price,
            original_size=abs(position.size),
            current_size=abs(position.size),
            initial_stop_loss=trade_record.initial_stop_loss,
            current_stop_loss=trade_record.initial_stop_loss,
            risk_amount=risk_amount,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            tp1_size=abs(position.size) * self.tp1_exit_percentage,
            tp2_size=abs(position.size) * (1 - self.tp1_exit_percentage)
        )
        
        # Place initial orders
        await self._place_initial_orders(mgmt_state)
        
        # Store management state
        self.managed_positions[position.id] = mgmt_state
        
        # Notify callbacks
        for callback in self._position_update_callbacks:
            try:
                callback(position.id, mgmt_state)
            except Exception as e:
                logger.error(f"Error in position update callback: {e}")
        
        logger.info(f"Position management active for {position.asset} - TP1: {tp1_price:.4f}, TP2: {tp2_price:.4f}")
        return mgmt_state
    
    async def _place_initial_orders(self, mgmt_state: PositionManagementState):
        """Place initial stop loss and take profit orders."""
        try:
            # Place stop loss order
            stop_order = await self.client.place_order(
                asset=mgmt_state.asset,
                size=mgmt_state.current_size,
                side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                order_type=OrderType.STOP_LOSS,
                stop_price=mgmt_state.current_stop_loss,
                metadata={"position_id": mgmt_state.position_id, "order_purpose": "stop_loss"}
            )
            mgmt_state.stop_order_id = stop_order.id
            self.active_orders[stop_order.id] = mgmt_state.position_id
            
            # Place TP1 order
            tp1_order = await self.client.place_order(
                asset=mgmt_state.asset,
                size=mgmt_state.tp1_size,
                side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=mgmt_state.tp1_price,
                metadata={"position_id": mgmt_state.position_id, "order_purpose": "tp1"}
            )
            mgmt_state.tp1_order_id = tp1_order.id
            self.active_orders[tp1_order.id] = mgmt_state.position_id
            
            # Place TP2 order  
            tp2_order = await self.client.place_order(
                asset=mgmt_state.asset,
                size=mgmt_state.tp2_size,
                side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=mgmt_state.tp2_price,
                metadata={"position_id": mgmt_state.position_id, "order_purpose": "tp2"}
            )
            mgmt_state.tp2_order_id = tp2_order.id
            self.active_orders[tp2_order.id] = mgmt_state.position_id
            
            logger.info(f"Initial orders placed for {mgmt_state.asset}: SL={mgmt_state.current_stop_loss:.4f}, TP1={mgmt_state.tp1_price:.4f}, TP2={mgmt_state.tp2_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error placing initial orders: {e}")
            raise
    
    async def _monitoring_loop(self):
        """Main monitoring loop for position management."""
        logger.info("Position monitoring loop started")
        
        while self._monitoring_active:
            try:
                # Update all managed positions
                for position_id, mgmt_state in list(self.managed_positions.items()):
                    await self._update_position_management(position_id, mgmt_state)
                
                # Sleep before next iteration
                await asyncio.sleep(1.0)  # Monitor every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in position monitoring loop: {e}")
                await asyncio.sleep(5.0)
        
        logger.info("Position monitoring loop stopped")
    
    async def _update_position_management(self, position_id: str, mgmt_state: PositionManagementState):
        """Update management logic for a specific position."""
        try:
            # Get current market data
            market_data = await self.client.get_market_data(mgmt_state.asset)
            if not market_data:
                return
            
            current_price = market_data.last
            
            # Update profit tracking
            if mgmt_state.side == OrderSide.LONG:
                if mgmt_state.highest_profitable_price is None or current_price > mgmt_state.highest_profitable_price:
                    mgmt_state.highest_profitable_price = current_price
            else:
                if mgmt_state.highest_profitable_price is None or current_price < mgmt_state.highest_profitable_price:
                    mgmt_state.highest_profitable_price = current_price
            
            # Check for breakeven trailing activation
            if not mgmt_state.breakeven_activated:
                r_multiple = mgmt_state.calculate_r_multiple(current_price)
                if r_multiple >= self.breakeven_buffer_r:
                    await self._activate_breakeven_trailing(mgmt_state)
            
            # Check for momentum exit conditions
            if mgmt_state.state in [PositionState.PARTIAL_TP1, PositionState.PARTIAL_TP2, PositionState.TRAILING]:
                await self._check_momentum_exit(mgmt_state, current_price)
            
            mgmt_state.last_updated = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error updating position management for {position_id}: {e}")
    
    async def _activate_breakeven_trailing(self, mgmt_state: PositionManagementState):
        """Activate breakeven trailing stop."""
        if mgmt_state.breakeven_activated:
            return
            
        logger.info(f"Activating breakeven trailing for {mgmt_state.asset}")
        
        # Cancel existing stop loss order
        if mgmt_state.stop_order_id:
            await self.client.cancel_order(mgmt_state.stop_order_id)
        
        # Place new breakeven stop
        breakeven_price = mgmt_state.entry_price
        
        try:
            stop_order = await self.client.place_order(
                asset=mgmt_state.asset,
                size=mgmt_state.current_size,
                side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                order_type=OrderType.STOP_LOSS,
                stop_price=breakeven_price,
                metadata={"position_id": mgmt_state.position_id, "order_purpose": "breakeven_stop"}
            )
            
            mgmt_state.stop_order_id = stop_order.id
            mgmt_state.current_stop_loss = breakeven_price
            mgmt_state.breakeven_activated = True
            mgmt_state.state = PositionState.BREAKEVEN
            
            self.active_orders[stop_order.id] = mgmt_state.position_id
            
            logger.info(f"Breakeven stop activated at {breakeven_price:.4f} for {mgmt_state.asset}")
            
        except Exception as e:
            logger.error(f"Error activating breakeven trailing: {e}")
    
    async def _check_momentum_exit(self, mgmt_state: PositionManagementState, current_price: float):
        """Check for momentum-based exit conditions."""
        if not mgmt_state.highest_profitable_price or mgmt_state.momentum_exit_triggered:
            return
        
        # Calculate pullback from highest profitable price
        if mgmt_state.side == OrderSide.LONG:
            pullback_amount = mgmt_state.highest_profitable_price - current_price
            pullback_r = pullback_amount / (mgmt_state.risk_amount / mgmt_state.original_size)
        else:
            pullback_amount = current_price - mgmt_state.highest_profitable_price
            pullback_r = pullback_amount / (mgmt_state.risk_amount / mgmt_state.original_size)
        
        # Check if pullback threshold exceeded
        if pullback_r >= self.momentum_exit_pullback_r:
            logger.info(f"Momentum exit triggered for {mgmt_state.asset} - pullback: {pullback_r:.2f}R")
            await self._execute_momentum_exit(mgmt_state, current_price)
    
    async def _execute_momentum_exit(self, mgmt_state: PositionManagementState, exit_price: float):
        """Execute momentum-based position exit."""
        try:
            # Cancel all pending orders
            for order_id in [mgmt_state.stop_order_id, mgmt_state.tp1_order_id, mgmt_state.tp2_order_id]:
                if order_id:
                    await self.client.cancel_order(order_id)
            
            # Place market exit order for remaining position
            if mgmt_state.current_size > 0:
                exit_order = await self.client.place_order(
                    asset=mgmt_state.asset,
                    size=mgmt_state.current_size,
                    side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    metadata={"position_id": mgmt_state.position_id, "order_purpose": "momentum_exit"}
                )
                
                logger.info(f"Momentum exit order placed for {mgmt_state.asset}: {mgmt_state.current_size} @ market")
            
            mgmt_state.momentum_exit_triggered = True
            mgmt_state.state = PositionState.MOMENTUM_EXIT
            
            # Notify exit callbacks
            for callback in self._exit_callbacks:
                try:
                    callback(mgmt_state.position_id, ExitReason.MOMENTUM, exit_price)
                except Exception as e:
                    logger.error(f"Error in exit callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error executing momentum exit: {e}")
    
    def _handle_order_update(self, order: Order):
        """Handle order updates from the client."""
        if order.id not in self.active_orders:
            return
        
        position_id = self.active_orders[order.id]
        mgmt_state = self.managed_positions.get(position_id)
        
        if not mgmt_state:
            return
        
        # Create task with proper tracking and error handling
        task = asyncio.create_task(
            self._process_order_update(mgmt_state, order),
            name=f"order_update_{order.id}"
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._task_done_callback)
    
    def _task_done_callback(self, task: asyncio.Task):
        """Callback when a background task completes. Handles errors and cleanup."""
        # Remove task from tracking set
        self._background_tasks.discard(task)
        
        # Check for exceptions
        if task.cancelled():
            logger.debug(f"Task {task.get_name()} was cancelled")
            return
        
        exception = task.exception()
        if exception:
            logger.error(
                f"Background task {task.get_name()} failed with error: {exception}",
                exc_info=(type(exception), exception, exception.__traceback__)
            )
    
    async def _process_order_update(self, mgmt_state: PositionManagementState, order: Order):
        """Process order update in async context."""
        try:
            if order.status == OrderStatus.FILLED:
                await self._handle_order_filled(mgmt_state, order)
            elif order.status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                await self._handle_order_cancelled(mgmt_state, order)
                
        except Exception as e:
            logger.error(f"Error processing order update: {e}", exc_info=True)
            raise  # Re-raise so it's captured by task callback
    
    async def _handle_order_filled(self, mgmt_state: PositionManagementState, order: Order):
        """Handle filled orders."""
        order_purpose = order.metadata.get("order_purpose")
        
        if order_purpose == "tp1":
            logger.info(f"TP1 hit for {mgmt_state.asset} at {order.avg_fill_price:.4f}")
            mgmt_state.tp1_filled = True
            mgmt_state.current_size -= order.filled_size
            mgmt_state.state = PositionState.PARTIAL_TP1
            
            # Update stop loss and TP2 orders for remaining position
            await self._update_orders_after_tp1(mgmt_state)
            
            # Notify callbacks
            for callback in self._exit_callbacks:
                try:
                    callback(mgmt_state.position_id, ExitReason.TP1, order.avg_fill_price)
                except Exception as e:
                    logger.error(f"Error in exit callback: {e}")
                    
        elif order_purpose == "tp2":
            logger.info(f"TP2 hit for {mgmt_state.asset} at {order.avg_fill_price:.4f}")
            mgmt_state.tp2_filled = True
            mgmt_state.current_size -= order.filled_size
            mgmt_state.state = PositionState.PARTIAL_TP2
            
            # Notify callbacks
            for callback in self._exit_callbacks:
                try:
                    callback(mgmt_state.position_id, ExitReason.TP2, order.avg_fill_price)
                except Exception as e:
                    logger.error(f"Error in exit callback: {e}")
                    
        elif order_purpose in ["stop_loss", "breakeven_stop"]:
            logger.info(f"Stop loss hit for {mgmt_state.asset} at {order.avg_fill_price:.4f}")
            mgmt_state.current_size = 0
            mgmt_state.state = PositionState.CLOSED
            
            # Clean up position
            await self._cleanup_position(mgmt_state.position_id)
            
            # Notify callbacks
            exit_reason = ExitReason.BREAKEVEN if order_purpose == "breakeven_stop" else ExitReason.STOP_LOSS
            for callback in self._exit_callbacks:
                try:
                    callback(mgmt_state.position_id, exit_reason, order.avg_fill_price)
                except Exception as e:
                    logger.error(f"Error in exit callback: {e}")
    
    async def _handle_order_cancelled(self, mgmt_state: PositionManagementState, order: Order):
        """Handle cancelled orders."""
        order_purpose = order.metadata.get("order_purpose")
        logger.warning(f"Order cancelled for {mgmt_state.asset}: {order_purpose} - {order.id}")
        
        # Remove from active orders
        if order.id in self.active_orders:
            del self.active_orders[order.id]
        
        # Reset order ID in management state
        if order.id == mgmt_state.stop_order_id:
            mgmt_state.stop_order_id = None
        elif order.id == mgmt_state.tp1_order_id:
            mgmt_state.tp1_order_id = None
        elif order.id == mgmt_state.tp2_order_id:
            mgmt_state.tp2_order_id = None
    
    async def _update_orders_after_tp1(self, mgmt_state: PositionManagementState):
        """Update orders after TP1 is hit."""
        try:
            # Cancel and replace stop loss for remaining position
            if mgmt_state.stop_order_id:
                await self.client.cancel_order(mgmt_state.stop_order_id)
            
            # Place new stop for remaining size
            stop_order = await self.client.place_order(
                asset=mgmt_state.asset,
                size=mgmt_state.current_size,
                side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                order_type=OrderType.STOP_LOSS,
                stop_price=mgmt_state.current_stop_loss,
                metadata={"position_id": mgmt_state.position_id, "order_purpose": "stop_loss"}
            )
            
            mgmt_state.stop_order_id = stop_order.id
            self.active_orders[stop_order.id] = mgmt_state.position_id
            
        except Exception as e:
            logger.error(f"Error updating orders after TP1: {e}")
    
    def _handle_position_update(self, position: Position):
        """Handle position updates from the client."""
        if position.id in self.managed_positions:
            mgmt_state = self.managed_positions[position.id]
            # Update current size if position was modified externally
            mgmt_state.current_size = abs(position.size)
    
    async def _cleanup_position(self, position_id: str):
        """Clean up completed position management."""
        if position_id not in self.managed_positions:
            return
            
        mgmt_state = self.managed_positions[position_id]
        
        # Cancel any remaining orders
        for order_id in [mgmt_state.stop_order_id, mgmt_state.tp1_order_id, mgmt_state.tp2_order_id]:
            if order_id:
                try:
                    await self.client.cancel_order(order_id)
                    if order_id in self.active_orders:
                        del self.active_orders[order_id]
                except Exception as e:
                    logger.error(f"Error cancelling order during cleanup: {e}")
        
        # Remove from managed positions
        del self.managed_positions[position_id]
        logger.info(f"Position management cleaned up for {position_id}")
    
    async def close_position(self, position_id: str, reason: ExitReason = ExitReason.MANUAL) -> bool:
        """Manually close a managed position."""
        if position_id not in self.managed_positions:
            logger.warning(f"Position {position_id} not under management")
            return False
        
        mgmt_state = self.managed_positions[position_id]
        
        try:
            # Cancel all orders
            for order_id in [mgmt_state.stop_order_id, mgmt_state.tp1_order_id, mgmt_state.tp2_order_id]:
                if order_id:
                    await self.client.cancel_order(order_id)
            
            # Place market exit order
            if mgmt_state.current_size > 0:
                exit_order = await self.client.place_order(
                    asset=mgmt_state.asset,
                    size=mgmt_state.current_size,
                    side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    metadata={"position_id": position_id, "order_purpose": "manual_close"}
                )
                
                logger.info(f"Manual close order placed for {mgmt_state.asset}: {mgmt_state.current_size} @ market")
            
            mgmt_state.state = PositionState.CLOSED
            await self._cleanup_position(position_id)
            
            # Notify callbacks
            for callback in self._exit_callbacks:
                try:
                    callback(position_id, reason, 0.0)  # Price will be updated when order fills
                except Exception as e:
                    logger.error(f"Error in exit callback: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position manually: {e}")
            return False
    
    def get_managed_positions(self) -> List[PositionManagementState]:
        """Get all currently managed positions."""
        return list(self.managed_positions.values())
    
    def get_position_state(self, position_id: str) -> Optional[PositionManagementState]:
        """Get management state for a specific position."""
        return self.managed_positions.get(position_id)
    
    def add_position_update_callback(self, callback: Callable[[str, PositionManagementState], None]):
        """Add callback for position updates."""
        self._position_update_callbacks.append(callback)
    
    def add_exit_callback(self, callback: Callable[[str, ExitReason, float], None]):
        """Add callback for position exits."""
        self._exit_callbacks.append(callback)
    
    def remove_position_update_callback(self, callback: Callable[[str, PositionManagementState], None]):
        """Remove position update callback."""
        if callback in self._position_update_callbacks:
            self._position_update_callbacks.remove(callback)
    
    def remove_exit_callback(self, callback: Callable[[str, ExitReason, float], None]):
        """Remove exit callback."""
        if callback in self._exit_callbacks:
            self._exit_callbacks.remove(callback)
    
    async def get_position_statistics(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get performance statistics for a managed position."""
        mgmt_state = self.managed_positions.get(position_id)
        if not mgmt_state:
            return None
        
        # Get current market data
        market_data = await self.client.get_market_data(mgmt_state.asset)
        if not market_data:
            return None
        
        current_price = market_data.last
        
        return {
            "position_id": position_id,
            "asset": mgmt_state.asset,
            "side": mgmt_state.side.value,
            "state": mgmt_state.state.value,
            "entry_price": mgmt_state.entry_price,
            "current_price": current_price,
            "original_size": mgmt_state.original_size,
            "current_size": mgmt_state.current_size,
            "unrealized_pnl": mgmt_state.calculate_unrealized_pnl(current_price),
            "r_multiple": mgmt_state.calculate_r_multiple(current_price),
            "tp1_price": mgmt_state.tp1_price,
            "tp2_price": mgmt_state.tp2_price,
            "current_stop": mgmt_state.current_stop_loss,
            "tp1_filled": mgmt_state.tp1_filled,
            "tp2_filled": mgmt_state.tp2_filled,
            "breakeven_activated": mgmt_state.breakeven_activated,
            "highest_profitable_price": mgmt_state.highest_profitable_price,
            "created_at": mgmt_state.created_at.isoformat(),
            "last_updated": mgmt_state.last_updated.isoformat()
        }