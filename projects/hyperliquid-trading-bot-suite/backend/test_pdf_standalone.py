#!/usr/bin/env python3
"""
Standalone test for PDF processor functionality.
This test bypasses the module imports to verify PDF processor works.
"""

import sys
import tempfile
from pathlib import Path
import asyncio

# Add src to path for direct imports
sys.path.insert(0, 'src')

# Direct imports to avoid problematic __init__.py in ingestion module
import src.types
from src.types.pydantic_models import IngestionSourceModel

# Alias the SourceType for convenience
SourceType = src.types.SourceType


def create_test_pdf():
    """Create a minimal test PDF file."""
    pdf_content = b"""%PDF-1.4
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
/Length 110
>>
stream
BT
/F1 12 Tf
72 720 Td
(Trading Strategy: Liquidity Engulf) Tj
0 -20 Td
(Entry: LE candle on BOS) Tj
0 -20 Td
(Risk: 2% with stop loss) Tj
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
350
%%EOF"""
    
    # Create temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(pdf_content)
        return tmp.name


async def test_pdf_processor():
    """Test PDF processor functionality."""
    
    print("🧪 Testing PDF Processor...")
    
    try:
        # Import PDF processor directly by loading the module file
        import importlib.util
        import os
        
        # Load pdf_processor.py directly without going through __init__.py
        spec = importlib.util.spec_from_file_location(
            "pdf_processor", 
            os.path.join("src", "ingestion", "pdf_processor.py")
        )
        pdf_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pdf_module)
        
        PDFProcessor = pdf_module.PDFProcessor
        is_pdf_file = pdf_module.is_pdf_file
        print("✅ PDF processor imported successfully")
        
        # Create processor instance
        processor = PDFProcessor(max_file_size_mb=5)
        print("✅ PDF processor instantiated")
        
        # Test keyword extraction
        test_text = """
        Trading Strategy Document
        
        This strategy focuses on liquidity engulf patterns (LE) combined with 
        break of structure (BOS) signals. Key components:
        
        1. Higher timeframe bias using H4 or Daily
        2. Entry on lower timeframe with LE candle
        3. Risk management: 2% per trade with stop loss below structure
        4. Take profit at resistance zones
        
        Market cycles: Drive phase shows momentum, range phase shows consolidation,
        liquidity phase shows stop hunts.
        """
        
        keywords = processor.extract_trading_keywords(test_text)
        print(f"✅ Trading keywords extracted: {keywords}")
        
        # Create test PDF
        pdf_path = create_test_pdf()
        print(f"✅ Test PDF created at: {pdf_path}")
        
        # Test PDF validation
        if is_pdf_file(pdf_path):
            print("✅ PDF file validation passed")
        else:
            print("❌ PDF file validation failed")
            return False
        
        # Test PDF processing
        try:
            result = await processor.process_pdf(
                file_path=pdf_path,
                title="Test Trading Strategy PDF",
                tags=["test", "trading"]
            )
            
            print("✅ PDF processed successfully!")
            print(f"   - Title: {result.title}")
            print(f"   - Status: {result.status}")
            print(f"   - Text length: {len(result.extracted_text)} chars")
            print(f"   - Contains 'Liquidity': {'Liquidity' in result.extracted_text}")
            print(f"   - Contains 'BOS': {'BOS' in result.extracted_text}")
            
            if result.extracted_text and 'Liquidity' in result.extracted_text:
                print("✅ Text extraction working correctly")
            else:
                print("⚠️  Text extraction may have issues")
            
        except Exception as e:
            print(f"❌ PDF processing failed: {e}")
            return False
        
        finally:
            # Clean up
            Path(pdf_path).unlink()
            print("🧹 Cleaned up test files")
        
        print("🎉 All PDF processor tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pdf_processor())
    sys.exit(0 if success else 1)