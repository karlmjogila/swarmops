"""
Risk Manager for Hyperliquid Trading Bot Suite

Handles comprehensive risk management including:
- Account-level risk controls (daily loss limits, max positions)
- Position validation before trade execution
- Real-time P&L tracking and circuit breakers
- Risk scoring and trade approval
- Exposure management across correlated assets
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Helper functions for Decimal conversion
def to_decimal(value: float) -> Decimal:
    """Convert float to Decimal with proper precision."""
    return Decimal(str(value))

def to_float(value: Decimal) -> float:
    """Convert Decimal back to float for external APIs."""
    return float(value)

from ..types import (
    Position, Order, OrderSide, OrderType, TradeRecord, 
    AccountInfo, RiskParameters, TradeOutcome, ExitReason
)
from .hyperliquid_client import HyperliquidClient
from .position_manager import PositionManager, PositionManagementState

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TradingState(str, Enum):
    """Trading system state."""
    ACTIVE = "active"  # Normal trading
    REDUCED = "reduced"  # Reduced position sizes
    HALT = "halt"  # No new positions
    EMERGENCY = "emergency"  # Close all positions


@dataclass
class RiskCheck:
    """Result of a risk validation check."""
    passed: bool
    risk_level: RiskLevel
    message: str
    suggested_size: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class DailyRiskMetrics:
    """Daily risk tracking metrics."""
    date: str  # YYYY-MM-DD
    starting_balance: Decimal
    current_balance: Decimal
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    total_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Trade statistics
    trades_executed: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    
    # Risk metrics
    max_drawdown: Decimal = field(default_factory=lambda: Decimal("0"))
    peak_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Position tracking
    max_concurrent_positions: int = 0
    total_fees_paid: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Timestamps
    first_trade_time: Optional[datetime] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Ensure all financial values are Decimal."""
        if isinstance(self.starting_balance, (int, float)):
            self.starting_balance = to_decimal(self.starting_balance)
        if isinstance(self.current_balance, (int, float)):
            self.current_balance = to_decimal(self.current_balance)
        if isinstance(self.realized_pnl, (int, float)):
            self.realized_pnl = to_decimal(self.realized_pnl)
        if isinstance(self.unrealized_pnl, (int, float)):
            self.unrealized_pnl = to_decimal(self.unrealized_pnl)
        if isinstance(self.total_pnl, (int, float)):
            self.total_pnl = to_decimal(self.total_pnl)
        if isinstance(self.max_drawdown, (int, float)):
            self.max_drawdown = to_decimal(self.max_drawdown)
        if isinstance(self.peak_balance, (int, float)):
            self.peak_balance = to_decimal(self.peak_balance)
        if isinstance(self.total_fees_paid, (int, float)):
            self.total_fees_paid = to_decimal(self.total_fees_paid)
    
    def calculate_pnl_percent(self) -> Decimal:
        """Calculate total P&L as percentage of starting balance."""
        if self.starting_balance == Decimal("0"):
            return Decimal("0")
        return (self.total_pnl / self.starting_balance) * Decimal("100")
    
    def calculate_win_rate(self) -> Decimal:
        """Calculate win rate percentage."""
        total_closed = self.trades_won + self.trades_lost
        if total_closed == 0:
            return Decimal("0")
        return (Decimal(self.trades_won) / Decimal(total_closed)) * Decimal("100")


