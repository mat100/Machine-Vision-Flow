"""
API Integration Tests for Vision Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from main import app
import base64
import numpy as np
import cv2


class TestVisionAPI:
    """Integration tests for vision API endpoints"""

    @pytest.fixture
    def captured_image_id(self, client):
        """Capture an image and return its ID"""
        response = client.post("/api/camera/capture?camera_id=test")
        return response.json()["image_id"]

    @pytest.fixture
    def template_id(self, client, captured_image_id):
        """Create a template from captured image"""
        request_data = {
            "image_id": captured_image_id,
            "name": "Test Template",
            "description": "Template for integration tests",
            "roi": {
                "x": 100,
                "y": 100,
                "width": 100,
                "height": 100
            }
        }
        response = client.post("/api/template/learn", json=request_data)
        return response.json()["template_id"]

    def test_template_match_basic(self, client, captured_image_id, template_id):
        """Test basic template matching"""
        request_data = {
            "image_id": captured_image_id,
            "template_id": template_id,
            "method": "TM_CCOEFF_NORMED",
            "threshold": 0.5
        }
        response = client.post("/api/vision/template-match", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "found" in data
        assert "matches" in data
        assert isinstance(data["matches"], list)
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] > 0
        assert "thumbnail_base64" in data

    def test_template_match_with_roi(self, client, captured_image_id, template_id):
        """Test template matching with ROI"""
        request_data = {
            "image_id": captured_image_id,
            "template_id": template_id,
            "method": "TM_CCOEFF_NORMED",
            "threshold": 0.7,
            "roi": {
                "x": 50,
                "y": 50,
                "width": 400,
                "height": 300
            }
        }
        response = client.post("/api/vision/template-match", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_template_match_high_threshold(self, client, captured_image_id, template_id):
        """Test template matching with very high threshold"""
        request_data = {
            "image_id": captured_image_id,
            "template_id": template_id,
            "method": "TM_CCOEFF_NORMED",
            "threshold": 0.99  # Very high threshold
        }
        response = client.post("/api/vision/template-match", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # High threshold might result in no matches
        assert "matches" in data

    def test_template_match_invalid_image(self, client, template_id):
        """Test template matching with non-existent image"""
        request_data = {
            "image_id": "non-existent-id",
            "template_id": template_id,
            "threshold": 0.8
        }
        response = client.post("/api/vision/template-match", json=request_data)

        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data

    def test_template_match_invalid_template(self, client, captured_image_id):
        """Test template matching with non-existent template"""
        request_data = {
            "image_id": captured_image_id,
            "template_id": "non-existent-template",
            "threshold": 0.8
        }
        response = client.post("/api/vision/template-match", json=request_data)

        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data

    def test_template_match_different_methods(self, client, captured_image_id, template_id):
        """Test different template matching methods"""
        methods = [
            "TM_CCOEFF_NORMED",
            "TM_CCORR_NORMED",
            "TM_SQDIFF_NORMED"
        ]

        for method in methods:
            request_data = {
                "image_id": captured_image_id,
                "template_id": template_id,
                "method": method,
                "threshold": 0.5
            }
            response = client.post("/api/vision/template-match", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_edge_detect_canny(self, client, captured_image_id):
        """Test Canny edge detection"""
        request_data = {
            "image_id": captured_image_id,
            "method": "canny"
        }
        response = client.post("/api/vision/edge-detect", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "edges_found" in data
        assert "contour_count" in data
        assert isinstance(data["contour_count"], int)
        assert "edge_pixels" in data
        assert "edge_ratio" in data
        assert "processing_time_ms" in data
        assert "thumbnail_base64" in data

    def test_edge_detect_all_methods(self, client, captured_image_id):
        """Test all edge detection methods"""
        methods = ["canny", "sobel", "laplacian", "scharr", "prewitt", "roberts"]

        for method in methods:
            request_data = {
                "image_id": captured_image_id,
                "method": method
            }
            response = client.post("/api/vision/edge-detect", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["contour_count"] >= 0

    def test_edge_detect_with_params(self, client, captured_image_id):
        """Test edge detection with custom parameters"""
        request_data = {
            "image_id": captured_image_id,
            "method": "canny",
            "params": {
                "canny_low": 50,
                "canny_high": 150,
                "blur_size": 5
            }
        }
        response = client.post("/api/vision/edge-detect", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_edge_detect_with_roi(self, client, captured_image_id):
        """Test edge detection with ROI"""
        request_data = {
            "image_id": captured_image_id,
            "method": "canny",
            "roi": {
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 200
            }
        }
        response = client.post("/api/vision/edge-detect", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_edge_detect_invalid_image(self, client):
        """Test edge detection with non-existent image"""
        request_data = {
            "image_id": "non-existent-id",
            "method": "canny"
        }
        response = client.post("/api/vision/edge-detect", json=request_data)

        assert response.status_code == 404

    def test_edge_detect_with_preprocessing(self, client, captured_image_id):
        """Test edge detection with preprocessing options"""
        request_data = {
            "image_id": captured_image_id,
            "method": "canny",
            "preprocessing": {
                "denoise": True,
                "enhance_contrast": True
            }
        }
        response = client.post("/api/vision/edge-detect", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_blob_detect_placeholder(self, client, captured_image_id):
        """Test blob detection endpoint (placeholder)"""
        request_data = {
            "image_id": captured_image_id
        }
        response = client.post("/api/vision/blob-detect", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Currently returns placeholder message
        assert "message" in data or "blob_count" in data
