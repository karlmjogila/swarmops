"""Visual signal generator using chart image analysis.

Combines numerical pattern detection with Claude Vision for visual chart analysis.
Implements ControllerFX playbook setups: Breakout, Fakeout, Onion.
"""

import asyncio
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.dates import DateFormatter
import mplfinance as mpf
import pandas as pd

from hl_bot.services.llm_client import LLMClient
from hl_bot.types import (
    Candle,
    Signal,
    SignalType,
    SetupType,
    MarketPhase,
    PatternType,
    Timeframe,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ControllerFX Strategy Prompt
# ============================================================================

CONTROLLERFX_ANALYSIS_PROMPT = """You are analyzing a trading chart using the combined 8amEST + ControllerFX strategy system.

## Knowledge Sources (These are correlated - same system)
1. **8amEST Price Action Course** — Daily bias, NY session timing, S/R drawing
2. **ControllerFX Playbook 2022** — Specific entry setups, wick patterns, range trading

## Pre-Analysis (8amEST Foundation)
Before identifying setups:
- What is the higher timeframe bias? (Daily/4H direction)
- Where is support? (Lowest rejection point, not lowest low)
- Where is resistance? (Highest rejection point, not highest high)
- Is there a consolidation range?
- Is price near a key level?

## Strategy Framework

There are 3 main setups to identify:

### BREAKOUT
- Price closes OUTSIDE a consolidation range
- Expect continuation in the breakout direction
- Entry: Buy/Sell Stop at candle high/low after close outside range
- Valid if: Clear range existed, clean close outside (not just wick)

### FAKEOUT  
- Price breaks out but closes BACK INTO the range
- This is a failed breakout → trade the reversal
- Entry: Buy/Sell Stop after candle closes back inside range
- Valid if: Clear wick outside range but body closes inside

### ONION
- Price is consolidating WITHIN a range
- Candle closes at one side (support or resistance) respecting it
- Trade towards the opposite side of range
- Valid if: Bullish close at support OR bearish close at resistance

## Candle Patterns to Note

- **Small Wick**: Minimal rejection, strong momentum → tighter stops
- **Steeper Wick**: Long rejection wick → wider stops at wick extreme  
- **Celery**: Wait for confirming wick before entry

## Your Task

Analyze this chart and identify:

1. **Range Detection**
   - Is there a clear consolidation range?
   - Where are support and resistance?
   - How many candles in the range?

2. **Current Setup**
   - Which setup type? (BREAKOUT / FAKEOUT / ONION / NONE)
   - Why this classification?
   - Direction (LONG / SHORT / WAIT)

3. **Entry Details** (if setup valid)
   - Entry price level
   - Stop loss level (based on wick type)
   - Take profit (next S/R or range boundary)
   - Wick type (small / steeper)

4. **Confluence Factors**
   - Higher timeframe bias (if visible)
   - Pattern quality (clean vs messy)
   - Risk/reward ratio

5. **Confidence Score** (0-100)
   - 80+: High probability setup, take full position
   - 60-79: Decent setup, consider half position
   - <60: Low probability, wait for better

Respond with structured JSON matching this schema:
{
    "range_detected": boolean,
    "range_high": float | null,
    "range_low": float | null,
    "range_candles": int,
    "setup_type": "BREAKOUT" | "FAKEOUT" | "ONION" | "NONE",
    "setup_reasoning": string,
    "direction": "LONG" | "SHORT" | "WAIT",
    "entry_price": float | null,
    "stop_loss": float | null,
    "take_profit": float | null,
    "wick_type": "small" | "steeper" | null,
    "celery_confirmation": boolean,
    "higher_tf_bias": "BULLISH" | "BEARISH" | "NEUTRAL" | "UNKNOWN",
    "pattern_quality": "clean" | "messy" | "marginal",
    "risk_reward": float | null,
    "confluence_factors": [string],
    "concerns": [string],
    "confidence_score": int
}
"""


@dataclass
class VisualSignalResult:
    """Result from visual chart analysis."""
    
    range_detected: bool
    range_high: Optional[float]
    range_low: Optional[float]
    range_candles: int
    setup_type: SetupType
    setup_reasoning: str
    direction: SignalType
    entry_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    wick_type: Optional[str]
    celery_confirmation: bool
    higher_tf_bias: str
    pattern_quality: str
    risk_reward: Optional[float]
    confluence_factors: list[str]
    concerns: list[str]
    confidence_score: int
    chart_image: Optional[bytes] = None


class ChartRenderer:
    """Renders candle data to chart images for visual analysis."""
    
    def __init__(self, style: str = "charles"):
        """Initialize chart renderer.
        
        Args:
            style: mplfinance style ('charles', 'yahoo', 'nightclouds', etc.)
        """
        self.style = style
    
    def render_candles(
        self,
        candles: list[Candle],
        title: str = "",
        show_volume: bool = True,
        highlight_range: Optional[tuple[float, float]] = None,
        width: int = 1200,
        height: int = 800,
    ) -> bytes:
        """Render candles to PNG image.
        
        Args:
            candles: List of candle data
            title: Chart title
            show_volume: Whether to show volume
            highlight_range: Optional (low, high) to highlight as range zone
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            PNG image bytes
        """
        if not candles:
            raise ValueError("No candles to render")
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'Date': c.timestamp,
                'Open': float(c.open),
                'High': float(c.high),
                'Low': float(c.low),
                'Close': float(c.close),
                'Volume': float(c.volume) if c.volume else 0,
            }
            for c in candles
        ])
        df.set_index('Date', inplace=True)
        
        # Create figure
        fig_ratio = (width / 100, height / 100)
        
        # Add horizontal lines for range if specified
        addplots = []
        if highlight_range:
            low, high = highlight_range
            addplots.append(mpf.make_addplot(
                [low] * len(df), color='green', linestyle='--', alpha=0.7
            ))
            addplots.append(mpf.make_addplot(
                [high] * len(df), color='red', linestyle='--', alpha=0.7
            ))
        
        # Render to buffer
        buf = io.BytesIO()
        
        mpf.plot(
            df,
            type='candle',
            style=self.style,
            title=title,
            volume=show_volume,
            figsize=fig_ratio,
            savefig=dict(fname=buf, dpi=100, format='png'),
            addplot=addplots if addplots else None,
        )
        
        buf.seek(0)
        return buf.read()


