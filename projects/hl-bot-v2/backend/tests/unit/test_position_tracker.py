"""Tests for position tracker."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from hl_bot.trading.position import (
    Position,
    PositionSide,
    PositionTracker,
    Fill,
    round_quantity,
    round_price,
    get_symbol_precision,
)


class TestPosition:
    """Test Position model."""

    def test_create_flat_position(self):
        """Test creating a flat position."""
        pos = Position(symbol="BTC-USD")
        assert pos.symbol == "BTC-USD"
        assert pos.side == PositionSide.FLAT
        assert pos.quantity == Decimal("0")
        assert pos.is_flat

    def test_update_price_long(self):
        """Test updating price for long position."""
        pos = Position(
            symbol="BTC-USD",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
            current_price=Decimal("50000"),
        )
        
        pos.update_price(Decimal("51000"))
        
        assert pos.current_price == Decimal("51000")
        assert pos.unrealized_pnl == Decimal("1000")

    def test_update_price_short(self):
        """Test updating price for short position."""
        pos = Position(
            symbol="BTC-USD",
            side=PositionSide.SHORT,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
            current_price=Decimal("50000"),
        )
        
        pos.update_price(Decimal("49000"))
        
        assert pos.current_price == Decimal("49000")
        assert pos.unrealized_pnl == Decimal("1000")

    def test_notional_value(self):
        """Test notional value calculation."""
        pos = Position(
            symbol="BTC-USD",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            current_price=Decimal("50000"),
        )
        
        assert pos.notional_value == Decimal("25000")

    def test_total_pnl(self):
        """Test total P&L calculation."""
        pos = Position(
            symbol="BTC-USD",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
            current_price=Decimal("51000"),
            realized_pnl=Decimal("500"),
        )
        
        pos.update_price(Decimal("51000"))
        
        # Unrealized: (51000 - 50000) * 1.0 = 1000
        # Total: 1000 + 500 = 1500
        assert pos.total_pnl == Decimal("1500")


class TestPositionTracker:
    """Test PositionTracker."""

    def test_get_position_creates_if_not_exists(self):
        """Test getting position creates new one if doesn't exist."""
        tracker = PositionTracker()
        
        pos = tracker.get_position("BTC-USD")
        
        assert pos.symbol == "BTC-USD"
        assert pos.is_flat

    def test_open_long_position(self):
        """Test opening a long position."""
        tracker = PositionTracker()
        
        fill = Fill(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
            order_id="order-1",
            fill_id="fill-1",
        )
        
        pos = tracker.update_from_fill(fill)
        
        assert pos.side == PositionSide.LONG
        assert pos.quantity == Decimal("1.0")
        assert pos.entry_price == Decimal("50000")

    def test_open_short_position(self):
        """Test opening a short position."""
        tracker = PositionTracker()
        
        fill = Fill(
            symbol="BTC-USD",
            side="sell",
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
            order_id="order-1",
            fill_id="fill-1",
        )
        
        pos = tracker.update_from_fill(fill)
        
        assert pos.side == PositionSide.SHORT
        assert pos.quantity == Decimal("1.0")
        assert pos.entry_price == Decimal("50000")

    def test_increase_long_position(self):
        """Test increasing a long position (weighted average entry)."""
        tracker = PositionTracker()
        
        # First buy at 50000
        fill1 = Fill(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
            order_id="order-1",
            fill_id="fill-1",
        )
        tracker.update_from_fill(fill1)
        
        # Second buy at 51000
        fill2 = Fill(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("1.0"),
            price=Decimal("51000"),
            order_id="order-2",
            fill_id="fill-2",
        )
        pos = tracker.update_from_fill(fill2)
        
        # Average entry: (50000 + 51000) / 2 = 50500
        assert pos.quantity == Decimal("2.0")
        assert pos.entry_price == Decimal("50500")

    def test_reduce_long_position(self):
        """Test reducing a long position (realizes P&L)."""
        tracker = PositionTracker()
        
        # Open long at 50000
        fill1 = Fill(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("2.0"),
            price=Decimal("50000"),
            order_id="order-1",
            fill_id="fill-1",
        )
        tracker.update_from_fill(fill1)
        
        # Sell 1 BTC at 51000
        fill2 = Fill(
            symbol="BTC-USD",
            side="sell",
            quantity=Decimal("1.0"),
            price=Decimal("51000"),
            order_id="order-2",
            fill_id="fill-2",
        )
        pos = tracker.update_from_fill(fill2)
        
        # Should have 1 BTC left
        assert pos.quantity == Decimal("1.0")
        # Realized P&L: (51000 - 50000) * 1 = 1000
        assert pos.realized_pnl == Decimal("1000")

    def test_close_position(self):
        """Test closing a position completely."""
        tracker = PositionTracker()
        
        # Open long
        fill1 = Fill(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
            order_id="order-1",
            fill_id="fill-1",
        )
        tracker.update_from_fill(fill1)
        
        # Close position
        fill2 = Fill(
            symbol="BTC-USD",
            side="sell",
            quantity=Decimal("1.0"),
            price=Decimal("51000"),
            order_id="order-2",
            fill_id="fill-2",
        )
        pos = tracker.update_from_fill(fill2)
        
        assert pos.is_flat
        assert pos.quantity == Decimal("0")
        assert pos.realized_pnl == Decimal("1000")

    def test_flip_position(self):
        """Test flipping from long to short."""
        tracker = PositionTracker()
        
        # Open long 1 BTC
        fill1 = Fill(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
            order_id="order-1",
            fill_id="fill-1",
        )
        tracker.update_from_fill(fill1)
        
        # Sell 2 BTC (closes long, opens short)
        fill2 = Fill(
            symbol="BTC-USD",
            side="sell",
            quantity=Decimal("2.0"),
            price=Decimal("51000"),
            order_id="order-2",
            fill_id="fill-2",
        )
        pos = tracker.update_from_fill(fill2)
        
        # Should be short 1 BTC at 51000
        assert pos.side == PositionSide.SHORT
        assert pos.quantity == Decimal("1.0")
        assert pos.entry_price == Decimal("51000")
        # Realized P&L from closing long: (51000 - 50000) * 1 = 1000
        assert pos.realized_pnl == Decimal("1000")

    def test_get_total_exposure(self):
        """Test calculating total exposure across positions."""
        tracker = PositionTracker()
        
        # Open BTC position
        tracker.update_from_fill(
            Fill(
                symbol="BTC-USD",
                side="buy",
                quantity=Decimal("1.0"),
                price=Decimal("50000"),
                order_id="order-1",
                fill_id="fill-1",
            )
        )
        
        # Open ETH position
        tracker.update_from_fill(
            Fill(
                symbol="ETH-USD",
                side="buy",
                quantity=Decimal("10.0"),
                price=Decimal("3000"),
                order_id="order-2",
                fill_id="fill-2",
            )
        )
        
        # Update prices
        tracker.update_prices({
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("3000"),
        })
        
        # Total exposure: 50000 + 30000 = 80000
        assert tracker.get_total_exposure() == Decimal("80000")

    def test_get_total_pnl(self):
        """Test calculating total P&L across positions."""
        tracker = PositionTracker()
        
        # Open and partially close BTC
        tracker.update_from_fill(
            Fill(
                symbol="BTC-USD",
                side="buy",
                quantity=Decimal("2.0"),
                price=Decimal("50000"),
                order_id="order-1",
                fill_id="fill-1",
            )
        )
        tracker.update_from_fill(
            Fill(
                symbol="BTC-USD",
                side="sell",
                quantity=Decimal("1.0"),
                price=Decimal("51000"),
                order_id="order-2",
                fill_id="fill-2",
            )
        )
        
        # Update price for unrealized P&L
        tracker.update_prices({"BTC-USD": Decimal("52000")})
        
        # Realized: (51000 - 50000) * 1 = 1000
        # Unrealized: (52000 - 50000) * 1 = 2000
        # Total: 3000
        assert tracker.get_total_pnl() == Decimal("3000")


class TestPrecisionRounding:
    """Test precision rounding functions."""

    def test_round_quantity(self):
        """Test quantity rounding to lot size."""
        quantity = Decimal("1.2345")
        step_size = Decimal("0.001")
        
        rounded = round_quantity(quantity, step_size)
        
        assert rounded == Decimal("1.234")

    def test_round_price(self):
        """Test price rounding to tick size."""
        price = Decimal("50123.456")
        tick_size = Decimal("0.1")
        
        rounded = round_price(price, tick_size)
        
        assert rounded == Decimal("50123.4")

    def test_get_symbol_precision(self):
        """Test getting symbol precision rules."""
        btc_precision = get_symbol_precision("BTC-USD")
        
        assert btc_precision["tick_size"] == Decimal("0.1")
        assert btc_precision["lot_size"] == Decimal("0.001")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
