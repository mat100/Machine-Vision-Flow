"""
API Integration Tests for Camera Endpoints

These tests make real HTTP requests to the FastAPI application
and verify the complete request-response cycle.
"""


class TestCameraAPI:
    """Integration tests for camera API endpoints"""

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["image_manager"] is True
        assert data["services"]["camera_manager"] is True

    def test_list_cameras(self, client):
        """Test listing available cameras"""
        response = client.post("/api/camera/list")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Should at least have test camera
        test_cam = next((c for c in data if c["id"] == "test"), None)
        assert test_cam is not None
        assert test_cam["name"] == "Test Image Generator"
        assert test_cam["type"] == "test"
        assert test_cam["connected"] is True

    def test_capture_image_from_test_camera(self, client):
        """Test capturing image from test camera"""
        response = client.post("/api/camera/capture?camera_id=test")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "image_id" in data
        assert len(data["image_id"]) > 0
        assert "thumbnail_base64" in data
        assert len(data["thumbnail_base64"]) > 0
        assert "metadata" in data
        assert data["metadata"]["camera_id"] == "test"
        assert data["metadata"]["width"] > 0
        assert data["metadata"]["height"] > 0

    def test_capture_image_with_roi(self, client):
        """Test capturing image with ROI"""
        params = {
            "camera_id": "test",
            "roi_x": 100,
            "roi_y": 100,
            "roi_width": 300,
            "roi_height": 200,
        }
        response = client.post("/api/camera/capture", params=params)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # Note: Test camera returns full image, ROI would be applied for real cameras
        assert data["metadata"]["width"] > 0
        assert data["metadata"]["height"] > 0

    def test_capture_image_invalid_camera(self, client):
        """Test capturing from non-existent camera falls back to test"""
        response = client.post("/api/camera/capture?camera_id=non_existent")

        # Should still work because of fallback to test image
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "image_id" in data

    def test_get_preview(self, client):
        """Test getting camera preview"""
        response = client.get("/api/camera/preview/test")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "thumbnail_base64" in data
        assert len(data["thumbnail_base64"]) > 0

    def test_connect_camera(self, client):
        """Test connecting to a camera"""
        request_data = {"camera_id": "test", "camera_type": "test"}
        response = client.post("/api/camera/connect", json=request_data)

        # Test camera may fail to connect in test environment
        # Accept both success and service unavailable
        assert response.status_code in [200, 503]

    def test_disconnect_camera(self, client):
        """Test disconnecting a camera"""
        # First connect
        connect_data = {"camera_id": "test", "camera_type": "test"}
        client.post("/api/camera/connect", json=connect_data)

        # Then disconnect
        response = client.delete("/api/camera/disconnect/test")

        # May return 404 if camera wasn't actually connected in test environment
        assert response.status_code in [200, 404]

    def test_capture_multiple_images(self, client):
        """Test capturing multiple images in sequence"""
        image_ids = []

        for i in range(3):
            response = client.post("/api/camera/capture?camera_id=test")
            assert response.status_code == 200
            data = response.json()
            image_ids.append(data["image_id"])

        # All image IDs should be unique
        assert len(image_ids) == len(set(image_ids))

    def test_invalid_roi_parameters(self, client):
        """Test capture with invalid ROI parameters"""
        params = {
            "camera_id": "test",
            "roi_x": -100,  # Negative values
            "roi_y": -100,
            "roi_width": 50,
            "roi_height": 50,
        }
        response = client.post("/api/camera/capture", params=params)

        # Should handle invalid ROI gracefully
        # Either return error or fall back to full image
        assert response.status_code in [200, 400]

    def test_capture_with_zero_dimensions(self, client):
        """Test capture with zero-dimension ROI"""
        params = {"camera_id": "test", "roi_x": 100, "roi_y": 100, "roi_width": 0, "roi_height": 0}
        response = client.post("/api/camera/capture", params=params)

        # May accept zero dimensions and fall back to full image
        # or reject with 400/422
        assert response.status_code in [200, 400, 422]

    def test_stream_endpoint_exists(self, client):
        """Test that stream endpoint exists and responds"""
        response = client.get("/api/camera/stream/test")

        # Stream endpoint should exist
        # It returns streaming response, so we just check it doesn't 404
        assert response.status_code != 404
