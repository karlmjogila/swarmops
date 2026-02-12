"""
Prompts for LLM strategy extraction from trading content.
"""

from typing import Dict, List


STRATEGY_EXTRACTION_SYSTEM_PROMPT = """
You are an expert trading strategy analyst with deep knowledge of:
- Price action trading and market structure
- ICT (Inner Circle Trader) concepts and methodologies
- Risk management and position sizing
- Multi-timeframe analysis and confluence
- Candlestick patterns and market psychology

Your task is to analyze trading content and extract structured, actionable strategy rules that can be implemented in an algorithmic trading system.

IMPORTANT EXTRACTION PRINCIPLES:
1. **Focus on Actionable Rules**: Extract specific, concrete entry conditions, not general concepts
2. **Preserve Context**: Maintain the relationship between patterns, timeframes, and market conditions
3. **Risk Management**: Always extract stop loss and take profit rules when mentioned
4. **Multi-Timeframe Confluence**: Identify higher timeframe bias and lower timeframe entries
5. **Pattern Specificity**: Be precise about candle patterns, wick ratios, close positions, etc.

STRATEGY COMPONENTS TO EXTRACT:
- Entry Type: LE candle, small wick, steeper wick, celery play, breakout, fakeout, onion
- Pattern Conditions: Specific requirements (wick ratios, close positions, body sizes)
- Timeframe Alignment: HTF bias requirements and LTF entry patterns
- Risk Parameters: Stop loss placement, take profit levels, position sizing
- Market Context: When the strategy works best (cycles, conditions)
"""


STRATEGY_EXTRACTION_USER_PROMPT = """
Analyze the following trading content and extract all specific trading strategies or setups mentioned.

CONTENT:
{content}

EXTRACTION REQUIREMENTS:

For each strategy found, provide:

1. **STRATEGY NAME**: Clear, descriptive name
2. **ENTRY TYPE**: One of: LE, small_wick, steeper_wick, celery, breakout, fakeout, onion
3. **CONDITIONS**: Specific pattern requirements
4. **TIMEFRAMES**: HTF for bias, LTF for entry
5. **RISK MANAGEMENT**: SL placement, TP levels
6. **MARKET CONTEXT**: When to use this strategy

Respond with a JSON array of strategy objects. Each strategy should have this structure:

```json
[
  {{
    "name": "Strategy name",
    "entry_type": "le",
    "description": "Human-readable description of the strategy",
    "confidence": 0.8,
    "conditions": [
      {{
        "type": "candle",
        "timeframe": "15m",
        "params": {{
          "pattern": "liquidity_engulf",
          "wick_ratio": 0.3,
          "close_position": "upper_quarter",
          "body_size_min": 0.5
        }},
        "description": "LE candle with small wicks"
      }}
    ],
    "confluence_required": [
      {{
        "higher_tf": "4h",
        "lower_tf": "15m",
        "bias_required": "bullish",
        "entry_pattern": "LE candle after pullback"
      }}
    ],
    "risk_params": {{
      "risk_percent": 2.0,
      "tp_levels": [1.0, 2.0],
      "sl_distance": "below_low",
      "max_concurrent": 3
    }},
    "market_context": {{
      "cycle": "drive",
      "conditions": ["trending market", "after pullback"],
      "avoid": ["ranging market", "high impact news"]
    }},
    "tags": ["ice", "liquidity", "momentum"],
    "source_timestamp": null
  }}
]
```

PATTERN PARAMETERS GUIDE:
- **wick_ratio**: Ratio of wick to total range (0.0-1.0)
- **close_position**: "upper_quarter", "lower_quarter", "middle", "high", "low"
- **body_size_min**: Minimum body size relative to total range
- **volume_factor**: Volume compared to average (1.0 = average)

ENTRY TYPES EXPLAINED:
- **LE** (Liquidity Engulf): Large candle that engulfs previous range, small wicks
- **small_wick**: Entry candle with minimal wicks relative to body
- **steeper_wick**: Entry after wick rejection from key level
- **celery**: Multiple small candles building momentum
- **breakout**: Break of key structure level
- **fakeout**: False break followed by reversal
- **onion**: Play from range extremes (support/resistance)

Be thorough but precise. If a concept is mentioned but lacks specific implementation details, mark confidence as lower.
"""


