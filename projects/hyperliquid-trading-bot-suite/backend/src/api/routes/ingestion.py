"""Ingestion endpoints for PDFs and videos."""

import uuid
import os
import asyncio
import hashlib
import secrets
from typing import Dict, Any, List, Annotated
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator
import structlog

from ...config import settings
from ..security import get_current_active_user, require_role
from ..security.auth import UserInDB, UserRole
from ..security.rate_limiter import rate_limit, RateLimitTier

router = APIRouter()
logger = structlog.get_logger()


# In-memory task storage (replace with database in production)
_ingestion_tasks = {}

# Allowed file magic bytes for PDF
PDF_MAGIC_BYTES = b'%PDF'

# Maximum file sizes
MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
MAX_ALLOWED_EXTENSIONS = {'.pdf'}


class IngestionResponse(BaseModel):
    """Response model for ingestion requests."""
    task_id: str
    status: str
    message: str


class IngestionStatus(BaseModel):
    """Status model for ingestion tasks."""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float = Field(ge=0.0, le=1.0, description="Progress from 0.0 to 1.0")
    message: str
    rules_extracted: int = Field(ge=0, default=0)
    errors: List[str] = []
    created_at: str
    completed_at: str | None = None
    user_id: str | None = None


class VideoIngestionRequest(BaseModel):
    """Request model for video ingestion."""
    url: str
    extract_frames: bool = True
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        # Normalize URL
        v = v.strip()
        
        # Validate YouTube URL format
        if not any(domain in v.lower() for domain in ['youtube.com', 'youtu.be']):
            raise ValueError('Only YouTube URLs are supported')
        
        # Basic URL validation to prevent injection
        if any(char in v for char in ['<', '>', '"', "'", ';', '|', '&', '$', '`']):
            raise ValueError('URL contains invalid characters')
        
        # Ensure it starts with https
        if not v.startswith('https://'):
            if v.startswith('http://'):
                v = v.replace('http://', 'https://', 1)
            elif v.startswith('www.'):
                v = 'https://' + v
            elif v.startswith('youtube.com') or v.startswith('youtu.be'):
                v = 'https://' + v
        
        return v


def validate_pdf_content(content: bytes) -> bool:
    """
    Validate that file content is actually a PDF.
    
    Checks magic bytes to prevent malicious file uploads.
    """
    if len(content) < 4:
        return False
    
    # Check PDF magic bytes
    if not content.startswith(PDF_MAGIC_BYTES):
        return False
    
    # Additional check: PDF should end with %%EOF
    # (Allow for trailing whitespace)
    tail = content[-1024:] if len(content) > 1024 else content
    if b'%%EOF' not in tail:
        logger.warning("PDF file missing %%EOF marker")
        # This is a warning, not a rejection - some PDFs are malformed but still valid
    
    return True


def generate_safe_filename(original_filename: str, task_id: str) -> str:
    """
    Generate a safe filename that prevents path traversal.
    
    The original filename is hashed and combined with a random suffix.
    """
    # Get extension safely
    ext = Path(original_filename).suffix.lower()
    if ext not in MAX_ALLOWED_EXTENSIONS:
        ext = '.pdf'  # Force .pdf extension
    
    # Generate hash of original filename for reference
    filename_hash = hashlib.sha256(original_filename.encode()).hexdigest()[:8]
    
    # Generate random suffix
    random_suffix = secrets.token_hex(8)
    
    return f"{task_id}_{filename_hash}_{random_suffix}{ext}"


