"""Trade Outcome Learner - Learn WHY trades worked or failed from chart analysis.

This module analyzes completed trades by looking at the charts and understanding
the technical reasons for success or failure. It builds a growing knowledge base
of what works and what doesn't.

The goal: Get smarter with every trade.
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from hl_bot.services.llm_client import LLMClient
from hl_bot.types import Signal, SignalType, Trade, TradeStatus

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class TradeOutcomeAnalysis:
    """Analysis of why a trade succeeded or failed."""
    trade_id: str
    outcome: str  # "win", "loss", "breakeven"
    pnl_percent: float
    
    # Technical analysis of what happened
    setup_was_valid: bool
    entry_was_good: bool
    stop_was_correct: bool
    market_conditions_favorable: bool
    
    # What the chart showed
    chart_observations: List[str]
    
    # Why it worked or didn't
    success_factors: List[str]
    failure_factors: List[str]
    
    # What could have been done differently
    improvements: List[str]
    
    # Key lesson from this trade
    lesson: str
    
    # Confidence in analysis
    confidence: float
    
    # Tags for categorization
    tags: List[str] = field(default_factory=list)


@dataclass
class PatternPerformance:
    """Track how specific patterns perform over time."""
    pattern_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    win_rate: float = 0.0
    
    # Conditions where it works best
    best_conditions: List[str] = field(default_factory=list)
    # Conditions where it fails
    worst_conditions: List[str] = field(default_factory=list)
    
    # Learned improvements
    learned_filters: List[str] = field(default_factory=list)


@dataclass
class TradingKnowledge:
    """Accumulated knowledge from trade outcomes."""
    total_trades_analyzed: int = 0
    
    # Pattern performance tracking
    pattern_stats: Dict[str, PatternPerformance] = field(default_factory=dict)
    
    # Learned rules (what to do / not do)
    rules_learned: List[Dict[str, Any]] = field(default_factory=list)
    
    # Market condition insights
    condition_insights: Dict[str, List[str]] = field(default_factory=dict)
    
    # Recent lessons (most important)
    recent_lessons: List[str] = field(default_factory=list)


# ============================================================================
# Analysis Prompts
# ============================================================================


OUTCOME_ANALYSIS_PROMPT = """You are an expert trading analyst performing a POST-TRADE REVIEW.

A trade has been closed. Your job is to analyze the chart and understand WHY it worked or failed.

## Trade Details
- **Setup Type:** {setup_type}
- **Direction:** {direction}
- **Entry Price:** {entry_price}
- **Stop Loss:** {stop_loss}
- **Take Profit:** {take_profit}
- **Exit Price:** {exit_price}
- **P&L:** {pnl_percent}%
- **Outcome:** {outcome}

## Strategy Context
{strategy_context}

## Chart Image
[Attached - shows price action before, during, and after the trade]

## Your Analysis Task

Study the chart carefully and answer:

### 1. Setup Validity
- Was this a valid {setup_type} setup according to the strategy rules?
- Were all entry conditions actually met?
- Was there anything that should have made us skip this trade?

### 2. Entry Quality
- Was the entry timing good?
- Did we enter at the right price level?
- Could entry have been better? How?

### 3. Stop Loss Placement
- Was the stop loss at the correct level (based on wick type, structure)?
- Was it too tight? Too wide?
- Did price action justify the stop placement?

### 4. Market Conditions
- What was the broader market doing?
- Was the higher timeframe bias aligned?
- Were there any external factors affecting the trade?

### 5. What Happened During the Trade
- How did price behave after entry?
- Were there warning signs?
- Did the setup play out as expected?

### 6. Technical Reasons for Outcome
IF WIN:
- What specific technical factors led to success?
- Was it the setup, timing, or market conditions?
- Was it skill or luck?

IF LOSS:
- What specific technical factors led to failure?
- Was the setup actually invalid?
- Did we miss warning signs?
- Was it a valid setup that just didn't work (acceptable loss)?

### 7. Key Lesson
What is the ONE most important thing to learn from this trade?

### 8. Future Improvements
What should we do differently next time we see a similar setup?