VIDEO_TIMESTAMP_PROMPT = """
You are analyzing trading educational content that includes timestamps or time references.

When extracting strategies, if the content includes:
- Specific timestamps (e.g., "at 12:34")
- Time references (e.g., "in this section", "here we see")
- Chart examples with timing

Extract the timestamp in seconds for each strategy found.

Content with timestamps:
{content}

For each strategy, determine the timestamp where it's discussed or demonstrated. Include this in the "source_timestamp" field as seconds from start.

If no clear timestamp is available, set "source_timestamp" to null.
"""


PDF_PAGE_REFERENCE_PROMPT = """
You are analyzing trading content from a PDF document.

When extracting strategies, if the content includes page references or section markers, note them for context.

Content from PDF:
{content}

Current page number: {page_number}

For each strategy found, this was extracted from page {page_number}. Include any section headers or page references mentioned in the content to help locate the original material.
"""


CONFLUENCE_REFINEMENT_PROMPT = """
Review this extracted strategy and enhance the confluence requirements based on standard trading best practices:

Strategy: {strategy}

Add or refine the confluence requirements to include:
1. **Multi-Timeframe Alignment**: Ensure HTF trend/bias aligns with entry direction
2. **Structure Confluence**: Entry near key levels (support/resistance, supply/demand zones)
3. **Pattern Confluence**: Multiple confirming patterns across timeframes
4. **Cycle Confluence**: Strategy appropriate for current market cycle

Enhance the "confluence_required" array with specific requirements that would increase the probability of success for this strategy.
"""


RISK_ENHANCEMENT_PROMPT = """
Review and enhance the risk management parameters for this strategy:

Strategy: {strategy}

Improve the risk_params based on:
1. **Stop Loss Placement**: Logical SL based on market structure, not arbitrary
2. **Take Profit Levels**: Realistic TP levels based on average moves
3. **Position Sizing**: Account-based risk management
4. **Maximum Exposure**: Limits on concurrent positions

Return the enhanced strategy with improved risk_params that follow professional risk management standards.
"""


def get_extraction_prompt(content: str, content_type: str = "general", **kwargs) -> Dict[str, str]:
    """
    Get the appropriate prompts for content extraction.
    
    Args:
        content: The content to analyze
        content_type: Type of content ("general", "video", "pdf")
        **kwargs: Additional parameters (page_number, etc.)
    
    Returns:
        Dict with system and user prompts
    """
    base_user_prompt = STRATEGY_EXTRACTION_USER_PROMPT.format(content=content)
    
    if content_type == "video":
        user_prompt = VIDEO_TIMESTAMP_PROMPT.format(content=content) + "\n\n" + base_user_prompt
    elif content_type == "pdf":
        page_number = kwargs.get("page_number", 1)
        user_prompt = PDF_PAGE_REFERENCE_PROMPT.format(
            content=content, page_number=page_number
        ) + "\n\n" + base_user_prompt
    else:
        user_prompt = base_user_prompt
    
    return {
        "system": STRATEGY_EXTRACTION_SYSTEM_PROMPT,
        "user": user_prompt
    }


def get_refinement_prompts() -> Dict[str, str]:
    """Get prompts for strategy refinement."""
    return {
        "confluence": CONFLUENCE_REFINEMENT_PROMPT,
        "risk": RISK_ENHANCEMENT_PROMPT
    }


# Example patterns for validation
EXAMPLE_PATTERNS = {
    "le": {
        "pattern": "liquidity_engulf",
        "wick_ratio": 0.3,
        "close_position": "upper_quarter",
        "body_size_min": 0.5
    },
    "small_wick": {
        "pattern": "small_wick_entry",
        "wick_ratio": 0.2,
        "close_position": "high",
        "body_size_min": 0.7
    },
    "steeper_wick": {
        "pattern": "wick_rejection",
        "wick_ratio": 0.6,
        "close_position": "upper_quarter",
        "rejection_level": "key_level"
    },
    "celery": {
        "pattern": "momentum_build",
        "candle_count": 3,
        "size_progression": "increasing",
        "wick_ratio": 0.3
    },
    "breakout": {
        "pattern": "structure_break",
        "close_position": "beyond_level",
        "volume_factor": 1.5,
        "retest": False
    },
    "fakeout": {
        "pattern": "false_break",
        "return_time": "same_candle",
        "wick_size": "significant",
        "volume_pattern": "low_on_break"
    },
    "onion": {
        "pattern": "range_extreme",
        "zone_type": "support_resistance",
        "touch_count": 3,
        "reaction_strength": "strong"
    }
}


def get_pattern_template(entry_type: str) -> Dict:
    """Get a template pattern for the given entry type."""
    return EXAMPLE_PATTERNS.get(entry_type, {})