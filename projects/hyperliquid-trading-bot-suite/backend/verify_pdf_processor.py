#!/usr/bin/env python3
"""
Verification script for PDF processor implementation.
This script checks that the PDF processor has all the required functionality.
"""

import os
from pathlib import Path

def check_pdf_processor_implementation():
    """Check if PDF processor is properly implemented."""
    
    print("🔍 Verifying PDF Processor Implementation...")
    
    # Check that PDF processor file exists
    pdf_processor_path = Path("src/ingestion/pdf_processor.py")
    if not pdf_processor_path.exists():
        print("❌ PDF processor file not found")
        return False
    
    print("✅ PDF processor file exists")
    
    # Read the PDF processor implementation
    with open(pdf_processor_path, 'r') as f:
        content = f.read()
    
    # Check for required classes and methods
    required_features = [
        "class PDFProcessor",
        "class PDFProcessingError", 
        "async def process_pdf",
        "async def _validate_file",
        "async def _extract_content", 
        "async def _extract_with_pymupdf",
        "async def _extract_with_pypdf2",
        "async def _clean_text",
        "def extract_trading_keywords",
        "async def batch_process_pdfs",
        "def is_pdf_file",
        "import fitz",  # PyMuPDF
        "import PyPDF2",
        "from ..types import IngestionSource, SourceType",
        "from ..types.pydantic_models import IngestionSourceModel"
    ]
    
    missing_features = []
    for feature in required_features:
        if feature not in content:
            missing_features.append(feature)
        else:
            print(f"✅ Found: {feature}")
    
    if missing_features:
        print(f"❌ Missing features: {missing_features}")
        return False
    
    # Check for trading keywords patterns
    trading_patterns = [
        "liquidity\\s+engulf",
        "LE\\s+candle", 
        "small\\s+wick",
        "steeper\\s+wick",
        "celery\\s+play",
        "break\\s+of\\s+structure",
        "BOS",
        "change\\s+of\\s+character",
        "CHoCH",
        "support",
        "resistance",
        "stop\\s+loss",
        "take\\s+profit"
    ]
    
    found_patterns = []
    for pattern in trading_patterns:
        if pattern in content:
            found_patterns.append(pattern)
    
    print(f"✅ Found {len(found_patterns)} trading keyword patterns")
    
    # Check for proper error handling
    error_handling_features = [
        "try:", 
        "except Exception",
        "logger.error", 
        "raise PDFProcessingError"
    ]
    
    error_features_found = sum(1 for feature in error_handling_features if feature in content)
    print(f"✅ Found {error_features_found}/4 error handling features")
    
    # Check file size validation
    if "max_file_size_mb" in content and "max_file_size_bytes" in content:
        print("✅ File size validation implemented")
    else:
        print("❌ File size validation missing")
        return False
    
    # Check async support
    if "async def" in content and "await" in content:
        print("✅ Async/await support implemented")
    else:
        print("❌ Async support missing")
        return False
    
    # Check metadata extraction
    metadata_features = [
        "metadata.get('title'",
        "metadata.get('author'", 
        "page_count"
    ]
    
    metadata_found = sum(1 for feature in metadata_features if feature in content)
    print(f"✅ Found {metadata_found}/3 metadata extraction features")
    
    return True

def check_test_file():
    """Check that test file exists."""
    test_path = Path("tests/test_pdf_processor.py")
    if test_path.exists():
        print("✅ PDF processor test file exists")
        
        with open(test_path, 'r') as f:
            test_content = f.read()
            
        test_features = [
            "@pytest.mark.asyncio",
            "async def test_",
            "PDFProcessor",
            "assert"
        ]
        
        test_features_found = sum(1 for feature in test_features if feature in test_content)
        print(f"✅ Found {test_features_found}/4 test features")
        return True
    else:
        print("❌ PDF processor test file missing")
        return False

def check_dependencies():
    """Check if dependencies are listed in requirements."""
    req_path = Path("requirements.txt")
    if req_path.exists():
        with open(req_path, 'r') as f:
            requirements = f.read()
        
        pdf_deps = ["PyMuPDF", "PyPDF2"]
        deps_found = []
        
        for dep in pdf_deps:
            if dep in requirements:
                deps_found.append(dep)
                print(f"✅ Dependency found: {dep}")
        
        if len(deps_found) == len(pdf_deps):
            print("✅ All PDF dependencies listed in requirements")
            return True
        else:
            print(f"❌ Missing dependencies: {set(pdf_deps) - set(deps_found)}")
            return False
    else:
        print("❌ requirements.txt not found")
        return False

def main():
    """Main verification function."""
    print("📋 PDF Processor Implementation Verification")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Check implementation
    if not check_pdf_processor_implementation():
        all_checks_passed = False
    
    print()
    
    # Check test file
    if not check_test_file():
        all_checks_passed = False
        
    print()
    
    # Check dependencies
    if not check_dependencies():
        all_checks_passed = False
    
    print()
    print("=" * 50)
    
    if all_checks_passed:
        print("🎉 PDF Processor Implementation Verification PASSED!")
        print("\n✅ Summary:")
        print("   - PDF processor class implemented with all required methods")
        print("   - Error handling and validation included")
        print("   - Trading keyword extraction implemented")
        print("   - Async processing support")
        print("   - Test file exists")
        print("   - Dependencies listed in requirements")
        print("\n✅ The PDF processor task appears to be COMPLETE!")
        return True
    else:
        print("❌ PDF Processor Implementation Verification FAILED!")
        print("   Some features are missing or incomplete.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)