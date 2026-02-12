"""
Trade Reasoner

Uses LLM to generate human-readable explanations for trade decisions based on
confluence scores and matched strategy rules. Provides context-aware reasoning
that explains the trade setup in terms of multi-timeframe price action.

This component bridges quantitative pattern detection with qualitative trade
understanding, helping traders and the system itself understand WHY trades
should be taken.

Author: Hyperliquid Trading Bot Suite
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import json
import os
import logging

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    logging.warning(
        "anthropic package not installed. Install with: pip install anthropic"
    )

from ..types import (
    CandleData, OrderSide, Timeframe, EntryType, MarketCycle, TradeOutcome
)
from ..detection.confluence_scorer import ConfluenceScore, TimeframeAnalysis, SignalGeneration
from ..knowledge.repository import StrategyRuleRepository
from ..knowledge.models import StrategyRule, TradeRecord, PriceActionSnapshot


logger = logging.getLogger(__name__)


@dataclass
class TradeReasoning:
    """
    Result of trade reasoning analysis.
    
    Contains the full decision context including whether to enter,
    confidence level, detailed explanation, and risk management suggestions.
    """
    
    # Core reasoning
    should_enter: bool = False
    confidence: float = 0.0
    explanation: str = ""
    
    # Trade details
    entry_bias: Optional[OrderSide] = None
    matched_strategy_id: Optional[str] = None
    matched_strategy_name: str = ""
    
    # Risk management suggestions
    suggested_stop_loss: Optional[float] = None
    suggested_targets: List[float] = field(default_factory=list)
    risk_reward_ratio: Optional[float] = None
    
    # Context summary
    setup_type: str = ""
    key_confluences: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    invalidation_points: List[str] = field(default_factory=list)
    
    # Price action narrative
    higher_tf_context: str = ""
    entry_tf_context: str = ""
    expected_behavior: str = ""
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    asset: str = ""
    reasoning_mode: str = "rule_based"  # 'llm' or 'rule_based'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "should_enter": self.should_enter,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "entry_bias": self.entry_bias.value if self.entry_bias else None,
            "matched_strategy_id": self.matched_strategy_id,
            "matched_strategy_name": self.matched_strategy_name,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_targets": self.suggested_targets,
            "risk_reward_ratio": self.risk_reward_ratio,
            "setup_type": self.setup_type,
            "key_confluences": self.key_confluences,
            "risks": self.risks,
            "invalidation_points": self.invalidation_points,
            "higher_tf_context": self.higher_tf_context,
            "entry_tf_context": self.entry_tf_context,
            "expected_behavior": self.expected_behavior,
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "reasoning_mode": self.reasoning_mode
        }


class TradeReasoner:
    """
    LLM-powered trade reasoner that explains trading decisions.
    
    Takes confluence scores and strategy rules, generates human-readable
    explanations for why trades should or shouldn't be taken. Can operate
    in LLM mode (using Claude) or rule-based mode (template-based fallback).
    
    The reasoner's job is to:
    1. Analyze confluence scores and multi-timeframe context
    2. Match setups to learned strategy rules
    3. Generate clear, actionable explanations
    4. Suggest risk management levels
    5. Identify key confluences and risks
    """
    
    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        use_llm: bool = True
    ):
        """
        Initialize trade reasoner.
        
        Args:
            anthropic_api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            model: Claude model to use (Sonnet for speed/cost balance)
            use_llm: Whether to use LLM or just rule-based reasoning
        """
        self.use_llm = use_llm and HAS_ANTHROPIC
        self.model = model
        
        if self.use_llm:
            api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning(
                    "No Anthropic API key provided. Falling back to rule-based reasoning."
                )
                self.use_llm = False
            else:
                try:
                    self.client = Anthropic(api_key=api_key)
                    logger.info(f"TradeReasoner initialized with LLM model: {self.model}")
                except Exception as e:
                    logger.error(f"Failed to initialize Anthropic client: {e}")
                    self.use_llm = False
        
        # Reasoning parameters
        self.min_confidence_for_entry = 0.55
        self.min_confluence_score = 0.50
        self.min_pattern_score = 0.30
        self.min_structure_score = 0.30
        
        # System prompt for LLM
        self.system_prompt = """You are an expert price action trader specializing in multi-timeframe confluence analysis. 
Your role is to analyze trading setups and provide clear, actionable reasoning for trade decisions.

When analyzing a setup, focus on:
1. Higher timeframe bias and trend direction
2. Market structure (BOS, ChoCH, support/resistance zones)
3. Market cycle phase (Drive, Range, Liquidity)
4. Entry pattern quality and confluence factors
5. Risk/reward ratio and invalidation points

