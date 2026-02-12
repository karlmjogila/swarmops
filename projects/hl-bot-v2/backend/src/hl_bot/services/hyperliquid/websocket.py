"""WebSocket market data feed with automatic reconnection.

Resilient connection handling — the market never sleeps, neither should your connection.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MarketDataFeed:
    """Resilient WebSocket connection with automatic reconnection."""

    def __init__(
        self,
        url: str,
        subscriptions: list[dict[str, Any]],
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
    ) -> None:
        """Initialize market data feed.

        Args:
            url: WebSocket URL
            subscriptions: List of subscription messages to send on connect
            reconnect_delay: Initial reconnection delay in seconds
            max_reconnect_delay: Maximum reconnection delay (exponential backoff cap)
        """
        self._url = url
        self._subscriptions = subscriptions
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._callbacks: list[Callable[[dict[str, Any]], Awaitable[None]]] = []
        self._running = False
        self._connection_task: asyncio.Task[None] | None = None
        self._current_delay = reconnect_delay

    def on_message(self, callback: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        """Register a callback for incoming messages.

        Args:
            callback: Async function to call with each message
        """
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start the WebSocket connection with automatic reconnection."""
        if self._running:
            logger.warning("Market data feed already running")
            return

        self._running = True
        self._connection_task = asyncio.create_task(self._connection_loop())
        logger.info("Market data feed started", extra={"url": self._url})

    async def stop(self) -> None:
        """Stop the WebSocket connection gracefully."""
        self._running = False
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
        logger.info("Market data feed stopped")

    async def _connection_loop(self) -> None:
        """Main connection loop with exponential backoff reconnection."""
        while self._running:
            try:
                async with websockets.connect(
                    self._url,
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    logger.info("WebSocket connected")
                    # Reset reconnection delay on successful connection
                    self._current_delay = self._reconnect_delay

                    # Send subscription messages
                    for sub in self._subscriptions:
                        await ws.send(json.dumps(sub))
                        logger.debug("Sent subscription", extra={"subscription": sub})

                    # Process messages
                    async for raw_message in ws:
                        if not self._running:
                            break

                        try:
                            message = json.loads(raw_message)
                            await self._handle_message(message)
                        except json.JSONDecodeError as e:
                            logger.error(
                                "Failed to decode message",
                                extra={"error": str(e), "raw": raw_message[:100]},
                            )
                        except Exception as e:
                            logger.error(
                                "Message handler error",
                                extra={"error": str(e)},
                                exc_info=True,
                            )

            except ConnectionClosed:
                if self._running:
                    logger.warning(
                        "WebSocket disconnected, reconnecting",
                        extra={"delay": self._current_delay},
                    )
                    await asyncio.sleep(self._current_delay)
                    # Exponential backoff
                    self._current_delay = min(
                        self._current_delay * 2, self._max_reconnect_delay
                    )
            except WebSocketException as e:
                if self._running:
                    logger.error(
                        "WebSocket error",
                        extra={"error": str(e), "delay": self._current_delay},
                    )
                    await asyncio.sleep(self._current_delay)
                    self._current_delay = min(
                        self._current_delay * 2, self._max_reconnect_delay
                    )
            except Exception as e:
                logger.error("Unexpected error in connection loop", exc_info=True)
                if self._running:
                    await asyncio.sleep(self._current_delay)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Dispatch message to all registered callbacks.

        Args:
            message: Parsed JSON message
        """
        for callback in self._callbacks:
            try:
                await callback(message)
            except Exception as e:
                # Never let a bad callback kill the feed
                logger.error(
                    "Callback error",
                    extra={"error": str(e), "callback": callback.__name__},
                    exc_info=True,
                )

    @property
    def is_running(self) -> bool:
        """Check if the feed is currently running."""
        return self._running
