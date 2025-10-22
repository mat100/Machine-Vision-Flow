"""
History API Router - Inspection history management
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Query

from api.models import HistoryResponse, InspectionRecord

logger = logging.getLogger(__name__)

router = APIRouter()


def get_managers(request: Request):
    """Get managers from app state"""
    return {
        'history_buffer': request.app.state.history_buffer()
    }


@router.get("/recent")
async def get_recent_history(
    limit: int = Query(10, ge=1, le=100),
    result_filter: Optional[str] = Query(None, regex="^(PASS|FAIL|ERROR)$"),
    managers=Depends(get_managers)
) -> HistoryResponse:
    """Get recent inspection history"""
    try:
        history_buffer = managers['history_buffer']

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
                detections=r.detections
            )
            for r in records
        ]

        # Get statistics
        stats = history_buffer.get_statistics()

        return HistoryResponse(
            inspections=inspections,
            statistics=stats
        )

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{inspection_id}")
async def get_inspection(
    inspection_id: str,
    managers=Depends(get_managers)
) -> InspectionRecord:
    """Get specific inspection details"""
    try:
        history_buffer = managers['history_buffer']

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
            detections=record.detections
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get inspection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_history(managers=Depends(get_managers)) -> dict:
    """Clear all history"""
    try:
        history_buffer = managers['history_buffer']
        history_buffer.clear()

        return {
            "success": True,
            "message": "History cleared"
        }

    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(managers=Depends(get_managers)) -> dict:
    """Get detailed statistics"""
    try:
        history_buffer = managers['history_buffer']
        return history_buffer.get_statistics()

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/failures")
async def get_failure_analysis(managers=Depends(get_managers)) -> dict:
    """Analyze failure patterns"""
    try:
        history_buffer = managers['history_buffer']
        return history_buffer.get_failure_analysis()

    except Exception as e:
        logger.error(f"Failed to get failure analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeseries")
async def get_time_series(
    interval_minutes: int = Query(5, ge=1, le=60),
    duration_hours: int = Query(1, ge=1, le=24),
    managers=Depends(get_managers)
) -> dict:
    """Get time series data for charting"""
    try:
        history_buffer = managers['history_buffer']
        data = history_buffer.get_time_series(interval_minutes, duration_hours)

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Failed to get time series: {e}")
        raise HTTPException(status_code=500, detail=str(e))