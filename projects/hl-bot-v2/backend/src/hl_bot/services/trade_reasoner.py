"""Trade reasoning LLM component.

Provides intelligent analysis of trade setups, risk assessment, and post-trade learning.
Uses Claude for reasoning while maintaining safety through validation and guardrails.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

from hl_bot.services.llm_client import LLMClient
from hl_bot.types import (
    Candle,
    ConfluenceScore,
    MarketPhase,
    PatternType,
    Signal,
    SignalType,
    Trade,
    TradeStatus,
)
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# Response Models for Structured LLM Output
# ============================================================================


class RiskAssessment(BaseModel):
    """Risk assessment for a trade setup."""

    risk_level: str = Field(..., pattern=r"^(low|medium|high)$")
    concerns: list[str] = Field(..., description="List of identified risks")
    probability_estimate: float = Field(..., ge=0, le=1, description="Win probability 0-1")
    position_size_recommendation: str = Field(
        ..., description="Position sizing advice (e.g., 'full', 'half', 'skip')"
    )
    key_invalidation_levels: list[float] = Field(
        ..., description="Price levels that invalidate the setup"
    )


class SetupAnalysis(BaseModel):
    """Complete setup analysis including reasoning and risk."""

    reasoning: str = Field(..., min_length=50, description="Why this trade makes sense")
    confluence_explanation: str = Field(
        ..., min_length=50, description="Multi-timeframe alignment breakdown"
    )
    risk_assessment: RiskAssessment
    key_observations: list[str] = Field(..., min_length=1)
    market_context: str = Field(..., min_length=20, description="Current market phase context")


class OutcomeAnalysis(BaseModel):
    """Post-trade outcome analysis."""

    what_happened: str = Field(..., min_length=50, description="Trade execution summary")
    what_worked: list[str] = Field(..., description="Aspects that went right")
    what_didnt_work: list[str] = Field(..., description="Aspects that went wrong")
    lessons_learned: list[str] = Field(..., min_length=1)
    setup_validity: str = Field(
        ..., pattern=r"^(valid|invalid|edge_case)$", description="Was the setup valid?"
    )
    performance_rating: int = Field(..., ge=1, le=5, description="Execution quality 1-5")


class LearningInsight(BaseModel):
    """Aggregated learning insight."""

    insight_type: str = Field(
        ..., pattern=r"^(pattern|setup|market_phase|risk|execution)$"
    )
    insight: str = Field(..., min_length=30, description="The learning/insight")
    confidence_score: float = Field(..., ge=0, le=1)
    sample_size: int = Field(..., ge=1, description="Number of trades supporting this")
    market_conditions: dict[str, Any] = Field(
        default_factory=dict, description="Context where this applies"
    )


# ============================================================================
# Prompt Management
# ============================================================================


class ReasonerPromptManager:
    """Manage prompts for trade reasoning."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize prompt manager.

        Args:
            prompts_dir: Optional directory for custom prompt templates
        """
        self._dir = prompts_dir
        self._cache: dict[str, str] = {}

    def get(self, name: str, **kwargs: Any) -> str:
        """Load and render a prompt template.

        Args:
            name: Prompt name
            **kwargs: Variables for template substitution

        Returns:
            Rendered prompt
        """
        if self._dir and name not in self._cache:
            path = self._dir / f"{name}.txt"
            if path.exists():
                self._cache[name] = path.read_text()

        if name not in self._cache:
            self._cache[name] = self._get_default_prompt(name)

        template = Template(self._cache[name])
        return template.safe_substitute(**kwargs)

    def _get_default_prompt(self, name: str) -> str:
        """Get default inline prompt."""
        if name == "analyze_setup":
            return self._ANALYZE_SETUP_PROMPT
        elif name == "review_outcome":
            return self._REVIEW_OUTCOME_PROMPT
        elif name == "aggregate_learnings":
            return self._AGGREGATE_LEARNINGS_PROMPT
        else:
            raise ValueError(f"Unknown prompt: {name}")

    _ANALYZE_SETUP_PROMPT = """You are an expert trading analyst with deep knowledge of price action, market structure, and risk management.

## Trading Strategy Framework

You follow these core setups from the ControllerFX Playbook:

**BREAKOUT:** Price closes outside range → trade continuation
- Entry: Buy/Sell Stop at candle high/low after close outside range
- SL: Previous candle low (long) / high (short)
- TP: Next S/R level

