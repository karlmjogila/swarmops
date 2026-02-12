"""Celery tasks for background processing of trading content.

Handles YouTube videos, PDF documents, and LLM-based strategy extraction
as asynchronous background tasks with proper error handling and retry logic.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from celery import Task
from celery.exceptions import Ignore, Retry

from app.celery_app import celery_app

# Import processors (we'll use the src modules)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from hl_bot.services.ingestion.youtube_processor import (
    YouTubeProcessor,
    YouTubeError,
    VideoInfo,
)
from hl_bot.services.ingestion.pdf_processor import (
    PDFProcessor,
    PDFError,
    PDFInfo,
)
from hl_bot.services.llm_client import LLMClient
from hl_bot.services.strategy_extractor import StrategyExtractor

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with custom callbacks."""

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Called on task success."""
        logger.info(f"Task {task_id} ({self.name}) succeeded")

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Called on task failure."""
        logger.error(f"Task {task_id} ({self.name}) failed: {exc}")

    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """Called on task retry."""
        logger.warning(f"Task {task_id} ({self.name}) retrying: {exc}")


# Helper to run async functions in Celery tasks
def run_async(coro):
    """Run an async coroutine in a new event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    finally:
        # Don't close the loop, it might be reused
        pass


@celery_app.task(
    name="app.workers.tasks.process_youtube_video",
    base=CallbackTask,
    bind=True,
    autoretry_for=(YouTubeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_youtube_video(
    self: Task,
    url: str,
    extract_frames: bool = True,
    prefer_captions: bool = True,
) -> dict[str, Any]:
    """Process a YouTube video: download, extract transcript, and frames.

    Args:
        url: YouTube video URL
        extract_frames: Whether to extract video frames
        prefer_captions: Prefer existing captions over Whisper

    Returns:
        Dictionary with video information and extracted content

    Raises:
        Retry: If processing fails and should be retried
    """
    logger.info(f"Processing YouTube video: {url}")

    try:
        # Initialize processor
        processor = YouTubeProcessor(
            cache_dir=Path("/tmp/hl_bot_youtube"),
            enable_whisper=True,
            max_video_duration=7200,  # 2 hours
            frame_interval=30,
        )

        # Process video (async)
        videos = run_async(
            processor.process_url(url, extract_frames, prefer_captions)
        )

        if not videos:
            raise YouTubeError("No videos processed")

        video = videos[0]

        # Serialize video info
        result = {
            "video_id": video.video_id,
            "title": video.title,
            "description": video.description,
            "duration": video.duration,
            "url": video.url,
            "transcript": video.transcript,
            "transcript_length": len(video.transcript),
            "channel": video.channel,
            "upload_date": video.upload_date,
            "num_frames": len(video.frames),
            "frame_paths": [str(f) for f in video.frames],
        }

        logger.info(
            f"Successfully processed video {video.video_id}: "
            f"{len(video.transcript)} chars, {len(video.frames)} frames"
        )

        return result

    except YouTubeError as e:
        logger.error(f"YouTube processing failed: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)

    except Exception as e:
        logger.error(f"Unexpected error processing YouTube video: {e}")
        # Don't retry on unexpected errors
        raise Ignore()


@celery_app.task(
    name="app.workers.tasks.process_youtube_playlist",
    base=CallbackTask,
    bind=True,
    autoretry_for=(YouTubeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_youtube_playlist(
    self: Task,
    url: str,
    extract_frames: bool = True,
    prefer_captions: bool = True,
) -> list[dict[str, Any]]:
    """Process an entire YouTube playlist.

    Args:
        url: YouTube playlist URL
        extract_frames: Whether to extract video frames
        prefer_captions: Prefer existing captions over Whisper

    Returns:
        List of dictionaries with video information

    Raises:
        Retry: If processing fails and should be retried
    """
    logger.info(f"Processing YouTube playlist: {url}")

    try:
        processor = YouTubeProcessor(
            cache_dir=Path("/tmp/hl_bot_youtube"),
            enable_whisper=True,
            max_video_duration=7200,
            frame_interval=30,
        )

        # Process playlist (async)
        videos = run_async(
            processor.process_url(url, extract_frames, prefer_captions)
        )

        results = []
        for video in videos:
            results.append({
                "video_id": video.video_id,
                "title": video.title,
                "description": video.description,
                "duration": video.duration,
                "url": video.url,
                "transcript": video.transcript,
                "transcript_length": len(video.transcript),
                "channel": video.channel,
                "upload_date": video.upload_date,
                "num_frames": len(video.frames),
                "frame_paths": [str(f) for f in video.frames],
            })

        logger.info(f"Successfully processed playlist with {len(videos)} videos")
        return results

    except YouTubeError as e:
        logger.error(f"Playlist processing failed: {e}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)

    except Exception as e:
        logger.error(f"Unexpected error processing playlist: {e}")
        raise Ignore()


@celery_app.task(
    name="app.workers.tasks.process_pdf_document",
    base=CallbackTask,
    bind=True,
    autoretry_for=(PDFError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_pdf_document(
    self: Task,
    pdf_path: str,
    extract_images: bool = True,
) -> dict[str, Any]:
    """Process a PDF document: extract text, images, and apply OCR if needed.

    Args:
        pdf_path: Path to PDF file
        extract_images: Whether to extract embedded images

    Returns:
        Dictionary with PDF information and extracted content

    Raises:
        Retry: If processing fails and should be retried
    """
    logger.info(f"Processing PDF document: {pdf_path}")

    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise PDFError(f"PDF file not found: {pdf_path}")

        # Initialize processor
        processor = PDFProcessor(
            cache_dir=Path("/tmp/hl_bot_pdf"),
            enable_ocr=True,
            min_image_size=(100, 100),
            max_pages=500,
            extract_images=extract_images,
        )

        # Process PDF (async)
        pdf_info = run_async(processor.process_file(pdf_file, extract_images))

        # Serialize PDF info
        result = {
            "filename": pdf_info.filename,
            "title": pdf_info.title,
            "author": pdf_info.author,
            "num_pages": pdf_info.num_pages,
            "full_text": pdf_info.get_full_text(),
            "text_length": len(pdf_info.get_full_text()),
            "num_images": len(pdf_info.get_all_images()),
            "image_paths": [str(img) for img in pdf_info.get_all_images()],
            "pages": [
                {
                    "page_num": page.page_num,
                    "text_length": len(page.text),
                    "ocr_text_length": len(page.ocr_text),
                    "num_images": len(page.images),
                    "has_text": page.has_text,
                }
                for page in pdf_info.pages
            ],
            "metadata": pdf_info.metadata,
        }

        logger.info(
            f"Successfully processed PDF {pdf_info.filename}: "
            f"{pdf_info.num_pages} pages, {len(pdf_info.get_full_text())} chars"
        )

        return result

    except PDFError as e:
        logger.error(f"PDF processing failed: {e}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)

    except Exception as e:
        logger.error(f"Unexpected error processing PDF: {e}")
        raise Ignore()


@celery_app.task(
    name="app.workers.tasks.extract_trading_strategy",
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def extract_trading_strategy(
    self: Task,
    content: str,
    content_type: str = "text",
    model: str = "claude-sonnet-4",
) -> dict[str, Any]:
    """Extract trading strategy from content using LLM.

    Args:
        content: Text content to analyze
        content_type: Type of content (text, transcript, etc.)
        model: LLM model to use

    Returns:
        Dictionary with extracted strategy information

    Raises:
        Retry: If extraction fails and should be retried
    """
    logger.info(f"Extracting trading strategy from {content_type} ({len(content)} chars)")

    try:
        from app.config import settings

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        # Initialize LLM client and strategy extractor
        llm_client = LLMClient(api_key=settings.anthropic_api_key)
        extractor = StrategyExtractor(llm_client=llm_client)

        # Extract strategy (async)
        strategy = run_async(extractor.extract_from_text(content, model))

        result = {
            "strategy": strategy,
            "content_type": content_type,
            "content_length": len(content),
            "model": model,
        }

        logger.info(f"Successfully extracted strategy using {model}")
        return result

    except Exception as e:
        logger.error(f"Strategy extraction failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
        raise Ignore()


@celery_app.task(
    name="app.workers.tasks.analyze_chart_image",
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def analyze_chart_image(
    self: Task,
    image_path: str,
    model: str = "claude-sonnet-4",
) -> dict[str, Any]:
    """Analyze a chart image to extract trading insights using LLM vision.

    Args:
        image_path: Path to chart image
        model: LLM model to use (must support vision)

    Returns:
        Dictionary with chart analysis

    Raises:
        Retry: If analysis fails and should be retried
    """
    logger.info(f"Analyzing chart image: {image_path}")

    try:
        from app.config import settings
        import base64

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        img_file = Path(image_path)
        if not img_file.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read image and encode to base64
        with open(img_file, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Initialize LLM client
        llm_client = LLMClient(api_key=settings.anthropic_api_key)

        # Analyze image (async)
        analysis = run_async(
            llm_client.analyze_image(
                image_data=image_data,
                prompt="Analyze this trading chart. Identify key patterns, support/resistance levels, "
                       "trend direction, and any notable technical indicators. Provide insights for trading decisions.",
                model=model,
            )
        )

        result = {
            "image_path": image_path,
            "analysis": analysis,
            "model": model,
        }

        logger.info(f"Successfully analyzed chart image using {model}")
        return result

    except Exception as e:
        logger.error(f"Chart image analysis failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
        raise Ignore()


@celery_app.task(name="app.workers.tasks.cleanup_youtube_cache")
def cleanup_youtube_cache(max_age_days: int = 7) -> dict[str, int]:
    """Clean up old YouTube cache files.

    Args:
        max_age_days: Remove files older than this many days

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Cleaning up YouTube cache older than {max_age_days} days")

    try:
        processor = YouTubeProcessor(cache_dir=Path("/tmp/hl_bot_youtube"))
        count = run_async(processor.cleanup_cache(max_age_days))

        logger.info(f"Cleaned up {count} YouTube cache directories")
        return {"removed": count, "type": "youtube"}

    except Exception as e:
        logger.error(f"YouTube cache cleanup failed: {e}")
        return {"removed": 0, "type": "youtube", "error": str(e)}


