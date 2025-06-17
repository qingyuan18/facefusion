"""
Unit tests for FaceFusion API services.

This test suite covers:
1. Analyze endpoint for face detection and extraction
2. Headless-run endpoint for single face swapping
3. Many faces functionality with mapping
4. Specific S3 integration tests
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import os
import base64

# Import the modules we want to test
from api.services import FaceFusionService
from api.models import HeadlessRunRequest, AnalyzeRequest


class TestFaceFusionService(unittest.TestCase):
    """Test cases for FaceFusionService class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.service = FaceFusionService()
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock S3 paths for testing
        self.test_s3_video = "s3://facefusiondemo/videos/3faces_video02.mp4"
        self.test_s3_image = "s3://facefusiondemo/b3b13bbd-ae5a-44bd-80df-1759d228cebd_abb01a6747d5a94f3624263bfdad93e0.jpeg"
        
        # Mock local paths
        self.test_local_video = os.path.join(self.temp_dir, "test_video.mp4")
        self.test_local_image = os.path.join(self.temp_dir, "test_image.jpg")
        self.test_output_path = os.path.join(self.temp_dir, "output.mp4")
        
    def tearDown(self):
        """Clean up after each test method."""
        # Clean up temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_mock_face(self) -> Mock:
        """Create a mock Face object for testing."""
        mock_face = Mock()
        mock_face.bounding_box = [100, 100, 200, 200]  # x1, y1, x2, y2
        mock_face.embedding = [0.1] * 512  # Mock 512-dimensional embedding
        return mock_face
    
    def create_mock_vision_frame(self, width: int = 640, height: int = 480):
        """Create a mock vision frame (numpy array) for testing."""
        import numpy as np
        return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


class TestAnalyzeEndpoint(TestFaceFusionService):
    """Test cases for the analyze endpoint functionality."""
    
    @patch('facefusion.vision.read_image')
    @patch('facefusion.face_analyser.get_many_faces')
    @patch('facefusion.download.download_file_if_needed')
    @patch('facefusion.download.is_s3_path')
    def test_analyze_image_success(self, mock_is_s3, mock_download, mock_get_faces, mock_read_image):
        """Test successful image analysis with face detection."""
        # Setup mocks
        mock_is_s3.return_value = False
        mock_download.return_value = self.test_local_image
        
        # Create mock vision frame
        mock_vision_frame = self.create_mock_vision_frame()
        mock_read_image.return_value = mock_vision_frame
        
        # Create mock faces
        mock_faces = [self.create_mock_face(), self.create_mock_face()]
        mock_get_faces.return_value = mock_faces
        
        # Mock frame_to_binary method
        with patch.object(self.service, 'frame_to_binary') as mock_frame_to_binary:
            mock_frame_to_binary.return_value = b'fake_image_data'
            
            # Create request
            request = AnalyzeRequest(target_path=self.test_local_image)
            
            # Execute
            response = self.service.execute_analyze(request)
            
            # Assertions
            self.assertTrue(response.success)
            self.assertIsNotNone(response.encoded_faces)
            self.assertEqual(len(response.encoded_faces), 2)
            self.assertIn("0", response.encoded_faces)
            self.assertIn("1", response.encoded_faces)
            
            # Verify the base64 encoding
            for face_id, encoded_data in response.encoded_faces.items():
                decoded_data = base64.b64decode(encoded_data)
                self.assertEqual(decoded_data, b'fake_image_data')
    
    @patch('facefusion.filesystem.is_video')
    @patch('facefusion.vision.read_video_frame')
    @patch('facefusion.face_analyser.get_many_faces')
    @patch('facefusion.download.download_file_if_needed')
    @patch('facefusion.download.is_s3_path')
    def test_analyze_video_success(self, mock_is_s3, mock_download, mock_get_faces, mock_read_video, mock_is_video):
        """Test successful video analysis with face detection."""
        # Setup mocks
        mock_is_s3.return_value = True
        mock_download.return_value = self.test_local_video
        mock_is_video.return_value = True
        
        # Create mock vision frame
        mock_vision_frame = self.create_mock_vision_frame()
        mock_read_video.return_value = mock_vision_frame
        
        # Create mock faces
        mock_faces = [self.create_mock_face()]
        mock_get_faces.return_value = mock_faces
        
        # Mock frame_to_binary method
        with patch.object(self.service, 'frame_to_binary') as mock_frame_to_binary:
            mock_frame_to_binary.return_value = b'fake_video_frame_data'
            
            # Create request for S3 video
            request = AnalyzeRequest(target_path=self.test_s3_video, frame_number=0)
            
            # Execute
            response = self.service.execute_analyze(request)
            
            # Assertions
            self.assertTrue(response.success)
            self.assertIsNotNone(response.encoded_faces)
            self.assertEqual(len(response.encoded_faces), 1)
            self.assertIn("0", response.encoded_faces)
            
            # Verify S3 download was called
            mock_download.assert_called_once_with(self.test_s3_video)
            mock_read_video.assert_called_once_with(self.test_local_video, 0)
    



