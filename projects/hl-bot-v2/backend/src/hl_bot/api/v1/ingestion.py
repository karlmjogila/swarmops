"""API endpoints for content ingestion (YouTube, PDFs)."""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, HttpUrl

from hl_bot.services.ingestion.youtube_processor import (
    YouTubeError,
    YouTubeProcessor,
    VideoInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

# Global processor instance (can be moved to dependency injection later)
youtube_processor = YouTubeProcessor(
    enable_whisper=True,
    max_video_duration=7200,
    frame_interval=60,
)


class YouTubeIngestionRequest(BaseModel):
    """Request to ingest a YouTube video."""

    url: HttpUrl = Field(..., description="YouTube video URL (single video or playlist)")
    extract_frames: bool = Field(default=True, description="Whether to extract key frames")
    prefer_captions: bool = Field(
        default=True,
        description="Prefer existing captions over Whisper transcription",
    )


class VideoInfoResponse(BaseModel):
    """Video information response."""

    video_id: str
    title: str
    description: str
    duration: int
    url: str
    channel: str
    upload_date: str
    transcript_length: int
    num_frames: int


class ProcessedVideosResponse(BaseModel):
    """Response for processed video(s)."""

    videos: list[VideoInfoResponse]
    total_processed: int


class IngestionJobResponse(BaseModel):
    """Ingestion job status response."""

    job_id: str
    status: str
    message: str


@router.post("/youtube/process", response_model=ProcessedVideosResponse)
async def process_youtube_url(request: YouTubeIngestionRequest) -> ProcessedVideosResponse:
    """Process a YouTube URL (video or playlist).

    Downloads video(s), extracts transcripts, and optionally extracts frames.

    Args:
        request: YouTube ingestion request

    Returns:
        Processed video information

    Raises:
        HTTPException: If processing fails
    """
    logger.info(f"Processing YouTube URL: {request.url}")

    try:
        videos = await youtube_processor.process_url(
            url=str(request.url),
            extract_frames=request.extract_frames,
            prefer_captions=request.prefer_captions,
        )

        return ProcessedVideosResponse(
            videos=[
                VideoInfoResponse(
                    video_id=video.video_id,
                    title=video.title,
                    description=video.description,
                    duration=video.duration,
                    url=video.url,
                    channel=video.channel,
                    upload_date=video.upload_date,
                    transcript_length=len(video.transcript),
                    num_frames=len(video.frames),
                )
                for video in videos
            ],
            total_processed=len(videos),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
    except YouTubeError as e:
        raise HTTPException(status_code=422, detail=f"Processing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def _process_video_background(url: str, extract_frames: bool, job_id: str) -> None:
    """Background task for video processing.

    Args:
        url: YouTube URL
        extract_frames: Whether to extract frames
        job_id: Job identifier for tracking
    """
    logger.info(f"Starting background processing for job {job_id}: {url}")

    try:
        videos = await youtube_processor.process_url(
            url=url,
            extract_frames=extract_frames,
            prefer_captions=True,
        )

        logger.info(
            f"Job {job_id} completed: {len(videos)} video(s) processed"
        )

        # TODO: Store results in database or send to strategy extractor
        # For now, just log completion

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)


@router.post("/youtube/process-async", response_model=IngestionJobResponse)
async def process_youtube_url_async(
    request: YouTubeIngestionRequest,
    background_tasks: BackgroundTasks,
) -> IngestionJobResponse:
    """Start background processing of a YouTube video/playlist.

    Use this for long videos or playlists to avoid request timeouts.
    Poll the job status endpoint to check progress.

    Args:
        request: YouTube ingestion request
        background_tasks: FastAPI background tasks

    Returns:
        Job status response
    """
    # Generate job ID
    import uuid

    job_id = str(uuid.uuid4())

    # Add background task
    background_tasks.add_task(
        _process_video_background,
        str(request.url),
        request.extract_frames,
        job_id,
    )

    logger.info(f"Queued background processing job {job_id} for {request.url}")

    return IngestionJobResponse(
        job_id=job_id,
        status="queued",
        message="Video processing started in background",
    )


@router.delete("/cache")
async def cleanup_cache(max_age_days: int = 7) -> dict[str, Any]:
    """Clean up old cached files.

    Args:
        max_age_days: Delete files older than this many days

    Returns:
        Cleanup statistics
    """
    try:
        deleted = await youtube_processor.cleanup_cache(max_age_days=max_age_days)

        return {
            "deleted_directories": deleted,
            "max_age_days": max_age_days,
            "message": f"Cleaned up {deleted} cache directories older than {max_age_days} days",
        }

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")


# ============================================================================
# PDF Processing Endpoints
# ============================================================================

from hl_bot.services.ingestion.pdf_processor import PDFProcessor, PDFError

# Global PDF processor instance
pdf_processor = PDFProcessor(
    enable_ocr=True,
    max_pages=500,
    extract_images=True,
)


class PDFPageResponse(BaseModel):
    """PDF page content response."""
    
    page_num: int
    text: str
    images: list[str]
    has_text: bool


class ProcessedPDFResponse(BaseModel):
    """Processed PDF response."""
    
    filename: str
    title: str
    author: str
    num_pages: int
    pages: list[PDFPageResponse]
    total_images: int
    processing_time_seconds: float


@router.post("/pdf/process", response_model=ProcessedPDFResponse)
async def process_pdf(
    file: UploadFile = File(..., description="PDF file to process")
) -> ProcessedPDFResponse:
    """Process a PDF file: extract text and images.
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        Processed PDF data
        
    Raises:
        HTTPException: If processing fails
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    logger.info(f"Processing PDF: {file.filename}")
    
    try:
        # Read file content
        content = await file.read()
        
        # Process PDF
        import time
        start_time = time.time()
        
        result = await pdf_processor.process_bytes(
            pdf_bytes=content,
            filename=file.filename,
            extract_images=True,
        )
        
        processing_time = time.time() - start_time
        
        # Convert to response format
        pages_response = []
        for page in result.pages:
            pages_response.append(PDFPageResponse(
                page_num=page.page_num,
                text=page.get_full_text(),
                images=[str(img) for img in page.images],
                has_text=page.has_text,
            ))
        
        return ProcessedPDFResponse(
            filename=result.filename,
            title=result.title,
            author=result.author,
            num_pages=result.num_pages,
            pages=pages_response,
            total_images=len(result.get_all_images()),
            processing_time_seconds=processing_time,
        )
        
    except PDFError as e:
        raise HTTPException(status_code=422, detail=f"PDF processing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/pdf/metadata")
async def get_pdf_metadata(
    file: UploadFile = File(..., description="PDF file")
) -> dict[str, Any]:
    """Get PDF metadata without full processing.
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        PDF metadata
        
    Raises:
        HTTPException: If metadata extraction fails
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        content = await file.read()
        
        # Write to temp file for metadata extraction
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            metadata = await pdf_processor._get_metadata(tmp_path)
            
            return {
                "filename": file.filename,
                "num_pages": metadata.get("num_pages", 0),
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
            }
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Failed to extract PDF metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Metadata extraction failed: {e}")


@router.post("/pdf/extract-tables")
async def extract_tables_from_pdf(
    file: UploadFile = File(..., description="PDF file"),
    page_num: int | None = None,
) -> dict[str, Any]:
    """Extract tables from a PDF.
    
    Args:
        file: Uploaded PDF file
        page_num: Specific page number (1-indexed), or None for all pages
        
    Returns:
        Extracted tables
        
    Raises:
        HTTPException: If extraction fails
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        content = await file.read()
        
        # Write to temp file
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            tables = await pdf_processor.extract_tables(tmp_path, page_num)
            
            return {
                "filename": file.filename,
                "page_num": page_num,
                "total_tables": len(tables),
                "tables": tables,
            }
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Table extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Table extraction failed: {e}")
