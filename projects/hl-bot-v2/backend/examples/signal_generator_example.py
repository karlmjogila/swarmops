"""Example usage of the signal generator module.

Demonstrates how to:
1. Generate trading signals from multi-timeframe confluence
2. Validate signals against risk management rules
3. Interpret signal components (entry, stop loss, take profits)
4. Use custom configuration for different trading styles
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import random

from app.core.market.data import Candle
from app.core.patterns.signals import (
    SignalGenerator,
    SignalGenerationConfig,
    generate_signal,
)
from src.hl_bot.types import SignalType


def create_sample_candles(
    count: int,
    timeframe: str,
    start_time: datetime,
    base_price: float = 50000.0,
    volatility: float = 100.0,
    trend: str = "bullish",
) -> List[Candle]:
    """Create sample candle data for demonstration."""
    candles = []
    current_price = base_price
    
    tf_minutes = {
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
    }
    minutes = tf_minutes.get(timeframe, 5)
    
    for i in range(count):
        timestamp = start_time + timedelta(minutes=i * minutes)
        
        # Generate price movement based on trend
        if trend == "bullish":
            move = random.uniform(0, volatility * 1.5)
            close = current_price + move
        elif trend == "bearish":
            move = random.uniform(0, volatility * 1.5)
            close = current_price - move
        else:  # sideways
            move = random.uniform(-volatility, volatility)
            close = current_price + move
        
        # Generate OHLC around the close
        open_price = current_price
        high = max(open_price, close) + random.uniform(0, volatility * 0.3)
        low = min(open_price, close) - random.uniform(0, volatility * 0.3)
        
        candles.append(Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=random.uniform(1000, 5000),
            symbol="BTC-USD",
            timeframe=timeframe,
        ))
        
        current_price = close
    
    return candles


def example_basic_signal_generation():
    """Example 1: Basic signal generation with default config."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Signal Generation")
    print("=" * 80)
    
    # Create strong bullish trend across timeframes
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_sample_candles(50, "1h", start_time, trend="bullish"),
    }
    
    # Generate signal
    signal = generate_signal(mtf_data, "15m", "BTC-USD")
    
    if signal:
        print(f"\n✅ SIGNAL GENERATED")
        print(f"   Direction: {signal.signal_type.value.upper()}")
        print(f"   Entry: ${signal.entry_price:,.2f}")
        print(f"   Stop Loss: ${signal.stop_loss:,.2f}")
        print(f"   Take Profit 1: ${signal.take_profit_1:,.2f}")
        print(f"   Take Profit 2: ${signal.take_profit_2:,.2f}")
        if signal.take_profit_3:
            print(f"   Take Profit 3: ${signal.take_profit_3:,.2f}")
        
        # Calculate risk metrics
        risk = abs(signal.entry_price - signal.stop_loss)
        reward_tp1 = abs(signal.take_profit_1 - signal.entry_price)
        reward_tp2 = abs(signal.take_profit_2 - signal.entry_price)
        rr_tp1 = reward_tp1 / risk
        rr_tp2 = reward_tp2 / risk
        
        print(f"\n   Risk: ${risk:,.2f} ({risk/signal.entry_price*100:.2f}%)")
        print(f"   Reward (TP1): ${reward_tp1:,.2f} - R:R = {rr_tp1:.2f}:1")
        print(f"   Reward (TP2): ${reward_tp2:,.2f} - R:R = {rr_tp2:.2f}:1")
        
        print(f"\n   Confluence Score: {signal.confluence_score:.1f}/100")
        print(f"   Setup Type: {signal.setup_type.value}")
        print(f"   Market Phase: {signal.market_phase.value}")
        print(f"   Higher TF Bias: {signal.higher_tf_bias.value}")
        
        print(f"\n   Reasoning:")
        for line in signal.reasoning.split(" | "):
            print(f"     • {line}")
    else:
        print("\n❌ No signal generated - criteria not met")
    
    print()


