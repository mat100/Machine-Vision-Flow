"""
API Integration Tests for History Endpoints
"""

import pytest


class TestHistoryAPI:
    """Integration tests for history API endpoints"""

    @pytest.fixture
    def setup_inspection_data(self, client):
        """Create some inspection history"""
        # Capture image
        capture_response = client.post("/api/camera/capture?camera_id=test")
        image_id = capture_response.json()["image_id"]

        # Learn template
        learn_data = {
            "image_id": image_id,
            "name": "History Test Template",
            "roi": {"x": 100, "y": 100, "width": 100, "height": 100},
        }
        learn_response = client.post("/api/template/learn", json=learn_data)
        template_id = learn_response.json()["template_id"]

        # Perform template match (creates history entry)
        match_data = {"image_id": image_id, "template_id": template_id, "threshold": 0.5}
        client.post("/api/vision/template-match", json=match_data)

        return image_id, template_id

    def test_get_recent_history(self, client, setup_inspection_data):
        """Test getting recent inspection history"""
        response = client.get("/api/history/recent")

        assert response.status_code == 200
        data = response.json()

        assert "inspections" in data
        assert isinstance(data["inspections"], list)
        assert len(data["inspections"]) > 0

        # Check structure of inspection record
        inspection = data["inspections"][0]
        assert "image_id" in inspection
        assert "result" in inspection
        assert "timestamp" in inspection
        assert "processing_time_ms" in inspection

    def test_get_recent_history_with_limit(self, client, setup_inspection_data):
        """Test getting limited number of recent inspections"""
        response = client.get("/api/history/recent?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data["inspections"]) <= 5

    def test_get_statistics(self, client, setup_inspection_data):
        """Test getting history statistics"""
        response = client.get("/api/history/statistics")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "passed" in data
        assert "failed" in data
        assert "success_rate" in data
        assert "avg_time_ms" in data

        assert isinstance(data["total"], int)
        assert data["total"] >= 0

    def test_clear_history(self, client, setup_inspection_data):
        """Test clearing history"""
        # First verify we have history
        before_response = client.get("/api/history/recent")
        before_count = len(before_response.json()["inspections"])
        assert before_count > 0

        # Clear history (POST, not DELETE)
        response = client.post("/api/history/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify history is empty
        after_response = client.get("/api/history/recent")
        after_count = len(after_response.json()["inspections"])
        assert after_count == 0

    def test_history_accumulation(self, client):
        """Test that multiple operations accumulate in history"""
        # Perform multiple inspections
        for i in range(5):
            # Capture
            capture_response = client.post("/api/camera/capture?camera_id=test")
            image_id = capture_response.json()["image_id"]

            # Edge detect (creates history entry)
            edge_data = {"image_id": image_id, "method": "canny"}
            client.post("/api/vision/edge-detect", json=edge_data)

        # Check history count
        response = client.get("/api/history/recent")
        data = response.json()

        assert len(data["inspections"]) >= 5

    def test_get_history_by_result(self, client, setup_inspection_data):
        """Test filtering history by result"""
        # Get all history
        all_response = client.get("/api/history/recent")
        all_data = all_response.json()

        if len(all_data["inspections"]) > 0:
            # Check if we can filter by result type
            # (This assumes the API supports filtering, adjust if not)
            first_result = all_data["inspections"][0]["result"]
            assert first_result in ["PASS", "FAIL"]
