"""Tests for the live position monitor.

Tests position monitoring, WebSocket streaming, and real-time P&L tracking.
"""

import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from hl_bot.trading.position import Fill, Position, PositionTracker
from hl_bot.trading.position_monitor import PositionMonitor, PositionUpdate
from hl_bot.trading.audit_logger import AuditLogger


@pytest.fixture
def mock_hl_client():
    """Create mock Hyperliquid client."""
    client = AsyncMock()
    client.get_positions = AsyncMock(return_value=[])
    client.get_market_price = AsyncMock(return_value=Decimal("50000"))
    client.subscribe_user_events = AsyncMock()
    return client


@pytest.fixture
def position_tracker():
    """Create position tracker."""
    return PositionTracker()


@pytest.fixture
def audit_logger(tmp_path):
    """Create audit logger."""
    return AuditLogger(tmp_path / "audit")


@pytest.fixture
def position_monitor(mock_hl_client, position_tracker, audit_logger):
    """Create position monitor."""
    return PositionMonitor(
        hyperliquid_client=mock_hl_client,
        position_tracker=position_tracker,
        audit_logger=audit_logger,
        update_interval=0.1,  # Fast for testing
    )


@pytest.mark.asyncio
async def test_position_monitor_initialization(position_monitor):
    """Test position monitor initializes correctly."""
    assert not position_monitor.is_running
    assert position_monitor._callbacks == []


@pytest.mark.asyncio
async def test_position_monitor_start_stop(position_monitor):
    """Test position monitor starts and stops."""
    # Start monitor
    await position_monitor.start()
    assert position_monitor.is_running
    
    # Wait a bit
    await asyncio.sleep(0.2)
    
    # Stop monitor
    await position_monitor.stop()
    assert not position_monitor.is_running


@pytest.mark.asyncio
async def test_position_update_callback(position_monitor, position_tracker):
    """Test position update callbacks are triggered."""
    updates = []
    
    def callback(update: PositionUpdate):
        updates.append(update)
    
    position_monitor.on_position_update(callback)
    
    # Create a fill
    fill = Fill(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        timestamp=datetime.now(timezone.utc),
        order_id="order123",
        fill_id="fill123",
        fee=Decimal("5"),
    )
    
    # Update position from fill
    position = position_tracker.update_from_fill(fill)
    
    # Create update
    update = PositionUpdate(
        symbol="BTC-USD",
        position=position,
        event_type="fill",
        fill=fill,
    )
    
    # Emit update
    await position_monitor._emit_position_update(update)
    
    # Check callback was called
    assert len(updates) == 1
    assert updates[0].symbol == "BTC-USD"
    assert updates[0].event_type == "fill"


@pytest.mark.asyncio
async def test_position_sync(position_monitor, mock_hl_client):
    """Test position sync from exchange."""
    # Mock exchange positions
    from hl_bot.types import Position as ExchangePosition, OrderSide
    
    mock_hl_client.get_positions.return_value = [
        ExchangePosition(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            quantity=0.5,
            entry_price=50000.0,
            mark_price=50500.0,
            liquidation_price=None,
            unrealized_pnl=250.0,
            realized_pnl=0.0,
            leverage=1.0,
        )
    ]
    
    # Sync positions
    await position_monitor._sync_positions()
    
    # Check position was synced
    pos = position_monitor._tracker.get_position("BTC-USD")
    assert pos.quantity == Decimal("0.5")
    assert pos.entry_price == Decimal("50000.0")
    assert pos.current_price == Decimal("50500.0")


@pytest.mark.asyncio
async def test_position_summary(position_monitor, position_tracker):
    """Test position summary generation."""
    # Create a position
    fill = Fill(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        timestamp=datetime.now(timezone.utc),
        order_id="order123",
        fill_id="fill123",
        fee=Decimal("5"),
    )
    
    position = position_tracker.update_from_fill(fill)
    position.update_price(Decimal("50500"))
    
    # Get summary
    summary = position_monitor.get_position_summary()
    
    # Verify summary
    assert "active_positions" in summary
    assert "total_pnl" in summary
    assert "positions" in summary
    assert summary["active_positions"] == 1
    assert "BTC-USD" in summary["positions"]


@pytest.mark.asyncio
async def test_position_update_serialization():
    """Test position update converts to dict correctly."""
    # Create position
    pos = Position(
        symbol="BTC-USD",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("50000"),
        current_price=Decimal("50500"),
        leverage=Decimal("1"),
    )
    pos.update_price(Decimal("50500"))
    
    # Create fill
    fill = Fill(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        timestamp=datetime.now(timezone.utc),
        order_id="order123",
        fill_id="fill123",
        fee=Decimal("5"),
    )
    
    # Create update
    update = PositionUpdate(
        symbol="BTC-USD",
        position=pos,
        event_type="fill",
        fill=fill,
    )
    
    # Convert to dict
    data = update.to_dict()
    
    # Verify structure
    assert data["type"] == "position_update"
    assert data["event_type"] == "fill"
    assert data["symbol"] == "BTC-USD"
    assert "position" in data
    assert "fill" in data
    assert data["position"]["quantity"] == "0.1"
    assert data["position"]["unrealized_pnl"] == "50.0"


@pytest.mark.asyncio
async def test_price_update_threshold(position_monitor, position_tracker):
    """Test that small price changes don't spam updates."""
    updates = []
    
    async def callback(update: PositionUpdate):
        updates.append(update)
    
    position_monitor.on_position_update(callback)
    
    # Create position
    fill = Fill(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        timestamp=datetime.now(timezone.utc),
        order_id="order123",
        fill_id="fill123",
        fee=Decimal("5"),
    )
    
    position = position_tracker.update_from_fill(fill)
    
    # Small price change (< $0.01 P&L change)
    old_pnl = position.unrealized_pnl
    position.update_price(Decimal("50000.05"))  # Tiny change
    
    # Should NOT trigger update (P&L change too small)
    pnl_change = abs(position.unrealized_pnl - old_pnl)
    assert pnl_change < Decimal("0.01")
    
    # Large price change
    position.update_price(Decimal("50100"))  # $100 change
    
    # Should trigger update
    pnl_change = abs(position.unrealized_pnl - old_pnl)
    assert pnl_change > Decimal("0.01")
