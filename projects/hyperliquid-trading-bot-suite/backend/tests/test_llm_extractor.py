"""
Tests for the LLM strategy extractor implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from src.types import SourceType, EntryType
from src.ingestion import (
    LLMStrategyExtractor, 
    ContentAnalyzer, 
    IngestionOrchestrator,
    ContentType,
    ContentQuality,
    StrategyExtractionError
)
from src.config import Settings


# Sample test data
SAMPLE_STRATEGY_JSON = """
[
  {
    "name": "ICT Liquidity Engulf Strategy",
    "entry_type": "le",
    "description": "Strategy focusing on LE candles that sweep liquidity",
    "confidence": 0.8,
    "conditions": [
      {
        "type": "candle",
        "timeframe": "15m",
        "params": {
          "pattern": "liquidity_engulf",
          "wick_ratio": 0.3,
          "close_position": "upper_quarter",
          "body_size_min": 0.7
        },
        "description": "LE candle with minimal wicks"
      }
    ],
    "confluence_required": [
      {
        "higher_tf": "4h",
        "lower_tf": "15m",
        "bias_required": "bullish",
        "entry_pattern": "LE after pullback"
      }
    ],
    "risk_params": {
      "risk_percent": 2.0,
      "tp_levels": [1.0, 2.0],
      "sl_distance": "structure",
      "max_concurrent": 3
    },
    "tags": ["ict", "liquidity"],
    "source_timestamp": null
  }
]
"""

SAMPLE_CONTENT = """
# ICT Liquidity Engulf Strategy

## Entry Rules
1. Wait for LE candle on 15-minute timeframe
2. Candle must have small wicks (less than 30% of range)
3. Close in upper quarter for bullish setups
4. Confirm 4-hour bias is bullish

