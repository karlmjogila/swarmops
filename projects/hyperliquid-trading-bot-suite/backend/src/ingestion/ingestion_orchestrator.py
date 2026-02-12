"""
Ingestion orchestrator that coordinates content processing and strategy extraction.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from ..config import Settings, get_settings
from ..types import SourceType
from ..knowledge.models import StrategyRule, IngestionResponse
from .strategy_extractor import LLMStrategyExtractor, StrategyExtractionError
from .content_analyzer import ContentAnalyzer


logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


class IngestionOrchestrator:
    """
    Orchestrates the full content ingestion and strategy extraction pipeline.
    """
    
    def __init__(self, settings: Settings = None):
        """
        Initialize the ingestion orchestrator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        
        # Initialize components
        self.extractor = LLMStrategyExtractor(self.settings)
        self.analyzer = ContentAnalyzer()
        
        # Processing settings
        self.max_concurrent_extractions = 3
        self.retry_attempts = 2
        self.min_strategy_confidence = 0.3
        
        logger.info("Ingestion orchestrator initialized")
    
    async def ingest_content(
        self,
        content: str,
        source_type: SourceType,
        source_ref: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> IngestionResponse:
        """
        Ingest content and extract trading strategies.
        
        Args:
            content: Text content to process
            source_type: Type of content source
            source_ref: Reference to source (file path, URL, etc.)
            metadata: Additional metadata
            tags: Tags to apply to extracted strategies
            
        Returns:
            Ingestion response with results
        """
        task_id = f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting ingestion task {task_id} for {source_type.value}: {source_ref}")
        
        try:
            # Analyze content first
            analysis = self.analyzer.analyze_content(content, source_type)
            
            logger.info(
                f"Content analysis: type={analysis['content_type']}, "
                f"quality={analysis['quality']}, confidence={analysis['extraction_confidence']:.2f}"
            )
            
            # Check if content should be processed
            if not self.analyzer.should_process_content(analysis):
                return IngestionResponse(
                    task_id=task_id,
                    status="skipped",
                    strategy_rules_created=[],
                    message=f"Content quality too low or unsuitable for extraction: {analysis['quality']}"
                )
            
            # Process content based on analysis
            strategies = await self._process_analyzed_content(
                content, source_type, source_ref, analysis, metadata, tags
            )
            
            # Filter strategies by confidence
            quality_strategies = [
                s for s in strategies 
                if s.confidence >= self.min_strategy_confidence
            ]
            
            logger.info(
                f"Ingestion complete: {len(quality_strategies)}/{len(strategies)} "
                f"strategies meet quality threshold"
            )
            
            return IngestionResponse(
                task_id=task_id,
                status="completed",
                strategy_rules_created=[s.id for s in quality_strategies],
                message=f"Successfully extracted {len(quality_strategies)} strategy rules"
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed for task {task_id}: {e}")
            return IngestionResponse(
                task_id=task_id,
                status="error",
                strategy_rules_created=[],
                message=f"Ingestion failed: {str(e)}"
            )
    
    async def _process_analyzed_content(
        self,
        content: str,
        source_type: SourceType,
        source_ref: str,
        analysis: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
        tags: Optional[List[str]]
    ) -> List[StrategyRule]:
        """
        Process content based on analysis results.
        
        Args:
            content: Content to process
            source_type: Source type
            source_ref: Source reference
            analysis: Content analysis results
            metadata: Additional metadata
            tags: Tags to apply
            
        Returns:
            List of extracted strategies
        """
        processing_strategy = analysis["processing_strategy"]
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            "content_type": analysis["content_type"],
            "quality": analysis["quality"],
            "extraction_confidence": analysis["extraction_confidence"]
        })
        
        # Chunk content if needed
        if len(content) > processing_strategy["chunk_size"]:
            return await self._process_chunked_content(
                content, source_type, source_ref, processing_strategy, metadata, tags
            )
        else:
            return await self._process_single_content(
                content, source_type, source_ref, processing_strategy, metadata, tags
            )
    
    async def _process_single_content(
        self,
        content: str,
        source_type: SourceType,
        source_ref: str,
        processing_strategy: Dict[str, Any],
        metadata: Dict[str, Any],
        tags: Optional[List[str]]
    ) -> List[StrategyRule]:
        """Process single piece of content."""
        try:
            strategies = await self.extractor.extract_strategies(
                content=content,
                source_type=source_type,
                source_ref=source_ref,
                content_metadata=metadata
            )
            
            # Apply tags if provided
            if tags:
                for strategy in strategies:
                    strategy.tags.extend(tags)
            
            # Validate strategies
            validated_strategies = []
            for strategy in strategies:
                is_valid, issues = self.extractor.validate_strategy_completeness(strategy)
                if is_valid:
                    validated_strategies.append(strategy)
                else:
                    logger.warning(f"Strategy '{strategy.name}' validation failed: {issues}")
            
            return validated_strategies
            
        except StrategyExtractionError as e:
            logger.warning(f"Strategy extraction failed: {e}")
            return []
    
    async def _process_chunked_content(
        self,
        content: str,
        source_type: SourceType,
        source_ref: str,
        processing_strategy: Dict[str, Any],
        metadata: Dict[str, Any],
        tags: Optional[List[str]]
    ) -> List[StrategyRule]:
        """Process content in chunks."""
        chunk_size = processing_strategy["chunk_size"]
        chunks_with_metadata = self.analyzer.chunk_content(content, chunk_size)
        
        logger.info(f"Processing {len(chunks_with_metadata)} chunks")
        
        # Process chunks with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_extractions)
        tasks = []
        
        for chunk_content, chunk_metadata in chunks_with_metadata:
            # Merge metadata
            combined_metadata = {**metadata, **chunk_metadata}
            
            task = self._process_chunk_with_semaphore(
                semaphore, chunk_content, source_type, source_ref, 
                combined_metadata, tags
            )
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        all_strategies = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Chunk {i} processing failed: {result}")
            else:
                all_strategies.extend(result)
        
        # Deduplicate strategies
        unique_strategies = self._deduplicate_strategies(all_strategies)
        
        logger.info(
            f"Processed {len(chunks_with_metadata)} chunks, "
            f"extracted {len(unique_strategies)} unique strategies"
        )
        
        return unique_strategies
    
    async def _process_chunk_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        content: str,
        source_type: SourceType,
        source_ref: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]]
    ) -> List[StrategyRule]:
        """Process a single chunk with concurrency control."""
        async with semaphore:
            try:
                strategies = await self.extractor.extract_strategies(
                    content=content,
                    source_type=source_type,
                    source_ref=source_ref,
                    content_metadata=metadata
                )
                
                # Apply tags
                if tags:
                    for strategy in strategies:
                        strategy.tags.extend(tags)
                
                return strategies
                
            except Exception as e:
                logger.warning(f"Chunk processing failed: {e}")
                return []
    
    def _deduplicate_strategies(self, strategies: List[StrategyRule]) -> List[StrategyRule]:
        """Remove duplicate strategies based on name and content similarity."""
        if not strategies:
            return []
        
        unique_strategies = []
        seen_names = set()
        
        for strategy in strategies:
            # Simple deduplication by name
            if strategy.name.lower() not in seen_names:
                unique_strategies.append(strategy)
                seen_names.add(strategy.name.lower())
            else:
                logger.debug(f"Duplicate strategy filtered: {strategy.name}")
        
        return unique_strategies
    
    async def ingest_pdf(
        self,
        file_path: str,
        strategy_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> IngestionResponse:
        """
        Ingest a PDF file and extract strategies.
        
        Args:
            file_path: Path to PDF file
            strategy_name: Override strategy name
            tags: Tags to apply
            
        Returns:
            Ingestion response
        """
        logger.info(f"Ingesting PDF: {file_path}")
        
        try:
            # Read PDF content (simplified - would use actual PDF processor)
            content = await self._extract_pdf_content(file_path)
            
            # Set source reference
            source_ref = str(Path(file_path).name)
            
            return await self.ingest_content(
                content=content,
                source_type=SourceType.PDF,
                source_ref=source_ref,
                metadata={"file_path": file_path},
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"PDF ingestion failed: {e}")
            raise IngestionError(f"Failed to ingest PDF {file_path}: {e}") from e
    
    async def ingest_video_transcript(
        self,
        transcript: str,
        video_url: str,
        strategy_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timestamps: Optional[List[Dict[str, Any]]] = None
    ) -> IngestionResponse:
        """
        Ingest video transcript and extract strategies.
        
        Args:
            transcript: Video transcript text
            video_url: Video URL
            strategy_name: Override strategy name
            tags: Tags to apply
            timestamps: Timestamp information
            
        Returns:
            Ingestion response
        """
        logger.info(f"Ingesting video transcript: {video_url}")
        
        try:
            metadata = {
                "video_url": video_url,
                "has_timestamps": timestamps is not None
            }
            
            if timestamps:
                metadata["timestamps"] = timestamps
            
            return await self.ingest_content(
                content=transcript,
                source_type=SourceType.VIDEO,
                source_ref=video_url,
                metadata=metadata,
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"Video transcript ingestion failed: {e}")
            raise IngestionError(f"Failed to ingest video transcript: {e}") from e
    
    async def _extract_pdf_content(self, file_path: str) -> str:
        """
        Extract text content from PDF file.
        
        This is a placeholder - would integrate with actual PDF processor.
        """
        # Placeholder implementation
        logger.warning("Using placeholder PDF content extraction")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return f"Sample PDF content from {file_path}"
    
    async def batch_ingest(
        self,
        sources: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[IngestionResponse]:
        """
        Ingest multiple sources concurrently.
        
        Args:
            sources: List of source dictionaries with content info
            max_concurrent: Maximum concurrent ingestions
            
        Returns:
            List of ingestion responses
        """
        logger.info(f"Starting batch ingestion of {len(sources)} sources")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        
        for source in sources:
            task = self._process_source_with_semaphore(semaphore, source)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error responses
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                responses.append(IngestionResponse(
                    task_id=f"batch_{i}",
                    status="error",
                    strategy_rules_created=[],
                    message=f"Batch ingestion failed: {result}"
                ))
            else:
                responses.append(result)
        
        successful = sum(1 for r in responses if r.status == "completed")
        logger.info(f"Batch ingestion complete: {successful}/{len(sources)} successful")
        
        return responses
    
    async def _process_source_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore,
        source: Dict[str, Any]
    ) -> IngestionResponse:
        """Process a single source with concurrency control."""
        async with semaphore:
            try:
                source_type = SourceType(source["type"])
                
                if source_type == SourceType.PDF:
                    return await self.ingest_pdf(
                        file_path=source["path"],
                        tags=source.get("tags")
                    )
                elif source_type == SourceType.VIDEO:
                    return await self.ingest_video_transcript(
                        transcript=source["transcript"],
                        video_url=source["url"],
                        tags=source.get("tags")
                    )
                else:
                    return await self.ingest_content(
                        content=source["content"],
                        source_type=source_type,
                        source_ref=source["ref"],
                        tags=source.get("tags")
                    )
                    
            except Exception as e:
                logger.error(f"Source processing failed: {e}")
                return IngestionResponse(
                    task_id="batch_error",
                    status="error",
                    strategy_rules_created=[],
                    message=f"Failed to process source: {e}"
                )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "max_concurrent_extractions": self.max_concurrent_extractions,
            "min_strategy_confidence": self.min_strategy_confidence,
            "retry_attempts": self.retry_attempts,
            "chunk_size": self.analyzer.max_chunk_size,
            "model": self.extractor.extraction_model,
            "temperature": self.extractor.temperature
        }
    
    def update_settings(
        self,
        max_concurrent: Optional[int] = None,
        min_confidence: Optional[float] = None,
        retry_attempts: Optional[int] = None
    ) -> None:
        """Update processing settings."""
        if max_concurrent is not None:
            self.max_concurrent_extractions = max_concurrent
            logger.info(f"Updated max_concurrent_extractions: {max_concurrent}")
        
        if min_confidence is not None:
            self.min_strategy_confidence = min_confidence
            logger.info(f"Updated min_strategy_confidence: {min_confidence}")
        
        if retry_attempts is not None:
            self.retry_attempts = retry_attempts
            logger.info(f"Updated retry_attempts: {retry_attempts}")


# Factory function for easy initialization
def create_ingestion_orchestrator(settings: Settings = None) -> IngestionOrchestrator:
    """Create and configure an ingestion orchestrator."""
    return IngestionOrchestrator(settings)