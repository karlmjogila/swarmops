"""Tests for Celery background tasks.

Tests the task definitions and basic functionality without actually
executing the long-running operations.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Import tasks
from app.workers.tasks import (
    process_youtube_video,
    process_youtube_playlist,
    process_pdf_document,
    extract_trading_strategy,
    analyze_chart_image,
    cleanup_youtube_cache,
    cleanup_pdf_cache,
)


class TestYouTubeTasks:
    """Tests for YouTube processing tasks."""

    @patch("app.workers.tasks.YouTubeProcessor")
    @patch("app.workers.tasks.run_async")
    def test_process_youtube_video_success(self, mock_run_async, mock_processor):
        """Test successful YouTube video processing."""
        # Mock VideoInfo
        mock_video = Mock()
        mock_video.video_id = "test_id"
        mock_video.title = "Test Video"
        mock_video.description = "Test description"
        mock_video.duration = 600
        mock_video.url = "https://youtube.com/watch?v=test_id"
        mock_video.transcript = "Test transcript"
        mock_video.channel = "Test Channel"
        mock_video.upload_date = "2024-01-01"
        mock_video.frames = [Path("/tmp/frame1.jpg")]

        # Mock processor instance and process_url
        mock_instance = Mock()
        mock_instance.process_url = AsyncMock(return_value=[mock_video])
        mock_processor.return_value = mock_instance
        mock_run_async.return_value = [mock_video]

        # Execute task
        result = process_youtube_video(
            url="https://youtube.com/watch?v=test_id",
            extract_frames=True,
            prefer_captions=True,
        )

        # Verify result
        assert result["video_id"] == "test_id"
        assert result["title"] == "Test Video"
        assert result["transcript"] == "Test transcript"
        assert result["num_frames"] == 1

    @patch("app.workers.tasks.YouTubeProcessor")
    @patch("app.workers.tasks.run_async")
    def test_process_youtube_playlist_success(self, mock_run_async, mock_processor):
        """Test successful YouTube playlist processing."""
        # Mock two videos
        mock_video1 = Mock()
        mock_video1.video_id = "video1"
        mock_video1.title = "Video 1"
        mock_video1.description = "Description 1"
        mock_video1.duration = 300
        mock_video1.url = "https://youtube.com/watch?v=video1"
        mock_video1.transcript = "Transcript 1"
        mock_video1.channel = "Channel"
        mock_video1.upload_date = "2024-01-01"
        mock_video1.frames = []

        mock_video2 = Mock()
        mock_video2.video_id = "video2"
        mock_video2.title = "Video 2"
        mock_video2.description = "Description 2"
        mock_video2.duration = 400
        mock_video2.url = "https://youtube.com/watch?v=video2"
        mock_video2.transcript = "Transcript 2"
        mock_video2.channel = "Channel"
        mock_video2.upload_date = "2024-01-02"
        mock_video2.frames = []

        mock_instance = Mock()
        mock_instance.process_url = AsyncMock(return_value=[mock_video1, mock_video2])
        mock_processor.return_value = mock_instance
        mock_run_async.return_value = [mock_video1, mock_video2]

        # Execute task
        result = process_youtube_playlist(
            url="https://youtube.com/playlist?list=test_playlist"
        )

        # Verify result
        assert len(result) == 2
        assert result[0]["video_id"] == "video1"
        assert result[1]["video_id"] == "video2"


class TestPDFTasks:
    """Tests for PDF processing tasks."""

    @patch("app.workers.tasks.PDFProcessor")
    @patch("app.workers.tasks.run_async")
    def test_process_pdf_document_success(self, mock_run_async, mock_processor):
        """Test successful PDF processing."""
        # Mock PDFInfo
        mock_pdf = Mock()
        mock_pdf.filename = "test.pdf"
        mock_pdf.title = "Test PDF"
        mock_pdf.author = "Test Author"
        mock_pdf.num_pages = 10
        mock_pdf.get_full_text.return_value = "Full text content"
        mock_pdf.get_all_images.return_value = [Path("/tmp/img1.jpg")]
        mock_pdf.metadata = {"creator": "Test"}

        # Mock page content
        mock_page = Mock()
        mock_page.page_num = 1
        mock_page.text = "Page text"
        mock_page.ocr_text = ""
        mock_page.images = []
        mock_page.has_text = True

        mock_pdf.pages = [mock_page]

        mock_instance = Mock()
        mock_instance.process_file = AsyncMock(return_value=mock_pdf)
        mock_processor.return_value = mock_instance
        mock_run_async.return_value = mock_pdf

        # Create temp PDF file for test
        test_pdf = Path("/tmp/test.pdf")
        test_pdf.touch()

        try:
            # Execute task
            result = process_pdf_document(
                pdf_path=str(test_pdf),
                extract_images=True,
            )

            # Verify result
            assert result["filename"] == "test.pdf"
            assert result["title"] == "Test PDF"
            assert result["num_pages"] == 10
            assert result["text_length"] == len("Full text content")
        finally:
            # Cleanup
            if test_pdf.exists():
                test_pdf.unlink()


class TestLLMTasks:
    """Tests for LLM-based tasks."""

    @patch("app.workers.tasks.StrategyExtractor")
    @patch("app.workers.tasks.LLMClient")
    @patch("app.workers.tasks.run_async")
    @patch("app.config.settings")
    def test_extract_trading_strategy_success(
        self, mock_settings, mock_run_async, mock_llm_client, mock_extractor
    ):
        """Test successful strategy extraction."""
        mock_settings.anthropic_api_key = "test-key"

        # Mock strategy extraction
        mock_strategy = {
            "entry": "Buy on breakout",
            "exit": "Sell on support",
            "risk": "2% per trade",
        }

        mock_extractor_instance = Mock()
        mock_extractor_instance.extract_from_text = AsyncMock(return_value=mock_strategy)
        mock_extractor.return_value = mock_extractor_instance
        mock_run_async.return_value = mock_strategy

        # Execute task
        result = extract_trading_strategy(
            content="Long trading content...",
            content_type="transcript",
            model="claude-sonnet-4",
        )

        # Verify result
        assert result["strategy"] == mock_strategy
        assert result["content_type"] == "transcript"
        assert result["model"] == "claude-sonnet-4"

    @patch("app.workers.tasks.LLMClient")
    @patch("app.workers.tasks.run_async")
    @patch("app.config.settings")
    def test_analyze_chart_image_success(
        self, mock_settings, mock_run_async, mock_llm_client
    ):
        """Test successful chart image analysis."""
        mock_settings.anthropic_api_key = "test-key"

        # Mock image analysis
        mock_analysis = "Bullish trend with strong support at $50,000"

        mock_client_instance = Mock()
        mock_client_instance.analyze_image = AsyncMock(return_value=mock_analysis)
        mock_llm_client.return_value = mock_client_instance
        mock_run_async.return_value = mock_analysis

        # Create temp image file
        test_image = Path("/tmp/chart.png")
        test_image.touch()

        try:
            # Execute task
            result = analyze_chart_image(
                image_path=str(test_image),
                model="claude-sonnet-4",
            )

            # Verify result
            assert result["analysis"] == mock_analysis
            assert result["model"] == "claude-sonnet-4"
        finally:
            # Cleanup
            if test_image.exists():
                test_image.unlink()


class TestCacheTasks:
    """Tests for cache cleanup tasks."""

    @patch("app.workers.tasks.YouTubeProcessor")
    @patch("app.workers.tasks.run_async")
    def test_cleanup_youtube_cache(self, mock_run_async, mock_processor):
        """Test YouTube cache cleanup."""
        mock_instance = Mock()
        mock_instance.cleanup_cache = AsyncMock(return_value=5)
        mock_processor.return_value = mock_instance
        mock_run_async.return_value = 5

        result = cleanup_youtube_cache(max_age_days=7)

        assert result["removed"] == 5
        assert result["type"] == "youtube"

    @patch("app.workers.tasks.PDFProcessor")
    @patch("app.workers.tasks.run_async")
    def test_cleanup_pdf_cache(self, mock_run_async, mock_processor):
        """Test PDF cache cleanup."""
        mock_instance = Mock()
        mock_instance.cleanup_cache = AsyncMock(return_value=3)
        mock_processor.return_value = mock_instance
        mock_run_async.return_value = 3

        result = cleanup_pdf_cache(max_age_days=7)

        assert result["removed"] == 3
        assert result["type"] == "pdf"


class TestTaskConfiguration:
    """Tests for task configuration."""

    def test_task_names(self):
        """Test that tasks have correct names."""
        assert process_youtube_video.name == "app.workers.tasks.process_youtube_video"
        assert process_youtube_playlist.name == "app.workers.tasks.process_youtube_playlist"
        assert process_pdf_document.name == "app.workers.tasks.process_pdf_document"
        assert extract_trading_strategy.name == "app.workers.tasks.extract_trading_strategy"
        assert analyze_chart_image.name == "app.workers.tasks.analyze_chart_image"

    def test_task_retry_configuration(self):
        """Test that tasks have retry configuration."""
        # YouTube tasks
        assert hasattr(process_youtube_video, "autoretry_for")
        assert hasattr(process_youtube_video, "retry_backoff")

        # PDF tasks
        assert hasattr(process_pdf_document, "autoretry_for")
        assert hasattr(process_pdf_document, "retry_backoff")

        # LLM tasks
        assert hasattr(extract_trading_strategy, "autoretry_for")
        assert hasattr(analyze_chart_image, "autoretry_for")