@dataclass
class RiskLimits:
    """Configurable risk limits."""
    # Daily limits
    max_daily_loss_percent: Decimal = field(default_factory=lambda: Decimal("6.0"))  # Max 6% daily loss
    max_daily_loss_absolute: Optional[Decimal] = None
    
    # Position limits
    max_concurrent_positions: int = 3
    max_position_size_percent: Decimal = field(default_factory=lambda: Decimal("10.0"))  # Max 10% of account per position
    
    # Per-trade risk
    default_risk_percent: Decimal = field(default_factory=lambda: Decimal("2.0"))  # Default 2% risk per trade
    max_risk_per_trade_percent: Decimal = field(default_factory=lambda: Decimal("3.0"))  # Never exceed 3% per trade
    
    # Correlation limits
    max_correlated_exposure_percent: Decimal = field(default_factory=lambda: Decimal("15.0"))  # Max 15% in correlated assets
    
    # Drawdown limits
    max_drawdown_percent: Decimal = field(default_factory=lambda: Decimal("15.0"))  # Stop trading if 15% drawdown
    
    # Leverage limits
    max_leverage: Decimal = field(default_factory=lambda: Decimal("5.0"))
    default_leverage: Decimal = field(default_factory=lambda: Decimal("1.0"))
    
    # Cooldown periods
    loss_streak_limit: int = 3  # Halt after 3 consecutive losses
    cooldown_after_daily_limit_hours: int = 24
    
    # Emergency stops
    max_slippage_percent: Decimal = field(default_factory=lambda: Decimal("1.0"))
    emergency_close_threshold_percent: Decimal = field(default_factory=lambda: Decimal("10.0"))  # Emergency close if >10% loss
    
    def __post_init__(self):
        """Ensure all percentage values are Decimal."""
        if isinstance(self.max_daily_loss_percent, (int, float)):
            self.max_daily_loss_percent = to_decimal(self.max_daily_loss_percent)
        if self.max_daily_loss_absolute is not None and isinstance(self.max_daily_loss_absolute, (int, float)):
            self.max_daily_loss_absolute = to_decimal(self.max_daily_loss_absolute)
        if isinstance(self.max_position_size_percent, (int, float)):
            self.max_position_size_percent = to_decimal(self.max_position_size_percent)
        if isinstance(self.default_risk_percent, (int, float)):
            self.default_risk_percent = to_decimal(self.default_risk_percent)
        if isinstance(self.max_risk_per_trade_percent, (int, float)):
            self.max_risk_per_trade_percent = to_decimal(self.max_risk_per_trade_percent)
        if isinstance(self.max_correlated_exposure_percent, (int, float)):
            self.max_correlated_exposure_percent = to_decimal(self.max_correlated_exposure_percent)
        if isinstance(self.max_drawdown_percent, (int, float)):
            self.max_drawdown_percent = to_decimal(self.max_drawdown_percent)
        if isinstance(self.max_leverage, (int, float)):
            self.max_leverage = to_decimal(self.max_leverage)
        if isinstance(self.default_leverage, (int, float)):
            self.default_leverage = to_decimal(self.default_leverage)
        if isinstance(self.max_slippage_percent, (int, float)):
            self.max_slippage_percent = to_decimal(self.max_slippage_percent)
        if isinstance(self.emergency_close_threshold_percent, (int, float)):
            self.emergency_close_threshold_percent = to_decimal(self.emergency_close_threshold_percent)


@dataclass
class AssetExposure:
    """Track exposure to a specific asset."""
    asset: str
    total_size: Decimal = field(default_factory=lambda: Decimal("0"))
    total_value_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    positions: List[str] = field(default_factory=list)  # Position IDs
    avg_entry: Decimal = field(default_factory=lambda: Decimal("0"))
    net_side: Optional[OrderSide] = None
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    
    def __post_init__(self):
        """Ensure all financial values are Decimal."""
        if isinstance(self.total_size, (int, float)):
            self.total_size = to_decimal(self.total_size)
        if isinstance(self.total_value_usd, (int, float)):
            self.total_value_usd = to_decimal(self.total_value_usd)
        if isinstance(self.avg_entry, (int, float)):
            self.avg_entry = to_decimal(self.avg_entry)
        if isinstance(self.unrealized_pnl, (int, float)):
            self.unrealized_pnl = to_decimal(self.unrealized_pnl)


