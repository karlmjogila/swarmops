# Trading Strategy Knowledge Base

This document contains the core trading strategies and setups used by the bot.
Sources: 8amEST Price Action Course, ControllerFX Playbook 2022

---

## Core Philosophy

- **Organic trading** — Candles only, no indicators or fibs
- **Setup ≠ Entry** — Wait for all conditions + trigger
- **Never settle** — Full alignment required before execution
- **Safety first** — No signal is better than a bad signal

---

## Daily Workflow

### Pre-Session (Before 8am EST)
1. Check daily/4H bias for direction
2. Draw support (lowest rejection) and resistance (highest rejection)
3. Identify ranges and consolidation zones
4. Note key levels from "looking left"

### Key Session Times (NY)
- **8:00 AM EST** — Pre-market liquidity
- **8:20 AM EST** — COMEX open (metals, commodities)
- **9:00 AM EST** — Major session activity
- **9:30 AM EST** — NYSE open (stocks, indices)

---

## Market Structure

### Trend Identification
- **Bullish:** Higher Highs (HH) + Higher Lows (HL)
- **Bearish:** Lower Highs (LH) + Lower Lows (LL)
- **Range:** Price oscillating between clear S/R

### Structure Breaks
- **BOS (Break of Structure):** Continuation signal
- **CHOCH (Change of Character):** Reversal signal

---

## The 3 Main Setups (ControllerFX)

### Setup 1: BREAKOUT
**Definition:** Price closes outside a range → expect continuation

#### Bullish Breakout
1. Candle closes ABOVE range/resistance
2. **Entry:** Buy Stop above candle high OR market buy on next open
3. **Stop Loss:** Below previous candle low
4. **Take Profit:** Next resistance level

#### Bearish Breakout
1. Candle closes BELOW range/support
2. **Entry:** Sell Stop below candle low OR market sell on next open
3. **Stop Loss:** Above previous candle high
4. **Take Profit:** Next support level

**Variations:**
- Small Wick: Tighter stop, faster entry
- Steeper Wick: Wider stop at wick extreme
- + Celery: Wait for confirmation wick before stop order

---

### Setup 2: FAKEOUT
**Definition:** Price breaks out but closes BACK into range (failed breakout)

#### Bullish Fakeout (after downside fake)
1. Price breaks BELOW range (fake breakdown)
2. Closes BACK into range
3. **Entry:** Buy Stop above the fakeout candle
4. **Stop Loss:** Below the fakeout wick low
5. **Take Profit:** Opposite end of range (resistance)

#### Bearish Fakeout (after upside fake)
1. Price breaks ABOVE range (fake breakout)
2. Closes BACK into range
3. **Entry:** Sell Stop below the fakeout candle
4. **Stop Loss:** Above the fakeout wick high
5. **Take Profit:** Opposite end of range (support)

**Variations:**
- Small Wick: Tighter stop at wick
- Steeper Wick: Wider stop, stronger rejection signal
- + Celery: Wait for confirmation wick

---

### Setup 3: ONION
**Definition:** Price consolidates in range, respects one side → trade to opposite side

#### Bullish Onion
1. Range forms with clear support/resistance
2. Bullish candle closes at SUPPORT within range
3. **Entry:** Buy Stop above range/resistance
4. **Stop Loss:** Below support
5. **Take Profit:** Retest of range high, then higher targets

#### Bearish Onion
1. Range forms with clear support/resistance
2. Bearish candle closes at RESISTANCE within range
3. **Entry:** Sell Stop below range/support
4. **Stop Loss:** Above resistance
5. **Take Profit:** Retest of range low, then lower targets

**Variations:**
- Small Wick: Standard entry
- Steeper Wick: Strong rejection, higher confidence
- + Celery: Wait for confirmation wick

---

## Entry Types

### Standard Entry
Enter immediately on close outside range (breakout) or back into range (fakeout)

