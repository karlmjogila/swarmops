"""Example: Using YouTube processor to extract trading content.

This example demonstrates how to:
1. Process a YouTube video to extract transcripts and frames
2. Use the extracted content with the strategy extractor
3. Store the resulting strategies in the database
"""

import asyncio
import logging
from pathlib import Path

from hl_bot.services.ingestion import YouTubeProcessor
from hl_bot.services.llm_client import LLMClient
from hl_bot.services.strategy_extractor import StrategyExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_youtube_video(url: str) -> None:
    """Process a YouTube video and extract trading strategies.

    Args:
        url: YouTube video URL
    """
    # Initialize processors
    cache_dir = Path("./data/youtube_cache")
    youtube = YouTubeProcessor(
        cache_dir=cache_dir,
        enable_whisper=True,  # Enable Whisper transcription as fallback
        max_video_duration=7200,  # 2 hours max
        frame_interval=30,  # Extract frame every 30 seconds
    )

    llm_client = LLMClient()
    strategy_extractor = StrategyExtractor(llm_client=llm_client)

    try:
        # Step 1: Process YouTube video
        logger.info(f"Processing YouTube URL: {url}")
        videos = await youtube.process_url(
            url,
            extract_frames=True,  # Extract frames for image analysis
            prefer_captions=True,  # Try captions first (faster)
        )

        # Step 2: Extract strategies from each video
        all_strategies = []

        for video in videos:
            logger.info(f"Processing video: {video.title} ({video.video_id})")
            logger.info(f"Transcript length: {len(video.transcript)} chars")
            logger.info(f"Frames extracted: {len(video.frames)}")

            # Combine transcript with image analysis if frames were extracted
            if video.frames:
                # Upload frames to a temporary location or use LLM image analysis
                # For this example, we'll just use the transcript
                logger.info("Frame-based analysis would happen here")

            # Extract strategies from transcript
            strategies = await strategy_extractor.extract_from_text(
                content=video.transcript,
                source_type="youtube",
                source_id=video.url,
            )

            logger.info(f"Extracted {len(strategies)} strategies from video")

            for i, strategy in enumerate(strategies):
                logger.info(f"\nStrategy {i+1}:")
                logger.info(f"  Name: {strategy.rule.name}")
                logger.info(f"  Description: {strategy.rule.description[:100]}...")
                logger.info(f"  Timeframes: {[tf.value for tf in strategy.rule.timeframes]}")
                logger.info(f"  Entry Conditions: {len(strategy.rule.entry_conditions)}")
                logger.info(f"  Confidence: {strategy.confidence:.2f}")

            all_strategies.extend(strategies)

        # Step 3: Store strategies (in real usage, save to database)
        logger.info(f"\nTotal strategies extracted: {len(all_strategies)}")

        # Clean up cache periodically
        await youtube.cleanup_cache(max_age_days=7)

    except Exception as e:
        logger.error(f"Failed to process video: {e}")
        raise


async def main() -> None:
    """Main entry point."""
    # Example: Process a trading education video
    # Replace with actual trading strategy video URL
    example_url = "https://www.youtube.com/watch?v=EXAMPLE_VIDEO_ID"

    logger.info("YouTube Video Processing Example")
    logger.info("=" * 50)
    logger.info("\nNote: This example uses a placeholder URL.")
    logger.info("Replace with a real trading education video URL.\n")

    # Uncomment to run with real URL
    # await process_youtube_video(example_url)

    logger.info("Example completed. See code for usage patterns.")


if __name__ == "__main__":
    asyncio.run(main())
