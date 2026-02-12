# PDF Processor for Hyperliquid Trading Bot Suite

This module provides comprehensive PDF processing capabilities for extracting trading strategies and educational content from PDF documents.

## 🎯 Features

- **Robust PDF Processing**: Supports multiple PDF extraction backends (PyMuPDF, PyPDF2)
- **Trading-Focused**: Automatically extracts trading-related keywords and concepts
- **Content Cleaning**: Advanced text preprocessing and normalization
- **Batch Processing**: Concurrent processing of multiple PDF files
- **Error Handling**: Comprehensive error recovery and logging
- **File Management**: Automatic storage, validation, and cleanup
- **CLI Interface**: Command-line tools for testing and development

## 📁 Module Structure

```
src/ingestion/
├── __init__.py              # Module exports
├── pdf_processor.py         # Core PDF processing logic
├── pdf_service.py          # High-level service layer
├── pdf_cli.py              # Command-line interface
└── README.md               # This documentation
```

## 🚀 Quick Start

### Basic Usage

```python
from src.ingestion import PDFProcessor, PDFIngestionService

# Initialize processor
processor = PDFProcessor(max_file_size_mb=50)

# Process a single PDF
result = await processor.process_pdf(
    file_path="trading_guide.pdf",
    title="Advanced Trading Strategies",
    tags=["scalping", "day-trading"]
)

print(f"Extracted {len(result.extracted_text)} characters")
print(f"Found keywords: {result.tags}")
```

### Service Layer Usage

```python
from src.ingestion import create_pdf_service

# Create service with configuration
service = await create_pdf_service({
    'storage_dir': 'data/pdfs',
    'max_file_size_mb': 50
})

# Upload and process a PDF
with open('strategy_guide.pdf', 'rb') as f:
    result = await service.upload_and_process_pdf(
        file_content=f.read(),
        filename='strategy_guide.pdf',
        title='Market Structure Guide',
        author='John Trader',
        tags=['market-structure', 'supply-demand']
    )
```

### Batch Processing

```python
# Process all PDFs in a directory
results = await service.batch_process_directory(
    directory='pdfs/trading_books',
    recursive=True,
    max_concurrent=3
)

print(f"Processed {len(results)} files")

# Show statistics
stats = await service.get_processing_stats()
print(f"Success rate: {stats['success_rate']:.1f}%")
```

## 🛠️ Command-Line Interface

The PDF processor includes a powerful CLI for development and testing:

```bash
# Navigate to the backend directory
cd backend

# Process a single PDF file
python -m src.ingestion.pdf_cli process trading_guide.pdf --format summary

# Process all PDFs in a directory
python -m src.ingestion.pdf_cli batch pdfs/ --recursive --format json

# Download and process a PDF from URL
python -m src.ingestion.pdf_cli download https://example.com/guide.pdf

# Preview PDF content
python -m src.ingestion.pdf_cli preview trading_guide.pdf --chars 1000

# List PDF files in directory
python -m src.ingestion.pdf_cli list pdfs/ --recursive
```

### CLI Command Reference

| Command | Description | Options |
|---------|-------------|---------|
| `process` | Process single PDF file | `--format` (json/summary/text) |
| `batch` | Process directory of PDFs | `--recursive`, `--concurrent`, `--format` |
| `download` | Download and process from URL | `--format` |
| `preview` | Show text preview | `--chars` |
| `list` | List PDF files in directory | `--recursive` |

## 🔧 Configuration

### PDFProcessor Configuration

```python
processor = PDFProcessor(
    max_file_size_mb=50  # Maximum file size to process
)
```

### PDFIngestionService Configuration

```python
service = PDFIngestionService(
    storage_dir="data/pdfs",           # Directory for file storage
    max_file_size_mb=50,               # Maximum file size
    allowed_file_types=['.pdf']        # Allowed file extensions
)
```

### Environment Variables

```bash
# Optional configuration via environment variables
TRADING_BOT_PDF_STORAGE_DIR=/opt/data/pdfs
TRADING_BOT_MAX_PDF_SIZE_MB=100
```

## 📊 Data Models

### IngestionSourceModel

The PDF processor returns data in the `IngestionSourceModel` format:

```python
{
    "id": "uuid4-string",
    "source_type": "pdf",
    "source_url": "https://example.com/guide.pdf",
    "local_path": "/path/to/stored/file.pdf",
    "title": "Trading Strategy Guide",
    "author": "Expert Trader",
    "description": "Comprehensive trading strategies",
    "tags": ["scalping", "risk-management", "market-structure"],
    "status": "completed",  # or "error"
    "error_message": "",
    "extracted_text": "Full extracted text content...",
    "extracted_images": [
        {
            "page": 1,
            "index": 0,
            "width": 800,
            "height": 600,
            # ... more image metadata
        }
    ],
    "created_at": "2026-02-10T12:00:00Z",
    "processed_at": "2026-02-10T12:01:30Z"
}
```

## 🏷️ Trading Keyword Extraction

The processor automatically identifies trading-related terms:

### Supported Categories

