"""
FastAPI routes for FaceFusion API.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from typing import List
import json
import asyncio

from api.models import (
    HeadlessRunRequest,
    HeadlessRunResponse,
    JobStatusResponse,
    ProcessorsResponse,
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    StreamProcessRequest,
    StreamProcessResponse,
    StreamStatusResponse
)
from api.services import FaceFusionService, StreamService

# Create router
router = APIRouter(prefix="/api/v1", tags=["facefusion"])

# Initialize services
service = FaceFusionService()
stream_service = StreamService()


@router.post("/headless-run", response_model=HeadlessRunResponse)
async def headless_run(request: HeadlessRunRequest):
    """
    Execute FaceFusion headless-run command with the provided parameters.
    
    This endpoint processes images or videos using FaceFusion's headless mode.
    It supports all the configuration options available in the command-line interface.
    """
    try:
        response = service.execute_headless_run(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a processing job by its ID.
    
    Returns information about the job including its current status,
    progress (if available), and output path when completed.
    """
    job_status = service.get_job_status(job_id)
    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    return job_status


@router.get("/processors", response_model=ProcessorsResponse)
async def get_processors():
    """
    Get a list of available processors.
    
    Returns all the processors that can be used with the FaceFusion system.
    """
    try:
        processors = service.get_available_processors()
        return ProcessorsResponse(processors=processors)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving processors: {str(e)}"
        )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_faces(request: AnalyzeRequest):
    """
    Analyze faces in an image or video frame.

    This endpoint extracts faces from the provided image or video frame,
    crops them with padding, and returns them as base64-encoded images.
    """
    try:
        response = service.execute_analyze(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the health status of the FaceFusion API service.
    """
    try:
        # Try to import facefusion to check if it's available
        import facefusion.metadata as metadata
        version = metadata.get('version')

        return HealthResponse(
            status="healthy",
            version=version,
            message="FaceFusion API is running successfully"
        )
    except ImportError:
        return HealthResponse(
            status="degraded",
            message="FaceFusion module not available - some features may not work"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post("/stream/start", response_model=StreamProcessResponse)
async def start_stream_processing(request: StreamProcessRequest):
    """
    Start real-time stream processing with face swapping.

    This endpoint starts processing a live video stream (RTMP, WebSocket, HTTP, etc.)
    and returns a session ID for tracking. Processed segments can be received via WebSocket.
    """
    try:
        response = await stream_service.start_stream_processing(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream processing: {str(e)}"
        )


@router.get("/stream/status/{session_id}", response_model=StreamStatusResponse)
async def get_stream_status(session_id: str):
    """
    Get the status of a stream processing session.

    Returns current status, statistics, and processing information for the given session.
    """
    try:
        response = stream_service.get_stream_status(session_id)
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream session not found: {session_id}"
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stream status: {str(e)}"
        )


@router.post("/stream/stop/{session_id}")
async def stop_stream_processing(session_id: str):
    """
    Stop a stream processing session.

    Gracefully stops the stream processing and cleans up resources.
    """
    try:
        success = await stream_service.stop_stream_processing(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream session not found: {session_id}"
            )
        return {"message": f"Stream processing stopped for session: {session_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping stream processing: {str(e)}"
        )


@router.websocket("/stream/ws/{session_id}")
async def stream_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving processed video segments.

    Clients connect to this endpoint to receive real-time processed video segments
    from the specified stream processing session.
    """
    await websocket.accept()

    try:
        # Check if session exists
        if not stream_service.has_session(session_id):
            await websocket.send_text(json.dumps({
                "error": f"Stream session not found: {session_id}"
            }))
            await websocket.close()
            return

        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": f"Connected to stream session: {session_id}"
        }))

        # Stream processed segments
        async for segment_id, segment_data, metadata in stream_service.get_processed_segments(session_id):
            try:
                # Send metadata first
                await websocket.send_text(json.dumps({
                    "type": "segment_metadata",
                    "segment_id": segment_id,
                    "metadata": metadata
                }))

                # Send binary segment data
                await websocket.send_bytes(segment_data)

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error sending segment: {str(e)}"
                }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"WebSocket error: {str(e)}"
            }))
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
