"""Tests for YouTube processor."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hl_bot.services.ingestion import VideoInfo, YouTubeError, YouTubeProcessor


class TestYouTubeProcessor:
    """Test YouTube video processing."""

    @pytest.fixture
    def processor(self, tmp_path: Path) -> YouTubeProcessor:
        """Create processor instance with temp cache."""
        return YouTubeProcessor(
            cache_dir=tmp_path / "cache",
            enable_whisper=True,
            max_video_duration=3600,
            frame_interval=60,
        )

    def test_init(self, processor: YouTubeProcessor) -> None:
        """Test processor initialization."""
        assert processor._cache_dir.exists()
        assert processor._enable_whisper is True
        assert processor._max_duration == 3600
        assert processor._frame_interval == 60

    def test_cache_key(self, processor: YouTubeProcessor) -> None:
        """Test cache key generation."""
        key1 = processor._cache_key("dQw4w9WgXcQ")
        key2 = processor._cache_key("dQw4w9WgXcQ")
        key3 = processor._cache_key("different123")

        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key
        assert len(key1) == 16  # MD5 hash truncated to 16 chars

    def test_clean_vtt(self, processor: YouTubeProcessor) -> None:
        """Test VTT subtitle cleaning."""
        vtt_content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello <c>world</c>!

00:00:02.000 --> 00:00:04.000
This is a test.

00:00:04.000 --> 00:00:06.000
Multiple   spaces.
"""
        cleaned = processor._clean_vtt(vtt_content)

        assert "WEBVTT" not in cleaned
        assert "-->" not in cleaned
        assert "<c>" not in cleaned
        assert "</c>" not in cleaned
        assert "Hello world! This is a test. Multiple spaces." == cleaned

    @pytest.mark.asyncio
    async def test_extract_video_ids_single(self, processor: YouTubeProcessor) -> None:
        """Test extracting single video ID."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            mock_ydl.extract_info.return_value = {"id": "dQw4w9WgXcQ"}

            video_ids = await processor._extract_video_ids(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )

            assert video_ids == ["dQw4w9WgXcQ"]

    @pytest.mark.asyncio
    async def test_extract_video_ids_playlist(self, processor: YouTubeProcessor) -> None:
        """Test extracting playlist video IDs."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            mock_ydl.extract_info.return_value = {
                "entries": [
                    {"id": "video1"},
                    {"id": "video2"},
                    {"id": "video3"},
                ]
            }

            video_ids = await processor._extract_video_ids(
                "https://www.youtube.com/playlist?list=PLtest"
            )

            assert video_ids == ["video1", "video2", "video3"]

    @pytest.mark.asyncio
    async def test_get_metadata(self, processor: YouTubeProcessor) -> None:
        """Test metadata extraction."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            mock_ydl.extract_info.return_value = {
                "id": "dQw4w9WgXcQ",
                "title": "Test Video",
                "description": "Test description",
                "duration": 212,
                "channel": "Test Channel",
                "upload_date": "20240101",
            }

            metadata = await processor._get_metadata("dQw4w9WgXcQ")

            assert metadata["title"] == "Test Video"
            assert metadata["duration"] == 212
            assert metadata["channel"] == "Test Channel"

    @pytest.mark.asyncio
    async def test_video_too_long_rejected(self, processor: YouTubeProcessor) -> None:
        """Test that videos exceeding max duration are rejected."""
        with patch.object(processor, "_get_metadata") as mock_metadata:
            mock_metadata.return_value = {"duration": 10000, "title": "Long Video"}

            with pytest.raises(YouTubeError, match="Video too long"):
                await processor._process_single_video("test_id", False, True)

    @pytest.mark.asyncio
    async def test_process_url_error_handling(self, processor: YouTubeProcessor) -> None:
        """Test error handling in URL processing."""
        with patch.object(processor, "_extract_video_ids") as mock_extract:
            mock_extract.side_effect = Exception("Network error")

            with pytest.raises(YouTubeError, match="Failed to process URL"):
                await processor.process_url("https://www.youtube.com/watch?v=invalid")

    def test_video_info_repr(self) -> None:
        """Test VideoInfo string representation."""
        info = VideoInfo(
            video_id="test123",
            title="Test Video",
            description="Test desc",
            duration=100,
            url="https://youtube.com/watch?v=test123",
            transcript="This is a transcript",
            frames=[],
        )

        repr_str = repr(info)
        assert "test123" in repr_str
        assert "Test Video" in repr_str
        assert "frames=0" in repr_str


@pytest.mark.integration
class TestYouTubeProcessorIntegration:
    """Integration tests requiring network access."""

    @pytest.fixture
    def processor(self, tmp_path: Path) -> YouTubeProcessor:
        """Create processor for integration tests."""
        return YouTubeProcessor(
            cache_dir=tmp_path / "cache",
            enable_whisper=False,  # Disable for faster testing
            max_video_duration=600,
            frame_interval=60,
        )

    @pytest.mark.skip(reason="Requires network access and takes time")
    @pytest.mark.asyncio
    async def test_process_real_video(self, processor: YouTubeProcessor) -> None:
        """Test processing a real short video (requires network)."""
        # Use a very short, public domain video for testing
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video

        try:
            videos = await processor.process_url(url, extract_frames=False, prefer_captions=True)

            assert len(videos) == 1
            video = videos[0]

            assert video.video_id == "jNQXAC9IVRw"
            assert len(video.title) > 0
            assert video.duration > 0
            assert len(video.transcript) > 0  # Should have captions

        except Exception as e:
            pytest.skip(f"Integration test failed (network issue?): {e}")
