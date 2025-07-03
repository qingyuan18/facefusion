"""
Async face processing module for real-time stream face swapping.
Handles parallel processing of video segments with face swapping.
"""

import asyncio
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from facefusion import logger, state_manager
from facefusion.face_analyser import get_many_faces, get_one_face
from facefusion.face_store import get_reference_faces
from facefusion.processors.modules.face_swapper import process_frame as swap_face_frame
from facefusion.vision import read_image


class ProcessingResult:
    """Result of processing a video segment."""
    
    def __init__(self, segment_id: str, input_path: str, success: bool = False):
        self.segment_id = segment_id
        self.input_path = input_path
        self.output_path: Optional[str] = None
        self.success = success
        self.error_message: Optional[str] = None
        self.processing_time: float = 0.0
        self.frames_processed: int = 0
        self.timestamp = time.time()


class AsyncFaceProcessor:
    """Handles async processing of video segments with face swapping."""
    
    def __init__(self, 
                 source_face_path: str,
                 max_workers: int = 4,
                 temp_dir: Optional[str] = None,
                 output_quality: int = 80):
        """
        Initialize the async face processor.
        
        Args:
            source_face_path: Path to source face image for swapping
            max_workers: Maximum number of worker threads
            temp_dir: Directory for temporary output files
            output_quality: Video output quality (1-100)
        """
        self.source_face_path = source_face_path
        self.max_workers = max_workers
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="facefusion_processed_")
        self.output_quality = output_quality
        
        # Processing state
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.source_face = None
        self.reference_faces = None
        self.processing_stats = {
            'total_segments': 0,
            'successful_segments': 0,
            'failed_segments': 0,
            'total_frames': 0,
            'average_processing_time': 0.0
        }
        
        # Ensure temp directory exists
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Load source face once
        self._load_source_face()
        
        logger.info(f"AsyncFaceProcessor initialized with {max_workers} workers")

    def _load_source_face(self) -> None:
        """Load and cache the source face."""
        try:
            source_image = read_image(self.source_face_path)
            if source_image is None:
                raise ValueError(f"Cannot read source image: {self.source_face_path}")
            
            self.source_face = get_one_face(source_image)
            if self.source_face is None:
                raise ValueError(f"No face found in source image: {self.source_face_path}")
            
            # Load reference faces if needed
            if 'reference' in state_manager.get_item('face_selector_mode'):
                self.reference_faces = get_reference_faces()
            
            logger.info("Source face loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load source face: {e}")
            raise

    def _process_segment_sync(self, segment_path: str, segment_id: str) -> ProcessingResult:
        """
        Synchronously process a single video segment.
        This runs in a thread pool executor.
        """
        result = ProcessingResult(segment_id, segment_path)
        start_time = time.time()
        
        try:
            logger.debug(f"Starting processing of segment: {segment_id}")
            
            # Open input video
            cap = cv2.VideoCapture(segment_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video segment: {segment_path}")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps <= 0 or width <= 0 or height <= 0:
                raise ValueError(f"Invalid video properties: fps={fps}, size={width}x{height}")
            
            # Create output path
            output_filename = f"processed_{segment_id}_{int(time.time())}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                raise ValueError(f"Cannot create output video writer: {output_path}")
            
            frames_processed = 0
            frames_with_faces = 0
            
            # Process each frame
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                try:
                    # Attempt face swapping
                    processed_frame = swap_face_frame({
                        'source_face': self.source_face,
                        'reference_faces': self.reference_faces,
                        'target_vision_frame': frame
                    })
                    
                    # Check if face swapping actually occurred
                    if not np.array_equal(frame, processed_frame):
                        frames_with_faces += 1
                    
                    out.write(processed_frame)
                    
                except Exception as frame_error:
                    logger.warning(f"Failed to process frame {frames_processed} in {segment_id}: {frame_error}")
                    # Write original frame if processing fails
                    out.write(frame)
                
                frames_processed += 1
                
                # Log progress for long segments
                if frames_processed % 100 == 0:
                    logger.debug(f"Processed {frames_processed}/{total_frames} frames in {segment_id}")
            
            # Clean up
            cap.release()
            out.release()
            
            # Verify output file was created successfully
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise ValueError("Output video file was not created or is empty")
            
            # Update result
            result.output_path = output_path
            result.success = True
            result.frames_processed = frames_processed
            result.processing_time = time.time() - start_time
            
            logger.debug(f"Successfully processed segment {segment_id}: "
                        f"{frames_processed} frames, {frames_with_faces} with faces, "
                        f"{result.processing_time:.2f}s")
            
        except Exception as e:
            result.error_message = str(e)
            result.processing_time = time.time() - start_time
            logger.error(f"Failed to process segment {segment_id}: {e}")
            
            # Clean up failed output
            if result.output_path and os.path.exists(result.output_path):
                try:
                    os.remove(result.output_path)
                except Exception:
                    pass
                result.output_path = None
        
        return result

    async def process_segment(self, segment_path: str, segment_id: str) -> ProcessingResult:
        """
        Asynchronously process a video segment.
        
        Args:
            segment_path: Path to input video segment
            segment_id: Unique identifier for the segment
            
        Returns:
            ProcessingResult: Result of the processing operation
        """
        loop = asyncio.get_event_loop()
        
        # Submit to thread pool
        future = self.executor.submit(self._process_segment_sync, segment_path, segment_id)
        
        # Wait for completion
        result = await loop.run_in_executor(None, future.result)
        
        # Update statistics
        self._update_stats(result)
        
        return result

    async def process_segments_batch(self, segment_paths: List[Tuple[str, str]]) -> List[ProcessingResult]:
        """
        Process multiple segments in parallel.
        
        Args:
            segment_paths: List of (segment_path, segment_id) tuples
            
        Returns:
            List[ProcessingResult]: Results for all segments
        """
        if not segment_paths:
            return []
        
        logger.info(f"Processing batch of {len(segment_paths)} segments")
        
        # Submit all tasks
        tasks = [
            self.process_segment(segment_path, segment_id)
            for segment_path, segment_id in segment_paths
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                segment_path, segment_id = segment_paths[i]
                error_result = ProcessingResult(segment_id, segment_path)
                error_result.error_message = str(result)
                processed_results.append(error_result)
                logger.error(f"Exception processing segment {segment_id}: {result}")
            else:
                processed_results.append(result)
        
        return processed_results

    def _update_stats(self, result: ProcessingResult) -> None:
        """Update processing statistics."""
        self.processing_stats['total_segments'] += 1
        
        if result.success:
            self.processing_stats['successful_segments'] += 1
            self.processing_stats['total_frames'] += result.frames_processed
        else:
            self.processing_stats['failed_segments'] += 1
        
        # Update average processing time
        total_segments = self.processing_stats['total_segments']
        current_avg = self.processing_stats['average_processing_time']
        new_avg = ((current_avg * (total_segments - 1)) + result.processing_time) / total_segments
        self.processing_stats['average_processing_time'] = new_avg

    def get_stats(self) -> Dict:
        """Get current processing statistics."""
        stats = self.processing_stats.copy()
        
        # Add derived metrics
        if stats['total_segments'] > 0:
            stats['success_rate'] = stats['successful_segments'] / stats['total_segments']
            stats['failure_rate'] = stats['failed_segments'] / stats['total_segments']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        if stats['average_processing_time'] > 0:
            stats['estimated_fps'] = stats['total_frames'] / (stats['total_segments'] * stats['average_processing_time'])
        else:
            stats['estimated_fps'] = 0.0
        
        return stats

    def cleanup_result(self, result: ProcessingResult) -> None:
        """Clean up files associated with a processing result."""
        try:
            if result.output_path and os.path.exists(result.output_path):
                os.remove(result.output_path)
                logger.debug(f"Cleaned up output file: {result.output_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up result files: {e}")

    async def shutdown(self) -> None:
        """Shutdown the processor and clean up resources."""
        logger.info("Shutting down AsyncFaceProcessor")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Clean up temp directory
        try:
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
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
