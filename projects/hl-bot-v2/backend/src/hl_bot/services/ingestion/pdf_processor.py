"""PDF processor for extracting trading knowledge from PDF documents.

Extracts text content per page, embedded images, and performs OCR on image-based PDFs.
Supports both text-based PDFs and scanned documents.
"""

import asyncio
import hashlib
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

logger = logging.getLogger(__name__)


class PDFError(Exception):
    """Base exception for PDF processing errors."""

    pass


class PageContent:
    """Content extracted from a single PDF page."""

    def __init__(
        self,
        page_num: int,
        text: str,
        images: list[Path],
        has_text: bool,
        ocr_text: str = "",
    ):
        self.page_num = page_num
        self.text = text
        self.images = images
        self.has_text = has_text
        self.ocr_text = ocr_text

    def get_full_text(self) -> str:
        """Get combined text from extraction and OCR."""
        if self.text:
            return self.text
        return self.ocr_text

    def __repr__(self) -> str:
        return (
            f"PageContent(page={self.page_num}, text_len={len(self.text)}, "
            f"images={len(self.images)}, has_text={self.has_text})"
        )


class PDFInfo:
    """PDF metadata and extracted content."""

    def __init__(
        self,
        filename: str,
        title: str,
        author: str,
        num_pages: int,
        pages: list[PageContent],
        metadata: dict[str, Any],
    ):
        self.filename = filename
        self.title = title
        self.author = author
        self.num_pages = num_pages
        self.pages = pages
        self.metadata = metadata

    def get_full_text(self) -> str:
        """Get all text from the PDF."""
        return "\n\n".join(page.get_full_text() for page in self.pages)

    def get_all_images(self) -> list[Path]:
        """Get all extracted images."""
        images = []
        for page in self.pages:
            images.extend(page.images)
        return images

    def __repr__(self) -> str:
        return (
            f"PDFInfo(filename='{self.filename}', pages={self.num_pages}, "
            f"images={len(self.get_all_images())})"
        )