class VisualSignalGenerator:
    """Generate trading signals using visual chart analysis."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        """Initialize visual signal generator.
        
        Args:
            llm_client: LLM client for vision analysis
            model: Model to use for analysis
        """
        self._llm = llm_client or LLMClient()
        self._model = model
        self._renderer = ChartRenderer()
        
        logger.info(f"Visual signal generator initialized with model: {model}")
    
    async def analyze_candles(
        self,
        candles: list[Candle],
        symbol: str = "UNKNOWN",
        timeframe: str = "unknown",
        render_chart: bool = True,
    ) -> VisualSignalResult:
        """Analyze candles visually for ControllerFX setups.
        
        Args:
            candles: List of recent candles (recommend 50-100)
            symbol: Trading symbol
            timeframe: Chart timeframe
            render_chart: Whether to render and analyze chart image
            
        Returns:
            VisualSignalResult with setup detection
        """
        if len(candles) < 10:
            return self._no_setup_result("Insufficient candles for analysis")
        
        # Render chart
        chart_image = None
        if render_chart:
            try:
                chart_image = self._renderer.render_candles(
                    candles,
                    title=f"{symbol} {timeframe}",
                )
            except Exception as e:
                logger.warning(f"Chart rendering failed: {e}")
        
        if not chart_image:
            return self._no_setup_result("Chart rendering failed")
        
        # Analyze with Claude Vision
        try:
            result = await self._analyze_chart_image(chart_image, symbol, timeframe)
            result.chart_image = chart_image
            return result
        except Exception as e:
            logger.error(f"Visual analysis failed: {e}")
            return self._no_setup_result(f"Analysis error: {e}")
    
    async def _analyze_chart_image(
        self,
        image_bytes: bytes,
        symbol: str,
        timeframe: str,
    ) -> VisualSignalResult:
        """Send chart to Claude Vision for analysis."""
        import base64
        import json
        
        # Convert to data URL
        b64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_url = f"data:image/png;base64,{b64_image}"
        
        # Call Claude Vision
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_image,
                        }
                    },
                    {
                        "type": "text",
                        "text": f"Chart: {symbol} {timeframe}\n\n{CONTROLLERFX_ANALYSIS_PROMPT}"
                    }
                ]
            }
        ]
        
        response = await self._llm.chat_async(
            messages=messages,
            model=self._model,
            max_tokens=2000,
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response
            response_text = response.content[0].text if hasattr(response, 'content') else str(response)
            
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            return self._parse_analysis_result(data)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse visual analysis: {e}")
            return self._no_setup_result(f"Parse error: {e}")
    
    def _parse_analysis_result(self, data: dict) -> VisualSignalResult:
        """Parse LLM response into VisualSignalResult."""
        
        # Map setup type
        setup_map = {
            "BREAKOUT": SetupType.BREAKOUT,
            "FAKEOUT": SetupType.FAKEOUT,
            "ONION": SetupType.ONION,
            "NONE": None,
        }
        setup_type = setup_map.get(data.get("setup_type", "NONE"))
        
        # Map direction
        direction_map = {
            "LONG": SignalType.LONG,
            "SHORT": SignalType.SHORT,
            "WAIT": None,
        }
        direction = direction_map.get(data.get("direction", "WAIT"))
        
        return VisualSignalResult(
            range_detected=data.get("range_detected", False),
            range_high=data.get("range_high"),
            range_low=data.get("range_low"),
            range_candles=data.get("range_candles", 0),
            setup_type=setup_type or SetupType.BREAKOUT,  # default
            setup_reasoning=data.get("setup_reasoning", ""),
            direction=direction or SignalType.LONG,  # default
            entry_price=Decimal(str(data["entry_price"])) if data.get("entry_price") else None,
            stop_loss=Decimal(str(data["stop_loss"])) if data.get("stop_loss") else None,
            take_profit=Decimal(str(data["take_profit"])) if data.get("take_profit") else None,
            wick_type=data.get("wick_type"),
            celery_confirmation=data.get("celery_confirmation", False),
            higher_tf_bias=data.get("higher_tf_bias", "UNKNOWN"),
            pattern_quality=data.get("pattern_quality", "marginal"),
            risk_reward=data.get("risk_reward"),
            confluence_factors=data.get("confluence_factors", []),
            concerns=data.get("concerns", []),
            confidence_score=data.get("confidence_score", 0),
        )
    
    def _no_setup_result(self, reason: str) -> VisualSignalResult:
        """Return a no-setup result."""
        return VisualSignalResult(
            range_detected=False,
            range_high=None,
            range_low=None,
            range_candles=0,
            setup_type=SetupType.BREAKOUT,
            setup_reasoning=reason,
            direction=SignalType.LONG,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            wick_type=None,
            celery_confirmation=False,
            higher_tf_bias="UNKNOWN",
            pattern_quality="marginal",
            risk_reward=None,
            confluence_factors=[],
            concerns=[reason],
            confidence_score=0,
        )
    
    def result_to_signal(
        self,
        result: VisualSignalResult,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[Signal]:
        """Convert visual analysis result to a Signal object.
        
        Args:
            result: Visual analysis result
            symbol: Trading symbol
            timeframe: Chart timeframe
            
        Returns:
            Signal if valid setup, None otherwise
        """
        # Minimum confidence threshold
        if result.confidence_score < 60:
            logger.info(f"Confidence too low: {result.confidence_score}")
            return None
        
        # Need entry, SL, TP
        if not all([result.entry_price, result.stop_loss, result.take_profit]):
            logger.info("Missing entry/SL/TP levels")
            return None
        
        # Calculate R:R
        if result.direction == SignalType.LONG:
            risk = result.entry_price - result.stop_loss
            reward = result.take_profit - result.entry_price
        else:
            risk = result.stop_loss - result.entry_price
            reward = result.entry_price - result.take_profit
        
        if risk <= 0:
            return None
        
        rr = float(reward / risk) if risk > 0 else 0
        
        # Minimum R:R check
        if rr < 1.5:
            logger.info(f"R:R too low: {rr:.2f}")
            return None
        
        import uuid
        
        return Signal(
            id=f"visual-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            signal_type=result.direction,
            timeframe=timeframe,
            entry_price=float(result.entry_price),
            stop_loss=float(result.stop_loss),
            take_profit_1=float(result.take_profit),
            take_profit_2=float(result.take_profit) * 1.5 if result.direction == SignalType.LONG else float(result.take_profit) * 0.5,
            confluence_score=float(result.confidence_score),
            patterns_detected=[
                PatternType.SMALL_WICK if result.wick_type == "small" else PatternType.STEEPER_WICK
            ] if result.wick_type else [],
            setup_type=result.setup_type,
            market_phase=MarketPhase.RANGE if result.range_detected else MarketPhase.DRIVE,
            higher_tf_bias=SignalType.LONG if result.higher_tf_bias == "BULLISH" else SignalType.SHORT if result.higher_tf_bias == "BEARISH" else result.direction,
            reasoning=result.setup_reasoning,
        )


# ============================================================================
# Utility Functions
# ============================================================================


async def analyze_chart_visually(
    candles: list[Candle],
    symbol: str,
    timeframe: str,
) -> Optional[Signal]:
    """Convenience function to analyze candles and get a signal.
    
    Args:
        candles: Recent candle data
        symbol: Trading symbol
        timeframe: Chart timeframe
        
    Returns:
        Signal if valid setup detected, None otherwise
    """
    generator = VisualSignalGenerator()
    result = await generator.analyze_candles(candles, symbol, timeframe)
    
    tf_map = {
        "5m": Timeframe.M5,
        "15m": Timeframe.M15,
        "30m": Timeframe.M30,
        "1h": Timeframe.H1,
        "4h": Timeframe.H4,
        "1d": Timeframe.D1,
    }
    
    return generator.result_to_signal(
        result,
        symbol,
        tf_map.get(timeframe.lower(), Timeframe.M15),
    )