**FAKEOUT:** Price breaks out but closes BACK into range → trade reversal
- Entry: Buy/Sell Stop after price returns into range
- SL: Beyond the fakeout wick
- TP: Opposite side of range

**ONION:** Price consolidates, respects one side of range → trade to opposite
- Entry: Buy/Sell Stop at range boundary after bullish close at support (or bearish at resistance)
- SL: Beyond the respected level
- TP: Opposite side of range

**Entry Modifiers:**
- Small Wick: Tighter SL, standard entry
- Steeper Wick: Wider SL at wick extreme, stronger rejection signal
- Celery Play: Wait for confirming wick before placing stop order

**Validation:** Higher TF bias must align. Minimum 2:1 R:R. Full confluence = full position.

## Your Task
Analyze the following trade setup and provide comprehensive reasoning, confluence breakdown, and risk assessment.

## Setup Details
**Symbol:** $symbol
**Timeframe:** $timeframe
**Signal Type:** $signal_type
**Entry Price:** $entry_price
**Stop Loss:** $stop_loss
**Take Profit 1:** $tp1
**Take Profit 2:** $tp2
**Take Profit 3:** $tp3

## Market Context
**Current Phase:** $market_phase
**Higher Timeframe Bias:** $htf_bias
**Confluence Score:** $confluence_score/100

## Detected Patterns
$patterns

## Setup Type
$setup_type

## Recent Price Action
$recent_candles

## Analysis Requirements

### 1. Reasoning
Explain WHY this trade makes sense. Consider:
- Pattern validity and context
- Market structure alignment
- Risk/reward profile
- Timing and entry quality

### 2. Confluence Explanation
Break down the multi-timeframe alignment:
- What timeframes are confirming?
- How do patterns align across timeframes?
- Structural elements supporting the trade

### 3. Risk Assessment
Evaluate:
- Overall risk level (low/medium/high)
- Specific concerns or red flags
- Win probability estimate (be realistic)
- Position sizing recommendation
- Key invalidation price levels

### 4. Key Observations
List 3-5 critical observations about this setup.

### 5. Market Context
Describe the current market phase and how this setup fits within it.

## Critical Guidelines
- Be honest: Flag concerns even if the setup looks good
- Be specific: Cite actual price levels and patterns
- Be practical: Focus on actionable insights
- Be conservative: Better to miss a trade than take a bad one
- Don't hallucinate: Base analysis ONLY on provided data
"""

    _REVIEW_OUTCOME_PROMPT = """You are a trading performance analyst reviewing a closed trade.

## Trade Details
**Symbol:** $symbol
**Signal Type:** $signal_type
**Entry Price:** $entry_price (at $entry_time)
**Exit Price:** $exit_price (at $exit_time)
**Stop Loss:** $stop_loss
**Take Profits:** $take_profits

**Position Size:** $position_size
**P&L:** $pnl ($pnl_percent%)
**Status:** $status

**Max Adverse Excursion:** $mae
**Max Favorable Excursion:** $mfe

## Pre-Trade Analysis
**Entry Reasoning:** $entry_reasoning
**Risk Assessment:** $risk_assessment

## Market Context
**Setup Type:** $setup_type
**Market Phase:** $market_phase
**Patterns Detected:** $patterns
**Confluence Score:** $confluence_score/100

## Recent Price Action (at entry)
$entry_candles

## Price Action (during trade)
$trade_candles

## Analysis Requirements

### 1. What Happened
Provide a clear summary of how the trade unfolded.

### 2. What Worked
List aspects that went RIGHT:
- Did the pattern play out as expected?
- Was the entry timing good?
- Did risk management work?
- What about the analysis was accurate?

### 3. What Didn't Work
List aspects that went WRONG or could improve:
- Did something unexpected happen?
- Was the setup actually valid?
- Were there warning signs we missed?
- Could we have managed better?

### 4. Lessons Learned
Extract 2-4 key takeaways from this trade.

### 5. Setup Validity
Classify: valid | invalid | edge_case
- Valid: Setup was good, outcome expected (win or loss within plan)
- Invalid: Setup was flawed from the start
- Edge case: Unusual circumstances, outlier behavior

