#!/usr/bin/env python3
"""
Test script for S3 functionality in FaceFusion API.
Tests both S3 input and output path support.
"""

import requests
import json
import time
import os
from typing import Dict, Any

def test_s3_download_optimization():
    """Test that S3 files are not re-downloaded if they exist locally with correct size."""
    print("🧪 Testing S3 download optimization...")
    
    try:
        from facefusion.download import download_s3_file, is_s3_path
        
        # Test with a sample S3 path (you can replace with your actual S3 file)
        test_s3_path = "s3://facefusiondemo/41a13dad-99d1-4cf0-b9fb-58712fd10f70_WeChat_20240709163338.mp4"
        
        print(f"📥 First download of: {test_s3_path}")
        local_path1 = download_s3_file(test_s3_path)
        
        if local_path1:
            print(f"✅ First download successful: {local_path1}")
            
            print(f"📥 Second download (should skip if file exists)...")
            local_path2 = download_s3_file(test_s3_path)
            
            if local_path2 == local_path1:
                print("✅ Download optimization working - file not re-downloaded")
                return True
            else:
                print("❌ Download optimization failed - file was re-downloaded")
                return False
        else:
            print("❌ First download failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing S3 download: {e}")
        return False

def test_analyze_with_s3_input(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test analyze endpoint with S3 input."""
    print("🧪 Testing analyze endpoint with S3 input...")
    
    analyze_data = {
        "target_path": "s3://facefusiondemo/41a13dad-99d1-4cf0-b9fb-58712fd10f70_WeChat_20240709163338.mp4",
        "frame_number": 80
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/analyze", json=analyze_data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                encoded_faces = result.get("encoded_faces", {})
                print(f"✅ S3 analyze successful - Found {len(encoded_faces)} faces")
                return result
            else:
                print(f"❌ S3 analyze failed: {result.get('message')}")
                return {}
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ Error during S3 analyze: {e}")
        return {}

def test_single_face_swap_with_s3_output(base_url: str = "http://localhost:8000") -> bool:
    """Test single face swap with S3 output path."""
    print("🧪 Testing single face swap with S3 output...")
    
    swap_data = {
        "source_paths": ["/home/ubuntu/facefusion/musk.jpg"],  # Local source
        "target_path": "/home/ubuntu/facefusion/source01.mp4",  # Local target
        "output_path": "s3://facefusiondemo/output/test_single_swap.mp4",  # S3 output
        "processors": ["face_swapper"]
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/headless-run", json=swap_data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Single face swap with S3 output successful")
                print(f"📁 Output saved to: {result.get('output_path')}")
                print(f"🆔 Job ID: {result.get('job_id')}")
                return True
            else:
                print(f"❌ Single face swap failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during single face swap: {e}")
        return False

def test_many_faces_workflow_with_s3(base_url: str = "http://localhost:8000") -> bool:
    """Test complete many faces workflow with S3 input and output."""
    print("🧪 Testing many faces workflow with S3...")
    
    # Step 1: Analyze S3 video
    print("📋 Step 1: Analyzing S3 video for faces...")
    analyze_result = test_analyze_with_s3_input(base_url)
    
    if not analyze_result or not analyze_result.get("encoded_faces"):
        print("❌ Cannot proceed without face analysis results")
        return False
    
    encoded_faces = analyze_result["encoded_faces"]
    print(f"✅ Found {len(encoded_faces)} faces for mapping")
    
    # Step 2: Create face mapping (map first 2 faces)
    faces_mapping = {}
    face_ids = list(encoded_faces.keys())[:2]  # Take first 2 faces
    
    for i, face_id in enumerate(face_ids):
        faces_mapping[str(i)] = encoded_faces[face_id]
    
    print(f"📋 Created mapping for {len(faces_mapping)} faces")
    
    # Step 3: Perform many faces swap with S3 output
    print("🔄 Step 3: Performing many faces swap with S3 output...")
    
    swap_data = {
        "source_paths": [
            "/home/ubuntu/facefusion/musk.jpg",
            "/home/ubuntu/facefusion/tangyan.jpg"
        ],
        "target_path": "s3://facefusiondemo/41a13dad-99d1-4cf0-b9fb-58712fd10f70_WeChat_20240709163338.mp4",  # S3 input
        "output_path": "s3://facefusiondemo/output/test_many_faces.mp4",  # S3 output
        "processors": ["face_swapper"],
        "face_selector_mode": "reference",
        "faces_mapping": faces_mapping
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/headless-run", json=swap_data, timeout=600)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Many faces swap with S3 I/O successful!")
                print(f"📁 Output saved to: {result.get('output_path')}")
                print(f"🆔 Job ID: {result.get('job_id')}")
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
    """Run all S3 functionality tests."""
    print("🚀 Starting S3 functionality tests...\n")
    
    base_url = "http://alb-facefusion-1532009031.us-west-2.elb.amazonaws.com:8080"
    
    tests = [
        ("S3 Download Optimization", test_s3_download_optimization),
        ("S3 Input Analysis", lambda: test_analyze_with_s3_input(base_url) != {}),
        ("Single Face Swap with S3 Output", lambda: test_single_face_swap_with_s3_output(base_url)),
        ("Many Faces Workflow with S3", lambda: test_many_faces_workflow_with_s3(base_url))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        time.sleep(2)  # Brief pause between tests
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All S3 functionality tests passed!")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main()