Respond with structured JSON:
{{
    "setup_was_valid": true/false,
    "entry_was_good": true/false,
    "stop_was_correct": true/false,
    "market_conditions_favorable": true/false,
    "chart_observations": [
        "Observation 1 about what the chart showed",
        "Observation 2...",
        "..."
    ],
    "success_factors": [
        "Factor that contributed to win (if applicable)"
    ],
    "failure_factors": [
        "Factor that contributed to loss (if applicable)"
    ],
    "improvements": [
        "Specific improvement for future trades"
    ],
    "lesson": "The ONE key lesson from this trade",
    "confidence": 0.0-1.0,
    "tags": ["tag1", "tag2"]
}}
"""


PATTERN_LEARNING_PROMPT = """You are analyzing patterns across multiple trades to find what ACTUALLY works.

## Trade History for {pattern_name}
{trade_history}

## Your Task

Analyze all these trades and find:

1. **When does this pattern work best?**
   - What market conditions?
   - What higher timeframe bias?
   - What time of day?
   - What additional confirmations?

2. **When does it fail?**
   - What conditions lead to losses?
   - What warning signs were missed?
   - What should we filter out?

3. **Refined Rules**
   Based on actual trade outcomes, what rules should we ADD to improve win rate?

4. **Updated Expectations**
   - Realistic win rate for this pattern
   - Average winner vs loser size
   - Best R:R to target

