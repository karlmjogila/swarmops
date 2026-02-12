"""Video pipeline for extracting frames and transcripts from YouTube videos."""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import aiofiles
import ffmpeg
import imagehash
import whisper
import yt_dlp
from PIL import Image

from ..types import IngestionSource, SourceType, VideoFrame

# Configure logging
logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Custom exception for video processing errors."""
    pass


class YouTubeVideoProcessor:
    """Handles YouTube video download and initial processing."""
    
    def __init__(self, output_dir: str = "/tmp/video_ingestion"):
        """Initialize the YouTube video processor.
        
        Args:
            output_dir: Directory to store downloaded videos and extracted content
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # yt-dlp configuration
        self.ytdl_opts = {
            'format': 'best[height<=720]/best',  # Limit quality for processing speed
            'outtmpl': str(self.output_dir / '%(id)s.%(ext)s'),
            'writeinfojson': True,
            'writesubtitles': False,  # We'll use Whisper instead
            'writeautomaticsub': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'extractflat': False,
        }
    
    async def download_video(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """Download video from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Tuple of (video_file_path, video_info_dict)
            
        Raises:
            VideoProcessingError: If download fails
        """
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id', 'unknown')
                
                logger.info(f"Downloading video: {info.get('title', 'Unknown')} (ID: {video_id})")
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                video_files = list(self.output_dir.glob(f"{video_id}.*"))
                video_files = [f for f in video_files if not f.name.endswith('.info.json')]
                
                if not video_files:
                    raise VideoProcessingError(f"No video file found after download for ID: {video_id}")
                
                video_path = str(video_files[0])
                
                logger.info(f"Successfully downloaded video to: {video_path}")
                return video_path, info
                
        except Exception as e:
            logger.error(f"Failed to download video from {url}: {str(e)}")
            raise VideoProcessingError(f"Download failed: {str(e)}") from e
    
    async def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.error(f"Failed to get video duration: {str(e)}")
            return 0.0


class AudioTranscriber:
    """Handles audio transcription using OpenAI Whisper."""
    
    def __init__(self, model_name: str = "base"):
        """Initialize the transcriber.
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.model = None
    
    def _load_model(self):
        """Load the Whisper model if not already loaded."""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
    
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio from video file.
        
        Args:
            video_path: Path to input video file
            output_path: Path for output audio file
            
        Returns:
            Path to extracted audio file
        """
        try:
            # Use ffmpeg to extract audio
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar=16000)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True)
            )
            
            logger.info(f"Extracted audio to: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error extracting audio: {e.stderr.decode()}")
            raise VideoProcessingError(f"Audio extraction failed: {e.stderr.decode()}")
        except Exception as e:
            logger.error(f"Unexpected error extracting audio: {str(e)}")
            raise VideoProcessingError(f"Audio extraction failed: {str(e)}")
    
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcription result with word-level timestamps
        """
        try:
            self._load_model()
            
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Run transcription in a separate thread to avoid blocking
            def _transcribe():
                return self.model.transcribe(
                    audio_path, 
                    word_timestamps=True,
                    verbose=False
                )
            
            # Run in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _transcribe)
            
            logger.info(f"Transcription completed. Found {len(result.get('segments', []))} segments")
            return result
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {str(e)}")
            raise VideoProcessingError(f"Transcription failed: {str(e)}") from e


class FrameExtractor:
    """Handles video frame extraction and deduplication."""
    
    def __init__(self, frame_interval: int = 10):
        """Initialize frame extractor.
        
        Args:
            frame_interval: Interval in seconds between extracted frames
        """
        self.frame_interval = frame_interval
    
    async def extract_frames(self, video_path: str, output_dir: str, duration: float) -> List[str]:
        """Extract frames from video at specified intervals.
        
        Args:
            video_path: Path to input video file
            output_dir: Directory to save extracted frames
            duration: Video duration in seconds
            
        Returns:
            List of paths to extracted frame images
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            frame_paths = []
            
            # Calculate number of frames to extract
            num_frames = int(duration // self.frame_interval) + 1
            
            logger.info(f"Extracting {num_frames} frames at {self.frame_interval}s intervals")
            
            for i in range(num_frames):
                timestamp = i * self.frame_interval
                if timestamp >= duration:
                    break
                
                frame_filename = f"frame_{timestamp:06d}.jpg"
                frame_path = output_path / frame_filename
                
                try:
                    # Extract frame at specific timestamp
                    (
                        ffmpeg
                        .input(video_path, ss=timestamp)
                        .output(str(frame_path), vframes=1, q=2)
                        .overwrite_output()
                        .run(quiet=True, capture_stdout=True)
                    )
                    
                    frame_paths.append(str(frame_path))
                    
                except ffmpeg.Error as e:
                    logger.warning(f"Failed to extract frame at {timestamp}s: {e.stderr.decode()}")
                    continue
            
            logger.info(f"Successfully extracted {len(frame_paths)} frames")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Failed to extract frames: {str(e)}")
            raise VideoProcessingError(f"Frame extraction failed: {str(e)}") from e
    
    async def calculate_perceptual_hashes(self, frame_paths: List[str]) -> Dict[str, str]:
        """Calculate perceptual hashes for frame deduplication.
        
        Args:
            frame_paths: List of frame file paths
            
        Returns:
            Dictionary mapping frame_path to perceptual_hash
        """
        hashes = {}
        
        for frame_path in frame_paths:
            try:
                # Load image and calculate perceptual hash
                with Image.open(frame_path) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Calculate hash using dhash (difference hash)
                    hash_value = str(imagehash.dhash(img))
                    hashes[frame_path] = hash_value
                    
            except Exception as e:
                logger.warning(f"Failed to calculate hash for {frame_path}: {str(e)}")
                hashes[frame_path] = "error"
        
        logger.info(f"Calculated perceptual hashes for {len(hashes)} frames")
        return hashes
    
    def deduplicate_frames(self, frame_hashes: Dict[str, str], similarity_threshold: int = 5) -> List[str]:
        """Remove duplicate/similar frames based on perceptual hashes.
        
        Args:
            frame_hashes: Dictionary mapping frame_path to perceptual_hash
            similarity_threshold: Hamming distance threshold for considering frames similar
            
        Returns:
            List of unique frame paths
        """
        unique_frames = []
        seen_hashes = []
        
        for frame_path, hash_str in frame_hashes.items():
            if hash_str == "error":
                continue
            
            try:
                current_hash = imagehash.hex_to_hash(hash_str)
                
                # Check if this frame is similar to any previously seen frame
                is_duplicate = False
                for seen_hash in seen_hashes:
                    hamming_distance = current_hash - seen_hash
                    if hamming_distance <= similarity_threshold:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_frames.append(frame_path)
                    seen_hashes.append(current_hash)
                else:
                    # Remove duplicate frame file
                    try:
                        os.remove(frame_path)
                    except OSError:
                        pass
                        
            except Exception as e:
                logger.warning(f"Error processing hash for {frame_path}: {str(e)}")
                continue
        
        logger.info(f"Deduplicated frames: {len(frame_hashes)} -> {len(unique_frames)}")
        return unique_frames


class TranscriptFrameCorrelator:
    """Correlates transcript segments with video frames."""
    
    @staticmethod
    def correlate_transcript_with_frames(
        transcript_result: Dict[str, Any], 
        frame_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate transcript segments with extracted frames.
        
        Args:
            transcript_result: Whisper transcription result
            frame_data: List of frame data with timestamps
            
        Returns:
            List of correlated frame-transcript segments
        """
        correlated_data = []
        
        # Get transcript segments
        segments = transcript_result.get('segments', [])
        
        for frame in frame_data:
            frame_timestamp = frame['timestamp_seconds']
            
            # Find the closest transcript segment(s)
            relevant_segments = []
            
            for segment in segments:
                seg_start = segment.get('start', 0)
                seg_end = segment.get('end', 0)
                
                # Check if frame timestamp falls within segment
                if seg_start <= frame_timestamp <= seg_end:
                    relevant_segments.append(segment)
                # Also include segments that are close (within 30 seconds)
                elif abs(seg_start - frame_timestamp) <= 30 or abs(seg_end - frame_timestamp) <= 30:
                    relevant_segments.append(segment)
            
            # Combine relevant segment texts
            combined_text = " ".join([seg.get('text', '').strip() for seg in relevant_segments])
            
            # Get word-level timestamps for more precise correlation
            relevant_words = []
            for segment in relevant_segments:
                for word_info in segment.get('words', []):
                    word_start = word_info.get('start', 0)
                    if abs(word_start - frame_timestamp) <= 15:  # Within 15 seconds
                        relevant_words.append(word_info)
            
            correlated_entry = {
                'frame_path': frame['frame_path'],
                'frame_timestamp': frame_timestamp,
                'perceptual_hash': frame['perceptual_hash'],
                'transcript_text': combined_text,
                'relevant_segments': relevant_segments,
                'relevant_words': relevant_words,
                'segment_count': len(relevant_segments),
                'word_count': len(relevant_words)
            }
            
            correlated_data.append(correlated_entry)
        
        logger.info(f"Correlated {len(correlated_data)} frames with transcript data")
        return correlated_data


class VideoPipeline:
    """Main video processing pipeline."""
    
    def __init__(
        self, 
        output_dir: str = "/tmp/video_ingestion",
        whisper_model: str = "base",
        frame_interval: int = 10,
        similarity_threshold: int = 5
    ):
        """Initialize the video pipeline.
        
        Args:
            output_dir: Directory for temporary files and output
            whisper_model: Whisper model name for transcription
            frame_interval: Seconds between extracted frames
            similarity_threshold: Similarity threshold for frame deduplication
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.youtube_processor = YouTubeVideoProcessor(str(self.output_dir))
        self.transcriber = AudioTranscriber(whisper_model)
        self.frame_extractor = FrameExtractor(frame_interval)
        self.correlator = TranscriptFrameCorrelator()
        self.similarity_threshold = similarity_threshold
    
    async def process_video_url(self, url: str) -> Dict[str, Any]:
        """Process a YouTube video URL through the complete pipeline.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing all extracted data
            
        Raises:
            VideoProcessingError: If any step of the pipeline fails
        """
        start_time = time.time()
        
        # Create a unique directory for this video
        video_id = hashlib.md5(url.encode()).hexdigest()[:12]
        video_dir = self.output_dir / f"video_{video_id}"
        video_dir.mkdir(exist_ok=True)
        
        try:
            logger.info(f"Starting video pipeline for URL: {url}")
            
            # Step 1: Download video
            video_path, video_info = await self.youtube_processor.download_video(url)
            
            # Step 2: Get video duration
            duration = await self.youtube_processor.get_video_duration(video_path)
            
            # Step 3: Extract and transcribe audio
            audio_path = str(video_dir / "audio.wav")
            await self.transcriber.extract_audio(video_path, audio_path)
            transcript_result = await self.transcriber.transcribe_audio(audio_path)
            
            # Step 4: Extract frames
            frames_dir = video_dir / "frames"
            frame_paths = await self.frame_extractor.extract_frames(
                video_path, str(frames_dir), duration
            )
            
            # Step 5: Calculate perceptual hashes and deduplicate
            frame_hashes = await self.frame_extractor.calculate_perceptual_hashes(frame_paths)
            unique_frame_paths = self.frame_extractor.deduplicate_frames(
                frame_hashes, self.similarity_threshold
            )
            
            # Step 6: Prepare frame data for correlation
            frame_data = []
            for frame_path in unique_frame_paths:
                # Extract timestamp from filename
                filename = Path(frame_path).stem
                timestamp_str = filename.split('_')[-1]
                timestamp = float(timestamp_str) if timestamp_str.isdigit() else 0.0
                
                frame_data.append({
                    'frame_path': frame_path,
                    'timestamp_seconds': timestamp,
                    'perceptual_hash': frame_hashes.get(frame_path, '')
                })
            
            # Step 7: Correlate transcript with frames
            correlated_data = self.correlator.correlate_transcript_with_frames(
                transcript_result, frame_data
            )
            
            # Step 8: Prepare final result
            processing_time = time.time() - start_time
            
            result = {
                'video_info': video_info,
                'video_path': video_path,
                'audio_path': audio_path,
                'duration_seconds': duration,
                'transcript_result': transcript_result,
                'frames_extracted': len(frame_paths),
                'frames_unique': len(unique_frame_paths),
                'frame_data': frame_data,
                'correlated_data': correlated_data,
                'processing_time_seconds': processing_time,
                'output_directory': str(video_dir)
            }
            
            # Save result to JSON file
            result_path = video_dir / "pipeline_result.json"
            async with aiofiles.open(result_path, 'w') as f:
                # Create JSON-serializable copy
                json_result = {
                    'video_info': video_info,
                    'video_path': video_path,
                    'audio_path': audio_path,
                    'duration_seconds': duration,
                    'transcript_text': transcript_result.get('text', ''),
                    'frames_extracted': len(frame_paths),
                    'frames_unique': len(unique_frame_paths),
                    'processing_time_seconds': processing_time,
                    'correlated_frame_count': len(correlated_data)
                }
                await f.write(json.dumps(json_result, indent=2))
            
            logger.info(f"Video pipeline completed in {processing_time:.2f} seconds")
            logger.info(f"Extracted {len(unique_frame_paths)} unique frames from {len(frame_paths)} total frames")
            logger.info(f"Transcribed {len(transcript_result.get('segments', []))} segments")
            
            return result
            
        except Exception as e:
            logger.error(f"Video pipeline failed: {str(e)}")
            raise VideoProcessingError(f"Pipeline failed: {str(e)}") from e
        
        finally:
            # Cleanup temporary video file if it exists
            try:
                if 'video_path' in locals():
                    os.remove(video_path)
                    # Also remove info.json file
                    info_path = video_path.rsplit('.', 1)[0] + '.info.json'
                    if os.path.exists(info_path):
                        os.remove(info_path)
            except OSError:
                pass
    
    def create_ingestion_source(self, url: str, result: Dict[str, Any]) -> IngestionSource:
        """Create an IngestionSource object from pipeline results.
        
        Args:
            url: Original video URL
            result: Pipeline processing result
            
        Returns:
            IngestionSource object
        """
        video_info = result.get('video_info', {})
        
        # Extract frame information for the images field
        extracted_images = []
        for frame_info in result.get('frame_data', []):
            extracted_images.append({
                'path': frame_info['frame_path'],
                'timestamp': frame_info['timestamp_seconds'],
                'hash': frame_info['perceptual_hash'],
                'description': f"Frame at {frame_info['timestamp_seconds']}s"
            })
        
        source = IngestionSource(
            source_type=SourceType.VIDEO,
            source_url=url,
            local_path=result.get('output_directory', ''),
            title=video_info.get('title', 'Unknown Video'),
            author=video_info.get('uploader', 'Unknown'),
            description=video_info.get('description', '')[:500] if video_info.get('description') else '',
            tags=[
                f"duration:{result.get('duration_seconds', 0):.0f}s",
                f"frames:{result.get('frames_unique', 0)}",
                f"segments:{len(result.get('transcript_result', {}).get('segments', []))}"
            ],
            status="completed",
            extracted_text=result.get('transcript_result', {}).get('text', ''),
            extracted_images=extracted_images,
            processed_at=datetime.utcnow()
        )
        
        return source
    
    def create_video_frames(self, source_id: str, result: Dict[str, Any]) -> List[VideoFrame]:
        """Create VideoFrame objects from pipeline results.
        
        Args:
            source_id: ID of the associated IngestionSource
            result: Pipeline processing result
            
        Returns:
            List of VideoFrame objects
        """
        video_frames = []
        correlated_data = result.get('correlated_data', [])
        
        for frame_info in correlated_data:
            video_frame = VideoFrame(
                source_id=source_id,
                timestamp_seconds=frame_info['frame_timestamp'],
                frame_path=frame_info['frame_path'],
                perceptual_hash=frame_info['perceptual_hash'],
                description=frame_info['transcript_text'][:500] if frame_info['transcript_text'] else '',
                contains_chart=False,  # Would need separate analysis to determine
                analysis_confidence=min(frame_info['word_count'] / 10.0, 1.0)  # Simple heuristic
            )
            video_frames.append(video_frame)
        
        return video_frames


# Convenience functions
async def process_youtube_video(
    url: str,
    output_dir: str = "/tmp/video_ingestion",
    whisper_model: str = "base",
    frame_interval: int = 10
) -> Tuple[IngestionSource, List[VideoFrame], Dict[str, Any]]:
    """Process a YouTube video and return structured data objects.
    
    Args:
        url: YouTube video URL
        output_dir: Directory for temporary files
        whisper_model: Whisper model for transcription
        frame_interval: Seconds between extracted frames
        
    Returns:
        Tuple of (IngestionSource, List[VideoFrame], raw_result)
    """
    pipeline = VideoPipeline(
        output_dir=output_dir,
        whisper_model=whisper_model,
        frame_interval=frame_interval
    )
    
    # Process the video
    result = await pipeline.process_video_url(url)
    
    # Create structured objects
    source = pipeline.create_ingestion_source(url, result)
    frames = pipeline.create_video_frames(source.id, result)
    
    return source, frames, result


# Export main components
__all__ = [
    'VideoPipeline',
    'VideoProcessingError', 
    'YouTubeVideoProcessor',
    'AudioTranscriber',
    'FrameExtractor',
    'TranscriptFrameCorrelator',
    'process_youtube_video'
]