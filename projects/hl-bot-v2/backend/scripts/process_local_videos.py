#!/usr/bin/env python3
"""Process local video files to extract frames.

Usage:
    python scripts/process_local_videos.py /path/to/video.mp4
    python scripts/process_local_videos.py /path/to/videos/  # Process all videos in dir

Frames are saved to /tmp/extracted_frames/<video_name>/
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hl_bot.services.ingestion import YouTubeProcessor


async def main():
    if len(sys.argv) < 2:
        print("Usage: python process_local_videos.py <video_file_or_dir>")
        print("\nExamples:")
        print("  python process_local_videos.py /tmp/course_videos/day1.mp4")
        print("  python process_local_videos.py /tmp/course_videos/")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    frame_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60  # Default: 1 frame/min

    processor = YouTubeProcessor(
        cache_dir=Path("/tmp/extracted_frames"),
        frame_interval=frame_interval,
    )

    if input_path.is_file():
        # Single video
        print(f"Processing: {input_path.name}")
        info = await processor.process_local_video(input_path, frame_interval=frame_interval)
        print(f"✅ Extracted {len(info.frames)} frames")
        print(f"   Saved to: {info.frames[0].parent if info.frames else 'N/A'}")

    elif input_path.is_dir():
        # Directory of videos
        print(f"Processing all videos in: {input_path}")
        videos = await processor.process_local_videos(input_path, frame_interval=frame_interval)
        
        total_frames = sum(len(v.frames) for v in videos)
        print(f"\n✅ Processed {len(videos)} videos, {total_frames} total frames")
        
        for v in videos:
            print(f"   {v.title}: {len(v.frames)} frames")
            if v.frames:
                print(f"      → {v.frames[0].parent}")

    else:
        print(f"❌ Not found: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