Respond with JSON:
{{
    "best_conditions": ["condition1", "condition2"],
    "worst_conditions": ["condition1", "condition2"],
    "new_rules": [
        {{"rule": "Only take this setup when...", "reason": "Based on X trades that..."}}
    ],
    "expected_win_rate": 0.XX,
    "recommended_rr": X.X,
    "key_insight": "The most important thing we learned..."
}}
"""


# ============================================================================
# Trade Outcome Learner
# ============================================================================


class TradeOutcomeLearner:
    """Learn from trade outcomes by analyzing charts."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: str = "claude-sonnet-4-20250514",
        knowledge_path: Optional[Path] = None,
    ):
        self._llm = llm_client or LLMClient()
        self._model = model
        self._knowledge_path = knowledge_path or Path("/opt/swarmops/projects/hl-bot-v2/knowledge/trading_knowledge.json")
        self._knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing knowledge
        self._knowledge = self._load_knowledge()
        
        logger.info(f"Trade Outcome Learner initialized. {self._knowledge.total_trades_analyzed} trades analyzed so far.")
    
    async def analyze_trade_outcome(
        self,
        trade: Trade,
        chart_image: bytes,
        strategy_context: str = "",
    ) -> TradeOutcomeAnalysis:
        """Analyze a completed trade to understand why it worked or failed.
        
        Args:
            trade: The completed trade
            chart_image: PNG image of the chart showing the trade
            strategy_context: Description of the strategy used
            
        Returns:
            Detailed analysis of the trade outcome
        """
        logger.info(f"Analyzing trade outcome: {trade.id}")
        
        # Determine outcome
        pnl_percent = float(trade.realized_pnl_percent) if trade.realized_pnl_percent else 0
        if pnl_percent > 0.5:
            outcome = "win"
        elif pnl_percent < -0.5:
            outcome = "loss"
        else:
            outcome = "breakeven"
        
        # Build prompt
        prompt = OUTCOME_ANALYSIS_PROMPT.format(
            setup_type=trade.setup_type if hasattr(trade, 'setup_type') else "Unknown",
            direction=trade.side.value if hasattr(trade.side, 'value') else str(trade.side),
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit_1 if hasattr(trade, 'take_profit_1') else "N/A",
            exit_price=trade.exit_price,
            pnl_percent=f"{pnl_percent:.2f}",
            outcome=outcome.upper(),
            strategy_context=strategy_context or "8amEST + ControllerFX methodology",
        )
        
        # Encode image
        b64_image = base64.b64encode(chart_image).decode('utf-8')
        
        # Call LLM with image
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
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        response = await self._llm.chat_async(
            messages=messages,
            model=self._model,
            max_tokens=3000,
        )
        
        # Parse response
        analysis_data = self._parse_json_response(response)
        
        analysis = TradeOutcomeAnalysis(
            trade_id=str(trade.id),
            outcome=outcome,
            pnl_percent=pnl_percent,
            setup_was_valid=analysis_data.get("setup_was_valid", False),
            entry_was_good=analysis_data.get("entry_was_good", False),
            stop_was_correct=analysis_data.get("stop_was_correct", False),
            market_conditions_favorable=analysis_data.get("market_conditions_favorable", False),
            chart_observations=analysis_data.get("chart_observations", []),
            success_factors=analysis_data.get("success_factors", []),
            failure_factors=analysis_data.get("failure_factors", []),
            improvements=analysis_data.get("improvements", []),
            lesson=analysis_data.get("lesson", "No lesson extracted"),
            confidence=analysis_data.get("confidence", 0.5),
            tags=analysis_data.get("tags", []),
        )
        
        # Update knowledge base
        await self._update_knowledge(trade, analysis)
        
        return analysis
    
    async def learn_from_trade_history(
        self,
        trades: List[Trade],
        pattern_name: str,
    ) -> Dict[str, Any]:
        """Analyze multiple trades to find patterns in what works.
        
        Args:
            trades: List of completed trades for a pattern
            pattern_name: Name of the setup/pattern
            
        Returns:
            Learned insights about the pattern
        """
        logger.info(f"Learning from {len(trades)} trades of {pattern_name}")
        
        # Build trade history summary
        trade_summaries = []
        for trade in trades:
            pnl = float(trade.realized_pnl_percent) if trade.realized_pnl_percent else 0
            outcome = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BE"
            
            trade_summaries.append({
                "outcome": outcome,
                "pnl_percent": pnl,
                "entry_price": str(trade.entry_price),
                "exit_price": str(trade.exit_price),
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else "N/A",
            })
        
        prompt = PATTERN_LEARNING_PROMPT.format(
            pattern_name=pattern_name,
            trade_history=json.dumps(trade_summaries, indent=2),
        )
        
        response = await self._llm.chat_async(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            max_tokens=2000,
        )
        
        insights = self._parse_json_response(response)
        
        # Update pattern stats
        if pattern_name not in self._knowledge.pattern_stats:
            self._knowledge.pattern_stats[pattern_name] = PatternPerformance(pattern_name=pattern_name)
        
        stats = self._knowledge.pattern_stats[pattern_name]
        stats.best_conditions = insights.get("best_conditions", [])
        stats.worst_conditions = insights.get("worst_conditions", [])
        stats.learned_filters = [r["rule"] for r in insights.get("new_rules", [])]
        
        # Save knowledge
        self._save_knowledge()
        
        return insights
    
    def get_learned_rules(self) -> List[Dict[str, Any]]:
        """Get all rules learned from trade analysis."""
        return self._knowledge.rules_learned
    
    def get_pattern_stats(self, pattern_name: str) -> Optional[PatternPerformance]:
        """Get performance stats for a pattern."""
        return self._knowledge.pattern_stats.get(pattern_name)
    
    def get_recent_lessons(self, limit: int = 10) -> List[str]:
        """Get the most recent lessons learned."""
        return self._knowledge.recent_lessons[-limit:]
    
    def should_take_trade(
        self,
        setup_type: str,
        conditions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if we should take a trade based on learned knowledge.
        
        Args:
            setup_type: Type of setup (Breakout, Fakeout, etc.)
            conditions: Current market conditions
            
        Returns:
            Recommendation with reasoning
        """
        stats = self._knowledge.pattern_stats.get(setup_type)
        
        if not stats:
            return {
                "should_take": True,
                "confidence": 0.5,
                "reason": "No historical data for this pattern yet",
            }
        
        # Check against worst conditions
        warnings = []
        for bad_condition in stats.worst_conditions:
            # Simple keyword matching (could be more sophisticated)
            for key, value in conditions.items():
                if bad_condition.lower() in str(value).lower():
                    warnings.append(f"Warning: {bad_condition}")
        
        # Check for best conditions
        confirmations = []
        for good_condition in stats.best_conditions:
            for key, value in conditions.items():
                if good_condition.lower() in str(value).lower():
                    confirmations.append(f"Confirmed: {good_condition}")
        
        # Decision
        if len(warnings) > len(confirmations):
            return {
                "should_take": False,
                "confidence": min(0.9, 0.5 + len(warnings) * 0.1),
                "reason": f"Conditions match known failure patterns: {warnings}",
                "warnings": warnings,
                "confirmations": confirmations,
            }
        else:
            return {
                "should_take": True,
                "confidence": min(0.9, 0.5 + len(confirmations) * 0.1),
                "reason": f"Conditions match successful trade patterns",
                "warnings": warnings,
                "confirmations": confirmations,
                "expected_win_rate": stats.win_rate,
            }
    
    async def _update_knowledge(
        self,
        trade: Trade,
        analysis: TradeOutcomeAnalysis,
    ) -> None:
        """Update knowledge base with new analysis."""
        self._knowledge.total_trades_analyzed += 1
        
        # Add lesson to recent
        self._knowledge.recent_lessons.append(analysis.lesson)
        if len(self._knowledge.recent_lessons) > 50:
            self._knowledge.recent_lessons = self._knowledge.recent_lessons[-50:]
        
        # Update pattern stats
        setup_type = trade.setup_type if hasattr(trade, 'setup_type') else "Unknown"
        if setup_type not in self._knowledge.pattern_stats:
            self._knowledge.pattern_stats[setup_type] = PatternPerformance(pattern_name=setup_type)
        
        stats = self._knowledge.pattern_stats[setup_type]
        stats.total_trades += 1
        stats.total_pnl += analysis.pnl_percent
        
        if analysis.outcome == "win":
            stats.winning_trades += 1
        elif analysis.outcome == "loss":
            stats.losing_trades += 1
        
        stats.win_rate = stats.winning_trades / stats.total_trades if stats.total_trades > 0 else 0
        
        # Extract rules from analysis
        if analysis.improvements:
            for improvement in analysis.improvements:
                rule = {
                    "source": f"Trade {trade.id}",
                    "outcome": analysis.outcome,
                    "rule": improvement,
                    "confidence": analysis.confidence,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._knowledge.rules_learned.append(rule)
        
        # Save
        self._save_knowledge()
    
    def _parse_json_response(self, response: Any) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            text = response.content[0].text if hasattr(response, 'content') else str(response)
            
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start:json_end])
            
            return {}
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {}
    
    def _load_knowledge(self) -> TradingKnowledge:
        """Load knowledge from disk."""
        if self._knowledge_path.exists():
            try:
                with open(self._knowledge_path) as f:
                    data = json.load(f)
                
                knowledge = TradingKnowledge(
                    total_trades_analyzed=data.get("total_trades_analyzed", 0),
                    rules_learned=data.get("rules_learned", []),
                    recent_lessons=data.get("recent_lessons", []),
                )
                
                for name, stats_data in data.get("pattern_stats", {}).items():
                    knowledge.pattern_stats[name] = PatternPerformance(
                        pattern_name=name,
                        total_trades=stats_data.get("total_trades", 0),
                        winning_trades=stats_data.get("winning_trades", 0),
                        losing_trades=stats_data.get("losing_trades", 0),
                        total_pnl=stats_data.get("total_pnl", 0.0),
                        win_rate=stats_data.get("win_rate", 0.0),
                        best_conditions=stats_data.get("best_conditions", []),
                        worst_conditions=stats_data.get("worst_conditions", []),
                        learned_filters=stats_data.get("learned_filters", []),
                    )
                
                return knowledge
            except Exception as e:
                logger.warning(f"Failed to load knowledge: {e}")
        
        return TradingKnowledge()
    
    def _save_knowledge(self) -> None:
        """Save knowledge to disk."""
        data = {
            "total_trades_analyzed": self._knowledge.total_trades_analyzed,
            "rules_learned": self._knowledge.rules_learned,
            "recent_lessons": self._knowledge.recent_lessons,
            "pattern_stats": {
                name: {
                    "total_trades": stats.total_trades,
                    "winning_trades": stats.winning_trades,
                    "losing_trades": stats.losing_trades,
                    "total_pnl": stats.total_pnl,
                    "win_rate": stats.win_rate,
                    "best_conditions": stats.best_conditions,
                    "worst_conditions": stats.worst_conditions,
                    "learned_filters": stats.learned_filters,
                }
                for name, stats in self._knowledge.pattern_stats.items()
            },
        }
        
        with open(self._knowledge_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved knowledge: {self._knowledge.total_trades_analyzed} trades analyzed")
