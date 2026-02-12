"""PDF processor for extracting trading strategies from PDF documents.

This module handles the extraction of text content from PDF files,
preprocessing the content for strategy analysis, and creating structured
data for the knowledge base.
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import fitz  # PyMuPDF
import PyPDF2
from io import BytesIO
import uuid

from ..types import IngestionSource, SourceType
from ..types.pydantic_models import IngestionSourceModel


logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""
    pass


class PDFProcessor:
    """
    PDF processor for extracting text and metadata from trading education PDFs.
    
    This processor handles:
    - Text extraction from PDF files
    - Content cleaning and preprocessing
    - Metadata extraction (title, author, page count)
    - Error handling and recovery
    - Integration with IngestionSource data model
    """
    
    def __init__(self, max_file_size_mb: int = 50):
        """
        Initialize the PDF processor.
        
        Args:
            max_file_size_mb: Maximum file size in MB to process
        """
        self.max_file_size_mb = max_file_size_mb
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        # Supported PDF MIME types
        self.supported_mime_types = {
            'application/pdf',
            'application/x-pdf',
            'application/acrobat',
            'applications/vnd.pdf',
            'text/pdf',
            'text/x-pdf'
        }
    
    async def process_pdf(
        self,
        file_path: str,
        source_url: str = "",
        title: str = "",
        author: str = "",
        description: str = "",
        tags: List[str] = None
    ) -> IngestionSourceModel:
        """
        Process a PDF file and create an IngestionSource record.
        
        Args:
            file_path: Path to the PDF file
            source_url: Original URL if downloaded
            title: Manual title override
            author: Manual author override
            description: Manual description override
            tags: List of tags to apply
            
        Returns:
            IngestionSourceModel with extracted content
            
        Raises:
            PDFProcessingError: If processing fails
        """
        if tags is None:
            tags = []
            
        # Validate file
        await self._validate_file(file_path)
        
        # Extract content and metadata
        try:
            text_content, metadata, images_info = await self._extract_content(file_path)
            
            # Create ingestion source record
            ingestion_source = IngestionSourceModel(
                id=str(uuid.uuid4()),
                source_type=SourceType.PDF,
                source_url=source_url,
                local_path=file_path,
                title=title or metadata.get('title', Path(file_path).stem),
                author=author or metadata.get('author', ''),
                description=description or metadata.get('subject', ''),
                tags=tags,
                status="completed",
                error_message="",
                extracted_text=text_content,
                extracted_images=images_info,
                created_at=datetime.utcnow(),
                processed_at=datetime.utcnow()
            )
            
            logger.info(f"Successfully processed PDF: {file_path}")
            logger.info(f"Extracted {len(text_content)} characters and {len(images_info)} images")
            
            return ingestion_source
            
        except Exception as e:
            error_msg = f"Failed to process PDF {file_path}: {str(e)}"
            logger.error(error_msg)
            
            # Return failed ingestion source for tracking
            return IngestionSourceModel(
                id=str(uuid.uuid4()),
                source_type=SourceType.PDF,
                source_url=source_url,
                local_path=file_path,
                title=title or Path(file_path).stem,
                author=author,
                description=description,
                tags=tags,
                status="error",
                error_message=error_msg,
                extracted_text="",
                extracted_images=[],
                created_at=datetime.utcnow(),
                processed_at=None
            )
    
    async def _validate_file(self, file_path: str) -> None:
        """
        Validate that the file exists, is readable, and within size limits.
        
        Args:
            file_path: Path to the PDF file
            
        Raises:
            PDFProcessingError: If validation fails
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            raise PDFProcessingError(f"File does not exist: {file_path}")
        
        # Check if file is readable
        if not path.is_file():
            raise PDFProcessingError(f"Path is not a file: {file_path}")
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size_bytes:
            size_mb = file_size / (1024 * 1024)
            raise PDFProcessingError(
                f"File too large: {size_mb:.1f}MB (max: {self.max_file_size_mb}MB)"
            )
        
        # Check file extension
        if path.suffix.lower() != '.pdf':
            logger.warning(f"File does not have .pdf extension: {file_path}")
    
    async def _extract_content(self, file_path: str) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract text content, metadata, and image information from PDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (text_content, metadata, images_info)
        """
        # Try PyMuPDF first (more robust)
        try:
            return await self._extract_with_pymupdf(file_path)
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}, trying PyPDF2")
            
            # Fallback to PyPDF2
            try:
                return await self._extract_with_pypdf2(file_path)
            except Exception as e2:
                logger.error(f"Both extraction methods failed. PyMuPDF: {e}, PyPDF2: {e2}")
                raise PDFProcessingError(f"Could not extract content from PDF: {e2}")
    
    async def _extract_with_pymupdf(self, file_path: str) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract content using PyMuPDF (fitz).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (text_content, metadata, images_info)
        """
        text_content = []
        images_info = []
        
        # Open PDF document
        doc = fitz.open(file_path)
        
        try:
            # Extract metadata
            metadata = {
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'keywords': doc.metadata.get('keywords', ''),
                'creator': doc.metadata.get('creator', ''),
                'producer': doc.metadata.get('producer', ''),
                'creation_date': doc.metadata.get('creationDate', ''),
                'modification_date': doc.metadata.get('modDate', ''),
                'page_count': doc.page_count,
                'is_encrypted': doc.is_encrypted,
                'is_pdf': doc.is_pdf
            }
            
            # Extract text from each page
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Extract text
                page_text = page.get_text()
                if page_text.strip():
                    text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                
                # Extract image information
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    images_info.append({
                        'page': page_num + 1,
                        'index': img_index,
                        'xref': img[0],
                        'smask': img[1],
                        'width': img[2],
                        'height': img[3],
                        'bpc': img[4],
                        'colorspace': img[5],
                        'alt': img[6],
                        'name': img[7],
                        'filter': img[8]
                    })
        
        finally:
            doc.close()
        
        # Join all text content
        full_text = '\n\n'.join(text_content)
        
        # Clean and preprocess text
        cleaned_text = await self._clean_text(full_text)
        
        return cleaned_text, metadata, images_info
    
    async def _extract_with_pypdf2(self, file_path: str) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract content using PyPDF2 as fallback.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (text_content, metadata, images_info)
        """
        text_content = []
        images_info = []
        
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract metadata
            metadata = {}
            if reader.metadata:
                metadata = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', ''),
                    'producer': reader.metadata.get('/Producer', ''),
                    'creation_date': str(reader.metadata.get('/CreationDate', '')),
                    'modification_date': str(reader.metadata.get('/ModDate', '')),
                    'page_count': len(reader.pages),
                    'is_encrypted': reader.is_encrypted
                }
            
            # Extract text from each page
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as e:
                    logger.warning(f"Could not extract text from page {page_num + 1}: {e}")
                    text_content.append(f"--- Page {page_num + 1} ---\n[Text extraction failed]")
        
        # Join all text content
        full_text = '\n\n'.join(text_content)
        
        # Clean and preprocess text
        cleaned_text = await self._clean_text(full_text)
        
        return cleaned_text, metadata, images_info
    
    async def _clean_text(self, text: str) -> str:
        """
        Clean and preprocess extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove page numbers and headers/footers (common patterns)
        text = re.sub(r'\n\d+\s*\n', '\n', text)  # Standalone page numbers
        text = re.sub(r'\nPage \d+ of \d+\n', '\n', text)  # "Page X of Y"
        
        # Remove excessive dashes and underscores (table formatting)
        text = re.sub(r'[-_]{10,}', '', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove zero-width characters and other non-printables
        text = re.sub(r'[\u200b-\u200f\u2060\ufeff]', '', text)
        
        # Ensure proper spacing after periods
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        return text.strip()
    
    def extract_trading_keywords(self, text: str) -> List[str]:
        """
        Extract trading-related keywords and phrases from text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of relevant trading keywords found
        """
        # Trading-related keyword patterns
        trading_patterns = {
            # Entry types
            'entry_patterns': [
                r'liquidity\s+engulf', r'LE\s+candle', r'small\s+wick', 
                r'steeper\s+wick', r'celery\s+play', r'breakout', r'fakeout'
            ],
            
            # Market structure
            'structure': [
                r'break\s+of\s+structure', r'BOS', r'change\s+of\s+character', 
                r'CHoCH', r'market\s+structure', r'support', r'resistance',
                r'supply\s+zone', r'demand\s+zone', r'order\s+block'
            ],
            
            # Risk management
            'risk': [
                r'risk\s+management', r'stop\s+loss', r'take\s+profit', 
                r'position\s+sizing', r'R\s+multiple', r'reward\s+risk',
                r'money\s+management'
            ],
            
            # Timeframes
            'timeframes': [
                r'\d+[mh]', r'daily', r'weekly', r'monthly', r'H\d+', r'M\d+',
                r'higher\s+timeframe', r'lower\s+timeframe', r'HTF', r'LTF'
            ],
            
            # Trading concepts
            'concepts': [
                r'confluence', r'bias', r'trend', r'ranging', r'momentum',
                r'reversal', r'continuation', r'accumulation', r'distribution'
            ]
        }
        
        found_keywords = []
        text_lower = text.lower()
        
        for category, patterns in trading_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    keyword = match.group(0)
                    if keyword not in found_keywords:
                        found_keywords.append(keyword)
        
        return found_keywords
    
    async def batch_process_pdfs(
        self,
        pdf_paths: List[str],
        max_concurrent: int = 3
    ) -> List[IngestionSourceModel]:
        """
        Process multiple PDF files concurrently.
        
        Args:
            pdf_paths: List of PDF file paths to process
            max_concurrent: Maximum concurrent processing tasks
            
        Returns:
            List of IngestionSourceModel objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_pdf(path: str) -> IngestionSourceModel:
            async with semaphore:
                return await self.process_pdf(path)
        
        tasks = [process_single_pdf(path) for path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {pdf_paths[i]}: {result}")
                # Create error record
                error_result = IngestionSourceModel(
                    id=str(uuid.uuid4()),
                    source_type=SourceType.PDF,
                    source_url="",
                    local_path=pdf_paths[i],
                    title=Path(pdf_paths[i]).stem,
                    status="error",
                    error_message=str(result),
                    created_at=datetime.utcnow()
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results


# Utility functions
def is_pdf_file(file_path: str) -> bool:
    """Check if a file is a PDF based on extension and magic bytes."""
    try:
        path = Path(file_path)
        
        # Check extension
        if path.suffix.lower() != '.pdf':
            return False
        
        # Check magic bytes
        with open(file_path, 'rb') as f:
            header = f.read(5)
            return header == b'%PDF-'
    except Exception:
        return False


def get_pdf_files_from_directory(directory: str, recursive: bool = False) -> List[str]:
    """
    Get all PDF files from a directory.
    
    Args:
        directory: Directory path to search
        recursive: Whether to search recursively
        
    Returns:
        List of PDF file paths
    """
    pdf_files = []
    path = Path(directory)
    
    if not path.exists() or not path.is_dir():
        return pdf_files
    
    pattern = "**/*.pdf" if recursive else "*.pdf"
    
    for pdf_path in path.glob(pattern):
        if pdf_path.is_file() and is_pdf_file(str(pdf_path)):
            pdf_files.append(str(pdf_path))
    
    return pdf_files


async def extract_text_preview(file_path: str, max_chars: int = 500) -> str:
    """
    Extract a text preview from a PDF file.
    
    Args:
        file_path: Path to PDF file
        max_chars: Maximum characters to extract
        
    Returns:
        Text preview
    """
    processor = PDFProcessor()
    
    try:
        await processor._validate_file(file_path)
        text, _, _ = await processor._extract_content(file_path)
        
        if len(text) > max_chars:
            return text[:max_chars] + "..."
        return text
    
    except Exception as e:
        return f"Error extracting preview: {str(e)}"