class RiskManager:
    """
    Comprehensive risk management system for trading operations.
    
    Features:
    - Pre-trade validation and position sizing
    - Real-time P&L monitoring with circuit breakers
    - Daily loss limits and drawdown protection
    - Correlation-aware exposure management
    - Automated risk escalation and trading halts
    """
    
    def __init__(
        self,
        hyperliquid_client: HyperliquidClient,
        position_manager: PositionManager,
        risk_limits: Optional[RiskLimits] = None
    ):
        self.client = hyperliquid_client
        self.position_manager = position_manager
        self.risk_limits = risk_limits or RiskLimits()
        
        # State tracking
        self.trading_state = TradingState.ACTIVE
        self.daily_metrics: Dict[str, DailyRiskMetrics] = {}
        self.asset_exposures: Dict[str, AssetExposure] = {}
        
        # Account tracking (use Decimal for precision)
        self.account_balance: Decimal = Decimal("0")
        self.starting_balance: Decimal = Decimal("0")
        
        # Trading statistics
        self.consecutive_losses: int = 0
        self.loss_streak_timestamps: List[datetime] = []
        
        # Circuit breaker state
        self.circuit_breaker_active: bool = False
        self.circuit_breaker_until: Optional[datetime] = None
        self.circuit_breaker_reason: str = ""
        
        # Callbacks
        self._risk_alert_callbacks: List[Callable[[RiskLevel, str], None]] = []
        self._state_change_callbacks: List[Callable[[TradingState, TradingState], None]] = []
        
        # Monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_active = False
        
        # Asset correlation matrix (simplified - can be enhanced)
        self.asset_correlations: Dict[str, List[str]] = {
            "BTC": ["ETH"],
            "ETH": ["BTC"],
            # Add more correlations as needed
        }
        
        # Persistence configuration
        self._persistence_path = Path(os.getenv("RISK_METRICS_PATH", "data/risk_metrics"))
        self._persistence_path.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing metrics on initialization
        self._load_persisted_metrics()
        
    def _load_persisted_metrics(self):
        """Load persisted daily metrics from disk."""
        try:
            # Load metrics for today and recent days
            today = datetime.now(timezone.utc)
            for days_ago in range(7):  # Load last 7 days
                date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                metrics_file = self._persistence_path / f"daily_metrics_{date}.json"
                
                if metrics_file.exists():
                    with open(metrics_file, 'r') as f:
                        data = json.load(f)
                        # Reconstruct DailyRiskMetrics from JSON
                        metrics = DailyRiskMetrics(
                            date=data['date'],
                            starting_balance=Decimal(data['starting_balance']),
                            current_balance=Decimal(data['current_balance']),
                            realized_pnl=Decimal(data.get('realized_pnl', '0')),
                            unrealized_pnl=Decimal(data.get('unrealized_pnl', '0')),
                            total_pnl=Decimal(data.get('total_pnl', '0')),
                            trades_executed=data.get('trades_executed', 0),
                            trades_won=data.get('trades_won', 0),
                            trades_lost=data.get('trades_lost', 0),
                            max_drawdown=Decimal(data.get('max_drawdown', '0')),
                            peak_balance=Decimal(data.get('peak_balance', data['starting_balance'])),
                            max_concurrent_positions=data.get('max_concurrent_positions', 0),
                            total_fees_paid=Decimal(data.get('total_fees_paid', '0')),
                        )
                        if data.get('first_trade_time'):
                            metrics.first_trade_time = datetime.fromisoformat(data['first_trade_time'])
                        
                        self.daily_metrics[date] = metrics
                        logger.info(f"Loaded persisted metrics for {date}")
                        
        except Exception as e:
            logger.warning(f"Error loading persisted metrics: {e}")
    
    def _persist_daily_metrics(self, date: str):
        """Persist daily metrics to disk."""
        if date not in self.daily_metrics:
            return
        
        try:
            metrics = self.daily_metrics[date]
            metrics_file = self._persistence_path / f"daily_metrics_{date}.json"
            
            # Convert to JSON-serializable format
            data = {
                'date': metrics.date,
                'starting_balance': str(metrics.starting_balance),
                'current_balance': str(metrics.current_balance),
                'realized_pnl': str(metrics.realized_pnl),
                'unrealized_pnl': str(metrics.unrealized_pnl),
                'total_pnl': str(metrics.total_pnl),
                'trades_executed': metrics.trades_executed,
                'trades_won': metrics.trades_won,
                'trades_lost': metrics.trades_lost,
                'max_drawdown': str(metrics.max_drawdown),
                'peak_balance': str(metrics.peak_balance),
                'max_concurrent_positions': metrics.max_concurrent_positions,
                'total_fees_paid': str(metrics.total_fees_paid),
                'first_trade_time': metrics.first_trade_time.isoformat() if metrics.first_trade_time else None,
                'last_updated': metrics.last_updated.isoformat(),
            }
            
            # Atomic write using temp file
            temp_file = metrics_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.rename(metrics_file)
            
            logger.debug(f"Persisted metrics for {date}")
            
        except Exception as e:
            logger.error(f"Error persisting metrics for {date}: {e}")
    
    async def initialize(self):
        """Initialize risk manager with current account state."""
        try:
            # Get current account info
            account_info = await self.client.get_account_info()
            if account_info:
                self.account_balance = to_decimal(account_info.total_balance_usd)
                self.starting_balance = self.account_balance
                
                logger.info(f"Risk manager initialized - Balance: ${to_float(self.account_balance):,.2f}")
            
            # Initialize today's metrics
            await self._initialize_daily_metrics()
            
            # Refresh position exposures
            await self._update_asset_exposures()
            
        except Exception as e:
            logger.error(f"Error initializing risk manager: {e}")
            raise
    
    async def start_monitoring(self):
        """Start risk monitoring loop."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Risk monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Risk monitoring started")
    
    async def stop_monitoring(self):
        """Stop risk monitoring loop."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Risk monitoring stopped")
    
    async def validate_trade(
        self,
        asset: str,
        side: OrderSide,
        size: float,
        entry_price: float,
        stop_loss: float,
        risk_params: Optional[RiskParameters] = None
    ) -> RiskCheck:
        """
        Validate a proposed trade against all risk criteria.
        
        Returns RiskCheck with validation result and suggested adjustments.
        """
        warnings = []
        
        # Check circuit breaker
        if self.circuit_breaker_active:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"Circuit breaker active: {self.circuit_breaker_reason}",
                warnings=warnings
            )
        
        # Check trading state
        if self.trading_state == TradingState.HALT:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                message="Trading is halted due to risk limits",
                warnings=warnings
            )
        
        if self.trading_state == TradingState.EMERGENCY:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message="Emergency state - no new positions allowed",
                warnings=warnings
            )
        
        # Get current metrics
        today_metrics = await self._get_today_metrics()
        
        # Check daily loss limit
        daily_loss_check = self._check_daily_loss_limit(today_metrics)
        if not daily_loss_check.passed:
            return daily_loss_check
        
        # Check maximum concurrent positions
        current_positions = len(self.position_manager.get_managed_positions())
        if current_positions >= self.risk_limits.max_concurrent_positions:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"Max concurrent positions reached: {current_positions}/{self.risk_limits.max_concurrent_positions}",
                warnings=warnings
            )
        
        # Calculate risk amount using Decimal for precision
        risk_percent = to_decimal(risk_params.risk_percent) if risk_params else self.risk_limits.default_risk_percent
        entry_decimal = to_decimal(entry_price)
        stop_decimal = to_decimal(stop_loss)
        size_decimal = to_decimal(size)
        risk_amount = abs(entry_decimal - stop_decimal) * size_decimal
        risk_percent_actual = (risk_amount / self.account_balance) * Decimal("100") if self.account_balance > 0 else Decimal("0")
        
        # Check per-trade risk limit
        if risk_percent_actual > self.risk_limits.max_risk_per_trade_percent:
            # Suggest adjusted size
            max_risk_dollar = self.account_balance * (self.risk_limits.max_risk_per_trade_percent / Decimal("100"))
            price_distance = abs(entry_decimal - stop_decimal)
            suggested_size = to_float(max_risk_dollar / price_distance) if price_distance > 0 else 0.0
            
            warnings.append(f"Risk {to_float(risk_percent_actual):.2f}% exceeds max {to_float(self.risk_limits.max_risk_per_trade_percent)}%")
            
            # Reduced state allows trading with reduced size
            if self.trading_state == TradingState.REDUCED:
                return RiskCheck(
                    passed=True,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Trade approved with reduced size (trading in reduced state)",
                    suggested_size=suggested_size,
                    warnings=warnings
                )
            else:
                return RiskCheck(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"Risk {to_float(risk_percent_actual):.2f}% exceeds limit {to_float(self.risk_limits.max_risk_per_trade_percent)}%",
                    suggested_size=suggested_size,
                    warnings=warnings
                )
        
        # Check position size as percentage of account
        position_value = size_decimal * entry_decimal
        position_percent = (position_value / self.account_balance) * Decimal("100") if self.account_balance > 0 else Decimal("0")
        
        if position_percent > self.risk_limits.max_position_size_percent:
            warnings.append(f"Position size {to_float(position_percent):.1f}% exceeds recommended {to_float(self.risk_limits.max_position_size_percent)}%")
        
        # Check correlation exposure
        correlation_check = await self._check_correlation_exposure(asset, position_value)
        if not correlation_check.passed:
            return correlation_check
        
        if correlation_check.warnings:
            warnings.extend(correlation_check.warnings)
        
        # Check consecutive losses
        if self.consecutive_losses >= self.risk_limits.loss_streak_limit:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"Loss streak limit reached: {self.consecutive_losses} consecutive losses",
                warnings=warnings
            )
        
        # All checks passed
        risk_level = RiskLevel.LOW
        if warnings:
            risk_level = RiskLevel.MEDIUM
        
        return RiskCheck(
            passed=True,
            risk_level=risk_level,
            message="Trade validated successfully",
            warnings=warnings
        )
    
    async def calculate_position_size(
        self,
        asset: str,
        entry_price: float,
        stop_loss: float,
        risk_percent: Optional[float] = None
    ) -> float:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            asset: Asset symbol
            entry_price: Planned entry price
            stop_loss: Stop loss price
            risk_percent: Risk as percentage of account (defaults to configured value)
            
        Returns:
            Position size in asset units
        """
        # Convert to Decimal for precision
        entry_decimal = to_decimal(entry_price)
        stop_decimal = to_decimal(stop_loss)
        
        if risk_percent is None:
            risk_pct_decimal = self.risk_limits.default_risk_percent
        else:
            risk_pct_decimal = to_decimal(risk_percent)
        
        # Cap risk percent at maximum
        risk_pct_decimal = min(risk_pct_decimal, self.risk_limits.max_risk_per_trade_percent)
        
        # Adjust risk based on trading state
        if self.trading_state == TradingState.REDUCED:
            risk_pct_decimal = risk_pct_decimal * Decimal("0.5")  # Halve risk in reduced state
            logger.info(f"Reducing position size by 50% due to REDUCED trading state")
        
        # Calculate risk amount in dollars
        risk_amount = self.account_balance * (risk_pct_decimal / Decimal("100"))
        
        # Calculate position size
        price_distance = abs(entry_decimal - stop_decimal)
        if price_distance == 0:
            logger.error("Stop loss equals entry price - cannot calculate position size")
            return 0.0
        
        position_size = risk_amount / price_distance
        
        # Apply position size limit
        max_position_value = self.account_balance * (self.risk_limits.max_position_size_percent / Decimal("100"))
        max_position_size = max_position_value / entry_decimal if entry_decimal > 0 else Decimal("0")
        
        position_size = min(position_size, max_position_size)
        
        logger.info(f"Position size calculated for {asset}: {to_float(position_size):.4f} (Risk: {to_float(risk_pct_decimal)}%)")
        
        return to_float(position_size)
    
    async def on_trade_opened(self, trade_record: TradeRecord, position: Position):
        """Handle trade opening event."""
        try:
            today_metrics = await self._get_today_metrics()
            
            # Update trade count
            today_metrics.trades_executed += 1
            
            if today_metrics.first_trade_time is None:
                today_metrics.first_trade_time = datetime.now(timezone.utc)
            
            # Update asset exposure
            await self._update_asset_exposures()
            
            # Track max concurrent positions
            current_positions = len(self.position_manager.get_managed_positions())
            today_metrics.max_concurrent_positions = max(
                today_metrics.max_concurrent_positions,
                current_positions
            )
            
            logger.info(f"Trade opened: {trade_record.asset} - {current_positions} active positions")
            
        except Exception as e:
            logger.error(f"Error handling trade opened event: {e}")
    
    async def on_trade_closed(
        self,
        trade_record: TradeRecord,
        exit_price: float,
        pnl: float,
        outcome: TradeOutcome
    ):
        """Handle trade closing event."""
        try:
            today_metrics = await self._get_today_metrics()
            
            # Update P&L using Decimal for precision
            pnl_decimal = to_decimal(pnl)
            today_metrics.realized_pnl += pnl_decimal
            today_metrics.total_pnl = today_metrics.realized_pnl + today_metrics.unrealized_pnl
            
            # Update trade outcome statistics
            if outcome == TradeOutcome.WIN:
                today_metrics.trades_won += 1
                self.consecutive_losses = 0
                self.loss_streak_timestamps.clear()
            elif outcome == TradeOutcome.LOSS:
                today_metrics.trades_lost += 1
                self.consecutive_losses += 1
                self.loss_streak_timestamps.append(datetime.now(timezone.utc))
                
                # Trim old timestamps (keep last 24 hours)
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                self.loss_streak_timestamps = [
                    ts for ts in self.loss_streak_timestamps if ts > cutoff
                ]
            
            # Update peak and drawdown tracking
            current_balance = self.starting_balance + today_metrics.total_pnl
            if current_balance > today_metrics.peak_balance:
                today_metrics.peak_balance = current_balance
            
            drawdown = today_metrics.peak_balance - current_balance
            drawdown_percent = (drawdown / today_metrics.peak_balance) * Decimal("100") if today_metrics.peak_balance > 0 else Decimal("0")
            
            if drawdown_percent > today_metrics.max_drawdown:
                today_metrics.max_drawdown = drawdown_percent
            
            today_metrics.last_updated = datetime.now(timezone.utc)
            
            # Update asset exposures
            await self._update_asset_exposures()
            
            # Check if risk limits breached
            await self._evaluate_risk_state()
            
            logger.info(
                f"Trade closed: {trade_record.asset} - P&L: ${to_float(pnl_decimal):.2f} ({outcome.value}) - "
                f"Daily P&L: ${to_float(today_metrics.total_pnl):.2f} ({to_float(today_metrics.calculate_pnl_percent()):.2f}%)"
            )
            
            # Persist metrics after trade close
            self._persist_daily_metrics(today_metrics.date)
            
        except Exception as e:
            logger.error(f"Error handling trade closed event: {e}")
    
    async def _monitoring_loop(self):
        """Main risk monitoring loop."""
        logger.info("Risk monitoring loop started")
        
        while self._monitoring_active:
            try:
                # Update account balance
                account_info = await self.client.get_account_info()
                if account_info:
                    self.account_balance = to_decimal(account_info.total_balance_usd)
                
                # Update today's metrics
                await self._update_daily_metrics()
                
                # Update asset exposures
                await self._update_asset_exposures()
                
                # Evaluate risk state
                await self._evaluate_risk_state()
                
                # Check circuit breaker expiry
                if self.circuit_breaker_active and self.circuit_breaker_until:
                    if datetime.now(timezone.utc) > self.circuit_breaker_until:
                        await self._deactivate_circuit_breaker()
                
                # Sleep before next iteration
                await asyncio.sleep(5.0)  # Monitor every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(10.0)
        
        logger.info("Risk monitoring loop stopped")
    
    async def _initialize_daily_metrics(self):
        """Initialize metrics for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if today not in self.daily_metrics:
            # Ensure account_balance is Decimal
            balance = self.account_balance if isinstance(self.account_balance, Decimal) else to_decimal(self.account_balance)
            self.daily_metrics[today] = DailyRiskMetrics(
                date=today,
                starting_balance=balance,
                current_balance=balance,
                peak_balance=balance
            )
    
    async def _get_today_metrics(self) -> DailyRiskMetrics:
        """Get or create today's metrics."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if today not in self.daily_metrics:
            await self._initialize_daily_metrics()
        
        return self.daily_metrics[today]
    
    async def _update_daily_metrics(self):
        """Update daily metrics with current state."""
        today_metrics = await self._get_today_metrics()
        
        # Calculate unrealized P&L from all positions using Decimal
        unrealized_pnl = Decimal("0")
        for mgmt_state in self.position_manager.get_managed_positions():
            try:
                market_data = await self.client.get_market_data(mgmt_state.asset)
                if market_data:
                    unrealized_pnl += to_decimal(mgmt_state.calculate_unrealized_pnl(market_data.last))
            except Exception as e:
                logger.error(f"Error calculating unrealized P&L for {mgmt_state.asset}: {e}")
        
        today_metrics.unrealized_pnl = unrealized_pnl
        today_metrics.total_pnl = today_metrics.realized_pnl + today_metrics.unrealized_pnl
        today_metrics.current_balance = today_metrics.starting_balance + today_metrics.total_pnl
        today_metrics.last_updated = datetime.now(timezone.utc)
        
        # Persist metrics periodically (every update in the monitoring loop)
        self._persist_daily_metrics(today_metrics.date)
    
    async def _update_asset_exposures(self):
        """Update asset exposure tracking."""
        exposures: Dict[str, AssetExposure] = {}
        
        for mgmt_state in self.position_manager.get_managed_positions():
            asset = mgmt_state.asset
            
            if asset not in exposures:
                exposures[asset] = AssetExposure(asset=asset)
            
            exposure = exposures[asset]
            exposure.positions.append(mgmt_state.position_id)
            
            # Get current price
            try:
                market_data = await self.client.get_market_data(asset)
                if market_data:
                    current_price = to_decimal(market_data.last)
                    current_size = to_decimal(mgmt_state.current_size)
                    position_value = current_size * current_price
                    
                    exposure.total_size += current_size
                    exposure.total_value_usd += position_value
                    exposure.unrealized_pnl += to_decimal(mgmt_state.calculate_unrealized_pnl(market_data.last))
                    
                    # Determine net side
                    if exposure.net_side is None:
                        exposure.net_side = mgmt_state.side
                    elif exposure.net_side != mgmt_state.side:
                        exposure.net_side = None  # Mixed positions
                    
            except Exception as e:
                logger.error(f"Error updating exposure for {asset}: {e}")
        
        self.asset_exposures = exposures
    
    def _check_daily_loss_limit(self, metrics: DailyRiskMetrics) -> RiskCheck:
        """Check if daily loss limit is breached."""
        loss_percent = abs(metrics.calculate_pnl_percent())
        
        if metrics.total_pnl < Decimal("0"):  # Only check if in loss
            if loss_percent >= self.risk_limits.max_daily_loss_percent:
                return RiskCheck(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"Daily loss limit reached: {to_float(loss_percent):.2f}% (max: {to_float(self.risk_limits.max_daily_loss_percent)}%)"
                )
            
            # Warning at 75% of limit
            warning_threshold = self.risk_limits.max_daily_loss_percent * Decimal("0.75")
            if loss_percent >= warning_threshold:
                return RiskCheck(
                    passed=True,
                    risk_level=RiskLevel.HIGH,
                    message=f"Approaching daily loss limit: {to_float(loss_percent):.2f}%",
                    warnings=[f"Daily loss at {to_float(loss_percent):.2f}% of {to_float(self.risk_limits.max_daily_loss_percent)}% limit"]
                )
        
        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            message="Daily loss within limits"
        )
    
    async def _check_correlation_exposure(self, asset: str, additional_value: float) -> RiskCheck:
        """Check if adding this position would exceed correlation limits."""
        correlated_assets = self.asset_correlations.get(asset, [])
        if not correlated_assets:
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.LOW,
                message="No correlation constraints"
            )
        
        # Calculate total correlated exposure using Decimal
        total_correlated_value = to_decimal(additional_value)
        
        for correlated_asset in correlated_assets:
            if correlated_asset in self.asset_exposures:
                total_correlated_value += self.asset_exposures[correlated_asset].total_value_usd
        
        correlation_percent = (total_correlated_value / self.account_balance) * Decimal("100") if self.account_balance > 0 else Decimal("0")
        
        if correlation_percent > self.risk_limits.max_correlated_exposure_percent:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"Correlated exposure {to_float(correlation_percent):.1f}% exceeds limit {to_float(self.risk_limits.max_correlated_exposure_percent)}%",
                warnings=[f"Correlated assets: {', '.join(correlated_assets)}"]
            )
        
        # Warning at 80% of limit
        warning_threshold = self.risk_limits.max_correlated_exposure_percent * Decimal("0.8")
        if correlation_percent > warning_threshold:
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.MEDIUM,
                message="Correlation exposure acceptable",
                warnings=[f"Correlated exposure at {to_float(correlation_percent):.1f}% of {to_float(self.risk_limits.max_correlated_exposure_percent)}% limit"]
            )
        
        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            message="Correlation exposure within limits"
        )
    
    async def _evaluate_risk_state(self):
        """Evaluate current risk state and adjust trading state if needed."""
        today_metrics = await self._get_today_metrics()
        previous_state = self.trading_state
        new_state = TradingState.ACTIVE
        
        # Check daily loss limit using Decimal
        loss_percent = abs(today_metrics.calculate_pnl_percent())
        if today_metrics.total_pnl < Decimal("0"):
            if loss_percent >= self.risk_limits.max_daily_loss_percent:
                new_state = TradingState.HALT
                await self._activate_circuit_breaker(
                    f"Daily loss limit reached: {to_float(loss_percent):.2f}%",
                    hours=self.risk_limits.cooldown_after_daily_limit_hours
                )
                await self._send_risk_alert(
                    RiskLevel.CRITICAL,
                    f"Daily loss limit reached: {to_float(loss_percent):.2f}% - Trading halted"
                )
            elif loss_percent >= self.risk_limits.max_daily_loss_percent * Decimal("0.75"):
                new_state = TradingState.REDUCED
                await self._send_risk_alert(
                    RiskLevel.HIGH,
                    f"Approaching daily loss limit: {to_float(loss_percent):.2f}% - Reducing position sizes"
                )
        
        # Check drawdown limit
        if today_metrics.max_drawdown >= self.risk_limits.max_drawdown_percent:
            new_state = TradingState.HALT
            await self._activate_circuit_breaker(
                f"Maximum drawdown reached: {to_float(today_metrics.max_drawdown):.2f}%",
                hours=self.risk_limits.cooldown_after_daily_limit_hours
            )
            await self._send_risk_alert(
                RiskLevel.CRITICAL,
                f"Maximum drawdown reached: {to_float(today_metrics.max_drawdown):.2f}% - Trading halted"
            )
        
        # Check loss streak
        if self.consecutive_losses >= self.risk_limits.loss_streak_limit:
            if new_state == TradingState.ACTIVE:
                new_state = TradingState.HALT
            await self._send_risk_alert(
                RiskLevel.HIGH,
                f"Loss streak: {self.consecutive_losses} consecutive losses"
            )
        
        # Check emergency threshold
        if today_metrics.total_pnl < Decimal("0"):
            emergency_loss_percent = abs(today_metrics.calculate_pnl_percent())
            if emergency_loss_percent >= self.risk_limits.emergency_close_threshold_percent:
                new_state = TradingState.EMERGENCY
                await self._emergency_close_all_positions()
                await self._send_risk_alert(
                    RiskLevel.CRITICAL,
                    f"Emergency threshold breached: {to_float(emergency_loss_percent):.2f}% - Closing all positions"
                )
        
        # Update state if changed
        if new_state != previous_state:
            await self._change_trading_state(new_state, previous_state)
    
    async def _change_trading_state(self, new_state: TradingState, old_state: TradingState):
        """Change trading state and notify callbacks."""
        self.trading_state = new_state
        
        logger.warning(f"Trading state changed: {old_state.value} -> {new_state.value}")
        
        # Notify callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    async def _activate_circuit_breaker(self, reason: str, hours: int = 24):
        """Activate circuit breaker to halt trading."""
        self.circuit_breaker_active = True
        self.circuit_breaker_reason = reason
        self.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(hours=hours)
        
        logger.critical(f"Circuit breaker activated: {reason} - Until: {self.circuit_breaker_until.isoformat()}")
    
    async def _deactivate_circuit_breaker(self):
        """Deactivate circuit breaker and resume trading."""
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        self.circuit_breaker_until = None
        
        # Reset to active state
        await self._change_trading_state(TradingState.ACTIVE, self.trading_state)
        
        logger.info("Circuit breaker deactivated - Trading resumed")
    
    async def _emergency_close_all_positions(self):
        """Emergency close all open positions."""
        logger.critical("EMERGENCY: Closing all positions")
        
        managed_positions = self.position_manager.get_managed_positions()
        
        for mgmt_state in managed_positions:
            try:
                await self.position_manager.close_position(
                    mgmt_state.position_id,
                    reason=ExitReason.MANUAL
                )
                logger.info(f"Emergency closed position: {mgmt_state.asset}")
            except Exception as e:
                logger.error(f"Error emergency closing position {mgmt_state.position_id}: {e}")
    
    async def _send_risk_alert(self, level: RiskLevel, message: str):
        """Send risk alert to registered callbacks."""
        logger.log(
            logging.CRITICAL if level == RiskLevel.CRITICAL else logging.WARNING,
            f"RISK ALERT [{level.value.upper()}]: {message}"
        )
        
        for callback in self._risk_alert_callbacks:
            try:
                callback(level, message)
            except Exception as e:
                logger.error(f"Error in risk alert callback: {e}")
    
    # Public API methods
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current risk manager state."""
        today_metrics = self.daily_metrics.get(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        
        return {
            "trading_state": self.trading_state.value,
            "circuit_breaker_active": self.circuit_breaker_active,
            "circuit_breaker_reason": self.circuit_breaker_reason,
            "circuit_breaker_until": self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None,
            "account_balance": to_float(self.account_balance),
            "consecutive_losses": self.consecutive_losses,
            "daily_metrics": {
                "total_pnl": to_float(today_metrics.total_pnl) if today_metrics else 0.0,
                "pnl_percent": to_float(today_metrics.calculate_pnl_percent()) if today_metrics else 0.0,
                "realized_pnl": to_float(today_metrics.realized_pnl) if today_metrics else 0.0,
                "unrealized_pnl": to_float(today_metrics.unrealized_pnl) if today_metrics else 0.0,
                "trades_executed": today_metrics.trades_executed if today_metrics else 0,
                "win_rate": to_float(today_metrics.calculate_win_rate()) if today_metrics else 0.0,
                "max_drawdown": to_float(today_metrics.max_drawdown) if today_metrics else 0.0
            },
            "exposures": {
                asset: {
                    "total_value_usd": to_float(exp.total_value_usd),
                    "unrealized_pnl": to_float(exp.unrealized_pnl),
                    "position_count": len(exp.positions)
                }
                for asset, exp in self.asset_exposures.items()
            }
        }
    
    def get_daily_metrics(self, date: Optional[str] = None) -> Optional[DailyRiskMetrics]:
        """Get daily metrics for a specific date (or today if None)."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.daily_metrics.get(date)
    
    def add_risk_alert_callback(self, callback: Callable[[RiskLevel, str], None]):
        """Add callback for risk alerts."""
        self._risk_alert_callbacks.append(callback)
    
    def add_state_change_callback(self, callback: Callable[[TradingState, TradingState], None]):
        """Add callback for trading state changes."""
        self._state_change_callbacks.append(callback)
    
    async def manual_override_state(self, new_state: TradingState):
        """Manually override trading state (use with caution)."""
        old_state = self.trading_state
        await self._change_trading_state(new_state, old_state)
        logger.warning(f"Manual state override: {old_state.value} -> {new_state.value}")
    
    async def reset_circuit_breaker(self):
        """Manually reset circuit breaker."""
        if self.circuit_breaker_active:
            await self._deactivate_circuit_breaker()
            logger.info("Circuit breaker manually reset")
    
    async def export_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Export comprehensive daily risk report."""
        metrics = self.get_daily_metrics(date)
        if not metrics:
            return {}
        
        return {
            "date": metrics.date,
            "balance": {
                "starting": to_float(metrics.starting_balance),
                "ending": to_float(metrics.current_balance),
                "peak": to_float(metrics.peak_balance)
            },
            "pnl": {
                "realized": to_float(metrics.realized_pnl),
                "unrealized": to_float(metrics.unrealized_pnl),
                "total": to_float(metrics.total_pnl),
                "percent": to_float(metrics.calculate_pnl_percent())
            },
            "trades": {
                "total": metrics.trades_executed,
                "won": metrics.trades_won,
                "lost": metrics.trades_lost,
                "win_rate": to_float(metrics.calculate_win_rate())
            },
            "risk_metrics": {
                "max_drawdown": to_float(metrics.max_drawdown),
                "max_concurrent_positions": metrics.max_concurrent_positions,
                "total_fees": to_float(metrics.total_fees_paid)
            },
            "timestamps": {
                "first_trade": metrics.first_trade_time.isoformat() if metrics.first_trade_time else None,
                "last_updated": metrics.last_updated.isoformat()
            }
        }
