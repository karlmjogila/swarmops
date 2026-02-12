"""Tests for PDF processor."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from hl_bot.services.ingestion.pdf_processor import (
    PDFError,
    PDFInfo,
    PDFProcessor,
    PageContent,
)


@pytest.fixture
def pdf_processor():
    """Create a PDF processor instance."""
    return PDFProcessor(enable_ocr=False, max_pages=100)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = Path(f.name)

    # Create a simple PDF with reportlab
    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    # Page 1
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is page 1 with some trading content.")
    c.drawString(100, 710, "Support level at $50,000")
    c.showPage()

    # Page 2
    c.drawString(100, 750, "Page 2: Advanced Strategies")
    c.drawString(100, 730, "Look for LE candles at key levels.")
    c.drawString(100, 710, "Risk management: 2% per trade")
    c.showPage()

    # Page 3
    c.drawString(100, 750, "Page 3: Market Structure")
    c.drawString(100, 730, "Identify BOS and CHoCH patterns")
    c.showPage()

    c.save()

    yield pdf_path

    # Cleanup
    pdf_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_process_file_basic(pdf_processor, sample_pdf):
    """Test basic PDF processing."""
    result = await pdf_processor.process_file(sample_pdf, extract_images=False)

    assert isinstance(result, PDFInfo)
    assert result.num_pages == 3
    assert len(result.pages) == 3
    assert result.filename == sample_pdf.name


@pytest.mark.asyncio
async def test_text_extraction(pdf_processor, sample_pdf):
    """Test text extraction from PDF."""
    result = await pdf_processor.process_file(sample_pdf, extract_images=False)

    # Check first page
    page1 = result.pages[0]
    assert isinstance(page1, PageContent)
    assert page1.page_num == 1
    assert page1.has_text
    assert "Test PDF Document" in page1.text
    assert "trading content" in page1.text.lower()

    # Check second page
    page2 = result.pages[1]
    assert page2.page_num == 2
    assert "LE candles" in page2.text or "le candles" in page2.text.lower()

    # Get full text
    full_text = result.get_full_text()
    assert "Support level" in full_text
    assert "Market Structure" in full_text


@pytest.mark.asyncio
async def test_process_bytes(pdf_processor, sample_pdf):
    """Test processing PDF from bytes."""
    # Read PDF as bytes
    with open(sample_pdf, "rb") as f:
        pdf_bytes = f.read()

    result = await pdf_processor.process_bytes(
        pdf_bytes, filename="test.pdf", extract_images=False
    )

    assert isinstance(result, PDFInfo)
    assert result.filename == "test.pdf"
    assert result.num_pages == 3


@pytest.mark.asyncio
async def test_metadata_extraction(pdf_processor, sample_pdf):
    """Test metadata extraction."""
    result = await pdf_processor.process_file(sample_pdf)

    assert result.num_pages == 3
    assert result.metadata is not None
    assert "num_pages" in result.metadata
    assert result.metadata["num_pages"] == 3


@pytest.mark.asyncio
async def test_file_not_found():
    """Test error handling for missing file."""
    processor = PDFProcessor()
    fake_path = Path("/tmp/nonexistent_file.pdf")

    with pytest.raises(PDFError, match="not found"):
        await processor.process_file(fake_path)


@pytest.mark.asyncio
async def test_invalid_file_type():
    """Test error handling for non-PDF file."""
    processor = PDFProcessor()

    # Create a text file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        text_path = Path(f.name)
        f.write(b"Not a PDF")

    try:
        with pytest.raises(PDFError, match="Not a PDF file"):
            await processor.process_file(text_path)
    finally:
        text_path.unlink()


@pytest.mark.asyncio
async def test_max_pages_limit():
    """Test max pages limit enforcement."""
    processor = PDFProcessor(max_pages=2)

    # Create PDF with 3 pages (using sample_pdf fixture approach)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = Path(f.name)

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    for i in range(3):
        c.drawString(100, 750, f"Page {i+1}")
        c.showPage()
    c.save()

    try:
        with pytest.raises(PDFError, match="too large"):
            await processor.process_file(pdf_path)
    finally:
        pdf_path.unlink()


@pytest.mark.asyncio
async def test_cache_cleanup(pdf_processor):
    """Test cache cleanup functionality."""
    # Process a sample PDF to create cache
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = Path(f.name)

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Test")
    c.showPage()
    c.save()

    try:
        await pdf_processor.process_file(pdf_path, extract_images=False)

        # Clean up cache (won't remove recent files)
        count = await pdf_processor.cleanup_cache(max_age_days=0)
        assert count >= 0  # Just ensure it runs without error

    finally:
        pdf_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_page_content_methods():
    """Test PageContent helper methods."""
    page = PageContent(
        page_num=1,
        text="Original text",
        images=[],
        has_text=True,
        ocr_text="OCR text",
    )

    # When has_text, should return original text
    assert page.get_full_text() == "Original text"

    # When no text, should return OCR text
    page2 = PageContent(
        page_num=2,
        text="",
        images=[],
        has_text=False,
        ocr_text="OCR text only",
    )
    assert page2.get_full_text() == "OCR text only"


@pytest.mark.asyncio
async def test_pdf_info_methods(pdf_processor, sample_pdf):
    """Test PDFInfo helper methods."""
    result = await pdf_processor.process_file(sample_pdf, extract_images=False)

    # Test get_full_text
    full_text = result.get_full_text()
    assert isinstance(full_text, str)
    assert len(full_text) > 0

    # Test get_all_images
    images = result.get_all_images()
    assert isinstance(images, list)


def test_cache_key_generation():
    """Test cache key generation."""
    processor = PDFProcessor()

    # Test with string
    key1 = processor._cache_key("test.pdf")
    assert isinstance(key1, str)
    assert len(key1) == 16

    # Same input should give same key
    key2 = processor._cache_key("test.pdf")
    assert key1 == key2

    # Different input should give different key
    key3 = processor._cache_key("other.pdf")
    assert key1 != key3
