#!/usr/bin/env python3
"""
Quick test script for FaceFusion API - demonstrates basic usage patterns.
"""

import requests
import json
import os
import sys
from typing import Dict, List


def test_api_connection(base_url: str = "http://localhost:8000") -> bool:
    """Test if the API server is running."""
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API server is running - Status: {health_data.get('status')}")
            return True
        else:
            print(f"❌ API server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error checking API: {e}")
        return False


def demo_analyze_endpoint(target_path: str, base_url: str = "http://localhost:8000") -> Dict:
    """Demonstrate the analyze endpoint."""
    print(f"\n🔍 Analyzing faces in: {target_path}")
    
    if not os.path.exists(target_path):
        print(f"❌ File not found: {target_path}")
        return {}
    
    analyze_data = {
        "target_path": target_path,
        "frame_number": 0
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/analyze", json=analyze_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                encoded_faces = result.get("encoded_faces", {})
                print(f"✅ Analysis successful - Found {len(encoded_faces)} faces")
                
                # Print face indices
                for face_id in encoded_faces.keys():
                    print(f"  - Face {face_id}: {len(encoded_faces[face_id])} bytes of base64 data")
                
                return result
            else:
                print(f"❌ Analysis failed: {result.get('message')}")
                return {}
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return {}


def demo_basic_headless_run(source_path: str, target_path: str, output_path: str, base_url: str = "http://localhost:8000") -> bool:
    """Demonstrate basic headless-run functionality."""
    print(f"\n🔄 Running basic face swap:")
    print(f"  Source: {source_path}")
    print(f"  Target: {target_path}")
    print(f"  Output: {output_path}")
    
    if not os.path.exists(source_path):
        print(f"❌ Source file not found: {source_path}")
        return False
        
    if not os.path.exists(target_path):
        print(f"❌ Target file not found: {target_path}")
        return False
    
    headless_data = {
        "source_paths": [source_path],
        "target_path": target_path,
        "output_path": output_path,
        "processors": ["face_swapper"]
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/headless-run", json=headless_data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Face swap completed successfully!")
                print(f"  Output saved to: {result.get('output_path')}")
                return True
            else:
                print(f"❌ Face swap failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during face swap: {e}")
        return False


def demo_many_faces_workflow(source_paths: List[str], target_path: str, output_path: str, base_url: str = "http://localhost:8000") -> bool:
    """Demonstrate the complete many faces workflow: analyze + many parameter."""
    print(f"\n🎭 Running many faces workflow:")
    print(f"  Sources: {source_paths}")
    print(f"  Target: {target_path}")
    print(f"  Output: {output_path}")
    
    # Step 1: Analyze target to get face mappings
    print("\n📋 Step 1: Analyzing target for faces...")
    analyze_result = demo_analyze_endpoint(target_path, base_url)
    
    if not analyze_result or not analyze_result.get("encoded_faces"):
        print("❌ Cannot proceed without face analysis results")
        return False
    
    encoded_faces = analyze_result["encoded_faces"]
    
    # Step 2: Create face mappings
    print("\n🗺️  Step 2: Creating face mappings...")
    faces_mapping = {}
    
    for i, source_path in enumerate(source_paths):
        if not os.path.exists(source_path):
            print(f"❌ Source file not found: {source_path}")
            return False
            
        # Map each source to a detected face (cycle through if more sources than faces)
        face_index = str(i % len(encoded_faces))
        faces_mapping[str(i)] = encoded_faces[face_index]
        print(f"  - Source {i} ({os.path.basename(source_path)}) → Face {face_index}")
    
    # Step 3: Run headless-run with many parameter
    print("\n🔄 Step 3: Running face swap with --many parameter...")
    
    headless_data = {
        "source_paths": source_paths,
        "target_path": target_path,
        "output_path": output_path,
        "processors": ["face_swapper"],
        "face_selector_mode": "reference",
        "faces_mapping": faces_mapping
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/headless-run", json=headless_data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Many faces swap completed successfully!")
                print(f"  Swapped {len(source_paths)} faces")
                print(f"  Output saved to: {result.get('output_path')}")
                return True
            else:
                print(f"❌ Many faces swap failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during many faces swap: {e}")
        return False


def main():
    """Main function with example usage."""
    print("🎭 FaceFusion API Quick Test")
    print("=" * 50)
    
    # Test API connection first
    if not test_api_connection():
        print("\n💡 To start the API server, run: python start_server.py")
        sys.exit(1)
    
    # Example file paths - UPDATE THESE WITH YOUR ACTUAL FILES
    example_config = {
        "source_image": "path/to/your/source.jpg",
        "source_images": [
            "path/to/your/source1.jpg",
            "path/to/your/source2.jpg"
        ],
        "target_image": "path/to/your/target.jpg",
        "target_video": "path/to/your/target.mp4",
        "output_basic": "output_basic.jpg",
        "output_many": "output_many.jpg"
    }
    
    print("\n📁 Example Configuration:")
    print("Update the file paths in the example_config dictionary with your actual files.")
    print("Current paths:")
    for key, value in example_config.items():
        if isinstance(value, list):
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    print("🧪 Available Test Functions:")
    print("1. demo_analyze_endpoint(target_path)")
    print("2. demo_basic_headless_run(source_path, target_path, output_path)")
    print("3. demo_many_faces_workflow(source_paths, target_path, output_path)")
    print("\n💡 Example usage:")
    print("python -c \"from quick_api_test import *; demo_analyze_endpoint('your_image.jpg')\"")
    
    # Uncomment and update paths to run actual tests:
    # demo_analyze_endpoint(example_config["target_image"])
    # demo_basic_headless_run(example_config["source_image"], example_config["target_image"], example_config["output_basic"])
    # demo_many_faces_workflow(example_config["source_images"], example_config["target_image"], example_config["output_many"])


if __name__ == "__main__":
    main()
