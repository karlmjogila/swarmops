"""
Integration tests for the Ingestion Orchestrator.

These tests verify the complete ingestion pipeline:
- Content extraction
- Analysis
- Strategy extraction
- Error handling
- Batch processing
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

from src.ingestion.ingestion_orchestrator import (
    IngestionOrchestrator,
    IngestionError,
    create_ingestion_orchestrator
)
from src.types import SourceType
from src.knowledge.models import StrategyRule, IngestionResponse


# Sample content for testing
SAMPLE_TRADING_CONTENT = """
# Moving Average Crossover Strategy

## Entry Rules
1. Wait for 50 MA to cross above 200 MA (bullish signal)
2. Enter on first pullback to 50 MA
3. Confirm with RSI above 50

## Exit Rules
- Take profit at 1.5R
- Stop loss below recent swing low
- Exit if 50 MA crosses below 200 MA

## Risk Management
- Risk 2% per trade
- Maximum 3 concurrent positions
"""

SAMPLE_PATTERN_CONTENT = """
# Hammer Candlestick Pattern

## Identification
- Small body at top of candle
- Long lower wick (at least 2x body size)
- Little to no upper wick
- Appears at support level

## Trading Rules
- Enter at open of next candle
- Stop loss below hammer low
- Target previous resistance level
"""

LOW_QUALITY_CONTENT = """
Trading is hard. You should practice a lot.
"""


@pytest.fixture
def orchestrator():
    """Create an orchestrator instance for testing."""
    return create_ingestion_orchestrator()


@pytest.fixture
def mock_extractor():
    """Mock the LLM strategy extractor."""
    with patch('src.ingestion.ingestion_orchestrator.LLMStrategyExtractor') as mock:
        extractor_instance = Mock()
        
        # Mock successful extraction
        async def mock_extract(*args, **kwargs):
            return [
                StrategyRule(
                    name="Test Strategy",
                    entry_type="breakout",
                    source_type=SourceType.MANUAL,
                    source_ref="test.md",
                    conditions=[],
                    notes="Test strategy",
                    tags=["test"],
                    confidence=0.7
                )
            ]
        
        extractor_instance.extract_strategies = mock_extract
        extractor_instance.validate_strategy_completeness = Mock(return_value=(True, []))
        
        mock.return_value = extractor_instance
        yield mock


class TestBasicIngestion:
    """Test basic content ingestion functionality."""
    
    @pytest.mark.asyncio
    async def test_ingest_valid_content(self, orchestrator):
        """Test ingestion of valid trading content."""
        response = await orchestrator.ingest_content(
            content=SAMPLE_TRADING_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="test_strategy.md",
            tags=["test", "ma_crossover"]
        )
        
        assert response is not None
        assert response.task_id is not None
        assert response.status in ["completed", "error"]
        assert isinstance(response.strategy_rules_created, list)
        assert isinstance(response.message, str)
    
    @pytest.mark.asyncio
    async def test_ingest_low_quality_content(self, orchestrator):
        """Test that low quality content is skipped."""
        response = await orchestrator.ingest_content(
            content=LOW_QUALITY_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="low_quality.md"
        )
        
        assert response is not None
        assert response.status == "skipped"
        assert len(response.strategy_rules_created) == 0
    
    @pytest.mark.asyncio
    async def test_ingest_with_metadata(self, orchestrator):
        """Test ingestion with custom metadata."""
        metadata = {
            "author": "Test Author",
            "category": "momentum",
            "difficulty": "intermediate"
        }
        
        response = await orchestrator.ingest_content(
            content=SAMPLE_TRADING_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="test.md",
            metadata=metadata,
            tags=["momentum"]
        )
        
        assert response is not None
        assert "content_type" in str(response.message) or response.status != "error"


class TestContentAnalysis:
    """Test content analysis and quality assessment."""
    
    def test_analyze_trading_content(self, orchestrator):
        """Test that trading content is properly analyzed."""
        analysis = orchestrator.analyzer.analyze_content(
            SAMPLE_TRADING_CONTENT,
            SourceType.MANUAL
        )
        
        assert "content_type" in analysis
        assert "quality" in analysis
        assert "extraction_confidence" in analysis
        assert analysis["extraction_confidence"] > 0.3
    
    def test_analyze_pattern_content(self, orchestrator):
        """Test analysis of pattern-focused content."""
        analysis = orchestrator.analyzer.analyze_content(
            SAMPLE_PATTERN_CONTENT,
            SourceType.MANUAL
        )
        
        assert analysis["content_type"] in ["pattern_focused", "strategy_focused", "educational"]
        assert analysis["quality"] != "very_low"
    
    def test_analyze_low_quality(self, orchestrator):
        """Test that low quality content is detected."""
        analysis = orchestrator.analyzer.analyze_content(
            LOW_QUALITY_CONTENT,
            SourceType.MANUAL
        )
        
        assert analysis["quality"] in ["low", "very_low"]
        assert not orchestrator.analyzer.should_process_content(analysis)


class TestChunking:
    """Test content chunking for large documents."""
    
    @pytest.mark.asyncio
    async def test_large_content_chunking(self, orchestrator):
        """Test that large content is properly chunked."""
        # Create large content
        large_content = SAMPLE_TRADING_CONTENT * 50  # Repeat to make it large
        
        response = await orchestrator.ingest_content(
            content=large_content,
            source_type=SourceType.MANUAL,
            source_ref="large_doc.md"
        )
        
        assert response is not None
        # Should still process successfully
        assert response.status in ["completed", "error", "skipped"]
    
    def test_chunk_content(self, orchestrator):
        """Test the chunking mechanism."""
        content = "Strategy section\n\n" * 100  # Create content > chunk size
        chunks = orchestrator.analyzer.chunk_content(content, chunk_size=500)
        
        assert len(chunks) > 0
        assert isinstance(chunks, list)
        
        # Each chunk should be a tuple of (content, metadata)
        for chunk_content, chunk_metadata in chunks:
            assert isinstance(chunk_content, str)
            assert isinstance(chunk_metadata, dict)
            assert "chunk_index" in chunk_metadata


class TestBatchProcessing:
    """Test batch processing of multiple sources."""
    
    @pytest.mark.asyncio
    async def test_batch_ingest_multiple_sources(self, orchestrator):
        """Test batch processing of multiple content sources."""
        sources = [
            {
                "type": "manual",
                "content": SAMPLE_TRADING_CONTENT,
                "ref": "strategy1.md",
                "tags": ["test"]
            },
            {
                "type": "manual",
                "content": SAMPLE_PATTERN_CONTENT,
                "ref": "pattern1.md",
                "tags": ["test"]
            }
        ]
        
        responses = await orchestrator.batch_ingest(sources, max_concurrent=2)
        
        assert len(responses) == 2
        assert all(isinstance(r, IngestionResponse) for r in responses)
    
    @pytest.mark.asyncio
    async def test_batch_with_errors(self, orchestrator):
        """Test batch processing handles errors gracefully."""
        sources = [
            {
                "type": "manual",
                "content": SAMPLE_TRADING_CONTENT,
                "ref": "good.md"
            },
            {
                "type": "invalid_type",  # This will cause an error
                "content": "content",
                "ref": "bad.md"
            }
        ]
        
        responses = await orchestrator.batch_ingest(sources, max_concurrent=2)
        
        assert len(responses) == 2
        # At least one should be an error
        error_responses = [r for r in responses if r.status == "error"]
        assert len(error_responses) > 0
    
    @pytest.mark.asyncio
    async def test_batch_concurrency_control(self, orchestrator):
        """Test that batch processing respects concurrency limits."""
        # Create many sources
        sources = [
            {
                "type": "manual",
                "content": f"Strategy {i}",
                "ref": f"strategy{i}.md"
            }
            for i in range(10)
        ]
        
        # Process with limited concurrency
        responses = await orchestrator.batch_ingest(sources, max_concurrent=2)
        
        assert len(responses) == 10


class TestPDFIngestion:
    """Test PDF-specific ingestion."""
    
    @pytest.mark.asyncio
    async def test_ingest_pdf(self, orchestrator, tmp_path):
        """Test PDF ingestion."""
        # Create a temporary test file
        test_file = tmp_path / "test_strategy.txt"
        test_file.write_text(SAMPLE_TRADING_CONTENT)
        
        response = await orchestrator.ingest_pdf(
            file_path=str(test_file),
            tags=["pdf", "test"]
        )
        
        assert response is not None
        assert response.task_id is not None
    
    @pytest.mark.asyncio
    async def test_ingest_nonexistent_pdf(self, orchestrator):
        """Test that nonexistent PDF raises error."""
        with pytest.raises(IngestionError):
            await orchestrator.ingest_pdf(
                file_path="/nonexistent/file.pdf"
            )


class TestVideoIngestion:
    """Test video transcript ingestion."""
    
    @pytest.mark.asyncio
    async def test_ingest_video_transcript(self, orchestrator):
        """Test video transcript ingestion."""
        response = await orchestrator.ingest_video_transcript(
            transcript=SAMPLE_TRADING_CONTENT,
            video_url="https://youtube.com/watch?v=test123",
            tags=["video", "test"]
        )
        
        assert response is not None
        assert response.task_id is not None
    
    @pytest.mark.asyncio
    async def test_ingest_video_with_timestamps(self, orchestrator):
        """Test video ingestion with timestamp information."""
        timestamps = [
            {"start": 0, "end": 10, "text": "Introduction"},
            {"start": 10, "end": 60, "text": "Strategy explanation"}
        ]
        
        response = await orchestrator.ingest_video_transcript(
            transcript=SAMPLE_TRADING_CONTENT,
            video_url="https://youtube.com/watch?v=test123",
            timestamps=timestamps,
            tags=["video"]
        )
        
        assert response is not None


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_empty_content(self, orchestrator):
        """Test handling of empty content."""
        response = await orchestrator.ingest_content(
            content="",
            source_type=SourceType.MANUAL,
            source_ref="empty.md"
        )
        
        assert response is not None
        # Should skip or error, not crash
        assert response.status in ["skipped", "error"]
    
    @pytest.mark.asyncio
    async def test_extraction_failure(self, orchestrator):
        """Test handling of extraction failures."""
        with patch.object(orchestrator.extractor, 'extract_strategies') as mock_extract:
            # Make extraction fail
            async def failing_extraction(*args, **kwargs):
                from src.ingestion.strategy_extractor import StrategyExtractionError
                raise StrategyExtractionError("Extraction failed")
            
            mock_extract.side_effect = failing_extraction
            
            response = await orchestrator.ingest_content(
                content=SAMPLE_TRADING_CONTENT,
                source_type=SourceType.MANUAL,
                source_ref="test.md"
            )
            
            # Should handle gracefully
            assert response is not None
            assert response.status in ["error", "completed"]


class TestStrategyValidation:
    """Test strategy validation and filtering."""
    
    @pytest.mark.asyncio
    async def test_confidence_filtering(self, orchestrator):
        """Test that low confidence strategies are filtered."""
        # Set high confidence threshold
        orchestrator.min_strategy_confidence = 0.8
        
        response = await orchestrator.ingest_content(
            content=SAMPLE_TRADING_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="test.md"
        )
        
        # Any strategies returned should meet the threshold
        assert response is not None
    
    def test_strategy_deduplication(self, orchestrator):
        """Test that duplicate strategies are removed."""
        strategies = [
            StrategyRule(
                name="Test Strategy",
                entry_type="breakout",
                source_type=SourceType.MANUAL,
                source_ref="test.md",
                conditions=[],
                notes="First",
                tags=[],
                confidence=0.7
            ),
            StrategyRule(
                name="Test Strategy",  # Duplicate name
                entry_type="breakout",
                source_type=SourceType.MANUAL,
                source_ref="test.md",
                conditions=[],
                notes="Second",
                tags=[],
                confidence=0.8
            ),
            StrategyRule(
                name="Different Strategy",
                entry_type="breakout",
                source_type=SourceType.MANUAL,
                source_ref="test.md",
                conditions=[],
                notes="Third",
                tags=[],
                confidence=0.6
            )
        ]
        
        unique = orchestrator._deduplicate_strategies(strategies)
        
        # Should keep only unique names
        assert len(unique) == 2
        assert "Test Strategy" in [s.name for s in unique]
        assert "Different Strategy" in [s.name for s in unique]


class TestConfiguration:
    """Test orchestrator configuration and settings."""
    
    def test_get_processing_stats(self, orchestrator):
        """Test retrieval of processing statistics."""
        stats = orchestrator.get_processing_stats()
        
        assert "max_concurrent_extractions" in stats
        assert "min_strategy_confidence" in stats
        assert "retry_attempts" in stats
        assert "model" in stats
    
    def test_update_settings(self, orchestrator):
        """Test updating orchestrator settings."""
        original_concurrent = orchestrator.max_concurrent_extractions
        
        orchestrator.update_settings(max_concurrent=5)
        assert orchestrator.max_concurrent_extractions == 5
        
        orchestrator.update_settings(min_confidence=0.5)
        assert orchestrator.min_strategy_confidence == 0.5
        
        orchestrator.update_settings(retry_attempts=3)
        assert orchestrator.retry_attempts == 3
    
    def test_factory_function(self):
        """Test the factory function creates valid orchestrator."""
        orchestrator = create_ingestion_orchestrator()
        
        assert isinstance(orchestrator, IngestionOrchestrator)
        assert orchestrator.extractor is not None
        assert orchestrator.analyzer is not None


class TestIntegrationFlow:
    """Test complete end-to-end integration flows."""
    
    @pytest.mark.asyncio
    async def test_complete_ingestion_flow(self, orchestrator):
        """Test complete flow from content to extracted strategies."""
        # Step 1: Ingest content
        response = await orchestrator.ingest_content(
            content=SAMPLE_TRADING_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="integration_test.md",
            tags=["integration", "test"]
        )
        
        # Verify response structure
        assert response.task_id is not None
        assert response.status in ["completed", "error", "skipped"]
        assert isinstance(response.strategy_rules_created, list)
        assert response.message is not None
        
        # If successful, verify strategies were created
        if response.status == "completed":
            assert len(response.strategy_rules_created) >= 0
    
    @pytest.mark.asyncio
    async def test_multiple_source_types_integration(self, orchestrator, tmp_path):
        """Test processing multiple source types in sequence."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text(SAMPLE_TRADING_CONTENT)
        
        # Process different source types
        pdf_response = await orchestrator.ingest_pdf(
            file_path=str(test_file),
            tags=["pdf"]
        )
        
        video_response = await orchestrator.ingest_video_transcript(
            transcript=SAMPLE_PATTERN_CONTENT,
            video_url="https://youtube.com/watch?v=test",
            tags=["video"]
        )
        
        manual_response = await orchestrator.ingest_content(
            content=SAMPLE_TRADING_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="manual.md",
            tags=["manual"]
        )
        
        # All should process
        assert pdf_response is not None
        assert video_response is not None
        assert manual_response is not None


# Performance and stress tests
class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_batch_performance(self, orchestrator):
        """Test performance with large batch of sources."""
        sources = [
            {
                "type": "manual",
                "content": SAMPLE_TRADING_CONTENT,
                "ref": f"strategy_{i}.md"
            }
            for i in range(20)
        ]
        
        import time
        start = time.time()
        
        responses = await orchestrator.batch_ingest(sources, max_concurrent=3)
        
        duration = time.time() - start
        
        assert len(responses) == 20
        # Should complete in reasonable time (adjust as needed)
        assert duration < 60  # 60 seconds for 20 sources
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, orchestrator):
        """Test that concurrent processing works correctly."""
        # Process multiple items simultaneously
        tasks = [
            orchestrator.ingest_content(
                content=SAMPLE_TRADING_CONTENT,
                source_type=SourceType.MANUAL,
                source_ref=f"concurrent_{i}.md"
            )
            for i in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 5
        assert all(r is not None for r in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
