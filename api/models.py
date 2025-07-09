"""
Pydantic models for FaceFusion API requests and responses.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class HeadlessRunRequest(BaseModel):
    """Request model for headless-run API endpoint."""
    
    # Required paths
    source_paths: List[str] = Field(..., description="List of source image/video paths")
    target_path: str = Field(..., description="Target image/video path")
    output_path: str = Field(..., description="Output path for processed result")
    
    # Optional configuration paths
    config_path: Optional[str] = Field(default="facefusion.ini", description="Configuration file path")
    temp_path: Optional[str] = Field(default=None, description="Temporary files path")
    jobs_path: Optional[str] = Field(default=None, description="Jobs directory path")
    
    # Face detector settings
    face_detector_model: Optional[str] = Field(default="yolo_face", description="Face detector model")
    face_detector_size: Optional[str] = Field(default=None, description="Face detector size")
    face_detector_angles: Optional[List[int]] = Field(default=[0], description="Face detector angles")
    face_detector_score: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Face detector score threshold")
    
    # Face landmarker settings
    face_landmarker_model: Optional[str] = Field(default="2dfan4", description="Face landmarker model")
    
    # Face selector settings
    face_selector_mode: Optional[str] = Field(default="reference", description="Face selector mode")
    face_selector_order: Optional[str] = Field(default="large-small", description="Face selector order")
    reference_face_distance: Optional[float] = Field(default=0.3, ge=0.0, le=1.0, description="Reference face distance")
    reference_frame_number: Optional[int] = Field(default=0, ge=0, description="Reference frame number")
    
    # Face masker settings
    face_occluder_model: Optional[str] = Field(default="xseg_1", description="Face occluder model")
    face_parser_model: Optional[str] = Field(default="bisenet_resnet_34", description="Face parser model")
    face_mask_types: Optional[List[str]] = Field(default=["box"], description="Face mask types")
    face_mask_blur: Optional[float] = Field(default=0.3, ge=0.0, le=1.0, description="Face mask blur")
    face_mask_padding: Optional[List[int]] = Field(default=[0, 0, 0, 0], description="Face mask padding")
    face_mask_regions: Optional[List[str]] = Field(default=None, description="Face mask regions")
    
    # Frame extraction settings
    trim_frame_start: Optional[int] = Field(default=None, ge=0, description="Trim frame start")
    trim_frame_end: Optional[int] = Field(default=None, ge=0, description="Trim frame end")
    temp_frame_format: Optional[str] = Field(default="png", description="Temporary frame format")
    keep_temp: Optional[bool] = Field(default=False, description="Keep temporary files")
    
    # Output creation settings
    output_image_quality: Optional[int] = Field(default=None, ge=0, le=100, description="Output image quality")
    output_image_resolution: Optional[str] = Field(default=None, description="Output image resolution")
    output_audio_encoder: Optional[str] = Field(default=None, description="Output audio encoder")
    output_audio_quality: Optional[int] = Field(default=None, ge=0, le=100, description="Output audio quality")
    output_audio_volume: Optional[float] = Field(default=None, ge=0.0, description="Output audio volume")
    output_video_encoder: Optional[str] = Field(default=None, description="Output video encoder")
    output_video_preset: Optional[str] = Field(default=None, description="Output video preset")
    output_video_quality: Optional[int] = Field(default=None, ge=0, le=100, description="Output video quality")
    output_video_resolution: Optional[str] = Field(default=None, description="Output video resolution")
    output_video_fps: Optional[float] = Field(default=None, gt=0.0, description="Output video FPS")
    
    # Processors
    processors: Optional[List[str]] = Field(default=["face_swapper"], description="List of processors to use")

    # Face swapper settings
    face_swapper_model: Optional[str] = Field(default="inswapper_128_fp16", description="Face swapper model")
    face_swapper_pixel_boost: Optional[str] = Field(default=None, description="Face swapper pixel boost")

    # Face enhancer settings
    face_enhancer_model: Optional[str] = Field(default="gfpgan_1.4", description="Face enhancer model")
    face_enhancer_blend: Optional[int] = Field(default=80, ge=0, le=100, description="Face enhancer blend percentage")
    face_enhancer_weight: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Face enhancer weight")

    # Frame enhancer settings
    frame_enhancer_model: Optional[str] = Field(default="span_kendata_x4", description="Frame enhancer model")
    frame_enhancer_blend: Optional[int] = Field(default=80, ge=0, le=100, description="Frame enhancer blend percentage")

    # Age modifier settings
    age_modifier_model: Optional[str] = Field(default="styleganex_age", description="Age modifier model")
    age_modifier_direction: Optional[int] = Field(default=0, ge=-100, le=100, description="Age modifier direction")

    # Lip syncer settings
    lip_syncer_model: Optional[str] = Field(default="wav2lip_gan_96", description="Lip syncer model")

    # Frame colorizer settings
    frame_colorizer_model: Optional[str] = Field(default="ddcolor", description="Frame colorizer model")
    frame_colorizer_size: Optional[str] = Field(default="256x256", description="Frame colorizer size")
    frame_colorizer_blend: Optional[int] = Field(default=100, ge=0, le=100, description="Frame colorizer blend percentage")

    # Many faces mapping (for multi-face swapping)
    faces_mapping: Optional[Dict[str, str]] = Field(default=None, description="Mapping of face indices to base64 encoded face data")
    
    # Execution settings
    execution_device_id: Optional[str] = Field(default="0", description="Execution device ID")
    execution_providers: Optional[List[str]] = Field(default=None, description="Execution providers")
    execution_thread_count: Optional[int] = Field(default=None, ge=1, description="Execution thread count")
    execution_queue_count: Optional[int] = Field(default=None, ge=1, description="Execution queue count")
    
    # Download settings
    download_providers: Optional[List[str]] = Field(default=None, description="Download providers")
    download_scope: Optional[str] = Field(default=None, description="Download scope")
    
    # Memory settings
    video_memory_strategy: Optional[str] = Field(default=None, description="Video memory strategy")
    system_memory_limit: Optional[int] = Field(default=None, ge=0, description="System memory limit in GB")
    
    # Logging
    log_level: Optional[str] = Field(default="info", description="Log level")


class HeadlessRunResponse(BaseModel):
    """Response model for headless-run API endpoint."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    job_id: Optional[str] = Field(default=None, description="Job ID for tracking")
    message: str = Field(..., description="Response message")
    error_code: Optional[int] = Field(default=None, description="Error code if failed")
    output_path: Optional[str] = Field(default=None, description="Path to the output file")


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint."""
    
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Job status")
    message: Optional[str] = Field(default=None, description="Status message")
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Progress percentage")
    output_path: Optional[str] = Field(default=None, description="Output file path if completed")


class ProcessorsResponse(BaseModel):
    """Response model for available processors endpoint."""
    
    processors: List[str] = Field(..., description="List of available processors")


class AnalyzeRequest(BaseModel):
    """Request model for analyze API endpoint."""

    target_path: str = Field(..., description="Target image/video path to analyze")
    frame_number: Optional[int] = Field(default=0, ge=0, description="Frame number to analyze (for videos)")


class AnalyzeResponse(BaseModel):
    """Response model for analyze API endpoint."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    encoded_faces: Optional[Dict[str, str]] = Field(default=None, description="Base64 encoded face images")
    error_code: Optional[int] = Field(default=None, description="Error code if failed")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Health status")
    version: Optional[str] = Field(default=None, description="FaceFusion version")
    message: str = Field(..., description="Health check message")


