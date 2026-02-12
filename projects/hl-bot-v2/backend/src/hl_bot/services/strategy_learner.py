"""Strategy Learning Engine - Deep comprehension of trading methodologies.

This module builds a comprehensive understanding of trading strategies from
multiple sources (videos, PDFs, images) and generates executable detection code.

The goal is not just rule extraction, but TRUE UNDERSTANDING:
- WHY do setups work?
- WHEN to take them vs skip them?
- HOW do different concepts connect?
- WHAT does a valid setup LOOK like?
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from hl_bot.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ============================================================================
# Knowledge Structures
# ============================================================================


@dataclass
class Concept:
    """A trading concept extracted from content."""
    id: str
    name: str
    category: str  # setup, entry, exit, pattern, timing, risk, psychology
    description: str
    source: str  # which content it came from
    related_concepts: List[str] = field(default_factory=list)
    visual_examples: List[str] = field(default_factory=list)  # base64 images
    code_implementation: Optional[str] = None
    confidence: float = 0.0


@dataclass
class StrategyKnowledge:
    """Complete knowledge base for a trading strategy."""
    id: str
    name: str
    sources: List[str]
    
    # Core understanding
    philosophy: str  # Why does this strategy work?
    market_conditions: str  # When does it work best?
    edge_explanation: str  # What's the statistical edge?
    
    # Concepts
    concepts: Dict[str, Concept] = field(default_factory=dict)
    
    # Relationships
    concept_graph: Dict[str, List[str]] = field(default_factory=dict)  # concept_id -> related_ids
    
    # Workflow
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Generated code
    detection_code: Optional[str] = None
    signal_code: Optional[str] = None
    
    # Validation
    validated: bool = False
    validation_results: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Prompts for Deep Understanding
# ============================================================================


COMPREHENSION_PROMPT = """You are a trading strategy researcher building deep understanding of a methodology.

You have access to the following content about a trading strategy:

## Content
{content}

## Your Task

Build a COMPLETE understanding of this strategy. Don't just extract rules - understand the ENTIRE system:

### 1. Philosophy & Edge
- WHY does this strategy work? What market inefficiency does it exploit?
- What is the psychological edge?
- What makes it different from random trading?

### 2. Core Concepts
For EACH concept mentioned (setups, patterns, entries, etc.):
- Name and category
- Detailed description
- When to use it
- When NOT to use it
- How it connects to other concepts
- Visual characteristics (what does it LOOK like on a chart?)

### 3. Concept Relationships
How do concepts connect? Build a mental model:
- What leads to what?
- What confirms what?
- What invalidates what?

### 4. Complete Workflow
Step-by-step process from market open to trade execution:
- Pre-session preparation
- Analysis sequence
- Setup identification
- Entry triggers
- Position management
- Exit conditions

### 5. Risk & Psychology
- Position sizing rules
- Maximum risk parameters
- Emotional management
- When to sit out

### 6. Visual Pattern Recognition
Describe what each setup LOOKS like visually:
- Candle shapes and wicks
- Price structure
- Range characteristics
- What to look for on the chart

Respond with detailed JSON:
{{
    "philosophy": "Why this strategy works...",
    "market_conditions": "Best conditions for this strategy...",
    "edge_explanation": "The statistical edge comes from...",
    "concepts": [
        {{
            "name": "Concept Name",
            "category": "setup|entry|exit|pattern|timing|risk|psychology",
            "description": "Detailed description...",
            "when_to_use": "Use when...",
            "when_not_to_use": "Don't use when...",
            "visual_characteristics": "On the chart, look for...",
            "related_concepts": ["Other Concept 1", "Other Concept 2"]
        }}
    ],
    "workflow": [
        {{"step": 1, "action": "...", "details": "..."}},
        {{"step": 2, "action": "...", "details": "..."}}
    ],
    "risk_rules": {{
        "max_risk_per_trade": "...",
        "max_daily_risk": "...",
        "position_sizing": "...",
        "when_to_stop": "..."
    }},
    "psychology": {{
        "key_principles": ["..."],
        "emotional_traps": ["..."],
        "discipline_rules": ["..."]
    }}
}}
"""


CODE_GENERATION_PROMPT = """You are an expert Python developer AND trading systems architect.

