"""
History Buffer - Circular buffer for inspection history
"""

import logging
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class InspectionRecord:
    """Single inspection record"""

    id: str
    timestamp: datetime
    image_id: str
    result: str  # PASS/FAIL/ERROR
    summary: str
    thumbnail_base64: Optional[str]
    processing_time_ms: int
    detections: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class HistoryBuffer:
    """Circular buffer for maintaining inspection history"""

    def __init__(self, max_size: int = 100):
        """
        Initialize History Buffer

        Args:
            max_size: Maximum number of inspections to store
        """
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)

        # Statistics
        self.total_inspections = 0
        self.pass_count = 0
        self.fail_count = 0
        self.error_count = 0
        self.total_processing_time = 0

        # Thread safety (RLock allows reentrant locking)
        self.lock = RLock()

        logger.info(f"History Buffer initialized with max size: {max_size}")

    def add_inspection(
        self,
        image_id: str,
        result: str,
        detections: List[Dict[str, Any]],
        processing_time_ms: int,
        thumbnail_base64: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add inspection record to history

        Args:
            image_id: Image identifier
            result: PASS/FAIL/ERROR
            detections: List of detection results
            processing_time_ms: Processing time in milliseconds
            thumbnail_base64: Optional thumbnail
            metadata: Optional metadata

        Returns:
            Inspection ID
        """
        with self.lock:
            # Generate inspection ID
            inspection_id = f"hist_{uuid.uuid4().hex[:8]}"

            # Create summary
            passed = sum(1 for d in detections if d.get("found", False))
            total = len(detections)
            summary = f"{passed}/{total} checks passed"

            # Create record
            record = InspectionRecord(
                id=inspection_id,
                timestamp=datetime.now(),
                image_id=image_id,
                result=result,
                summary=summary,
                thumbnail_base64=thumbnail_base64,
                processing_time_ms=processing_time_ms,
                detections=detections,
                metadata=metadata or {},
            )

            # Add to buffer
            self.buffer.append(record)

            # Update statistics
            self.total_inspections += 1
            self.total_processing_time += processing_time_ms

            if result == "PASS":
                self.pass_count += 1
            elif result == "FAIL":
                self.fail_count += 1
            else:
                self.error_count += 1

            logger.debug(f"Added inspection {inspection_id}: {result} - {summary}")
            return inspection_id

    def get_inspection(self, inspection_id: str) -> Optional[InspectionRecord]:
        """Get specific inspection by ID"""
        with self.lock:
            for record in self.buffer:
                if record.id == inspection_id:
                    return record
        return None

    def get_recent(
        self, limit: int = 10, result_filter: Optional[str] = None
    ) -> List[InspectionRecord]:
        """
        Get recent inspections

        Args:
            limit: Maximum number of records to return
            result_filter: Filter by result (PASS/FAIL/ERROR)

        Returns:
            List of inspection records
        """
        with self.lock:
            records = list(self.buffer)

            # Apply filter
            if result_filter:
                records = [r for r in records if r.result == result_filter]

            # Sort by timestamp (newest first)
            records.sort(key=lambda x: x.timestamp, reverse=True)

            # Apply limit
            return records[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get inspection statistics"""
        with self.lock:
            if self.total_inspections == 0:
                return {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                    "success_rate": 0.0,
                    "avg_time_ms": 0,
                    "buffer_usage": 0,
                }

            success_rate = (self.pass_count / self.total_inspections) * 100
            avg_time = self.total_processing_time / self.total_inspections

            # Calculate recent statistics (last hour)
            recent_cutoff = datetime.now() - timedelta(hours=1)
            recent_records = [r for r in self.buffer if r.timestamp > recent_cutoff]

            recent_stats = {
                "total": len(recent_records),
                "passed": sum(1 for r in recent_records if r.result == "PASS"),
                "failed": sum(1 for r in recent_records if r.result == "FAIL"),
            }

            return {
                "total": self.total_inspections,
                "passed": self.pass_count,
                "failed": self.fail_count,
                "errors": self.error_count,
                "success_rate": round(success_rate, 2),
                "avg_time_ms": round(avg_time, 2),
                "buffer_usage": len(self.buffer),
                "buffer_max": self.max_size,
                "recent_hour": recent_stats,
            }

    def get_time_series(
        self, interval_minutes: int = 5, duration_hours: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for charting

        Args:
            interval_minutes: Grouping interval
            duration_hours: Total duration to analyze

        Returns:
            List of time buckets with counts
        """
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=duration_hours)

            # Create time buckets
            buckets = []
            current_time = cutoff

            while current_time < now:
                bucket_end = current_time + timedelta(minutes=interval_minutes)

                # Count inspections in this bucket
                bucket_records = [
                    r for r in self.buffer if current_time <= r.timestamp < bucket_end
                ]

                buckets.append(
                    {
                        "timestamp": current_time.isoformat(),
                        "total": len(bucket_records),
                        "passed": sum(1 for r in bucket_records if r.result == "PASS"),
                        "failed": sum(1 for r in bucket_records if r.result == "FAIL"),
                    }
                )

                current_time = bucket_end

            return buckets

    def clear(self):
        """Clear all history"""
        with self.lock:
            self.buffer.clear()
            self.total_inspections = 0
            self.pass_count = 0
            self.fail_count = 0
            self.error_count = 0
            self.total_processing_time = 0

            logger.info("History buffer cleared")

    def export_to_dict(self) -> Dict[str, Any]:
        """Export history to dictionary"""
        with self.lock:
            return {
                "inspections": [
                    {
                        "id": r.id,
                        "timestamp": r.timestamp.isoformat(),
                        "image_id": r.image_id,
                        "result": r.result,
                        "summary": r.summary,
                        "processing_time_ms": r.processing_time_ms,
                        "detections": r.detections,
                        "metadata": r.metadata,
                    }
                    for r in self.buffer
                ],
                "statistics": self.get_statistics(),
            }

    def import_from_dict(self, data: Dict[str, Any]):
        """Import history from dictionary"""
        with self.lock:
            self.clear()

            for record_data in data.get("inspections", []):
                record = InspectionRecord(
                    id=record_data["id"],
                    timestamp=datetime.fromisoformat(record_data["timestamp"]),
                    image_id=record_data["image_id"],
                    result=record_data["result"],
                    summary=record_data["summary"],
                    thumbnail_base64=record_data.get("thumbnail_base64"),
                    processing_time_ms=record_data["processing_time_ms"],
                    detections=record_data["detections"],
                    metadata=record_data.get("metadata", {}),
                )

                self.buffer.append(record)

                # Update statistics
                self.total_inspections += 1
                if record.result == "PASS":
                    self.pass_count += 1
                elif record.result == "FAIL":
                    self.fail_count += 1
                else:
                    self.error_count += 1

            logger.info(f"Imported {len(self.buffer)} inspection records")

    def get_failure_analysis(self) -> Dict[str, Any]:
        """Analyze failure patterns"""
        with self.lock:
            failures = [r for r in self.buffer if r.result == "FAIL"]

            if not failures:
                return {"total_failures": 0, "common_failures": [], "failure_rate": 0.0}

            # Analyze which detections fail most often
            failure_counts = {}

            for record in failures:
                for detection in record.detections:
                    if not detection.get("found", True):
                        name = detection.get("name", "Unknown")
                        failure_counts[name] = failure_counts.get(name, 0) + 1

            # Sort by frequency
            common_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total_failures": len(failures),
                "common_failures": [
                    {"name": name, "count": count} for name, count in common_failures
                ],
                "failure_rate": (len(failures) / len(self.buffer)) * 100 if self.buffer else 0.0,
            }
