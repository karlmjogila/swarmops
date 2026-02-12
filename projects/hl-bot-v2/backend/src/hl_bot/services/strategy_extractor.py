"""Strategy extraction from educational content using LLM.

Converts unstructured text/video/PDF content into structured StrategyRule objects.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

from hl_bot.services.llm_client import LLMClient
from hl_bot.types import (
    Condition,
    ExitRules,
    ExtractedStrategy,
    MarketPhase,
    RiskParams,
    Source,
    StrategyRule,
    Timeframe,
)
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class PromptManager:
    """Manage and version prompts for strategy extraction."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt templates (optional)
        """
        self._dir = prompts_dir
        self._cache: dict[str, str] = {}

    def get(self, name: str, **kwargs: Any) -> str:
        """Load a prompt template and render with variables.

        Args:
            name: Prompt template name
            **kwargs: Variables to substitute in template

        Returns:
            Rendered prompt
        """
        # Try to load from file first
        if self._dir and name not in self._cache:
            path = self._dir / f"{name}.txt"
            if path.exists():
                self._cache[name] = path.read_text()

        # Use inline defaults if file doesn't exist
        if name not in self._cache:
            self._cache[name] = self._get_default_prompt(name)

        template = Template(self._cache[name])
        return template.safe_substitute(**kwargs)

    def _get_default_prompt(self, name: str) -> str:
        """Get default inline prompt if file doesn't exist."""
        if name == "extract_strategy":
            return self._EXTRACT_STRATEGY_PROMPT
        elif name == "analyze_chart_image":
            return self._ANALYZE_CHART_PROMPT
        else:
            raise ValueError(f"Unknown prompt: {name}")

    # Default prompts (can be overridden by files)
    _EXTRACT_STRATEGY_PROMPT = """You are an expert trading strategy analyst. Extract structured trading rules from the provided content.

## Your Task
Analyze the following trading content and extract ALL trading strategies mentioned. For each strategy, identify:
1. Strategy name and clear description
2. Timeframes used
3. Market conditions (drive/range/liquidity phase)
4. Entry conditions (be specific and structured)
5. Exit rules (take profits, stop loss, breakeven management)
6. Risk management parameters

## Format Requirements
Return a JSON array of strategies. Each strategy must follow this structure:
{
  "name": "Strategy Name",
  "description": "Clear description of what this strategy does",
  "timeframes": ["5m", "15m"],
  "market_phase": "drive" | "range" | "liquidity",
  "entry_conditions": [
    {
      "field": "pattern_type",
      "operator": "eq",
      "value": "le_candle",
      "description": "Look for LE candle pattern"
    }
  ],
  "exit_rules": {
    "tp1_percent": 1.0,
    "tp1_position_percent": 0.5,
    "tp2_percent": 2.0,
    "tp3_percent": 3.0,
    "move_to_breakeven_at": 1.0,
    "trailing_stop": false,
    "trailing_stop_trigger": null
  },
  "risk_params": {
    "risk_percent": 0.01,
    "max_positions": 3,
    "max_correlation": 0.7,
    "max_daily_loss": 0.05
  }
}

## Entry Condition Operators
- eq: equals
- ne: not equals
- gt: greater than
- gte: greater than or equal
- lt: less than
- lte: less than or equal
- in: value in list
- contains: string contains

## Common Fields for Entry Conditions
- pattern_type: Pattern detected (le_candle, small_wick, celery, etc.)
- market_phase: Current market phase
- zone_type: Zone type (support, resistance, demand, supply)
- structure_type: Structure element (bos, choch, fvg, order_block)
- confluence_score: Multi-timeframe score (0-100)
- timeframe: Specific timeframe requirement

## Guidelines
- Be precise: Extract exact rules, not vague concepts
- Be complete: Include all mentioned strategies
- Be conservative: If risk parameters aren't specified, use safe defaults (1% risk, max 3 positions)
- Be structured: Convert narrative descriptions into field/operator/value conditions
- Be realistic: Timeframes should be valid (5m, 15m, 30m, 1h, 4h, 1d)

## Content to Analyze
$content

## Important
- Return ONLY the JSON array, no additional text
- If no clear strategies found, return empty array: []
- Each strategy must be complete and actionable
"""

    _ANALYZE_CHART_PROMPT = """You are an expert chart analyst. Analyze this trading chart image and extract visible patterns and setup information.

## Your Task
Identify:
1. Visible patterns (candle patterns, market structure)
2. Support and resistance levels
3. Trend direction
4. Any annotations or markings that indicate trading setups
5. Timeframe if visible

## Format
Provide a clear, structured description that can be used to enhance strategy extraction.

Focus on:
- What patterns are present
- Where are the key levels
- What is the context (drive, range, liquidity grab)
- Any visible entry/exit markers
"""


