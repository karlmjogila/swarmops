"""Trading and trade history endpoints."""

from typing import Dict, Any, List, Optional, Annotated
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import structlog

from ..security import get_current_active_user, require_role
from ..security.auth import UserInDB, UserRole
from ..security.rate_limiter import rate_limit, RateLimitTier

router = APIRouter()
logger = structlog.get_logger()


class ManualTradeRequest(BaseModel):
    """Request model for creating a manual trade with validation."""
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol (e.g., 'ETH-USD')")
    direction: str = Field(..., description="Trade direction ('long' or 'short')")
    quantity: str = Field(..., description="Trade quantity as string (for precision)")
    entry_price: Optional[str] = Field(None, description="Entry price as string (optional, uses market price if not provided)")
    stop_loss: Optional[str] = Field(None, description="Stop loss price as string")
    take_profit_1: Optional[str] = Field(None, description="First take profit level as string")
    take_profit_2: Optional[str] = Field(None, description="Second take profit level as string")
    reasoning: Optional[str] = Field(None, max_length=1000, description="Trade reasoning")
    
    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        v = v.lower()
        if v not in ('long', 'short'):
            raise ValueError("direction must be 'long' or 'short'")
        return v
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        # Basic symbol validation - alphanumeric with optional dash
        v = v.upper().strip()
        if not all(c.isalnum() or c == '-' for c in v):
            raise ValueError("symbol must contain only alphanumeric characters and dashes")
        return v
    
    @field_validator('quantity', 'entry_price', 'stop_loss', 'take_profit_1', 'take_profit_2')
    @classmethod
    def validate_decimal_string(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            d = Decimal(v)
            if d <= 0:
                raise ValueError("Value must be positive")
            return str(d)
        except:
            raise ValueError("Must be a valid decimal number")
    
    def get_quantity(self) -> Decimal:
        """Get quantity as Decimal."""
        return Decimal(self.quantity)
    
    def get_entry_price(self) -> Optional[Decimal]:
        """Get entry price as Decimal."""
        return Decimal(self.entry_price) if self.entry_price else None
    
    def get_stop_loss(self) -> Optional[Decimal]:
        """Get stop loss as Decimal."""
        return Decimal(self.stop_loss) if self.stop_loss else None


class Trade(BaseModel):
    """Trade record model."""
    id: str
    strategy_id: str
    strategy_name: str
    symbol: str
    direction: str  # long, short
    entry_price: str  # Use string for precision
    entry_time: str
    exit_price: Optional[str] = None
    exit_time: Optional[str] = None
    exit_reason: Optional[str] = None
    quantity: str
    pnl: str
    pnl_r: str  # P&L in R multiples
    status: str  # pending, active, closed
    reasoning: str
    confluence_score: str
    stop_loss: str
    take_profit_1: Optional[str] = None
    take_profit_2: Optional[str] = None
    created_at: str


class Position(BaseModel):
    """Current position model - all financial values as strings for precision."""
    symbol: str
    direction: str
    size: str = "0"  # Use string for precision
    entry_price: str = "0"
    current_price: str = "0"
    unrealized_pnl: str = "0"
    unrealized_pnl_r: str = "0"
    stop_loss: str = "0"
    take_profit_1: Optional[str] = None
    take_profit_2: Optional[str] = None
    trade_id: str
    
    @classmethod
    def from_floats(
        cls,
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        current_price: float,
        unrealized_pnl: float,
        unrealized_pnl_r: float,
        stop_loss: float,
        take_profit_1: Optional[float],
        take_profit_2: Optional[float],
        trade_id: str
    ) -> "Position":
        """Create Position from float values, converting to strings."""
        return cls(
            symbol=symbol,
            direction=direction,
            size=str(Decimal(str(size))),
            entry_price=str(Decimal(str(entry_price))),
            current_price=str(Decimal(str(current_price))),
            unrealized_pnl=str(Decimal(str(unrealized_pnl))),
            unrealized_pnl_r=str(Decimal(str(unrealized_pnl_r))),
            stop_loss=str(Decimal(str(stop_loss))),
            take_profit_1=str(Decimal(str(take_profit_1))) if take_profit_1 else None,
            take_profit_2=str(Decimal(str(take_profit_2))) if take_profit_2 else None,
            trade_id=trade_id
        )


class TradingStats(BaseModel):
    """Overall trading statistics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: str  # Use string for precision
    profit_factor: str
    total_pnl: str
    total_pnl_r: str
    max_drawdown: str
    max_consecutive_losses: int
    current_streak: int
    avg_win_r: str
    avg_loss_r: str


@router.get("/", summary="List all trades")
async def list_trades(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    status: Optional[str] = Query(None, description="Filter by status (pending, active, closed)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    strategy_id: Optional[str] = Query(None, description="Filter by strategy"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of trades to return"),
    offset: int = Query(0, ge=0, description="Number of trades to skip"),
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> Dict[str, Any]:
    """
    List trades with optional filtering.
    
    Requires authentication. Users can only see their own trades.
    """
    from ..services import trade_service
    
    # Validate status if provided
    if status and status not in ('pending', 'active', 'closed'):
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be 'pending', 'active', or 'closed'"
        )
    
    logger.info(
        "Trade list requested",
        user=current_user.username,
        status=status,
        symbol=symbol,
        strategy_id=strategy_id,
        limit=limit,
        offset=offset
    )
    
    try:
        trades = await trade_service.list_trades(
            user_id=current_user.id,
            status=status,
            symbol=symbol,
            strategy_id=strategy_id,
            limit=limit,
            offset=offset
        )
        return {
            "trades": trades,
            "total": len(trades),
            "limit": limit,
            "offset": offset,
            "has_more": len(trades) == limit
        }
    except NotImplementedError:
        logger.warning("Trade listing service not yet implemented")
        return {
            "trades": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "has_more": False,
            "_warning": "Trade listing service not yet implemented"
        }
    except Exception as e:
        logger.error(f"Failed to list trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trades")


@router.get("/{trade_id}", summary="Get trade details")
async def get_trade(
    trade_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> Dict[str, Any]:
    """Get detailed information about a specific trade."""
    from ..services import trade_service
    
    # Validate trade_id format
    if not trade_id or len(trade_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid trade_id format")
    
    logger.info("Trade details requested", trade_id=trade_id, user=current_user.username)
    
    try:
        trade = await trade_service.get_trade(trade_id, user_id=current_user.id)
        if trade is None:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        return trade
    except HTTPException:
        raise
    except NotImplementedError:
        logger.warning("Trade retrieval service not yet implemented")
        raise HTTPException(
            status_code=501,
            detail="Trade retrieval service not yet implemented"
        )
    except Exception as e:
        logger.error(f"Failed to get trade {trade_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trade")


@router.get("/positions/current", summary="Get current positions")
async def get_current_positions(
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> List[Position]:
    """Get all current open positions. Requires trader role."""
    from ..services import position_service
    
    logger.info("Current positions requested", user=current_user.username)
    
    try:
        positions = await position_service.get_current_positions(user_id=current_user.id)
        logger.info(f"Retrieved {len(positions)} positions", user=current_user.username)
        return positions
    except Exception as e:
        logger.error(f"Failed to get current positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve positions")


@router.get("/stats/overall", summary="Get overall trading statistics")
async def get_trading_stats(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> Dict[str, Any]:
    """Get comprehensive trading performance statistics."""
    from ..services import trade_service
    
    logger.info("Trading statistics requested", user=current_user.username)
    
    try:
        stats = await trade_service.get_trading_stats(user_id=current_user.id)
        return {
            "statistics": stats,
            "_warning": None if stats.get("total_trades", 0) > 0 else "No trades recorded yet"
        }
    except NotImplementedError:
        logger.warning("Trading statistics service not yet implemented")
        return {
            "statistics": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": "0.0",
                "profit_factor": "0.0",
                "total_pnl": "0.0",
                "total_pnl_r": "0.0",
                "max_drawdown": "0.0",
                "max_consecutive_losses": 0,
                "current_streak": 0,
                "avg_win_r": "0.0",
                "avg_loss_r": "0.0"
            },
            "_warning": "Statistics service not yet implemented - showing default values"
        }
    except Exception as e:
        logger.error(f"Failed to get trading statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trading statistics")


@router.get("/stats/by-strategy", summary="Get statistics by strategy")
async def get_stats_by_strategy(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> List[Dict[str, Any]]:
    """Get performance statistics broken down by strategy."""
    
    logger.info("Strategy-wise statistics requested", user=current_user.username)
    
    # TODO: Implement strategy-wise statistics
    return []


@router.post("/manual", summary="Create manual trade")
async def create_manual_trade(
    trade_data: ManualTradeRequest,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    _: None = Depends(rate_limit(RateLimitTier.TRADING))
) -> Dict[str, Any]:
    """
    Create a manual trade entry (for testing or manual intervention).
    
    Requires trader role. This bypasses the normal signal generation process.
    
    IMPORTANT: Uses Decimal arithmetic for all financial calculations.
    """
    from ..services import position_service
    from ..security.key_vault import get_key_vault
    
    # Check if user has a registered wallet
    key_vault = get_key_vault()
    if not key_vault.has_key(current_user.id):
        raise HTTPException(
            status_code=400,
            detail="No wallet registered. Register a wallet first via /api/auth/wallet/register"
        )
    
    logger.info(
        "Manual trade creation requested",
        user=current_user.username,
        symbol=trade_data.symbol,
        direction=trade_data.direction,
        quantity=trade_data.quantity
    )
    
    try:
        # Validate stop loss and take profit levels make sense
        entry_price = trade_data.get_entry_price()
        stop_loss = trade_data.get_stop_loss()
        
        if entry_price and stop_loss:
            if trade_data.direction == "long" and stop_loss >= entry_price:
                raise HTTPException(
                    status_code=400,
                    detail="Stop loss must be below entry price for long positions"
                )
            if trade_data.direction == "short" and stop_loss <= entry_price:
                raise HTTPException(
                    status_code=400,
                    detail="Stop loss must be above entry price for short positions"
                )
        
        trade_id = await position_service.create_manual_trade(
            user_id=current_user.id,
            symbol=trade_data.symbol,
            direction=trade_data.direction,
            quantity=trade_data.quantity,
            entry_price=trade_data.entry_price,
            stop_loss=trade_data.stop_loss,
            take_profit_1=trade_data.take_profit_1,
            take_profit_2=trade_data.take_profit_2,
            reasoning=trade_data.reasoning
        )
        
        return {
            "message": "Manual trade created successfully",
            "trade_id": trade_id,
            "symbol": trade_data.symbol,
            "direction": trade_data.direction,
            "quantity": trade_data.quantity
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create manual trade: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create manual trade: {str(e)}")


@router.put("/{trade_id}/close", summary="Close trade manually")
async def close_trade_manually(
    trade_id: str,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    reason: str = "manual",
    _: None = Depends(rate_limit(RateLimitTier.TRADING))
) -> Dict[str, Any]:
    """Close an active trade manually. Requires trader role."""
    from ..services import position_service
    
    logger.info(
        "Manual trade closure requested",
        trade_id=trade_id,
        reason=reason,
        user=current_user.username
    )
    
    try:
        success = await position_service.close_position(
            trade_id,
            user_id=current_user.id,
            reason=reason
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Position not found")
        
        return {
            "message": "Trade closed manually",
            "trade_id": trade_id,
            "exit_reason": reason
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close trade: {e}")
        raise HTTPException(status_code=500, detail="Failed to close trade")


@router.put("/{trade_id}/update-stops", summary="Update stop loss and take profit")
async def update_trade_stops(
    trade_id: str,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    stop_loss: Optional[str] = None,
    take_profit_1: Optional[str] = None,
    take_profit_2: Optional[str] = None,
    _: None = Depends(rate_limit(RateLimitTier.TRADING))
) -> Dict[str, Any]:
    """Update stop loss and take profit levels for an active trade."""
    from ..services import position_service
    
    # Validate decimal values
    for name, value in [("stop_loss", stop_loss), ("take_profit_1", take_profit_1), ("take_profit_2", take_profit_2)]:
        if value is not None:
            try:
                d = Decimal(value)
                if d <= 0:
                    raise HTTPException(status_code=400, detail=f"{name} must be positive")
            except:
                raise HTTPException(status_code=400, detail=f"{name} must be a valid decimal number")
    
    logger.info(
        "Trade stops update requested",
        trade_id=trade_id,
        stop_loss=stop_loss,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        user=current_user.username
    )
    
    try:
        success = await position_service.update_position_stops(
            trade_id,
            user_id=current_user.id,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Position not found or not managed")
        
        return {
            "message": "Trade stops updated",
            "trade_id": trade_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update trade stops: {e}")
        raise HTTPException(status_code=500, detail="Failed to update trade stops")


@router.get("/positions/{position_id}/stats", summary="Get position statistics")
async def get_position_stats(
    position_id: str,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> Dict[str, Any]:
    """Get detailed statistics for a specific position."""
    from ..services import position_service
    
    logger.info(
        "Position statistics requested",
        position_id=position_id,
        user=current_user.username
    )
    
    try:
        stats = await position_service.get_position_statistics(
            position_id,
            user_id=current_user.id
        )
        
        if not stats:
            raise HTTPException(status_code=404, detail="Position not found or not managed")
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get position statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve position statistics")


@router.post("/positions/{position_id}/manage", summary="Start managing a position")
async def start_managing_position(
    position_id: str,
    management_config: Dict[str, Any],
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    _: None = Depends(rate_limit(RateLimitTier.TRADING))
) -> Dict[str, Any]:
    """Start managing an existing position with risk management."""
    from ..services import position_service
    
    logger.info(
        "Position management start requested",
        position_id=position_id,
        config=management_config,
        user=current_user.username
    )
    
    try:
        success = await position_service.start_managing_position(
            position_id,
            user_id=current_user.id,
            stop_loss=management_config.get("stop_loss"),
            take_profit_1=management_config.get("take_profit_1"),
            take_profit_2=management_config.get("take_profit_2")
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start managing position")
        
        return {
            "message": "Position management started",
            "position_id": position_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start managing position: {e}")
        raise HTTPException(status_code=500, detail="Failed to start position management")


@router.get("/portfolio/summary", summary="Get portfolio summary")
async def get_portfolio_summary(
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> Dict[str, Any]:
    """Get overall portfolio summary and statistics."""
    from ..services import position_service
    
    logger.info("Portfolio summary requested", user=current_user.username)
    
    try:
        summary = await position_service.get_portfolio_summary(user_id=current_user.id)
        return summary
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio summary")
