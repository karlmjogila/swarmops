"""Trading client implementations.

Provides safe, production-ready clients for exchange connectivity.
Following Trading Systems Excellence principles.
"""

from hl_bot.trading.hyperliquid import HyperliquidClient
from hl_bot.trading.rate_limiter import RateLimiter
from hl_bot.trading.audit_logger import AuditLogger
from hl_bot.trading.position import (
    Position,
    PositionSide,
    PositionTracker,
    Fill,
    round_quantity,
    round_price,
    get_symbol_precision,
)
from hl_bot.trading.risk import (
    RiskManager,
    RiskCheckResult,
    OrderRequest,
)
from hl_bot.trading.risk_config import (
    RiskConfig,
    TradingState,
)

__all__ = [
    "HyperliquidClient",
    "RateLimiter",
    "AuditLogger",
    "Position",
    "PositionSide",
    "PositionTracker",
    "Fill",
    "RiskManager",
    "RiskConfig",
    "RiskCheckResult",
    "OrderRequest",
    "TradingState",
    "round_quantity",
    "round_price",
    "get_symbol_precision",
]