You have deeply understood a trading strategy. Now generate production-ready Python code to detect setups.

## Strategy Understanding
{understanding}

## Your Task

Generate a complete Python module that:

1. **Detects Setups** - Identifies Breakout, Fakeout, Onion setups from candle data
2. **Validates Conditions** - Checks all entry conditions are met
3. **Calculates Levels** - Computes entry, stop loss, take profit
4. **Scores Confluence** - Rates setup quality 0-100

## Requirements

- Use only standard libraries + numpy/pandas
- Type hints on all functions
- Docstrings explaining the logic
- Handle edge cases gracefully
- Return structured results

## Candle Data Format
```python
@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

## Expected Output Structure
```python
@dataclass
class SetupDetection:
    setup_type: str  # "BREAKOUT", "FAKEOUT", "ONION", "NONE"
    direction: str  # "LONG", "SHORT", "NONE"
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    reasoning: str
    conditions_met: List[str]
    conditions_failed: List[str]
```

Generate the complete module code:
"""


VISUAL_LEARNING_PROMPT = """You are learning to visually recognize trading setups from chart examples.

## Chart Image
[Image attached]

## Strategy Context
{strategy_context}

## Your Task

Study this chart example and learn:

1. **What setup is shown?** (Breakout/Fakeout/Onion/Other)
2. **Visual characteristics:**
   - Range boundaries (where?)
   - Candle that triggered setup (which one? what does it look like?)
   - Wick characteristics (small/steeper?)
   - Entry point (where exactly?)
   - Stop loss placement (where?)
   - Take profit zone (where?)

3. **Pattern recognition features:**
   - How many candles in the range?
   - What's the range size relative to candles?
   - How did price behave at support/resistance?
   - What confirmed the entry?

4. **What makes this a VALID setup?**
   - List the conditions that are met
   - Note anything that could have invalidated it

Respond with detailed pattern recognition data that can be used to identify similar setups:
{{
    "setup_type": "...",
    "direction": "LONG|SHORT",
    "visual_features": {{
        "range_candles": int,
        "range_size_atr_multiple": float,
        "breakout_candle_body_percent": float,
        "wick_type": "small|steeper",
        "wick_direction": "up|down",
        "close_location": "above_range|below_range|at_support|at_resistance"
    }},
    "detection_rules": [
        "Rule 1: ...",
        "Rule 2: ..."
    ],
    "key_visual_cues": ["...", "..."]
}}
"""


# ============================================================================
# Strategy Learner
# ============================================================================


class StrategyLearner:
    """Learns and deeply understands trading strategies from content."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: str = "claude-sonnet-4-20250514",
        knowledge_dir: Optional[Path] = None,
    ):
        self._llm = llm_client or LLMClient()
        self._model = model
        self._knowledge_dir = knowledge_dir or Path("/tmp/strategy_knowledge")
        self._knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        self._current_knowledge: Optional[StrategyKnowledge] = None
        
        logger.info(f"Strategy Learner initialized with model: {model}")
    
    async def learn_from_content(
        self,
        content: str,
        source_name: str,
        content_type: str = "text",  # text, transcript, pdf_text
    ) -> StrategyKnowledge:
        """Learn strategy from text content (transcripts, PDFs, etc.)."""
        logger.info(f"Learning from {source_name} ({content_type})")
        
        # Build deep understanding
        understanding = await self._build_understanding(content)
        
        # Create or update knowledge base
        if self._current_knowledge is None:
            self._current_knowledge = StrategyKnowledge(
                id=str(uuid4()),
                name=source_name,
                sources=[source_name],
                philosophy=understanding.get("philosophy", ""),
                market_conditions=understanding.get("market_conditions", ""),
                edge_explanation=understanding.get("edge_explanation", ""),
            )
        else:
            self._current_knowledge.sources.append(source_name)
        
        # Add concepts
        for concept_data in understanding.get("concepts", []):
            concept = Concept(
                id=str(uuid4()),
                name=concept_data["name"],
                category=concept_data.get("category", "unknown"),
                description=concept_data.get("description", ""),
                source=source_name,
                related_concepts=concept_data.get("related_concepts", []),
                confidence=0.8,
            )
            self._current_knowledge.concepts[concept.name] = concept
        
        # Add workflow
        self._current_knowledge.workflow_steps = understanding.get("workflow", [])
        
        # Save knowledge
        await self._save_knowledge()
        
        return self._current_knowledge
    
    async def learn_from_image(
        self,
        image_bytes: bytes,
        source_name: str,
    ) -> Dict[str, Any]:
        """Learn visual patterns from chart images."""
        import base64
        
        logger.info(f"Learning visual patterns from {source_name}")
        
        # Get current strategy context
        context = ""
        if self._current_knowledge:
            context = f"Strategy: {self._current_knowledge.name}\n"
            context += f"Philosophy: {self._current_knowledge.philosophy}\n"
            context += f"Concepts: {', '.join(self._current_knowledge.concepts.keys())}"
        
        # Analyze image
        b64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = VISUAL_LEARNING_PROMPT.format(strategy_context=context)
        
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
        
        return self._parse_json_response(response)
    
    async def generate_detection_code(self) -> str:
        """Generate Python code to detect the learned strategy."""
        if not self._current_knowledge:
            raise ValueError("No strategy knowledge loaded. Call learn_from_content first.")
        
        logger.info("Generating detection code from learned strategy")
        
        # Prepare understanding summary
        understanding = {
            "name": self._current_knowledge.name,
            "philosophy": self._current_knowledge.philosophy,
            "concepts": [
                {
                    "name": c.name,
                    "category": c.category,
                    "description": c.description,
                }
                for c in self._current_knowledge.concepts.values()
            ],
            "workflow": self._current_knowledge.workflow_steps,
        }
        
        prompt = CODE_GENERATION_PROMPT.format(
            understanding=json.dumps(understanding, indent=2)
        )
        
        response = await self._llm.chat_async(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            max_tokens=8000,
        )
        
        # Extract code from response
        code = self._extract_code(response)
        
        # Store in knowledge
        self._current_knowledge.detection_code = code
        await self._save_knowledge()
        
        return code
    
    async def validate_code(
        self,
        code: str,
        test_candles: List[Any],
        expected_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate generated code against test cases."""
        logger.info("Validating generated detection code")
        
        results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "details": [],
        }
        
        # Create a temporary module
        try:
            exec_globals = {}
            exec(code, exec_globals)
            
            # Look for detect_setup function
            detect_func = exec_globals.get("detect_setup")
            if not detect_func:
                results["errors"].append("No detect_setup function found in generated code")
                return results
            
            # Run tests
            for i, (candles, expected) in enumerate(zip(test_candles, expected_results)):
                try:
                    result = detect_func(candles)
                    
                    # Compare with expected
                    if result.setup_type == expected.get("setup_type"):
                        results["passed"] += 1
                        results["details"].append({
                            "test": i,
                            "status": "passed",
                            "expected": expected,
                            "got": result,
                        })
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "test": i,
                            "status": "failed",
                            "expected": expected,
                            "got": result,
                        })
                except Exception as e:
                    results["errors"].append(f"Test {i}: {str(e)}")
        
        except Exception as e:
            results["errors"].append(f"Code execution error: {str(e)}")
        
        # Update knowledge validation status
        if self._current_knowledge:
            self._current_knowledge.validated = results["failed"] == 0 and not results["errors"]
            self._current_knowledge.validation_results = results
            await self._save_knowledge()
        
        return results
    
    async def _build_understanding(self, content: str) -> Dict[str, Any]:
        """Build deep understanding of strategy from content."""
        prompt = COMPREHENSION_PROMPT.format(content=content[:50000])  # Limit content size
        
        response = await self._llm.chat_async(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            max_tokens=8000,
        )
        
        return self._parse_json_response(response)
    
    def _parse_json_response(self, response: Any) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            text = response.content[0].text if hasattr(response, 'content') else str(response)
            
            # Find JSON in response
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start:json_end])
            
            return {}
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {}
    
    def _extract_code(self, response: Any) -> str:
        """Extract Python code from LLM response."""
        text = response.content[0].text if hasattr(response, 'content') else str(response)
        
        # Look for code blocks
        if "```python" in text:
            start = text.find("```python") + 9
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        
        return text
    
    async def _save_knowledge(self) -> None:
        """Save knowledge to disk."""
        if not self._current_knowledge:
            return
        
        path = self._knowledge_dir / f"{self._current_knowledge.id}.json"
        
        data = {
            "id": self._current_knowledge.id,
            "name": self._current_knowledge.name,
            "sources": self._current_knowledge.sources,
            "philosophy": self._current_knowledge.philosophy,
            "market_conditions": self._current_knowledge.market_conditions,
            "edge_explanation": self._current_knowledge.edge_explanation,
            "concepts": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "category": v.category,
                    "description": v.description,
                    "source": v.source,
                    "related_concepts": v.related_concepts,
                }
                for k, v in self._current_knowledge.concepts.items()
            },
            "workflow_steps": self._current_knowledge.workflow_steps,
            "detection_code": self._current_knowledge.detection_code,
            "validated": self._current_knowledge.validated,
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved knowledge to {path}")
    
    async def load_knowledge(self, knowledge_id: str) -> Optional[StrategyKnowledge]:
        """Load knowledge from disk."""
        path = self._knowledge_dir / f"{knowledge_id}.json"
        
        if not path.exists():
            return None
        
        with open(path) as f:
            data = json.load(f)
        
        self._current_knowledge = StrategyKnowledge(
            id=data["id"],
            name=data["name"],
            sources=data["sources"],
            philosophy=data["philosophy"],
            market_conditions=data["market_conditions"],
            edge_explanation=data["edge_explanation"],
            detection_code=data.get("detection_code"),
            validated=data.get("validated", False),
        )
        
        # Restore concepts
        for name, concept_data in data.get("concepts", {}).items():
            self._current_knowledge.concepts[name] = Concept(
                id=concept_data["id"],
                name=concept_data["name"],
                category=concept_data["category"],
                description=concept_data["description"],
                source=concept_data["source"],
                related_concepts=concept_data.get("related_concepts", []),
            )
        
        self._current_knowledge.workflow_steps = data.get("workflow_steps", [])
        
        return self._current_knowledge


