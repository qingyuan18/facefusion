#!/usr/bin/env python3
"""
Test script for real-time stream processing functionality.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from facefusion.stream_processor import StreamProcessor
    from facefusion.stream_splitter import StreamSplitter
    from facefusion.async_face_processor import AsyncFaceProcessor
    from facefusion import state_manager, logger
except ImportError as e:
    print(f"Error importing FaceFusion modules: {e}")
    print("Make sure FaceFusion is properly installed and configured.")
    sys.exit(1)


async def test_stream_splitter():
    """Test the stream splitter component."""
    print("Testing StreamSplitter...")
    
    # Create a test HTTP stream URL (you can replace with actual stream)
    test_stream_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    
    splitter = StreamSplitter(segment_duration=3.0)
    
    try:
        await splitter.start_splitting(test_stream_url)
        print(f"✓ Stream splitting started for: {test_stream_url}")
        
        # Wait for a few segments
        segment_count = 0
        async for segment_path in splitter.get_available_segments():
            print(f"✓ Got segment: {segment_path}")
            segment_count += 1
            
            if segment_count >= 3:  # Test with 3 segments
                break
        
        await splitter.stop_splitting()
        print("✓ Stream splitting stopped")
        
    except Exception as e:
        print(f"✗ Stream splitter test failed: {e}")
        return False
    finally:
        splitter.cleanup()
    
    return True


async def test_face_processor():
    """Test the async face processor component."""
    print("Testing AsyncFaceProcessor...")
    
    # Create a test source face image (you need to provide a real image path)
    source_face_path = "path/to/source/face.jpg"  # Replace with actual path
    
    if not os.path.exists(source_face_path):
        print(f"✗ Source face image not found: {source_face_path}")
        print("Please provide a valid source face image path")
        return False
    
    processor = AsyncFaceProcessor(
        source_face_path=source_face_path,
        max_workers=2
    )
    
    try:
        # Test with a sample video segment (you need to provide a real video path)
        test_video_path = "path/to/test/video.mp4"  # Replace with actual path
        
        if not os.path.exists(test_video_path):
            print(f"✗ Test video not found: {test_video_path}")
            print("Please provide a valid test video path")
            return False
        
        result = await processor.process_segment(test_video_path, "test_segment_001")
        
        if result.success:
            print(f"✓ Face processing successful: {result.frames_processed} frames in {result.processing_time:.2f}s")
            print(f"✓ Output path: {result.output_path}")
        else:
            print(f"✗ Face processing failed: {result.error_message}")
            return False
        
        # Test statistics
        stats = processor.get_stats()
        print(f"✓ Processing stats: {stats}")
        
    except Exception as e:
        print(f"✗ Face processor test failed: {e}")
        return False
    finally:
        await processor.shutdown()
    
    return True


async def test_stream_processor():
    """Test the complete stream processor."""
    print("Testing StreamProcessor...")
    
    # Create a test source face image (you need to provide a real image path)
    source_face_path = "path/to/source/face.jpg"  # Replace with actual path
    
    if not os.path.exists(source_face_path):
        print(f"✗ Source face image not found: {source_face_path}")
        print("Please provide a valid source face image path")
        return False
    
    # Test stream URL
    test_stream_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    
    processor = StreamProcessor(
        source_face_path=source_face_path,
        segment_duration=3.0,
        max_workers=2
    )
    
    try:
        print(f"✓ StreamProcessor initialized with session_id: {processor.get_session_id()}")
        
        # Process stream for a short time
        segment_count = 0
        start_time = time.time()
        
        async for segment_id, segment_data, metadata in processor.process_stream(test_stream_url):
            print(f"✓ Processed segment: {segment_id}")
            print(f"  - Size: {len(segment_data)} bytes")
            print(f"  - Metadata: {metadata}")
            
            segment_count += 1
            
            # Stop after 3 segments or 30 seconds
            if segment_count >= 3 or (time.time() - start_time) > 30:
                break
        
        # Get final statistics
        stats = processor.get_stats()
        print(f"✓ Final stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        print(f"✗ Stream processor test failed: {e}")
        return False
    finally:
        await processor.stop_async()
    
    return True


async def test_api_models():
    """Test the API models."""
    print("Testing API models...")
    
    try:
        from api.models import StreamProcessRequest, StreamProcessResponse, StreamStatusResponse
        
        # Test request model
        request = StreamProcessRequest(
            stream_url="rtmp://example.com/live/stream",
            source_face_path="path/to/source.jpg",
            segment_duration=5.0,
            max_workers=4
        )
        print(f"✓ StreamProcessRequest created: {request.stream_url}")
        
        # Test response model
        response = StreamProcessResponse(
            success=True,
            session_id="test-session-123",
            message="Stream processing started",
            websocket_url="/api/v1/stream/ws/test-session-123"
        )
        print(f"✓ StreamProcessResponse created: {response.session_id}")
        
        # Test status model
        status = StreamStatusResponse(
            session_id="test-session-123",
            status="active",
            message="Processing active",
            segments_processed=10,
            processing_fps=2.5
        )
        print(f"✓ StreamStatusResponse created: {status.status}")
        
    except Exception as e:
        print(f"✗ API models test failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("FaceFusion Real-time Stream Processing Test Suite")
    print("=" * 60)
    
    # Configure FaceFusion state manager
    try:
        state_manager.set_item('face_detector_model', 'yolo_face')
        state_manager.set_item('face_detector_score', 0.5)
        state_manager.set_item('face_selector_mode', 'reference')
        state_manager.set_item('reference_face_distance', 0.3)
        state_manager.set_item('execution_providers', ['cpu'])
        state_manager.set_item('execution_thread_count', 4)
        state_manager.set_item('log_level', 'info')
        print("✓ FaceFusion state configured")
    except Exception as e:
        print(f"✗ Failed to configure FaceFusion state: {e}")
        return
    
    tests = [
        ("API Models", test_api_models),
        ("Stream Splitter", test_stream_splitter),
        ("Face Processor", test_face_processor),
        ("Stream Processor", test_stream_processor),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                print(f"✓ {test_name} test PASSED")
            else:
                print(f"✗ {test_name} test FAILED")
        except Exception as e:
            print(f"✗ {test_name} test ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:20} : {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    # Note: Before running this test, you need to:
    # 1. Provide valid paths for source_face_path and test_video_path
    # 2. Ensure FaceFusion is properly installed and configured
    # 3. Have a valid stream URL for testing
    
    print("Note: This test requires valid file paths and stream URLs.")
    print("Please edit the script to provide actual paths before running.")
    print("Run with: python test_stream_processing.py")
    
    # Uncomment the line below to run the tests
    # asyncio.run(main())