- **Entry Patterns**: liquidity engulf, LE candle, small wick, breakout, fakeout
- **Market Structure**: BOS, CHoCH, support, resistance, supply zone, demand zone
- **Risk Management**: stop loss, take profit, position sizing, R multiple
- **Timeframes**: 1m, 5m, 15m, H4, daily, HTF, LTF
- **Concepts**: confluence, bias, trend, momentum, reversal

### Example

```python
text = """
This guide covers liquidity engulf candles and proper risk management.
We'll discuss higher timeframe bias and confluence areas for entries.
"""

keywords = processor.extract_trading_keywords(text)
# Returns: ["liquidity engulf", "risk management", "higher timeframe", "confluence"]
```

## 🛡️ Error Handling

The PDF processor includes comprehensive error handling:

```python
try:
    result = await processor.process_pdf("corrupted.pdf")
except PDFProcessingError as e:
    print(f"Processing failed: {e}")
    # Handle error appropriately

# Check result status
if result.status == "error":
    print(f"Processing failed: {result.error_message}")
else:
    print(f"Successfully extracted {len(result.extracted_text)} characters")
```

### Common Error Types

| Error | Cause | Solution |
|-------|--------|----------|
| `File does not exist` | Invalid file path | Check file path |
| `File too large` | Exceeds size limit | Reduce file size or increase limit |
| `Invalid file type` | Wrong extension | Ensure .pdf extension |
| `Not a valid PDF` | Corrupted/invalid file | Use different PDF file |
| `Extraction failed` | PDF parsing error | Try different extraction backend |

## 📈 Performance

### Processing Metrics

The service tracks detailed performance metrics:

```python
stats = await service.get_processing_stats()

{
    "total_processed": 150,
    "successful_processing": 142,
    "failed_processing": 8,
    "success_rate": 94.7,
    "total_characters_extracted": 2840000,
    "total_images_found": 89,
    "average_characters_per_pdf": 20000,
    "average_images_per_pdf": 0.6
}
```

### Performance Tips

- **Batch Processing**: Use `batch_process_directory()` for multiple files
- **Concurrency**: Adjust `max_concurrent` based on system resources
- **File Size**: Keep PDFs under 50MB for optimal performance
- **Cleanup**: Regularly clean up old files with `cleanup_storage()`

## 🧪 Testing

### Running Tests

```bash
# Run all PDF processor tests
pytest tests/test_pdf_processor.py -v

# Run specific test class
pytest tests/test_pdf_processor.py::TestPDFProcessor -v

# Run integration tests (requires sample PDFs)
pytest tests/test_pdf_processor.py -m integration
```

### Test Coverage

- **Unit Tests**: Core functionality testing
- **Integration Tests**: End-to-end workflow testing
- **Mock Tests**: Testing without PDF dependencies
- **Error Tests**: Error handling validation

## 🔄 Integration with Trading Bot

### Workflow Integration

1. **Content Ingestion**: PDF processor extracts text and metadata
2. **LLM Analysis**: Extracted content feeds into Claude for strategy extraction
3. **Knowledge Base**: Processed content stored in PostgreSQL + pgvector
4. **Strategy Learning**: Bot learns trading patterns from content

### Example Integration

```python
from src.ingestion import PDFIngestionService
from src.knowledge import StrategyExtractor

# Process PDF
service = await create_pdf_service()
pdf_result = await service.process_existing_pdf("trading_guide.pdf")

# Extract strategies using LLM
extractor = StrategyExtractor()
strategies = await extractor.extract_strategies(pdf_result.extracted_text)

# Store in knowledge base
for strategy in strategies:
    await knowledge_repo.store_strategy(strategy)
```

## 🔧 Dependencies

### Required Packages

```txt
PyMuPDF>=1.23.0       # Primary PDF processing
PyPDF2>=3.0.0         # Fallback PDF processing
aiohttp>=3.9.0        # HTTP client for downloads
pydantic>=2.4.0       # Data validation
```

### Optional Dependencies

```txt
Pillow>=9.0.0         # Image processing
python-magic>=0.4.0   # File type detection
```

## 🚀 Future Enhancements

### Planned Features

- **OCR Support**: Extract text from scanned PDFs
- **Image Analysis**: Analyze charts and diagrams in PDFs
- **Table Extraction**: Extract trading data from tables
- **Multi-language**: Support for non-English trading content
- **Content Classification**: Automatic content type detection
- **Semantic Search**: Vector-based content search

### Performance Improvements

- **Streaming Processing**: Handle very large PDFs
- **Caching**: Cache extraction results
- **Background Processing**: Queue-based processing
- **Compression**: Store extracted content efficiently

## 📝 Contributing

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/test_pdf_processor.py

# Run linting
black src/ingestion/
flake8 src/ingestion/
```

### Code Style

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations
- **Docstrings**: Document all functions and classes
- **Error Handling**: Comprehensive error handling
- **Testing**: Write tests for new features

## 📄 License

This PDF processor is part of the Hyperliquid Trading Bot Suite and follows the same licensing terms.

---

For more information, see the main project documentation or contact the development team.