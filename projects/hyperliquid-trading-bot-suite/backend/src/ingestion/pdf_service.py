"""PDF ingestion service for managing PDF processing workflow.

This service provides a high-level interface for PDF ingestion,
including database integration, file management, and coordination
with other ingestion components.
"""

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from .pdf_processor import PDFProcessor, PDFProcessingError
from ..types import SourceType
from ..types.pydantic_models import IngestionSourceModel


logger = logging.getLogger(__name__)


class PDFIngestionService:
    """
    Service for managing PDF ingestion workflow.
    
    Handles:
    - File upload and storage
    - PDF processing coordination
    - Database integration
    - Error handling and retry logic
    - Content validation and enrichment
    """
    
    def __init__(
        self,
        storage_dir: str = "data/pdfs",
        max_file_size_mb: int = 50,
        allowed_file_types: Optional[List[str]] = None
    ):
        """
        Initialize the PDF ingestion service.
        
        Args:
            storage_dir: Directory to store uploaded PDF files
            max_file_size_mb: Maximum file size in MB
            allowed_file_types: List of allowed file extensions
        """
        self.storage_dir = Path(storage_dir)
        self.max_file_size_mb = max_file_size_mb
        self.allowed_file_types = allowed_file_types or ['.pdf']
        self.processor = PDFProcessor(max_file_size_mb=max_file_size_mb)
        
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'successful_processing': 0,
            'failed_processing': 0,
            'total_characters_extracted': 0,
            'total_images_found': 0
        }
    
    async def upload_and_process_pdf(
        self,
        file_content: bytes,
        filename: str,
        source_url: str = "",
        title: str = "",
        author: str = "",
        description: str = "",
        tags: List[str] = None,
        auto_extract_tags: bool = True
    ) -> IngestionSourceModel:
        """
        Upload a PDF file and process it for content extraction.
        
        Args:
            file_content: PDF file content as bytes
            filename: Original filename
            source_url: Source URL if downloaded
            title: Manual title override
            author: Manual author override  
            description: Manual description override
            tags: List of tags to apply
            auto_extract_tags: Whether to auto-extract trading keywords as tags
            
        Returns:
            IngestionSourceModel with processing results
            
        Raises:
            PDFProcessingError: If upload or processing fails
        """
        if tags is None:
            tags = []
        
        # Validate file
        await self._validate_upload(file_content, filename)
        
        # Generate unique filename and save file
        file_id = str(uuid.uuid4())
        safe_filename = self._sanitize_filename(filename)
        storage_path = self.storage_dir / f"{file_id}_{safe_filename}"
        
        try:
            # Save uploaded file
            with open(storage_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Saved PDF file: {storage_path}")
            
            # Process the PDF
            result = await self.processor.process_pdf(
                file_path=str(storage_path),
                source_url=source_url,
                title=title,
                author=author,
                description=description,
                tags=tags
            )
            
            # Auto-extract trading keywords as tags if requested
            if auto_extract_tags and result.extracted_text:
                trading_keywords = self.processor.extract_trading_keywords(result.extracted_text)
                result.tags.extend(trading_keywords)
                result.tags = list(set(result.tags))  # Remove duplicates
            
            # Update statistics
            await self._update_stats(result)
            
            return result
            
        except Exception as e:
            # Clean up file on failure
            if storage_path.exists():
                storage_path.unlink()
            
            logger.error(f"Failed to process uploaded PDF {filename}: {e}")
            raise PDFProcessingError(f"Processing failed: {str(e)}")
    
    async def process_existing_pdf(
        self,
        file_path: str,
        source_url: str = "",
        title: str = "",
        author: str = "",
        description: str = "",
        tags: List[str] = None,
        auto_extract_tags: bool = True
    ) -> IngestionSourceModel:
        """
        Process an existing PDF file from the filesystem.
        
        Args:
            file_path: Path to existing PDF file
            source_url: Source URL if applicable
            title: Manual title override
            author: Manual author override
            description: Manual description override
            tags: List of tags to apply
            auto_extract_tags: Whether to auto-extract trading keywords as tags
            
        Returns:
            IngestionSourceModel with processing results
        """
        if tags is None:
            tags = []
        
        # Process the PDF
        result = await self.processor.process_pdf(
            file_path=file_path,
            source_url=source_url,
            title=title,
            author=author,
            description=description,
            tags=tags
        )
        
        # Auto-extract trading keywords as tags if requested
        if auto_extract_tags and result.extracted_text:
            trading_keywords = self.processor.extract_trading_keywords(result.extracted_text)
            result.tags.extend(trading_keywords)
            result.tags = list(set(result.tags))  # Remove duplicates
        
        # Update statistics
        await self._update_stats(result)
        
        return result
    
    async def batch_process_directory(
        self,
        directory: str,
        recursive: bool = False,
        max_concurrent: int = 3,
        auto_extract_tags: bool = True
    ) -> List[IngestionSourceModel]:
        """
        Process all PDF files in a directory.
        
        Args:
            directory: Directory containing PDF files
            recursive: Whether to search recursively
            max_concurrent: Maximum concurrent processing tasks
            auto_extract_tags: Whether to auto-extract trading keywords as tags
            
        Returns:
            List of IngestionSourceModel objects
        """
        from .pdf_processor import get_pdf_files_from_directory
        
        pdf_files = get_pdf_files_from_directory(directory, recursive)
        
        if not pdf_files:
            logger.warning(f"No PDF files found in directory: {directory}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_file(file_path: str) -> IngestionSourceModel:
            async with semaphore:
                return await self.process_existing_pdf(
                    file_path=file_path,
                    auto_extract_tags=auto_extract_tags
                )
        
        tasks = [process_single_file(path) for path in pdf_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update stats
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {pdf_files[i]}: {result}")
                # Create error record
                error_result = IngestionSourceModel(
                    id=str(uuid.uuid4()),
                    source_type=SourceType.PDF,
                    local_path=pdf_files[i],
                    title=Path(pdf_files[i]).stem,
                    status="error",
                    error_message=str(result),
                    created_at=datetime.utcnow()
                )
                processed_results.append(error_result)
                await self._update_stats(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def reprocess_failed_pdfs(
        self,
        failed_sources: List[IngestionSourceModel]
    ) -> List[IngestionSourceModel]:
        """
        Retry processing for failed PDF sources.
        
        Args:
            failed_sources: List of failed IngestionSourceModel objects
            
        Returns:
            List of reprocessed IngestionSourceModel objects
        """
        reprocessed = []
        
        for source in failed_sources:
            if source.status != "error" or not source.local_path:
                continue
            
            try:
                logger.info(f"Retrying processing for: {source.local_path}")
                
                result = await self.process_existing_pdf(
                    file_path=source.local_path,
                    source_url=source.source_url,
                    title=source.title,
                    author=source.author,
                    description=source.description,
                    tags=source.tags
                )
                
                reprocessed.append(result)
                
            except Exception as e:
                logger.error(f"Retry failed for {source.local_path}: {e}")
                # Update error message
                source.error_message = f"Retry failed: {str(e)}"
                reprocessed.append(source)
        
        return reprocessed
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_processing'] / max(self.stats['total_processed'], 1)
            ) * 100,
            'average_characters_per_pdf': (
                self.stats['total_characters_extracted'] / max(self.stats['successful_processing'], 1)
            ),
            'average_images_per_pdf': (
                self.stats['total_images_found'] / max(self.stats['successful_processing'], 1)
            ),
            'storage_directory': str(self.storage_dir),
            'max_file_size_mb': self.max_file_size_mb
        }
    
    async def cleanup_storage(self, older_than_days: int = 30) -> int:
        """
        Clean up old PDF files from storage.
        
        Args:
            older_than_days: Remove files older than this many days
            
        Returns:
            Number of files removed
        """
        if not self.storage_dir.exists():
            return 0
        
        current_time = datetime.utcnow().timestamp()
        cutoff_time = current_time - (older_than_days * 24 * 60 * 60)
        
        removed_count = 0
        
        for file_path in self.storage_dir.glob("*.pdf"):
            try:
                file_mtime = file_path.stat().st_mtime
                if file_mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1
                    logger.info(f"Removed old PDF file: {file_path}")
            
            except Exception as e:
                logger.error(f"Failed to remove file {file_path}: {e}")
        
        return removed_count
    
    async def _validate_upload(self, file_content: bytes, filename: str) -> None:
        """
        Validate uploaded file content and metadata.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Raises:
            PDFProcessingError: If validation fails
        """
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise PDFProcessingError(
                f"File too large: {file_size_mb:.1f}MB (max: {self.max_file_size_mb}MB)"
            )
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_file_types:
            raise PDFProcessingError(
                f"Invalid file type: {file_ext}. Allowed: {self.allowed_file_types}"
            )
        
        # Check PDF magic bytes
        if not file_content.startswith(b'%PDF-'):
            raise PDFProcessingError("File does not appear to be a valid PDF")
        
        # Check for empty files
        if len(file_content) < 100:  # Minimum reasonable PDF size
            raise PDFProcessingError("File appears to be empty or corrupted")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path components and keep only the filename
        safe_name = Path(filename).name
        
        # Replace problematic characters
        safe_name = safe_name.replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '._-')
        
        # Ensure .pdf extension
        if not safe_name.lower().endswith('.pdf'):
            safe_name += '.pdf'
        
        # Limit length
        if len(safe_name) > 255:
            name_part = safe_name[:-4]  # Remove .pdf
            safe_name = name_part[:251] + '.pdf'  # Keep .pdf extension
        
        return safe_name
    
    async def _update_stats(self, result: IngestionSourceModel) -> None:
        """Update processing statistics."""
        self.stats['total_processed'] += 1
        
        if result.status == "completed":
            self.stats['successful_processing'] += 1
            self.stats['total_characters_extracted'] += len(result.extracted_text)
            self.stats['total_images_found'] += len(result.extracted_images)
        else:
            self.stats['failed_processing'] += 1


# Utility functions for the service
async def create_pdf_service(config: Optional[Dict[str, Any]] = None) -> PDFIngestionService:
    """
    Create and configure a PDF ingestion service.
    
    Args:
        config: Service configuration dictionary
        
    Returns:
        Configured PDFIngestionService instance
    """
    if config is None:
        config = {}
    
    service = PDFIngestionService(
        storage_dir=config.get('storage_dir', 'data/pdfs'),
        max_file_size_mb=config.get('max_file_size_mb', 50),
        allowed_file_types=config.get('allowed_file_types', ['.pdf'])
    )
    
    return service


async def process_pdf_from_url(
    service: PDFIngestionService,
    url: str,
    title: str = "",
    author: str = "",
    description: str = "",
    tags: List[str] = None
) -> IngestionSourceModel:
    """
    Download and process a PDF from a URL.
    
    Args:
        service: PDF ingestion service instance
        url: URL to download PDF from
        title: Manual title override
        author: Manual author override
        description: Manual description override
        tags: List of tags to apply
        
    Returns:
        IngestionSourceModel with processing results
    """
    import aiohttp
    
    if tags is None:
        tags = []
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise PDFProcessingError(f"Failed to download PDF: HTTP {response.status}")
            
            content = await response.read()
            filename = url.split('/')[-1]
            
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            return await service.upload_and_process_pdf(
                file_content=content,
                filename=filename,
                source_url=url,
                title=title,
                author=author,
                description=description,
                tags=tags
            )