### Celery Play 🥬
A planned entry that looks like impulse but isn't — wait for confirming wick:
- **Bullish:** Wait for wick DOWN → Buy Stop above candle high → SL below candle low
- **Bearish:** Wait for wick UP → Sell Stop below candle low → SL above candle high
- **Key Rule:** The breakout candle must respect previous candle lows/highs

### Onion Play 🧅
Setup where price creates a range, then closes at one side:
- **Bullish:** Range forms → bullish close at support → Buy Stop above range
- **Bearish:** Range forms → bearish close at resistance → Sell Stop below range

---

## Candle Pattern Recognition

### Small Wick
- Minimal wicks on both sides
- Strong momentum/conviction
- Entry: Standard, tighter stop loss

### Steeper Wick (Rejection)
- Long wick in one direction
- Shows rejection from a level
- Entry: Stop order at wick extreme, wider SL

### Celery Candle
- Narrow body
- Long wicks on both sides
- Wait for direction confirmation

### LE Candle (Liquidity Engine)
- Strong directional move
- Engulfing previous candles
- High momentum continuation signal

---

## Support & Resistance Drawing

### The "Connect the Dots" Method
1. **Support:** Find the LOWEST rejection point (not lowest low)
2. **Resistance:** Find the HIGHEST rejection point (not highest high)
3. **Look Left:** Always check historical levels
4. **Clean Traffic:** Prefer zones with few touches (clean vs noisy)

### Zone Validation
- Multiple touches = stronger zone
- Recent touches more relevant than old
- Confluence with round numbers adds strength

---

## Risk Management

### Position Sizing
- **Max daily risk:** 8% of account
- **Per trade:** Split into 4 positions (2% each)
- **High confluence (>70):** Full position
- **Medium confluence (50-70):** Half position
- **Low confluence (<50):** Skip or quarter position

### Stop Loss Rules
- Always defined BEFORE entry
- Based on structure, not arbitrary percentages
- Small wick → tighter SL
- Steeper wick → SL beyond wick extreme

### Take Profit Strategy
1. **TP1:** Next S/R level (partial close)
2. **TP2:** Major S/R or measured move
3. **TP3:** Extended target (let it run)
- Move SL to break-even after TP1

---

## Trade Validation Checklist

Before taking any trade, confirm:

- [ ] Higher timeframe bias aligns
- [ ] Setup type identified (Breakout/Fakeout/Onion)
- [ ] Entry type confirmed (Standard/Celery/Onion)
- [ ] Wick pattern noted (Small/Steeper)
- [ ] S/R levels drawn correctly
- [ ] Stop loss placed at structure
- [ ] Risk/reward minimum 2:1
- [ ] Position size appropriate for confluence

---

## Setup Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│                    BULLISH SETUPS                           │
├─────────────────┬───────────────────────────────────────────┤
│ BREAKOUT        │ Close above range → Buy on next open/high │
│ FAKEOUT         │ Fake break down → Back in range → Buy     │
│ ONION           │ Bullish close at support → Buy breakout   │
├─────────────────┴───────────────────────────────────────────┤
│                    BEARISH SETUPS                           │
├─────────────────┬───────────────────────────────────────────┤
│ BREAKOUT        │ Close below range → Sell on next open/low │
│ FAKEOUT         │ Fake break up → Back in range → Sell      │
│ ONION           │ Bearish close at resistance → Sell break  │
└─────────────────┴───────────────────────────────────────────┘
```

---

## Expected Performance

- **Claimed win rate:** 85% (ControllerFX)
- **Minimum R:R:** 2:1
- **One loss should not affect conviction** — these are high-probability setups

---

## Sources

1. **8amEST Price Action Course** — Daily bias, NY session timing, S/R drawing
2. **ControllerFX Playbook 2022** — Breakout/Fakeout/Onion setups, Celery/Onion plays

---

*Last updated: 2026-02-12*
