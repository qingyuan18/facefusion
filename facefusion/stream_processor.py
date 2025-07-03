"""
Real-time stream processing module for FaceFusion.
Handles live stream splitting, async face swapping, and output streaming.
"""

import asyncio
import os
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import cv2
import numpy as np

from facefusion import logger, state_manager
from facefusion.stream_splitter import StreamSplitter
from facefusion.async_face_processor import AsyncFaceProcessor, ProcessingResult


class StreamProcessor:
    """Main class for processing real-time video streams with face swapping."""

    def __init__(self,
                 source_face_path: str,
                 segment_duration: float = 5.0,
                 max_workers: int = 4,
                 temp_dir: Optional[str] = None,
                 output_quality: int = 80):
        """
        Initialize the stream processor.

        Args:
            source_face_path: Path to the source face image for swapping
            segment_duration: Duration of each video segment in seconds
            max_workers: Maximum number of worker threads for processing
            temp_dir: Temporary directory for storing segments
            output_quality: Video output quality (1-100)
        """
        self.source_face_path = source_face_path
        self.segment_duration = segment_duration
        self.max_workers = max_workers
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="facefusion_stream_")
        self.output_quality = output_quality

        # Processing state
        self.is_processing = False
        self.session_id = str(uuid.uuid4())

        # Initialize components
        self.splitter = StreamSplitter(
            temp_dir=os.path.join(self.temp_dir, "segments"),
            segment_duration=segment_duration
        )

        self.processor = AsyncFaceProcessor(
            source_face_path=source_face_path,
            max_workers=max_workers,
            temp_dir=os.path.join(self.temp_dir, "processed"),
            output_quality=output_quality
        )

        # Processing queues
        self.pending_segments: asyncio.Queue = asyncio.Queue()
        self.completed_segments: asyncio.Queue = asyncio.Queue()

        # Statistics
        self.stats = {
            'segments_processed': 0,
            'total_processing_time': 0.0,
            'start_time': None,
            'last_segment_time': None
        }

        logger.info(f"StreamProcessor initialized with session_id: {self.session_id}")

    async def _segment_monitor_task(self) -> None:
        """Monitor for new segments and queue them for processing."""
        async for segment_path in self.splitter.get_available_segments():
            if not self.is_processing:
                break

            # Generate unique segment ID
            segment_id = f"{self.session_id}_{int(time.time() * 1000)}"

            # Queue segment for processing
            await self.pending_segments.put((segment_path, segment_id))
            logger.debug(f"Queued segment for processing: {segment_id}")

    async def _processing_task(self) -> None:
        """Process segments from the queue."""
        while self.is_processing:
            try:
                # Get next segment to process
                segment_path, segment_id = await asyncio.wait_for(
                    self.pending_segments.get(),
                    timeout=1.0
                )

                # Process the segment
                start_time = time.time()
                result = await self.processor.process_segment(segment_path, segment_id)
                processing_time = time.time() - start_time

                # Update statistics
                self.stats['segments_processed'] += 1
                self.stats['total_processing_time'] += processing_time
                self.stats['last_segment_time'] = time.time()

                # Queue completed segment
                if result.success:
                    await self.completed_segments.put(result)
                    logger.debug(f"Completed processing segment: {segment_id} in {processing_time:.2f}s")
                else:
                    logger.error(f"Failed to process segment {segment_id}: {result.error_message}")

                # Clean up input segment
                try:
                    if os.path.exists(segment_path):
                        os.remove(segment_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up input segment: {e}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in processing task: {e}")
                continue

    async def process_stream(self, stream_url: str) -> AsyncIterator[Tuple[str, bytes, Dict]]:
        """
        Process a live stream and yield processed video segments.

        Args:
            stream_url: URL of the live stream (rtmp://, wss://, etc.)

        Yields:
            Tuple[str, bytes, Dict]: (segment_id, processed_video_data, metadata)
        """
        self.is_processing = True
        self.stats['start_time'] = time.time()

        try:
            # Start stream splitting
            await self.splitter.start_splitting(stream_url)
            logger.info(f"Started stream processing for: {stream_url}")

            # Start background tasks
            monitor_task = asyncio.create_task(self._segment_monitor_task())
            processing_task = asyncio.create_task(self._processing_task())

            # Yield processed segments as they become available
            while self.is_processing:
                try:
                    # Wait for completed segment
                    result = await asyncio.wait_for(
                        self.completed_segments.get(),
                        timeout=5.0
                    )

                    if result.success and result.output_path:
                        # Read processed segment data
                        with open(result.output_path, 'rb') as f:
                            segment_data = f.read()

                        # Create metadata
                        metadata = {
                            'segment_id': result.segment_id,
                            'timestamp': result.timestamp,
                            'processing_time': result.processing_time,
                            'frames_processed': result.frames_processed,
                            'file_size': len(segment_data),
                            'session_id': self.session_id
                        }

                        # Clean up processed file
                        self.processor.cleanup_result(result)

                        yield result.segment_id, segment_data, metadata

                except asyncio.TimeoutError:
                    # Check if we should continue waiting
                    if time.time() - self.stats.get('last_segment_time', self.stats['start_time']) > 30:
                        logger.warning("No segments processed in 30 seconds, stopping...")
                        break
                    continue
                except Exception as e:
                    logger.error(f"Error yielding segment: {e}")
                    continue

        finally:
            # Clean up tasks
            if 'monitor_task' in locals():
                monitor_task.cancel()
            if 'processing_task' in locals():
                processing_task.cancel()

            await self._cleanup()

    def get_stats(self) -> Dict:
        """Get current processing statistics."""
        current_time = time.time()
        runtime = current_time - self.stats['start_time'] if self.stats['start_time'] else 0

        stats = {
            'session_id': self.session_id,
            'runtime_seconds': runtime,
            'segments_processed': self.stats['segments_processed'],
            'total_processing_time': self.stats['total_processing_time'],
            'last_segment_time': self.stats['last_segment_time'],
            'is_processing': self.is_processing
        }

        # Add derived metrics
        if self.stats['segments_processed'] > 0:
            stats['average_processing_time'] = self.stats['total_processing_time'] / self.stats['segments_processed']
            stats['processing_fps'] = self.stats['segments_processed'] / runtime if runtime > 0 else 0
        else:
            stats['average_processing_time'] = 0.0
            stats['processing_fps'] = 0.0

        # Add processor stats
        if hasattr(self.processor, 'get_stats'):
            processor_stats = self.processor.get_stats()
            stats.update({f'processor_{k}': v for k, v in processor_stats.items()})

        return stats

    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id

    async def _cleanup(self) -> None:
        """Clean up resources."""
        self.is_processing = False

        try:
            # Stop splitter
            await self.splitter.stop_splitting()

            # Shutdown processor
            await self.processor.shutdown()

            # Clean up splitter
            self.splitter.cleanup()

            # Remove temp directory if empty
            if os.path.exists(self.temp_dir):
                try:
                    # Try to remove any remaining files
                    for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                        for file in files:
                            try:
                                os.remove(os.path.join(root, file))
                            except Exception:
                                pass
                        for dir in dirs:
                            try:
                                os.rmdir(os.path.join(root, dir))
                            except Exception:
                                pass

                    # Remove main temp directory
                    os.rmdir(self.temp_dir)
                    logger.debug(f"Cleaned up temp directory: {self.temp_dir}")

                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def stop(self) -> None:
        """Stop stream processing."""
        self.is_processing = False
        logger.info("Stream processing stopped")

    async def stop_async(self) -> None:
        """Asynchronously stop stream processing."""
        await self._cleanup()
