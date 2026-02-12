"""Position tracking and management.

Single source of truth for all positions. Tracks from fills, not exchange polling.
Uses Decimal for all financial calculations to avoid floating point errors.
"""

from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from enum import StrEnum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class PositionSide(StrEnum):
    """Position side."""
    
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class Position(BaseModel):
    """Position model with P&L tracking."""
    
    symbol: str
    side: PositionSide = PositionSide.FLAT
    quantity: Decimal = Field(default=Decimal("0"))
    entry_price: Decimal = Field(default=Decimal("0"))
    current_price: Decimal = Field(default=Decimal("0"))
    unrealized_pnl: Decimal = Field(default=Decimal("0"))
    realized_pnl: Decimal = Field(default=Decimal("0"))
    leverage: Decimal = Field(default=Decimal("1"))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {"json_encoders": {Decimal: str}}
    
    def update_price(self, price: Decimal) -> None:
        """Update current price and recalculate unrealized P&L.
        
        Args:
            price: Current market price
        """
        self.current_price = price
        self.last_updated = datetime.now(timezone.utc)
        
        if self.quantity == 0:
            self.unrealized_pnl = Decimal("0")
            return
        
        # Calculate P&L based on position side
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (price - self.entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            self.unrealized_pnl = (self.entry_price - price) * self.quantity
        else:
            self.unrealized_pnl = Decimal("0")
    
    @property
    def notional_value(self) -> Decimal:
        """Get current notional value of position."""
        return abs(self.quantity * self.current_price)
    
    @property
    def total_pnl(self) -> Decimal:
        """Get total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def is_flat(self) -> bool:
        """Check if position is flat (no position)."""
        return self.quantity == 0 or self.side == PositionSide.FLAT


class Fill(BaseModel):
    """Trade fill model."""
    
    symbol: str
    side: str  # "buy" or "sell"
    quantity: Decimal
    price: Decimal
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    order_id: str
    fill_id: str
    fee: Decimal = Field(default=Decimal("0"))
    
    model_config = {"json_encoders": {Decimal: str}}


class PositionTracker:
    """Track all positions from order fills.
    
    Single source of truth for positions. Updates from fills, not from exchange.
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        """Initialize position tracker."""
        self._positions: Dict[str, Position] = {}
    
    def get_position(self, symbol: str) -> Position:
        """Get position for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position object (creates new if doesn't exist)
        """
        if symbol not in self._positions:
            self._positions[symbol] = Position(symbol=symbol)
        return self._positions[symbol]
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions.
        
        Returns:
            Dictionary of symbol -> Position
        """
        return self._positions.copy()
    
    def update_from_fill(self, fill: Fill) -> Position:
        """Update position from a trade fill.
        
        Args:
            fill: Fill object
            
        Returns:
            Updated position
        """
        pos = self.get_position(fill.symbol)
        
        # Convert buy/sell to quantity delta
        quantity_delta = fill.quantity if fill.side == "buy" else -fill.quantity
        
        # Handle different cases
        if pos.is_flat:
            # Opening new position
            pos.side = PositionSide.LONG if quantity_delta > 0 else PositionSide.SHORT
            pos.quantity = abs(quantity_delta)
            pos.entry_price = fill.price
            pos.realized_pnl -= fill.fee  # Subtract fees from realized P&L
        else:
            old_quantity = pos.quantity if pos.side == PositionSide.LONG else -pos.quantity
            new_quantity = old_quantity + quantity_delta
            
            if abs(new_quantity) > abs(old_quantity):
                # Increasing position - weighted average entry price
                total_cost = (pos.entry_price * pos.quantity) + (fill.price * fill.quantity)
                total_quantity = pos.quantity + fill.quantity
                pos.entry_price = total_cost / total_quantity if total_quantity > 0 else Decimal("0")
                pos.quantity = abs(new_quantity)
                pos.realized_pnl -= fill.fee
            else:
                # Reducing or flipping position - realize P&L on closed portion
                close_quantity = min(pos.quantity, fill.quantity)
                
                if pos.side == PositionSide.LONG:
                    pnl = (fill.price - pos.entry_price) * close_quantity
                else:
                    pnl = (pos.entry_price - fill.price) * close_quantity
                
                pos.realized_pnl += pnl - fill.fee
                
                if new_quantity == 0:
                    # Position closed
                    pos.side = PositionSide.FLAT
                    pos.quantity = Decimal("0")
                    pos.entry_price = Decimal("0")
                    pos.unrealized_pnl = Decimal("0")
                elif (old_quantity > 0 and new_quantity < 0) or (old_quantity < 0 and new_quantity > 0):
                    # Position flipped - open new position on the other side
                    pos.side = PositionSide.LONG if new_quantity > 0 else PositionSide.SHORT
                    pos.quantity = abs(new_quantity)
                    pos.entry_price = fill.price
                else:
                    # Position reduced
                    pos.quantity = abs(new_quantity)
        
        pos.current_price = fill.price
        pos.last_updated = fill.timestamp
        
        return pos
    
    def update_prices(self, prices: Dict[str, Decimal]) -> None:
        """Update prices for all positions.
        
        Args:
            prices: Dictionary of symbol -> current price
        """
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].update_price(price)
    
    def get_total_exposure(self) -> Decimal:
        """Get total absolute notional exposure across all positions.
        
        Returns:
            Total exposure in base currency
        """
        return sum(
            pos.notional_value
            for pos in self._positions.values()
            if not pos.is_flat
        )
    
    def get_total_pnl(self) -> Decimal:
        """Get total P&L across all positions.
        
        Returns:
            Total P&L (realized + unrealized)
        """
        return sum(pos.total_pnl for pos in self._positions.values())
    
    def get_realized_pnl(self) -> Decimal:
        """Get total realized P&L across all positions.
        
        Returns:
            Total realized P&L
        """
        return sum(pos.realized_pnl for pos in self._positions.values())
    
    def get_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L across all positions.
        
        Returns:
            Total unrealized P&L
        """
        return sum(pos.unrealized_pnl for pos in self._positions.values())
    
    def reset_position(self, symbol: str) -> None:
        """Reset position for a symbol (for testing/simulation).
        
        Args:
            symbol: Symbol to reset
        """
        if symbol in self._positions:
            del self._positions[symbol]
    
    def reset_all(self) -> None:
        """Reset all positions (for testing/simulation)."""
        self._positions.clear()


def round_quantity(quantity: Decimal, step_size: Decimal) -> Decimal:
    """Round quantity to exchange's lot size.
    
    Args:
        quantity: Quantity to round
        step_size: Exchange lot size (e.g., 0.001 for BTC)
        
    Returns:
        Rounded quantity
    """
    if step_size == 0:
        return quantity
    return (quantity / step_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * step_size


def round_price(price: Decimal, tick_size: Decimal) -> Decimal:
    """Round price to exchange's tick size.
    
    Args:
        price: Price to round
        tick_size: Exchange tick size (e.g., 0.1 for BTC-USD)
        
    Returns:
        Rounded price
    """
    if tick_size == 0:
        return price
    return (price / tick_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick_size


# Exchange-specific precision rules
SYMBOL_PRECISION = {
    "BTC-USD": {"tick_size": Decimal("0.1"), "lot_size": Decimal("0.001")},
    "ETH-USD": {"tick_size": Decimal("0.01"), "lot_size": Decimal("0.01")},
    "SOL-USD": {"tick_size": Decimal("0.001"), "lot_size": Decimal("0.1")},
}


def get_symbol_precision(symbol: str) -> Dict[str, Decimal]:
    """Get precision rules for a symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Dictionary with tick_size and lot_size
    """
    return SYMBOL_PRECISION.get(
        symbol,
        {"tick_size": Decimal("0.01"), "lot_size": Decimal("0.01")}  # Default
    )
