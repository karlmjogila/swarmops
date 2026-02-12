"""Signal generation module with multi-timeframe confluence.

Generates trading signals from confluence analysis with proper risk management,
entry/exit level calculation, and defensive validation.

Principles:
- Safety over speed - validate everything before generating signals
- No signal is better than a bad signal
- Every level (entry, SL, TP) must be justified by structure/zones
- Risk-reward ratios are non-negotiable minimums
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.core.market.data import Candle
from app.core.patterns.candles import PatternSignal
from app.core.patterns.confluence import (
    ConfluenceScore,
    ConfluenceSignal,
    MultiTimeframeConfluenceScorer,
    TimeframeAnalysis,
)
from app.core.patterns.structure import StructureBreak, StructureBreakType, SwingPoint
from app.core.patterns.zones import SupportResistanceZone, ZoneType

from src.hl_bot.types import (
    Signal,
    SignalType,
    SetupType,
    MarketPhase,
    PatternType,
    Timeframe,
)


class MinimumRR(Enum):
    """Minimum risk-reward ratios for different confluence levels."""
    HIGH_CONFIDENCE = 2.0  # >70 confluence
    MEDIUM_CONFIDENCE = 2.5  # 50-70 confluence
    LOW_CONFIDENCE = 3.0  # <50 confluence (rarely taken)


@dataclass
class SignalValidationResult:
    """Result of signal validation checks."""
    valid: bool
    reason: str = ""
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class TradeLevels:
    """Calculated trade entry and exit levels."""
    entry: Decimal
    stop_loss: Decimal
    take_profit_1: Decimal
    take_profit_2: Decimal
    take_profit_3: Optional[Decimal] = None
    
    # Justification for each level
    entry_reason: str = ""
    stop_reason: str = ""
    tp_reasons: List[str] = None
    
    # Risk metrics
    risk_amount: Decimal = Decimal("0")
    reward_amount_tp1: Decimal = Decimal("0")
    reward_amount_tp2: Decimal = Decimal("0")
    risk_reward_ratio: Decimal = Decimal("0")
    
    def __post_init__(self):
        if self.tp_reasons is None:
            self.tp_reasons = []


class SignalGenerationConfig:
    """Configuration for signal generation.
    
    These are the risk parameters that control signal generation.
    All values are conservative defaults - adjust based on backtesting.
    """
    
    def __init__(
        self,
        min_confluence_score: float = 50.0,
        min_agreement_percentage: float = 60.0,
        require_higher_tf_alignment: bool = True,
        min_risk_reward: float = 2.0,
        max_stop_loss_percent: float = 0.03,  # 3% max stop loss
        use_atr_stops: bool = True,
        atr_multiplier: float = 1.5,
        require_zone_confluence: bool = True,
        require_structure_break: bool = False,
    ):
        """Initialize signal generation configuration.
        
        Args:
            min_confluence_score: Minimum confluence score to generate signal (0-100)
            min_agreement_percentage: Minimum % of timeframes agreeing
            require_higher_tf_alignment: Require higher TF to align with signal
            min_risk_reward: Minimum R:R ratio required
            max_stop_loss_percent: Maximum stop loss as % of entry
            use_atr_stops: Use ATR for dynamic stop placement
            atr_multiplier: ATR multiplier for stops
            require_zone_confluence: Require price near S/R zone
            require_structure_break: Require recent structure break
        """
        self.min_confluence_score = min_confluence_score
        self.min_agreement_percentage = min_agreement_percentage
        self.require_higher_tf_alignment = require_higher_tf_alignment
        self.min_risk_reward = min_risk_reward
        self.max_stop_loss_percent = max_stop_loss_percent
        self.use_atr_stops = use_atr_stops
        self.atr_multiplier = atr_multiplier
        self.require_zone_confluence = require_zone_confluence
        self.require_structure_break = require_structure_break


class SignalGenerator:
    """Generate trading signals from multi-timeframe confluence analysis.
    
    Core responsibilities:
    - Analyze confluence scores and determine if signal threshold met
    - Calculate entry, stop loss, and take profit levels
    - Validate risk-reward ratios
    - Ensure proper positioning relative to zones and structure
    - Generate Signal objects with full context
    
    Example:
        >>> generator = SignalGenerator()
        >>> mtf_data = {"5m": candles_5m, "15m": candles_15m, "1h": candles_1h}
        >>> signal = generator.generate_signal(
        ...     mtf_data=mtf_data,
        ...     analysis_timeframe="15m",
        ...     symbol="BTC-USD",
        ... )
        >>> if signal:
        ...     print(f"Signal: {signal.signal_type} @ {signal.entry_price}")
    """
    
    def __init__(
        self,
        config: Optional[SignalGenerationConfig] = None,
        confluence_scorer: Optional[MultiTimeframeConfluenceScorer] = None,
    ):
        """Initialize signal generator.
        
        Args:
            config: Signal generation configuration (uses defaults if None)
            confluence_scorer: Custom confluence scorer (creates default if None)
        """
        self.config = config or SignalGenerationConfig()
        self.scorer = confluence_scorer or MultiTimeframeConfluenceScorer()
    
    def generate_signal(
        self,
        mtf_data: Dict[str, List[Candle]],
        analysis_timeframe: str,
        symbol: str,
    ) -> Optional[Signal]:
        """Generate a trading signal from multi-timeframe data.
        
        Returns None if confluence doesn't meet threshold or if validation fails.
        
        Args:
            mtf_data: Multi-timeframe candle data
            analysis_timeframe: Primary timeframe for entry
            symbol: Trading symbol
            
        Returns:
            Signal object if valid setup found, None otherwise
        """
        # Analyze confluence
        confluence = self.scorer.score_confluence(mtf_data, analysis_timeframe)
        
        # Check if meets minimum threshold
        if not self._meets_minimum_threshold(confluence):
            return None
        
        # Analyze each timeframe to get structure and zones
        analyses = self._analyze_all_timeframes(mtf_data)
        
        # Get current price from analysis timeframe
        current_price = analyses[analysis_timeframe].candles[-1].close
        
        # Determine signal direction
        signal_type = self._determine_signal_type(confluence)
        if signal_type is None:
            return None
        
        # Calculate trade levels
        levels = self._calculate_trade_levels(
            signal_type=signal_type,
            current_price=current_price,
            analyses=analyses,
            analysis_timeframe=analysis_timeframe,
            confluence=confluence,
        )
        
        if levels is None:
            return None
        
        # Validate the signal
        validation = self._validate_signal(
            signal_type=signal_type,
            levels=levels,
            confluence=confluence,
            analyses=analyses,
        )
        
        if not validation.valid:
            return None
        
        # Determine setup type and market phase
        setup_type = self._determine_setup_type(analyses[analysis_timeframe], signal_type)
        market_phase = self._determine_market_phase(analyses[analysis_timeframe])
        
        # Collect pattern types
        patterns = self._get_recent_patterns(analyses[analysis_timeframe])
        
        # Determine higher timeframe bias
        higher_tf_bias = self._get_higher_tf_bias(
            analyses, analysis_timeframe, signal_type
        )
        
        # Build reasoning
        reasoning = self._build_signal_reasoning(
            confluence=confluence,
            levels=levels,
            validation=validation,
            setup_type=setup_type,
        )
        
        # Create and return signal
        signal = Signal(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            signal_type=signal_type,
            timeframe=Timeframe(analysis_timeframe),
            entry_price=float(levels.entry),
            stop_loss=float(levels.stop_loss),
            take_profit_1=float(levels.take_profit_1),
            take_profit_2=float(levels.take_profit_2),
            take_profit_3=float(levels.take_profit_3) if levels.take_profit_3 else None,
            confluence_score=confluence.overall_score,
            patterns_detected=patterns,
            setup_type=setup_type,
            market_phase=market_phase,
            higher_tf_bias=higher_tf_bias,
            reasoning=reasoning,
        )
        
        return signal
    
    def _meets_minimum_threshold(self, confluence: ConfluenceScore) -> bool:
        """Check if confluence meets minimum threshold for signal generation."""
        if confluence.overall_score < self.config.min_confluence_score:
            return False
        
        if confluence.agreement_percentage < self.config.min_agreement_percentage:
            return False
        
        # Must have clear directional signal (not neutral)
        if confluence.signal in (ConfluenceSignal.NEUTRAL,):
            return False
        
        return True
    
    def _analyze_all_timeframes(
        self, mtf_data: Dict[str, List[Candle]]
    ) -> Dict[str, TimeframeAnalysis]:
        """Analyze all timeframes comprehensively."""
        analyses = {}
        for tf, candles in mtf_data.items():
            if candles:
                analyses[tf] = self.scorer.analyze_timeframe(candles, tf)
        return analyses
    
    def _determine_signal_type(
        self, confluence: ConfluenceScore
    ) -> Optional[SignalType]:
        """Determine signal direction from confluence."""
        if confluence.signal in (
            ConfluenceSignal.STRONG_BULLISH,
            ConfluenceSignal.BULLISH,
        ):
            return SignalType.LONG
        elif confluence.signal in (
            ConfluenceSignal.STRONG_BEARISH,
            ConfluenceSignal.BEARISH,
        ):
            return SignalType.SHORT
        
        return None
    
    def _calculate_trade_levels(
        self,
        signal_type: SignalType,
        current_price: float,
        analyses: Dict[str, TimeframeAnalysis],
        analysis_timeframe: str,
        confluence: ConfluenceScore,
    ) -> Optional[TradeLevels]:
        """Calculate entry, stop loss, and take profit levels.
        
        Entry: Current price or better level from zones
        Stop Loss: Beyond structure or zone, validated by ATR
        Take Profits: At resistance/support zones and key levels
        """
        analysis = analyses[analysis_timeframe]
        
        # Convert to Decimal for precision
        price = Decimal(str(current_price))
        
        # Calculate entry
        entry, entry_reason = self._calculate_entry(
            signal_type, price, analysis
        )
        
        # Calculate stop loss
        stop_loss, stop_reason = self._calculate_stop_loss(
            signal_type, entry, analysis, analyses
        )
        
        if stop_loss is None:
            return None
        
        # Validate stop loss distance
        stop_distance = abs(entry - stop_loss)
        stop_percent = stop_distance / entry
        
        if stop_percent > Decimal(str(self.config.max_stop_loss_percent)):
            # Stop too wide - skip this signal
            return None
        
        # Calculate take profits
        tp_result = self._calculate_take_profits(
            signal_type, entry, stop_loss, analysis, analyses, confluence
        )
        
        if tp_result is None:
            return None
        
        tp1, tp2, tp3, tp_reasons = tp_result
        
        # Calculate risk and reward
        risk = abs(entry - stop_loss)
        reward_tp1 = abs(tp1 - entry)
        reward_tp2 = abs(tp2 - entry)
        
        rr_ratio = reward_tp2 / risk if risk > 0 else Decimal("0")
        
        # Validate minimum R:R
        min_rr = self._get_minimum_rr(confluence.overall_score)
        if rr_ratio < Decimal(str(min_rr)):
            return None
        
        return TradeLevels(
            entry=entry,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            entry_reason=entry_reason,
            stop_reason=stop_reason,
            tp_reasons=tp_reasons,
            risk_amount=risk,
            reward_amount_tp1=reward_tp1,
            reward_amount_tp2=reward_tp2,
            risk_reward_ratio=rr_ratio,
        )
    
    def _calculate_entry(
        self,
        signal_type: SignalType,
        current_price: Decimal,
        analysis: TimeframeAnalysis,
    ) -> Tuple[Decimal, str]:
        """Calculate entry price.
        
        For now, use current price. In future, could use:
        - Limit orders at zone boundaries
        - Breakout levels
        - Pullback levels
        """
        return current_price, "Current market price"
    
    def _calculate_stop_loss(
        self,
        signal_type: SignalType,
        entry: Decimal,
        analysis: TimeframeAnalysis,
        all_analyses: Dict[str, TimeframeAnalysis],
    ) -> Tuple[Optional[Decimal], str]:
        """Calculate stop loss level.
        
        Priority:
        1. Beyond recent swing low/high
        2. Beyond nearest zone
        3. ATR-based stop
        
        Stop must invalidate the setup if hit.
        """
        if signal_type == SignalType.LONG:
            # Find swing low
            stop, reason = self._find_stop_below_structure(entry, analysis)
        else:
            # Find swing high
            stop, reason = self._find_stop_above_structure(entry, analysis)
        
        if stop is None:
            # Fallback to ATR stop
            stop, reason = self._calculate_atr_stop(signal_type, entry, analysis)
        
        return stop, reason
    
    def _find_stop_below_structure(
        self, entry: Decimal, analysis: TimeframeAnalysis
    ) -> Tuple[Optional[Decimal], str]:
        """Find stop loss below recent swing low for LONG."""
        if not analysis.swings:
            return None, ""
        
        # Find recent swing lows below entry
        from app.core.patterns.structure import SwingType
        
        recent_lows = [
            s for s in analysis.swings[-10:]
            if s.swing_type == SwingType.LOW and s.price < float(entry)
        ]
        
        if not recent_lows:
            return None, ""
        
        # Use most recent swing low
        swing_low = recent_lows[-1]
        
        # Place stop below swing low with buffer
        buffer = Decimal("0.001")  # 0.1% buffer
        stop = Decimal(str(swing_low.price)) * (Decimal("1") - buffer)
        
        return stop, f"Below swing low at {swing_low.price:.2f}"
    
    def _find_stop_above_structure(
        self, entry: Decimal, analysis: TimeframeAnalysis
    ) -> Tuple[Optional[Decimal], str]:
        """Find stop loss above recent swing high for SHORT."""
        if not analysis.swings:
            return None, ""
        
        from app.core.patterns.structure import SwingType
        
        recent_highs = [
            s for s in analysis.swings[-10:]
            if s.swing_type == SwingType.HIGH and s.price > float(entry)
        ]
        
        if not recent_highs:
            return None, ""
        
        swing_high = recent_highs[-1]
        
        buffer = Decimal("0.001")
        stop = Decimal(str(swing_high.price)) * (Decimal("1") + buffer)
        
        return stop, f"Above swing high at {swing_high.price:.2f}"
    
    def _calculate_atr_stop(
        self,
        signal_type: SignalType,
        entry: Decimal,
        analysis: TimeframeAnalysis,
    ) -> Tuple[Decimal, str]:
        """Calculate ATR-based stop loss."""
        # Calculate ATR from recent candles
        atr = self._calculate_atr(analysis.candles[-14:])  # 14-period ATR
        
        atr_stop_distance = atr * Decimal(str(self.config.atr_multiplier))
        
        if signal_type == SignalType.LONG:
            stop = entry - atr_stop_distance
        else:
            stop = entry + atr_stop_distance
        
        return stop, f"ATR-based ({self.config.atr_multiplier}x ATR)"
    
    def _calculate_atr(self, candles: List[Candle]) -> Decimal:
        """Calculate Average True Range."""
        if len(candles) < 2:
            # Fallback to 1% of price
            return Decimal(str(candles[-1].close * 0.01))
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = Decimal(str(candles[i].high))
            low = Decimal(str(candles[i].low))
            prev_close = Decimal(str(candles[i - 1].close))
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)
        
        atr = sum(true_ranges) / len(true_ranges)
        return atr
    
    def _calculate_take_profits(
        self,
        signal_type: SignalType,
        entry: Decimal,
        stop_loss: Decimal,
        analysis: TimeframeAnalysis,
        all_analyses: Dict[str, TimeframeAnalysis],
        confluence: ConfluenceScore,
    ) -> Optional[Tuple[Decimal, Decimal, Optional[Decimal], List[str]]]:
        """Calculate take profit levels.
        
        Returns:
            Tuple of (tp1, tp2, tp3, reasons) or None if can't find valid TPs
        """
        risk = abs(entry - stop_loss)
        
        # Get minimum R:R based on confluence
        min_rr = self._get_minimum_rr(confluence.overall_score)
        
        # TP1: Conservative (1.5-2R)
        tp1_rr = Decimal("1.5")
        tp1_distance = risk * tp1_rr
        
        if signal_type == SignalType.LONG:
            tp1 = entry + tp1_distance
        else:
            tp1 = entry - tp1_distance
        
        # TP2: Main target (at minimum R:R or better)
        tp2_rr = Decimal(str(min_rr))
        tp2_distance = risk * tp2_rr
        
        if signal_type == SignalType.LONG:
            tp2 = entry + tp2_distance
        else:
            tp2 = entry - tp2_distance
        
        # Try to align TP2 with zones
        tp2, tp2_reason = self._align_tp_with_zones(
            signal_type, tp2, risk, analysis
        )
        
        # TP3: Extended target (optional, high confluence only)
        tp3 = None
        tp3_reason = ""
        
        if confluence.overall_score >= 70:
            tp3_rr = tp2_rr * Decimal("1.5")
            tp3_distance = risk * tp3_rr
            
            if signal_type == SignalType.LONG:
                tp3 = entry + tp3_distance
            else:
                tp3 = entry - tp3_distance
            
            tp3_reason = f"Extended target at {float(tp3_rr):.1f}R"
        
        reasons = [
            f"TP1: Conservative target at {float(tp1_rr)}R",
            tp2_reason or f"TP2: Main target at {float(tp2_rr)}R",
        ]
        
        if tp3:
            reasons.append(tp3_reason)
        
        return tp1, tp2, tp3, reasons
    
    def _align_tp_with_zones(
        self,
        signal_type: SignalType,
        target: Decimal,
        risk: Decimal,
        analysis: TimeframeAnalysis,
    ) -> Tuple[Decimal, str]:
        """Try to align take profit with resistance/support zones."""
        if not analysis.active_zones:
            return target, f"Target at {float(abs(target - risk) / risk):.1f}R"
        
        # Find zones near target
        target_zones = []
        for zone in analysis.active_zones:
            zone_mid = Decimal(str((zone.price_low + zone.price_high) / 2))
            distance = abs(zone_mid - target) / target
            
            # Check if zone is in the right direction
            if signal_type == SignalType.LONG:
                if zone.zone_type == ZoneType.RESISTANCE and zone_mid > target * Decimal("0.8"):
                    target_zones.append((zone, distance))
            else:
                if zone.zone_type == ZoneType.SUPPORT and zone_mid < target * Decimal("1.2"):
                    target_zones.append((zone, distance))
        
        if not target_zones:
            return target, f"Target at {float(abs(target - risk) / risk):.1f}R"
        
        # Use closest zone
        closest_zone, _ = min(target_zones, key=lambda x: x[1])
        adjusted_target = Decimal(str((closest_zone.price_low + closest_zone.price_high) / 2))
        
        return adjusted_target, f"Aligned with {closest_zone.zone_type.value} zone"
    
    def _get_minimum_rr(self, confluence_score: float) -> float:
        """Get minimum risk-reward ratio based on confluence."""
        if confluence_score >= 70:
            return MinimumRR.HIGH_CONFIDENCE.value
        elif confluence_score >= 50:
            return MinimumRR.MEDIUM_CONFIDENCE.value
        else:
            return MinimumRR.LOW_CONFIDENCE.value
    
    def _validate_signal(
        self,
        signal_type: SignalType,
        levels: TradeLevels,
        confluence: ConfluenceScore,
        analyses: Dict[str, TimeframeAnalysis],
    ) -> SignalValidationResult:
        """Validate signal meets all requirements.
        
        Validation checks:
        - Stop loss is on correct side of entry
        - Take profits are on correct side of entry
        - Risk-reward ratio meets minimum
        - Stop loss distance is reasonable
        - No conflicting higher timeframe signals (if required)
        """
        warnings = []
        
        # Check stop loss side
        if signal_type == SignalType.LONG:
            if levels.stop_loss >= levels.entry:
                return SignalValidationResult(
                    valid=False,
                    reason="Stop loss must be below entry for LONG"
                )
        else:
            if levels.stop_loss <= levels.entry:
                return SignalValidationResult(
                    valid=False,
                    reason="Stop loss must be above entry for SHORT"
                )
        
        # Check take profit sides
        if signal_type == SignalType.LONG:
            if levels.take_profit_1 <= levels.entry or levels.take_profit_2 <= levels.entry:
                return SignalValidationResult(
                    valid=False,
                    reason="Take profits must be above entry for LONG"
                )
        else:
            if levels.take_profit_1 >= levels.entry or levels.take_profit_2 >= levels.entry:
                return SignalValidationResult(
                    valid=False,
                    reason="Take profits must be below entry for SHORT"
                )
        
        # Check minimum R:R
        min_rr = Decimal(str(self._get_minimum_rr(confluence.overall_score)))
        if levels.risk_reward_ratio < min_rr:
            return SignalValidationResult(
                valid=False,
                reason=f"Risk-reward {float(levels.risk_reward_ratio):.2f} below minimum {float(min_rr)}"
            )
        
        # Check for conflicting timeframes
        if confluence.conflicting_timeframes:
            warnings.append(
                f"Conflicting signals on: {', '.join(confluence.conflicting_timeframes)}"
            )
        
        # Check higher timeframe alignment if required
        if self.config.require_higher_tf_alignment:
            # Find higher timeframes
            from app.core.market.data import get_timeframe_minutes
            
            analysis_tf = confluence.dominant_timeframe
            analysis_minutes = get_timeframe_minutes(analysis_tf)
            
            higher_tfs = [
                tf for tf in confluence.timeframe_signals.keys()
                if get_timeframe_minutes(tf) > analysis_minutes
            ]
            
            if higher_tfs:
                # Check if any higher TF conflicts
                for tf in higher_tfs:
                    tf_signal = confluence.timeframe_signals[tf]
                    
                    if signal_type == SignalType.LONG and tf_signal == PatternSignal.BEARISH:
                        warnings.append(f"Higher TF {tf} is bearish")
                    elif signal_type == SignalType.SHORT and tf_signal == PatternSignal.BULLISH:
                        warnings.append(f"Higher TF {tf} is bullish")
        
        return SignalValidationResult(valid=True, warnings=warnings)
    
    def _determine_setup_type(
        self, analysis: TimeframeAnalysis, signal_type: SignalType
    ) -> SetupType:
        """Determine the type of setup using ControllerFX Playbook logic.
        
        ControllerFX Setups:
        - BREAKOUT: Price closes outside range → continuation
        - FAKEOUT: Price breaks out but closes back into range → reversal
        - ONION: Price respects one side of range → trade to opposite side
        """
        if len(analysis.candles) < 10:
            return SetupType.BREAKOUT
        
        # Detect range (consolidation) using recent candles
        recent = analysis.candles[-20:] if len(analysis.candles) >= 20 else analysis.candles
        range_high = max(c.high for c in recent[:-1])  # Exclude current candle
        range_low = min(c.low for c in recent[:-1])
        range_size = range_high - range_low
        
        current = analysis.candles[-1]
        prev = analysis.candles[-2] if len(analysis.candles) >= 2 else current
        
        # Check if we're in a valid range (not too wide)
        avg_candle_size = sum(c.high - c.low for c in recent) / len(recent)
        is_ranging = range_size < avg_candle_size * 8  # Range less than 8 candle sizes
        
        if not is_ranging:
            # Not in a range - likely trending
            if analysis.last_structure_break:
                if analysis.last_structure_break.break_type == StructureBreakType.BOS:
                    return SetupType.BREAKOUT
            return SetupType.BREAKOUT
        
        # === FAKEOUT DETECTION ===
        # Previous candle broke out but current candle closed back in range
        prev_broke_high = prev.close > range_high or prev.high > range_high * 1.001
        prev_broke_low = prev.close < range_low or prev.low < range_low * 0.999
        current_in_range = range_low <= current.close <= range_high
        
        if (prev_broke_high or prev_broke_low) and current_in_range:
            return SetupType.FAKEOUT
        
        # === BREAKOUT DETECTION ===
        # Current candle closed outside range
        if current.close > range_high:
            return SetupType.BREAKOUT
        if current.close < range_low:
            return SetupType.BREAKOUT
        
        # === ONION DETECTION ===
        # Price is within range and respecting one side
        # Bullish close at support or bearish close at resistance
        support_zone = range_low + (range_size * 0.2)  # Bottom 20% of range
        resistance_zone = range_high - (range_size * 0.2)  # Top 20% of range
        
        is_bullish_candle = current.close > current.open
        is_bearish_candle = current.close < current.open
        
        # Onion: Bullish at support or bearish at resistance
        if is_bullish_candle and current.close <= support_zone:
            return SetupType.ONION
        if is_bearish_candle and current.close >= resistance_zone:
            return SetupType.ONION
        
        # Check if near zones (pullback to support/resistance)
        if analysis.active_zones:
            return SetupType.PULLBACK
        
        # Default to breakout if no clear pattern
        return SetupType.BREAKOUT
    
    def _determine_market_phase(self, analysis: TimeframeAnalysis) -> MarketPhase:
        """Determine current market phase."""
        # Simple heuristic based on recent price action
        if len(analysis.candles) < 20:
            return MarketPhase.RANGE
        
        recent_candles = analysis.candles[-20:]
        
        # Calculate price range
        high = max(c.high for c in recent_candles)
        low = min(c.low for c in recent_candles)
        range_pct = (high - low) / low
        
        # Calculate trend strength
        close_first = recent_candles[0].close
        close_last = recent_candles[-1].close
        trend_pct = abs(close_last - close_first) / close_first
        
        # If strong trend relative to range, it's a drive
        if trend_pct / range_pct > 0.6:
            return MarketPhase.DRIVE
        
        # If mostly sideways, it's ranging
        if range_pct < 0.05:  # Less than 5% range
            return MarketPhase.RANGE
        
        # Default to liquidity phase (consolidation before breakout)
        return MarketPhase.LIQUIDITY
    
    def _get_recent_patterns(self, analysis: TimeframeAnalysis) -> List[PatternType]:
        """Get recent pattern types."""
        if not analysis.recent_patterns:
            return []
        
        # Map internal pattern names to PatternType enum
        pattern_map = {
            "le_candle": PatternType.LE_CANDLE,
            "small_wick": PatternType.SMALL_WICK,
            "steeper_wick": PatternType.STEEPER_WICK,
            "celery": PatternType.CELERY,
            "engulfing": PatternType.ENGULFING,
            "inside_bar": PatternType.INSIDE_BAR,
            "outside_bar": PatternType.OUTSIDE_BAR,
            "pinbar": PatternType.PINBAR,
            "hammer": PatternType.HAMMER,
            "shooting_star": PatternType.SHOOTING_STAR,
        }
        
        patterns = []
        for pattern in analysis.recent_patterns[-5:]:  # Last 5 patterns
            # Try to map pattern name
            pattern_name = pattern.pattern_name.lower().replace(" ", "_")
            if pattern_name in pattern_map:
                patterns.append(pattern_map[pattern_name])
        
        return patterns or [PatternType.ENGULFING]  # Default if can't map
    
    def _get_higher_tf_bias(
        self,
        analyses: Dict[str, TimeframeAnalysis],
        analysis_tf: str,
        signal_type: SignalType,
    ) -> SignalType:
        """Determine higher timeframe bias."""
        from app.core.market.data import get_timeframe_minutes
        
        analysis_minutes = get_timeframe_minutes(analysis_tf)
        
        # Find highest timeframe
        higher_tfs = [
            (tf, analysis) for tf, analysis in analyses.items()
            if get_timeframe_minutes(tf) > analysis_minutes
        ]
        
        if not higher_tfs:
            return signal_type  # No higher TF, use signal direction
        
        # Get signal from highest timeframe
        highest_tf, highest_analysis = max(
            higher_tfs,
            key=lambda x: get_timeframe_minutes(x[0])
        )
        
        sig, _ = highest_analysis.get_pattern_signal_score()
        
        if sig == PatternSignal.BULLISH:
            return SignalType.LONG
        elif sig == PatternSignal.BEARISH:
            return SignalType.SHORT
        else:
            return signal_type
    
    def _build_signal_reasoning(
        self,
        confluence: ConfluenceScore,
        levels: TradeLevels,
        validation: SignalValidationResult,
        setup_type: SetupType,
    ) -> str:
        """Build human-readable reasoning for the signal."""
        lines = []
        
        lines.append(
            f"Confluence score: {confluence.overall_score:.1f}/100 "
            f"({confluence.signal.value})"
        )
        
        lines.append(
            f"Timeframe agreement: {confluence.agreement_percentage:.1f}% "
            f"(dominant: {confluence.dominant_timeframe})"
        )
        
        lines.append(f"Setup type: {setup_type.value}")
        
        lines.append(f"Entry: {levels.entry_reason}")
        lines.append(f"Stop: {levels.stop_reason}")
        
        for reason in levels.tp_reasons:
            lines.append(reason)
        
        lines.append(
            f"Risk-Reward: {float(levels.risk_reward_ratio):.2f}:1"
        )
        
        if validation.warnings:
            lines.append("Warnings:")
            for warning in validation.warnings:
                lines.append(f"  - {warning}")
        
        return " | ".join(lines)


def generate_signal(
    mtf_data: Dict[str, List[Candle]],
    analysis_timeframe: str,
    symbol: str,
    config: Optional[SignalGenerationConfig] = None,
) -> Optional[Signal]:
    """Convenience function to generate a signal.
    
    Args:
        mtf_data: Multi-timeframe candle data
        analysis_timeframe: Primary analysis timeframe
        symbol: Trading symbol
        config: Optional configuration
        
    Returns:
        Signal if valid setup found, None otherwise
        
    Example:
        >>> from app.core.patterns.signals import generate_signal
        >>> mtf_data = {"5m": candles_5m, "15m": candles_15m, "1h": candles_1h}
        >>> signal = generate_signal(mtf_data, "15m", "BTC-USD")
        >>> if signal:
        ...     print(f"{signal.signal_type} @ {signal.entry_price}")
    """
    generator = SignalGenerator(config=config)
    return generator.generate_signal(mtf_data, analysis_timeframe, symbol)
