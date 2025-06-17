# FaceFusion Analyze API Usage Guide

## Overview

The Analyze API endpoint allows you to extract face images from videos or images and return them as base64-encoded data. This is useful for face detection and extraction workflows.

## API Endpoint

**POST** `/api/v1/analyze`

## Request Format

```json
{
    "target_path": "/path/to/your/image_or_video.jpg",
    "frame_number": 0
}
```

### Parameters

- `target_path` (required): Path to the target image or video file
- `frame_number` (optional): Frame number to analyze (for videos, default: 0)

## Response Format

### Success Response

```json
{
    "success": true,
    "message": "Successfully detected and extracted 2 faces",
    "encoded_faces": {
        "0": "iVBORw0KGgoAAAANSUhEUgAA...",
        "1": "iVBORw0KGgoAAAANSUhEUgAA..."
    },
    "error_code": null
}
```

### Error Response

```json
{
    "success": false,
    "message": "Target path does not exist: /invalid/path.jpg",
    "encoded_faces": null,
    "error_code": 1
}
```

## Error Codes

- `1`: Target path does not exist
- `2`: Failed to read image/video frame
- `3`: FaceFusion modules not available
- `4`: Unexpected error during analysis

## Usage Examples

### Python Example

```python
import requests
import base64
import json
from PIL import Image
import io

# API endpoint
url = "http://localhost:8000/api/v1/analyze"

# Request data
data = {
    "target_path": "/path/to/your/image.jpg",
    "frame_number": 0
}

# Make request
response = requests.post(url, json=data)
result = response.json()

if result["success"]:
    print(f"Detected {len(result['encoded_faces'])} faces")
    
    # Save each detected face
    for face_id, encoded_face in result["encoded_faces"].items():
        # Decode base64 image
        image_data = base64.b64decode(encoded_face)
        image = Image.open(io.BytesIO(image_data))
        
        # Save face image
        image.save(f"face_{face_id}.png")
        print(f"Saved face {face_id}")
else:
    print(f"Error: {result['message']}")
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "target_path": "/path/to/your/image.jpg",
       "frame_number": 0
     }'
```

### JavaScript Example

```javascript
const analyzeImage = async (imagePath, frameNumber = 0) => {
    const response = await fetch('http://localhost:8000/api/v1/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            target_path: imagePath,
            frame_number: frameNumber
        })
    });
    
    const result = await response.json();
    
    if (result.success) {
        console.log(`Detected ${Object.keys(result.encoded_faces).length} faces`);
        return result.encoded_faces;
    } else {
        console.error(`Error: ${result.message}`);
        return null;
    }
};

// Usage
analyzeImage('/path/to/your/image.jpg')
    .then(faces => {
        if (faces) {
            Object.entries(faces).forEach(([id, base64Data]) => {
                console.log(`Face ${id}: ${base64Data.substring(0, 50)}...`);
            });
        }
    });
```

## Features

- **Face Detection**: Uses YOLO-based face detection from FaceFusion
- **Automatic Cropping**: Crops detected faces with 25% padding
- **Base64 Encoding**: Returns face images as base64-encoded PNG data
- **Video Support**: Can extract faces from specific video frames
- **Memory Management**: Automatically cleans up GPU memory after processing

## Notes

1. **File Paths**: Use absolute paths for best results
2. **Video Frames**: Frame numbers start from 0
3. **Image Formats**: Supports common image formats (JPG, PNG, etc.)
4. **Video Formats**: Supports common video formats (MP4, AVI, etc.)
5. **Face Padding**: Detected faces include 25% padding around the bounding box
6. **Memory Usage**: GPU memory is automatically cleared after processing

## Testing

Use the provided test script to verify the API:

```bash
python test_analyze_api.py
```

Make sure to update the `target_path` in the test script with a valid image or video file path.
