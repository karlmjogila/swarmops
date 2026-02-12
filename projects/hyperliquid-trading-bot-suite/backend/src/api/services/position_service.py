"""Position management service for API integration."""

from typing import Dict, List, Optional, Any
import asyncio
import secrets
import structlog
from datetime import datetime, timezone
from decimal import Decimal

from ...trading.position_manager import PositionManager, PositionManagementState
from ...trading.hyperliquid_client import HyperliquidClient
from ...types import Position, ExitReason, OrderSide, TradeRecord
from ..routes.trades import Position as PositionResponse
from .trade_service import trade_service

logger = structlog.get_logger()


class PositionService:
    """Service layer for position management API integration."""
    
    def __init__(self):
        self.client: Optional[HyperliquidClient] = None
        self.position_manager: Optional[PositionManager] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the position service with clients."""
        if self._initialized:
            return
            
        try:
            # Initialize Hyperliquid client
            self.client = HyperliquidClient()
            await self.client.connect()
            
            # Initialize position manager
            self.position_manager = PositionManager(self.client)
            
            # Add callbacks for real-time updates
            self.position_manager.add_position_update_callback(self._on_position_update)
            self.position_manager.add_exit_callback(self._on_position_exit)
            
            # Start monitoring
            await self.position_manager.start_monitoring()
            
            self._initialized = True
            logger.info("Position service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize position service", error=str(e))
            raise
    
    async def create_manual_trade(
        self,
        user_id: str,
        symbol: str,
        direction: str,
        quantity: str,
        entry_price: Optional[str] = None,
        stop_loss: Optional[str] = None,
        take_profit_1: Optional[str] = None,
        take_profit_2: Optional[str] = None,
        reasoning: Optional[str] = None
    ) -> str:
        """
        Create a manual trade.
        
        All numeric values are handled as strings/Decimal for precision.
        
        Args:
            user_id: User ID creating the trade
            symbol: Trading symbol
            direction: 'long' or 'short'
            quantity: Trade quantity as string
            entry_price: Optional entry price (uses market if not provided)
            stop_loss: Stop loss price as string
            take_profit_1: First take profit level as string
            take_profit_2: Second take profit level as string
            reasoning: Trade reasoning
            
        Returns:
            trade_id: The created trade ID
        """
        await self.initialize()
        
        # Generate unique trade ID
        trade_id = f"manual_{secrets.token_hex(12)}"
        
        # Create trade record via trade service
        await trade_service.create_trade(
            trade_id=trade_id,
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            reasoning=reasoning,
            strategy_id="manual",
            strategy_name="Manual Trade",
            confluence_score="1.0"
        )
        
        logger.info(
            "Manual trade created",
            trade_id=trade_id,
            user_id=user_id,
            symbol=symbol,
            direction=direction
        )
        
        return trade_id
    
    async def get_current_positions(self, user_id: str) -> List[PositionResponse]:
        """Get all current open positions for a user."""
        await self.initialize()
        
        try:
            # Get positions from Hyperliquid
            hyperliquid_positions = await self.client.get_positions()
            
            # Get managed positions from position manager
            managed_positions = {
                mgmt.position_id: mgmt 
                for mgmt in self.position_manager.get_managed_positions()
            }
            
            positions = []
            
            for hl_pos in hyperliquid_positions:
                # Get current market price
                market_data = await self.client.get_market_data(hl_pos.asset)
                current_price = market_data.last if market_data else hl_pos.avg_fill_price
                
                # Check if this position is managed
                mgmt_state = managed_positions.get(hl_pos.id)
                
                # Calculate P&L using Decimal for precision
                entry = Decimal(str(hl_pos.avg_fill_price))
                current = Decimal(str(current_price))
                size = Decimal(str(abs(hl_pos.size)))
                
                if hl_pos.side == OrderSide.LONG:
                    unrealized_pnl = float((current - entry) * size)
                else:
                    unrealized_pnl = float((entry - current) * size)
                
                # Calculate R multiple if managed
                unrealized_pnl_r = 0.0
                if mgmt_state:
                    unrealized_pnl_r = mgmt_state.calculate_r_multiple(current_price)
                
                position_data = PositionResponse.from_floats(
                    symbol=hl_pos.asset,
                    direction=hl_pos.side.value.lower(),
                    size=abs(hl_pos.size),
                    entry_price=hl_pos.avg_fill_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_r=unrealized_pnl_r,
                    stop_loss=mgmt_state.current_stop_loss if mgmt_state else 0.0,
                    take_profit_1=mgmt_state.tp1_price if mgmt_state else None,
                    take_profit_2=mgmt_state.tp2_price if mgmt_state else None,
                    trade_id=hl_pos.id
                )
                
                positions.append(position_data)
            
            logger.info(f"Retrieved {len(positions)} current positions")
            return positions
            
        except Exception as e:
            logger.error("Failed to get current positions", error=str(e))
            return []
    
    async def get_position_statistics(
        self, 
        position_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed statistics for a specific position."""
        await self.initialize()
        
        try:
            # TODO: Add user_id verification when position-user mapping is implemented
            return await self.position_manager.get_position_statistics(position_id)
        except Exception as e:
            logger.error("Failed to get position statistics", position_id=position_id, error=str(e))
            return None
    
    async def close_position(
        self, 
        position_id: str, 
        user_id: str,
        reason: str = "manual"
    ) -> bool:
        """Close a position manually."""
        await self.initialize()
        
        try:
            # TODO: Add user_id verification when position-user mapping is implemented
            exit_reason = ExitReason.MANUAL
            if reason == "stop_loss":
                exit_reason = ExitReason.STOP_LOSS
            elif reason == "take_profit":
                exit_reason = ExitReason.TP1  # Default to TP1 for manual TP
            
            success = await self.position_manager.close_position(position_id, exit_reason)
            logger.info("Position close requested", position_id=position_id, user_id=user_id, success=success)
            return success
            
        except Exception as e:
            logger.error("Failed to close position", position_id=position_id, error=str(e))
            return False
    
    async def start_managing_position(
        self, 
        position_id: str,
        user_id: str,
        stop_loss: Optional[str] = None,
        take_profit_1: Optional[str] = None,
        take_profit_2: Optional[str] = None
    ) -> bool:
        """Start managing an existing position."""
        await self.initialize()
        
        try:
            # Convert string values to Decimal for calculations
            initial_stop_loss = float(Decimal(stop_loss)) if stop_loss else 0.0
            tp1 = float(Decimal(take_profit_1)) if take_profit_1 else None
            tp2 = float(Decimal(take_profit_2)) if take_profit_2 else None
            # Get the position from Hyperliquid
            positions = await self.client.get_positions()
            target_position = None
            
            for pos in positions:
                if pos.id == position_id:
                    target_position = pos
                    break
            
            if not target_position:
                logger.error("Position not found", position_id=position_id)
                return False
            
            # Create a trade record for the position manager
            trade_record = TradeRecord(
                id=position_id,
                strategy_name="Manual",
                symbol=target_position.asset,
                side=target_position.side,
                entry_price=target_position.avg_fill_price,
                initial_stop_loss=initial_stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                quantity=abs(target_position.size),
                confidence=1.0,
                reasoning="Manually managed position",
                created_at=datetime.now(timezone.utc)
            )
            
            # Get current market price
            market_data = await self.client.get_market_data(target_position.asset)
            current_price = market_data.last if market_data else target_position.avg_fill_price
            
            # Start managing the position
            await self.position_manager.manage_position(
                target_position, 
                trade_record, 
                current_price
            )
            
            logger.info("Started managing position", position_id=position_id)
            return True
            
        except Exception as e:
            logger.error("Failed to start managing position", position_id=position_id, error=str(e))
            return False
    
    async def update_position_stops(
        self,
        position_id: str,
        user_id: str,
        stop_loss: Optional[str] = None,
        take_profit_1: Optional[str] = None,
        take_profit_2: Optional[str] = None
    ) -> bool:
        """Update stop loss and take profit levels."""
        await self.initialize()
        
        try:
            # Convert string values to float for internal use
            stop_loss_f = float(Decimal(stop_loss)) if stop_loss else None
            tp1_f = float(Decimal(take_profit_1)) if take_profit_1 else None
            tp2_f = float(Decimal(take_profit_2)) if take_profit_2 else None
            
            mgmt_state = self.position_manager.get_position_state(position_id)
            if not mgmt_state:
                logger.error("Position not under management", position_id=position_id)
                return False
            
            # Update stop loss
            if stop_loss_f is not None:
                # Cancel existing stop order
                if mgmt_state.stop_order_id:
                    await self.client.cancel_order(mgmt_state.stop_order_id)
                
                # Place new stop order
                from ...types import OrderType
                stop_order = await self.client.place_order(
                    asset=mgmt_state.asset,
                    size=mgmt_state.current_size,
                    side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                    order_type=OrderType.STOP_LOSS,
                    stop_price=stop_loss_f,
                    metadata={"position_id": position_id, "order_purpose": "updated_stop"}
                )
                
                mgmt_state.stop_order_id = stop_order.id
                mgmt_state.current_stop_loss = stop_loss_f
            
            # Update take profit levels
            if tp1_f is not None:
                mgmt_state.tp1_price = tp1_f
                
                # Update TP1 order if it hasn't been filled
                if not mgmt_state.tp1_filled and mgmt_state.tp1_order_id:
                    await self.client.cancel_order(mgmt_state.tp1_order_id)
                    
                    from ...types import OrderType
                    tp1_order = await self.client.place_order(
                        asset=mgmt_state.asset,
                        size=mgmt_state.tp1_size,
                        side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                        order_type=OrderType.LIMIT,
                        price=tp1_f,
                        metadata={"position_id": position_id, "order_purpose": "updated_tp1"}
                    )
                    mgmt_state.tp1_order_id = tp1_order.id
            
            if tp2_f is not None:
                mgmt_state.tp2_price = tp2_f
                
                # Update TP2 order if it hasn't been filled
                if not mgmt_state.tp2_filled and mgmt_state.tp2_order_id:
                    await self.client.cancel_order(mgmt_state.tp2_order_id)
                    
                    from ...types import OrderType
                    tp2_order = await self.client.place_order(
                        asset=mgmt_state.asset,
                        size=mgmt_state.tp2_size,
                        side=OrderSide.SELL if mgmt_state.side == OrderSide.LONG else OrderSide.BUY,
                        order_type=OrderType.LIMIT,
                        price=tp2_f,
                        metadata={"position_id": position_id, "order_purpose": "updated_tp2"}
                    )
                    mgmt_state.tp2_order_id = tp2_order.id
            
            logger.info("Position stops updated", position_id=position_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update position stops", position_id=position_id, error=str(e))
            return False
    
    def _on_position_update(self, position_id: str, mgmt_state: PositionManagementState):
        """Handle position update callback."""
        # This could be used to broadcast updates via WebSocket
        logger.info(
            "Position updated", 
            position_id=position_id,
            state=mgmt_state.state.value,
            current_size=mgmt_state.current_size
        )
    
    def _on_position_exit(self, position_id: str, reason: ExitReason, exit_price: float):
        """Handle position exit callback."""
        # This could be used to broadcast exit notifications
        logger.info(
            "Position exited",
            position_id=position_id,
            reason=reason.value,
            exit_price=exit_price
        )
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary statistics for a user."""
        await self.initialize()
        
        try:
            positions = await self.get_current_positions(user_id)
            
            total_pnl = sum(pos.unrealized_pnl for pos in positions)
            long_positions = [p for p in positions if p.direction == "long"]
            short_positions = [p for p in positions if p.direction == "short"]
            
            # Get account info from Hyperliquid
            account_info = await self.client.get_account_info()
            portfolio_value = account_info.get("total_equity", 0.0) if account_info else 0.0
            
            return {
                "portfolio_value": portfolio_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": (total_pnl / portfolio_value * 100) if portfolio_value > 0 else 0.0,
                "open_positions": len(positions),
                "long_positions": len(long_positions),
                "short_positions": len(short_positions),
                "positions_in_profit": len([p for p in positions if p.unrealized_pnl > 0]),
                "positions_in_loss": len([p for p in positions if p.unrealized_pnl < 0])
            }
            
        except Exception as e:
            logger.error("Failed to get portfolio summary", error=str(e))
            return {
                "portfolio_value": 0.0,
                "total_pnl": 0.0,
                "total_pnl_percent": 0.0,
                "open_positions": 0,
                "long_positions": 0,
                "short_positions": 0,
                "positions_in_profit": 0,
                "positions_in_loss": 0
            }


# Global service instance
position_service = PositionService()