"""Audit logging for all trading events.

Every order, fill, position change, and risk event must be logged.
Append-only, immutable audit trail for forensics and compliance.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles


class AuditLogger:
    """Append-only audit log for trading events."""

    def __init__(self, log_dir: Path | str):
        """Initialize audit logger.
        
        Args:
            log_dir: Directory to store audit logs
        """
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
    
    async def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log a trading event.
        
        Args:
            event_type: Type of event (order_submitted, order_filled, etc.)
            data: Event data dictionary
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **data,
        }
        
        line = json.dumps(entry, default=str) + "\n"
        
        # Daily log files for easy rotation
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"audit-{date_str}.jsonl"
        
        async with aiofiles.open(log_file, "a") as f:
            await f.write(line)
    
    async def log_order_submitted(self, order_data: dict[str, Any]) -> None:
        """Log order submission."""
        await self.log_event("order_submitted", order_data)
    
    async def log_order_filled(self, order_data: dict[str, Any], fill_data: dict[str, Any]) -> None:
        """Log order fill."""
        await self.log_event("order_filled", {
            "order": order_data,
            "fill": fill_data,
        })
    
    async def log_order_cancelled(self, order_id: str, reason: str) -> None:
        """Log order cancellation."""
        await self.log_event("order_cancelled", {
            "order_id": order_id,
            "reason": reason,
        })
    
    async def log_position_update(self, position_data: dict[str, Any]) -> None:
        """Log position change."""
        await self.log_event("position_update", position_data)
    
    async def log_risk_rejection(self, order_data: dict[str, Any], reason: str) -> None:
        """Log risk check rejection."""
        await self.log_event("risk_rejection", {
            "order": order_data,
            "reason": reason,
        })
    
    async def log_circuit_breaker(self, reason: str, metadata: dict[str, Any] | None = None) -> None:
        """Log circuit breaker trip."""
        await self.log_event("circuit_breaker", {
            "reason": reason,
            **(metadata or {}),
        })
    
    async def log_error(self, error_type: str, error_message: str, context: dict[str, Any] | None = None) -> None:
        """Log error event."""
        await self.log_event("error", {
            "error_type": error_type,
            "error_message": error_message,
            **(context or {}),
        })
    
    async def log_connection_event(self, event: str, details: dict[str, Any] | None = None) -> None:
        """Log connection events (connect, disconnect, reconnect)."""
        await self.log_event("connection", {
            "event": event,
            **(details or {}),
        })
