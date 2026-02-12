"""Trading-related Pydantic models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderSide(StrEnum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(StrEnum):
    """Order status enumeration."""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# Example request/response models
class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""

    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9_-]+$")
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: float | None = Field(default=None, gt=0, description="Limit price (required for limit orders)")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC-USD",
                "side": "buy",
                "order_type": "limit",
                "quantity": 0.1,
                "price": 50000.0,
            }
        }


class OrderResponse(BaseModel):
    """Response model for order information."""

    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: float
    price: float | None
    filled_quantity: float = Field(default=0.0, ge=0)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
