"""Simplified content ingestion API with job tracking."""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl

from hl_bot.services.ingestion.youtube_processor import YouTubeError, YouTubeProcessor
from hl_bot.services.ingestion.pdf_processor import PDFError, PDFProcessor
from hl_bot.services.ingestion.image_analyzer import ImageAnalyzer, ImageAnalyzerError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

# Initialize processors
youtube_processor = YouTubeProcessor(
    enable_whisper=True,
    max_video_duration=7200,
    frame_interval=60,
)

pdf_processor = PDFProcessor(
    enable_ocr=True,
    max_pages=500,
    extract_images=True,
)

image_analyzer = ImageAnalyzer(
    cache_dir=Path("./data/image_cache"),
    max_image_size=10 * 1024 * 1024,  # 10MB
)


# ============================================================================
# Job Tracking (In-memory for MVP, move to database later)
# ============================================================================

class JobStore:
    """In-memory job storage."""
    
    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
    
    def create_job(
        self,
        content_type: str,
        url: str | None = None,
        filename: str | None = None,
    ) -> str:
        """Create a new job."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "id": job_id,
            "content_source": {
                "content_type": content_type,
                "url": url,
                "file_content": None,
                "metadata": {"filename": filename} if filename else {},
            },
            "status": "pending",
            "progress": 0.0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error_message": None,
            "extracted_strategies": [],
        }
        return job_id
    
    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> list[dict[str, Any]]:
        """Get all jobs sorted by started_at descending."""
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda x: x["started_at"], reverse=True)
        return jobs
    
    def update_job(self, job_id: str, **updates) -> None:
        """Update job fields."""
        if job_id in self._jobs:
            self._jobs[job_id].update(updates)
    
    def update_progress(self, job_id: str, progress: float) -> None:
        """Update job progress."""
        self.update_job(job_id, progress=progress, status="processing")
    
    def mark_completed(self, job_id: str, extracted_strategies: list[str] | None = None) -> None:
        """Mark job as completed."""
        self.update_job(
            job_id,
            status="completed",
            progress=1.0,
            completed_at=datetime.utcnow().isoformat(),
            extracted_strategies=extracted_strategies or [],
        )
    
    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        self.update_job(
            job_id,
            status="failed",
            completed_at=datetime.utcnow().isoformat(),
            error_message=error,
        )


# Global job store
job_store = JobStore()


# ============================================================================
# Request/Response Models
# ============================================================================

class YouTubeRequest(BaseModel):
    """YouTube URL submission request."""
    
    url: HttpUrl


class PDFUploadResponse(BaseModel):
    """PDF upload response."""
    
    job_id: str


class JobResponse(BaseModel):
    """Job status response."""
    
    job_id: str


class JobListResponse(BaseModel):
    """List of jobs."""
    
    jobs: list[dict[str, Any]]


# ============================================================================
# Background Processing Tasks
# ============================================================================

async def process_youtube_job(job_id: str, url: str) -> None:
    """Background task to process YouTube video."""
    logger.info(f"[Job {job_id}] Starting YouTube processing: {url}")
    
    try:
        # Update to processing status
        job_store.update_progress(job_id, 0.1)
        
        # Process video
        videos = await youtube_processor.process_url(
            url=url,
            extract_frames=True,
            prefer_captions=True,
        )
        
        job_store.update_progress(job_id, 0.6)
        
        # TODO: Extract strategies using LLM
        # For now, just mark as completed with mock data
        logger.info(f"[Job {job_id}] Processed {len(videos)} video(s)")
        
        job_store.update_progress(job_id, 0.9)
        
        # Simulate strategy extraction
        await asyncio.sleep(1)
        
        # Mark as completed
        # In real implementation, this would be the extracted strategy IDs
        job_store.mark_completed(job_id, extracted_strategies=[])
        
        logger.info(f"[Job {job_id}] Completed successfully")
        
    except YouTubeError as e:
        logger.error(f"[Job {job_id}] YouTube processing failed: {e}")
        job_store.mark_failed(job_id, str(e))
    except Exception as e:
        logger.error(f"[Job {job_id}] Unexpected error: {e}", exc_info=True)
        job_store.mark_failed(job_id, f"Internal error: {str(e)}")


async def process_pdf_job(job_id: str, pdf_bytes: bytes, filename: str) -> None:
    """Background task to process PDF."""
    logger.info(f"[Job {job_id}] Starting PDF processing: {filename}")
    
    try:
        # Update to processing status
        job_store.update_progress(job_id, 0.1)
        
        # Process PDF
        result = await pdf_processor.process_bytes(
            pdf_bytes=pdf_bytes,
            filename=filename,
            extract_images=True,
        )
        
        job_store.update_progress(job_id, 0.6)
        
        # TODO: Extract strategies using LLM
        # For now, just mark as completed
        logger.info(
            f"[Job {job_id}] Processed PDF: {result.num_pages} pages, "
            f"{len(result.get_all_images())} images"
        )
        
        job_store.update_progress(job_id, 0.9)
        
        # Simulate strategy extraction
        await asyncio.sleep(1)
        
        # Mark as completed
        job_store.mark_completed(job_id, extracted_strategies=[])
        
        logger.info(f"[Job {job_id}] Completed successfully")
        
    except PDFError as e:
        logger.error(f"[Job {job_id}] PDF processing failed: {e}")
        job_store.mark_failed(job_id, str(e))
    except Exception as e:
        logger.error(f"[Job {job_id}] Unexpected error: {e}", exc_info=True)
        job_store.mark_failed(job_id, f"Internal error: {str(e)}")


async def process_image_job(job_id: str, image_bytes: bytes, filename: str) -> None:
    """Background task to process chart image."""
    logger.info(f"[Job {job_id}] Starting image analysis: {filename}")
    
    try:
        # Update to processing status
        job_store.update_progress(job_id, 0.1)
        
        # Analyze image
        result = await image_analyzer.analyze_image(
            image_source=image_bytes,
            filename=filename,
            use_structured_output=False,
        )
        
        job_store.update_progress(job_id, 0.7)
        
        # TODO: Extract strategies from chart analysis
        # For now, just log the analysis
        logger.info(
            f"[Job {job_id}] Analyzed chart: "
            f"bias={result.analysis.trading_bias}, "
            f"patterns={len(result.analysis.patterns)}, "
            f"confidence={result.analysis.confidence_score:.2f}"
        )
        
        job_store.update_progress(job_id, 0.9)
        
        # Simulate strategy extraction
        await asyncio.sleep(0.5)
        
        # Mark as completed
        job_store.mark_completed(job_id, extracted_strategies=[])
        
        logger.info(f"[Job {job_id}] Completed successfully")
        
    except ImageAnalyzerError as e:
        logger.error(f"[Job {job_id}] Image analysis failed: {e}")
        job_store.mark_failed(job_id, str(e))
    except Exception as e:
        logger.error(f"[Job {job_id}] Unexpected error: {e}", exc_info=True)
        job_store.mark_failed(job_id, f"Internal error: {str(e)}")


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/youtube", response_model=JobResponse)
async def submit_youtube_url(
    request: YouTubeRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Submit a YouTube URL for processing.
    
    Args:
        request: YouTube URL request
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID for tracking
    """
    logger.info(f"Received YouTube URL: {request.url}")
    
    # Create job
    job_id = job_store.create_job(
        content_type="youtube",
        url=str(request.url),
    )
    
    # Queue background processing
    background_tasks.add_task(
        process_youtube_job,
        job_id,
        str(request.url),
    )
    
    return JobResponse(job_id=job_id)


