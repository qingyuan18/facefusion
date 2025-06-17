#!/usr/bin/env python3
"""
Complete example workflow for FaceFusion --many parameter functionality.
This demonstrates the full process from face analysis to multi-face swapping.
"""

import requests
import json
import base64
import os
from typing import Dict, List

class FaceFusionClient:
    """Client for FaceFusion API operations."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.analyze_url = f"{base_url}/api/v1/analyze"
        self.headless_run_url = f"{base_url}/api/v1/headless-run"
        self.health_url = f"{base_url}/api/v1/health"
    
    def check_health(self) -> bool:
        """Check if the API server is running."""
        try:
            response = requests.get(self.health_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def analyze_faces(self, target_path: str, frame_number: int = 0) -> Dict:
        """Analyze faces in target image/video."""
        data = {
            "target_path": target_path,
            "frame_number": frame_number
        }
        
        response = requests.post(self.analyze_url, json=data)
        response.raise_for_status()
        return response.json()
    
    def swap_faces_many(self, source_paths: List[str], target_path: str, 
                       output_path: str, faces_mapping: Dict[str, str]) -> Dict:
        """Perform multi-face swapping using --many parameter."""
        data = {
            "source_paths": source_paths,
            "target_path": target_path,
            "output_path": output_path,
            "processors": ["face_swapper"],
            "face_selector_mode": "reference",
            "faces_mapping": faces_mapping,
            "reference_face_distance": 0.3  # Adjust similarity threshold as needed
        }
        
        response = requests.post(self.headless_run_url, json=data)
        response.raise_for_status()
        return response.json()

def main():
    """Main workflow demonstration."""
    
    # Initialize client
    client = FaceFusionClient()
    
    # Check if server is running
    if not client.check_health():
        print("❌ FaceFusion API server is not running!")
        print("Please start the server with: python start_server.py")
        return
    
    print("✅ FaceFusion API server is running")
    
    # Configuration - UPDATE THESE PATHS
    target_video = "/path/to/your/target/video.mp4"  # Video with faces to replace
    source_images = [
        "/path/to/source1.jpg",  # Face to use for replacement 1
        "/path/to/source2.jpg"   # Face to use for replacement 2
    ]
    output_video = "/path/to/output/result.mp4"  # Where to save the result
    
    # Validate paths
    if not os.path.exists(target_video):
        print(f"❌ Target video not found: {target_video}")
        print("Please update the target_video path in the script")
        return
    
    for i, source_img in enumerate(source_images):
        if not os.path.exists(source_img):
            print(f"❌ Source image {i} not found: {source_img}")
            print("Please update the source_images paths in the script")
            return
    
    try:
        # Step 1: Analyze target video to detect faces
        print("\n🔍 Step 1: Analyzing target video for faces...")
        analyze_result = client.analyze_faces(target_video, frame_number=0)
        
        if not analyze_result.get("success"):
            print(f"❌ Face analysis failed: {analyze_result.get('message')}")
            return
        
        encoded_faces = analyze_result.get("encoded_faces", {})
        print(f"✅ Detected {len(encoded_faces)} faces in target video")
        
        if len(encoded_faces) == 0:
            print("❌ No faces detected in target video")
            return
        
        # Step 2: Create face mapping
        print("\n🗺️  Step 2: Creating face mapping...")
        faces_mapping = {}
        
        # Map each source image to a detected face
        for i, source_img in enumerate(source_images):
            face_key = str(i)
            if face_key in encoded_faces:
                faces_mapping[str(i)] = encoded_faces[face_key]
                print(f"✅ Mapped source image {i} to detected face {face_key}")
            else:
                print(f"⚠️  No detected face {face_key} to map source image {i}")
        
        if not faces_mapping:
            print("❌ No face mappings created")
            return
        
        print(f"✅ Created {len(faces_mapping)} face mappings")
        
        # Step 3: Perform multi-face swapping
        print("\n🔄 Step 3: Performing multi-face swapping...")
        swap_result = client.swap_faces_many(
            source_paths=source_images,
            target_path=target_video,
            output_path=output_video,
            faces_mapping=faces_mapping
        )
        
        if swap_result.get("success"):
            print("✅ Multi-face swapping completed successfully!")
            print(f"📁 Output saved to: {swap_result.get('output_path')}")
            print(f"🆔 Job ID: {swap_result.get('job_id')}")
        else:
            print(f"❌ Face swapping failed: {swap_result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def demo_with_sample_data():
    """Demo function with sample data structure."""
    print("\n📋 Sample Data Structure Demo")
    print("=" * 40)
    
    # Sample analyze response
    sample_analyze_response = {
        "success": True,
        "message": "Successfully detected and extracted 2 faces",
        "encoded_faces": {
            "0": "iVBORw0KGgoAAAANSUhEUgAA...",  # Base64 encoded face 0
            "1": "iVBORw0KGgoAAAANSUhEUgAA..."   # Base64 encoded face 1
        }
    }
    
    # Sample face mapping
    sample_faces_mapping = {
        "0": sample_analyze_response["encoded_faces"]["0"],  # Map source 0 to face 0
        "1": sample_analyze_response["encoded_faces"]["1"]   # Map source 1 to face 1
    }
    
    # Sample headless-run request
    sample_request = {
        "source_paths": ["/path/to/source1.jpg", "/path/to/source2.jpg"],
        "target_path": "/path/to/target.mp4",
        "output_path": "/path/to/output.mp4",
        "processors": ["face_swapper"],
        "face_selector_mode": "reference",
        "faces_mapping": sample_faces_mapping
    }
    
    print("Sample analyze response:")
    print(json.dumps(sample_analyze_response, indent=2))
    
    print("\nSample faces mapping:")
    print(json.dumps(sample_faces_mapping, indent=2))
    
    print("\nSample headless-run request:")
    print(json.dumps(sample_request, indent=2))

if __name__ == "__main__":
    print("FaceFusion --many Parameter Workflow Example")
    print("=" * 50)
    
    # Run the main workflow
    main()
    
    # Show sample data structure
    demo_with_sample_data()
    
    print("\n📝 Notes:")
    print("1. Update file paths in the script before running")
    print("2. Ensure source images contain clear, single faces")
    print("3. Target video should contain the faces you want to replace")
    print("4. Adjust reference_face_distance for similarity threshold")
    print("5. Check the output video for results")
