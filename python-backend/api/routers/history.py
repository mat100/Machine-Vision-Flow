"""
History API Router - Inspection history management
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_history_buffer
from api.exceptions import safe_endpoint
from api.models import HistoryResponse, InspectionRecord

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recent")
@safe_endpoint
async def get_recent_history(
    limit: int = Query(10, ge=1, le=100),
    result_filter: Optional[str] = Query(None, regex="^(PASS|FAIL|ERROR)$"),
    history_buffer=Depends(get_history_buffer),
) -> HistoryResponse:
    """Get recent inspection history"""
    # Get recent records
    records = history_buffer.get_recent(limit, result_filter)

    # Convert to response models
    inspections = [
        InspectionRecord(
            id=r.id,
            timestamp=r.timestamp,
            image_id=r.image_id,
            result=r.result,
            summary=r.summary,
            thumbnail_base64=r.thumbnail_base64,
            processing_time_ms=r.processing_time_ms,
            detections=r.detections,
        )
        for r in records
    ]

    # Get statistics
    stats = history_buffer.get_statistics()

    return HistoryResponse(inspections=inspections, statistics=stats)


@router.post("/clear")
@safe_endpoint
async def clear_history(history_buffer=Depends(get_history_buffer)) -> dict:
    """Clear all history"""
    history_buffer.clear()

    return {"success": True, "message": "History cleared"}


@router.get("/statistics")
@safe_endpoint
async def get_statistics(history_buffer=Depends(get_history_buffer)) -> dict:
    """Get detailed statistics"""
    return history_buffer.get_statistics()


@router.get("/{inspection_id}")
@safe_endpoint
async def get_inspection(
    inspection_id: str, history_buffer=Depends(get_history_buffer)
) -> InspectionRecord:
    """Get specific inspection details"""
    record = history_buffer.get_inspection(inspection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    return InspectionRecord(
        id=record.id,
        timestamp=record.timestamp,
        image_id=record.image_id,
        result=record.result,
        summary=record.summary,
        thumbnail_base64=record.thumbnail_base64,
        processing_time_ms=record.processing_time_ms,
        detections=record.detections,
    )


@router.get("/analysis/failures")
@safe_endpoint
async def get_failure_analysis(history_buffer=Depends(get_history_buffer)) -> dict:
    """Analyze failure patterns"""
    return history_buffer.get_failure_analysis()


@router.get("/timeseries")
@safe_endpoint
async def get_time_series(
    interval_minutes: int = Query(5, ge=1, le=60),
    duration_hours: int = Query(1, ge=1, le=24),
    history_buffer=Depends(get_history_buffer),
) -> dict:
    """Get time series data for charting"""
    data = history_buffer.get_time_series(interval_minutes, duration_hours)

    return {"success": True, "data": data}