@router.post("/pdf", response_model=JobResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
) -> JobResponse:
    """Upload a PDF file for processing.
    
    Args:
        file: PDF file upload
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID for tracking
        
    Raises:
        HTTPException: If file is not a PDF
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    logger.info(f"Received PDF upload: {file.filename}")
    
    # Read file content
    content = await file.read()
    
    # Create job
    job_id = job_store.create_job(
        content_type="pdf",
        filename=file.filename,
    )
    
    # Queue background processing
    background_tasks.add_task(
        process_pdf_job,
        job_id,
        content,
        file.filename,
    )
    
    return JobResponse(job_id=job_id)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs() -> JobListResponse:
    """Get all ingestion jobs.
    
    Returns:
        List of jobs sorted by created date descending
    """
    jobs = job_store.get_all_jobs()
    return JobListResponse(jobs=jobs)


@router.post("/image", response_model=JobResponse)
async def upload_chart_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
) -> JobResponse:
    """Upload a chart screenshot for analysis.
    
    Args:
        file: Image file upload (PNG, JPG, JPEG, WEBP)
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID for tracking
        
    Raises:
        HTTPException: If file is not a supported image format
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    ext = file.filename.lower().split(".")[-1]
    if ext not in ["png", "jpg", "jpeg", "webp"]:
        raise HTTPException(
            status_code=400,
            detail="File must be PNG, JPG, JPEG, or WEBP"
        )
    
    logger.info(f"Received chart image upload: {file.filename}")
    
    # Read file content
    content = await file.read()
    
    # Create job
    job_id = job_store.create_job(
        content_type="image",
        filename=file.filename,
    )
    
    # Queue background processing
    background_tasks.add_task(
        process_image_job,
        job_id,
        content,
        file.filename,
    )
    
    return JobResponse(job_id=job_id)


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get status of a specific job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status
        
    Raises:
        HTTPException: If job not found
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return job