## Risk Management
- Risk 2% per trade
- Take profit at 1R and 2R
- Stop loss below LE candle low
"""


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.anthropic_api_key = "test-api-key"
    settings.claude_extraction_model = "claude-3-sonnet-20240229"
    settings.claude_max_tokens = 4000
    settings.claude_temperature = 0.1
    return settings


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text=SAMPLE_STRATEGY_JSON)]
    client.messages.create = AsyncMock(return_value=mock_response)
    return client


class TestContentAnalyzer:
    """Test the content analyzer."""
    
    def test_analyze_strategy_content(self):
        """Test analysis of strategy content."""
        analyzer = ContentAnalyzer()
        
        analysis = analyzer.analyze_content(SAMPLE_CONTENT, SourceType.MANUAL)
        
        assert analysis["content_type"] == ContentType.STRATEGY_GUIDE
        assert analysis["quality"] in [ContentQuality.HIGH, ContentQuality.MEDIUM]
        assert analysis["extraction_confidence"] > 0.5
        assert "ict" in analysis["topics"] or "patterns" in analysis["topics"]
    
    def test_analyze_low_quality_content(self):
        """Test analysis of low-quality content."""
        analyzer = ContentAnalyzer()
        
        poor_content = "Buy low, sell high. Good luck!"
        analysis = analyzer.analyze_content(poor_content, SourceType.MANUAL)
        
        assert analysis["quality"] in [ContentQuality.LOW, ContentQuality.UNSUITABLE]
        assert analysis["extraction_confidence"] < 0.5
    
    def test_extract_timeframes(self):
        """Test timeframe extraction."""
        analyzer = ContentAnalyzer()
        
        content = "Use 15m for entry and 4h for bias. Also check daily trend."
        timeframes = analyzer._extract_timeframes(content)
        
        assert "15" in str(timeframes) or "15m" in timeframes
        assert "4" in str(timeframes) or "4h" in timeframes
    
    def test_content_chunking(self):
        """Test content chunking functionality."""
        analyzer = ContentAnalyzer()
        
        long_content = "This is a sentence. " * 200  # Create long content
        chunks = analyzer.chunk_content(long_content, max_chunk_size=500)
        
        assert len(chunks) > 1
        for chunk_content, metadata in chunks:
            assert len(chunk_content) <= 500
            assert "chunk_index" in metadata
            assert "total_chunks" in metadata
    
    def test_should_process_content(self):
        """Test content processing decision."""
        analyzer = ContentAnalyzer()
        
        # High quality content
        good_analysis = {
            "quality": ContentQuality.HIGH,
            "extraction_confidence": 0.8,
            "metrics": {"word_count": 100}
        }
        assert analyzer.should_process_content(good_analysis) is True
        
        # Poor quality content
        bad_analysis = {
            "quality": ContentQuality.UNSUITABLE,
            "extraction_confidence": 0.2,
            "metrics": {"word_count": 10}
        }
        assert analyzer.should_process_content(bad_analysis) is False


class TestLLMStrategyExtractor:
    """Test the LLM strategy extractor."""
    
    @pytest.mark.asyncio
    async def test_extract_strategies_success(self, mock_settings):
        """Test successful strategy extraction."""
        with patch('src.ingestion.strategy_extractor.anthropic.Anthropic') as mock_anthropic_class:
            # Setup mock
            mock_client = mock_anthropic_client()
            mock_anthropic_class.return_value = mock_client
            
            extractor = LLMStrategyExtractor(mock_settings)
            
            strategies = await extractor.extract_strategies(
                content=SAMPLE_CONTENT,
                source_type=SourceType.MANUAL,
                source_ref="test.md"
            )
            
            assert len(strategies) == 1
            assert strategies[0].name == "ICT Liquidity Engulf Strategy"
            assert strategies[0].entry_type == EntryType.LE
            assert len(strategies[0].conditions) == 1
    
    @pytest.mark.asyncio
    async def test_extract_strategies_api_error(self, mock_settings):
        """Test handling of API errors."""
        with patch('src.ingestion.strategy_extractor.anthropic.Anthropic') as mock_anthropic_class:
            # Setup mock to raise exception
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic_class.return_value = mock_client
            
            extractor = LLMStrategyExtractor(mock_settings)
            
            with pytest.raises(StrategyExtractionError):
                await extractor.extract_strategies(
                    content=SAMPLE_CONTENT,
                    source_type=SourceType.MANUAL,
                    source_ref="test.md"
                )
    
    def test_extract_json_from_response(self, mock_settings):
        """Test JSON extraction from Claude response."""
        extractor = LLMStrategyExtractor(mock_settings)
        
        # Test with markdown formatting
        markdown_response = f"```json\n{SAMPLE_STRATEGY_JSON}\n```"
        result = extractor._extract_json_from_response(markdown_response)
        
        # Should be valid JSON
        json.loads(result)  # This will raise if invalid
    
    def test_validate_strategy_completeness(self, mock_settings):
        """Test strategy validation."""
        from src.knowledge.models import (
            StrategyRule, ContentSource, PatternCondition, RiskParameters
        )
        
        extractor = LLMStrategyExtractor(mock_settings)
        
        # Valid strategy
        valid_strategy = StrategyRule(
            name="Test Strategy",
            source=ContentSource(type=SourceType.MANUAL, ref="test"),
            entry_type=EntryType.LE,
            conditions=[PatternCondition(
                type="candle",
                timeframe="15m",
                params={"pattern": "test", "wick_ratio": 0.3, "close_position": "high"}
            )],
            risk_params=RiskParameters(
                risk_percent=2.0,
                tp_levels=[1.0, 2.0],
                sl_distance="structure"
            ),
            confidence=0.7
        )
        
        is_valid, issues = extractor.validate_strategy_completeness(valid_strategy)
        assert is_valid is True
        assert len(issues) == 0


class TestIngestionOrchestrator:
    """Test the ingestion orchestrator."""
    
    @pytest.mark.asyncio
    async def test_ingest_content_success(self, mock_settings):
        """Test successful content ingestion."""
        with patch('src.ingestion.strategy_extractor.anthropic.Anthropic') as mock_anthropic_class:
            mock_client = mock_anthropic_client()
            mock_anthropic_class.return_value = mock_client
            
            orchestrator = IngestionOrchestrator(mock_settings)
            
            response = await orchestrator.ingest_content(
                content=SAMPLE_CONTENT,
                source_type=SourceType.MANUAL,
                source_ref="test.md",
                tags=["test"]
            )
            
            assert response.status == "completed"
            assert len(response.strategy_rules_created) > 0
            assert "Successfully extracted" in response.message
    
    @pytest.mark.asyncio
    async def test_ingest_low_quality_content(self, mock_settings):
        """Test ingestion of low-quality content."""
        orchestrator = IngestionOrchestrator(mock_settings)
        
        poor_content = "Buy low, sell high."
        response = await orchestrator.ingest_content(
            content=poor_content,
            source_type=SourceType.MANUAL,
            source_ref="poor.md"
        )
        
        assert response.status == "skipped"
        assert "quality too low" in response.message
    
    @pytest.mark.asyncio
    async def test_batch_ingestion(self, mock_settings):
        """Test batch ingestion of multiple sources."""
        with patch('src.ingestion.strategy_extractor.anthropic.Anthropic') as mock_anthropic_class:
            mock_client = mock_anthropic_client()
            mock_anthropic_class.return_value = mock_client
            
            orchestrator = IngestionOrchestrator(mock_settings)
            
            sources = [
                {
                    "type": "manual",
                    "content": SAMPLE_CONTENT,
                    "ref": "test1.md",
                    "tags": ["batch"]
                },
                {
                    "type": "manual", 
                    "content": SAMPLE_CONTENT,
                    "ref": "test2.md",
                    "tags": ["batch"]
                }
            ]
            
            responses = await orchestrator.batch_ingest(sources, max_concurrent=1)
            
            assert len(responses) == 2
            assert all(r.status == "completed" for r in responses)
    
    def test_get_processing_stats(self, mock_settings):
        """Test processing statistics."""
        orchestrator = IngestionOrchestrator(mock_settings)
        
        stats = orchestrator.get_processing_stats()
        
        assert "max_concurrent_extractions" in stats
        assert "min_strategy_confidence" in stats
        assert "model" in stats
        assert "temperature" in stats
    
    def test_update_settings(self, mock_settings):
        """Test updating orchestrator settings."""
        orchestrator = IngestionOrchestrator(mock_settings)
        
        original_concurrent = orchestrator.max_concurrent_extractions
        orchestrator.update_settings(max_concurrent=5, min_confidence=0.6)
        
        assert orchestrator.max_concurrent_extractions == 5
        assert orchestrator.min_strategy_confidence == 0.6


class TestIntegration:
    """Integration tests for the full pipeline."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_extraction(self, mock_settings):
        """Test end-to-end strategy extraction."""
        with patch('src.ingestion.strategy_extractor.anthropic.Anthropic') as mock_anthropic_class:
            # Setup realistic mock response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text=SAMPLE_STRATEGY_JSON)]
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic_class.return_value = mock_client
            
            # Test the full pipeline
            from src.ingestion import create_ingestion_orchestrator
            
            orchestrator = create_ingestion_orchestrator(mock_settings)
            
            # Analyze content
            analysis = orchestrator.analyzer.analyze_content(SAMPLE_CONTENT, SourceType.MANUAL)
            assert orchestrator.analyzer.should_process_content(analysis) is True
            
            # Extract strategies
            response = await orchestrator.ingest_content(
                content=SAMPLE_CONTENT,
                source_type=SourceType.MANUAL,
                source_ref="integration_test.md",
                tags=["integration", "test"]
            )
            
            # Verify results
            assert response.status == "completed"
            assert len(response.strategy_rules_created) > 0
            
            # Verify the extracted strategy has all components
            # Note: In real implementation, we'd fetch from database
            # Here we just verify the response structure


if __name__ == "__main__":
    pytest.main([__file__])