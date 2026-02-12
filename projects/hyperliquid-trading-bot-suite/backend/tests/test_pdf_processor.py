"""Tests for PDF processor functionality."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.ingestion.pdf_processor import PDFProcessor, PDFProcessingError, is_pdf_file
from src.ingestion.pdf_service import PDFIngestionService
from src.types import SourceType


class TestPDFProcessor:
    """Test cases for PDFProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a PDFProcessor instance for testing."""
        return PDFProcessor(max_file_size_mb=10)
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Create a minimal PDF content for testing."""
        # This is a minimal PDF structure for testing
        return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello Trading World!) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000189 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
284
%%EOF"""
    
    @pytest.mark.asyncio
    async def test_validate_file_exists(self, processor):
        """Test file validation with existing file."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-test content')
            tmp_path = tmp.name
        
        try:
            await processor._validate_file(tmp_path)
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_validate_file_not_exists(self, processor):
        """Test file validation with non-existent file."""
        with pytest.raises(PDFProcessingError, match="File does not exist"):
            await processor._validate_file("nonexistent.pdf")
    
    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, processor):
        """Test file validation with oversized file."""
        # Create a file larger than the limit
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Write more than 10MB (processor limit)
            large_content = b'x' * (11 * 1024 * 1024)
            tmp.write(large_content)
            tmp_path = tmp.name
        
        try:
            with pytest.raises(PDFProcessingError, match="File too large"):
                await processor._validate_file(tmp_path)
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_clean_text(self, processor):
        """Test text cleaning functionality."""
        dirty_text = """
        
        Page 1 of 10
        
        
        This is some    trading    text.
        
        
        Page 2 of 10
        
        More content here.And this sentence.
        
        ________________
        
        """
        
        cleaned = await processor._clean_text(dirty_text)
        
        assert "Page 1 of 10" not in cleaned
        assert "Page 2 of 10" not in cleaned
        assert "This is some trading text." in cleaned
        assert ". And this sentence." in cleaned
        assert "________________" not in cleaned
    
    def test_extract_trading_keywords(self, processor):
        """Test trading keyword extraction."""
        text = """
        This document covers liquidity engulf candles and LE patterns.
        We'll discuss risk management, stop loss placement, and take profit levels.
        Market structure analysis including break of structure (BOS) and 
        change of character (CHoCH) are essential for higher timeframe bias.
        """
        
        keywords = processor.extract_trading_keywords(text)
        
        assert "liquidity engulf" in [k.lower() for k in keywords]
        assert any("risk management" in k.lower() for k in keywords)
        assert any("stop loss" in k.lower() for k in keywords)
        assert any("break of structure" in k.lower() for k in keywords)
    
    @pytest.mark.asyncio
    async def test_process_pdf_success(self, processor, sample_pdf_content):
        """Test successful PDF processing."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(sample_pdf_content)
            tmp_path = tmp.name
        
        try:
            # Mock the extraction methods to avoid PDF library dependencies in tests
            with patch.object(processor, '_extract_content') as mock_extract:
                mock_extract.return_value = (
                    "Hello Trading World!",
                    {"title": "Test PDF", "author": "Test Author"},
                    []
                )
                
                result = await processor.process_pdf(
                    file_path=tmp_path,
                    title="Test Trading PDF"
                )
                
                assert result.source_type == SourceType.PDF
                assert result.title == "Test Trading PDF"
                assert result.status == "completed"
                assert result.extracted_text == "Hello Trading World!"
        
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_process_pdf_failure(self, processor):
        """Test PDF processing failure handling."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"Invalid PDF content")
            tmp_path = tmp.name
        
        try:
            result = await processor.process_pdf(file_path=tmp_path)
            
            assert result.status == "error"
            assert result.error_message != ""
        
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_batch_process_pdfs(self, processor):
        """Test batch processing of multiple PDFs."""
        # Create multiple temporary PDF files
        pdf_files = []
        
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(b'%PDF-test content')
                    pdf_files.append(tmp.name)
            
            # Mock the process_pdf method
            async def mock_process_pdf(file_path, **kwargs):
                from src.types.pydantic_models import IngestionSourceModel
                return IngestionSourceModel(
                    source_type=SourceType.PDF,
                    local_path=file_path,
                    title=f"Test {Path(file_path).stem}",
                    status="completed",
                    extracted_text="Test content"
                )
            
            with patch.object(processor, 'process_pdf', side_effect=mock_process_pdf):
                results = await processor.batch_process_pdfs(pdf_files)
                
                assert len(results) == 3
                assert all(r.status == "completed" for r in results)
        
        finally:
            for pdf_file in pdf_files:
                Path(pdf_file).unlink(missing_ok=True)


