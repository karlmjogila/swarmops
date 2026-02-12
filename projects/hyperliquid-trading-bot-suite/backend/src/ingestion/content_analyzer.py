"""
Content analysis utilities for determining content type and processing strategy.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from ..types import SourceType


logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Types of trading content we can analyze."""
    STRATEGY_GUIDE = "strategy_guide"
    PATTERN_EXPLANATION = "pattern_explanation"
    MARKET_ANALYSIS = "market_analysis"
    TRADING_RULES = "trading_rules"
    CASE_STUDY = "case_study"
    GENERAL_EDUCATIONAL = "general_educational"


class ContentQuality(str, Enum):
    """Quality assessment of content for strategy extraction."""
    HIGH = "high"          # Clear, actionable strategies with specific rules
    MEDIUM = "medium"      # Good content but may need clarification
    LOW = "low"           # Vague or conceptual content
    UNSUITABLE = "unsuitable"  # No actionable trading information


class ContentAnalyzer:
    """
    Analyzes trading content to determine processing strategy and quality.
    """
    
    # Keywords that indicate different content types
    STRATEGY_KEYWORDS = [
        "entry", "exit", "stop loss", "take profit", "setup", "pattern",
        "strategy", "trade", "signal", "condition", "rule"
    ]
    
    PATTERN_KEYWORDS = [
        "candle", "wick", "body", "doji", "hammer", "engulfing", "inside bar",
        "outside bar", "pin bar", "shooting star", "hanging man", "marubozu"
    ]
    
    STRUCTURE_KEYWORDS = [
        "support", "resistance", "breakout", "breakdown", "trend", "range",
        "structure", "level", "zone", "supply", "demand", "liquidity"
    ]
    
    ICT_KEYWORDS = [
        "ict", "inner circle trader", "fair value gap", "order block", "breaker",
        "mitigation", "displacement", "imbalance", "inefficiency", "inducement",
        "manipulation", "accumulation", "distribution", "smart money", "liquidity grab"
    ]
    
    TIMEFRAME_KEYWORDS = [
        "1m", "5m", "15m", "30m", "1h", "4h", "daily", "weekly", "monthly",
        "minute", "hour", "day", "week", "month", "timeframe", "tf"
    ]
    
    RISK_KEYWORDS = [
        "risk", "position size", "stop loss", "sl", "take profit", "tp",
        "risk reward", "r:r", "money management", "drawdown", "leverage"
    ]
    
    # Quality indicators
    HIGH_QUALITY_INDICATORS = [
        "specific entry", "exact rules", "backtested", "win rate", "profit factor",
        "precise conditions", "step by step", "detailed explanation"
    ]
    
    LOW_QUALITY_INDICATORS = [
        "general advice", "usually", "sometimes", "might work", "depends",
        "market feeling", "gut instinct", "experience tells"
    ]
    
    def __init__(self):
        """Initialize the content analyzer."""
        self.min_content_length = 100  # Minimum viable content length
        self.max_chunk_size = 4000     # Maximum size for LLM processing
    
    def analyze_content(self, content: str, source_type: SourceType) -> Dict[str, Any]:
        """
        Analyze content to determine type, quality, and processing strategy.
        
        Args:
            content: Text content to analyze
            source_type: Source type (PDF, video, etc.)
            
        Returns:
            Analysis results with recommendations
        """
        logger.info(f"Analyzing {len(content)} characters of {source_type.value} content")
        
        # Basic content metrics
        word_count = len(content.split())
        sentence_count = len(re.split(r'[.!?]+', content))
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Content type classification
        content_type = self._classify_content_type(content)
        
        # Quality assessment
        quality = self._assess_content_quality(content)
        
        # Extract key topics
        topics = self._extract_topics(content)
        
        # Timeframe mentions
        timeframes = self._extract_timeframes(content)
        
        # Strategy indicators
        strategy_indicators = self._find_strategy_indicators(content)
        
        # Processing recommendations
        processing_strategy = self._recommend_processing_strategy(
            content, content_type, quality, source_type
        )
        
        analysis = {
            "content_type": content_type,
            "quality": quality,
            "metrics": {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "avg_sentence_length": avg_sentence_length,
                "character_count": len(content)
            },
            "topics": topics,
            "timeframes": timeframes,
            "strategy_indicators": strategy_indicators,
            "processing_strategy": processing_strategy,
            "extraction_confidence": self._estimate_extraction_confidence(
                content_type, quality, strategy_indicators
            )
        }
        
        logger.debug(f"Content analysis: {content_type.value}, {quality.value}, confidence: {analysis['extraction_confidence']}")
        return analysis
    
    def _classify_content_type(self, content: str) -> ContentType:
        """Classify the type of trading content."""
        content_lower = content.lower()
        
        # Count keyword occurrences
        strategy_score = sum(1 for kw in self.STRATEGY_KEYWORDS if kw in content_lower)
        pattern_score = sum(1 for kw in self.PATTERN_KEYWORDS if kw in content_lower)
        structure_score = sum(1 for kw in self.STRUCTURE_KEYWORDS if kw in content_lower)
        ict_score = sum(1 for kw in self.ICT_KEYWORDS if kw in content_lower)
        
        # Normalize by content length
        total_words = len(content.split())
        strategy_density = strategy_score / max(total_words / 100, 1)
        pattern_density = pattern_score / max(total_words / 100, 1)
        structure_density = structure_score / max(total_words / 100, 1)
        ict_density = ict_score / max(total_words / 100, 1)
        
        # Specific indicators
        has_step_by_step = bool(re.search(r'step\s*\d+|first.*second.*third|1\.|2\.|3\.', content_lower))
        has_rules = bool(re.search(r'rule\s*\d+|rule:|rules?', content_lower))
        has_examples = 'example' in content_lower or 'for instance' in content_lower
        
        # Classification logic
        if has_step_by_step or has_rules:
            if strategy_density > 2:
                return ContentType.STRATEGY_GUIDE
            else:
                return ContentType.TRADING_RULES
        
        if pattern_density > 1.5:
            return ContentType.PATTERN_EXPLANATION
        
        if structure_density > 1.5 or ict_density > 1:
            return ContentType.MARKET_ANALYSIS
        
        if has_examples and strategy_density > 1:
            return ContentType.CASE_STUDY
        
        return ContentType.GENERAL_EDUCATIONAL
    
    def _assess_content_quality(self, content: str) -> ContentQuality:
        """Assess the quality of content for strategy extraction."""
        content_lower = content.lower()
        
        # Check for quality indicators
        high_quality_count = sum(1 for indicator in self.HIGH_QUALITY_INDICATORS 
                               if indicator in content_lower)
        low_quality_count = sum(1 for indicator in self.LOW_QUALITY_INDICATORS 
                              if indicator in content_lower)
        
        # Check for specific numerical values
        has_percentages = bool(re.search(r'\d+%|\d+\s*percent', content))
        has_numbers = len(re.findall(r'\d+', content)) / max(len(content.split()) / 20, 1)
        has_specific_levels = bool(re.search(r'\d+\.\d+|\d+\s*pips|\d+\s*points', content))
        
        # Check for actionable language
        action_words = ['buy', 'sell', 'enter', 'exit', 'place', 'set', 'move']
        action_count = sum(1 for word in action_words if word in content_lower)
        
        # Calculate quality score
        quality_score = high_quality_count * 2
        quality_score += 1 if has_percentages else 0
        quality_score += min(has_numbers, 3)  # Cap numerical score
        quality_score += 1 if has_specific_levels else 0
        quality_score += min(action_count / 5, 2)  # Cap action score
        quality_score -= low_quality_count
        
        # Length penalty for very short content
        if len(content) < self.min_content_length:
            return ContentQuality.UNSUITABLE
        
        # Classification thresholds
        if quality_score >= 6:
            return ContentQuality.HIGH
        elif quality_score >= 3:
            return ContentQuality.MEDIUM
        elif quality_score >= 1:
            return ContentQuality.LOW
        else:
            return ContentQuality.UNSUITABLE
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract key trading topics mentioned in the content."""
        topics = []
        content_lower = content.lower()
        
        # Topic categories
        topic_patterns = {
            "price_action": r"price\s+action|pa\s+",
            "support_resistance": r"support|resistance|s/r",
            "breakouts": r"breakout|breakdown|break\s+out",
            "patterns": r"pattern|formation|setup",
            "indicators": r"indicator|oscillator|moving\s+average|ma\s+",
            "risk_management": r"risk\s+management|money\s+management|position\s+sizing",
            "psychology": r"psychology|emotion|fear|greed|discipline",
            "backtesting": r"backtest|historical\s+data|testing",
            "automation": r"automat|algorithm|bot|system"
        }
        
        for topic, pattern in topic_patterns.items():
            if re.search(pattern, content_lower):
                topics.append(topic)
        
        return topics
    
    def _extract_timeframes(self, content: str) -> List[str]:
        """Extract timeframe mentions from content."""
        timeframes = []
        
        # Timeframe patterns
        tf_patterns = [
            r'\b(\d+)\s*m(?:in)?(?:ute)?s?\b',      # 1m, 5min, 30 minutes
            r'\b(\d+)\s*h(?:our)?s?\b',             # 1h, 4 hours
            r'\b(\d+)\s*d(?:ay)?s?\b',              # 1d, daily
            r'\b(\d+)\s*w(?:eek)?s?\b',             # 1w, weekly
            r'\bM(\d+)\b',                          # M1, M5, M15
            r'\bH(\d+)\b',                          # H1, H4
            r'\bD(\d+)\b',                          # D1
            r'\b(daily|weekly|monthly|hourly)\b',    # Named timeframes
        ]
        
        for pattern in tf_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ''.join(match)
                if match and match not in timeframes:
                    timeframes.append(match)
        
        return timeframes[:10]  # Limit to prevent noise
    
    def _find_strategy_indicators(self, content: str) -> Dict[str, List[str]]:
        """Find indicators of specific trading strategies."""
        indicators = {
            "entry_signals": [],
            "exit_signals": [],
            "conditions": [],
            "patterns": []
        }
        
        content_lower = content.lower()
        
        # Entry signal patterns
        entry_patterns = [
            r"enter\s+(?:when|if|at)\s+([^.!?]+)",
            r"buy\s+(?:when|if|at)\s+([^.!?]+)",
            r"go\s+long\s+(?:when|if|at)\s+([^.!?]+)",
            r"entry\s+(?:condition|signal|rule)[:]\s*([^.!?]+)"
        ]
        
        for pattern in entry_patterns:
            matches = re.findall(pattern, content_lower)
            indicators["entry_signals"].extend(matches[:3])  # Limit results
        
        # Exit signal patterns
        exit_patterns = [
            r"exit\s+(?:when|if|at)\s+([^.!?]+)",
            r"sell\s+(?:when|if|at)\s+([^.!?]+)",
            r"take\s+profit\s+(?:at|when)\s+([^.!?]+)",
            r"stop\s+loss\s+(?:at|when)\s+([^.!?]+)"
        ]
        
        for pattern in exit_patterns:
            matches = re.findall(pattern, content_lower)
            indicators["exit_signals"].extend(matches[:3])
        
        # General conditions
        condition_patterns = [
            r"if\s+([^,]+),?\s+then",
            r"when\s+([^,]+),?\s+(?:then|we|you)",
            r"condition[:]\s*([^.!?]+)"
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, content_lower)
            indicators["conditions"].extend(matches[:5])
        
        # Pattern mentions
        for keyword in self.PATTERN_KEYWORDS:
            if keyword in content_lower:
                indicators["patterns"].append(keyword)
        
        return indicators
    
    def _recommend_processing_strategy(
        self, 
        content: str, 
        content_type: ContentType,
        quality: ContentQuality,
        source_type: SourceType
    ) -> Dict[str, Any]:
        """Recommend processing strategy based on analysis."""
        
        strategy = {
            "chunk_size": self.max_chunk_size,
            "use_refinement": False,
            "extract_patterns": True,
            "extract_rules": True,
            "confidence_threshold": 0.5,
            "processing_notes": []
        }
        
        # Adjust based on content type
        if content_type == ContentType.STRATEGY_GUIDE:
            strategy["extract_rules"] = True
            strategy["use_refinement"] = True
            strategy["confidence_threshold"] = 0.6
            strategy["processing_notes"].append("High-value strategy content")
        
        elif content_type == ContentType.PATTERN_EXPLANATION:
            strategy["extract_patterns"] = True
            strategy["chunk_size"] = 3000  # Smaller chunks for detailed analysis
            strategy["processing_notes"].append("Focus on pattern details")
        
        elif content_type == ContentType.TRADING_RULES:
            strategy["extract_rules"] = True
            strategy["use_refinement"] = True
            strategy["processing_notes"].append("Extract specific trading rules")
        
        # Adjust based on quality
        if quality == ContentQuality.HIGH:
            strategy["confidence_threshold"] = 0.7
            strategy["use_refinement"] = True
        elif quality == ContentQuality.LOW:
            strategy["confidence_threshold"] = 0.3
            strategy["processing_notes"].append("Low quality - extract with caution")
        elif quality == ContentQuality.UNSUITABLE:
            strategy["extract_patterns"] = False
            strategy["extract_rules"] = False
            strategy["processing_notes"].append("Content not suitable for extraction")
        
        # Adjust based on source type
        if source_type == SourceType.VIDEO:
            strategy["chunk_size"] = 2000  # Smaller chunks for transcript
            strategy["processing_notes"].append("Video transcript - may have noise")
        elif source_type == SourceType.PDF:
            strategy["chunk_size"] = 4000  # Larger chunks for structured text
        
        # Content length adjustments
        if len(content) > 10000:
            strategy["chunk_size"] = 3000  # Smaller chunks for very long content
            strategy["processing_notes"].append("Long content - process in chunks")
        
        return strategy
    
    def _estimate_extraction_confidence(
        self,
        content_type: ContentType,
        quality: ContentQuality,
        strategy_indicators: Dict[str, List[str]]
    ) -> float:
        """Estimate confidence in successful strategy extraction."""
        
        base_confidence = 0.5
        
        # Content type modifiers
        type_modifiers = {
            ContentType.STRATEGY_GUIDE: 0.3,
            ContentType.TRADING_RULES: 0.25,
            ContentType.CASE_STUDY: 0.15,
            ContentType.PATTERN_EXPLANATION: 0.1,
            ContentType.MARKET_ANALYSIS: 0.05,
            ContentType.GENERAL_EDUCATIONAL: -0.1
        }
        
        # Quality modifiers
        quality_modifiers = {
            ContentQuality.HIGH: 0.3,
            ContentQuality.MEDIUM: 0.1,
            ContentQuality.LOW: -0.1,
            ContentQuality.UNSUITABLE: -0.5
        }
        
        # Strategy indicator bonus
        indicator_bonus = 0
        indicator_bonus += min(len(strategy_indicators["entry_signals"]) * 0.05, 0.15)
        indicator_bonus += min(len(strategy_indicators["exit_signals"]) * 0.05, 0.15)
        indicator_bonus += min(len(strategy_indicators["conditions"]) * 0.03, 0.1)
        indicator_bonus += min(len(strategy_indicators["patterns"]) * 0.02, 0.1)
        
        # Calculate final confidence
        confidence = base_confidence
        confidence += type_modifiers.get(content_type, 0)
        confidence += quality_modifiers.get(quality, 0)
        confidence += indicator_bonus
        
        # Clamp to valid range
        return max(0.1, min(0.95, confidence))
    
    def should_process_content(self, analysis: Dict[str, Any]) -> bool:
        """Determine if content should be processed for strategy extraction."""
        quality = ContentQuality(analysis["quality"])
        confidence = analysis["extraction_confidence"]
        
        if quality == ContentQuality.UNSUITABLE:
            return False
        
        if confidence < 0.3:
            return False
        
        # Check minimum content requirements
        metrics = analysis["metrics"]
        if metrics["word_count"] < 50:
            return False
        
        return True
    
    def chunk_content(self, content: str, max_chunk_size: int = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Split content into optimal chunks for processing.
        
        Args:
            content: Content to chunk
            max_chunk_size: Maximum size per chunk
            
        Returns:
            List of (chunk_content, chunk_metadata) tuples
        """
        if max_chunk_size is None:
            max_chunk_size = self.max_chunk_size
        
        # If content is smaller than chunk size, return as single chunk
        if len(content) <= max_chunk_size:
            return [(content, {"chunk_index": 0, "total_chunks": 1})]
        
        chunks = []
        
        # Try to split on sentences first
        sentences = re.split(r'[.!?]+', content)
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            potential_chunk = current_chunk + ". " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > max_chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append((
                    current_chunk.strip(),
                    {"chunk_index": chunk_index, "chunk_start": sentence[:50]}
                ))
                current_chunk = sentence
                chunk_index += 1
            else:
                current_chunk = potential_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append((
                current_chunk.strip(),
                {"chunk_index": chunk_index, "chunk_start": current_chunk[:50]}
            ))
        
        # Add total_chunks to all metadata
        for _, metadata in chunks:
            metadata["total_chunks"] = len(chunks)
        
        logger.debug(f"Split content into {len(chunks)} chunks")
        return chunks