class TestHeadlessRunEndpoint(TestFaceFusionService):
    """Test cases for the headless-run endpoint functionality."""
    
    @patch('subprocess.run')
    def test_headless_run_single_face_success(self, mock_subprocess):
        """Test successful single face swap using headless-run."""
        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Processing completed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Create request for single face swap
        request = HeadlessRunRequest(
            source_paths=[self.test_local_image],
            target_path=self.test_local_video,
            output_path=self.test_output_path,
            processors=["face_swapper"]
        )
        
        # Execute
        response = self.service.execute_headless_run(request)
        
        # Assertions
        self.assertTrue(response.success)
        self.assertIsNotNone(response.job_id)
        self.assertEqual(response.output_path, self.test_output_path)
        
        # Verify subprocess was called with correct arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("headless-run", call_args)
        self.assertIn("-s", call_args)
        self.assertIn(self.test_local_image, call_args)
        self.assertIn("-t", call_args)
        self.assertIn(self.test_local_video, call_args)
        self.assertIn("-o", call_args)
        self.assertIn(self.test_output_path, call_args)





class TestManyFacesEndpoint(TestFaceFusionService):
    """Test cases for the many faces functionality."""

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_many_faces_with_mapping_success(self, mock_temp_file, mock_subprocess):
        """Test successful many faces swap with face mapping."""
        # Setup mock temporary file for faces mapping
        mock_temp = Mock()
        mock_temp.name = "/tmp/faces_mapping.json"
        mock_temp_file.return_value.__enter__.return_value = mock_temp

        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Many faces processing completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Create faces mapping (simulating analyze results)
        faces_mapping = {
            "0": "base64_encoded_face_data_here"
        }

        # Create request for many faces swap
        request = HeadlessRunRequest(
            source_paths=[self.test_s3_image],
            target_path=self.test_s3_video,
            output_path=self.test_output_path,
            processors=["face_swapper"],
            face_selector_mode="reference",
            faces_mapping=faces_mapping
        )

        # Execute
        response = self.service.execute_headless_run(request)

        # Assertions
        self.assertTrue(response.success)
        self.assertIsNotNone(response.job_id)

        # Verify subprocess was called with --many parameter
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("--many", call_args)
        self.assertIn(mock_temp.name, call_args)

    def test_build_command_with_many_parameter(self):
        """Test command building with many parameter."""
        # Create faces mapping
        faces_mapping = {
            "0": "base64_face_data",
            "1": "another_base64_face_data"
        }

        # Create request
        request = HeadlessRunRequest(
            source_paths=["source1.jpg", "source2.jpg"],
            target_path="target.mp4",
            output_path="output.mp4",
            face_selector_mode="reference",
            faces_mapping=faces_mapping
        )

        # Build command
        cmd = self.service.build_command(request)

        # Assertions
        self.assertIn("headless-run", cmd)
        self.assertIn("-s", cmd)
        self.assertIn("source1.jpg", cmd)
        self.assertIn("source2.jpg", cmd)
        self.assertIn("-t", cmd)
        self.assertIn("target.mp4", cmd)
        self.assertIn("-o", cmd)
        self.assertIn("output.mp4", cmd)
        self.assertIn("--face-selector-mode", cmd)
        self.assertIn("reference", cmd)


class TestSpecificS3ManyFacesWorkflow(TestFaceFusionService):
    """Test cases for the specific S3 many faces workflow as requested."""

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_many_faces_s3_workflow_complete(self, mock_temp_file, mock_subprocess):
        """Test 4: Specific S3 many faces workflow -
        Input video: s3://facefusiondemo/videos/3faces_video02.mp4
        Source face: s3://facefusiondemo/b3b13bbd-ae5a-44bd-80df-1759d228cebd_abb01a6747d5a94f3624263bfdad93e0.jpeg
        Mapping: Replace first detected face with source face
        """
        # Setup mock temporary file for faces mapping
        mock_temp = Mock()
        mock_temp.name = "/tmp/faces_mapping.json"
        mock_temp_file.return_value.__enter__.return_value = mock_temp

        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Many faces processing completed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Simulate the face mapping from analyze results (first face)
        faces_mapping = {
            "0": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }

        # Create request for many faces swap with specific S3 paths
        request = HeadlessRunRequest(
            source_paths=[self.test_s3_image],  # S3 source image
            target_path=self.test_s3_video,     # S3 target video
            output_path=self.test_output_path,
            processors=["face_swapper"],
            face_selector_mode="reference",
            faces_mapping=faces_mapping
        )

        # Execute
        response = self.service.execute_headless_run(request)

        # Assertions
        self.assertTrue(response.success)
        self.assertIsNotNone(response.job_id)
        self.assertEqual(response.output_path, self.test_output_path)

        # Verify subprocess was called with correct parameters
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        # Check for many parameter
        self.assertIn("--many", call_args)
        self.assertIn(mock_temp.name, call_args)

        # Check for face selector mode
        self.assertIn("--face-selector-mode", call_args)
        self.assertIn("reference", call_args)


if __name__ == '__main__':
    unittest.main()
