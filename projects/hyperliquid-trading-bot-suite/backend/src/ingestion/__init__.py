"""
Ingestion pipeline for extracting trading strategies from content.

This module provides:
- LLM-powered strategy extraction using Claude
- Content analysis and quality assessment
- Orchestrated processing pipeline
- Support for PDF and video content
"""

from .strategy_extractor import LLMStrategyExtractor, StrategyExtractionError
from .content_analyzer import ContentAnalyzer, ContentType, ContentQuality
from .ingestion_orchestrator import IngestionOrchestrator, IngestionError, create_ingestion_orchestrator
from .extraction_prompts import get_extraction_prompt, get_refinement_prompts

__all__ = [
    # Main classes
    "LLMStrategyExtractor",
    "ContentAnalyzer", 
    "IngestionOrchestrator",
    
    # Factory functions
    "create_ingestion_orchestrator",
    
    # Enums
    "ContentType",
    "ContentQuality",
    
    # Exceptions
    "StrategyExtractionError",
    "IngestionError",
    
    # Utilities
    "get_extraction_prompt",
    "get_refinement_prompts",
]