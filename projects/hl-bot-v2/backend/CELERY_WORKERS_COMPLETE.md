# Celery Workers Implementation Complete

## Summary

Successfully implemented Celery workers for background processing of trading content including YouTube videos, PDF documents, and LLM-based strategy extraction.

## What Was Implemented

### 1. Celery Application Configuration (`app/celery_app.py`)
- Configured Celery app with Redis as broker and result backend
- Set up task queues: `default`, `youtube`, `pdf`, `llm`
- Configured task routing for different task types
- Set up periodic tasks (cache cleanup) with Celery Beat
- Configured retry policies, time limits, and worker settings

### 2. Worker Tasks (`app/workers/tasks.py`)
Implemented the following background tasks:

#### YouTube Processing
- **`process_youtube_video`** - Process single YouTube videos
  - Downloads video, extracts transcript (captions or Whisper)
  - Extracts frames at regular intervals
  - Automatic retry with exponential backoff
  - Routes to `youtube` queue

- **`process_youtube_playlist`** - Process entire playlists
  - Handles multiple videos from a playlist URL
  - Same features as single video processing
  - Routes to `youtube` queue

#### PDF Processing
- **`process_pdf_document`** - Process PDF documents
  - Extracts text content from all pages
  - Extracts embedded images (with size filtering)
  - Applies OCR to image-based PDFs if needed
  - Routes to `pdf` queue

#### LLM Strategy Extraction
- **`extract_trading_strategy`** - Extract trading strategies from text
  - Uses Claude API to analyze content
  - Extracts structured trading strategies
  - Routes to `llm` queue

- **`analyze_chart_image`** - Analyze chart images
  - Uses Claude vision API to analyze chart patterns
  - Identifies support/resistance, trends, indicators
  - Routes to `llm` queue

#### Cache Maintenance
- **`cleanup_youtube_cache`** - Periodic YouTube cache cleanup
  - Runs daily via Celery Beat
  - Removes files older than 7 days

- **`cleanup_pdf_cache`** - Periodic PDF cache cleanup
  - Runs daily via Celery Beat
  - Removes files older than 7 days

### 3. Task Features
- **Error Handling**: Custom `CallbackTask` base class with success/failure/retry callbacks
- **Retry Logic**: Automatic retry with exponential backoff (3 retries max)
- **Time Limits**: 30-minute soft limit, 40-minute hard limit
- **Async Support**: Helper function to run async processors in Celery tasks
- **Monitoring**: Detailed logging for task execution and failures

### 4. Docker Compose Integration
Updated `docker-compose.yml` to include:
- **celery-worker**: Processes tasks from all queues with concurrency=2
- **celery-beat**: Schedules periodic tasks (cache cleanup)
- Both services share volumes with backend for cache access

### 5. Configuration Updates
- Added Celery and Redis to `pyproject.toml` dependencies
- Updated `.env.example` with Redis URL configuration
- Updated `app/config.py` with Redis URL setting

### 6. Documentation
- **`CELERY_WORKERS.md`**: Comprehensive guide covering:
  - Architecture overview
  - Task descriptions and usage examples
  - Running workers (local, Docker, production)
  - Configuration and environment variables
  - Monitoring and troubleshooting
  - Performance tips and best practices

### 7. Testing
- **`tests/test_celery_tasks.py`**: Unit tests for all tasks
  - Mocked processor execution
  - Tests for success cases
  - Tests for task configuration
  - Tests for retry behavior

### 8. Worker Entry Point
- **`worker.py`**: Entry point script with usage instructions
- Can be used to start workers or as reference for commands

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
│                                                                   │
│  API Endpoints  ──►  Enqueue Tasks  ──►  Redis Broker           │
└─────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Celery Workers (x2)                         │
│                                                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│  │  YouTube  │  │    PDF    │  │    LLM    │  │  Default  │   │
│  │   Queue   │  │   Queue   │  │   Queue   │  │   Queue   │   │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
│        │              │              │              │            │
│        ▼              ▼              ▼              ▼            │
│   YouTubeProc    PDFProc       LLMClient      Other Tasks       │
└─────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
                                     Redis Result Backend
                                                │
                                                ▼
                                        FastAPI Backend
                                        (Poll Results)