Provide concise, practical explanations that a trader can use to understand the setup.
Be honest about risks and what could invalidate the trade. Think like a professional
price action trader who trades for a living.

Format your response as JSON with these fields:
{
  "should_enter": true/false,
  "confidence_adjustment": 0.0 to 0.2 (boost or reduction),
  "explanation": "concise narrative explanation",
  "key_confluences": ["factor 1", "factor 2", ...],
  "risks": ["risk 1", "risk 2", ...],
  "invalidation_points": ["what invalidates the setup"],
  "higher_tf_context": "higher timeframe bias and structure",
  "entry_tf_context": "entry timeframe pattern and setup",
  "expected_behavior": "what should happen if trade works"
}"""
    
    def analyze_setup(
        self,
        asset: str,
        confluence_score: ConfluenceScore,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        strategy_repository: StrategyRuleRepository,
        current_price: Optional[float] = None
    ) -> TradeReasoning:
        """
        Analyze a trading setup and generate reasoning.
        
        Args:
            asset: Trading asset symbol
            confluence_score: Confluence analysis result
            timeframe_analyses: Multi-timeframe analysis results
            strategy_repository: Repository to fetch matching strategies
            current_price: Current market price
            
        Returns:
            TradeReasoning with detailed explanation and decision
        """
        reasoning = TradeReasoning(
            asset=asset,
            timestamp=confluence_score.timestamp,
            reasoning_mode="llm" if self.use_llm else "rule_based"
        )
        
        try:
            # 1. Check if confluence score meets minimum threshold
            if confluence_score.total_score < self.min_confluence_score:
                reasoning.explanation = (
                    f"Confluence score ({confluence_score.total_score:.2%}) "
                    f"below minimum threshold ({self.min_confluence_score:.0%}). "
                    f"Setup lacks sufficient alignment across timeframes and factors."
                )
                return reasoning
            
            # 2. Check component minimums
            if confluence_score.pattern_score < self.min_pattern_score:
                reasoning.explanation = (
                    f"Pattern score ({confluence_score.pattern_score:.2%}) too weak "
                    f"(minimum: {self.min_pattern_score:.0%}). Entry pattern lacks quality."
                )
                return reasoning
            
            if confluence_score.structure_score < self.min_structure_score:
                reasoning.explanation = (
                    f"Structure score ({confluence_score.structure_score:.2%}) too weak "
                    f"(minimum: {self.min_structure_score:.0%}). Market structure unclear."
                )
                return reasoning
            
            # 3. Check for valid bias direction
            if not confluence_score.bias_direction:
                reasoning.explanation = (
                    "No clear directional bias detected. Market may be in transition "
                    "or lacking clear trend direction across timeframes."
                )
                return reasoning
            
            # 4. Find matching strategy rule
            matched_strategy = self._find_matching_strategy(
                confluence_score, strategy_repository
            )
            
            if not matched_strategy:
                reasoning.explanation = (
                    "No matching strategy rule found in knowledge base. "
                    f"While confluence exists ({confluence_score.total_score:.0%}), "
                    "this setup pattern hasn't been learned yet. Consider adding it "
                    "to the knowledge base if it represents a valid setup."
                )
                return reasoning
            
            reasoning.matched_strategy_id = matched_strategy.id
            reasoning.matched_strategy_name = matched_strategy.name
            reasoning.entry_bias = confluence_score.bias_direction
            
            # 5. Describe setup type
            reasoning.setup_type = self._describe_setup_type(
                confluence_score, matched_strategy
            )
            
            # 6. Calculate risk management levels
            if current_price:
                self._calculate_risk_levels(
                    reasoning, confluence_score, timeframe_analyses, 
                    current_price, matched_strategy
                )
            
            # 7. Generate detailed reasoning (LLM or rule-based)
            if self.use_llm:
                self._generate_llm_reasoning(
                    reasoning, confluence_score, timeframe_analyses, matched_strategy
                )
            else:
                self._generate_rule_based_reasoning(
                    reasoning, confluence_score, timeframe_analyses, matched_strategy
                )
            
            # 8. Determine final recommendation
            reasoning.should_enter = self._should_enter_trade(
                confluence_score, matched_strategy, reasoning
            )
            
            # 9. Calculate final confidence
            reasoning.confidence = self._calculate_confidence(
                confluence_score, matched_strategy, reasoning
            )
            
        except Exception as e:
            logger.error(f"Error analyzing setup for {asset}: {e}", exc_info=True)
            reasoning.explanation = (
                f"Error during setup analysis: {str(e)}. "
                "Trade rejected due to analysis failure."
            )
            reasoning.should_enter = False
            reasoning.confidence = 0.0
        
        return reasoning
    
    def _find_matching_strategy(
        self,
        confluence_score: ConfluenceScore,
        repository: StrategyRuleRepository
    ) -> Optional[StrategyRule]:
        """
        Find the best matching strategy rule from knowledge base.
        
        Matches based on entry type, market cycle, and required conditions.
        """
        try:
            # Get all strategies with matching entry type
            if not confluence_score.lower_tf_pattern:
                return None
            
            strategies = repository.get_all(
                entry_type=confluence_score.lower_tf_pattern.value,
                min_confidence=0.3  # Only consider strategies with some confidence
            )
            
            if not strategies:
                return None
            
            # Score each strategy by how well it matches current conditions
            best_strategy = None
            best_score = 0.0
            
            for strategy in strategies:
                score = 0.0
                
                # Base score from strategy confidence
                score += strategy.confidence * 0.4
                
                # Bonus for cycle match
                if confluence_score.higher_tf_cycle:
                    # Check if any condition specifies this cycle
                    for condition in strategy.conditions:
                        if (condition.type.value == "cycle" and 
                            condition.params.get("cycle") == confluence_score.higher_tf_cycle.value):
                            score += 0.2
                            break
                
                # Bonus for timeframe alignment
                if strategy.confluence_required:
                    for alignment in strategy.confluence_required:
                        # Check if alignment matches our analysis
                        if (alignment.higher_tf.value in confluence_score.timeframe_analyses and
                            alignment.lower_tf.value in confluence_score.timeframe_analyses):
                            score += 0.2
                            break
                
                # Bonus for recent success (if win_rate exists)
                if strategy.win_rate and strategy.win_rate > 0.5:
                    score += 0.2
                
                if score > best_score:
                    best_score = score
                    best_strategy = strategy
            
            return best_strategy
            
        except Exception as e:
            logger.error(f"Error finding matching strategy: {e}")
            return None
    
    def _describe_setup_type(
        self,
        confluence_score: ConfluenceScore,
        strategy: StrategyRule
    ) -> str:
        """Generate a concise description of the setup type."""
        parts = []
        
        # Bias direction
        if confluence_score.bias_direction:
            parts.append(confluence_score.bias_direction.value.upper())
        
        # Entry pattern
        if confluence_score.lower_tf_pattern:
            parts.append(confluence_score.lower_tf_pattern.value.replace("_", " ").title())
        
        # Market cycle
        if confluence_score.higher_tf_cycle:
            parts.append(f"in {confluence_score.higher_tf_cycle.value.title()} phase")
        
        # Timeframe
        if confluence_score.entry_timeframe:
            parts.append(f"on {confluence_score.entry_timeframe.value}")
        
        return " ".join(parts) if parts else "Multi-timeframe setup"
    
    def _calculate_risk_levels(
        self,
        reasoning: TradeReasoning,
        confluence_score: ConfluenceScore,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        current_price: float,
        strategy: StrategyRule
    ):
        """
        Calculate suggested stop loss and take profit levels.
        
        Uses market structure (swing highs/lows) and strategy risk parameters.
        """
        try:
            direction = confluence_score.bias_direction
            if not direction:
                return
            
            # Find nearest structural level for stop loss
            stop_loss = None
            structure_buffer = 0.002  # 0.2% buffer
            
            # Look through timeframe analyses for structure
            for tf_key, analysis in timeframe_analyses.items():
                if not analysis.market_structure:
                    continue
                
                structure = analysis.market_structure
                
                if direction == OrderSide.LONG:
                    # Stop below nearest support or recent swing low
                    for zone in structure.support_zones:
                        zone_price = zone.get('price_level', 0)
                        if zone_price > 0 and zone_price < current_price:
                            candidate_stop = zone_price * (1 - structure_buffer)
                            if stop_loss is None or candidate_stop > stop_loss:
                                stop_loss = candidate_stop
                    
                else:  # SHORT
                    # Stop above nearest resistance or recent swing high
                    for zone in structure.resistance_zones:
                        zone_price = zone.get('price_level', 0)
                        if zone_price > 0 and zone_price > current_price:
                            candidate_stop = zone_price * (1 + structure_buffer)
                            if stop_loss is None or candidate_stop < stop_loss:
                                stop_loss = candidate_stop
            
            # Default stop loss if no structure found (1% from entry)
            if stop_loss is None:
                if direction == OrderSide.LONG:
                    stop_loss = current_price * 0.99
                else:
                    stop_loss = current_price * 1.01
            
            reasoning.suggested_stop_loss = stop_loss
            
            # Calculate take profit targets based on R-multiples
            risk = abs(current_price - stop_loss)
            tp_multiples = strategy.risk_params.tp_levels
            
            targets = []
            for multiple in tp_multiples:
                if direction == OrderSide.LONG:
                    target = current_price + (risk * multiple)
                else:
                    target = current_price - (risk * multiple)
                targets.append(target)
            
            reasoning.suggested_targets = targets
            
            # Calculate risk/reward ratio (to first target)
            if targets:
                reward = abs(targets[0] - current_price)
                reasoning.risk_reward_ratio = reward / risk if risk > 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating risk levels: {e}")
    
    def _generate_llm_reasoning(
        self,
        reasoning: TradeReasoning,
        confluence_score: ConfluenceScore,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        strategy: StrategyRule
    ):
        """Generate reasoning using LLM (Claude)."""
        try:
            # Build prompt with all context
            user_prompt = self._build_llm_prompt(
                reasoning.asset,
                confluence_score,
                timeframe_analyses,
                strategy
            )
            
            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self.system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            
            # Parse response
            response_text = response.content[0].text
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response_text)
                reasoning.explanation = parsed.get("explanation", response_text)
                reasoning.key_confluences = parsed.get("key_confluences", [])
                reasoning.risks = parsed.get("risks", [])
                reasoning.invalidation_points = parsed.get("invalidation_points", [])
                reasoning.higher_tf_context = parsed.get("higher_tf_context", "")
                reasoning.entry_tf_context = parsed.get("entry_tf_context", "")
                reasoning.expected_behavior = parsed.get("expected_behavior", "")
                
                # Apply confidence adjustment if provided
                confidence_adj = parsed.get("confidence_adjustment", 0.0)
                # We'll apply this in _calculate_confidence
                
            except json.JSONDecodeError:
                # If not JSON, use the whole response as explanation
                reasoning.explanation = response_text
                self._extract_info_from_text(reasoning, response_text)
            
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}. Falling back to rule-based.")
            # Fall back to rule-based
            self._generate_rule_based_reasoning(
                reasoning, confluence_score, timeframe_analyses, strategy
            )
    
    def _build_llm_prompt(
        self,
        asset: str,
        confluence_score: ConfluenceScore,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        strategy: StrategyRule
    ) -> str:
        """Build detailed prompt for LLM analysis."""
        prompt_parts = [
            f"## Trading Setup Analysis for {asset}",
            "",
            "### Confluence Score Summary",
            f"- Total Score: {confluence_score.total_score:.2%}",
            f"- Confidence: {confluence_score.confidence:.2%}",
            f"- Signal Strength: {confluence_score.signal_strength:.2%}",
            f"- Bias Direction: {confluence_score.bias_direction.value.upper() if confluence_score.bias_direction else 'NONE'}",
            f"- Entry Pattern: {confluence_score.lower_tf_pattern.value if confluence_score.lower_tf_pattern else 'NONE'}",
            f"- Entry Timeframe: {confluence_score.entry_timeframe.value if confluence_score.entry_timeframe else 'NONE'}",
            "",
            "### Component Scores",
            f"- Pattern Score: {confluence_score.pattern_score:.2%}",
            f"- Structure Score: {confluence_score.structure_score:.2%}",
            f"- Cycle Score: {confluence_score.cycle_score:.2%}",
            f"- Zone Score: {confluence_score.zone_score:.2%}",
            "",
            "### Higher Timeframe Context",
            f"- Bias: {confluence_score.higher_tf_bias.value.upper() if confluence_score.higher_tf_bias else 'NONE'}",
            f"- Strength: {confluence_score.higher_tf_strength:.2%}",
            f"- Cycle: {confluence_score.higher_tf_cycle.value.upper() if confluence_score.higher_tf_cycle else 'NONE'}",
            "",
            "### Timeframe Alignment",
            f"- Aligned: {confluence_score.timeframes_aligned}/{confluence_score.total_timeframes} timeframes",
            f"- Alignment %: {confluence_score.alignment_percentage:.1%}",
            "",
        ]
        
        # Add confluence factors
        if confluence_score.confluence_factors:
            prompt_parts.append("### Confluence Factors")
            for factor in confluence_score.confluence_factors:
                prompt_parts.append(f"✓ {factor}")
            prompt_parts.append("")
        
        # Add warning factors
        if confluence_score.warning_factors:
            prompt_parts.append("### Warning Factors")
            for warning in confluence_score.warning_factors:
                prompt_parts.append(f"⚠ {warning}")
            prompt_parts.append("")
        
        # Add matched strategy info
        prompt_parts.extend([
            "### Matched Strategy",
            f"- Name: {strategy.name}",
            f"- Confidence: {strategy.confidence:.2%}",
            f"- Entry Type: {strategy.entry_type.value}",
        ])
        
        if strategy.description:
            prompt_parts.append(f"- Description: {strategy.description}")
        
        if strategy.win_rate:
            prompt_parts.append(f"- Historical Win Rate: {strategy.win_rate:.1%}")
        
        prompt_parts.append("")
        prompt_parts.append("### Analysis Request")
        prompt_parts.append(
            "Based on the above confluence analysis and matched strategy, "
            "provide your expert analysis of whether this trade should be taken. "
            "Consider all factors and provide clear reasoning."
        )
        
        return "\n".join(prompt_parts)
    
    def _extract_info_from_text(self, reasoning: TradeReasoning, text: str):
        """Extract structured info from unstructured LLM text response."""
        # Simple keyword-based extraction
        lines = text.split("\n")
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if "confluence" in line.lower() or "factor" in line.lower():
                current_section = "confluences"
            elif "risk" in line.lower() or "warning" in line.lower():
                current_section = "risks"
            elif "invalidat" in line.lower():
                current_section = "invalidation"
            elif line.startswith("-") or line.startswith("•") or line.startswith("*"):
                # Bullet point
                item = line.lstrip("-•* ").strip()
                if current_section == "confluences":
                    reasoning.key_confluences.append(item)
                elif current_section == "risks":
                    reasoning.risks.append(item)
                elif current_section == "invalidation":
                    reasoning.invalidation_points.append(item)
    
    def _generate_rule_based_reasoning(
        self,
        reasoning: TradeReasoning,
        confluence_score: ConfluenceScore,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        strategy: StrategyRule
    ):
        """Generate reasoning using template-based rules (fallback)."""
        
        # Build explanation from components
        explanation_parts = []
        
        # Opening statement
        quality = self._assess_quality(confluence_score)
        explanation_parts.append(
            f"{quality} {reasoning.entry_bias.value if reasoning.entry_bias else 'neutral'} "
            f"setup on {reasoning.asset} with {confluence_score.total_score:.0%} confluence."
        )
        
        # Pattern description
        if confluence_score.lower_tf_pattern:
            explanation_parts.append(
                f"{confluence_score.lower_tf_pattern.value.replace('_', ' ').title()} pattern "
                f"detected at {confluence_score.entry_timeframe.value if confluence_score.entry_timeframe else 'entry timeframe'} "
                f"with {confluence_score.lower_tf_confidence:.0%} confidence."
            )
        
        # Higher TF context
        if confluence_score.higher_tf_bias:
            explanation_parts.append(
                f"Higher timeframes show {confluence_score.higher_tf_bias.value} bias "
                f"with {confluence_score.higher_tf_strength:.0%} strength."
            )
        
        # Cycle context
        if confluence_score.higher_tf_cycle:
            cycle_desc = {
                MarketCycle.DRIVE: "strong momentum (favorable for trends)",
                MarketCycle.RANGE: "consolidation (lower trend probability)",
                MarketCycle.LIQUIDITY: "liquidity phase (watch for stop hunts)"
            }.get(confluence_score.higher_tf_cycle, "")
            
            if cycle_desc:
                explanation_parts.append(f"Market is in {cycle_desc}.")
        
        # Alignment
        explanation_parts.append(
            f"{confluence_score.timeframes_aligned}/{confluence_score.total_timeframes} "
            f"timeframes aligned ({confluence_score.alignment_percentage:.0%})."
        )
        
        reasoning.explanation = " ".join(explanation_parts)
        
        # Populate confluence factors
        reasoning.key_confluences = confluence_score.confluence_factors.copy()
        
        # Populate risks/warnings
        reasoning.risks = confluence_score.warning_factors.copy()
        
        # Generate contexts
        reasoning.higher_tf_context = (
            f"{confluence_score.higher_tf_bias.value.upper() if confluence_score.higher_tf_bias else 'Neutral'} bias, "
            f"{confluence_score.higher_tf_strength:.0%} strength, "
            f"{confluence_score.higher_tf_cycle.value.title() if confluence_score.higher_tf_cycle else 'unknown'} phase"
        )
        
        reasoning.entry_tf_context = (
            f"{confluence_score.lower_tf_pattern.value.replace('_', ' ').title() if confluence_score.lower_tf_pattern else 'Pattern'} "
            f"on {confluence_score.entry_timeframe.value if confluence_score.entry_timeframe else 'entry TF'}, "
            f"{confluence_score.entry_quality:.0%} quality"
        )
        
        # Expected behavior
        if reasoning.entry_bias and reasoning.suggested_targets:
            target_desc = f"${reasoning.suggested_targets[0]:,.2f}" if reasoning.suggested_targets[0] > 1000 else f"{reasoning.suggested_targets[0]:.4f}"
            reasoning.expected_behavior = (
                f"If setup is valid, expect move toward {target_desc}. "
                f"Invalidation if price breaks {reasoning.suggested_stop_loss:.4f if reasoning.suggested_stop_loss else 'stop level'}."
            )
        
        # Invalidation points
        if reasoning.suggested_stop_loss:
            reasoning.invalidation_points.append(
                f"Stop loss breach at {reasoning.suggested_stop_loss:.4f}"
            )
        
        if confluence_score.higher_tf_bias:
            reasoning.invalidation_points.append(
                f"Break of higher TF {confluence_score.higher_tf_bias.value} structure"
            )
    
    def _assess_quality(self, confluence_score: ConfluenceScore) -> str:
        """Assess overall setup quality."""
        score = confluence_score.total_score
        
        if score >= 0.80:
            return "Excellent"
        elif score >= 0.70:
            return "Strong"
        elif score >= 0.60:
            return "Good"
        elif score >= 0.50:
            return "Acceptable"
        else:
            return "Weak"
    
    def _should_enter_trade(
        self,
        confluence_score: ConfluenceScore,
        strategy: StrategyRule,
        reasoning: TradeReasoning
    ) -> bool:
        """
        Determine if trade should be entered based on all factors.
        """
        # Must generate a signal
        if not confluence_score.generates_signal:
            return False
        
        # Must have entry bias
        if not confluence_score.bias_direction:
            return False
        
        # Must have matched strategy
        if not reasoning.matched_strategy_id:
            return False
        
        # Confluence must meet minimum
        if confluence_score.total_score < self.min_confluence_score:
            return False
        
        # Component minimums
        if confluence_score.pattern_score < self.min_pattern_score:
            return False
        
        if confluence_score.structure_score < self.min_structure_score:
            return False
        
        # All checks passed
        return True
    
    def _calculate_confidence(
        self,
        confluence_score: ConfluenceScore,
        strategy: StrategyRule,
        reasoning: TradeReasoning
    ) -> float:
        """
        Calculate overall confidence in the trade decision.
        
        Combines confluence score, strategy confidence, and quality factors.
        """
        # Base confidence from confluence and strategy
        base_confidence = (
            confluence_score.total_score * 0.6 +
            strategy.confidence * 0.4
        )
        
        # Boost for quality factors
        quality_boost = 0.0
        
        # High signal strength
        if confluence_score.signal_strength >= 0.80:
            quality_boost += 0.10
        elif confluence_score.signal_strength >= 0.70:
            quality_boost += 0.05
        
        # Strong alignment
        if confluence_score.alignment_percentage >= 0.80:
            quality_boost += 0.05
        
        # Good risk/reward
        if reasoning.risk_reward_ratio and reasoning.risk_reward_ratio >= 2.0:
            quality_boost += 0.05
        
        # Reduce for warning factors
        warning_penalty = min(0.05 * len(reasoning.risks), 0.15)
        
        # Final confidence
        confidence = base_confidence + quality_boost - warning_penalty
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))
    
    async def _generate_llm_reasoning_from_signal(
        self,
        signal: SignalGeneration,
        candle_data: Optional[Dict[str, List[CandleData]]],
        timeframe_analyses: Dict[str, TimeframeAnalysis]
    ) -> Tuple[str, str]:
        """Generate LLM reasoning from a signal object."""
        confluence = signal.confluence_score
        
        # Build system prompt
        system_prompt = """You are an expert price action trader. Analyze this setup and explain it clearly."""
        
        # Build user prompt
        user_prompt = f"""Analyze this {signal.direction.value} setup for {signal.asset}:

