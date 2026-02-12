"""
LLM-powered strategy extractor for trading content.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import anthropic
from pydantic import ValidationError

from ..config import Settings, get_settings
from ..types import SourceType, EntryType, PatternType, Timeframe
from ..knowledge.models import (
    StrategyRule, ContentSource, PatternCondition, 
    TimeframeAlignment, RiskParameters
)
from .extraction_prompts import (
    get_extraction_prompt, get_refinement_prompts, get_pattern_template
)


logger = logging.getLogger(__name__)


class StrategyExtractionError(Exception):
    """Custom exception for strategy extraction errors."""
    pass


class LLMStrategyExtractor:
    """
    Uses Claude to extract structured trading strategies from content.
    """
    
    def __init__(self, settings: Settings = None):
        """
        Initialize the strategy extractor.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        
        if not self.settings.anthropic_api_key:
            raise StrategyExtractionError("Anthropic API key not configured")
        
        # Initialize Claude client
        self.client = anthropic.Anthropic(
            api_key=self.settings.anthropic_api_key,
            max_retries=3,
            timeout=60.0
        )
        
        # Extraction settings
        self.extraction_model = self.settings.claude_extraction_model
        self.max_tokens = self.settings.claude_max_tokens
        self.temperature = self.settings.claude_temperature
        
        logger.info(f"LLM Strategy Extractor initialized with model: {self.extraction_model}")
    
    async def extract_strategies(
        self, 
        content: str,
        source_type: SourceType,
        source_ref: str,
        content_metadata: Optional[Dict[str, Any]] = None
    ) -> List[StrategyRule]:
        """
        Extract trading strategies from content using Claude.
        
        Args:
            content: Text content to analyze
            source_type: Type of source (PDF, video, etc.)
            source_ref: Reference to source (file path, URL)
            content_metadata: Additional metadata (page_number, timestamp, etc.)
        
        Returns:
            List of extracted strategy rules
        """
        try:
            logger.info(f"Extracting strategies from {source_type.value} content: {source_ref}")
            
            # Get extraction prompts based on content type
            content_type_map = {
                SourceType.PDF: "pdf",
                SourceType.VIDEO: "video",
                SourceType.MANUAL: "general",
                SourceType.SYSTEM: "general"
            }
            
            prompts = get_extraction_prompt(
                content=content,
                content_type=content_type_map.get(source_type, "general"),
                **(content_metadata or {})
            )
            
            # Call Claude for strategy extraction
            raw_strategies = await self._call_claude(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"]
            )
            
            # Parse and validate extracted strategies
            strategies = await self._parse_extraction_response(
                raw_strategies, source_type, source_ref, content_metadata
            )
            
            # Enhance strategies with refinement passes
            enhanced_strategies = []
            for strategy in strategies:
                enhanced = await self._enhance_strategy(strategy)
                enhanced_strategies.append(enhanced)
            
            logger.info(f"Successfully extracted {len(enhanced_strategies)} strategies")
            return enhanced_strategies
            
        except Exception as e:
            logger.error(f"Error extracting strategies: {e}")
            raise StrategyExtractionError(f"Failed to extract strategies: {e}") from e
    
    async def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make API call to Claude.
        
        Args:
            system_prompt: System prompt for Claude
            user_prompt: User prompt with content to analyze
            
        Returns:
            Claude's response
        """
        try:
            logger.debug("Sending request to Claude API")
            
            response = self.client.messages.create(
                model=self.extraction_model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            result = response.content[0].text
            logger.debug(f"Claude response received ({len(result)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise StrategyExtractionError(f"LLM API call failed: {e}") from e
    
    async def _parse_extraction_response(
        self, 
        response: str, 
        source_type: SourceType,
        source_ref: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[StrategyRule]:
        """
        Parse Claude's response into structured StrategyRule objects.
        
        Args:
            response: Raw response from Claude
            source_type: Source type for the content
            source_ref: Source reference
            metadata: Additional metadata
            
        Returns:
            List of parsed strategy rules
        """
        try:
            # Extract JSON from response (handle markdown formatting)
            json_str = self._extract_json_from_response(response)
            
            # Parse JSON
            raw_strategies = json.loads(json_str)
            
            if not isinstance(raw_strategies, list):
                raw_strategies = [raw_strategies]
            
            strategies = []
            for i, raw_strategy in enumerate(raw_strategies):
                try:
                    strategy = await self._convert_to_strategy_rule(
                        raw_strategy, source_type, source_ref, metadata
                    )
                    strategies.append(strategy)
                except Exception as e:
                    logger.warning(f"Failed to parse strategy {i}: {e}")
                    continue
            
            return strategies
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise StrategyExtractionError(f"Invalid JSON in LLM response: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            raise StrategyExtractionError(f"Response parsing failed: {e}") from e
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON from Claude's response, handling markdown formatting.
        
        Args:
            response: Raw response text
            
        Returns:
            Clean JSON string
        """
        # Remove markdown code blocks
        response = response.strip()
        
        # Look for JSON array or object
        start_markers = ['```json', '```', '[', '{']
        end_markers = ['```', ']', '}']
        
        start_idx = 0
        end_idx = len(response)
        
        # Find start of JSON
        for marker in start_markers:
            idx = response.find(marker)
            if idx != -1:
                if marker in ['```json', '```']:
                    start_idx = idx + len(marker)
                else:
                    start_idx = idx
                break
        
        # Find end of JSON
        if start_idx > 0:
            remaining = response[start_idx:]
            for marker in end_markers:
                idx = remaining.rfind(marker)
                if idx != -1:
                    if marker == '```':
                        end_idx = start_idx + idx
                    else:
                        end_idx = start_idx + idx + len(marker)
                    break
        
        json_str = response[start_idx:end_idx].strip()
        
        # Remove any trailing markdown
        if json_str.endswith('```'):
            json_str = json_str[:-3].strip()
        
        return json_str
    
    async def _convert_to_strategy_rule(
        self,
        raw_strategy: Dict[str, Any],
        source_type: SourceType,
        source_ref: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StrategyRule:
        """
        Convert raw strategy dict to StrategyRule object.
        
        Args:
            raw_strategy: Raw strategy dictionary from Claude
            source_type: Source type
            source_ref: Source reference
            metadata: Additional metadata
            
        Returns:
            Validated StrategyRule object
        """
        try:
            # Extract basic fields
            name = raw_strategy.get("name", "Untitled Strategy")
            entry_type = EntryType(raw_strategy.get("entry_type", "le"))
            confidence = raw_strategy.get("confidence", 0.5)
            description = raw_strategy.get("description", "")
            
            # Create source
            source = ContentSource(
                type=source_type,
                ref=source_ref,
                timestamp=raw_strategy.get("source_timestamp"),
                page_number=metadata.get("page_number") if metadata else None
            )
            
            # Parse conditions
            conditions = []
            for raw_condition in raw_strategy.get("conditions", []):
                condition = self._parse_pattern_condition(raw_condition)
                conditions.append(condition)
            
            # Parse confluence requirements
            confluence_required = []
            for raw_confluence in raw_strategy.get("confluence_required", []):
                confluence = self._parse_timeframe_alignment(raw_confluence)
                confluence_required.append(confluence)
            
            # Parse risk parameters
            risk_params = self._parse_risk_parameters(
                raw_strategy.get("risk_params", {})
            )
            
            # Create strategy rule
            strategy = StrategyRule(
                name=name,
                source=source,
                entry_type=entry_type,
                conditions=conditions,
                confluence_required=confluence_required,
                risk_params=risk_params,
                confidence=confidence,
                description=description,
                tags=raw_strategy.get("tags", []),
                created_at=datetime.utcnow()
            )
            
            logger.debug(f"Converted strategy: {name}")
            return strategy
            
        except ValidationError as e:
            logger.error(f"Strategy validation failed: {e}")
            raise StrategyExtractionError(f"Invalid strategy format: {e}") from e
        except Exception as e:
            logger.error(f"Strategy conversion failed: {e}")
            raise StrategyExtractionError(f"Strategy conversion error: {e}") from e
    
    def _parse_pattern_condition(self, raw_condition: Dict[str, Any]) -> PatternCondition:
        """Parse raw condition into PatternCondition object."""
        pattern_type = PatternType(raw_condition.get("type", "candle"))
        timeframe = Timeframe(raw_condition.get("timeframe", "15m"))
        params = raw_condition.get("params", {})
        
        # Validate and enhance parameters based on pattern type
        if pattern_type == PatternType.CANDLE:
            # Ensure required candle parameters exist
            if "pattern" not in params:
                params["pattern"] = "basic_candle"
            
            # Add default values for missing parameters
            defaults = {
                "wick_ratio": 0.3,
                "close_position": "middle",
                "body_size_min": 0.3,
                "volume_factor": 1.0
            }
            for key, default_value in defaults.items():
                if key not in params:
                    params[key] = default_value
        
        return PatternCondition(
            type=pattern_type,
            timeframe=timeframe,
            params=params,
            required=raw_condition.get("required", True)
        )
    
    def _parse_timeframe_alignment(self, raw_confluence: Dict[str, Any]) -> TimeframeAlignment:
        """Parse raw confluence into TimeframeAlignment object."""
        return TimeframeAlignment(
            higher_tf=Timeframe(raw_confluence.get("higher_tf", "4h")),
            lower_tf=Timeframe(raw_confluence.get("lower_tf", "15m")),
            bias_required=raw_confluence.get("bias_required", "neutral"),
            entry_pattern=raw_confluence.get("entry_pattern", "any")
        )
    
    def _parse_risk_parameters(self, raw_risk: Dict[str, Any]) -> RiskParameters:
        """Parse raw risk parameters into RiskParameters object."""
        return RiskParameters(
            risk_percent=raw_risk.get("risk_percent", 2.0),
            tp_levels=raw_risk.get("tp_levels", [1.0, 2.0]),
            sl_distance=raw_risk.get("sl_distance", "structure"),
            max_concurrent=raw_risk.get("max_concurrent", 3)
        )
    
    async def _enhance_strategy(self, strategy: StrategyRule) -> StrategyRule:
        """
        Enhance strategy with additional refinement passes.
        
        Args:
            strategy: Base strategy rule
            
        Returns:
            Enhanced strategy rule
        """
        try:
            logger.debug(f"Enhancing strategy: {strategy.name}")
            
            # Convert to dict for refinement
            strategy_dict = {
                "name": strategy.name,
                "entry_type": strategy.entry_type.value,
                "conditions": [
                    {
                        "type": c.type.value,
                        "timeframe": c.timeframe.value,
                        "params": c.params
                    } for c in strategy.conditions
                ],
                "confluence_required": [
                    {
                        "higher_tf": ta.higher_tf.value,
                        "lower_tf": ta.lower_tf.value,
                        "bias_required": ta.bias_required,
                        "entry_pattern": ta.entry_pattern
                    } for ta in strategy.confluence_required
                ],
                "risk_params": {
                    "risk_percent": strategy.risk_params.risk_percent,
                    "tp_levels": strategy.risk_params.tp_levels,
                    "sl_distance": strategy.risk_params.sl_distance,
                    "max_concurrent": strategy.risk_params.max_concurrent
                }
            }
            
            # Get refinement prompts
            refinement_prompts = get_refinement_prompts()
            
            # Enhance confluence if needed
            if len(strategy.confluence_required) < 2:  # Add more confluence
                confluence_prompt = refinement_prompts["confluence"].format(
                    strategy=json.dumps(strategy_dict, indent=2)
                )
                enhanced_confluence = await self._call_claude(
                    system_prompt="You are a trading strategy analyst. Enhance the confluence requirements.",
                    user_prompt=confluence_prompt
                )
                # Parse enhanced confluence (simplified for now)
                logger.debug("Enhanced confluence requirements")
            
            # Enhance risk management
            risk_prompt = refinement_prompts["risk"].format(
                strategy=json.dumps(strategy_dict, indent=2)
            )
            enhanced_risk = await self._call_claude(
                system_prompt="You are a risk management expert. Enhance the risk parameters.",
                user_prompt=risk_prompt
            )
            # Parse enhanced risk management (simplified for now)
            logger.debug("Enhanced risk management")
            
            # For now, return original strategy
            # TODO: Implement full refinement parsing
            return strategy
            
        except Exception as e:
            logger.warning(f"Strategy enhancement failed: {e}")
            # Return original strategy if enhancement fails
            return strategy
    
    async def extract_from_chunks(
        self,
        content_chunks: List[str],
        source_type: SourceType,
        source_ref: str,
        chunk_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[StrategyRule]:
        """
        Extract strategies from multiple content chunks.
        
        Args:
            content_chunks: List of content chunks to analyze
            source_type: Source type
            source_ref: Source reference
            chunk_metadata: Metadata for each chunk
            
        Returns:
            Combined list of extracted strategies
        """
        all_strategies = []
        
        for i, chunk in enumerate(content_chunks):
            metadata = chunk_metadata[i] if chunk_metadata and i < len(chunk_metadata) else None
            
            try:
                strategies = await self.extract_strategies(
                    content=chunk,
                    source_type=source_type,
                    source_ref=source_ref,
                    content_metadata=metadata
                )
                all_strategies.extend(strategies)
                
            except Exception as e:
                logger.warning(f"Failed to extract from chunk {i}: {e}")
                continue
        
        # Deduplicate strategies by name
        seen_names = set()
        unique_strategies = []
        for strategy in all_strategies:
            if strategy.name not in seen_names:
                seen_names.add(strategy.name)
                unique_strategies.append(strategy)
            else:
                logger.debug(f"Duplicate strategy filtered: {strategy.name}")
        
        logger.info(f"Extracted {len(unique_strategies)} unique strategies from {len(content_chunks)} chunks")
        return unique_strategies
    
    def validate_strategy_completeness(self, strategy: StrategyRule) -> Tuple[bool, List[str]]:
        """
        Validate that a strategy has all required components.
        
        Args:
            strategy: Strategy to validate
            
        Returns:
            Tuple of (is_valid, list of missing components)
        """
        issues = []
        
        # Check basic fields
        if not strategy.name or strategy.name == "Untitled Strategy":
            issues.append("Strategy needs a descriptive name")
        
        if not strategy.conditions:
            issues.append("Strategy needs at least one pattern condition")
        
        # Check conditions have required parameters
        for i, condition in enumerate(strategy.conditions):
            if condition.type == PatternType.CANDLE:
                required_params = ["pattern", "wick_ratio", "close_position"]
                missing_params = [p for p in required_params if p not in condition.params]
                if missing_params:
                    issues.append(f"Condition {i+1} missing parameters: {missing_params}")
        
        # Check risk management
        if not strategy.risk_params.tp_levels:
            issues.append("Strategy needs take profit levels")
        
        if strategy.risk_params.risk_percent <= 0 or strategy.risk_params.risk_percent > 10:
            issues.append("Risk percent should be between 0.1% and 10%")
        
        # Check confidence
        if strategy.confidence < 0.3:
            issues.append("Strategy confidence is very low (< 0.3)")
        
        is_valid = len(issues) == 0
        return is_valid, issues