"""
Example usage of the Risk Manager

Demonstrates:
- Risk manager initialization and configuration
- Trade validation before execution
- Real-time risk monitoring
- Circuit breaker activation
- Daily risk reporting
"""

import asyncio
import logging
from datetime import datetime

from .hyperliquid_client import HyperliquidClient
from .position_manager import PositionManager
from .risk_manager import RiskManager, RiskLimits, RiskLevel, TradingState
from ..types import OrderSide, Position, TradeRecord, TradeOutcome, RiskParameters

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """Basic risk manager usage example."""
    
    # Initialize components
    client = HyperliquidClient(
        api_key="your_api_key",
        secret_key="your_secret_key",
        testnet=True
    )
    
    position_manager = PositionManager(client)
    
    # Create custom risk limits
    risk_limits = RiskLimits(
        max_daily_loss_percent=6.0,
        max_concurrent_positions=3,
        default_risk_percent=2.0,
        max_risk_per_trade_percent=3.0,
        loss_streak_limit=3,
        max_drawdown_percent=15.0
    )
    
    # Initialize risk manager
    risk_manager = RiskManager(
        hyperliquid_client=client,
        position_manager=position_manager,
        risk_limits=risk_limits
    )
    
    # Initialize with current account state
    await risk_manager.initialize()
    
    # Start monitoring
    await risk_manager.start_monitoring()
    await position_manager.start_monitoring()
    
    try:
        # Example trade validation
        asset = "BTC"
        entry_price = 50000.0
        stop_loss = 49500.0  # $500 stop
        
        # Calculate position size based on 2% risk
        position_size = await risk_manager.calculate_position_size(
            asset=asset,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_percent=2.0
        )
        
        logger.info(f"Calculated position size for {asset}: {position_size:.4f} BTC")
        
        # Validate trade before execution
        risk_check = await risk_manager.validate_trade(
            asset=asset,
            side=OrderSide.LONG,
            size=position_size,
            entry_price=entry_price,
            stop_loss=stop_loss
        )
        
        if risk_check.passed:
            logger.info(f"✅ Trade validated: {risk_check.message}")
            if risk_check.warnings:
                for warning in risk_check.warnings:
                    logger.warning(f"⚠️  {warning}")
            
            # Trade approved - execute here
            # order = await client.place_order(...)
            
        else:
            logger.error(f"❌ Trade rejected: {risk_check.message}")
            if risk_check.suggested_size:
                logger.info(f"💡 Suggested size: {risk_check.suggested_size:.4f}")
        
        # Keep monitoring
        await asyncio.sleep(60)
        
    finally:
        await risk_manager.stop_monitoring()
        await position_manager.stop_monitoring()


async def example_with_callbacks():
    """Example using risk callbacks for alerts."""
    
    def risk_alert_handler(level: RiskLevel, message: str):
        """Handle risk alerts."""
        if level == RiskLevel.CRITICAL:
            logger.critical(f"🚨 CRITICAL RISK ALERT: {message}")
            # Send notification (email, SMS, Discord, etc.)
        elif level == RiskLevel.HIGH:
            logger.error(f"⚠️  HIGH RISK ALERT: {message}")
        else:
            logger.warning(f"⚡ RISK ALERT: {message}")
    
    def state_change_handler(old_state: TradingState, new_state: TradingState):
        """Handle trading state changes."""
        logger.warning(f"🔄 Trading state changed: {old_state.value} → {new_state.value}")
        
        if new_state == TradingState.HALT:
            logger.critical("🛑 TRADING HALTED - Review risk limits")
        elif new_state == TradingState.REDUCED:
            logger.warning("📉 Trading in REDUCED mode - Position sizes halved")
        elif new_state == TradingState.EMERGENCY:
            logger.critical("🚨 EMERGENCY STATE - All positions being closed")
    
    # Setup components
    client = HyperliquidClient(api_key="key", secret_key="secret", testnet=True)
    position_manager = PositionManager(client)
    risk_manager = RiskManager(client, position_manager)
    
    # Register callbacks
    risk_manager.add_risk_alert_callback(risk_alert_handler)
    risk_manager.add_state_change_callback(state_change_handler)
    
    await risk_manager.initialize()
    await risk_manager.start_monitoring()
    
    # Monitoring will now trigger callbacks on risk events
    await asyncio.sleep(3600)  # Monitor for 1 hour
    
    await risk_manager.stop_monitoring()