Confluence: {confluence.total_score:.0%}
Confidence: {confluence.confidence:.0%}
Pattern: {signal.entry_type.value}

Factors: {', '.join(confluence.confluence_factors[:3])}

Provide:
SUMMARY: One sentence
EXPLANATION: 2-3 sentences on why this trade makes sense and what risks exist"""
        
        # Call Claude
        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        response = message.content[0].text.strip()
        
        # Parse response
        lines = response.split('\n')
        summary = ""
        explanation = ""
        
        for i, line in enumerate(lines):
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("EXPLANATION:"):
                explanation = '\n'.join(lines[i+1:]).strip()
                break
        
        if not summary:
            summary = f"{signal.direction.value} setup with {confluence.confidence:.0%} confidence"
        if not explanation:
            explanation = response
        
        return explanation, summary
    
    def _generate_rule_based_reasoning_from_signal(
        self,
        signal: SignalGeneration,
        timeframe_analyses: Dict[str, TimeframeAnalysis]
    ) -> Tuple[str, str]:
        """Generate rule-based reasoning from a signal object."""
        confluence = signal.confluence_score
        
        direction_word = "bullish" if signal.direction == OrderSide.LONG else "bearish"
        
        # Summary
        summary = (
            f"{signal.direction.value} {signal.entry_type.value} setup on {signal.asset} "
            f"with {confluence.confidence:.0%} confidence"
        )
        
        # Explanation
        paragraphs = []
        paragraphs.append(
            f"Detected {signal.direction.value} setup on {signal.asset} with "
            f"{confluence.total_score:.0%} confluence and {confluence.confidence:.0%} confidence."
        )
        
        if confluence.higher_tf_bias:
            paragraphs.append(
                f"Higher timeframe shows {confluence.higher_tf_bias.value} bias "
                f"with {confluence.higher_tf_strength:.0%} strength."
            )
        
        if confluence.warning_factors:
            paragraphs.append(
                f"Key risks: {'; '.join(confluence.warning_factors[:2])}."
            )
        
        explanation = " ".join(paragraphs)
        
        return explanation, summary
    
    def create_trade_record(
        self,
        reasoning: TradeReasoning,
        confluence_score: ConfluenceScore,
        timeframe_analyses: Dict[str, TimeframeAnalysis],
        entry_price: float,
        position_size: float,
        is_backtest: bool = False
    ) -> TradeRecord:
        """
        Create a trade record from reasoning result.
        
        Args:
            reasoning: Trade reasoning result
            confluence_score: Confluence score that generated the signal
            timeframe_analyses: Multi-timeframe context
            entry_price: Actual entry price
            position_size: Position size
            is_backtest: Whether this is a backtested trade
            
        Returns:
            TradeRecord ready to be saved to database
        """
        # Create price action snapshot
        snapshot = PriceActionSnapshot(
            timeframes={},
            structure_notes=reasoning.key_confluences,
            zone_interactions=[],
            market_cycle=confluence_score.higher_tf_cycle,
            confluence_score=confluence_score.total_score
        )
        
        # Build trade record
        trade = TradeRecord(
            strategy_rule_id=reasoning.matched_strategy_id,
            asset=reasoning.asset,
            direction=reasoning.entry_bias,
            entry_price=entry_price,
            entry_time=reasoning.timestamp,
            position_size=position_size,
            stop_loss=reasoning.suggested_stop_loss,
            take_profit_levels=reasoning.suggested_targets,
            reasoning=reasoning.explanation,
            price_action_context=snapshot,
            confidence=reasoning.confidence,
            is_backtest=is_backtest,
            outcome=TradeOutcome.PENDING
        )
        
        return trade


# Convenience function for quick analysis
def analyze_trade_setup(
    asset: str,
    confluence_score: ConfluenceScore,
    timeframe_analyses: Dict[str, TimeframeAnalysis],
    strategy_repository: StrategyRuleRepository,
    current_price: Optional[float] = None,
    use_llm: bool = True,
    anthropic_api_key: Optional[str] = None
) -> TradeReasoning:
    """
    Convenience function to analyze a trade setup.
    
    Args:
        asset: Trading asset symbol
        confluence_score: Confluence analysis result
        timeframe_analyses: Multi-timeframe analysis results
        strategy_repository: Strategy rule repository
        current_price: Current market price
        use_llm: Whether to use LLM reasoning
        anthropic_api_key: Anthropic API key (optional)
        
    Returns:
        TradeReasoning with full analysis
    """
    reasoner = TradeReasoner(
        anthropic_api_key=anthropic_api_key,
        use_llm=use_llm
    )
    
    return reasoner.analyze_setup(
        asset=asset,
        confluence_score=confluence_score,
        timeframe_analyses=timeframe_analyses,
        strategy_repository=strategy_repository,
        current_price=current_price
    )


async def explain_trade(
    signal: SignalGeneration,
    candle_data: Optional[Dict[str, List[CandleData]]] = None,
    timeframe_analyses: Optional[Dict[str, TimeframeAnalysis]] = None,
    anthropic_api_key: Optional[str] = None
) -> TradeReasoning:
    """
    Convenience function to generate trade reasoning from a signal.
    
    Args:
        signal: Trading signal to explain
        candle_data: Optional candle data by timeframe
        timeframe_analyses: Optional timeframe analysis results
        anthropic_api_key: Optional API key (uses env var if not provided)
        
    Returns:
        TradeReasoning object with explanation
    """
    reasoner = TradeReasoner(anthropic_api_key=anthropic_api_key)
    
    # Use timeframe analyses from signal's confluence score if not provided
    if timeframe_analyses is None:
        timeframe_analyses = signal.confluence_score.timeframe_analyses
    
    # Convert signal to the format expected by analyze_setup
    # For now, create a simple reasoning from the signal directly
    confluence = signal.confluence_score
    
    # Build reasoning
    should_enter = confluence.generates_signal and confluence.confidence >= reasoner.min_confidence
    
    # Generate explanation using LLM or rule-based
    if reasoner.use_llm:
        try:
            # Build prompt for LLM
            explanation, summary = await reasoner._generate_llm_reasoning_from_signal(
                signal, candle_data, timeframe_analyses
            )
        except:
            # Fall back to rule-based
            explanation, summary = reasoner._generate_rule_based_reasoning_from_signal(
                signal, timeframe_analyses
            )
    else:
        explanation, summary = reasoner._generate_rule_based_reasoning_from_signal(
            signal, timeframe_analyses
        )
    
    reasoning = TradeReasoning(
        should_enter=should_enter,
        confidence=confluence.confidence,
        explanation=explanation,
        one_sentence_summary=summary,
        entry_bias=signal.direction,
        entry_type=signal.entry_type,
        suggested_stop_loss=signal.suggested_stop_loss,
        suggested_targets=signal.suggested_take_profits,
        risk_reward_ratio=signal.risk_reward_ratio,
        confluence_factors=confluence.confluence_factors.copy(),
        risks=confluence.warning_factors.copy(),
        higher_tf_context=f"{confluence.higher_tf_bias.value if confluence.higher_tf_bias else 'Unknown'} bias",
        entry_tf_context=f"{confluence.lower_tf_pattern.value if confluence.lower_tf_pattern else 'Unknown'} pattern",
        expected_behavior=f"Expect movement toward ${signal.suggested_take_profits[0]:,.2f}" if signal.suggested_take_profits else "",
        timestamp=signal.generated_at,
        asset=signal.asset,
        generated_at=datetime.utcnow(),
        model_used=reasoner.model if reasoner.use_llm else "rule-based"
    )
    
    return reasoning


def format_reasoning_for_display(reasoning: TradeReasoning) -> str:
    """
    Format reasoning for console/UI display.
    
    Args:
        reasoning: TradeReasoning object
        
    Returns:
        Formatted string for display
    """
    lines = []
    
    # Header
    if reasoning.should_enter:
        lines.append("=" * 80)
        lines.append(f"✅ ENTER {reasoning.entry_bias.value if reasoning.entry_bias else 'UNKNOWN'} TRADE")
        lines.append(f"Confidence: {reasoning.confidence:.0%}")
        lines.append("=" * 80)
    else:
        lines.append("=" * 80)
        lines.append("❌ NO ENTRY")
        lines.append("=" * 80)
    
    # Summary
    if reasoning.one_sentence_summary:
        lines.append(f"\nSUMMARY:")
        lines.append(f"  {reasoning.one_sentence_summary}")
    
    # Explanation
    lines.append(f"\nREASONING:")
    for line in reasoning.explanation.split('\n'):
        lines.append(f"  {line}")
    
    # Risk management
    if reasoning.suggested_stop_loss or reasoning.suggested_targets:
        lines.append(f"\nRISK MANAGEMENT:")
        if reasoning.suggested_stop_loss:
            lines.append(f"  Stop Loss: ${reasoning.suggested_stop_loss:,.2f}")
        if reasoning.suggested_targets:
            targets_str = ", ".join([f"${t:,.2f}" for t in reasoning.suggested_targets])
            lines.append(f"  Targets: {targets_str}")
        if reasoning.risk_reward_ratio:
            lines.append(f"  R:R Ratio: 1:{reasoning.risk_reward_ratio:.1f}")
    
    # Confluence factors
    if reasoning.confluence_factors:
        lines.append(f"\nKEY CONFLUENCE FACTORS:")
        for factor in reasoning.confluence_factors:
            lines.append(f"  • {factor}")
    
    # Risks
    if reasoning.risks:
        lines.append(f"\nRISKS:")
        for risk in reasoning.risks:
            lines.append(f"  • {risk}")
    
    # Expected behavior
    if reasoning.expected_behavior:
        lines.append(f"\nEXPECTED BEHAVIOR:")
        lines.append(f"  {reasoning.expected_behavior}")
    
    # Metadata
    lines.append(f"\nGenerated: {reasoning.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Model: {reasoning.model_used}")
    lines.append("=" * 80)
    
    return "\n".join(lines)


__all__ = [
    "TradeReasoner",
    "TradeReasoning",
    "analyze_trade_setup",
    "explain_trade",
    "format_reasoning_for_display"
]
