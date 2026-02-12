"""Trade management service for API integration."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
import structlog

logger = structlog.get_logger()


# In-memory trade storage (replace with database in production)
_trades_db: Dict[str, Dict[str, Any]] = {}


class TradeService:
    """Service layer for trade management API integration."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self):
        """Initialize the trade service."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("Trade service initialized")
    
    async def list_trades(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List trades for a user with optional filtering.
        
        Args:
            user_id: User ID to filter by (users can only see their own trades)
            status: Filter by status (pending, active, closed)
            symbol: Filter by trading symbol
            strategy_id: Filter by strategy
            limit: Maximum results
            offset: Skip N results
            
        Returns:
            List of trade records
        """
        await self.initialize()
        
        # Filter trades by user and criteria
        trades = [
            trade for trade in _trades_db.values()
            if trade.get('user_id') == user_id
        ]
        
        if status:
            trades = [t for t in trades if t.get('status') == status]
        
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol.upper()]
        
        if strategy_id:
            trades = [t for t in trades if t.get('strategy_id') == strategy_id]
        
        # Sort by created_at descending
        trades.sort(key=lambda t: t.get('created_at', ''), reverse=True)
        
        # Apply pagination
        return trades[offset:offset + limit]
    
    async def get_trade(
        self,
        trade_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific trade by ID.
        
        Args:
            trade_id: Trade ID
            user_id: User ID (for ownership check)
            
        Returns:
            Trade record or None
        """
        await self.initialize()
        
        trade = _trades_db.get(trade_id)
        
        # Check ownership
        if trade and trade.get('user_id') != user_id:
            logger.warning(
                "Unauthorized trade access attempt",
                trade_id=trade_id,
                user_id=user_id
            )
            return None
        
        return trade
    
    async def create_trade(
        self,
        trade_id: str,
        user_id: str,
        symbol: str,
        direction: str,
        quantity: str,
        entry_price: Optional[str] = None,
        stop_loss: Optional[str] = None,
        take_profit_1: Optional[str] = None,
        take_profit_2: Optional[str] = None,
        reasoning: Optional[str] = None,
        strategy_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        confluence_score: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new trade record.
        
        All numeric values are stored as strings for precision.
        """
        await self.initialize()
        
        now = datetime.now(timezone.utc).isoformat()
        
        trade = {
            'id': trade_id,
            'user_id': user_id,
            'strategy_id': strategy_id or 'manual',
            'strategy_name': strategy_name or 'Manual Trade',
            'symbol': symbol.upper(),
            'direction': direction.lower(),
            'entry_price': entry_price or '0',
            'entry_time': now,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'quantity': quantity,
            'pnl': '0',
            'pnl_r': '0',
            'status': 'pending',
            'reasoning': reasoning or '',
            'confluence_score': confluence_score or '0',
            'stop_loss': stop_loss or '0',
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'created_at': now,
            'updated_at': now
        }
        
        _trades_db[trade_id] = trade
        
        logger.info(
            "Trade created",
            trade_id=trade_id,
            user_id=user_id,
            symbol=symbol
        )
        
        return trade
    
    async def update_trade(
        self,
        trade_id: str,
        user_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update a trade record.
        
        Only allows updating specific fields.
        """
        await self.initialize()
        
        trade = _trades_db.get(trade_id)
        
        if not trade:
            return None
        
        # Check ownership
        if trade.get('user_id') != user_id:
            logger.warning(
                "Unauthorized trade update attempt",
                trade_id=trade_id,
                user_id=user_id
            )
            return None
        
        # Allowed update fields
        allowed_fields = {
            'status', 'exit_price', 'exit_time', 'exit_reason',
            'pnl', 'pnl_r', 'stop_loss', 'take_profit_1', 'take_profit_2'
        }
        
        for key, value in updates.items():
            if key in allowed_fields:
                trade[key] = value
        
        trade['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info("Trade updated", trade_id=trade_id)
        
        return trade
    
    async def close_trade(
        self,
        trade_id: str,
        user_id: str,
        exit_price: str,
        exit_reason: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """Close a trade."""
        await self.initialize()
        
        trade = _trades_db.get(trade_id)
        
        if not trade:
            return None
        
        if trade.get('user_id') != user_id:
            return None
        
        if trade.get('status') == 'closed':
            return trade
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Calculate P&L using Decimal for precision
        entry_price = Decimal(trade.get('entry_price', '0'))
        exit_price_d = Decimal(exit_price)
        quantity = Decimal(trade.get('quantity', '0'))
        direction = trade.get('direction', 'long')
        
        if direction == 'long':
            pnl = (exit_price_d - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price_d) * quantity
        
        # Calculate R multiple
        stop_loss = Decimal(trade.get('stop_loss', '0'))
        if stop_loss > 0 and entry_price > 0:
            risk = abs(entry_price - stop_loss) * quantity
            pnl_r = pnl / risk if risk > 0 else Decimal('0')
        else:
            pnl_r = Decimal('0')
        
        trade['status'] = 'closed'
        trade['exit_price'] = exit_price
        trade['exit_time'] = now
        trade['exit_reason'] = exit_reason
        trade['pnl'] = str(pnl)
        trade['pnl_r'] = str(pnl_r)
        trade['updated_at'] = now
        
        logger.info(
            "Trade closed",
            trade_id=trade_id,
            pnl=str(pnl),
            exit_reason=exit_reason
        )
        
        return trade
    
    async def get_trading_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get trading statistics for a user.
        
        All values returned as strings for precision.
        """
        await self.initialize()
        
        # Get user's closed trades
        trades = [
            t for t in _trades_db.values()
            if t.get('user_id') == user_id and t.get('status') == 'closed'
        ]
        
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': '0.0',
                'profit_factor': '0.0',
                'total_pnl': '0.0',
                'total_pnl_r': '0.0',
                'max_drawdown': '0.0',
                'max_consecutive_losses': 0,
                'current_streak': 0,
                'avg_win_r': '0.0',
                'avg_loss_r': '0.0'
            }
        
        # Calculate statistics using Decimal
        total_trades = len(trades)
        winning_trades = [t for t in trades if Decimal(t.get('pnl', '0')) > 0]
        losing_trades = [t for t in trades if Decimal(t.get('pnl', '0')) < 0]
        
        total_pnl = sum(Decimal(t.get('pnl', '0')) for t in trades)
        total_pnl_r = sum(Decimal(t.get('pnl_r', '0')) for t in trades)
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else Decimal('0')
        
        gross_profit = sum(Decimal(t.get('pnl', '0')) for t in winning_trades)
        gross_loss = abs(sum(Decimal(t.get('pnl', '0')) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal('0')
        
        avg_win_r = (
            sum(Decimal(t.get('pnl_r', '0')) for t in winning_trades) / len(winning_trades)
            if winning_trades else Decimal('0')
        )
        avg_loss_r = (
            sum(Decimal(t.get('pnl_r', '0')) for t in losing_trades) / len(losing_trades)
            if losing_trades else Decimal('0')
        )
        
        # Calculate drawdown and streaks
        # Sort trades by exit time
        trades.sort(key=lambda t: t.get('exit_time', ''))
        
        max_consecutive_losses = 0
        current_losses = 0
        
        for t in trades:
            if Decimal(t.get('pnl', '0')) < 0:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0
        
        # Current streak
        current_streak = 0
        for t in reversed(trades):
            pnl = Decimal(t.get('pnl', '0'))
            if current_streak == 0:
                current_streak = 1 if pnl > 0 else -1
            elif (pnl > 0 and current_streak > 0) or (pnl < 0 and current_streak < 0):
                current_streak += 1 if current_streak > 0 else -1
            else:
                break
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': str(win_rate),
            'profit_factor': str(profit_factor),
            'total_pnl': str(total_pnl),
            'total_pnl_r': str(total_pnl_r),
            'max_drawdown': '0.0',  # TODO: Calculate actual drawdown
            'max_consecutive_losses': max_consecutive_losses,
            'current_streak': current_streak,
            'avg_win_r': str(avg_win_r),
            'avg_loss_r': str(avg_loss_r)
        }


# Global service instance
trade_service = TradeService()
