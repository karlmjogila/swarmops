#!/usr/bin/env python3
"""Command-line interface for PDF processing.

This script provides a CLI for testing and using the PDF processor
independently of the main application.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from .pdf_service import PDFIngestionService, create_pdf_service, process_pdf_from_url
from .pdf_processor import get_pdf_files_from_directory, extract_text_preview


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_single_file(file_path: str, output_format: str = 'json') -> None:
    """Process a single PDF file."""
    try:
        service = await create_pdf_service()
        result = await service.process_existing_pdf(file_path)
        
        if output_format == 'json':
            print(json.dumps(result.model_dump(), indent=2, default=str))
        elif output_format == 'summary':
            print(f"Title: {result.title}")
            print(f"Author: {result.author}")
            print(f"Status: {result.status}")
            print(f"Characters extracted: {len(result.extracted_text)}")
            print(f"Images found: {len(result.extracted_images)}")
            print(f"Tags: {', '.join(result.tags)}")
            if result.error_message:
                print(f"Error: {result.error_message}")
        elif output_format == 'text':
            print(result.extracted_text)
        
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        sys.exit(1)


async def process_directory(
    directory: str,
    recursive: bool = False,
    output_format: str = 'summary',
    max_concurrent: int = 3
) -> None:
    """Process all PDF files in a directory."""
    try:
        service = await create_pdf_service()
        results = await service.batch_process_directory(
            directory=directory,
            recursive=recursive,
            max_concurrent=max_concurrent
        )
        
        if output_format == 'json':
            output = [result.model_dump() for result in results]
            print(json.dumps(output, indent=2, default=str))
            
        elif output_format == 'summary':
            print(f"Processed {len(results)} PDF files:")
            print("-" * 50)
            
            successful = 0
            failed = 0
            
            for result in results:
                status_icon = "✅" if result.status == "completed" else "❌"
                print(f"{status_icon} {result.title or Path(result.local_path).stem}")
                
                if result.status == "completed":
                    successful += 1
                    print(f"    Characters: {len(result.extracted_text)}")
                    print(f"    Images: {len(result.extracted_images)}")
                    if result.tags:
                        print(f"    Tags: {', '.join(result.tags[:5])}...")
                else:
                    failed += 1
                    print(f"    Error: {result.error_message}")
                
                print()
            
            print(f"Summary: {successful} successful, {failed} failed")
            
            # Show service statistics
            stats = await service.get_processing_stats()
            print(f"Success rate: {stats['success_rate']:.1f}%")
            
    except Exception as e:
        logger.error(f"Failed to process directory {directory}: {e}")
        sys.exit(1)


async def download_and_process(url: str, output_format: str = 'summary') -> None:
    """Download and process a PDF from URL."""
    try:
        service = await create_pdf_service()
        result = await process_pdf_from_url(service, url)
        
        if output_format == 'json':
            print(json.dumps(result.model_dump(), indent=2, default=str))
        elif output_format == 'summary':
            print(f"Downloaded and processed: {url}")
            print(f"Title: {result.title}")
            print(f"Author: {result.author}")
            print(f"Status: {result.status}")
            print(f"Characters extracted: {len(result.extracted_text)}")
            print(f"Tags: {', '.join(result.tags)}")
            if result.error_message:
                print(f"Error: {result.error_message}")
        elif output_format == 'text':
            print(result.extracted_text)
            
    except Exception as e:
        logger.error(f"Failed to download and process {url}: {e}")
        sys.exit(1)


async def preview_file(file_path: str, max_chars: int = 500) -> None:
    """Show a text preview of a PDF file."""
    try:
        preview = await extract_text_preview(file_path, max_chars)
        print(f"Preview of {file_path}:")
        print("-" * 50)
        print(preview)
        
    except Exception as e:
        logger.error(f"Failed to preview {file_path}: {e}")
        sys.exit(1)


async def list_pdfs_in_directory(directory: str, recursive: bool = False) -> None:
    """List all PDF files in a directory."""
    try:
        pdf_files = get_pdf_files_from_directory(directory, recursive)
        
        if not pdf_files:
            print(f"No PDF files found in {directory}")
            return
        
        print(f"Found {len(pdf_files)} PDF files:")
        for pdf_file in pdf_files:
            file_size = Path(pdf_file).stat().st_size / (1024 * 1024)
            print(f"  {pdf_file} ({file_size:.1f} MB)")
            
    except Exception as e:
        logger.error(f"Failed to list PDFs in {directory}: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PDF Processor CLI for Hyperliquid Trading Bot Suite'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process single file
    process_parser = subparsers.add_parser('process', help='Process a single PDF file')
    process_parser.add_argument('file', help='Path to PDF file')
    process_parser.add_argument(
        '--format', 
        choices=['json', 'summary', 'text'], 
        default='summary',
        help='Output format'
    )
    
    # Process directory
    batch_parser = subparsers.add_parser('batch', help='Process all PDFs in a directory')
    batch_parser.add_argument('directory', help='Directory containing PDF files')
    batch_parser.add_argument('--recursive', action='store_true', help='Search recursively')
    batch_parser.add_argument(
        '--format', 
        choices=['json', 'summary'], 
        default='summary',
        help='Output format'
    )
    batch_parser.add_argument(
        '--concurrent', 
        type=int, 
        default=3, 
        help='Maximum concurrent processing tasks'
    )
    
    # Download and process
    download_parser = subparsers.add_parser('download', help='Download and process PDF from URL')
    download_parser.add_argument('url', help='URL of PDF to download')
    download_parser.add_argument(
        '--format', 
        choices=['json', 'summary', 'text'], 
        default='summary',
        help='Output format'
    )
    
    # Preview file
    preview_parser = subparsers.add_parser('preview', help='Show text preview of PDF file')
    preview_parser.add_argument('file', help='Path to PDF file')
    preview_parser.add_argument(
        '--chars', 
        type=int, 
        default=500, 
        help='Maximum characters to show'
    )
    
    # List files
    list_parser = subparsers.add_parser('list', help='List PDF files in directory')
    list_parser.add_argument('directory', help='Directory to search')
    list_parser.add_argument('--recursive', action='store_true', help='Search recursively')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'process':
        asyncio.run(process_single_file(args.file, args.format))
    elif args.command == 'batch':
        asyncio.run(process_directory(
            args.directory, 
            args.recursive, 
            args.format, 
            args.concurrent
        ))
    elif args.command == 'download':
        asyncio.run(download_and_process(args.url, args.format))
    elif args.command == 'preview':
        asyncio.run(preview_file(args.file, args.chars))
    elif args.command == 'list':
        asyncio.run(list_pdfs_in_directory(args.directory, args.recursive))


if __name__ == '__main__':
    main()