### 6. Performance Rating (1-5)
Rate the quality of trade execution:
- 5: Perfect execution, followed plan, optimal management
- 4: Good execution, minor improvements possible
- 3: Acceptable execution, several improvements needed
- 2: Poor execution, major mistakes made
- 1: Terrible execution, ignored plan or rules

## Critical Guidelines
- Be objective: Don't blame the market, assess the analysis
- Be specific: Reference actual price action and decisions
- Be actionable: Focus on learnings we can apply
- Be honest: Acknowledge both good and bad aspects
- Separate luck from skill: Did we win/lose for the right reasons?
"""

    _AGGREGATE_LEARNINGS_PROMPT = """You are a trading pattern analyst aggregating insights from multiple trades.

## Your Task
Analyze the following trade outcomes and extract meaningful insights that can improve future trading.

## Trade Summary
$trade_summaries

## Analysis Requirements

Generate 1-3 high-confidence insights based on this data. For each insight:

### 1. Insight Type
Classify as: pattern | setup | market_phase | risk | execution

### 2. Insight
A clear, actionable statement about what we've learned.

Examples:
- "LE candle setups in range-bound markets have 65% win rate vs 45% in drive phases"
- "Trades taken within first hour of session show higher adverse excursion"
- "Setups with confluence score >75 and HTF bias alignment have 2.1x win rate"

### 3. Confidence Score (0-1)
How confident are we in this insight based on sample size and consistency?

### 4. Sample Size
Number of trades supporting this insight.

### 5. Market Conditions
When does this insight apply? (timeframe, phase, conditions)

