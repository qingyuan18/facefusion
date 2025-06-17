"""
FastAPI routes for FaceFusion API.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List

from api.models import (
    HeadlessRunRequest,
    HeadlessRunResponse,
    JobStatusResponse,
    ProcessorsResponse,
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse
)
from api.services import FaceFusionService

# Create router
router = APIRouter(prefix="/api/v1", tags=["facefusion"])

# Initialize service
service = FaceFusionService()


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