async def _process_pdf_task(task_id: str, file_path: str, user_id: str, extract_images: bool = True):
    """Background task for PDF processing."""
    try:
        # Lazy import to avoid loading dependencies on startup
        from ...ingestion.ingestion_orchestrator import IngestionOrchestrator
        
        _ingestion_tasks[task_id]['status'] = 'processing'
        _ingestion_tasks[task_id]['progress'] = 0.1
        
        # Initialize orchestrator
        orchestrator = IngestionOrchestrator()
        
        # Process PDF
        result = await orchestrator.process_pdf(file_path, extract_images=extract_images)
        
        _ingestion_tasks[task_id]['status'] = 'completed'
        _ingestion_tasks[task_id]['progress'] = 1.0
        _ingestion_tasks[task_id]['rules_extracted'] = len(result.rules)
        _ingestion_tasks[task_id]['message'] = f"Successfully extracted {len(result.rules)} rules"
        _ingestion_tasks[task_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info("PDF processing completed", task_id=task_id, rules=len(result.rules), user_id=user_id)
        
    except Exception as e:
        logger.error("PDF processing failed", task_id=task_id, error=str(e), user_id=user_id)
        _ingestion_tasks[task_id]['status'] = 'failed'
        _ingestion_tasks[task_id]['message'] = f"Processing failed: {str(e)}"
        _ingestion_tasks[task_id]['errors'].append(str(e))
    finally:
        # Clean up uploaded file after processing
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("Cleaned up uploaded file", file_path=file_path)
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {e}")


async def _process_video_task(task_id: str, url: str, user_id: str, extract_frames: bool = True):
    """Background task for video processing."""
    try:
        # Lazy import to avoid loading dependencies on startup
        from ...ingestion.ingestion_orchestrator import IngestionOrchestrator
        
        _ingestion_tasks[task_id]['status'] = 'processing'
        _ingestion_tasks[task_id]['progress'] = 0.1
        
        # Initialize orchestrator
        orchestrator = IngestionOrchestrator()
        
        # Process video
        result = await orchestrator.process_video(url, extract_frames=extract_frames)
        
        _ingestion_tasks[task_id]['status'] = 'completed'
        _ingestion_tasks[task_id]['progress'] = 1.0
        _ingestion_tasks[task_id]['rules_extracted'] = len(result.rules)
        _ingestion_tasks[task_id]['message'] = f"Successfully extracted {len(result.rules)} rules"
        _ingestion_tasks[task_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info("Video processing completed", task_id=task_id, rules=len(result.rules), user_id=user_id)
        
    except Exception as e:
        logger.error("Video processing failed", task_id=task_id, error=str(e), user_id=user_id)
        _ingestion_tasks[task_id]['status'] = 'failed'
        _ingestion_tasks[task_id]['message'] = f"Processing failed: {str(e)}"
        _ingestion_tasks[task_id]['errors'].append(str(e))


@router.post("/pdf", response_model=IngestionResponse, summary="Upload and process PDF", status_code=202)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.STRATEGIST))],
    file: UploadFile = File(..., description="PDF file to process"),
    extract_images: bool = Form(True, description="Whether to extract images from PDF"),
    _: None = Depends(rate_limit(RateLimitTier.UPLOAD))
) -> IngestionResponse:
    """
    Upload and process a PDF document to extract trading strategies.
    
    Requires strategist role.
    
    The system will:
    1. Extract text and images from the PDF
    2. Use LLM to analyze content and extract strategy rules
    3. Store structured rules in the knowledge base
    
    Processing happens asynchronously. Use GET /ingestion/status/{task_id} to track progress.
    
    Security:
    - Files are validated by content (magic bytes), not just extension
    - Filenames are sanitized to prevent path traversal
    - Files are deleted after processing
    """
    # Validate file extension first
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in MAX_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(MAX_ALLOWED_EXTENSIONS)} files are supported"
        )
    
    # Read file content
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")
    
    # Validate file size
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    if len(contents) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_PDF_SIZE // (1024*1024)}MB)"
        )
    
    # Validate file content (magic bytes)
    if not validate_pdf_content(contents):
        logger.warning(
            "Invalid PDF content uploaded",
            filename=file.filename,
            user=current_user.username
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file. The file does not appear to be a valid PDF."
        )
    
    # Generate task ID
    task_id = f"pdf_{uuid.uuid4().hex[:12]}"
    
    # Generate safe filename
    safe_filename = generate_safe_filename(file.filename, task_id)
    
    # Save uploaded file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename
    
    try:
        with open(file_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        logger.error("File save failed", filename=safe_filename, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # Initialize task tracking
    _ingestion_tasks[task_id] = {
        'task_id': task_id,
        'status': 'pending',
        'progress': 0.0,
        'message': f"PDF queued for processing",
        'rules_extracted': 0,
        'errors': [],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'completed_at': None,
        'user_id': current_user.id
    }
    
    # Queue background task
    background_tasks.add_task(
        _process_pdf_task,
        task_id,
        str(file_path),
        current_user.id,
        extract_images
    )
    
    logger.info(
        "PDF ingestion requested",
        task_id=task_id,
        original_filename=file.filename,
        safe_filename=safe_filename,
        user=current_user.username,
        size_bytes=len(contents)
    )
    
    return IngestionResponse(
        task_id=task_id,
        status="pending",
        message=f"PDF queued for processing"
    )


@router.post("/video", response_model=IngestionResponse, summary="Process YouTube video", status_code=202)
async def ingest_video(
    background_tasks: BackgroundTasks,
    request: VideoIngestionRequest,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.STRATEGIST))],
    _: None = Depends(rate_limit(RateLimitTier.UPLOAD))
) -> IngestionResponse:
    """
    Process a YouTube video to extract trading strategies.
    
    Requires strategist role.
    
    The system will:
    1. Download video and extract audio
    2. Transcribe audio using Whisper
    3. Extract frames at regular intervals
    4. Use LLM to analyze transcript + frames and extract strategy rules
    5. Store structured rules in the knowledge base
    
    Processing happens asynchronously. Use GET /ingestion/status/{task_id} to track progress.
    """
    # Generate task ID
    task_id = f"video_{uuid.uuid4().hex[:12]}"
    
    # Initialize task tracking
    _ingestion_tasks[task_id] = {
        'task_id': task_id,
        'status': 'pending',
        'progress': 0.0,
        'message': f"Video queued for processing",
        'rules_extracted': 0,
        'errors': [],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'completed_at': None,
        'user_id': current_user.id
    }
    
    # Queue background task
    background_tasks.add_task(
        _process_video_task,
        task_id,
        request.url,
        current_user.id,
        request.extract_frames
    )
    
    logger.info(
        "Video ingestion requested",
        task_id=task_id,
        url=request.url,
        user=current_user.username
    )
    
    return IngestionResponse(
        task_id=task_id,
        status="pending",
        message=f"Video queued for processing"
    )


