# Celery Workers for Background Processing

This document explains the Celery worker setup for processing YouTube videos, PDF documents, and LLM-based strategy extraction as background tasks.

## Architecture

The worker system consists of:

1. **Celery Worker** - Processes tasks from Redis queues
2. **Celery Beat** - Schedules periodic tasks (cache cleanup)
3. **Redis** - Message broker and result backend
4. **Task Queues**:
   - `default` - General tasks
   - `youtube` - YouTube video processing
   - `pdf` - PDF document processing
   - `llm` - LLM-based analysis and extraction

## Available Tasks

### YouTube Processing

#### `process_youtube_video`
Process a single YouTube video: download, extract transcript, and frames.

```python
from app.workers.tasks import process_youtube_video

# Enqueue task
result = process_youtube_video.delay(
    url="https://www.youtube.com/watch?v=VIDEO_ID",
    extract_frames=True,
    prefer_captions=True
)

# Get result (blocking)
video_info = result.get(timeout=600)  # 10 minutes
```

#### `process_youtube_playlist`
Process an entire YouTube playlist.

```python
from app.workers.tasks import process_youtube_playlist

result = process_youtube_playlist.delay(
    url="https://www.youtube.com/playlist?list=PLAYLIST_ID",
    extract_frames=True,
    prefer_captions=True
)

videos = result.get(timeout=3600)  # 1 hour
```

### PDF Processing

#### `process_pdf_document`
Extract text, images, and apply OCR to PDF documents.

```python
from app.workers.tasks import process_pdf_document

result = process_pdf_document.delay(
    pdf_path="/path/to/document.pdf",
    extract_images=True
)

pdf_info = result.get(timeout=600)
```

### LLM Strategy Extraction

#### `extract_trading_strategy`
Extract trading strategy from text content using LLM.

```python
from app.workers.tasks import extract_trading_strategy

result = extract_trading_strategy.delay(
    content="Long text content about trading strategies...",
    content_type="transcript",
    model="claude-sonnet-4"
)

strategy = result.get(timeout=300)
```

#### `analyze_chart_image`
Analyze chart images using LLM vision capabilities.

```python
from app.workers.tasks import analyze_chart_image

result = analyze_chart_image.delay(
    image_path="/path/to/chart.png",
    model="claude-sonnet-4"
)

analysis = result.get(timeout=300)
```

### Periodic Tasks

These tasks run automatically via Celery Beat:

- `cleanup_youtube_cache` - Cleans up YouTube cache daily
- `cleanup_pdf_cache` - Cleans up PDF cache daily

## Running Workers

### Development (Local)

1. **Start Redis** (if not running):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Start Celery Worker**:
   ```bash
   cd backend
   celery -A app.celery_app worker --loglevel=info --concurrency=2
   ```

3. **Start Celery Beat** (for periodic tasks):
   ```bash
   celery -A app.celery_app beat --loglevel=info
   ```

### Development (Docker Compose)

```bash
# Start all services including workers
docker-compose up -d

# View worker logs
docker-compose logs -f celery-worker

# View beat scheduler logs
docker-compose logs -f celery-beat
```

### Production

For production, use systemd services or dedicated Docker containers with proper resource limits.

Example systemd service (`/etc/systemd/system/hlbot-worker.service`):

```ini
[Unit]
Description=HL Bot Celery Worker
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=hlbot
Group=hlbot
WorkingDirectory=/opt/hlbot/backend
Environment="PATH=/opt/hlbot/venv/bin"
ExecStart=/opt/hlbot/venv/bin/celery -A app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=100
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

## Configuration

Workers are configured in `app/celery_app.py`:

- **Task time limits**: 30 minutes soft, 40 minutes hard
- **Concurrency**: Default 2 workers (configurable)
- **Retry policy**: 3 retries with exponential backoff
- **Result expiration**: 1 hour

### Environment Variables

Required environment variables:

```bash
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:password@localhost:5432/hlbot
ANTHROPIC_API_KEY=your-api-key-here
```

## Monitoring

### Task Status

```python
from app.celery_app import celery_app

# Check task status
result = celery_app.AsyncResult(task_id)
print(f"Status: {result.state}")
print(f"Result: {result.result}")
```

### Worker Stats

```bash
# View active workers
celery -A app.celery_app inspect active

# View registered tasks
celery -A app.celery_app inspect registered

# View stats
celery -A app.celery_app inspect stats

# View scheduled tasks (beat)
celery -A app.celery_app inspect scheduled
```

### Flower (Web UI)

Install Flower for a web-based monitoring interface:

```bash
pip install flower
flower -A app.celery_app --port=5555
```

Then visit http://localhost:5555

## Queue Management

### Purge Queue

```bash
# Purge all tasks from a specific queue
celery -A app.celery_app purge -Q youtube

# Purge all queues
celery -A app.celery_app purge
```

### Control Workers

```bash
# Stop workers gracefully
celery -A app.celery_app control shutdown

# Cancel task
celery -A app.celery_app control revoke <task_id>

# Set concurrency
celery -A app.celery_app control pool_grow 4
celery -A app.celery_app control pool_shrink 2
```

## Error Handling

Tasks implement automatic retry with exponential backoff:

- **Max retries**: 3
- **Retry delay**: 60s * (2 ^ retry_count)
- **Exceptions**: YouTubeError, PDFError, general Exception

Failed tasks are logged and can be inspected in the result backend.

## Performance Tips

1. **Concurrency**: Adjust based on CPU cores and task I/O ratio
   ```bash
   celery -A app.celery_app worker --concurrency=4
   ```

2. **Resource Limits**: Set task time limits to prevent hung tasks

3. **Prefetch**: Set `worker_prefetch_multiplier=1` for long-running tasks

4. **Queue Routing**: Use separate queues for different task types

5. **Cache Cleanup**: Periodic cleanup prevents disk space issues

## Testing

Test tasks in development:

```python
# test_celery.py
from app.workers.tasks import process_youtube_video

def test_youtube_processing():
    result = process_youtube_video.apply_async(
        args=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        kwargs={"extract_frames": False}
    )
    
    # Wait for result
    video_info = result.get(timeout=300)
    assert video_info["video_id"] == "dQw4w9WgXcQ"
    assert len(video_info["transcript"]) > 0
```

## Troubleshooting

### Worker not starting
- Check Redis connection: `redis-cli ping`
- Check environment variables
- Check logs: `celery -A app.celery_app worker --loglevel=debug`

### Tasks not processing
- Check worker is running: `celery -A app.celery_app inspect active_queues`
- Check task is in correct queue
- Check worker logs for errors

### Memory issues
- Reduce concurrency
- Enable `worker_max_tasks_per_child`
- Monitor with `celery -A app.celery_app inspect stats`

### Slow processing
- Check network connectivity (YouTube downloads)
- Monitor task execution time
- Consider adding more workers

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [YouTube Processor](../src/hl_bot/services/ingestion/youtube_processor.py)
- [PDF Processor](../src/hl_bot/services/ingestion/pdf_processor.py)
