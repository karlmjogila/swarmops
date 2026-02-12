"""
Test script for the video pipeline.

This script demonstrates how to use the video pipeline to process YouTube content
for trading strategy extraction.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_pipeline import VideoPipelineManager, VideoPipelineConfig


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_video_pipeline():
    """Test the video pipeline with a sample YouTube video."""
    
    # Sample trading-related YouTube URLs for testing
    test_urls = [
        # Short educational trading video
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder - replace with actual trading video
        # Add more test URLs here
    ]
    
    # Configure pipeline for testing
    config = VideoPipelineConfig(
        frame_interval_seconds=15,  # Extract frames every 15 seconds for testing
        whisper_model="tiny",       # Use tiny model for faster processing during tests
        frame_quality="medium",
        max_video_duration=600,     # Limit to 10 minutes for testing
        enable_word_timestamps=True
    )
    
    manager = VideoPipelineManager(config)
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Processing URL: {url}")
        print(f"{'='*60}")
        
        try:
            # Process the video
            result = manager.process_youtube_url(url)
            
            # Print results
            print(f"Status: {result.status}")
            print(f"Title: {result.title}")
            print(f"Author: {result.author}")
            print(f"Description Length: {len(result.description)} characters")
            print(f"Extracted Text Length: {len(result.extracted_text)} characters")
            print(f"Number of Frames: {len(result.extracted_images)}")
            print(f"Tags: {', '.join(result.tags)}")
            
            if result.error_message:
                print(f"Error: {result.error_message}")
            
            # Show sample transcript
            if result.extracted_text:
                print(f"\nSample Transcript (first 200 chars):")
                print(result.extracted_text[:200] + "..." if len(result.extracted_text) > 200 else result.extracted_text)
            
            # Show frame information
            if result.extracted_images:
                print(f"\nFrame Information:")
                for i, frame in enumerate(result.extracted_images[:3]):  # Show first 3 frames
                    print(f"  Frame {i+1}: t={frame['timestamp']}s, size={frame['width']}x{frame['height']}")
                    if frame.get('context_text'):
                        context = frame['context_text'][:100]
                        print(f"    Context: {context}..." if len(frame['context_text']) > 100 else f"    Context: {context}")
                        
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            import traceback
            traceback.print_exc()


def demo_usage():
    """Demonstrate basic usage patterns."""
    
    print("Video Pipeline Demo")
    print("==================")
    
    # Basic usage
    print("\n1. Basic Usage:")
    print("from ingestion.video_pipeline import VideoPipelineManager")
    print("manager = VideoPipelineManager()")
    print("result = manager.process_youtube_url('https://youtube.com/watch?v=...')")
    
    # Custom configuration
    print("\n2. Custom Configuration:")
    print("from ingestion.video_pipeline import VideoPipelineConfig, VideoPipelineManager")
    print("config = VideoPipelineConfig(")
    print("    frame_interval_seconds=20,")
    print("    whisper_model='base',")
    print("    frame_quality='high'")
    print(")")
    print("manager = VideoPipelineManager(config)")
    
    # Advanced usage
    print("\n3. Advanced Usage with Context Manager:")
    print("from ingestion.video_pipeline import VideoPipeline")
    print("with VideoPipeline() as pipeline:")
    print("    result = pipeline.process_video_url(url)")
    print("    # Temporary files are automatically cleaned up")
    
    # Expected output structure
    print("\n4. Expected Output Structure:")
    print("result = IngestionSourceModel(")
    print("    source_type=SourceType.VIDEO,")
    print("    source_url='...',")
    print("    title='Video Title',")
    print("    author='Channel Name',")
    print("    extracted_text='Full transcript...',")
    print("    extracted_images=[{")
    print("        'timestamp': 10.0,")
    print("        'path': '/tmp/frame_10.0s.jpg',")
    print("        'context_text': 'Relevant transcript...'")
    print("    }, ...],")
    print("    tags=['duration:300s', 'frames:30', 'segments:15']")
    print(")")


if __name__ == "__main__":
    setup_logging()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_usage()
    elif len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        # Process specific URL
        url = sys.argv[1]
        config = VideoPipelineConfig(whisper_model="tiny")
        manager = VideoPipelineManager(config)
        result = manager.process_youtube_url(url)
        print(f"Processed: {result.title}")
        print(f"Status: {result.status}")
    else:
        print("Usage:")
        print("  python video_pipeline_test.py --demo           # Show usage examples")
        print("  python video_pipeline_test.py <youtube_url>    # Process specific URL")
        print("  python video_pipeline_test.py                 # Run full test suite")
        print()
        test_video_pipeline()