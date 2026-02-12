"""
Example integration showing how the video pipeline fits into the broader system.

This demonstrates the complete flow:
1. Video Pipeline processes YouTube content
2. LLM Extractor analyzes content to extract trading strategies  
3. Strategy rules are stored in the knowledge base
4. Rules are used by the trading engine
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from video_pipeline import VideoPipelineManager, VideoPipelineConfig
from ..types.pydantic_models import (
    IngestionSourceModel, 
    StrategyRuleModel,
    PatternConditionModel,
    EntryType,
    PatternType,
    Timeframe,
    SourceType
)


logger = logging.getLogger(__name__)


class TradingContentProcessor:
    """
    Processes trading educational content and extracts actionable strategies.
    
    This class demonstrates how the video pipeline integrates with the LLM
    strategy extractor to convert YouTube videos into structured trading rules.
    """
    
    def __init__(self):
        # Configure video pipeline for trading content
        self.video_config = VideoPipelineConfig(
            frame_interval_seconds=10,      # Capture key moments
            whisper_model="base",           # Good balance of speed/accuracy
            frame_quality="medium",         # Sufficient for chart analysis
            max_video_duration=3600,        # 1-hour max per video
            enable_word_timestamps=True     # Precise timing for correlations
        )
        self.pipeline_manager = VideoPipelineManager(self.video_config)
        
    async def process_trading_video(self, youtube_url: str) -> List[StrategyRuleModel]:
        """
        Process a trading education video and extract strategy rules.
        
        Args:
            youtube_url: YouTube video URL
            
        Returns:
            List of extracted strategy rules
        """
        logger.info(f"Processing trading video: {youtube_url}")
        
        # Step 1: Extract content using video pipeline
        source = self.pipeline_manager.process_youtube_url(youtube_url)
        
        if source.status != "completed":
            logger.error(f"Video processing failed: {source.error_message}")
            return []
            
        logger.info(f"Extracted content from '{source.title}' by {source.author}")
        
        # Step 2: Analyze content for trading strategies
        # (In real implementation, this would call the LLM extractor)
        strategies = await self._extract_strategies_from_content(source)
        
        logger.info(f"Extracted {len(strategies)} trading strategies")
        return strategies
        
    async def _extract_strategies_from_content(
        self, 
        source: IngestionSourceModel
    ) -> List[StrategyRuleModel]:
        """
        Extract trading strategies from processed video content.
        
        This is a simplified example. In the real system, this would:
        1. Send frames + transcript to LLM (Claude)
        2. Use structured prompts to identify trading patterns
        3. Extract specific entry/exit rules
        4. Convert to StrategyRuleModel objects
        """
        
        strategies = []
        
        # Example: Detect if video discusses specific trading concepts
        content_text = source.extracted_text.lower()
        
        # Look for LE (Liquidity Engineering) candle discussions
        if "liquidity engineering" in content_text or "le candle" in content_text:
            le_strategy = self._create_le_strategy(source)
            if le_strategy:
                strategies.append(le_strategy)
                
        # Look for wick-based entries
        if "small wick" in content_text or "steeper wick" in content_text:
            wick_strategy = self._create_wick_strategy(source)
            if wick_strategy:
                strategies.append(wick_strategy)
                
        # Look for breakout strategies
        if "breakout" in content_text or "break of structure" in content_text:
            breakout_strategy = self._create_breakout_strategy(source)
            if breakout_strategy:
                strategies.append(breakout_strategy)
        
        return strategies
        
    def _create_le_strategy(self, source: IngestionSourceModel) -> StrategyRuleModel:
        """Create an LE candle strategy from video content."""
        
        # Find frames that might show LE candle examples
        relevant_frames = [
            frame for frame in source.extracted_images
            if "liquidity" in frame.get('context_text', '').lower()
            or "le candle" in frame.get('context_text', '').lower()
        ]
        
        strategy = StrategyRuleModel(
            name=f"LE Candle Strategy - {source.title[:50]}",
            entry_type=EntryType.LE,
            source_type=SourceType.VIDEO,
            source_ref=source.source_url,
            source_timestamp=relevant_frames[0]['timestamp'] if relevant_frames else None,
            
            conditions=[
                PatternConditionModel(
                    type=PatternType.CANDLE,
                    timeframe=Timeframe.M15,  # Default to 15M for LE entries
                    params={
                        "candle_type": "le",
                        "wick_ratio_min": 2.0,
                        "body_position": "upper_third",
                        "context_required": "support_level"
                    },
                    description="LE candle at support with minimal lower wick"
                ),
                PatternConditionModel(
                    type=PatternType.STRUCTURE,
                    timeframe=Timeframe.H4,  # Higher timeframe bias
                    params={
                        "bias": "bullish",
                        "structure_type": "support_hold"
                    },
                    description="4H showing bullish bias with support holding"
                )
            ],
            
            notes=f"Extracted from video: {source.title}\nKey frames at timestamps: {[f['timestamp'] for f in relevant_frames[:3]]}",
            tags=["le_candle", "video_extracted", source.author.replace(" ", "_").lower()],
            confidence=0.7  # Initial confidence for video-extracted strategies
        )
        
        return strategy
        
    def _create_wick_strategy(self, source: IngestionSourceModel) -> StrategyRuleModel:
        """Create a wick-based entry strategy."""
        
        relevant_frames = [
            frame for frame in source.extracted_images
            if "wick" in frame.get('context_text', '').lower()
        ]
        
        strategy = StrategyRuleModel(
            name=f"Small Wick Entry - {source.title[:50]}",
            entry_type=EntryType.SMALL_WICK,
            source_type=SourceType.VIDEO,
            source_ref=source.source_url,
            source_timestamp=relevant_frames[0]['timestamp'] if relevant_frames else None,
            
            conditions=[
                PatternConditionModel(
                    type=PatternType.CANDLE,
                    timeframe=Timeframe.M15,
                    params={
                        "wick_type": "small",
                        "max_wick_ratio": 0.3,
                        "body_strength": "strong",
                        "close_position": "near_high"
                    },
                    description="Small wick candle with strong body closing near highs"
                )
            ],
            
            notes=f"Small wick strategy from: {source.title}",
            tags=["small_wick", "video_extracted"],
            confidence=0.6
        )
        
        return strategy
        
    def _create_breakout_strategy(self, source: IngestionSourceModel) -> StrategyRuleModel:
        """Create a breakout strategy."""
        
        strategy = StrategyRuleModel(
            name=f"Breakout Strategy - {source.title[:50]}",
            entry_type=EntryType.BREAKOUT,
            source_type=SourceType.VIDEO,
            source_ref=source.source_url,
            
            conditions=[
                PatternConditionModel(
                    type=PatternType.STRUCTURE,
                    timeframe=Timeframe.H1,
                    params={
                        "pattern": "break_of_structure",
                        "volume_confirmation": True,
                        "retest_required": False
                    },
                    description="Break of structure with volume confirmation"
                )
            ],
            
            notes=f"Breakout strategy from: {source.title}",
            tags=["breakout", "video_extracted"],
            confidence=0.65
        )
        
        return strategy


async def example_workflow():
    """
    Example workflow showing complete integration.
    """
    
    # Sample trading education URLs
    sample_urls = [
        "https://youtube.com/watch?v=SAMPLE_TRADING_VIDEO_1",
        "https://youtube.com/watch?v=SAMPLE_TRADING_VIDEO_2"
    ]
    
    processor = TradingContentProcessor()
    
    all_strategies = []
    
    for url in sample_urls:
        try:
            # Process video and extract strategies
            strategies = await processor.process_trading_video(url)
            all_strategies.extend(strategies)
            
            print(f"\nProcessed {url}")
            print(f"Extracted {len(strategies)} strategies:")
            
            for strategy in strategies:
                print(f"  - {strategy.name} ({strategy.entry_type})")
                print(f"    Conditions: {len(strategy.conditions)}")
                print(f"    Confidence: {strategy.confidence}")
                
        except Exception as e:
            logger.error(f"Failed to process {url}: {str(e)}")
            
    print(f"\nTotal strategies extracted: {len(all_strategies)}")
    
    # In the real system, these would be saved to the knowledge base
    # and made available to the trading engine
    
    return all_strategies


class VideoIngestionOrchestrator:
    """
    Orchestrates the complete video ingestion workflow.
    
    This class demonstrates how video processing fits into the larger
    ingestion pipeline alongside PDF processing and other content sources.
    """
    
    def __init__(self):
        self.content_processor = TradingContentProcessor()
        self.processed_sources = []
        
    async def ingest_content_source(self, source_url: str, source_type: str = "auto"):
        """
        Ingest content from various sources.
        
        Args:
            source_url: URL or path to content
            source_type: "video", "pdf", or "auto" for auto-detection
        """
        
        if source_type == "auto":
            source_type = self._detect_source_type(source_url)
            
        if source_type == "video":
            return await self._process_video_source(source_url)
        elif source_type == "pdf":
            return await self._process_pdf_source(source_url) 
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
            
    def _detect_source_type(self, source_url: str) -> str:
        """Auto-detect content source type."""
        if "youtube.com" in source_url or "youtu.be" in source_url:
            return "video"
        elif source_url.lower().endswith(".pdf"):
            return "pdf"
        else:
            raise ValueError(f"Cannot detect source type for: {source_url}")
            
    async def _process_video_source(self, url: str):
        """Process video source using video pipeline."""
        strategies = await self.content_processor.process_trading_video(url)
        
        source_record = {
            'type': 'video',
            'url': url,
            'processed_at': datetime.utcnow(),
            'strategies_extracted': len(strategies),
            'strategies': strategies
        }
        
        self.processed_sources.append(source_record)
        return source_record
        
    async def _process_pdf_source(self, url: str):
        """Process PDF source (placeholder for PDF pipeline)."""
        # This would integrate with the PDF processor
        print(f"PDF processing not implemented in this example: {url}")
        return None
        
    def get_processing_summary(self):
        """Get summary of all processed content."""
        video_sources = [s for s in self.processed_sources if s['type'] == 'video']
        total_strategies = sum(s['strategies_extracted'] for s in self.processed_sources)
        
        return {
            'total_sources': len(self.processed_sources),
            'video_sources': len(video_sources),
            'total_strategies': total_strategies,
            'processing_timespan': {
                'first': min(s['processed_at'] for s in self.processed_sources) if self.processed_sources else None,
                'last': max(s['processed_at'] for s in self.processed_sources) if self.processed_sources else None
            }
        }


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("Video Pipeline Integration Example")
    print("==================================")
    
    # Run example workflow
    asyncio.run(example_workflow())
    
    print("\nIntegration Points:")
    print("1. Video Pipeline -> Processes YouTube content")
    print("2. LLM Extractor -> Analyzes content for strategies")
    print("3. Knowledge Base -> Stores extracted strategies")
    print("4. Trading Engine -> Uses strategies for decisions")
    print("5. Learning Loop -> Updates strategies based on outcomes")