class StreamProcessRequest(BaseModel):
    """Request model for real-time stream processing endpoint."""

    stream_url: str = Field(..., description="Stream URL (rtmp://, wss://, http://, etc.)")
    source_face_path: str = Field(..., description="Path to source face image for swapping")

    # Stream processing settings
    segment_duration: Optional[float] = Field(default=5.0, ge=1.0, le=30.0, description="Duration of each video segment in seconds")
    max_workers: Optional[int] = Field(default=4, ge=1, le=16, description="Maximum number of worker threads")

    # Face processing settings
    face_detector_model: Optional[str] = Field(default="yolo_face", description="Face detector model")
    face_detector_score: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Face detector score threshold")
    face_selector_mode: Optional[str] = Field(default="reference", description="Face selector mode")
    reference_face_distance: Optional[float] = Field(default=0.3, ge=0.0, le=1.0, description="Reference face distance")
    face_swapper_model: Optional[str] = Field(default="inswapper_128_fp16", description="Face swapper model")
    face_enhancer_model: Optional[str] = Field(default="gfpgan_1.4", description="Face enhancer model")
    face_enhancer_blend: Optional[int] = Field(default=80, ge=0, le=100, description="Face enhancer blend percentage")

    # Output settings
    output_quality: Optional[int] = Field(default=80, ge=1, le=100, description="Output video quality")

    # Execution settings
    execution_providers: Optional[List[str]] = Field(default=None, description="Execution providers")
    execution_thread_count: Optional[int] = Field(default=None, ge=1, description="Execution thread count")


class StreamProcessResponse(BaseModel):
    """Response model for stream processing endpoint."""

    success: bool = Field(..., description="Whether the stream processing started successfully")
    session_id: Optional[str] = Field(default=None, description="Session ID for tracking the stream")
    message: str = Field(..., description="Response message")
    websocket_url: Optional[str] = Field(default=None, description="WebSocket URL for receiving processed segments")
    error_code: Optional[int] = Field(default=None, description="Error code if failed")


class StreamSegmentData(BaseModel):
    """Model for stream segment data."""

    segment_id: str = Field(..., description="Unique segment identifier")
    timestamp: float = Field(..., description="Segment timestamp")
    duration: float = Field(..., description="Segment duration in seconds")
    data: bytes = Field(..., description="Processed video segment data")
    format: str = Field(default="mp4", description="Video format")


class StreamStatusResponse(BaseModel):
    """Response model for stream status endpoint."""

    session_id: str = Field(..., description="Stream session ID")
    status: str = Field(..., description="Stream status (active, stopped, error)")
    message: Optional[str] = Field(default=None, description="Status message")
    segments_processed: Optional[int] = Field(default=None, description="Number of segments processed")
    processing_fps: Optional[float] = Field(default=None, description="Processing frames per second")
    error_code: Optional[int] = Field(default=None, description="Error code if failed")