class StrategyExtractorOutput(BaseModel):
    """Intermediate model for LLM output validation."""

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    timeframes: list[str] = Field(..., min_length=1)
    market_phase: str
    entry_conditions: list[dict[str, Any]] = Field(..., min_length=1)
    exit_rules: dict[str, Any]
    risk_params: dict[str, Any]


class StrategyExtractor:
    """Extract trading strategies from raw content using LLM."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompts_dir: Path | None = None,
    ):
        """Initialize strategy extractor.

        Args:
            llm_client: LLM client instance (creates default if not provided)
            prompts_dir: Directory for prompt templates
        """
        self._llm = llm_client or LLMClient()
        self._prompts = PromptManager(prompts_dir)
        logger.info("Strategy extractor initialized")

    async def extract_from_text(
        self,
        content: str,
        source_type: str,
        source_id: str,
        model: str = LLMClient.MODEL_SONNET,
    ) -> list[ExtractedStrategy]:
        """Extract strategies from text content.

        Args:
            content: Raw text content (transcript, PDF text, etc.)
            source_type: Type of source ("youtube", "pdf", "manual")
            source_id: Source identifier (URL, filename, etc.)
            model: LLM model to use

        Returns:
            List of extracted strategies

        Raises:
            ValueError: If extraction fails or produces invalid output
        """
        logger.info(f"Extracting strategies from {source_type} source: {source_id}")

        # Truncate if needed (leave room for system prompt + response)
        max_content_tokens = 80000  # Conservative limit for context window
        if self._llm.estimate_tokens(content) > max_content_tokens:
            logger.warning(f"Content too long, truncating to {max_content_tokens} tokens")
            content = self._llm.truncate_to_fit(content, max_content_tokens, strategy="middle")

        # Get extraction prompt
        prompt = self._prompts.get("extract_strategy", content=content)

        try:
            # Call LLM with unstructured output (array of strategies)
            response = await self._llm.generate(
                system="You are a trading strategy extraction expert. Extract structured rules from trading content.",
                user_message=prompt,
                model=model,
                max_tokens=8000,
                temperature=0.0,
            )

            # Parse the JSON response
            strategies = self._parse_strategies_response(response, source_type, source_id)

            logger.info(f"Successfully extracted {len(strategies)} strategies")
            return strategies

        except Exception as e:
            logger.error(f"Strategy extraction failed: {e}")
            raise ValueError(f"Failed to extract strategies: {e}")

    async def extract_from_images(
        self,
        image_urls: list[str],
        context_text: str = "",
        source_type: str = "youtube",
        source_id: str = "",
        model: str = LLMClient.MODEL_SONNET,
    ) -> list[ExtractedStrategy]:
        """Extract strategies from chart images.

        Args:
            image_urls: List of chart image URLs
            context_text: Optional text context from video/document
            source_type: Type of source
            source_id: Source identifier
            model: LLM model to use

        Returns:
            List of extracted strategies
        """
        logger.info(f"Analyzing {len(image_urls)} chart images")

        # Analyze each image
        image_analyses = []
        for i, url in enumerate(image_urls):
            try:
                prompt = self._prompts.get("analyze_chart_image")
                analysis = await self._llm.analyze_image(
                    system="You are a trading chart analysis expert.",
                    user_message=prompt,
                    image_url=url,
                    model=model,
                )
                image_analyses.append(f"[Image {i+1} Analysis]\n{analysis}\n")
                logger.debug(f"Analyzed image {i+1}/{len(image_urls)}")
            except Exception as e:
                logger.warning(f"Failed to analyze image {i+1}: {e}")

        # Combine image analyses with context text
        combined_content = context_text + "\n\n" + "\n\n".join(image_analyses)

        # Extract strategies from combined content
        return await self.extract_from_text(combined_content, source_type, source_id, model)

    def _parse_strategies_response(
        self, response: str, source_type: str, source_id: str
    ) -> list[ExtractedStrategy]:
        """Parse LLM response into validated strategy objects.

        Args:
            response: Raw LLM response (JSON array)
            source_type: Source type for metadata
            source_id: Source ID for metadata

        Returns:
            List of validated ExtractedStrategy objects

        Raises:
            ValueError: If parsing or validation fails
        """
        import json

        # Clean response - extract JSON array
        response = response.strip()

        # Handle markdown code blocks
        if response.startswith("```"):
            response = re.sub(r"```(?:json)?\n?", "", response)

        try:
            strategies_data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response[:500]}")
            raise ValueError(f"Invalid JSON response: {e}")

        if not isinstance(strategies_data, list):
            raise ValueError("Expected JSON array of strategies")

        extracted_strategies = []

        for i, strategy_data in enumerate(strategies_data):
            try:
                # Validate intermediate structure
                intermediate = StrategyExtractorOutput(**strategy_data)

                # Convert to full StrategyRule
                strategy_rule = self._convert_to_strategy_rule(
                    intermediate, source_type, source_id
                )

                # Calculate confidence based on completeness
                confidence = self._calculate_confidence(intermediate)

                extracted = ExtractedStrategy(
                    rule=strategy_rule,
                    raw_text=json.dumps(strategy_data, indent=2),
                    images_analyzed=[],  # Populated externally if images were used
                    confidence=confidence,
                )

                extracted_strategies.append(extracted)
                logger.debug(f"Validated strategy {i+1}: {strategy_rule.name}")

            except ValidationError as e:
                logger.warning(f"Skipping invalid strategy {i+1}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Failed to process strategy {i+1}: {e}")
                continue

        return extracted_strategies

    def _convert_to_strategy_rule(
        self, intermediate: StrategyExtractorOutput, source_type: str, source_id: str
    ) -> StrategyRule:
        """Convert intermediate output to full StrategyRule.

        Args:
            intermediate: Validated intermediate output
            source_type: Source type
            source_id: Source identifier

        Returns:
            Validated StrategyRule
        """
        # Parse timeframes
        timeframes = []
        for tf_str in intermediate.timeframes:
            try:
                timeframes.append(Timeframe(tf_str))
            except ValueError:
                logger.warning(f"Invalid timeframe '{tf_str}', skipping")

        if not timeframes:
            raise ValueError("No valid timeframes specified")

        # Parse market phase
        try:
            market_phase = MarketPhase(intermediate.market_phase)
        except ValueError:
            logger.warning(
                f"Invalid market phase '{intermediate.market_phase}', defaulting to 'drive'"
            )
            market_phase = MarketPhase.DRIVE

        # Convert entry conditions
        conditions = []
        for cond_data in intermediate.entry_conditions:
            try:
                condition = Condition(**cond_data)
                conditions.append(condition)
            except ValidationError as e:
                logger.warning(f"Invalid entry condition: {e}")

        if not conditions:
            raise ValueError("No valid entry conditions")

        # Build objects
        exit_rules = ExitRules(**intermediate.exit_rules)
        risk_params = RiskParams(**intermediate.risk_params)
        source = Source(
            source_type=source_type,  # type: ignore
            source_id=source_id,
            extracted_at=datetime.now(timezone.utc),
            confidence=0.8,  # Will be updated by confidence calculation
        )

        strategy_id = str(uuid.uuid4())

        return StrategyRule(
            id=strategy_id,
            name=intermediate.name,
            description=intermediate.description,
            timeframes=timeframes,
            market_phase=market_phase,
            entry_conditions=conditions,
            exit_rules=exit_rules,
            risk_params=risk_params,
            source=source,
        )

    def _calculate_confidence(self, strategy: StrategyExtractorOutput) -> float:
        """Calculate confidence score based on strategy completeness.

        Args:
            strategy: Intermediate strategy output

        Returns:
            Confidence score 0.0-1.0
        """
        score = 0.0

        # Name and description quality
        if len(strategy.name) > 5:
            score += 0.1
        if len(strategy.description) > 20:
            score += 0.1

        # Timeframes specified
        if len(strategy.timeframes) >= 2:
            score += 0.15
        elif len(strategy.timeframes) == 1:
            score += 0.1

        # Entry conditions detail
        if len(strategy.entry_conditions) >= 3:
            score += 0.2
        elif len(strategy.entry_conditions) >= 2:
            score += 0.15
        else:
            score += 0.1

        # Exit rules completeness
        exit_keys = [
            "tp1_percent",
            "tp2_percent",
            "move_to_breakeven_at",
        ]
        if all(k in strategy.exit_rules for k in exit_keys):
            score += 0.15

        # Risk params specified
        risk_keys = ["risk_percent", "max_positions", "max_daily_loss"]
        if all(k in strategy.risk_params for k in risk_keys):
            score += 0.15

        # Market phase specificity
        if strategy.market_phase in ["drive", "range", "liquidity"]:
            score += 0.15

        return min(score, 1.0)