@router.get("/status/{task_id}", response_model=IngestionStatus, summary="Get ingestion status")
async def get_ingestion_status(
    task_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> IngestionStatus:
    """
    Get the status of an ingestion task.
    
    Users can only see their own tasks unless they are admin.
    """
    # Validate task ID format
    if not (task_id.startswith('pdf_') or task_id.startswith('video_')):
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    # Get task status
    task_data = _ingestion_tasks.get(task_id)
    
    if not task_data:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found"
        )
    
    # Check ownership (admin can see all)
    if task_data.get('user_id') != current_user.id and 'admin' not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view this task"
        )
    
    logger.info("Status requested", task_id=task_id, status=task_data['status'], user=current_user.username)
    
    return IngestionStatus(**task_data)


@router.get("/tasks", summary="List all ingestion tasks")
async def list_ingestion_tasks(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    status: str | None = None,
    limit: int = 50,
    _: None = Depends(rate_limit(RateLimitTier.READ))
) -> List[IngestionStatus]:
    """
    List all ingestion tasks with their current status.
    
    Users can only see their own tasks unless they are admin.
    """
    # Validate limit
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    # Validate status filter
    if status and status not in ['pending', 'processing', 'completed', 'failed']:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be one of: pending, processing, completed, failed"
        )
    
    # Filter tasks by ownership (admin sees all)
    is_admin = 'admin' in current_user.roles
    tasks = [
        t for t in _ingestion_tasks.values()
        if (is_admin or t.get('user_id') == current_user.id)
    ]
    
    if status:
        tasks = [t for t in tasks if t['status'] == status]
    
    # Sort by creation time (newest first)
    tasks.sort(key=lambda t: t['created_at'], reverse=True)
    
    # Apply limit
    tasks = tasks[:limit]
    
    logger.info(
        "Task list requested",
        count=len(tasks),
        status_filter=status,
        user=current_user.username
    )
    
    return [IngestionStatus(**task) for task in tasks]


@router.delete("/tasks/{task_id}", summary="Delete ingestion task")
async def delete_ingestion_task(
    task_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    _: None = Depends(rate_limit(RateLimitTier.MUTATION))
) -> Dict[str, Any]:
    """
    Delete an ingestion task and its data.
    
    Users can only delete their own tasks unless they are admin.
    """
    # Validate task ID format
    if not (task_id.startswith('pdf_') or task_id.startswith('video_')):
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    if task_id not in _ingestion_tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    
    task_data = _ingestion_tasks[task_id]
    
    # Check ownership (admin can delete all)
    if task_data.get('user_id') != current_user.id and 'admin' not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this task"
        )
    
    # Remove task
    del _ingestion_tasks[task_id]
    
    logger.info("Task deleted", task_id=task_id, user=current_user.username)
    
    return {"message": "Task deleted successfully", "task_id": task_id}
