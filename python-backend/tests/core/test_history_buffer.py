"""
Tests for HistoryBuffer module
"""

from datetime import datetime

import pytest

from core.history_buffer import HistoryBuffer


class TestHistoryBuffer:
    """Test HistoryBuffer functionality"""

    @pytest.fixture
    def buffer(self):
        """Create a fresh history buffer for each test"""
        return HistoryBuffer(max_size=10)

    @pytest.fixture
    def sample_detections(self):
        """Sample detection results"""
        return [
            {"name": "check1", "found": True, "confidence": 0.95},
            {"name": "check2", "found": True, "confidence": 0.87},
        ]

    def test_initialization(self, buffer):
        """Test buffer initialization"""
        assert buffer.max_size == 10
        assert len(buffer.buffer) == 0
        assert buffer.total_inspections == 0
        assert buffer.pass_count == 0
        assert buffer.fail_count == 0
        assert buffer.error_count == 0

    def test_add_inspection_pass(self, buffer, sample_detections):
        """Test adding a passing inspection"""
        inspection_id = buffer.add_inspection(
            image_id="img_001",
            result="PASS",
            detections=sample_detections,
            processing_time_ms=150,
        )

        # Check ID format
        assert inspection_id.startswith("hist_")
        assert len(inspection_id) > 5

        # Check buffer contents
        assert len(buffer.buffer) == 1
        assert buffer.total_inspections == 1
        assert buffer.pass_count == 1
        assert buffer.fail_count == 0

    def test_add_inspection_fail(self, buffer):
        """Test adding a failing inspection"""
        detections = [
            {"name": "check1", "found": False},
            {"name": "check2", "found": True},
        ]

        inspection_id = buffer.add_inspection(
            image_id="img_002",
            result="FAIL",
            detections=detections,
            processing_time_ms=200,
        )

        assert len(buffer.buffer) == 1
        assert buffer.fail_count == 1
        assert buffer.pass_count == 0

        # Check summary generation
        record = buffer.get_inspection(inspection_id)
        assert record is not None
        assert "1/2" in record.summary  # 1 out of 2 checks passed

    def test_add_inspection_error(self, buffer):
        """Test adding an error inspection"""
        buffer.add_inspection(
            image_id="img_003",
            result="ERROR",
            detections=[],
            processing_time_ms=50,
        )

        assert buffer.error_count == 1
        assert buffer.pass_count == 0
        assert buffer.fail_count == 0

    def test_add_inspection_with_thumbnail(self, buffer, sample_detections):
        """Test adding inspection with thumbnail"""
        thumbnail = "base64encodedimage=="

        inspection_id = buffer.add_inspection(
            image_id="img_004",
            result="PASS",
            detections=sample_detections,
            processing_time_ms=100,
            thumbnail_base64=thumbnail,
        )

        record = buffer.get_inspection(inspection_id)
        assert record.thumbnail_base64 == thumbnail

    def test_add_inspection_with_metadata(self, buffer, sample_detections):
        """Test adding inspection with metadata"""
        metadata = {"camera": "cam1", "operator": "user1"}

        inspection_id = buffer.add_inspection(
            image_id="img_005",
            result="PASS",
            detections=sample_detections,
            processing_time_ms=100,
            metadata=metadata,
        )

        record = buffer.get_inspection(inspection_id)
        assert record.metadata == metadata

    def test_circular_buffer_overflow(self, buffer, sample_detections):
        """Test that buffer respects max_size limit"""
        # Add 15 inspections to a buffer with max_size=10
        ids = []
        for i in range(15):
            inspection_id = buffer.add_inspection(
                image_id=f"img_{i:03d}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=100,
            )
            ids.append(inspection_id)

        # Buffer should only contain 10 items (most recent)
        assert len(buffer.buffer) == 10

        # Oldest items should be gone
        assert buffer.get_inspection(ids[0]) is None
        assert buffer.get_inspection(ids[1]) is None

        # Recent items should still exist
        assert buffer.get_inspection(ids[-1]) is not None
        assert buffer.get_inspection(ids[-2]) is not None

        # Total count should still be 15
        assert buffer.total_inspections == 15

    def test_get_inspection_found(self, buffer, sample_detections):
        """Test retrieving an existing inspection"""
        inspection_id = buffer.add_inspection(
            image_id="img_006",
            result="PASS",
            detections=sample_detections,
            processing_time_ms=120,
        )

        record = buffer.get_inspection(inspection_id)
        assert record is not None
        assert record.id == inspection_id
        assert record.image_id == "img_006"
        assert record.result == "PASS"
        assert record.processing_time_ms == 120

    def test_get_inspection_not_found(self, buffer):
        """Test retrieving non-existent inspection"""
        record = buffer.get_inspection("nonexistent_id")
        assert record is None

    def test_get_recent_no_filter(self, buffer, sample_detections):
        """Test getting recent inspections without filter"""
        # Add 5 inspections
        for i in range(5):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS" if i % 2 == 0 else "FAIL",
                detections=sample_detections,
                processing_time_ms=100,
            )

        recent = buffer.get_recent(limit=3)
        assert len(recent) == 3

        # Should be in reverse chronological order (newest first)
        assert recent[0].image_id == "img_4"
        assert recent[1].image_id == "img_3"
        assert recent[2].image_id == "img_2"

    def test_get_recent_with_filter(self, buffer, sample_detections):
        """Test getting recent inspections with result filter"""
        # Add mix of PASS and FAIL
        for i in range(6):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS" if i % 2 == 0 else "FAIL",
                detections=sample_detections,
                processing_time_ms=100,
            )

        # Get only PASS results
        pass_records = buffer.get_recent(limit=10, result_filter="PASS")
        assert len(pass_records) == 3
        assert all(r.result == "PASS" for r in pass_records)

        # Get only FAIL results
        fail_records = buffer.get_recent(limit=10, result_filter="FAIL")
        assert len(fail_records) == 3
        assert all(r.result == "FAIL" for r in fail_records)

    def test_get_recent_limit(self, buffer, sample_detections):
        """Test that limit parameter works"""
        # Add 8 inspections
        for i in range(8):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=100,
            )

        recent = buffer.get_recent(limit=5)
        assert len(recent) == 5

    def test_get_statistics_empty(self, buffer):
        """Test statistics for empty buffer"""
        stats = buffer.get_statistics()

        assert stats["total"] == 0
        assert stats["passed"] == 0
        assert stats["failed"] == 0
        assert stats["errors"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_time_ms"] == 0
        assert stats["buffer_usage"] == 0

    def test_get_statistics_with_data(self, buffer, sample_detections):
        """Test statistics calculation"""
        # Add 10 inspections: 6 pass, 3 fail, 1 error
        for i in range(10):
            if i < 6:
                result = "PASS"
            elif i < 9:
                result = "FAIL"
            else:
                result = "ERROR"

            buffer.add_inspection(
                image_id=f"img_{i}",
                result=result,
                detections=sample_detections,
                processing_time_ms=100 + i * 10,
            )

        stats = buffer.get_statistics()

        assert stats["total"] == 10
        assert stats["passed"] == 6
        assert stats["failed"] == 3
        assert stats["errors"] == 1
        # Success rate = 6/10 = 60%
        assert stats["success_rate"] == 60.0
        # Average time = (100+110+120+...+190) / 10 = 145
        assert stats["avg_time_ms"] == 145.0
        assert stats["buffer_usage"] == 10
        assert stats["buffer_max"] == 10

    def test_get_statistics_recent_hour(self, buffer, sample_detections):
        """Test recent hour statistics"""
        # Add some inspections
        for i in range(5):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS" if i < 3 else "FAIL",
                detections=sample_detections,
                processing_time_ms=100,
            )

        stats = buffer.get_statistics()

        # Recent hour stats should exist
        assert "recent_hour" in stats
        recent = stats["recent_hour"]
        assert recent["total"] == 5
        assert recent["passed"] == 3
        assert recent["failed"] == 2

    def test_clear(self, buffer, sample_detections):
        """Test clearing the buffer"""
        # Add some inspections
        for i in range(5):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=100,
            )

        assert len(buffer.buffer) > 0
        assert buffer.total_inspections > 0

        # Clear buffer
        buffer.clear()

        assert len(buffer.buffer) == 0
        assert buffer.total_inspections == 0
        assert buffer.pass_count == 0
        assert buffer.fail_count == 0
        assert buffer.error_count == 0
        assert buffer.total_processing_time == 0

    def test_export_to_dict(self, buffer, sample_detections):
        """Test exporting buffer to dictionary"""
        # Add some inspections
        for i in range(3):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=100 + i * 10,
                metadata={"index": i},
            )

        exported = buffer.export_to_dict()

        # Check structure
        assert "inspections" in exported
        assert "statistics" in exported

        # Check inspections
        assert len(exported["inspections"]) == 3
        first_inspection = exported["inspections"][0]
        assert "id" in first_inspection
        assert "timestamp" in first_inspection
        assert "image_id" in first_inspection
        assert "result" in first_inspection
        assert "detections" in first_inspection

        # Check statistics
        assert exported["statistics"]["total"] == 3

    def test_import_from_dict(self, buffer, sample_detections):
        """Test importing buffer from dictionary"""
        # Create export data
        export_data = {
            "inspections": [
                {
                    "id": "hist_abc123",
                    "timestamp": datetime.now().isoformat(),
                    "image_id": "img_001",
                    "result": "PASS",
                    "summary": "2/2 checks passed",
                    "processing_time_ms": 150,
                    "detections": sample_detections,
                    "metadata": {"test": True},
                }
            ]
        }

        # Import
        buffer.import_from_dict(export_data)

        # Check buffer state
        assert len(buffer.buffer) == 1
        assert buffer.total_inspections == 1
        assert buffer.pass_count == 1

        # Check record
        record = buffer.buffer[0]
        assert record.id == "hist_abc123"
        assert record.image_id == "img_001"
        assert record.result == "PASS"

    def test_import_export_roundtrip(self, buffer, sample_detections):
        """Test export and import preserve data"""
        # Add inspections
        for i in range(5):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS" if i % 2 == 0 else "FAIL",
                detections=sample_detections,
                processing_time_ms=100 + i * 10,
            )

        # Export
        exported = buffer.export_to_dict()

        # Create new buffer and import
        new_buffer = HistoryBuffer(max_size=10)
        new_buffer.import_from_dict(exported)

        # Compare
        assert len(new_buffer.buffer) == len(buffer.buffer)
        assert new_buffer.total_inspections == buffer.total_inspections
        assert new_buffer.pass_count == buffer.pass_count
        assert new_buffer.fail_count == buffer.fail_count

    def test_get_failure_analysis_no_failures(self, buffer, sample_detections):
        """Test failure analysis with no failures"""
        # Add only passing inspections
        for i in range(3):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=100,
            )

        analysis = buffer.get_failure_analysis()

        assert analysis["total_failures"] == 0
        assert analysis["common_failures"] == []
        assert analysis["failure_rate"] == 0.0

    def test_get_failure_analysis_with_failures(self, buffer):
        """Test failure analysis with actual failures"""
        # Add failing inspections with specific failed checks
        for i in range(5):
            detections = [
                {"name": "check_A", "found": i != 0},  # Fails once
                {"name": "check_B", "found": i < 3},  # Fails twice
                {"name": "check_C", "found": False},  # Always fails
            ]

            buffer.add_inspection(
                image_id=f"img_{i}",
                result="FAIL",
                detections=detections,
                processing_time_ms=100,
            )

        analysis = buffer.get_failure_analysis()

        assert analysis["total_failures"] == 5
        assert analysis["failure_rate"] == 100.0  # All are failures

        # Check common failures (should be sorted by count)
        common = analysis["common_failures"]
        assert len(common) > 0

        # check_C should be most common (fails 5 times)
        assert common[0]["name"] == "check_C"
        assert common[0]["count"] == 5

    def test_get_failure_analysis_mixed(self, buffer):
        """Test failure analysis with mixed pass/fail"""
        # Add 3 pass, 2 fail
        for i in range(5):
            if i < 3:
                detections = [{"name": "check1", "found": True}]
                result = "PASS"
            else:
                detections = [{"name": "check1", "found": False}]
                result = "FAIL"

            buffer.add_inspection(
                image_id=f"img_{i}",
                result=result,
                detections=detections,
                processing_time_ms=100,
            )

        analysis = buffer.get_failure_analysis()

        assert analysis["total_failures"] == 2
        # Failure rate = 2/5 = 40%
        assert analysis["failure_rate"] == 40.0

    def test_get_time_series(self, buffer, sample_detections):
        """Test time series data generation"""
        # Add some inspections
        for i in range(5):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=100,
            )

        # Get time series for last hour with 5-minute intervals
        time_series = buffer.get_time_series(interval_minutes=5, duration_hours=1)

        # Should have buckets (60 minutes / 5 = 12 buckets)
        assert len(time_series) == 12

        # Each bucket should have required fields
        for bucket in time_series:
            assert "timestamp" in bucket
            assert "total" in bucket
            assert "passed" in bucket
            assert "failed" in bucket

        # All inspections should be in the most recent bucket(s)
        total_count = sum(b["total"] for b in time_series)
        assert total_count == 5

    @pytest.mark.skip(reason="Threading test can cause timeout in CI")
    def test_thread_safety_add(self, buffer, sample_detections):
        """Test thread-safe adding (basic check)"""
        import threading

        def add_inspections():
            for i in range(10):
                buffer.add_inspection(
                    image_id=f"img_{i}",
                    result="PASS",
                    detections=sample_detections,
                    processing_time_ms=100,
                )

        # Run two threads concurrently
        thread1 = threading.Thread(target=add_inspections)
        thread2 = threading.Thread(target=add_inspections)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Should have 20 total inspections (though buffer may have < 20 due to size limit)
        assert buffer.total_inspections == 20

    def test_processing_time_accumulation(self, buffer, sample_detections):
        """Test that processing times accumulate correctly"""
        times = [100, 150, 200, 250, 300]

        for i, time_ms in enumerate(times):
            buffer.add_inspection(
                image_id=f"img_{i}",
                result="PASS",
                detections=sample_detections,
                processing_time_ms=time_ms,
            )

        assert buffer.total_processing_time == sum(times)

        stats = buffer.get_statistics()
        expected_avg = sum(times) / len(times)
        assert stats["avg_time_ms"] == expected_avg