async def example_trade_lifecycle():
    """Example of complete trade lifecycle with risk management."""
    
    client = HyperliquidClient(api_key="key", secret_key="secret", testnet=True)
    position_manager = PositionManager(client)
    risk_manager = RiskManager(client, position_manager)
    
    await risk_manager.initialize()
    await risk_manager.start_monitoring()
    await position_manager.start_monitoring()
    
    try:
        # 1. Calculate position size
        asset = "ETH"
        entry_price = 3000.0
        stop_loss = 2950.0
        
        position_size = await risk_manager.calculate_position_size(
            asset=asset,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_percent=2.0
        )
        
        # 2. Validate trade
        risk_check = await risk_manager.validate_trade(
            asset=asset,
            side=OrderSide.LONG,
            size=position_size,
            entry_price=entry_price,
            stop_loss=stop_loss
        )
        
        if not risk_check.passed:
            logger.error(f"Trade validation failed: {risk_check.message}")
            return
        
        # 3. Execute trade
        order = await client.place_order(
            asset=asset,
            size=position_size,
            side=OrderSide.LONG,
            price=entry_price
        )
        
        # 4. Create position and trade record
        position = Position(
            id=order.id,
            asset=asset,
            size=position_size,
            avg_price=entry_price,
            side=OrderSide.LONG
        )
        
        trade_record = TradeRecord(
            id=order.id,
            asset=asset,
            direction=OrderSide.LONG,
            entry_price=entry_price,
            quantity=position_size,
            initial_stop_loss=stop_loss
        )
        
        # 5. Notify risk manager of trade opening
        await risk_manager.on_trade_opened(trade_record, position)
        
        # 6. Start position management
        await position_manager.manage_position(
            position=position,
            trade_record=trade_record,
            current_price=entry_price
        )
        
        # 7. Wait for position to close (or close manually)
        await asyncio.sleep(600)  # Wait 10 minutes
        
        # 8. Simulate trade close
        exit_price = 3100.0  # Profitable exit
        pnl = (exit_price - entry_price) * position_size
        outcome = TradeOutcome.WIN if pnl > 0 else TradeOutcome.LOSS
        
        # 9. Notify risk manager of trade closing
        await risk_manager.on_trade_closed(
            trade_record=trade_record,
            exit_price=exit_price,
            pnl=pnl,
            outcome=outcome
        )
        
        logger.info(f"Trade completed: P&L = ${pnl:.2f}")
        
    finally:
        await risk_manager.stop_monitoring()
        await position_manager.stop_monitoring()


async def example_risk_reporting():
    """Example of generating risk reports."""
    
    client = HyperliquidClient(api_key="key", secret_key="secret", testnet=True)
    position_manager = PositionManager(client)
    risk_manager = RiskManager(client, position_manager)
    
    await risk_manager.initialize()
    
    # Get current state
    current_state = risk_manager.get_current_state()
    
    logger.info("=" * 60)
    logger.info("RISK MANAGER STATE")
    logger.info("=" * 60)
    logger.info(f"Trading State: {current_state['trading_state']}")
    logger.info(f"Account Balance: ${current_state['account_balance']:,.2f}")
    logger.info(f"Circuit Breaker: {'ACTIVE' if current_state['circuit_breaker_active'] else 'Inactive'}")
    logger.info(f"Consecutive Losses: {current_state['consecutive_losses']}")
    logger.info("")
    
    # Daily metrics
    daily = current_state['daily_metrics']
    logger.info("TODAY'S METRICS")
    logger.info("-" * 60)
    logger.info(f"Total P&L: ${daily['total_pnl']:,.2f} ({daily['pnl_percent']:.2f}%)")
    logger.info(f"Realized P&L: ${daily['realized_pnl']:,.2f}")
    logger.info(f"Unrealized P&L: ${daily['unrealized_pnl']:,.2f}")
    logger.info(f"Trades: {daily['trades_executed']} (Win Rate: {daily['win_rate']:.1f}%)")
    logger.info(f"Max Drawdown: {daily['max_drawdown']:.2f}%")
    logger.info("")
    
    # Asset exposures
    if current_state['exposures']:
        logger.info("ASSET EXPOSURES")
        logger.info("-" * 60)
        for asset, exposure in current_state['exposures'].items():
            logger.info(
                f"{asset}: ${exposure['total_value_usd']:,.2f} | "
                f"P&L: ${exposure['unrealized_pnl']:,.2f} | "
                f"Positions: {exposure['position_count']}"
            )
    logger.info("=" * 60)
    
    # Export daily report
    report = await risk_manager.export_daily_report()
    
    # Save to file or send via API
    import json
    with open(f"risk_report_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Daily report exported")