class TestPDFIngestionService:
    """Test cases for PDFIngestionService class."""
    
    @pytest.fixture
    def service(self):
        """Create a PDFIngestionService instance for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield PDFIngestionService(storage_dir=tmp_dir, max_file_size_mb=5)
    
    @pytest.mark.asyncio
    async def test_validate_upload_valid_pdf(self, service):
        """Test upload validation with valid PDF content."""
        valid_pdf = b'%PDF-1.4\ntest content'
        
        await service._validate_upload(valid_pdf, "test.pdf")
        # Should not raise an exception
    
    @pytest.mark.asyncio
    async def test_validate_upload_invalid_extension(self, service):
        """Test upload validation with invalid file extension."""
        valid_pdf = b'%PDF-1.4\ntest content'
        
        with pytest.raises(PDFProcessingError, match="Invalid file type"):
            await service._validate_upload(valid_pdf, "test.txt")
    
    @pytest.mark.asyncio
    async def test_validate_upload_invalid_content(self, service):
        """Test upload validation with invalid PDF content."""
        invalid_content = b'not a pdf'
        
        with pytest.raises(PDFProcessingError, match="does not appear to be a valid PDF"):
            await service._validate_upload(invalid_content, "test.pdf")
    
    @pytest.mark.asyncio
    async def test_validate_upload_too_large(self, service):
        """Test upload validation with oversized file."""
        large_content = b'%PDF-1.4\n' + b'x' * (6 * 1024 * 1024)  # 6MB, limit is 5MB
        
        with pytest.raises(PDFProcessingError, match="File too large"):
            await service._validate_upload(large_content, "test.pdf")
    
    def test_sanitize_filename(self, service):
        """Test filename sanitization."""
        assert service._sanitize_filename("test file.pdf") == "test_file.pdf"
        assert service._sanitize_filename("../../../etc/passwd") == "passwd.pdf"
        assert service._sanitize_filename("file@#$%^&*().pdf") == "file.pdf"
        assert service._sanitize_filename("normal_file.pdf") == "normal_file.pdf"
    
    @pytest.mark.asyncio
    async def test_upload_and_process_pdf(self, service):
        """Test the complete upload and processing workflow."""
        pdf_content = b'%PDF-1.4\ntest trading content'
        
        # Mock the processor
        with patch.object(service.processor, 'process_pdf') as mock_process:
            from src.types.pydantic_models import IngestionSourceModel
            mock_process.return_value = IngestionSourceModel(
                source_type=SourceType.PDF,
                title="Test PDF",
                status="completed",
                extracted_text="test trading content"
            )
            
            result = await service.upload_and_process_pdf(
                file_content=pdf_content,
                filename="test.pdf",
                title="Trading Guide"
            )
            
            assert result.title == "Trading Guide"
            assert result.status == "completed"
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_processing_stats(self, service):
        """Test statistics retrieval."""
        # Simulate some processing
        service.stats['total_processed'] = 10
        service.stats['successful_processing'] = 8
        service.stats['failed_processing'] = 2
        service.stats['total_characters_extracted'] = 10000
        
        stats = await service.get_processing_stats()
        
        assert stats['total_processed'] == 10
        assert stats['success_rate'] == 80.0
        assert stats['average_characters_per_pdf'] == 1250.0
        assert 'storage_directory' in stats
        assert 'max_file_size_mb' in stats


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_is_pdf_file_valid(self):
        """Test PDF file detection with valid file."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4')
            tmp_path = tmp.name
        
        try:
            assert is_pdf_file(tmp_path) is True
        finally:
            Path(tmp_path).unlink()
    
    def test_is_pdf_file_invalid_extension(self):
        """Test PDF file detection with invalid extension."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b'%PDF-1.4')
            tmp_path = tmp.name
        
        try:
            assert is_pdf_file(tmp_path) is False
        finally:
            Path(tmp_path).unlink()
    
    def test_is_pdf_file_invalid_content(self):
        """Test PDF file detection with invalid content."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'not a pdf')
            tmp_path = tmp.name
        
        try:
            assert is_pdf_file(tmp_path) is False
        finally:
            Path(tmp_path).unlink()
    
    def test_is_pdf_file_nonexistent(self):
        """Test PDF file detection with non-existent file."""
        assert is_pdf_file("nonexistent.pdf") is False


# Example of integration test that could be run with actual PDF files
@pytest.mark.integration
class TestPDFProcessorIntegration:
    """Integration tests that require actual PDF files."""
    
    @pytest.mark.asyncio
    async def test_real_pdf_processing(self):
        """Test processing with a real PDF file (if available)."""
        # This test would only run if a sample PDF is available
        sample_pdf = "tests/fixtures/sample_trading_guide.pdf"
        
        if not Path(sample_pdf).exists():
            pytest.skip("Sample PDF not available")
        
        processor = PDFProcessor()
        result = await processor.process_pdf(sample_pdf)
        
        assert result.status == "completed"
        assert len(result.extracted_text) > 0
        assert result.source_type == SourceType.PDF