def example_risk_management_configs():
    """Example 2: Different risk management configurations."""
    print("=" * 80)
    print("EXAMPLE 2: Risk Management Configurations")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_sample_candles(50, "1h", start_time, trend="bullish"),
    }
    
    configs = [
        ("Conservative", SignalGenerationConfig(
            min_confluence_score=70.0,
            min_agreement_percentage=80.0,
            min_risk_reward=3.0,
            max_stop_loss_percent=0.02,  # 2% max stop
        )),
        ("Balanced", SignalGenerationConfig(
            min_confluence_score=60.0,
            min_agreement_percentage=70.0,
            min_risk_reward=2.5,
            max_stop_loss_percent=0.03,  # 3% max stop
        )),
        ("Aggressive", SignalGenerationConfig(
            min_confluence_score=50.0,
            min_agreement_percentage=60.0,
            min_risk_reward=2.0,
            max_stop_loss_percent=0.05,  # 5% max stop
        )),
    ]
    
    for name, config in configs:
        print(f"\n{name} Configuration:")
        print(f"  Min Confluence: {config.min_confluence_score}")
        print(f"  Min Agreement: {config.min_agreement_percentage}%")
        print(f"  Min R:R: {config.min_risk_reward}:1")
        print(f"  Max Stop Loss: {config.max_stop_loss_percent * 100}%")
        
        signal = generate_signal(mtf_data, "15m", "BTC-USD", config=config)
        
        if signal:
            risk_pct = abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100
            reward_pct = abs(signal.take_profit_2 - signal.entry_price) / signal.entry_price * 100
            rr = reward_pct / risk_pct
            
            print(f"  ✅ Signal: {signal.signal_type.value.upper()}")
            print(f"     Risk: {risk_pct:.2f}% | Reward: {reward_pct:.2f}% | R:R: {rr:.2f}:1")
        else:
            print(f"  ❌ No signal (criteria not met)")
    
    print()


def example_bearish_signal():
    """Example 3: Bearish signal generation."""
    print("=" * 80)
    print("EXAMPLE 3: Bearish Signal Generation")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Strong bearish trend
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bearish", base_price=52000),
        "15m": create_sample_candles(100, "15m", start_time, trend="bearish", base_price=52000),
        "1h": create_sample_candles(50, "1h", start_time, trend="bearish", base_price=52000),
    }
    
    signal = generate_signal(mtf_data, "15m", "BTC-USD")
    
    if signal:
        print(f"\n🔴 SHORT SIGNAL")
        print(f"   Entry: ${signal.entry_price:,.2f}")
        print(f"   Stop Loss: ${signal.stop_loss:,.2f} (above entry)")
        print(f"   Take Profit 1: ${signal.take_profit_1:,.2f}")
        print(f"   Take Profit 2: ${signal.take_profit_2:,.2f}")
        
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.entry_price - signal.take_profit_2)
        
        print(f"\n   Risk/Reward: {reward/risk:.2f}:1")
        print(f"   Confluence: {signal.confluence_score:.1f}/100")
        
        # Position sizing example (1% risk)
        account_balance = 10000  # $10k account
        risk_amount = account_balance * 0.01  # 1% risk = $100
        position_size = risk_amount / risk
        
        print(f"\n   Position Sizing (1% risk on ${account_balance:,} account):")
        print(f"     Risk per trade: ${risk_amount:.2f}")
        print(f"     Position size: {position_size:.4f} BTC")
        print(f"     Notional value: ${position_size * signal.entry_price:,.2f}")
    else:
        print("\n❌ No bearish signal generated")
    
    print()


def example_mixed_timeframes():
    """Example 4: Handling mixed timeframe signals."""
    print("=" * 80)
    print("EXAMPLE 4: Mixed Timeframe Signals")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Lower TF bullish, higher TF bearish (retracement in downtrend)
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish", base_price=48000),
        "15m": create_sample_candles(100, "15m", start_time, trend="sideways", base_price=48000),
        "1h": create_sample_candles(50, "1h", start_time, trend="bearish", base_price=48000),
    }
    
    # Try with default config
    print("\nDefault Config (higher TF alignment required):")
    signal = generate_signal(mtf_data, "15m", "BTC-USD")
    
    if signal:
        print(f"  ✅ Signal: {signal.signal_type.value.upper()}")
        print(f"     Confluence: {signal.confluence_score:.1f}/100")
        print(f"     Higher TF Bias: {signal.higher_tf_bias.value}")
        print(f"     ⚠️  Warning: Mixed signals - lower confidence setup")
    else:
        print(f"  ❌ No signal - conflicting timeframes")
    
    # Try with config that doesn't require higher TF alignment
    print("\nFlexible Config (no higher TF requirement):")
    flexible_config = SignalGenerationConfig(
        require_higher_tf_alignment=False,
        min_confluence_score=40.0,
    )
    signal_flexible = generate_signal(mtf_data, "15m", "BTC-USD", flexible_config)
    
    if signal_flexible:
        print(f"  ✅ Signal: {signal_flexible.signal_type.value.upper()}")
        print(f"     Confluence: {signal_flexible.confluence_score:.1f}/100")
        print(f"     ⚠️  Higher TF not aligned - use smaller position size")
    else:
        print(f"  ❌ Still no signal - confluence too low")
    
    print()


