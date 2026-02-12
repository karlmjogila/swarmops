# Content Ingestion Services

This module provides content ingestion capabilities for extracting trading knowledge from various sources.

## YouTube Processor

The `YouTubeProcessor` downloads and processes YouTube videos to extract educational content about trading strategies.

### Features

- ✅ Single video and playlist support
- ✅ Automatic caption/subtitle extraction
- ✅ Fallback to Whisper transcription (faster-whisper)
- ✅ Video frame extraction at configurable intervals
- ✅ Caching to avoid re-downloading
- ✅ Duration limits to prevent processing very long videos
- ✅ Async/await support for non-blocking operations
- ✅ Comprehensive error handling

### Usage

```python
from pathlib import Path
from hl_bot.services.ingestion import YouTubeProcessor

# Initialize processor
processor = YouTubeProcessor(
    cache_dir=Path("./data/youtube_cache"),
    enable_whisper=True,        # Enable Whisper transcription fallback
    max_video_duration=7200,    # 2 hours max
    frame_interval=30,          # Extract frame every 30 seconds
)

# Process a video
videos = await processor.process_url(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    extract_frames=True,        # Extract video frames
    prefer_captions=True,       # Try captions first (faster)
)

# Access video info
for video in videos:
    print(f"Title: {video.title}")
    print(f"Duration: {video.duration}s")
    print(f"Transcript: {len(video.transcript)} chars")
    print(f"Frames: {len(video.frames)} extracted")
```

### VideoInfo Object

The processor returns `VideoInfo` objects with the following attributes:

- `video_id` (str): YouTube video ID
- `title` (str): Video title
- `description` (str): Video description
- `duration` (int): Duration in seconds
- `url` (str): Full video URL
- `transcript` (str): Full transcript text
- `frames` (list[Path]): Paths to extracted frame images
- `channel` (str): Channel name
- `upload_date` (str): Upload date

### Dependencies

Required system dependencies:
- **ffmpeg**: For frame extraction (install via `apt install ffmpeg` or `brew install ffmpeg`)

Python dependencies (automatically installed):
- `yt-dlp`: YouTube download
- `faster-whisper`: Speech-to-text transcription
- `pillow`: Image processing
- `aiofiles`: Async file operations

### Error Handling

The processor raises `YouTubeError` exceptions for:
- Invalid URLs
- Videos exceeding max duration
- Network failures
- Transcription failures (when Whisper is disabled and no captions exist)

### Cache Management

Clean up old cached files periodically:

```python
# Remove cache files older than 7 days
removed_count = await processor.cleanup_cache(max_age_days=7)
print(f"Cleaned up {removed_count} old cache directories")
```

### Performance Notes

- **Captions vs Whisper**: Captions are much faster (seconds vs minutes). Always prefer captions when available.
- **Frame extraction**: Extracting frames requires downloading the full video. Set `extract_frames=False` if not needed.
- **Concurrent processing**: Use `asyncio.gather()` to process multiple videos in parallel.
- **Cache hits**: Repeated processing of the same video will be faster due to caching.

### Examples

See `examples/youtube_ingestion_example.py` for a complete example of using the processor with the strategy extractor.

### Testing

Run tests with:

```bash
poetry run pytest tests/unit/test_youtube_processor.py -v
```

Integration tests (requiring network access) are skipped by default. To run them:

```bash
poetry run pytest tests/unit/test_youtube_processor.py -v -m integration
```
