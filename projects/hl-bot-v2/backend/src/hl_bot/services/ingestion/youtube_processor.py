"""YouTube video processor for extracting trading knowledge from videos.

Downloads videos, extracts transcripts (captions or Whisper transcription),
and extracts video frames for image analysis.
"""

import asyncio
import hashlib
import logging
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import aiofiles
import yt_dlp
from PIL import Image

logger = logging.getLogger(__name__)


class YouTubeError(Exception):
    """Base exception for YouTube processing errors."""

    pass


class VideoInfo:
    """Video metadata and content."""

    def __init__(
        self,
        video_id: str,
        title: str,
        description: str,
        duration: int,
        url: str,
        transcript: str,
        frames: list[Path],
        channel: str = "",
        upload_date: str = "",
    ):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.duration = duration
        self.url = url
        self.transcript = transcript
        self.frames = frames
        self.channel = channel
        self.upload_date = upload_date

    def __repr__(self) -> str:
        return (
            f"VideoInfo(video_id='{self.video_id}', title='{self.title}', "
            f"frames={len(self.frames)})"
        )


class YouTubeProcessor:
    """Process YouTube videos to extract educational content."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        enable_whisper: bool = True,
        max_video_duration: int = 7200,  # 2 hours
        frame_interval: int = 30,  # Extract frame every N seconds
    ):
        """Initialize YouTube processor.

        Args:
            cache_dir: Directory for caching downloaded videos (uses temp if None)
            enable_whisper: Whether to use Whisper for transcription fallback
            max_video_duration: Maximum video duration in seconds
            frame_interval: Extract frame every N seconds
        """
        self._cache_dir = cache_dir or Path(tempfile.gettempdir()) / "hl_bot_youtube"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._enable_whisper = enable_whisper
        self._max_duration = max_video_duration
        self._frame_interval = frame_interval
        logger.info(
            f"YouTube processor initialized: cache={self._cache_dir}, "
            f"whisper={enable_whisper}, max_duration={max_video_duration}s"
        )

    async def process_url(
        self,
        url: str,
        extract_frames: bool = True,
        prefer_captions: bool = True,
    ) -> list[VideoInfo]:
        """Process YouTube URL (single video or playlist).

        Args:
            url: YouTube video or playlist URL
            extract_frames: Whether to extract video frames
            prefer_captions: Prefer existing captions over Whisper transcription

        Returns:
            List of VideoInfo objects (single video or multiple from playlist)

        Raises:
            YouTubeError: If processing fails
        """
        logger.info(f"Processing YouTube URL: {url}")

        try:
            # Check if it's a playlist
            video_ids = await self._extract_video_ids(url)
            logger.info(f"Found {len(video_ids)} video(s) to process")

            videos = []
            for i, video_id in enumerate(video_ids):
                try:
                    logger.info(f"Processing video {i+1}/{len(video_ids)}: {video_id}")
                    video_info = await self._process_single_video(
                        video_id, extract_frames, prefer_captions
                    )
                    videos.append(video_info)
                except Exception as e:
                    logger.error(f"Failed to process video {video_id}: {e}")
                    # Continue with remaining videos
                    continue

            if not videos:
                raise YouTubeError("No videos were successfully processed")

            return videos

        except Exception as e:
            logger.error(f"YouTube processing failed: {e}")
            raise YouTubeError(f"Failed to process URL: {e}")

    async def _extract_video_ids(self, url: str) -> list[str]:
        """Extract video IDs from URL (handles playlists).

        Args:
            url: YouTube URL

        Returns:
            List of video IDs

        Raises:
            YouTubeError: If URL is invalid
        """
        # Run yt-dlp in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def _extract() -> list[str]:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)

                    # Handle playlist
                    if "entries" in info:
                        return [entry["id"] for entry in info["entries"] if entry.get("id")]
                    # Handle single video
                    elif "id" in info:
                        return [info["id"]]
                    else:
                        raise YouTubeError("Could not extract video ID from URL")

                except Exception as e:
                    raise YouTubeError(f"Invalid YouTube URL: {e}")

        return await loop.run_in_executor(None, _extract)

    async def _process_single_video(
        self,
        video_id: str,
        extract_frames: bool,
        prefer_captions: bool,
    ) -> VideoInfo:
        """Process a single video.

        Args:
            video_id: YouTube video ID
            extract_frames: Whether to extract frames
            prefer_captions: Prefer captions over Whisper

        Returns:
            VideoInfo object

        Raises:
            YouTubeError: If processing fails
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        cache_key = self._cache_key(video_id)
        work_dir = self._cache_dir / cache_key
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Get video metadata
            metadata = await self._get_metadata(video_id)

            # Check duration
            duration = metadata.get("duration", 0)
            if duration > self._max_duration:
                raise YouTubeError(
                    f"Video too long: {duration}s (max {self._max_duration}s)"
                )

            # Get transcript
            transcript = await self._get_transcript(
                video_id, work_dir, prefer_captions
            )

            # Extract frames
            frames: list[Path] = []
            if extract_frames:
                frames = await self._extract_frames(video_id, work_dir, duration)

            return VideoInfo(
                video_id=video_id,
                title=metadata.get("title", "Unknown"),
                description=metadata.get("description", ""),
                duration=duration,
                url=video_url,
                transcript=transcript,
                frames=frames,
                channel=metadata.get("channel", ""),
                upload_date=metadata.get("upload_date", ""),
            )

        except Exception as e:
            logger.error(f"Failed to process video {video_id}: {e}")
            # Clean up work directory on failure
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
            raise YouTubeError(f"Video processing failed: {e}")

    async def _get_metadata(self, video_id: str) -> dict[str, Any]:
        """Get video metadata without downloading.

        Args:
            video_id: YouTube video ID

        Returns:
            Metadata dictionary
        """
        loop = asyncio.get_event_loop()

        def _fetch() -> dict[str, Any]:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=False,
                )

        return await loop.run_in_executor(None, _fetch)

    async def _get_transcript(
        self,
        video_id: str,
        work_dir: Path,
        prefer_captions: bool,
    ) -> str:
        """Get video transcript (captions or Whisper transcription).

        Args:
            video_id: YouTube video ID
            work_dir: Working directory
            prefer_captions: Try captions first

        Returns:
            Transcript text

        Raises:
            YouTubeError: If transcription fails
        """
        # Try to get captions first if preferred
        if prefer_captions:
            try:
                transcript = await self._download_captions(video_id, work_dir)
                if transcript:
                    logger.info(f"Retrieved captions for {video_id}")
                    return transcript
            except Exception as e:
                logger.warning(f"Caption download failed, will try Whisper: {e}")

        # Fall back to Whisper transcription
        if self._enable_whisper:
            try:
                transcript = await self._transcribe_with_whisper(video_id, work_dir)
                logger.info(f"Transcribed with Whisper: {video_id}")
                return transcript
            except Exception as e:
                raise YouTubeError(f"Whisper transcription failed: {e}")
        else:
            raise YouTubeError("No transcript available and Whisper is disabled")

    async def _download_captions(self, video_id: str, work_dir: Path) -> str:
        """Download YouTube captions/subtitles.

        Args:
            video_id: YouTube video ID
            work_dir: Working directory

        Returns:
            Caption text
        """
        loop = asyncio.get_event_loop()
        subtitle_file = work_dir / f"{video_id}.en.vtt"

        def _download() -> None:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "subtitlesformat": "vtt",
                "outtmpl": str(work_dir / video_id),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        await loop.run_in_executor(None, _download)

        # Read and clean VTT file
        if subtitle_file.exists():
            async with aiofiles.open(subtitle_file, "r", encoding="utf-8") as f:
                content = await f.read()
                # Clean VTT formatting
                transcript = self._clean_vtt(content)
                return transcript

        raise YouTubeError("No captions found")

    async def _transcribe_with_whisper(self, video_id: str, work_dir: Path) -> str:
        """Transcribe video using faster-whisper.

        Args:
            video_id: YouTube video ID
            work_dir: Working directory

        Returns:
            Transcription text
        """
        audio_file = work_dir / f"{video_id}.mp3"

        # Download audio
        await self._download_audio(video_id, audio_file)

        # Transcribe with faster-whisper
        loop = asyncio.get_event_loop()

        def _transcribe() -> str:
            from faster_whisper import WhisperModel

            # Use base model on CPU for compatibility
            model = WhisperModel("base", device="cpu", compute_type="int8")
            
            segments, _ = model.transcribe(str(audio_file), language="en")
            
            # Collect all segments
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
            
            return " ".join(transcript_parts)

        transcript = await loop.run_in_executor(None, _transcribe)

        # Clean up audio file
        audio_file.unlink(missing_ok=True)

        return transcript

    async def _download_audio(self, video_id: str, output_path: Path) -> None:
        """Download audio from video.

        Args:
            video_id: YouTube video ID
            output_path: Where to save audio
        """
        loop = asyncio.get_event_loop()

        def _download() -> None:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": str(output_path.with_suffix("")),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        await loop.run_in_executor(None, _download)

        if not output_path.exists():
            raise YouTubeError(f"Audio download failed: {output_path} not found")

    async def _extract_frames(
        self, video_id: str, work_dir: Path, duration: int
    ) -> list[Path]:
        """Extract frames from video at regular intervals.

        Args:
            video_id: YouTube video ID
            work_dir: Working directory
            duration: Video duration in seconds

        Returns:
            List of frame file paths
        """
        video_file = work_dir / f"{video_id}.mp4"
        frames_dir = work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

        # Download video
        await self._download_video(video_id, video_file)

        # Extract frames using ffmpeg
        num_frames = max(1, duration // self._frame_interval)
        logger.info(f"Extracting ~{num_frames} frames from video")

        loop = asyncio.get_event_loop()

        def _extract() -> list[Path]:
            frame_paths: list[Path] = []

            # Extract frames at intervals
            for i in range(num_frames):
                timestamp = i * self._frame_interval
                if timestamp >= duration:
                    break

                frame_path = frames_dir / f"frame_{i:04d}.jpg"

                # Use ffmpeg to extract frame
                cmd = [
                    "ffmpeg",
                    "-ss", str(timestamp),
                    "-i", str(video_file),
                    "-vframes", "1",
                    "-q:v", "2",  # High quality
                    "-y",  # Overwrite
                    str(frame_path),
                ]

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )

                    if result.returncode == 0 and frame_path.exists():
                        frame_paths.append(frame_path)
                    else:
                        logger.warning(
                            f"Frame extraction failed at {timestamp}s: "
                            f"{result.stderr.decode()}"
                        )

                except subprocess.TimeoutExpired:
                    logger.warning(f"Frame extraction timeout at {timestamp}s")
                except Exception as e:
                    logger.warning(f"Frame extraction error at {timestamp}s: {e}")

            return frame_paths

        frames = await loop.run_in_executor(None, _extract)

        # Clean up video file
        video_file.unlink(missing_ok=True)

        logger.info(f"Extracted {len(frames)} frames")
        return frames

    async def _download_video(self, video_id: str, output_path: Path) -> None:
        """Download video file.

        Args:
            video_id: YouTube video ID
            output_path: Where to save video
        """
        loop = asyncio.get_event_loop()

        def _download() -> None:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "merge_output_format": "mp4",
                "outtmpl": str(output_path.with_suffix("")),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        await loop.run_in_executor(None, _download)

        if not output_path.exists():
            raise YouTubeError(f"Video download failed: {output_path} not found")

    def _clean_vtt(self, vtt_content: str) -> str:
        """Clean VTT subtitle content.

        Args:
            vtt_content: Raw VTT file content

        Returns:
            Clean transcript text
        """
        lines = vtt_content.split("\n")
        transcript_lines = []

        for line in lines:
            # Skip VTT headers, timestamps, and empty lines
            line = line.strip()
            if not line or line.startswith("WEBVTT") or "-->" in line:
                continue
            # Skip lines that are just numbers (sequence markers)
            if line.isdigit():
                continue

            # Remove formatting tags
            line = re.sub(r"<[^>]+>", "", line)

            transcript_lines.append(line)

        # Join and clean up whitespace
        transcript = " ".join(transcript_lines)
        transcript = re.sub(r"\s+", " ", transcript)

        return transcript.strip()

    def _cache_key(self, video_id: str) -> str:
        """Generate cache key from video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            Cache key (hash)
        """
        return hashlib.md5(video_id.encode()).hexdigest()[:16]

    async def cleanup_cache(self, max_age_days: int = 7) -> int:
        """Clean up old cached files.

        Args:
            max_age_days: Remove files older than this many days

        Returns:
            Number of directories removed
        """
        count = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)

        for item in self._cache_dir.iterdir():
            if item.is_dir():
                if item.stat().st_mtime < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    count += 1

        logger.info(f"Cleaned up {count} old cache directories")
        return count

    async def process_local_video(
        self,
        video_path: Path,
        title: str = "",
        frame_interval: int | None = None,
    ) -> VideoInfo:
        """Process a local video file (bypass YouTube download).

        Args:
            video_path: Path to local video file (.mp4, .mkv, .webm, etc.)
            title: Optional title for the video
            frame_interval: Override default frame interval (seconds)

        Returns:
            VideoInfo with extracted frames
        """
        if not video_path.exists():
            raise YouTubeError(f"Video file not found: {video_path}")

        interval = frame_interval or self._frame_interval
        video_id = video_path.stem  # Use filename as ID

        # Get video duration using ffprobe
        duration = await self._get_video_duration(video_path)
        logger.info(f"Processing local video: {video_path.name} ({duration}s)")

        # Create work directory
        work_dir = self._cache_dir / f"local_{video_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        frames_dir = work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

        # Extract frames using ffmpeg
        frames = await self._extract_frames_from_file(
            video_path, frames_dir, duration, interval
        )

        return VideoInfo(
            video_id=video_id,
            title=title or video_path.stem,
            description="Local video file",
            duration=duration,
            url=str(video_path),
            transcript="",  # No transcript for local files
            frames=frames,
            channel="local",
            upload_date=datetime.now().strftime("%Y%m%d"),
        )

    async def process_local_videos(
        self,
        video_dir: Path,
        frame_interval: int | None = None,
    ) -> list[VideoInfo]:
        """Process all video files in a directory.

        Args:
            video_dir: Directory containing video files
            frame_interval: Override default frame interval (seconds)

        Returns:
            List of VideoInfo objects
        """
        video_extensions = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
        videos = []

        for video_file in sorted(video_dir.iterdir()):
            if video_file.suffix.lower() in video_extensions:
                try:
                    info = await self.process_local_video(
                        video_file, frame_interval=frame_interval
                    )
                    videos.append(info)
                    logger.info(f"Processed {video_file.name}: {len(info.frames)} frames")
                except Exception as e:
                    logger.error(f"Failed to process {video_file.name}: {e}")

        return videos

    async def _get_video_duration(self, video_path: Path) -> int:
        """Get video duration in seconds using ffprobe."""
        loop = asyncio.get_event_loop()

        def _probe() -> int:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return int(float(result.stdout.strip()))
            return 0

        return await loop.run_in_executor(None, _probe)

    async def _extract_frames_from_file(
        self,
        video_path: Path,
        frames_dir: Path,
        duration: int,
        interval: int,
    ) -> list[Path]:
        """Extract frames from a video file at regular intervals.

        Uses a single ffmpeg command for efficiency.
        """
        loop = asyncio.get_event_loop()
        num_frames = max(1, duration // interval)
        logger.info(f"Extracting ~{num_frames} frames (every {interval}s)")

        def _extract() -> list[Path]:
            # Use fps filter for efficient extraction
            fps_value = 1.0 / interval
            output_pattern = str(frames_dir / "frame_%04d.jpg")

            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-vf", f"fps={fps_value}",
                "-q:v", "2",  # High quality JPEG
                "-y",  # Overwrite
                output_pattern,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=duration + 60,  # Allow time for processing
            )

            if result.returncode != 0:
                logger.warning(f"ffmpeg warning: {result.stderr.decode()[-500:]}")

            # Collect extracted frames
            frames = sorted(frames_dir.glob("frame_*.jpg"))
            return frames

        return await loop.run_in_executor(None, _extract)
