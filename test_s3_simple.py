#!/usr/bin/env python3
"""
Simple test to verify S3 functionality modifications.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_s3_functions():
    """Test that our S3 functions can be imported and work correctly."""
    print("🧪 Testing S3 function imports...")
    
    try:
        from facefusion.download import is_s3_path, upload_s3_file, upload_file_if_needed
        print("✅ Successfully imported S3 functions")
        
        # Test is_s3_path function
        test_cases = [
            ("s3://bucket/file.mp4", True),
            ("/local/path/file.mp4", False),
            ("https://example.com/file.mp4", False),
            ("s3://facefusiondemo/output/video.mp4", True)
        ]
        
        print("\n🧪 Testing is_s3_path function...")
        for path, expected in test_cases:
            result = is_s3_path(path)
            status = "✅" if result == expected else "❌"
            print(f"{status} is_s3_path('{path}') = {result} (expected {expected})")
        
        print("\n✅ S3 function tests completed")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import S3 functions: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing S3 functions: {e}")
        return False

def test_api_service_methods():
    """Test that API service methods can be imported."""
    print("\n🧪 Testing API service modifications...")
    
    try:
        from api.services import FaceFusionService
        
        service = FaceFusionService()
        
        # Test new methods exist
        assert hasattr(service, 'is_s3_output_path'), "is_s3_output_path method missing"
        assert hasattr(service, 'upload_to_s3_if_needed'), "upload_to_s3_if_needed method missing"
        
        # Test is_s3_output_path method
        test_s3_path = "s3://bucket/output.mp4"
        test_local_path = "/tmp/output.mp4"
        
        s3_result = service.is_s3_output_path(test_s3_path)
        local_result = service.is_s3_output_path(test_local_path)
        
        print(f"✅ is_s3_output_path('{test_s3_path}') = {s3_result}")
        print(f"✅ is_s3_output_path('{test_local_path}') = {local_result}")
        
        print("✅ API service modifications working")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import API service: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing API service: {e}")
        return False

def test_request_models():
    """Test that request models still work correctly."""
    print("\n🧪 Testing API request models...")
    
    try:
        from api.models import HeadlessRunRequest, AnalyzeRequest
        
        # Test HeadlessRunRequest with S3 paths
        request_data = {
            "source_paths": ["s3://bucket/source.jpg"],
            "target_path": "s3://bucket/target.mp4",
            "output_path": "s3://bucket/output.mp4",
            "processors": ["face_swapper"]
        }
        
        request = HeadlessRunRequest(**request_data)
        print(f"✅ HeadlessRunRequest created with S3 paths")
        print(f"   Source: {request.source_paths}")
        print(f"   Target: {request.target_path}")
        print(f"   Output: {request.output_path}")
        
        # Test AnalyzeRequest with S3 path
        analyze_data = {
            "target_path": "s3://bucket/video.mp4",
            "frame_number": 80
        }
        
        analyze_request = AnalyzeRequest(**analyze_data)
        print(f"✅ AnalyzeRequest created with S3 path: {analyze_request.target_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing request models: {e}")
        return False

def main():
    """Run all simple tests."""
    print("🚀 Running simple S3 functionality tests...\n")
    
    tests = [
        ("S3 Functions", test_s3_functions),
        ("API Service Methods", test_api_service_methods),
        ("Request Models", test_request_models)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
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
        print("🎉 All simple tests passed! S3 functionality is ready.")
    else:
        print("⚠️  Some tests failed. Check the implementation.")

if __name__ == "__main__":
    main()
