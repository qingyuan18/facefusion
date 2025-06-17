# FaceFusion API

A RESTful API interface for FaceFusion's headless-run functionality, built with FastAPI.

## Features

- **RESTful API**: Clean HTTP API for FaceFusion operations
- **Comprehensive Configuration**: Supports all headless-run parameters
- **Job Tracking**: Track processing jobs with unique IDs
- **Health Monitoring**: Health check endpoints
- **Auto Documentation**: Interactive API docs with Swagger UI
- **CORS Support**: Cross-origin resource sharing enabled

## Installation

1. Install the additional dependencies:
```bash
pip install fastapi uvicorn[standard]
```

Or install from the updated requirements.txt:
```bash
pip install -r requirements.txt
```

## Quick Start

### Start the API Server

Using the startup script:
```bash
python start_server.py
```

With custom configuration:
```bash
python start_server.py --host 127.0.0.1 --port 8080 --reload
```

Direct uvicorn command:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### POST /api/v1/headless-run

Execute FaceFusion headless processing.

**Required Parameters:**
- `source_paths`: List of source image/video paths
- `target_path`: Target image/video path  
- `output_path`: Output path for processed result

**Optional Parameters:**
- Face detection settings (model, size, angles, score)
- Face landmarker settings
- Face selector settings (mode, order, reference distance)
- Face masker settings (occluder model, parser model, mask types)
- Frame extraction settings (trim frames, format, keep temp)
- Output settings (quality, resolution, encoder, fps)
- Processors list
- Execution settings (device, providers, threads)
- Memory settings
- Logging level

### GET /api/v1/status/{job_id}

Get processing job status by ID.

### GET /api/v1/processors

Get list of available processors.

### GET /api/v1/health

Health check endpoint.

## Example Usage

### Basic Face Swap

```bash
curl -X POST "http://localhost:8000/api/v1/headless-run" \
  -H "Content-Type: application/json" \
  -d '{
    "source_paths": ["/path/to/source.jpg"],
    "target_path": "/path/to/target.jpg",
    "output_path": "/path/to/output.jpg",
    "processors": ["face_swapper"]
  }'
```

### Advanced Configuration

```bash
curl -X POST "http://localhost:8000/api/v1/headless-run" \
  -H "Content-Type: application/json" \
  -d '{
    "source_paths": ["/path/to/source.jpg"],
    "target_path": "/path/to/target.mp4",
    "output_path": "/path/to/output.mp4",
    "processors": ["face_swapper", "face_enhancer"],
    "face_detector_model": "yolo_face",
    "face_detector_score": 0.7,
    "output_video_quality": 85,
    "output_video_fps": 30,
    "trim_frame_start": 0,
    "trim_frame_end": 100,
    "log_level": "debug"
  }'
```

### Check Job Status

```bash
curl "http://localhost:8000/api/v1/status/your-job-id"
```

### Get Available Processors

```bash
curl "http://localhost:8000/api/v1/processors"
```

## Response Format

### Success Response
```json
{
  "success": true,
  "job_id": "uuid-string",
  "message": "Processing completed successfully",
  "output_path": "/path/to/output.jpg"
}
```

### Error Response
```json
{
  "success": false,
  "job_id": "uuid-string", 
  "message": "Error description",
  "error_code": 1
}
```

## Configuration

### Server Configuration

The server can be configured via command line arguments:

```bash
python start_server.py --help
```

Options:
- `--host`: Host to bind (default: 0.0.0.0)
- `--port`: Port to bind (default: 8000)
- `--reload`: Enable auto-reload for development
- `--workers`: Number of worker processes
- `--log-level`: Logging level

### Environment Variables

- `OMP_NUM_THREADS`: Set to '1' automatically for optimal performance

## Development

### Project Structure

```
api/
├── __init__.py
├── main.py          # FastAPI application
├── models.py        # Pydantic models
├── routes.py        # API route handlers
└── services.py      # Business logic

start_server.py      # Server startup script
API_README.md        # This documentation
```

### Adding New Features

1. Add new Pydantic models in `models.py`
2. Implement business logic in `services.py`
3. Add new routes in `routes.py`
4. Update documentation

## Production Deployment

For production deployment, consider:

1. **Security**: Configure CORS properly, add authentication
2. **Performance**: Use multiple workers, configure resource limits
3. **Monitoring**: Add logging, metrics, health checks
4. **Storage**: Use persistent job storage (Redis, database)
5. **Load Balancing**: Use reverse proxy (nginx, traefik)

Example production command:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure FaceFusion dependencies are installed
2. **Path Issues**: Use absolute paths for file operations
3. **Memory Issues**: Configure system memory limits appropriately
4. **Permission Issues**: Ensure write permissions for output directories

### Logs

Check server logs for detailed error information. Increase log level to 'debug' for more verbose output.
