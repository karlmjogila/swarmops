#!/usr/bin/env python3
"""Example usage of the PDF processor.

This script demonstrates how to:
1. Process a PDF file
2. Extract text and images
3. Handle OCR for scanned PDFs
4. Extract tables from PDFs
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hl_bot.services.ingestion.pdf_processor import PDFProcessor


async def main():
    """Run PDF processor examples."""
    print("=" * 80)
    print("PDF Processor Example")
    print("=" * 80)

    # Initialize processor
    processor = PDFProcessor(
        enable_ocr=True,
        extract_images=True,
        min_image_size=(100, 100),
        max_pages=500,
    )

    print(f"\n✓ Initialized PDF processor")
    print(f"  Cache dir: {processor._cache_dir}")
    print(f"  OCR enabled: {processor._enable_ocr}")
    print(f"  Max pages: {processor._max_pages}")

    # Check if a PDF file was provided as argument
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        if not pdf_path.exists():
            print(f"\n✗ Error: File not found: {pdf_path}")
            return

        print(f"\n📄 Processing PDF: {pdf_path.name}")
        print("-" * 80)

        try:
            # Process the PDF
            result = await processor.process_file(pdf_path)

            # Display metadata
            print(f"\n📊 Metadata:")
            print(f"  Filename: {result.filename}")
            print(f"  Title: {result.title or '(none)'}")
            print(f"  Author: {result.author or '(none)'}")
            print(f"  Pages: {result.num_pages}")

            # Display page information
            print(f"\n📑 Pages:")
            for page in result.pages:
                text_len = len(page.text)
                ocr_len = len(page.ocr_text)
                img_count = len(page.images)

                status = "✓ text" if page.has_text else "✗ no text"
                if ocr_len > 0:
                    status += f" (OCR: {ocr_len} chars)"

                print(
                    f"  Page {page.page_num:3d}: {text_len:6d} chars, "
                    f"{img_count} images, {status}"
                )

            # Display text preview
            full_text = result.get_full_text()
            print(f"\n📝 Text Preview (first 500 chars):")
            print("-" * 80)
            print(full_text[:500])
            if len(full_text) > 500:
                print("...")

            # Display image information
            all_images = result.get_all_images()
            if all_images:
                print(f"\n🖼️  Extracted Images ({len(all_images)}):")
                for img_path in all_images[:10]:  # Show first 10
                    print(f"  - {img_path.name}")
                if len(all_images) > 10:
                    print(f"  ... and {len(all_images) - 10} more")

            # Try to extract tables
            print(f"\n📊 Extracting tables...")
            tables = await processor.extract_tables(pdf_path)
            if tables:
                print(f"  Found {len(tables)} table(s)")
                for i, table in enumerate(tables[:3], 1):  # Show first 3
                    print(f"\n  Table {i}: {len(table)} rows x {len(table[0]) if table else 0} cols")
                    if table:
                        # Show first row (header)
                        print(f"    Header: {table[0]}")
            else:
                print(f"  No tables found")

            print(f"\n✓ Processing complete!")

        except Exception as e:
            print(f"\n✗ Error processing PDF: {e}")
            import traceback

            traceback.print_exc()

    else:
        # Demo mode - create a sample PDF
        print("\n💡 Usage: python pdf_processor_example.py <path-to-pdf>")
        print("\nNo PDF provided, showing example output format:")
        print("-" * 80)
        print("""
Example output for a trading strategy PDF:

📊 Metadata:
  Filename: trading_strategy.pdf
  Title: Advanced Trading Strategies
  Author: Don Vo
  Pages: 25

📑 Pages:
  Page   1:   1245 chars, 2 images, ✓ text
  Page   2:   987 chars, 1 images, ✓ text
  Page   3:   1534 chars, 3 images, ✓ text
  ...

📝 Text Preview:
Support and Resistance Trading Strategy

This strategy focuses on identifying key levels where price is likely
to react. Look for confluence of multiple factors:

1. Multi-timeframe support/resistance alignment
2. LE candles at key levels
3. Market structure breaks (BOS/CHoCH)
4. Order blocks and fair value gaps

Entry Rules:
- Wait for price to reach key level
- Look for LE candle formation
- Confirm with higher timeframe bias
...

🖼️  Extracted Images (8):
  - page_1_img_0.png (chart screenshot)
  - page_3_img_0.png (pattern diagram)
  - page_5_img_0.png (entry example)
  ...

📊 Extracting tables...
  Found 2 table(s)

  Table 1: 5 rows x 4 cols
    Header: ['Setup', 'Win Rate', 'Avg R', 'Notes']

✓ Processing complete!
        """)

    # Cache cleanup demo
    print("\n🧹 Cache Management:")
    count = await processor.cleanup_cache(max_age_days=7)
    print(f"  Cleaned up {count} old cache directories (>7 days)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
