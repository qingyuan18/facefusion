# FaceFusion --many Parameter Usage Guide

## Overview

The `--many` parameter enables multi-face swapping functionality in FaceFusion. It allows you to map specific source faces to specific target faces based on similarity comparison with reference face data obtained from the analyze endpoint.

## Workflow

### Step 1: Analyze Target Video/Image

First, use the analyze endpoint to detect faces in your target video or image:

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "target_path": "/path/to/target/video.mp4",
       "frame_number": 0
     }'
```

Response:
```json
{
  "success": true,
  "message": "Successfully detected and extracted 2 faces",
  "encoded_faces": {
    "0": "iVBORw0KGgoAAAANSUhEUgAA...",
    "1": "iVBORw0KGgoAAAANSUhEUgAA..."
  }
}
```

### Step 2: Create Face Mapping

Create a mapping dictionary that maps source face indices to the base64 encoded reference faces:

```json
{
  "0": "iVBORw0KGgoAAAANSUhEUgAA...",  // Maps source image 0 to reference face 0
  "1": "iVBORw0KGgoAAAANSUhEUgAA..."   // Maps source image 1 to reference face 1
}
```

### Step 3: Run Face Swap with --many Parameter

Use the headless-run endpoint with the `faces_mapping` parameter:

```bash
curl -X POST "http://localhost:8000/api/v1/headless-run" \
     -H "Content-Type: application/json" \
     -d '{
       "source_paths": [
         "/path/to/source1.jpg",
         "/path/to/source2.jpg"
       ],
       "target_path": "/path/to/target/video.mp4",
       "output_path": "/path/to/output/result.mp4",
       "processors": ["face_swapper"],
       "face_selector_mode": "reference",
       "faces_mapping": {
         "0": "iVBORw0KGgoAAAANSUhEUgAA...",
         "1": "iVBORw0KGgoAAAANSUhEUgAA..."
       }
     }'
```

## How It Works

1. **Face Detection**: The system detects faces in each frame of the target video
2. **Similarity Comparison**: For each source face, it compares detected faces with the corresponding reference face from the mapping
3. **Threshold Filtering**: Only faces that meet the similarity threshold (`reference_face_distance`) are selected for swapping
4. **Face Swapping**: The source face is swapped with the matching target face

## Python Example

```python
import requests
import json

# Step 1: Analyze target
analyze_response = requests.post("http://localhost:8000/api/v1/analyze", json={
    "target_path": "/path/to/target.mp4",
    "frame_number": 0
})

encoded_faces = analyze_response.json()["encoded_faces"]

# Step 2: Create mapping
faces_mapping = {
    "0": encoded_faces["0"],  # Map source 0 to detected face 0
    "1": encoded_faces["1"]   # Map source 1 to detected face 1
}

# Step 3: Run face swap
swap_response = requests.post("http://localhost:8000/api/v1/headless-run", json={
    "source_paths": ["/path/to/source1.jpg", "/path/to/source2.jpg"],
    "target_path": "/path/to/target.mp4",
    "output_path": "/path/to/output.mp4",
    "processors": ["face_swapper"],
    "face_selector_mode": "reference",
    "faces_mapping": faces_mapping
})

print(swap_response.json())
```

## Parameters

### faces_mapping (Dict[str, str])
- **Key**: String index of the source image (e.g., "0", "1", "2")
- **Value**: Base64 encoded PNG image data of the reference face
- **Purpose**: Maps each source face to a specific reference face for similarity comparison

### Required Settings
- `face_selector_mode`: Must be set to "reference" for the mapping to work
- `processors`: Must include "face_swapper"
- `source_paths`: List of source images (one for each mapping index)

## Advanced Usage

### Selective Face Mapping

You don't need to map all source faces. You can selectively map only specific ones:

```json
{
  "faces_mapping": {
    "0": "base64_data_for_first_face",
    // Skip index 1 - this source face won't be processed
    "2": "base64_data_for_third_face"
  }
}
```

### Adjusting Similarity Threshold

Control how strict the face matching is:

```json
{
  "reference_face_distance": 0.3,  // Lower = more strict matching
  "faces_mapping": { ... }
}
```

## Error Handling

Common issues and solutions:

1. **No faces detected in reference data**
   - Ensure the base64 data contains a clear face image
   - Check that the image is properly encoded

2. **No matching faces found**
   - Adjust the `reference_face_distance` threshold
   - Verify the reference face matches faces in the target video

3. **Invalid base64 data**
   - Ensure the base64 string is properly formatted
   - Verify it represents a valid PNG image

## Testing

Use the provided test script to verify functionality:

```bash
python test_many_faces_api.py
```

Make sure to update the file paths in the test script with your actual image/video files.

## Notes

- The mapping indices correspond to the order of source images in `source_paths`
- Each source image should contain exactly one clear face for best results
- The reference face data should come from the analyze endpoint for consistency
- Processing time increases with the number of faces and video length
