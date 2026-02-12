"""Utility functions for working with types and data models."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum

from . import (
    CandleData, Timeframe, OrderSide, MarketCycle, EntryType,
    StrategyRule, TradeRecord, PatternCondition, PriceActionSnapshot
)


def enum_to_dict(enum_class: type) -> Dict[str, str]:
    """Convert an enum to a dictionary for serialization."""
    if not issubclass(enum_class, Enum):
        raise ValueError("Input must be an Enum class")
    return {member.name: member.value for member in enum_class}


def get_all_timeframes() -> List[str]:
    """Get all available timeframes."""
    return [tf.value for tf in Timeframe]


def get_all_entry_types() -> List[str]:
    """Get all available entry types."""
    return [et.value for et in EntryType]


def get_all_market_cycles() -> List[str]:
    """Get all available market cycles."""
    return [mc.value for mc in MarketCycle]


def timeframe_to_minutes(timeframe: Timeframe) -> int:
    """Convert timeframe to minutes."""
    timeframe_minutes = {
        Timeframe.M1: 1,
        Timeframe.M5: 5,
        Timeframe.M15: 15,
        Timeframe.M30: 30,
        Timeframe.H1: 60,
        Timeframe.H4: 240,
        Timeframe.H12: 720,
        Timeframe.D1: 1440,
        Timeframe.W1: 10080,
    }
    return timeframe_minutes.get(timeframe, 0)


def is_higher_timeframe(tf1: Timeframe, tf2: Timeframe) -> bool:
    """Check if tf1 is a higher timeframe than tf2."""
    return timeframe_to_minutes(tf1) > timeframe_to_minutes(tf2)


def calculate_candle_metrics(candle: CandleData) -> Dict[str, float]:
    """Calculate additional metrics for a candle."""
    body_size = abs(candle.close - candle.open)
    total_range = candle.high - candle.low
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low
    
    # Avoid division by zero
    if total_range == 0:
        body_ratio = 0
        upper_wick_ratio = 0
        lower_wick_ratio = 0
    else:
        body_ratio = body_size / total_range
        upper_wick_ratio = upper_wick / total_range
        lower_wick_ratio = lower_wick / total_range
    
    return {
        "body_size": body_size,
        "total_range": total_range,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_ratio": body_ratio,
        "upper_wick_ratio": upper_wick_ratio,
        "lower_wick_ratio": lower_wick_ratio,
        "is_bullish": candle.close > candle.open,
        "is_bearish": candle.close < candle.open,
        "is_doji": body_size < (total_range * 0.1) if total_range > 0 else False,
    }


def validate_strategy_rule(rule: StrategyRule) -> List[str]:
    """Validate a strategy rule and return list of validation errors."""
    errors = []
    
    # Name validation
    if not rule.name or len(rule.name.strip()) == 0:
        errors.append("Strategy name is required")
    elif len(rule.name) > 100:
        errors.append("Strategy name must be 100 characters or less")
    
    # Conditions validation
    if not rule.conditions:
        errors.append("At least one pattern condition is required")
    else:
        for i, condition in enumerate(rule.conditions):
            if not condition.params:
                errors.append(f"Condition {i+1} must have parameters")
    
    # Confluence validation
    for i, confluence in enumerate(rule.confluence_required):
        higher_minutes = timeframe_to_minutes(confluence.higher_tf)
        lower_minutes = timeframe_to_minutes(confluence.lower_tf)
        if higher_minutes <= lower_minutes:
            errors.append(f"Confluence {i+1}: higher timeframe must be greater than lower timeframe")
        
        if confluence.required_confluence < 0 or confluence.required_confluence > 1:
            errors.append(f"Confluence {i+1}: required confidence must be between 0 and 1")
    
    # Risk parameters validation
    if rule.risk_params.risk_percent <= 0 or rule.risk_params.risk_percent > 10:
        errors.append("Risk percentage must be between 0 and 10")
    
    if not rule.risk_params.tp_levels:
        errors.append("At least one take profit level is required")
    elif any(tp <= 0 for tp in rule.risk_params.tp_levels):
        errors.append("All take profit levels must be positive")
    elif rule.risk_params.tp_levels != sorted(rule.risk_params.tp_levels):
        errors.append("Take profit levels must be in ascending order")
    
    return errors


def calculate_trade_pnl(trade: TradeRecord) -> Dict[str, float]:
    """Calculate P&L metrics for a trade."""
    if not trade.exit_price:
        return {"pnl_absolute": 0.0, "pnl_percentage": 0.0, "r_multiple": 0.0}
    
    # Calculate absolute P&L
    if trade.direction == OrderSide.LONG:
        pnl_absolute = (trade.exit_price - trade.entry_price) * trade.quantity
    else:  # SHORT
        pnl_absolute = (trade.entry_price - trade.exit_price) * trade.quantity
    
    # Calculate percentage P&L
    pnl_percentage = (pnl_absolute / (trade.entry_price * trade.quantity)) * 100
    
    # Calculate R multiple (requires stop loss distance)
    r_multiple = 0.0
    if trade.initial_stop_loss:
        if trade.direction == OrderSide.LONG:
            risk_per_share = trade.entry_price - trade.initial_stop_loss
        else:  # SHORT
            risk_per_share = trade.initial_stop_loss - trade.entry_price
        
        total_risk = risk_per_share * trade.quantity
        if total_risk > 0:
            r_multiple = pnl_absolute / total_risk
    
    return {
        "pnl_absolute": pnl_absolute,
        "pnl_percentage": pnl_percentage,
        "r_multiple": r_multiple,
    }


def create_price_action_snapshot(
    timeframes: Dict[str, List[CandleData]],
    structure_notes: Optional[List[str]] = None,
    zone_interactions: Optional[List[str]] = None,
    market_cycle: Optional[MarketCycle] = None,
    confluence_score: float = 0.0
) -> PriceActionSnapshot:
    """Helper to create a price action snapshot."""
    return PriceActionSnapshot(
        timestamp=datetime.now(timezone.utc),
        timeframes=timeframes,
        structure_notes=structure_notes or [],
        zone_interactions=zone_interactions or [],
        market_cycle=market_cycle,
        confluence_score=confluence_score,
    )


def get_pattern_condition_template(pattern_type: EntryType, timeframe: Timeframe) -> PatternCondition:
    """Get a template pattern condition with default parameters."""
    templates = {
        EntryType.LE: {
            "wickRatio": ">2.0",
            "closePosition": "upper_third",
            "minBodySize": "0.3",
            "prevCandleConfirmation": True,
        },
        EntryType.SMALL_WICK: {
            "maxWickRatio": "0.3",
            "minBodySize": "0.7",
            "closePosition": "upper_half",
        },
        EntryType.STEEPER_WICK: {
            "wickAngle": ">45",
            "wickRatio": ">1.5",
            "previousWickComparison": True,
        },
        EntryType.CELERY: {
            "rangePosition": "extreme",
            "volumeConfirmation": True,
            "structureBreak": "required",
        },
        EntryType.BREAKOUT: {
            "volumeIncrease": ">150%",
            "closeBeyondLevel": True,
            "retestOptional": False,
        },
        EntryType.FAKEOUT: {
            "initialBreak": "required",
            "falseBreakTime": "<4h",
            "reverseDirection": True,
        },
        EntryType.ONION: {
            "extremePosition": "required",
            "rangeAge": ">24h",
            "volumeDrying": True,
        },
    }
    
    params = templates.get(pattern_type, {})
    
    return PatternCondition(
        type=PatternType.CANDLE,  # Default to candle pattern
        timeframe=timeframe,
        params=params,
        description=f"Default {pattern_type.value} pattern on {timeframe.value}",
    )


def serialize_for_api(obj: Any) -> Dict[str, Any]:
    """Serialize a dataclass object for API responses."""
    if hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, list):
                result[key] = [serialize_for_api(item) if hasattr(item, '__dict__') else item for item in value]
            elif isinstance(value, dict):
                result[key] = {k: serialize_for_api(v) if hasattr(v, '__dict__') else v for k, v in value.items()}
            elif hasattr(value, '__dict__'):
                result[key] = serialize_for_api(value)
            else:
                result[key] = value
        return result
    else:
        return obj


__all__ = [
    "enum_to_dict",
    "get_all_timeframes",
    "get_all_entry_types",
    "get_all_market_cycles",
    "timeframe_to_minutes",
    "is_higher_timeframe",
    "calculate_candle_metrics",
    "validate_strategy_rule",
    "calculate_trade_pnl",
    "create_price_action_snapshot",
    "get_pattern_condition_template",
    "serialize_for_api",
]