## Critical Guidelines
- Minimum 3 trades required for any insight
- Look for patterns, not random noise
- Be specific about conditions
- Higher sample size = higher confidence
- Consider both winners and losers
- Focus on reproducible patterns
"""


# ============================================================================
# Trade Reasoner Service
# ============================================================================


class TradeReasoner:
    """LLM-powered trade reasoning and learning system."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompts_dir: Path | None = None,
        model: str = LLMClient.MODEL_SONNET,
    ):
        """Initialize trade reasoner.

        Args:
            llm_client: LLM client instance (creates default if not provided)
            prompts_dir: Optional directory for custom prompt templates
            model: LLM model to use (default: Sonnet for balanced speed/quality)
        """
        self._llm = llm_client or LLMClient()
        self._prompts = ReasonerPromptManager(prompts_dir)
        self._model = model
        logger.info(f"Trade reasoner initialized with model: {model}")

    async def analyze_setup(
        self,
        signal: Signal,
        recent_candles: list[Candle],
        confluence_score: ConfluenceScore,
        additional_context: dict[str, Any] | None = None,
    ) -> SetupAnalysis:
        """Analyze a trade setup before execution.

        Args:
            signal: The trade signal to analyze
            recent_candles: Recent price action (last 20-50 candles)
            confluence_score: Multi-timeframe confluence breakdown
            additional_context: Optional additional market context

        Returns:
            Complete setup analysis with reasoning and risk assessment

        Raises:
            ValueError: If analysis fails or produces invalid output
        """
        logger.info(f"Analyzing setup: {signal.symbol} {signal.signal_type} @ {signal.entry_price}")

        # Format recent candles for prompt
        candles_text = self._format_candles(recent_candles[-20:])  # Last 20 candles

        # Build prompt context
        prompt = self._prompts.get(
            "analyze_setup",
            symbol=signal.symbol,
            timeframe=signal.timeframe.value,
            signal_type=signal.signal_type.value.upper(),
            entry_price=f"{signal.entry_price:.2f}",
            stop_loss=f"{signal.stop_loss:.2f}",
            tp1=f"{signal.take_profit_1:.2f}",
            tp2=f"{signal.take_profit_2:.2f}",
            tp3=f"{signal.take_profit_3:.2f}" if signal.take_profit_3 else "None",
            market_phase=signal.market_phase.value,
            htf_bias=signal.higher_tf_bias.value.upper(),
            confluence_score=f"{signal.confluence_score:.0f}",
            patterns=", ".join(p.value for p in signal.patterns_detected),
            setup_type=signal.setup_type.value,
            recent_candles=candles_text,
        )

        try:
            # Get structured analysis from LLM
            analysis = await self._llm.generate_structured(
                system="You are a professional trading analyst. Provide thorough, honest analysis.",
                user_message=prompt,
                response_model=SetupAnalysis,
                model=self._model,
                max_tokens=3000,
                temperature=0.1,  # Slight randomness for varied explanations
            )

            # Validate risk assessment
            self._validate_risk_assessment(analysis.risk_assessment, signal)

            logger.info(
                f"Setup analysis complete: risk={analysis.risk_assessment.risk_level}, "
                f"prob={analysis.risk_assessment.probability_estimate:.2%}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Setup analysis failed: {e}")
            raise ValueError(f"Failed to analyze setup: {e}")

    async def assess_risk(self, signal: Signal, analysis: SetupAnalysis) -> bool:
        """Quick risk assessment to filter out high-risk setups.

        Args:
            signal: Trade signal
            analysis: Setup analysis from analyze_setup()

        Returns:
            True if setup passes risk checks, False to skip

        Note:
            This is a guardrail function that applies strict filters.
            Use for automated trading where safety is critical.
        """
        risk = analysis.risk_assessment

        # Hard filters
        if risk.risk_level == "high":
            logger.warning(f"Setup rejected: high risk level - {risk.concerns}")
            return False

        if risk.probability_estimate < 0.40:
            logger.warning(f"Setup rejected: low win probability ({risk.probability_estimate:.1%})")
            return False

        if risk.position_size_recommendation == "skip":
            logger.warning(f"Setup rejected: LLM recommends skip - {risk.concerns}")
            return False

        # Signal quality checks
        if signal.confluence_score < 40:
            logger.warning(f"Setup rejected: low confluence score ({signal.confluence_score})")
            return False

        logger.info("Setup passed risk assessment filters")
        return True

    async def review_outcome(
        self,
        trade: Trade,
        entry_reasoning: str,
        entry_candles: list[Candle],
        trade_candles: list[Candle],
    ) -> OutcomeAnalysis:
        """Review a closed trade and extract learnings.

        Args:
            trade: Completed trade
            entry_reasoning: Original entry reasoning from analyze_setup()
            entry_candles: Price action at entry time
            trade_candles: Price action during the trade

        Returns:
            Detailed outcome analysis with lessons learned

        Raises:
            ValueError: If review fails or produces invalid output
        """
        logger.info(
            f"Reviewing trade outcome: {trade.symbol} {trade.side.value} "
            f"P&L: {trade.pnl_percent:.2%}"
        )

        # Format candles
        entry_candles_text = self._format_candles(entry_candles[-20:])
        trade_candles_text = self._format_candles(trade_candles)

        # Build prompt
        prompt = self._prompts.get(
            "review_outcome",
            symbol=trade.symbol,
            signal_type=trade.side.value.upper(),
            entry_price=f"{trade.entry_price:.2f}",
            entry_time=trade.entry_time.isoformat(),
            exit_price=f"{trade.exit_price:.2f}" if trade.exit_price else "None",
            exit_time=trade.exit_time.isoformat() if trade.exit_time else "None",
            stop_loss=f"{trade.stop_loss:.2f}",
            take_profits=", ".join(f"{tp:.2f}" for tp in trade.take_profits),
            position_size=f"{trade.position_size:.4f}",
            pnl=f"{trade.pnl:.2f}" if trade.pnl else "None",
            pnl_percent=f"{trade.pnl_percent:.2f}" if trade.pnl_percent else "None",
            status=trade.status.value,
            mae=f"{trade.max_adverse_excursion:.2f}" if trade.max_adverse_excursion else "None",
            mfe=f"{trade.max_favorable_excursion:.2f}" if trade.max_favorable_excursion else "None",
            entry_reasoning=entry_reasoning,
            risk_assessment="(from entry analysis)",  # Could pass full risk assessment
            setup_type="(from signal)",
            market_phase="(from signal)",
            patterns="(from signal)",
            confluence_score="(from signal)",
            entry_candles=entry_candles_text,
            trade_candles=trade_candles_text,
        )

        try:
            # Get structured outcome analysis
            outcome = await self._llm.generate_structured(
                system="You are a trading performance analyst. Be objective and honest in your analysis.",
                user_message=prompt,
                response_model=OutcomeAnalysis,
                model=self._model,
                max_tokens=3000,
                temperature=0.1,
            )

            logger.info(
                f"Outcome review complete: validity={outcome.setup_validity}, "
                f"rating={outcome.performance_rating}/5"
            )

            return outcome

        except Exception as e:
            logger.error(f"Outcome review failed: {e}")
            raise ValueError(f"Failed to review outcome: {e}")

    async def aggregate_learnings(
        self,
        trade_summaries: list[dict[str, Any]],
        min_sample_size: int = 3,
    ) -> list[LearningInsight]:
        """Aggregate insights from multiple trade outcomes.

        Args:
            trade_summaries: List of trade summary dicts with outcome data
            min_sample_size: Minimum trades required for an insight

        Returns:
            List of learning insights

        Raises:
            ValueError: If aggregation fails
        """
        if len(trade_summaries) < min_sample_size:
            logger.warning(
                f"Insufficient trades for aggregation: {len(trade_summaries)} < {min_sample_size}"
            )
            return []

        logger.info(f"Aggregating learnings from {len(trade_summaries)} trades")

        # Format trade summaries
        summaries_text = "\n\n".join(
            f"Trade {i+1}:\n" + "\n".join(f"  {k}: {v}" for k, v in summary.items())
            for i, summary in enumerate(trade_summaries)
        )

        prompt = self._prompts.get(
            "aggregate_learnings",
            trade_summaries=summaries_text,
        )

        try:
            # Get unstructured response (array of insights)
            response = await self._llm.generate(
                system="You are a trading pattern analyst. Extract meaningful, actionable insights.",
                user_message=prompt,
                model=self._model,
                max_tokens=2000,
                temperature=0.1,
            )

            # Parse insights
            insights = self._parse_insights_response(response, min_sample_size)

            logger.info(f"Generated {len(insights)} learning insights")
            return insights

        except Exception as e:
            logger.error(f"Learning aggregation failed: {e}")
            raise ValueError(f"Failed to aggregate learnings: {e}")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _format_candles(self, candles: list[Candle]) -> str:
        """Format candles for prompt context.

        Args:
            candles: List of candles to format

        Returns:
            Formatted string representation
        """
        if not candles:
            return "No candle data available"

        lines = ["Time | Open | High | Low | Close | Volume"]
        lines.append("-" * 60)

        for candle in candles:
            lines.append(
                f"{candle.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{candle.open:8.2f} | {candle.high:8.2f} | "
                f"{candle.low:8.2f} | {candle.close:8.2f} | {candle.volume:10.0f}"
            )

        return "\n".join(lines)

    def _validate_risk_assessment(self, risk: RiskAssessment, signal: Signal) -> None:
        """Validate risk assessment against signal data.

        Args:
            risk: Risk assessment from LLM
            signal: Trade signal

        Raises:
            ValueError: If risk assessment contains invalid data
        """
        # Check invalidation levels are within reasonable range
        for level in risk.key_invalidation_levels:
            if level <= 0:
                raise ValueError(f"Invalid invalidation level: {level}")

            # Should be near stop loss (within 20% deviation)
            sl_deviation = abs(level - signal.stop_loss) / signal.stop_loss
            if sl_deviation > 0.20:
                logger.warning(
                    f"Invalidation level {level} far from stop loss {signal.stop_loss} "
                    f"({sl_deviation:.1%} deviation)"
                )

        # Probability must be reasonable
        if risk.probability_estimate > 0.95:
            logger.warning("Unrealistically high win probability, capping at 0.90")
            risk.probability_estimate = 0.90

    def _parse_insights_response(
        self, response: str, min_sample_size: int
    ) -> list[LearningInsight]:
        """Parse LLM response into validated insight objects.

        Args:
            response: Raw LLM response
            min_sample_size: Minimum sample size filter

        Returns:
            List of validated insights
        """
        import json
        import re

        # Clean response
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"```(?:json)?\n?", "", response)

        try:
            insights_data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse insights JSON: {e}")
            return []

        if not isinstance(insights_data, list):
            logger.error("Expected JSON array of insights")
            return []

        validated_insights = []

        for insight_data in insights_data:
            try:
                insight = LearningInsight(**insight_data)

                # Filter by sample size
                if insight.sample_size < min_sample_size:
                    logger.debug(f"Skipping insight with small sample: {insight.sample_size}")
                    continue

                validated_insights.append(insight)

            except ValidationError as e:
                logger.warning(f"Invalid insight data: {e}")
                continue

        return validated_insights