```

## Queue Routing

- **youtube**: YouTube video and playlist processing
- **pdf**: PDF document processing
- **llm**: LLM-based strategy extraction and chart analysis
- **default**: General tasks and cache cleanup

## Usage Examples

### From Python Code

```python
from app.workers.tasks import process_youtube_video

# Enqueue video processing
result = process_youtube_video.delay(
    url="https://www.youtube.com/watch?v=VIDEO_ID",
    extract_frames=True
)

# Check status
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE

# Get result (blocking)
video_info = result.get(timeout=600)
print(f"Processed: {video_info['title']}")
```

### From FastAPI Endpoint

```python
from fastapi import APIRouter
from app.workers.tasks import process_youtube_video

router = APIRouter()

@router.post("/process-video")
async def process_video(url: str):
    # Enqueue task
    task = process_youtube_video.delay(url=url)
    
    return {
        "task_id": task.id,
        "status": "Processing",
        "message": "Video processing started"
    }

@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    from app.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.ready() else None
    }
```

## Running Workers

### Development (Docker Compose)
```bash
# Start all services including workers
docker-compose up -d

# View worker logs
docker-compose logs -f celery-worker

# View beat scheduler logs
docker-compose logs -f celery-beat
```

### Development (Local)
```bash
# Terminal 1: Start worker
cd backend
celery -A app.celery_app worker --loglevel=info --concurrency=2

# Terminal 2: Start beat scheduler
celery -A app.celery_app beat --loglevel=info
```

### Monitoring
```bash
# Check active tasks
celery -A app.celery_app inspect active

# Check registered tasks
celery -A app.celery_app inspect registered

# Check worker stats
celery -A app.celery_app inspect stats
```

## Performance Characteristics

- **Concurrency**: 2 workers by default (configurable)
- **Task Limits**: 30min soft, 40min hard time limits
- **Retry Policy**: 3 retries with exponential backoff (60s, 120s, 240s)
- **Memory Management**: Workers restart after 50 tasks to prevent leaks
- **Prefetch**: 1 task per worker (for long-running tasks)

## Dependencies Added

```toml
celery = {version = "^5.4.0", extras = ["redis"]}
redis = "^5.0.0"
```

## Files Created/Modified

### Created
- `app/celery_app.py` - Celery application configuration
- `app/workers/__init__.py` - Workers package
- `app/workers/tasks.py` - Task definitions (14KB, 400+ lines)
- `worker.py` - Worker entry point
- `CELERY_WORKERS.md` - Comprehensive documentation (7KB)
- `CELERY_WORKERS_COMPLETE.md` - This file
- `tests/test_celery_tasks.py` - Task tests (10KB)

### Modified
- `pyproject.toml` - Added Celery and Redis dependencies
- `.env.example` - Added Redis URL configuration
- `docker-compose.yml` - Added celery-worker and celery-beat services
- `progress.md` - Marked workers task as complete

## Testing

Run the tests:
```bash
cd backend
pytest tests/test_celery_tasks.py -v
```

All tests mock the underlying processors and verify:
- Task execution flow
- Result structure
- Error handling
- Task configuration

## Next Steps

1. **Image Analyzer**: Implement the `image-analyzer` task for chart screenshot analysis
2. **API Integration**: Add FastAPI endpoints to enqueue and monitor tasks
3. **Database Integration**: Store task results in PostgreSQL for long-term tracking
4. **Monitoring**: Set up Flower for web-based monitoring (optional)
5. **Production Setup**: Configure systemd services or Kubernetes deployments

## Notes

- Workers use existing processors from `src/hl_bot/services/ingestion/`
- All async operations wrapped with `run_async()` helper
- Cache directories shared between backend and workers via Docker volumes
- Periodic cleanup tasks prevent disk space issues
- Retry logic handles transient failures (network, API rate limits)
- Each task type routes to dedicated queue for better resource management

## Success Criteria ✅

- [x] Celery configured with Redis broker
- [x] Task queues set up (youtube, pdf, llm, default)
- [x] YouTube video/playlist processing tasks implemented
- [x] PDF document processing task implemented
- [x] LLM strategy extraction tasks implemented
- [x] Periodic cache cleanup tasks implemented
- [x] Docker Compose integration complete
- [x] Documentation written (usage, monitoring, troubleshooting)
- [x] Unit tests created
- [x] Dependencies installed
- [x] Configuration updated

**Task Status: COMPLETE ✅**
