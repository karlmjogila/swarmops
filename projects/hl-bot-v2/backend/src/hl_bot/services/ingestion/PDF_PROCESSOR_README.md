# PDF Processor

Extract trading knowledge from PDF documents with text extraction, image extraction, and OCR support.

## Features

- **Text Extraction**: Extracts text per page using pdfplumber (primary) and PyMuPDF (fallback)
- **Image Extraction**: Extracts embedded images from PDFs, filtering out small icons/logos
- **OCR Support**: Automatic OCR for scanned/image-based PDFs using Tesseract
- **Table Extraction**: Extract structured tables from PDFs
- **Async/Await**: Fully asynchronous API for non-blocking operations
- **Caching**: Intelligent caching with automatic cleanup
- **Error Handling**: Comprehensive error handling with detailed logging

## Installation

The PDF processor dependencies are included in the project:

```bash
poetry install
```

For OCR functionality, you also need Tesseract installed on your system:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Check installation
tesseract --version
```

## Quick Start

```python
from pathlib import Path
from hl_bot.services.ingestion import PDFProcessor

async def process_pdf():
    # Initialize processor
    processor = PDFProcessor(
        enable_ocr=True,          # Enable OCR for scanned PDFs
        extract_images=True,       # Extract embedded images
        min_image_size=(100, 100), # Filter small images
        max_pages=500,             # Maximum pages to process
    )
    
    # Process a PDF file
    result = await processor.process_file(Path("strategy.pdf"))
    
    # Access extracted content
    print(f"Pages: {result.num_pages}")
    print(f"Full text length: {len(result.get_full_text())}")
    print(f"Images extracted: {len(result.get_all_images())}")
    
    # Access individual pages
    for page in result.pages:
        print(f"Page {page.page_num}: {len(page.text)} chars")
        if page.images:
            print(f"  - {len(page.images)} images")
        if page.ocr_text:
            print(f"  - OCR applied")
```

## API Reference

### PDFProcessor

Main class for processing PDF documents.

#### Constructor

```python
PDFProcessor(
    cache_dir: Path | None = None,
    enable_ocr: bool = True,
    min_image_size: tuple[int, int] = (100, 100),
    max_pages: int = 500,
    extract_images: bool = True,
)
```

**Parameters:**
- `cache_dir`: Directory for caching extracted content (uses temp if None)
- `enable_ocr`: Whether to use OCR for image-based PDFs
- `min_image_size`: Minimum image dimensions (width, height) to extract
- `max_pages`: Maximum number of pages to process
- `extract_images`: Whether to extract embedded images

#### Methods

##### `process_file(pdf_path: Path, extract_images: bool | None = None) -> PDFInfo`

Process a PDF file and extract content.

```python
result = await processor.process_file(Path("document.pdf"))
```

**Raises:** `PDFError` if processing fails

##### `process_bytes(pdf_bytes: bytes, filename: str, extract_images: bool | None = None) -> PDFInfo`

Process PDF from bytes (useful for uploaded files).

```python
with open("document.pdf", "rb") as f:
    pdf_bytes = f.read()
result = await processor.process_bytes(pdf_bytes, "document.pdf")
```

##### `extract_tables(pdf_path: Path, page_num: int | None = None) -> list[list[list[str]]]`

Extract tables from PDF.

```python
# Extract from all pages
tables = await processor.extract_tables(Path("document.pdf"))

# Extract from specific page
tables = await processor.extract_tables(Path("document.pdf"), page_num=5)
```

##### `cleanup_cache(max_age_days: int = 7) -> int`

Clean up old cached files.

```python
removed = await processor.cleanup_cache(max_age_days=7)
print(f"Removed {removed} old cache directories")
```

### PDFInfo

Container for extracted PDF content.

**Attributes:**
- `filename: str` - Original filename
- `title: str` - PDF title from metadata
- `author: str` - PDF author from metadata
- `num_pages: int` - Number of pages
- `pages: list[PageContent]` - List of page contents
- `metadata: dict[str, Any]` - Full PDF metadata

**Methods:**
- `get_full_text() -> str` - Get all text from the PDF
- `get_all_images() -> list[Path]` - Get all extracted images

### PageContent

Content from a single PDF page.

**Attributes:**
- `page_num: int` - Page number (1-indexed)
- `text: str` - Extracted text
- `images: list[Path]` - Paths to extracted images
- `has_text: bool` - Whether page has extractable text
- `ocr_text: str` - Text from OCR (if applied)

**Methods:**
- `get_full_text() -> str` - Get combined text from extraction and OCR

## Usage Examples

### Process PDF with Images

```python
processor = PDFProcessor(extract_images=True)
result = await processor.process_file(Path("trading_guide.pdf"))

# Save images to a specific directory
import shutil
output_dir = Path("extracted_images")
output_dir.mkdir(exist_ok=True)

for img_path in result.get_all_images():
    shutil.copy(img_path, output_dir / img_path.name)
```

### Process Scanned PDF with OCR

```python
processor = PDFProcessor(enable_ocr=True)
result = await processor.process_file(Path("scanned_doc.pdf"))

# Check which pages needed OCR
for page in result.pages:
    if page.ocr_text:
        print(f"Page {page.page_num} was OCR'd")
```

### Extract Trading Strategy Rules

```python
processor = PDFProcessor()
result = await processor.process_file(Path("strategy.pdf"))

full_text = result.get_full_text()

