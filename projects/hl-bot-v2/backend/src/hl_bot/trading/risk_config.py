"""Risk management configuration.

All risk limits are configurable but MUST be enforced.
Never hardcode risk parameters — always load from config/environment.
"""

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskConfig(BaseSettings):
    """Risk management configuration with sane defaults.
    
    All limits are designed to fail safely. Better to miss trades than blow up accounts.
    """
    
    # Position sizing
    max_position_size_usd: Decimal = Field(
        default=Decimal("1000"),
        gt=0,
        description="Maximum position size in USD",
    )
    
    max_position_size_percent: Decimal = Field(
        default=Decimal("0.1"),
        gt=0,
        le=1,
        description="Max position as % of account (0.1 = 10%)",
    )
    
    # Order limits
    max_order_notional: Decimal = Field(
        default=Decimal("5000"),
        gt=0,
        description="Maximum order size in USD",
    )
    
    max_open_orders: int = Field(
        default=10,
        gt=0,
        description="Maximum number of open orders",
    )
    
    # Loss limits
    max_daily_loss: Decimal = Field(
        default=Decimal("500"),
        gt=0,
        description="Maximum daily loss in USD",
    )
    
    max_daily_loss_percent: Decimal = Field(
        default=Decimal("0.05"),
        gt=0,
        le=1,
        description="Max daily loss as % of account (0.05 = 5%)",
    )
    
    max_consecutive_losses: int = Field(
        default=3,
        gt=0,
        description="Max consecutive losses before circuit breaker",
    )
    
    # Exposure limits
    max_total_exposure: Decimal = Field(
        default=Decimal("10000"),
        gt=0,
        description="Maximum total notional exposure across all positions",
    )
    
    max_exposure_percent: Decimal = Field(
        default=Decimal("0.5"),
        gt=0,
        le=1,
        description="Max total exposure as % of account (0.5 = 50%)",
    )
    
    max_positions: int = Field(
        default=5,
        gt=0,
        description="Maximum number of open positions",
    )
    
    # Price validation
    max_price_deviation: Decimal = Field(
        default=Decimal("0.05"),
        gt=0,
        le=1,
        description="Max price deviation from market (0.05 = 5%)",
    )
    
    max_slippage_percent: Decimal = Field(
        default=Decimal("0.01"),
        gt=0,
        le=1,
        description="Max allowed slippage (0.01 = 1%)",
    )
    
    # Circuit breaker
    max_consecutive_errors: int = Field(
        default=5,
        gt=0,
        description="Max consecutive errors before circuit breaker trips",
    )
    
    circuit_breaker_cooldown_minutes: int = Field(
        default=30,
        gt=0,
        description="Minutes before circuit breaker can reset",
    )
    
    # Leverage limits
    max_leverage: Decimal = Field(
        default=Decimal("3"),
        gt=0,
        le=20,
        description="Maximum leverage allowed",
    )
    
    # Time-based limits
    max_orders_per_minute: int = Field(
        default=10,
        gt=0,
        description="Maximum orders per minute per symbol",
    )
    
    cooldown_after_stop_loss_minutes: int = Field(
        default=15,
        gt=0,
        description="Cooldown period after stop loss before re-entry",
    )
    
    model_config = SettingsConfigDict(
        env_prefix="RISK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    @classmethod
    def from_file(cls, path: Path | str) -> "RiskConfig":
        """Load configuration from file.
        
        Args:
            path: Path to config file (JSON or YAML)
            
        Returns:
            RiskConfig instance
        """
        import json
        
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path) as f:
            data = json.load(f)
        
        return cls(**data)
    
    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return self.model_dump()


class TradingState(BaseModel):
    """Current trading state for risk tracking.
    
    This tracks mutable state that changes during trading.
    Separate from RiskConfig which is mostly immutable.
    """
    
    # Daily metrics (reset daily)
    daily_pnl: Decimal = Field(default=Decimal("0"), description="Today's P&L")
    daily_trades: int = Field(default=0, ge=0, description="Trades today")
    daily_wins: int = Field(default=0, ge=0, description="Winning trades today")
    daily_losses: int = Field(default=0, ge=0, description="Losing trades today")
    
    # Consecutive metrics
    consecutive_wins: int = Field(default=0, ge=0)
    consecutive_losses: int = Field(default=0, ge=0)
    consecutive_errors: int = Field(default=0, ge=0)
    
    # Current state
    open_positions: int = Field(default=0, ge=0)
    open_orders: int = Field(default=0, ge=0)
    total_exposure_usd: Decimal = Field(default=Decimal("0"), ge=0)
    
    # Circuit breaker
    circuit_breaker_tripped: bool = Field(default=False)
    circuit_breaker_reason: str | None = Field(default=None)
    circuit_breaker_time: float | None = Field(default=None)
    
    # Account state
    account_balance: Decimal = Field(default=Decimal("0"), ge=0)
    account_equity: Decimal = Field(default=Decimal("0"), ge=0)
    
    def reset_daily(self) -> None:
        """Reset daily metrics (call at start of trading day)."""
        self.daily_pnl = Decimal("0")
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
    
    def record_trade(self, pnl: Decimal) -> None:
        """Record a trade result.
        
        Args:
            pnl: Trade P&L (positive for win, negative for loss)
        """
        self.daily_trades += 1
        self.daily_pnl += pnl
        
        if pnl > 0:
            self.daily_wins += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.daily_losses += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self.consecutive_errors += 1
    
    def record_success(self) -> None:
        """Record a successful operation (resets error count)."""
        self.consecutive_errors = 0
    
    def trip_circuit_breaker(self, reason: str) -> None:
        """Trip the circuit breaker.
        
        Args:
            reason: Why the circuit breaker tripped
        """
        import time
        
        self.circuit_breaker_tripped = True
        self.circuit_breaker_reason = reason
        self.circuit_breaker_time = time.monotonic()
    
    def can_reset_circuit_breaker(self, cooldown_minutes: int) -> bool:
        """Check if circuit breaker can be reset.
        
        Args:
            cooldown_minutes: Required cooldown period
            
        Returns:
            True if cooldown period has passed
        """
        import time
        
        if not self.circuit_breaker_tripped or self.circuit_breaker_time is None:
            return False
        
        elapsed_minutes = (time.monotonic() - self.circuit_breaker_time) / 60
        return elapsed_minutes >= cooldown_minutes
    
    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after cooldown."""
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason = None
        self.circuit_breaker_time = None
        self.consecutive_errors = 0
