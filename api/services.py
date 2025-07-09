"""
Service layer for FaceFusion API operations.
"""
import json
import os
import sys
import subprocess
import uuid
import json
import tempfile
import base64
import gc
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Add the project root to Python path so we can import facefusion modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from api.models import (
    HeadlessRunRequest, HeadlessRunResponse, JobStatusResponse,
    AnalyzeRequest, AnalyzeResponse, StreamProcessRequest,
    StreamProcessResponse, StreamStatusResponse
)


class FaceFusionService:
    """Service class for FaceFusion operations."""
    
    def __init__(self):
        self.jobs_storage = {}  # In-memory job storage (in production, use Redis or database)
        self.facefusion_script = os.path.join(project_root, "facefusion.py")
        
    def get_available_processors(self) -> List[str]:
        """Get list of available processors."""
        try:
            # Get processors from the processors/modules directory
            processors_dir = Path("facefusion/processors/modules")
            if processors_dir.exists():
                processors = []
                for file_path in processors_dir.glob("*.py"):
                    if file_path.name != "__init__.py":
                        processors.append(file_path.stem)
                return sorted(processors)
            return ["face_swapper", "face_enhancer", "face_debugger"]  # fallback
        except Exception:
            return ["face_swapper", "face_enhancer", "face_debugger"]  # fallback
    
    def download_s3_paths_if_needed(self, request: HeadlessRunRequest) -> Tuple[bool, str, HeadlessRunRequest]:
        """Download S3 paths to local /tmp/ directory if needed."""
        try:
            # Import S3 download functions
            sys.path.insert(0, project_root)
            from facefusion.download import download_file_if_needed, is_s3_path

            # Create a copy of the request to modify paths
            updated_request = request.model_copy()

            # Download source paths if they are S3 URLs
            updated_source_paths = []
            for source_path in request.source_paths:
                if is_s3_path(source_path):
                    local_path = download_file_if_needed(source_path)
                    updated_source_paths.append(local_path)
                else:
                    updated_source_paths.append(source_path)
            updated_request.source_paths = updated_source_paths

            # Download target path if it's an S3 URL
            if is_s3_path(request.target_path):
                updated_request.target_path = download_file_if_needed(request.target_path)

            return True, "S3 paths downloaded successfully", updated_request

        except Exception as e:
            return False, f"Failed to download S3 paths: {str(e)}", request

    def is_s3_output_path(self, output_path: str) -> bool:
        """Check if output path is an S3 URL."""
        try:
            from facefusion.download import is_s3_path
            return is_s3_path(output_path)
        except ImportError:
            return False

    def upload_to_s3_if_needed(self, local_file_path: str, s3_output_path: str) -> Tuple[bool, str]:
        """Upload local file to S3 if needed."""
        try:
            from facefusion.download import upload_file_if_needed

            # Check if local file exists
            if not os.path.exists(local_file_path):
                return False, f"Local output file does not exist: {local_file_path}"

            # Upload to S3
            upload_file_if_needed(local_file_path, s3_output_path)
            return True, "Successfully uploaded to S3"

        except Exception as e:
            return False, f"S3 upload failed: {str(e)}"

    def validate_paths(self, request: HeadlessRunRequest) -> Tuple[bool, str]:
        """Validate input paths."""
        # Check source paths
        for source_path in request.source_paths:
            if not os.path.exists(source_path):
                return False, f"Source path does not exist: {source_path}"

        # Check target path
        if not os.path.exists(request.target_path):
            return False, f"Target path does not exist: {request.target_path}"

        # Check output directory exists
        output_dir = os.path.dirname(request.output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create output directory: {e}"

        return True, "Paths validated successfully"
    
    def build_command(self, request: HeadlessRunRequest) -> List[str]:
        """Build the facefusion command from request parameters."""
        cmd = [sys.executable, self.facefusion_script, "headless-run"]

        # Smart defaults based on processors
        processors = request.processors or []

        # Adjust face_selector_mode based on processors if not explicitly set
        if not hasattr(request, '_face_selector_mode_set'):
            if any(proc in processors for proc in ['age_modifier', 'face_enhancer', 'frame_enhancer']) and 'face_swapper' not in processors:
                # For processors that don't need reference faces, use 'one' mode
                request.face_selector_mode = 'one'
            # For face_swapper or mixed scenarios, keep 'reference' (default)

        # Add source paths (only if needed)
        if request.source_paths and (request.face_selector_mode == 'reference' or 'face_swapper' in processors):
            cmd.extend(["-s"] + request.source_paths)
        
        # Add target and output paths
        cmd.extend(["-t", request.target_path])

        # Handle output path - if it's a directory, generate a filename
        output_path = request.output_path
        if output_path.endswith('/'):
            # Extract target filename and use it for output
            import os
            target_name = os.path.basename(request.target_path)
            if target_name:
                # Remove extension and add processed suffix
                name_without_ext = os.path.splitext(target_name)[0]
                ext = os.path.splitext(target_name)[1] or '.mp4'
                output_path = output_path + name_without_ext + '_processed' + ext
            else:
                # Fallback filename
                output_path = output_path + 'output.mp4'

        cmd.extend(["-o", output_path])
        
        # Add configuration path (always include it to ensure proper initialization)
        config_path = request.config_path or "facefusion.ini"
        cmd.extend(["--config-path", config_path])
        
        if request.temp_path:
            cmd.extend(["--temp-path", request.temp_path])
        
        if request.jobs_path:
            cmd.extend(["--jobs-path", request.jobs_path])
        
        # Face detector settings
        if request.face_detector_model:
            cmd.extend(["--face-detector-model", request.face_detector_model])
        
        if request.face_detector_size:
            cmd.extend(["--face-detector-size", request.face_detector_size])
        
        if request.face_detector_angles:
            cmd.extend(["--face-detector-angles"] + [str(angle) for angle in request.face_detector_angles])
        
        if request.face_detector_score is not None:
            cmd.extend(["--face-detector-score", str(request.face_detector_score)])
        
        # Face landmarker settings
        if request.face_landmarker_model:
            cmd.extend(["--face-landmarker-model", request.face_landmarker_model])
        
        # Face selector settings
        if request.face_selector_mode:
            cmd.extend(["--face-selector-mode", request.face_selector_mode])
        
        if request.face_selector_order:
            cmd.extend(["--face-selector-order", request.face_selector_order])
        
        if request.reference_face_distance is not None:
            cmd.extend(["--reference-face-distance", str(request.reference_face_distance)])
        
        if request.reference_frame_number is not None:
            cmd.extend(["--reference-frame-number", str(request.reference_frame_number)])
        
        # Face masker settings
        if request.face_occluder_model:
            cmd.extend(["--face-occluder-model", request.face_occluder_model])
        
        if request.face_parser_model:
            cmd.extend(["--face-parser-model", request.face_parser_model])
        
        if request.face_mask_types:
            cmd.extend(["--face-mask-types"] + request.face_mask_types)
        
        if request.face_mask_blur is not None:
            cmd.extend(["--face-mask-blur", str(request.face_mask_blur)])
        
        if request.face_mask_padding:
            cmd.extend(["--face-mask-padding"] + [str(p) for p in request.face_mask_padding])
        
        if request.face_mask_regions:
            cmd.extend(["--face-mask-regions"] + request.face_mask_regions)
        
        # Frame extraction settings
        if request.trim_frame_start is not None:
            cmd.extend(["--trim-frame-start", str(request.trim_frame_start)])
        
        if request.trim_frame_end is not None:
            cmd.extend(["--trim-frame-end", str(request.trim_frame_end)])
        
        if request.temp_frame_format:
            cmd.extend(["--temp-frame-format", request.temp_frame_format])
        
        if request.keep_temp:
            cmd.append("--keep-temp")
        
        # Output settings
        if request.output_image_quality is not None:
            cmd.extend(["--output-image-quality", str(request.output_image_quality)])
        
        if request.output_image_resolution:
            cmd.extend(["--output-image-resolution", request.output_image_resolution])
        
        if request.output_video_encoder:
            cmd.extend(["--output-video-encoder", request.output_video_encoder])
        
        if request.output_video_preset:
            cmd.extend(["--output-video-preset", request.output_video_preset])
        
        if request.output_video_quality is not None:
            cmd.extend(["--output-video-quality", str(request.output_video_quality)])
        
        if request.output_video_resolution:
            cmd.extend(["--output-video-resolution", request.output_video_resolution])
        
        if request.output_video_fps is not None:
            cmd.extend(["--output-video-fps", str(request.output_video_fps)])
        
        # Processors
        if request.processors:
            cmd.extend(["--processors"] + request.processors)

        # Only add processor-specific parameters if the processor is being used
        processors = request.processors or []

        # Face swapper settings
        if "face_swapper" in processors:
            if request.face_swapper_model:
                cmd.extend(["--face-swapper-model", request.face_swapper_model])

            if request.face_swapper_pixel_boost:
                cmd.extend(["--face-swapper-pixel-boost", request.face_swapper_pixel_boost])

        # Face enhancer settings
        if "face_enhancer" in processors:
            if request.face_enhancer_model:
                cmd.extend(["--face-enhancer-model", request.face_enhancer_model])

            if request.face_enhancer_blend is not None:
                cmd.extend(["--face-enhancer-blend", str(request.face_enhancer_blend)])

            if request.face_enhancer_weight is not None:
                cmd.extend(["--face-enhancer-weight", str(request.face_enhancer_weight)])

        # Frame enhancer settings
        if "frame_enhancer" in processors:
            if request.frame_enhancer_model:
                cmd.extend(["--frame-enhancer-model", request.frame_enhancer_model])

            if request.frame_enhancer_blend is not None:
                cmd.extend(["--frame-enhancer-blend", str(request.frame_enhancer_blend)])

        # Age modifier settings
        if "age_modifier" in processors:
            if request.age_modifier_model:
                cmd.extend(["--age-modifier-model", request.age_modifier_model])

            if request.age_modifier_direction is not None:
                cmd.extend(["--age-modifier-direction", str(request.age_modifier_direction)])

        # Lip syncer settings
        if "lip_syncer" in processors:
            if request.lip_syncer_model:
                cmd.extend(["--lip-syncer-model", request.lip_syncer_model])

        # Frame colorizer settings
        if "frame_colorizer" in processors:
            if request.frame_colorizer_model:
                cmd.extend(["--frame-colorizer-model", request.frame_colorizer_model])

            if request.frame_colorizer_size:
                cmd.extend(["--frame-colorizer-size", request.frame_colorizer_size])

            if request.frame_colorizer_blend is not None:
                cmd.extend(["--frame-colorizer-blend", str(request.frame_colorizer_blend)])

        # Many faces mapping
        if request.faces_mapping:
            faces_mapping_json = json.dumps(request.faces_mapping)
            cmd.extend(["--many", faces_mapping_json])
        
        # Execution settings
        if request.execution_device_id:
            cmd.extend(["--execution-device-id", request.execution_device_id])
        
        if request.execution_providers:
            cmd.extend(["--execution-providers"] + request.execution_providers)
        
        if request.execution_thread_count is not None:
            cmd.extend(["--execution-thread-count", str(request.execution_thread_count)])
        
        if request.execution_queue_count is not None:
            cmd.extend(["--execution-queue-count", str(request.execution_queue_count)])
        
        # Memory settings
        if request.video_memory_strategy:
            cmd.extend(["--video-memory-strategy", request.video_memory_strategy])
        
        if request.system_memory_limit is not None:
            cmd.extend(["--system-memory-limit", str(request.system_memory_limit)])
        
        # Logging
        if request.log_level:
            cmd.extend(["--log-level", request.log_level])
        
        return cmd
    
    def execute_headless_run(self, request: HeadlessRunRequest) -> HeadlessRunResponse:
        """Execute headless-run command."""
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Store original output path for S3 upload later
        original_output_path = request.output_path

        # Download S3 paths if needed
        s3_success, s3_message, updated_request = self.download_s3_paths_if_needed(request)
        if not s3_success:
            return HeadlessRunResponse(
                success=False,
                job_id=job_id,
                message=s3_message,
                error_code=1
            )

        # Use the updated request with local paths
        request = updated_request

        # Handle S3 output path - convert to local path for processing
        local_output_path = request.output_path
        if self.is_s3_output_path(original_output_path):
            # Generate local output path in /tmp
            import tempfile
            from facefusion.download import is_s3_path

            if is_s3_path(original_output_path):
                # Extract filename from S3 path
                output_filename = os.path.basename(original_output_path)
                local_output_path = os.path.join(tempfile.gettempdir(), f"{job_id}_{output_filename}")
                request.output_path = local_output_path

        # Validate paths
        valid, message = self.validate_paths(request)
        if not valid:
            return HeadlessRunResponse(
                success=False,
                job_id=job_id,
                message=message,
                error_code=1
            )

        # Build command
        cmd = self.build_command(request)

        # Print the complete command for debugging
        print("=" * 80)
        print("FACEFUSION COMMAND EXECUTION")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Command ({len(cmd)} arguments):")
        for i, arg in enumerate(cmd):
            print(f"  {i:2d}: {arg}")
        print("\nComplete command line:")
        print(" ".join(cmd))
        print("=" * 80)

        # Store job info
        self.jobs_storage[job_id] = {
            "status": "running",
            "command": cmd,
            "output_path": original_output_path,  # Store original S3 path
            "local_output_path": local_output_path,  # Store local path for processing
            "message": "Processing started"
        }

        try:
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            # Print execution results
            print("\nEXECUTION RESULTS:")
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout[:1000])  # First 1000 chars
                if len(result.stdout) > 1000:
                    print("... (truncated)")
            if result.stderr:
                print("STDERR:")
                print(result.stderr[:1000])  # First 1000 chars
                if len(result.stderr) > 1000:
                    print("... (truncated)")
            print("=" * 80)

            if result.returncode == 0:
                # Processing completed successfully, now handle S3 upload if needed
                final_output_path = original_output_path

                if self.is_s3_output_path(original_output_path):
                    # Upload to S3
                    upload_success, upload_message = self.upload_to_s3_if_needed(local_output_path, original_output_path)
                    if not upload_success:
                        self.jobs_storage[job_id].update({
                            "status": "failed",
                            "message": f"Processing completed but S3 upload failed: {upload_message}"
                        })

                        return HeadlessRunResponse(
                            success=False,
                            job_id=job_id,
                            message=f"Processing completed but S3 upload failed: {upload_message}",
                            error_code=2
                        )

                    # Clean up local file after successful upload
                    try:
                        if os.path.exists(local_output_path):
                            os.remove(local_output_path)
                    except Exception as e:
                        # Log but don't fail the request
                        print(f"Warning: Failed to clean up local file {local_output_path}: {e}")

                # Success
                self.jobs_storage[job_id].update({
                    "status": "completed",
                    "message": "Processing completed successfully"
                })

                return HeadlessRunResponse(
                    success=True,
                    job_id=job_id,
                    message="Processing completed successfully",
                    output_path=final_output_path
                )
            else:
                # Error
                error_message = result.stderr or result.stdout or "Unknown error occurred"
                self.jobs_storage[job_id].update({
                    "status": "failed",
                    "message": f"Processing failed: {error_message}"
                })

                return HeadlessRunResponse(
                    success=False,
                    job_id=job_id,
                    message=f"Processing failed: {error_message}",
                    error_code=result.returncode
                )
                
        except subprocess.TimeoutExpired:
            self.jobs_storage[job_id].update({
                "status": "failed",
                "message": "Processing timed out"
            })
            
            return HeadlessRunResponse(
                success=False,
                job_id=job_id,
                message="Processing timed out",
                error_code=124
            )
            
        except Exception as e:
            self.jobs_storage[job_id].update({
                "status": "failed",
                "message": f"Unexpected error: {str(e)}"
            })
            
            return HeadlessRunResponse(
                success=False,
                job_id=job_id,
                message=f"Unexpected error: {str(e)}",
                error_code=1
            )
    
    def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """Get job status by ID."""
        if job_id not in self.jobs_storage:
            return None

        job_info = self.jobs_storage[job_id]
        return JobStatusResponse(
            job_id=job_id,
            status=job_info["status"],
            message=job_info.get("message"),
            output_path=job_info.get("output_path") if job_info["status"] == "completed" else None
        )

    def frame_to_binary(self, frame) -> bytes:
        """Convert vision frame to binary data."""
        import cv2
        import numpy

        # Ensure frame is uint8 format
        if frame.dtype != numpy.uint8:
            frame = (frame * 255).astype(numpy.uint8)

        # Encode frame as PNG
        return cv2.imencode('.png', frame)[1].tobytes()

    def execute_analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Execute face analysis on target image/video."""
        try:
            # Import FaceFusion modules
            import facefusion.globals
            from facefusion.filesystem import is_video
            from facefusion.vision import read_image, read_video_frame
            from facefusion.face_analyser import get_many_faces
            from facefusion.face_detector import clear_inference_pool as clear_face_analyser
            from facefusion.download import download_file_if_needed, is_s3_path
            import torch

            # Download S3 file if needed
            target_path = request.target_path
            if is_s3_path(target_path):
                try:
                    target_path = download_file_if_needed(target_path)
                except Exception as e:
                    return AnalyzeResponse(
                        success=False,
                        message=f"Failed to download S3 file: {str(e)}",
                        error_code=1
                    )

            # Check if target path exists
            if not os.path.exists(target_path):
                return AnalyzeResponse(
                    success=False,
                    message=f"Target path does not exist: {target_path}",
                    error_code=1
                )

            # Get vision frame
            vision_frame = None
            if is_video(target_path):
                vision_frame = read_video_frame(target_path, request.frame_number)
                if vision_frame is None:
                    return AnalyzeResponse(
                        success=False,
                        message=f"Failed to read frame {request.frame_number} from video",
                        error_code=2
                    )
            else:
                vision_frame = read_image(target_path)
                if vision_frame is None:
                    return AnalyzeResponse(
                        success=False,
                        message="Failed to read image",
                        error_code=2
                    )

            # Get reference faces using YOLO detection
            reference_faces = get_many_faces([vision_frame])

            if not reference_faces:
                return AnalyzeResponse(
                    success=True,
                    message="No faces detected in the image/frame",
                    encoded_faces={}
                )

            # Crop and encode faces
            binary_faces = {}
            for index, face in enumerate(reference_faces):
                start_x, start_y, end_x, end_y = map(int, face.bounding_box)

                # Add padding (25% of face size)
                padding_x = int((end_x - start_x) * 0.25)
                padding_y = int((end_y - start_y) * 0.25)
                start_x = max(0, start_x - padding_x)
                start_y = max(0, start_y - padding_y)
                end_x = min(vision_frame.shape[1], end_x + padding_x)
                end_y = min(vision_frame.shape[0], end_y + padding_y)

                # Crop face region
                crop_vision_frame = vision_frame[start_y:end_y, start_x:end_x]

                # Convert to binary and encode as base64
                binary_face = self.frame_to_binary(crop_vision_frame)
                binary_faces[str(index)] = base64.b64encode(binary_face).decode('utf-8')

            # Clean up memory
            clear_face_analyser()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

            return AnalyzeResponse(
                success=True,
                message=f"Successfully detected and extracted {len(binary_faces)} faces",
                encoded_faces=binary_faces
            )

        except ImportError as e:
            return AnalyzeResponse(
                success=False,
                message=f"FaceFusion modules not available: {str(e)}",
                error_code=3
            )
        except Exception as e:
            return AnalyzeResponse(
                success=False,
                message=f"Unexpected error during analysis: {str(e)}",
                error_code=4
            )


class StreamService:
    """Service class for real-time stream processing operations."""

    def __init__(self):
        self.active_sessions = {}  # session_id -> StreamProcessor
        self.session_tasks = {}    # session_id -> asyncio.Task

    async def start_stream_processing(self, request: StreamProcessRequest) -> StreamProcessResponse:
        """Start a new stream processing session."""
        try:
            # Import FaceFusion modules
            sys.path.insert(0, project_root)
            from facefusion.stream_processor import StreamProcessor
            from facefusion import state_manager

            # Configure FaceFusion state
            if request.face_detector_model:
                state_manager.set_item('face_detector_model', request.face_detector_model)
            if request.face_detector_score:
                state_manager.set_item('face_detector_score', request.face_detector_score)
            if request.face_selector_mode:
                state_manager.set_item('face_selector_mode', request.face_selector_mode)
            if request.reference_face_distance:
                state_manager.set_item('reference_face_distance', request.reference_face_distance)
            if request.face_swapper_model:
                state_manager.set_item('face_swapper_model', request.face_swapper_model)
            if request.face_enhancer_model:
                state_manager.set_item('face_enhancer_model', request.face_enhancer_model)
            if request.face_enhancer_blend is not None:
                state_manager.set_item('face_enhancer_blend', request.face_enhancer_blend)
            if request.execution_providers:
                state_manager.set_item('execution_providers', request.execution_providers)
            if request.execution_thread_count:
                state_manager.set_item('execution_thread_count', request.execution_thread_count)

            # Create stream processor
            processor = StreamProcessor(
                source_face_path=request.source_face_path,
                segment_duration=request.segment_duration,
                max_workers=request.max_workers,
                output_quality=request.output_quality
            )

            session_id = processor.get_session_id()

            # Store session
            self.active_sessions[session_id] = processor

            # Start processing task
            task = asyncio.create_task(
                self._run_stream_processing(processor, request.stream_url, session_id)
            )
            self.session_tasks[session_id] = task

            # Create WebSocket URL
            websocket_url = f"/api/v1/stream/ws/{session_id}"

            return StreamProcessResponse(
                success=True,
                session_id=session_id,
                message="Stream processing started successfully",
                websocket_url=websocket_url
            )

        except Exception as e:
            return StreamProcessResponse(
                success=False,
                message=f"Failed to start stream processing: {str(e)}",
                error_code=1
            )

    async def _run_stream_processing(self, processor: 'StreamProcessor', stream_url: str, session_id: str):
        """Run the stream processing in the background."""
        try:
            async for segment_id, segment_data, metadata in processor.process_stream(stream_url):
                # Processing continues in the background
                # Segments are yielded through get_processed_segments
                pass
        except Exception as e:
            print(f"Error in stream processing for session {session_id}: {e}")
        finally:
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.session_tasks:
                del self.session_tasks[session_id]

    def get_stream_status(self, session_id: str) -> Optional[StreamStatusResponse]:
        """Get status of a stream processing session."""
        if session_id not in self.active_sessions:
            return None

        processor = self.active_sessions[session_id]
        stats = processor.get_stats()

        # Determine status
        if processor.is_processing:
            status = "active"
        else:
            status = "stopped"

        return StreamStatusResponse(
            session_id=session_id,
            status=status,
            message=f"Stream processing {status}",
            segments_processed=stats.get('segments_processed', 0),
            processing_fps=stats.get('processing_fps', 0.0)
        )

    async def stop_stream_processing(self, session_id: str) -> bool:
        """Stop a stream processing session."""
        if session_id not in self.active_sessions:
            return False

        try:
            processor = self.active_sessions[session_id]
            await processor.stop_async()

            # Cancel task
            if session_id in self.session_tasks:
                task = self.session_tasks[session_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Clean up
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.session_tasks:
                del self.session_tasks[session_id]

            return True

        except Exception as e:
            print(f"Error stopping stream processing for session {session_id}: {e}")
            return False

    def has_session(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self.active_sessions

    async def get_processed_segments(self, session_id: str):
        """Get processed segments for a session (async generator)."""
        if session_id not in self.active_sessions:
            return

        processor = self.active_sessions[session_id]

        try:
            async for segment_id, segment_data, metadata in processor.process_stream(""):
                yield segment_id, segment_data, metadata
        except Exception as e:
            print(f"Error getting processed segments for session {session_id}: {e}")
            return