async def example_circuit_breaker():
    """Example demonstrating circuit breaker activation."""
    
    client = HyperliquidClient(api_key="key", secret_key="secret", testnet=True)
    position_manager = PositionManager(client)
    
    # Set aggressive limits to demonstrate circuit breaker
    risk_limits = RiskLimits(
        max_daily_loss_percent=3.0,  # Very tight limit
        loss_streak_limit=2,  # Halt after 2 losses
        max_drawdown_percent=5.0
    )
    
    risk_manager = RiskManager(client, position_manager, risk_limits)
    
    def on_circuit_breaker(level: RiskLevel, message: str):
        if "Circuit breaker activated" in message or "Daily loss limit" in message:
            logger.critical(f"🚨 {message}")
            # Take action: close positions, send alerts, etc.
    
    risk_manager.add_risk_alert_callback(on_circuit_breaker)
    
    await risk_manager.initialize()
    await risk_manager.start_monitoring()
    
    # Simulate losing trades that trigger circuit breaker
    # (In real scenario, this would come from actual trade closures)
    
    # Manual circuit breaker reset (after reviewing issues)
    # await risk_manager.reset_circuit_breaker()
    
    # Manual state override (use with extreme caution)
    # await risk_manager.manual_override_state(TradingState.ACTIVE)
    
    await asyncio.sleep(60)
    await risk_manager.stop_monitoring()


async def example_position_sizing_scenarios():
    """Demonstrate position sizing under different conditions."""
    
    client = HyperliquidClient(api_key="key", secret_key="secret", testnet=True)
    position_manager = PositionManager(client)
    risk_manager = RiskManager(client, position_manager)
    
    # Assume $10,000 account
    risk_manager.account_balance = 10000.0
    risk_manager.starting_balance = 10000.0
    
    logger.info("=" * 60)
    logger.info("POSITION SIZING EXAMPLES (Account: $10,000)")
    logger.info("=" * 60)
    
    scenarios = [
        # (asset, entry, stop, risk%)
        ("BTC", 50000, 49500, 2.0),   # Tight stop
        ("BTC", 50000, 48000, 2.0),   # Wide stop
        ("ETH", 3000, 2950, 2.0),     # Standard setup
        ("ETH", 3000, 2950, 1.0),     # Conservative
        ("SOL", 100, 98, 3.0),        # Aggressive
    ]
    
    for asset, entry, stop, risk_pct in scenarios:
        size = await risk_manager.calculate_position_size(
            asset=asset,
            entry_price=entry,
            stop_loss=stop,
            risk_percent=risk_pct
        )
        
        position_value = size * entry
        risk_amount = abs(entry - stop) * size
        
        logger.info(f"\n{asset} @ ${entry:,.2f} | SL: ${stop:,.2f} | Risk: {risk_pct}%")
        logger.info(f"  Position Size: {size:.4f} {asset}")
        logger.info(f"  Position Value: ${position_value:,.2f}")
        logger.info(f"  Risk Amount: ${risk_amount:,.2f}")
    
    logger.info("\n" + "=" * 60)


async def main():
    """Run all examples."""
    
    logger.info("Starting Risk Manager Examples\n")
    
    # Run examples (comment out ones you don't need)
    
    # await example_basic_usage()
    # await example_with_callbacks()
    # await example_trade_lifecycle()
    await example_risk_reporting()
    # await example_circuit_breaker()
    await example_position_sizing_scenarios()
    
    logger.info("\nExamples completed")


if __name__ == "__main__":
    asyncio.run(main())