# ============================================================================
# Convenience Functions
# ============================================================================


async def learn_strategy_from_files(
    transcript_path: Optional[Path] = None,
    pdf_text_path: Optional[Path] = None,
    chart_images: Optional[List[Path]] = None,
    strategy_name: str = "Learned Strategy",
) -> StrategyKnowledge:
    """Learn a complete strategy from multiple content sources.
    
    Args:
        transcript_path: Path to video transcript
        pdf_text_path: Path to extracted PDF text
        chart_images: List of chart image paths
        strategy_name: Name for the strategy
        
    Returns:
        Complete StrategyKnowledge with understanding and generated code
    """
    learner = StrategyLearner()
    
    # Learn from transcript
    if transcript_path and transcript_path.exists():
        content = transcript_path.read_text()
        await learner.learn_from_content(content, "YouTube Course", "transcript")
    
    # Learn from PDF
    if pdf_text_path and pdf_text_path.exists():
        content = pdf_text_path.read_text()
        await learner.learn_from_content(content, "PDF Playbook", "pdf_text")
    
    # Learn from chart images
    if chart_images:
        for img_path in chart_images:
            if img_path.exists():
                img_bytes = img_path.read_bytes()
                await learner.learn_from_image(img_bytes, img_path.name)
    
    # Generate detection code
    await learner.generate_detection_code()
    
    return learner._current_knowledge