# Look for entry rules
if "entry" in full_text.lower():
    print("✓ Found entry rules")
    
# Look for risk management
if "risk" in full_text.lower() or "stop loss" in full_text.lower():
    print("✓ Found risk management section")
    
# Extract tables (could be setup parameters)
tables = await processor.extract_tables(Path("strategy.pdf"))
if tables:
    print(f"✓ Found {len(tables)} tables")
```

### Process Uploaded PDF (FastAPI Example)

```python
from fastapi import UploadFile, File
from hl_bot.services.ingestion import PDFProcessor

processor = PDFProcessor()

@app.post("/api/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)):
    # Read uploaded file
    pdf_bytes = await file.read()
    
    # Process
    result = await processor.process_bytes(pdf_bytes, file.filename)
    
    return {
        "filename": result.filename,
        "pages": result.num_pages,
        "text_length": len(result.get_full_text()),
        "images": len(result.get_all_images()),
    }
```

### Batch Processing with Concurrency Control

```python
from pathlib import Path
import asyncio

async def process_with_limit(pdf_files: list[Path], concurrency: int = 3):
    """Process multiple PDFs with concurrency limit."""
    processor = PDFProcessor()
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async def process_one(pdf_path: Path):
        async with semaphore:
            try:
                result = await processor.process_file(pdf_path)
                print(f"✓ {pdf_path.name}: {result.num_pages} pages")
                return result
            except Exception as e:
                print(f"✗ {pdf_path.name}: {e}")
                return None
    
    tasks = [process_one(pdf) for pdf in pdf_files]
    results = await asyncio.gather(*tasks)
    
    return [r for r in results if r is not None]

# Usage
pdf_files = list(Path("pdfs").glob("*.pdf"))
results = await process_with_limit(pdf_files, concurrency=3)
```

## Error Handling

The processor raises `PDFError` for processing failures:

```python
from hl_bot.services.ingestion import PDFProcessor, PDFError

processor = PDFProcessor()

try:
    result = await processor.process_file(Path("document.pdf"))
except PDFError as e:
    print(f"PDF processing failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

Common error cases:
- File not found
- Not a valid PDF file
- PDF too large (exceeds max_pages)
- Corrupted PDF
- OCR failure (falls back to empty text)

## Performance Tips

1. **Disable features you don't need:**
   ```python
   # For text-only extraction (faster)
   processor = PDFProcessor(extract_images=False, enable_ocr=False)
   ```

2. **Adjust image filtering:**
   ```python
   # Skip small images (icons, logos)
   processor = PDFProcessor(min_image_size=(200, 200))
   ```

3. **Process in batches:**
   ```python
   # Use concurrency control to avoid overwhelming the system
   results = await process_with_limit(pdf_files, concurrency=3)
   ```

4. **Clean cache regularly:**
   ```python
   # Clean up old cache files
   await processor.cleanup_cache(max_age_days=1)
   ```

## Architecture

The PDF processor uses a hybrid approach for maximum compatibility:

1. **Text Extraction:**
   - Primary: `pdfplumber` (better for structured documents)
   - Fallback: `PyMuPDF` (faster, more robust)

2. **Image Extraction:**
   - `PyMuPDF` for extracting embedded images
   - `PIL` for image validation and filtering

3. **OCR:**
   - `pytesseract` wrapper for Google's Tesseract
   - Only applied to pages without extractable text

4. **Async Execution:**
   - CPU-intensive operations run in thread pool executor
   - No blocking of the event loop
   - Proper error handling and cleanup

## Testing

Run tests with pytest:

```bash
cd backend
poetry run pytest tests/test_pdf_processor.py -v
```

Example test run:

```bash
poetry run python examples/pdf_processor_example.py path/to/your.pdf
```

## Integration with Content Ingestion Pipeline

The PDF processor is designed to integrate with the broader content ingestion system:

```python
# In ingestion API endpoint
from hl_bot.services.ingestion import PDFProcessor

processor = PDFProcessor()

async def ingest_pdf_document(pdf_path: Path) -> dict:
    # Extract content
    pdf_info = await processor.process_file(pdf_path)
    
    # Pass to strategy extractor (LLM)
    from hl_bot.llm.extractor import extract_strategy_rules
    
    strategy_rules = await extract_strategy_rules(
        text=pdf_info.get_full_text(),
        images=pdf_info.get_all_images(),
        source={
            "type": "pdf",
            "filename": pdf_info.filename,
            "pages": pdf_info.num_pages,
        }
    )
    
    return strategy_rules
```

## Limitations

- **OCR Accuracy**: Tesseract works best on clear, high-contrast scans
- **Complex Layouts**: Multi-column layouts may not extract in reading order
- **Encrypted PDFs**: Password-protected PDFs are not supported
- **Large Files**: Very large PDFs (>500 pages) are rejected by default
- **Memory**: Large PDFs with many images can use significant memory

## Troubleshooting

**Problem:** OCR not working

**Solution:** Ensure Tesseract is installed:
```bash
tesseract --version
```

**Problem:** Slow processing

**Solution:** 
- Disable features you don't need (images, OCR)
- Reduce image quality or skip small images
- Process in batches with concurrency limit

**Problem:** Text extraction garbled

**Solution:**
- Try disabling pdfplumber (set it to only use PyMuPDF)
- Check if PDF is encrypted or has copy protection
- Enable OCR for scanned documents

## License

Part of the HL-Bot-V2 project.
