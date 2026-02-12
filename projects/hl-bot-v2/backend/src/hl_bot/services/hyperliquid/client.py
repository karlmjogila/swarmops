"""Hyperliquid exchange client with safety-first design.

Every order is validated. Every error is logged. Every price uses Decimal.
This client assumes the exchange, network, and your code will fail — plan accordingly.
"""

import asyncio
import hashlib
import hmac
import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any, Final

import httpx
from pydantic import BaseModel

from hl_bot.types import Order, OrderRequest, OrderSide, OrderType, Position

from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class HyperliquidConfig(BaseModel):
    """Hyperliquid client configuration."""

    base_url: str = "https://api.hyperliquid.xyz"
    ws_url: str = "wss://api.hyperliquid.xyz/ws"
    api_key: str
    api_secret: str
    rate_limit_per_min: int = 100
    rate_limit_headroom: float = 0.3  # 30% safety margin
    request_timeout: float = 10.0
    max_retries: int = 3


class SymbolInfo(BaseModel):
    """Trading pair precision and limits."""

    symbol: str
    tick_size: Decimal
    lot_size: Decimal
    min_order_size: Decimal
    max_order_size: Decimal


class HyperliquidClient:
    """Exchange client with retries, rate limiting, and error handling."""

    def __init__(self, config: HyperliquidConfig) -> None:
        """Initialize Hyperliquid client.

        Args:
            config: Client configuration including API credentials
        """
        self._config = config
        self._rate_limiter = RateLimiter(
            max_requests=config.rate_limit_per_min,
            window_seconds=60.0,
            headroom_percent=config.rate_limit_headroom,
        )
        # Symbol info cache: symbol -> SymbolInfo
        self._symbol_info: dict[str, SymbolInfo] = {}
        logger.info(
            "HyperliquidClient initialized",
            extra={
                "rate_limit": self._rate_limiter.capacity,
                "timeout": config.request_timeout,
            },
        )

    async def _sign_request(
        self, method: str, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """Generate authentication headers for request.

        Args:
            method: HTTP method
            path: Request path
            data: Request body

        Returns:
            Headers dict with authentication signature
        """
        timestamp = str(int(time.time() * 1000))
        body = "" if data is None else str(data)

        # HMAC-SHA256 signature
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self._config.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-API-KEY": self._config.api_key,
            "X-TIMESTAMP": timestamp,
            "X-SIGNATURE": signature,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retries and rate limiting.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API endpoint path
            data: Request body for POST/PUT
            max_retries: Override default retry count

        Returns:
            Response JSON

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
            httpx.TimeoutException: On timeout after retries
        """
        retries = max_retries if max_retries is not None else self._config.max_retries
        await self._rate_limiter.acquire()

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._config.request_timeout
                ) as client:
                    headers = await self._sign_request(method, path, data)
                    url = f"{self._config.base_url}{path}"

                    response = await client.request(
                        method,
                        url,
                        json=data,
                        headers=headers,
                    )

                    # Handle rate limiting with exponential backoff
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 5))
                        logger.warning(
                            "Rate limited by exchange",
                            extra={"retry_after": retry_after, "attempt": attempt},
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    result = response.json()

                    logger.debug(
                        "API request successful",
                        extra={
                            "method": method,
                            "path": path,
                            "status": response.status_code,
                        },
                    )

                    return result

            except httpx.TimeoutException:
                logger.warning(
                    "Request timeout",
                    extra={"path": path, "attempt": attempt, "max": retries},
                )
                if attempt == retries:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

            except httpx.HTTPStatusError as e:
                # Retry on 5xx errors, fail immediately on 4xx
                if e.response.status_code >= 500 and attempt < retries:
                    logger.warning(
                        "Server error, retrying",
                        extra={
                            "status": e.response.status_code,
                            "attempt": attempt,
                            "max": retries,
                        },
                    )
                    await asyncio.sleep(2**attempt)
                    continue

                logger.error(
                    "HTTP error",
                    extra={
                        "status": e.response.status_code,
                        "path": path,
                        "response": e.response.text,
                    },
                )
                raise

        raise RuntimeError("Unreachable: retry loop exited without return or raise")

    async def load_symbol_info(self, symbol: str) -> SymbolInfo:
        """Load and cache trading pair information.

        Args:
            symbol: Trading pair symbol

        Returns:
            Symbol precision and limits
        """
        if symbol in self._symbol_info:
            return self._symbol_info[symbol]

        # Fetch from exchange
        response = await self._request("GET", f"/v1/markets/{symbol}")

        info = SymbolInfo(
            symbol=symbol,
            tick_size=Decimal(str(response["tick_size"])),
            lot_size=Decimal(str(response["lot_size"])),
            min_order_size=Decimal(str(response["min_order_size"])),
            max_order_size=Decimal(str(response["max_order_size"])),
        )

        self._symbol_info[symbol] = info
        logger.info("Loaded symbol info", extra={"symbol": symbol, "info": info})
        return info

    def round_price(self, symbol: str, price: Decimal) -> Decimal:
        """Round price to exchange tick size.

        Args:
            symbol: Trading pair
            price: Price to round

        Returns:
            Price rounded down to valid tick
        """
        if symbol not in self._symbol_info:
            raise ValueError(f"Symbol {symbol} not loaded. Call load_symbol_info first.")

        tick_size = self._symbol_info[symbol].tick_size
        return (price / tick_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick_size

    def round_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """Round quantity to exchange lot size.

        Args:
            symbol: Trading pair
            quantity: Quantity to round

        Returns:
            Quantity rounded down to valid lot
        """
        if symbol not in self._symbol_info:
            raise ValueError(f"Symbol {symbol} not loaded. Call load_symbol_info first.")

        lot_size = self._symbol_info[symbol].lot_size
        return (
            quantity / lot_size
        ).quantize(Decimal("1"), rounding=ROUND_DOWN) * lot_size

    async def place_order(self, order_request: OrderRequest) -> Order:
        """Place an order on the exchange.

        Args:
            order_request: Order parameters

        Returns:
            Confirmed order with exchange ID

        Raises:
            ValueError: If order validation fails
            httpx.HTTPStatusError: On exchange rejection
        """
        # Ensure symbol info is loaded
        if order_request.symbol not in self._symbol_info:
            await self.load_symbol_info(order_request.symbol)

        # Convert to Decimal for precise math
        quantity_dec = Decimal(str(order_request.quantity))
        price_dec = (
            Decimal(str(order_request.price)) if order_request.price else None
        )

        # Round to exchange precision
        quantity_dec = self.round_quantity(order_request.symbol, quantity_dec)
        if price_dec:
            price_dec = self.round_price(order_request.symbol, price_dec)

        # Validate order size
        symbol_info = self._symbol_info[order_request.symbol]
        if quantity_dec < symbol_info.min_order_size:
            raise ValueError(
                f"Order quantity {quantity_dec} below minimum {symbol_info.min_order_size}"
            )
        if quantity_dec > symbol_info.max_order_size:
            raise ValueError(
                f"Order quantity {quantity_dec} above maximum {symbol_info.max_order_size}"
            )

        # Build request payload
        payload = {
            "symbol": order_request.symbol,
            "side": order_request.side.value,
            "type": order_request.order_type.value,
            "quantity": str(quantity_dec),
            "reduce_only": order_request.reduce_only,
        }

        if price_dec:
            payload["price"] = str(price_dec)
            payload["post_only"] = order_request.post_only

        if order_request.stop_price:
            payload["stop_price"] = str(
                self.round_price(
                    order_request.symbol, Decimal(str(order_request.stop_price))
                )
            )

        logger.info("Placing order", extra={"payload": payload})

        response = await self._request("POST", "/v1/orders", data=payload)

        order = Order(
            id=response["id"],
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=float(quantity_dec),
            price=float(price_dec) if price_dec else None,
            stop_price=order_request.stop_price,
            status=response["status"],
            filled_quantity=float(response.get("filled_quantity", 0)),
            average_fill_price=response.get("average_fill_price"),
            created_at=response["created_at"],
            updated_at=response["updated_at"],
        )

        logger.info(
            "Order placed",
            extra={
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
            },
        )

        return order

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an existing order.

        Args:
            order_id: Exchange order ID

        Returns:
            Cancellation confirmation
        """
        logger.info("Cancelling order", extra={"order_id": order_id})
        response = await self._request("DELETE", f"/v1/orders/{order_id}")
        logger.info("Order cancelled", extra={"order_id": order_id})
        return response

    async def cancel_all_orders(self, symbol: str | None = None) -> list[str]:
        """Cancel all open orders.

        Args:
            symbol: Optional symbol filter, cancels all if None

        Returns:
            List of cancelled order IDs
        """
        logger.warning("Cancelling all orders", extra={"symbol": symbol})

        payload = {}
        if symbol:
            payload["symbol"] = symbol

        response = await self._request("DELETE", "/v1/orders", data=payload)
        cancelled_ids = response.get("cancelled_order_ids", [])

        logger.warning(
            "All orders cancelled",
            extra={"count": len(cancelled_ids), "symbol": symbol},
        )

        return cancelled_ids

    async def get_order(self, order_id: str) -> Order:
        """Get order status.

        Args:
            order_id: Exchange order ID

        Returns:
            Current order state
        """
        response = await self._request("GET", f"/v1/orders/{order_id}")

        return Order(
            id=response["id"],
            symbol=response["symbol"],
            side=OrderSide(response["side"]),
            order_type=OrderType(response["type"]),
            quantity=float(response["quantity"]),
            price=response.get("price"),
            stop_price=response.get("stop_price"),
            status=response["status"],
            filled_quantity=float(response.get("filled_quantity", 0)),
            average_fill_price=response.get("average_fill_price"),
            created_at=response["created_at"],
            updated_at=response["updated_at"],
        )

    async def get_open_orders(self, symbol: str | None = None) -> list[Order]:
        """Get all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params["symbol"] = symbol

        response = await self._request("GET", "/v1/orders/open", data=params)

        return [
            Order(
                id=order["id"],
                symbol=order["symbol"],
                side=OrderSide(order["side"]),
                order_type=OrderType(order["type"]),
                quantity=float(order["quantity"]),
                price=order.get("price"),
                stop_price=order.get("stop_price"),
                status=order["status"],
                filled_quantity=float(order.get("filled_quantity", 0)),
                average_fill_price=order.get("average_fill_price"),
                created_at=order["created_at"],
                updated_at=order["updated_at"],
            )
            for order in response.get("orders", [])
        ]

    async def get_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of current positions
        """
        response = await self._request("GET", "/v1/positions")

        return [
            Position(
                symbol=pos["symbol"],
                side=OrderSide(pos["side"]),
                quantity=float(pos["quantity"]),
                entry_price=float(pos["entry_price"]),
                mark_price=float(pos["mark_price"]),
                liquidation_price=pos.get("liquidation_price"),
                unrealized_pnl=float(pos["unrealized_pnl"]),
                realized_pnl=float(pos["realized_pnl"]),
                leverage=float(pos["leverage"]),
            )
            for pos in response.get("positions", [])
        ]

    async def get_account_balance(self) -> dict[str, Any]:
        """Get account balance and margin info.

        Returns:
            Account balance details
        """
        response = await self._request("GET", "/v1/account")
        logger.debug("Account balance retrieved", extra={"balance": response})
        return response

    async def get_market_price(self, symbol: str) -> Decimal:
        """Get current market price for a symbol.

        Args:
            symbol: Trading pair

        Returns:
            Current market price
        """
        response = await self._request("GET", f"/v1/markets/{symbol}/ticker")
        return Decimal(str(response["last_price"]))

    async def healthcheck(self) -> bool:
        """Check if exchange API is accessible.

        Returns:
            True if API is healthy
        """
        try:
            await self._request("GET", "/v1/health")
            return True
        except Exception as e:
            logger.error("Healthcheck failed", extra={"error": str(e)})
            return False
