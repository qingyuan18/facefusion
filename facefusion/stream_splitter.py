"""
Stream splitter module for real-time video stream processing.
Handles splitting live streams into manageable segments using FFmpeg.
"""

import asyncio
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

from facefusion import ffmpeg_builder, logger
from facefusion.ffmpeg import open_ffmpeg


class StreamSplitter:
    """Handles splitting live video streams into segments for processing."""
    
    def __init__(self, 
                 temp_dir: Optional[str] = None,
                 segment_duration: float = 5.0,
                 segment_format: str = "mp4"):
        """
        Initialize the stream splitter.
        
        Args:
            temp_dir: Directory for storing temporary segments
            segment_duration: Duration of each segment in seconds
            segment_format: Output format for segments
        """
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="facefusion_segments_")
        self.segment_duration = segment_duration
        self.segment_format = segment_format
        
        # Processing state
        self.is_active = False
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.segment_counter = 0
        self.current_segments: Dict[str, float] = {}  # segment_name -> creation_time
        
        # Ensure temp directory exists
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"StreamSplitter initialized with temp_dir: {self.temp_dir}")

    def _is_valid_stream_url(self, url: str) -> bool:
        """Validate if the URL is a supported streaming protocol."""
        try:
            parsed = urlparse(url)
            supported_schemes = ['rtmp', 'rtmps', 'wss', 'ws', 'http', 'https', 'udp', 'tcp']
            return parsed.scheme.lower() in supported_schemes
        except Exception:
            return False

    def _build_ffmpeg_command(self, stream_url: str) -> List[str]:
        """Build FFmpeg command for stream splitting."""
        segment_pattern = os.path.join(self.temp_dir, f"segment_%06d.{self.segment_format}")
        
        # Base command for stream input
        commands = [
            '-i', stream_url,
            '-c', 'copy',  # Copy streams without re-encoding for speed
            '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
            '-f', 'segment',
            '-segment_time', str(self.segment_duration),
            '-segment_format', self.segment_format,
            '-reset_timestamps', '1',
            '-segment_list_flags', '+live',
            '-segment_wrap', '10',  # Keep only last 10 segments to save space
            segment_pattern
        ]
        
        # Add stream-specific options
        if stream_url.startswith(('rtmp://', 'rtmps://')):
            # RTMP specific options
            commands = ['-rtmp_live', 'live'] + commands
        elif stream_url.startswith(('wss://', 'ws://')):
            # WebSocket specific options
            commands = ['-protocol_whitelist', 'file,http,https,tcp,tls,crypto'] + commands
        elif stream_url.startswith(('http://', 'https://')):
            # HTTP stream options
            commands = ['-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5'] + commands
        
        return ffmpeg_builder.run(commands)

    async def start_splitting(self, stream_url: str) -> None:
        """Start splitting the stream into segments."""
        if not self._is_valid_stream_url(stream_url):
            raise ValueError(f"Invalid or unsupported stream URL: {stream_url}")
        
        if self.is_active:
            raise RuntimeError("Stream splitter is already active")
        
        try:
            # Build and start FFmpeg process
            ffmpeg_cmd = self._build_ffmpeg_command(stream_url)
            logger.info(f"Starting stream splitting for: {stream_url}")
            logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.is_active = True
            self.segment_counter = 0
            
            # Start monitoring FFmpeg process
            asyncio.create_task(self._monitor_ffmpeg_process())
            
        except Exception as e:
            logger.error(f"Failed to start stream splitting: {e}")
            await self.stop_splitting()
            raise

    async def _monitor_ffmpeg_process(self) -> None:
        """Monitor FFmpeg process for errors and completion."""
        if not self.ffmpeg_process:
            return
        
        try:
            while self.is_active and self.ffmpeg_process.poll() is None:
                await asyncio.sleep(1.0)
            
            # Process has ended
            if self.ffmpeg_process.poll() != 0:
                stderr_output = self.ffmpeg_process.stderr.read() if self.ffmpeg_process.stderr else ""
                logger.error(f"FFmpeg process ended with error code {self.ffmpeg_process.poll()}: {stderr_output}")
            else:
                logger.info("FFmpeg process completed successfully")
                
        except Exception as e:
            logger.error(f"Error monitoring FFmpeg process: {e}")
        finally:
            self.is_active = False

    async def get_available_segments(self) -> AsyncIterator[str]:
        """
        Async iterator that yields paths to newly available segments.
        
        Yields:
            str: Path to a complete segment file
        """
        last_check_time = time.time()
        processed_segments = set()
        
        while self.is_active:
            try:
                # Get all segment files in the directory
                segment_files = [
                    f for f in os.listdir(self.temp_dir)
                    if f.startswith("segment_") and f.endswith(f".{self.segment_format}")
                ]
                
                # Sort by creation time
                segment_files.sort()
                
                for segment_file in segment_files:
                    segment_path = os.path.join(self.temp_dir, segment_file)
                    
                    # Skip if already processed
                    if segment_file in processed_segments:
                        continue
                    
                    # Check if file is complete (not being written to)
                    if self._is_segment_complete(segment_path):
                        processed_segments.add(segment_file)
                        yield segment_path
                        logger.debug(f"New segment available: {segment_file}")
                
                # Clean up old processed segments to save space
                await self._cleanup_old_segments(processed_segments)
                
            except Exception as e:
                logger.error(f"Error checking for segments: {e}")
            
            await asyncio.sleep(0.5)  # Check every 500ms

    def _is_segment_complete(self, segment_path: str) -> bool:
        """Check if a segment file is complete and ready for processing."""
        try:
            if not os.path.exists(segment_path):
                return False
            
            # Check file size stability (file not being written to)
            initial_size = os.path.getsize(segment_path)
            time.sleep(0.1)  # Small delay
            final_size = os.path.getsize(segment_path)
            
            # File is complete if size is stable and > 0
            return initial_size == final_size and final_size > 0
            
        except Exception as e:
            logger.warning(f"Error checking segment completeness: {e}")
            return False

    async def _cleanup_old_segments(self, processed_segments: set) -> None:
        """Clean up old segment files to save disk space."""
        try:
            # Keep only the last few segments
            max_segments_to_keep = 5
            
            if len(processed_segments) > max_segments_to_keep:
                # Get all segment files sorted by name (which includes timestamp)
                all_segments = sorted([
                    f for f in os.listdir(self.temp_dir)
                    if f.startswith("segment_") and f.endswith(f".{self.segment_format}")
                ])
                
                # Remove oldest segments
                segments_to_remove = all_segments[:-max_segments_to_keep]
                
                for segment_file in segments_to_remove:
                    segment_path = os.path.join(self.temp_dir, segment_file)
                    try:
                        os.remove(segment_path)
                        processed_segments.discard(segment_file)
                        logger.debug(f"Cleaned up old segment: {segment_file}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old segment {segment_file}: {e}")
                        
        except Exception as e:
            logger.warning(f"Error during segment cleanup: {e}")

    async def stop_splitting(self) -> None:
        """Stop the stream splitting process."""
        self.is_active = False
        
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process_termination()),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("FFmpeg process did not terminate gracefully, killing...")
                    self.ffmpeg_process.kill()
                
                self.ffmpeg_process = None
                logger.info("Stream splitting stopped")
                
            except Exception as e:
                logger.error(f"Error stopping FFmpeg process: {e}")

    async def _wait_for_process_termination(self) -> None:
        """Wait for FFmpeg process to terminate."""
        if self.ffmpeg_process:
            while self.ffmpeg_process.poll() is None:
                await asyncio.sleep(0.1)

    def cleanup(self) -> None:
        """Clean up all temporary files and directories."""
        try:
            # Remove all segment files
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove file {file_path}: {e}")
                
                # Remove temp directory if empty
                try:
                    os.rmdir(self.temp_dir)
                    logger.debug(f"Removed temp directory: {self.temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp directory: {e}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        if self.is_active:
            asyncio.create_task(self.stop_splitting())
        self.cleanup()