@celery_app.task(name="app.workers.tasks.cleanup_pdf_cache")
def cleanup_pdf_cache(max_age_days: int = 7) -> dict[str, int]:
    """Clean up old PDF cache files.

    Args:
        max_age_days: Remove files older than this many days

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Cleaning up PDF cache older than {max_age_days} days")

    try:
        processor = PDFProcessor(cache_dir=Path("/tmp/hl_bot_pdf"))
        count = run_async(processor.cleanup_cache(max_age_days))

        logger.info(f"Cleaned up {count} PDF cache directories")
        return {"removed": count, "type": "pdf"}

    except Exception as e:
        logger.error(f"PDF cache cleanup failed: {e}")
        return {"removed": 0, "type": "pdf", "error": str(e)}


# ============== Hyperliquid Data Sync Tasks ==============

@celery_app.task(
    name="app.workers.tasks.sync_hyperliquid_data",
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_hyperliquid_data(
    self: Task,
    symbol: str,
    timeframe: str,
    mode: str = "incremental",
) -> dict[str, Any]:
    """Sync historical OHLCV data from Hyperliquid for a symbol/timeframe.

    This task fetches candle data from the Hyperliquid API and stores it
    in the local database. Supports both full historical sync and 
    incremental updates.

    Args:
        symbol: Trading symbol (e.g., "BTC", "ETH")
        timeframe: Candle timeframe (e.g., "5m", "1h", "4h")
        mode: "full" for complete history, "incremental" for new data only

    Returns:
        Dictionary with sync results (candles fetched/inserted, time range)

    Raises:
        Retry: If sync fails and should be retried
    """
    logger.info(f"Starting Hyperliquid sync: {symbol}/{timeframe} ({mode})")

    try:
        from app.db.session import SessionLocal
        from app.services.data_sync import run_sync
        
        # Create database session
        db = SessionLocal()
        
        try:
            result = run_sync(
                db=db,
                symbol=symbol,
                timeframe=timeframe,
                mode=mode,
                testnet=False,
            )
            
            logger.info(
                f"Hyperliquid sync complete: {symbol}/{timeframe}, "
                f"fetched={result.get('candles_fetched', 0)}, "
                f"inserted={result.get('candles_inserted', 0)}"
            )
            
            return result
            
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Hyperliquid sync failed for {symbol}/{timeframe}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)
        raise Ignore()


@celery_app.task(
    name="app.workers.tasks.sync_hyperliquid_bulk",
    base=CallbackTask,
    bind=True,
)
def sync_hyperliquid_bulk(
    self: Task,
    symbols: list[str],
    timeframes: list[str] | None = None,
    mode: str = "incremental",
) -> dict[str, Any]:
    """Sync data for multiple symbols and timeframes.

    Runs syncs sequentially to respect rate limits.

    Args:
        symbols: List of trading symbols
        timeframes: List of timeframes (default: all configured timeframes)
        mode: Sync mode (full or incremental)

    Returns:
        Dictionary with overall results
    """
    from app.config import settings
    
    if timeframes is None:
        timeframes = settings.hl_sync_timeframes_list
    
    logger.info(f"Starting bulk Hyperliquid sync: {len(symbols)} symbols, {len(timeframes)} timeframes")

    results = []
    errors = []
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                result = sync_hyperliquid_data.delay(symbol, timeframe, mode)
                results.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "task_id": result.id,
                })
            except Exception as e:
                logger.error(f"Failed to queue sync for {symbol}/{timeframe}: {e}")
                errors.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                })
    
    return {
        "queued": len(results),
        "failed": len(errors),
        "tasks": results,
        "errors": errors,
    }


@celery_app.task(name="app.workers.tasks.sync_all_hyperliquid_data")
def sync_all_hyperliquid_data(
    mode: str = "incremental",
    timeframes: list[str] | None = None,
) -> dict[str, Any]:
    """Sync data for all available Hyperliquid symbols.

    Fetches the list of available symbols and queues sync tasks for each.

    Args:
        mode: Sync mode (full or incremental)
        timeframes: List of timeframes to sync

    Returns:
        Dictionary with overall results
    """
    logger.info(f"Starting full Hyperliquid sync ({mode})")

    try:
        from app.db.session import SessionLocal
        from app.services.data_sync import DataSyncService
        
        db = SessionLocal()
        
        try:
            # Get available symbols
            service = DataSyncService(db)
            symbols = run_async(service.get_available_symbols())
            
            logger.info(f"Found {len(symbols)} symbols on Hyperliquid")
            
            # Queue bulk sync
            result = sync_hyperliquid_bulk.delay(symbols, timeframes, mode)
            
            return {
                "symbols_found": len(symbols),
                "bulk_task_id": result.id,
                "symbols": symbols,
            }
            
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to start full Hyperliquid sync: {e}")
        return {"error": str(e)}


@celery_app.task(
    name="app.workers.tasks.sync_hyperliquid_hourly",
    base=CallbackTask,
    bind=True,
)
def sync_hyperliquid_hourly(self: Task) -> dict[str, Any]:
    """Hourly scheduled sync for all configured symbols and timeframes.
    
    This is the main scheduled task that runs every hour to keep data fresh.
    Syncs all timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M
    
    Returns:
        Dictionary with sync results summary
    """
    from app.config import settings
    
    symbols = settings.hl_sync_symbols_list
    timeframes = settings.hl_sync_timeframes_list
    
    logger.info(
        f"Starting hourly Hyperliquid sync: "
        f"{len(symbols)} symbols × {len(timeframes)} timeframes"
    )
    
    # Queue bulk sync for all symbols and timeframes
    result = sync_hyperliquid_bulk.delay(symbols, timeframes, "incremental")
    
    return {
        "scheduled_at": str(datetime.now(timezone.utc)),
        "symbols": symbols,
        "timeframes": timeframes,
        "bulk_task_id": result.id,
        "total_pairs": len(symbols) * len(timeframes),
    }


# ============== Data Retention & Cleanup Tasks ==============

@celery_app.task(
    name="app.workers.tasks.cleanup_old_candles",
    base=CallbackTask,
    bind=True,
)
def cleanup_old_candles(self: Task) -> dict[str, Any]:
    """Clean up old 1m candles using TimescaleDB drop_chunks().
    
    Retention policy:
    - 1m candles: Keep for 3 years (configurable via HL_RETENTION_1M_DAYS)
    - All other timeframes: Keep forever
    
    Uses TimescaleDB's drop_chunks() for efficient deletion of old data.
    This is much faster than DELETE queries for time-series data.
    
    Returns:
        Dictionary with cleanup results
    """
    from app.config import settings
    from app.db.session import SessionLocal
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text
    
    retention_days = settings.hl_retention_1m_days
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    logger.info(
        f"Starting cleanup of 1m candles older than {retention_days} days "
        f"(cutoff: {cutoff_date.isoformat()})"
    )
    
    db = SessionLocal()
    
    try:
        # Use TimescaleDB drop_chunks for efficient deletion
        # Only drop chunks for 1m timeframe data
        # We use a workaround since ohlcv_data has multiple timeframes:
        # First, count what we're about to delete
        count_result = db.execute(
            text("""
                SELECT COUNT(*) 
                FROM ohlcv_data 
                WHERE timeframe = '1m' 
                AND timestamp < :cutoff
            """),
            {"cutoff": cutoff_date}
        ).scalar()
        
        if count_result and count_result > 0:
            # Delete old 1m candles
            # For hypertables with mixed data, we need to use DELETE
            # but we can still benefit from chunk exclusion
            delete_result = db.execute(
                text("""
                    DELETE FROM ohlcv_data 
                    WHERE timeframe = '1m' 
                    AND timestamp < :cutoff
                """),
                {"cutoff": cutoff_date}
            )
            deleted_count = delete_result.rowcount
            db.commit()
            
            logger.info(f"Deleted {deleted_count} old 1m candles")
        else:
            deleted_count = 0
            logger.info("No old 1m candles to delete")
        
        # Also try to use drop_chunks if we have old chunks
        # This helps reclaim space more efficiently
        try:
            db.execute(
                text("""
                    SELECT drop_chunks(
                        'ohlcv_data', 
                        older_than => :cutoff::timestamptz,
                        verbose => true
                    )
                """),
                {"cutoff": cutoff_date}
            )
            db.commit()
            logger.info("TimescaleDB drop_chunks completed")
        except Exception as e:
            # drop_chunks might fail if chunks contain mixed data
            # This is expected - we fall back to DELETE above
            logger.debug(f"drop_chunks skipped (mixed timeframe chunks): {e}")
        
        return {
            "success": True,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "candles_found": count_result or 0,
            "candles_deleted": deleted_count,
            "cleaned_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
        }
    finally:
        db.close()


@celery_app.task(
    name="app.workers.tasks.run_timescaledb_maintenance",
    base=CallbackTask,
    bind=True,
)
def run_timescaledb_maintenance(self: Task) -> dict[str, Any]:
    """Run TimescaleDB maintenance tasks.
    
    Tasks performed:
    1. Compress chunks older than compression threshold
    2. Reorder chunks for better query performance
    3. Update statistics
    
    Returns:
        Dictionary with maintenance results
    """
    from app.config import settings
    from app.db.session import SessionLocal
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text
    
    compression_after_days = settings.hl_compression_after_days
    compress_older_than = datetime.now(timezone.utc) - timedelta(days=compression_after_days)
    
    logger.info(f"Starting TimescaleDB maintenance (compress chunks older than {compression_after_days} days)")
    
    db = SessionLocal()
    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "compression_threshold_days": compression_after_days,
        "operations": [],
    }
    
    try:
        # 1. Check if compression policy exists, if not, add it
        try:
            # Check existing compression settings
            compression_check = db.execute(
                text("""
                    SELECT * FROM timescaledb_information.compression_settings 
                    WHERE hypertable_name = 'ohlcv_data'
                """)
            ).fetchone()
            
            if not compression_check:
                # Enable compression on the hypertable
                db.execute(
                    text("""
                        ALTER TABLE ohlcv_data SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'symbol, timeframe, source',
                            timescaledb.compress_orderby = 'timestamp DESC'
                        )
                    """)
                )
                db.commit()
                results["operations"].append({
                    "operation": "enable_compression",
                    "status": "success",
                })
                logger.info("Enabled compression on ohlcv_data")
            else:
                results["operations"].append({
                    "operation": "enable_compression",
                    "status": "already_enabled",
                })
        except Exception as e:
            logger.warning(f"Compression setup check failed: {e}")
            results["operations"].append({
                "operation": "enable_compression",
                "status": "error",
                "error": str(e),
            })
        
        # 2. Manually compress chunks older than threshold
        try:
            compress_result = db.execute(
                text("""
                    SELECT compress_chunk(c.chunk_name::regclass)
                    FROM (
                        SELECT chunk_name 
                        FROM timescaledb_information.chunks 
                        WHERE hypertable_name = 'ohlcv_data'
                        AND NOT is_compressed
                        AND range_end < :compress_older_than
                    ) c
                """),
                {"compress_older_than": compress_older_than}
            )
            chunks_compressed = compress_result.rowcount
            db.commit()
            
            results["operations"].append({
                "operation": "compress_chunks",
                "status": "success",
                "chunks_compressed": chunks_compressed,
            })
            logger.info(f"Compressed {chunks_compressed} chunks")
        except Exception as e:
            logger.warning(f"Chunk compression failed: {e}")
            results["operations"].append({
                "operation": "compress_chunks",
                "status": "error",
                "error": str(e),
            })
        
        # 3. Update table statistics
        try:
            db.execute(text("ANALYZE ohlcv_data"))
            db.commit()
            results["operations"].append({
                "operation": "analyze_table",
                "status": "success",
            })
            logger.info("Updated table statistics")
        except Exception as e:
            logger.warning(f"ANALYZE failed: {e}")
            results["operations"].append({
                "operation": "analyze_table",
                "status": "error",
                "error": str(e),
            })
        
        # 4. Get compression stats
        try:
            stats = db.execute(
                text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE is_compressed) as compressed_chunks,
                        COUNT(*) FILTER (WHERE NOT is_compressed) as uncompressed_chunks,
                        COUNT(*) as total_chunks
                    FROM timescaledb_information.chunks 
                    WHERE hypertable_name = 'ohlcv_data'
                """)
            ).fetchone()
            
            if stats:
                results["compression_stats"] = {
                    "compressed_chunks": stats[0] or 0,
                    "uncompressed_chunks": stats[1] or 0,
                    "total_chunks": stats[2] or 0,
                }
        except Exception as e:
            logger.warning(f"Could not get compression stats: {e}")
        
        results["success"] = True
        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        return results
        
    except Exception as e:
        logger.error(f"TimescaleDB maintenance failed: {e}", exc_info=True)
        results["success"] = False
        results["error"] = str(e)
        return results
    finally:
        db.close()


# ============== Utility Functions ==============

from datetime import datetime, timezone