class PDFProcessor:
    """Process PDF documents to extract educational content."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        enable_ocr: bool = True,
        min_image_size: tuple[int, int] = (100, 100),
        max_pages: int = 500,
        extract_images: bool = True,
    ):
        """Initialize PDF processor.

        Args:
            cache_dir: Directory for caching extracted content (uses temp if None)
            enable_ocr: Whether to use OCR for image-based PDFs
            min_image_size: Minimum image dimensions (width, height) to extract
            max_pages: Maximum number of pages to process
            extract_images: Whether to extract embedded images
        """
        self._cache_dir = cache_dir or Path(tempfile.gettempdir()) / "hl_bot_pdf"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._enable_ocr = enable_ocr
        self._min_image_size = min_image_size
        self._max_pages = max_pages
        self._extract_images = extract_images
        logger.info(
            f"PDF processor initialized: cache={self._cache_dir}, "
            f"ocr={enable_ocr}, max_pages={max_pages}"
        )

    async def process_file(
        self,
        pdf_path: Path,
        extract_images: bool | None = None,
    ) -> PDFInfo:
        """Process a PDF file and extract content.

        Args:
            pdf_path: Path to PDF file
            extract_images: Override default image extraction setting

        Returns:
            PDFInfo object with extracted content

        Raises:
            PDFError: If processing fails
        """
        if not pdf_path.exists():
            raise PDFError(f"PDF file not found: {pdf_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise PDFError(f"Not a PDF file: {pdf_path}")

        logger.info(f"Processing PDF: {pdf_path}")

        extract_imgs = extract_images if extract_images is not None else self._extract_images
        cache_key = self._cache_key(pdf_path)
        work_dir = self._cache_dir / cache_key
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Get metadata
            metadata = await self._get_metadata(pdf_path)
            num_pages = metadata.get("num_pages", 0)

            if num_pages > self._max_pages:
                raise PDFError(
                    f"PDF too large: {num_pages} pages (max {self._max_pages})"
                )

            logger.info(f"Processing {num_pages} pages from {pdf_path.name}")

            # Extract content from all pages
            pages = await self._extract_pages(pdf_path, work_dir, extract_imgs)

            # Check if OCR is needed
            if self._enable_ocr:
                pages = await self._apply_ocr_if_needed(pages, work_dir)

            return PDFInfo(
                filename=pdf_path.name,
                title=metadata.get("title", pdf_path.stem),
                author=metadata.get("author", ""),
                num_pages=num_pages,
                pages=pages,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            raise PDFError(f"PDF processing failed: {e}")

    async def process_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        extract_images: bool | None = None,
    ) -> PDFInfo:
        """Process PDF from bytes.

        Args:
            pdf_bytes: PDF file content
            filename: Original filename for reference
            extract_images: Override default image extraction setting

        Returns:
            PDFInfo object with extracted content

        Raises:
            PDFError: If processing fails
        """
        # Write to temporary file
        temp_path = self._cache_dir / f"temp_{self._cache_key(filename)}.pdf"

        try:
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(pdf_bytes)

            result = await self.process_file(temp_path, extract_images)
            # Update filename to original
            result.filename = filename
            return result

        finally:
            # Clean up temp file
            temp_path.unlink(missing_ok=True)

    async def _get_metadata(self, pdf_path: Path) -> dict[str, Any]:
        """Extract PDF metadata.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Metadata dictionary
        """
        loop = asyncio.get_event_loop()

        def _extract_metadata() -> dict[str, Any]:
            try:
                doc = fitz.open(pdf_path)
                metadata = {
                    "num_pages": len(doc),
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "keywords": doc.metadata.get("keywords", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "producer": doc.metadata.get("producer", ""),
                    "creation_date": doc.metadata.get("creationDate", ""),
                    "mod_date": doc.metadata.get("modDate", ""),
                }
                doc.close()
                return metadata
            except Exception as e:
                logger.warning(f"Failed to extract metadata: {e}")
                return {"num_pages": 0}

        return await loop.run_in_executor(None, _extract_metadata)

    async def _extract_pages(
        self,
        pdf_path: Path,
        work_dir: Path,
        extract_images: bool,
    ) -> list[PageContent]:
        """Extract content from all pages.

        Args:
            pdf_path: Path to PDF file
            work_dir: Working directory for extracted content
            extract_images: Whether to extract images

        Returns:
            List of PageContent objects
        """
        loop = asyncio.get_event_loop()

        def _extract() -> list[PageContent]:
            pages: list[PageContent] = []

            # Use PyMuPDF for images and pdfplumber for text
            doc = fitz.open(pdf_path)

            try:
                for page_num in range(len(doc)):
                    try:
                        # Extract text with pdfplumber (better text extraction)
                        text = self._extract_text_with_pdfplumber(pdf_path, page_num)

                        # Extract images with PyMuPDF
                        images: list[Path] = []
                        if extract_images:
                            images = self._extract_images_from_page(
                                doc[page_num], page_num, work_dir
                            )

                        has_text = bool(text.strip())

                        pages.append(
                            PageContent(
                                page_num=page_num + 1,  # 1-indexed
                                text=text,
                                images=images,
                                has_text=has_text,
                            )
                        )

                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        # Add empty page to maintain numbering
                        pages.append(
                            PageContent(
                                page_num=page_num + 1,
                                text="",
                                images=[],
                                has_text=False,
                            )
                        )

            finally:
                doc.close()

            logger.info(f"Extracted {len(pages)} pages")
            return pages

        return await loop.run_in_executor(None, _extract)

    def _extract_text_with_pdfplumber(self, pdf_path: Path, page_num: int) -> str:
        """Extract text from a page using pdfplumber.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            Extracted text
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num < len(pdf.pages):
                    page = pdf.pages[page_num]
                    text = page.extract_text() or ""
                    return text.strip()
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for page {page_num + 1}: {e}")

        # Fallback to PyMuPDF
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            text = page.get_text()
            doc.close()
            return text.strip()
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed for page {page_num + 1}: {e}")
            return ""

    def _extract_images_from_page(
        self,
        page: Any,  # fitz.Page
        page_num: int,
        work_dir: Path,
    ) -> list[Path]:
        """Extract images from a PDF page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)
            work_dir: Working directory for images

        Returns:
            List of paths to extracted images
        """
        images: list[Path] = []
        images_dir = work_dir / "images"
        images_dir.mkdir(exist_ok=True)

        try:
            image_list = page.get_images()

            for img_idx, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    base_image = page.parent.extract_image(xref)

                    if not base_image:
                        continue

                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Save image
                    image_path = images_dir / f"page_{page_num + 1}_img_{img_idx}.{image_ext}"

                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)

                    # Check image size
                    try:
                        with Image.open(image_path) as img:
                            width, height = img.size

                            # Filter out small images (likely icons/logos)
                            if (
                                width >= self._min_image_size[0]
                                and height >= self._min_image_size[1]
                            ):
                                images.append(image_path)
                                logger.debug(
                                    f"Extracted image: {image_path.name} ({width}x{height})"
                                )
                            else:
                                # Remove small image
                                image_path.unlink()

                    except Exception as e:
                        logger.warning(f"Failed to validate image {image_path}: {e}")
                        image_path.unlink(missing_ok=True)

                except Exception as e:
                    logger.warning(
                        f"Failed to extract image {img_idx} from page {page_num + 1}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to get images from page {page_num + 1}: {e}")

        return images

    async def _apply_ocr_if_needed(
        self,
        pages: list[PageContent],
        work_dir: Path,
    ) -> list[PageContent]:
        """Apply OCR to pages that have no text but have images.

        Args:
            pages: List of page contents
            work_dir: Working directory

        Returns:
            Updated list of page contents with OCR text
        """
        # Check if any pages need OCR
        pages_needing_ocr = [
            page for page in pages if not page.has_text and len(page.images) > 0
        ]

        if not pages_needing_ocr:
            logger.info("No pages need OCR")
            return pages

        logger.info(f"Applying OCR to {len(pages_needing_ocr)} pages")

        loop = asyncio.get_event_loop()

        async def _ocr_page(page: PageContent) -> PageContent:
            """Apply OCR to a single page."""

            def _do_ocr() -> str:
                try:
                    import pytesseract

                    # OCR all images from this page
                    texts = []
                    for img_path in page.images:
                        try:
                            img = Image.open(img_path)
                            text = pytesseract.image_to_string(img)
                            if text.strip():
                                texts.append(text.strip())
                        except Exception as e:
                            logger.warning(f"OCR failed for {img_path}: {e}")

                    return "\n\n".join(texts)

                except ImportError:
                    logger.warning("pytesseract not available, skipping OCR")
                    return ""
                except Exception as e:
                    logger.warning(f"OCR failed for page {page.page_num}: {e}")
                    return ""

            ocr_text = await loop.run_in_executor(None, _do_ocr)
            page.ocr_text = ocr_text
            return page

        # Apply OCR to all pages that need it (with concurrency limit)
        for page in pages_needing_ocr:
            await _ocr_page(page)

        return pages

    def _cache_key(self, identifier: Path | str) -> str:
        """Generate cache key from file path or string.

        Args:
            identifier: File path or string to hash

        Returns:
            Cache key (hash)
        """
        if isinstance(identifier, Path):
            # Use file path and modification time for uniqueness
            try:
                mtime = identifier.stat().st_mtime
                key_str = f"{identifier.absolute()}_{mtime}"
            except Exception:
                key_str = str(identifier.absolute())
        else:
            key_str = identifier

        return hashlib.md5(key_str.encode()).hexdigest()[:16]

    async def cleanup_cache(self, max_age_days: int = 7) -> int:
        """Clean up old cached files.

        Args:
            max_age_days: Remove files older than this many days

        Returns:
            Number of directories removed
        """
        count = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)

        loop = asyncio.get_event_loop()

        def _cleanup() -> int:
            removed = 0
            for item in self._cache_dir.iterdir():
                if item.is_dir():
                    try:
                        if item.stat().st_mtime < cutoff:
                            shutil.rmtree(item, ignore_errors=True)
                            removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove {item}: {e}")
            return removed

        count = await loop.run_in_executor(None, _cleanup)

        logger.info(f"Cleaned up {count} old cache directories")
        return count

    async def extract_tables(self, pdf_path: Path, page_num: int | None = None) -> list[list[list[str]]]:
        """Extract tables from PDF using pdfplumber.

        Args:
            pdf_path: Path to PDF file
            page_num: Specific page number (1-indexed), or None for all pages

        Returns:
            List of tables (each table is a list of rows, each row is a list of cells)
        """
        loop = asyncio.get_event_loop()

        def _extract() -> list[list[list[str]]]:
            tables = []
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    pages_to_process = (
                        [pdf.pages[page_num - 1]] if page_num else pdf.pages
                    )

                    for page in pages_to_process:
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables.extend(page_tables)

            except Exception as e:
                logger.warning(f"Table extraction failed: {e}")

            return tables

        return await loop.run_in_executor(None, _extract)
