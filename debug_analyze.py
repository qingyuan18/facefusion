#!/usr/bin/env python3
"""
Debug script for testing the analyze functionality.
"""

import sys
import os
from pathlib import Path

# Ensure we're importing from the current project
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from api.services import FaceFusionService
from api.models import AnalyzeRequest


def test_analyze_with_real_data():
    """Test analyze with real downloaded data."""
    print("🔍 Testing analyze functionality...")
    
    service = FaceFusionService()
    
    # Test with S3 image
    s3_image = "s3://facefusiondemo/b3b13bbd-ae5a-44bd-80df-1759d228cebd_abb01a6747d5a94f3624263bfdad93e0.jpeg"
    
    print(f"📥 Testing with S3 image: {s3_image}")
    
    request = AnalyzeRequest(target_path=s3_image)
    
    try:
        response = service.execute_analyze(request)
        
        print(f"✅ Success: {response.success}")
        print(f"📝 Message: {response.message}")
        
        if response.error_code:
            print(f"❌ Error code: {response.error_code}")
        
        if response.encoded_faces:
            print(f"👥 Found {len(response.encoded_faces)} faces:")
            for face_id, encoded_data in response.encoded_faces.items():
                print(f"   Face {face_id}: {len(encoded_data)} characters (base64)")
                
                # Show first few characters of base64 data
                preview = encoded_data[:50] + "..." if len(encoded_data) > 50 else encoded_data
                print(f"   Preview: {preview}")
        else:
            print("👥 No faces found")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()


def test_analyze_with_video():
    """Test analyze with video data."""
    print("\n🎥 Testing analyze with video...")
    
    service = FaceFusionService()
    
    # Test with S3 video
    s3_video = "s3://facefusiondemo/videos/3faces_video02.mp4"
    
    print(f"📥 Testing with S3 video: {s3_video}")
    
    request = AnalyzeRequest(target_path=s3_video, frame_number=0)
    
    try:
        response = service.execute_analyze(request)
        
        print(f"✅ Success: {response.success}")
        print(f"📝 Message: {response.message}")
        
        if response.error_code:
            print(f"❌ Error code: {response.error_code}")
        
        if response.encoded_faces:
            print(f"👥 Found {len(response.encoded_faces)} faces:")
            for face_id, encoded_data in response.encoded_faces.items():
                print(f"   Face {face_id}: {len(encoded_data)} characters (base64)")
        else:
            print("👥 No faces found")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_many_faces_workflow():
    """Demonstrate the complete many faces workflow."""
    print("\n🔄 Demonstrating complete many faces workflow...")
    
    service = FaceFusionService()
    
    # Step 1: Analyze target video to get faces
    print("📹 Step 1: Analyzing target video...")
    s3_video = "s3://facefusiondemo/videos/3faces_video02.mp4"
    analyze_request = AnalyzeRequest(target_path=s3_video, frame_number=0)
    
    analyze_response = service.execute_analyze(analyze_request)
    
    if not analyze_response.success:
        print(f"❌ Failed to analyze video: {analyze_response.message}")
        return
    
    print(f"✅ Found {len(analyze_response.encoded_faces)} faces in video")
    
    # Step 2: Use the first detected face for mapping
    if analyze_response.encoded_faces:
        first_face_id = list(analyze_response.encoded_faces.keys())[0]
        first_face_data = analyze_response.encoded_faces[first_face_id]
        
        print(f"🎯 Using face {first_face_id} for mapping")
        print(f"   Face data length: {len(first_face_data)} characters")
        
        # This is what you would use in the HeadlessRunRequest for many faces
        faces_mapping = {
            first_face_id: first_face_data
        }
        
        print("📋 Faces mapping created:")
        print(f"   {first_face_id}: {first_face_data[:50]}...")
        
        print("\n💡 To use this in many faces swap:")
        print("   1. Create HeadlessRunRequest with:")
        print("      - source_paths: [path_to_source_face_image]")
        print("      - target_path: s3://facefusiondemo/videos/3faces_video02.mp4")
        print("      - face_selector_mode: 'reference'")
        print(f"      - faces_mapping: {{'0': '{first_face_data[:30]}...'}}")
        print("   2. Call execute_headless_run()")


if __name__ == "__main__":
    test_analyze_with_real_data()
    test_analyze_with_video()
    demonstrate_many_faces_workflow()