def example_position_sizing():
    """Example 5: Position sizing with generated signals."""
    print("=" * 80)
    print("EXAMPLE 5: Position Sizing Examples")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_sample_candles(50, "1h", start_time, trend="bullish"),
    }
    
    signal = generate_signal(mtf_data, "15m", "BTC-USD")
    
    if not signal:
        print("\n❌ No signal generated for example")
        return
    
    risk_per_trade = abs(signal.entry_price - signal.stop_loss)
    
    account_sizes = [1000, 10000, 100000]  # Different account sizes
    risk_percentages = [0.01, 0.015, 0.02]  # 1%, 1.5%, 2%
    
    print(f"\nSignal: {signal.signal_type.value.upper()} @ ${signal.entry_price:,.2f}")
    print(f"Stop Loss: ${signal.stop_loss:,.2f}")
    print(f"Risk per coin: ${risk_per_trade:,.2f}\n")
    
    print(f"{'Account':>10} | {'Risk %':>8} | {'Risk $':>10} | {'Position':>12} | {'Notional':>12}")
    print("-" * 70)
    
    for account in account_sizes:
        for risk_pct in risk_percentages:
            risk_dollar = account * risk_pct
            position_size = risk_dollar / risk_per_trade
            notional = position_size * signal.entry_price
            
            print(f"${account:>9,} | {risk_pct*100:>6.1f}% | "
                  f"${risk_dollar:>9.2f} | "
                  f"{position_size:>10.4f} | "
                  f"${notional:>11.2f}")
    
    print()


def example_trade_management():
    """Example 6: Trade management with partial exits."""
    print("=" * 80)
    print("EXAMPLE 6: Trade Management Strategy")
    print("=" * 80)
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    mtf_data = {
        "5m": create_sample_candles(200, "5m", start_time, trend="bullish"),
        "15m": create_sample_candles(100, "15m", start_time, trend="bullish"),
        "1h": create_sample_candles(50, "1h", start_time, trend="bullish"),
    }
    
    signal = generate_signal(mtf_data, "15m", "BTC-USD")
    
    if not signal:
        print("\n❌ No signal generated for example")
        return
    
    print(f"\nTrade Setup: {signal.signal_type.value.upper()}")
    print(f"Entry: ${signal.entry_price:,.2f}")
    print(f"Initial Stop: ${signal.stop_loss:,.2f}")
    
    risk = abs(signal.entry_price - signal.stop_loss)
    
    print(f"\nTrade Management Plan:")
    print(f"  1️⃣  TP1 @ ${signal.take_profit_1:,.2f} ({abs(signal.take_profit_1 - signal.entry_price)/risk:.1f}R)")
    print(f"     → Close 50% of position")
    print(f"     → Move stop to breakeven")
    
    print(f"\n  2️⃣  TP2 @ ${signal.take_profit_2:,.2f} ({abs(signal.take_profit_2 - signal.entry_price)/risk:.1f}R)")
    print(f"     → Close 30% of position")
    print(f"     → Trail stop to lock in profits")
    
    if signal.take_profit_3:
        print(f"\n  3️⃣  TP3 @ ${signal.take_profit_3:,.2f} ({abs(signal.take_profit_3 - signal.entry_price)/risk:.1f}R)")
        print(f"     → Close remaining 20%")
    else:
        print(f"\n  3️⃣  Trail remaining 20% with tight stop")
    
    print(f"\n📊 Expected Outcomes (1% risk per trade):")
    
    # Calculate expected R based on partial exits
    avg_r = (
        0.50 * abs(signal.take_profit_1 - signal.entry_price) / risk +
        0.30 * abs(signal.take_profit_2 - signal.entry_price) / risk +
        0.20 * (abs(signal.take_profit_3 - signal.entry_price) / risk if signal.take_profit_3 else abs(signal.take_profit_2 - signal.entry_price) / risk)
    )
    
    print(f"  Average R if all targets hit: {avg_r:.2f}R")
    print(f"  1% risk = 1R loss → {avg_r:.2f}% gain")
    print(f"  On $10,000 account: ${100 * avg_r:.2f} profit")
    
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SIGNAL GENERATOR EXAMPLES" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    examples = [
        example_basic_signal_generation,
        example_risk_management_configs,
        example_bearish_signal,
        example_mixed_timeframes,
        example_position_sizing,
        example_trade_management,
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"❌ Error in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 80)
    print("Examples complete!")
    print("=" * 80)
    print("\n💡 Key Takeaways:")
    print("  • Always validate signals meet minimum confluence thresholds")
    print("  • Use appropriate risk-reward ratios (minimum 2:1)")
    print("  • Adjust position size based on confluence score")
    print("  • Respect higher timeframe bias for better win rate")
    print("  • Use partial exits to lock in profits")
    print("  • Never risk more than 1-2% per trade")
    print()


if __name__ == "__main__":
    main()
