"""
Vision API Router - Vision processing endpoints
"""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import get_image_manager  # Still needed for blob detection (placeholder)
from api.dependencies import get_vision_service
from api.exceptions import safe_endpoint
from api.models import (
    BlobDetectRequest,
    EdgeDetectRequest,
    TemplateMatchRequest,
    TemplateMatchResponse,
)
from core.roi_handler import ROI

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/template-match")
@safe_endpoint
async def template_match(
    request: TemplateMatchRequest, vision_service=Depends(get_vision_service)
) -> TemplateMatchResponse:
    """Perform template matching"""
    # Convert ROI from request to ROI object if provided
    roi = None
    if request.roi:
        roi = ROI(
            x=request.roi.x, y=request.roi.y, width=request.roi.width, height=request.roi.height
        )

    # Service handles all template matching logic, history recording, and thumbnail creation
    matches, thumbnail_base64, processing_time = vision_service.template_match(
        image_id=request.image_id,
        template_id=request.template_id,
        method=request.method.value,
        threshold=request.threshold,
        roi=roi,
        record_history=True,
    )

    return TemplateMatchResponse(
        success=True,
        found=len(matches) > 0,
        matches=matches,
        processing_time_ms=processing_time,
        thumbnail_base64=thumbnail_base64,
    )


@router.post("/edge-detect")
@safe_endpoint
async def edge_detect(
    request: EdgeDetectRequest, vision_service=Depends(get_vision_service)
) -> dict:
    """Perform edge detection with multiple methods"""
    # Prepare ROI if specified
    roi = None
    if request.roi:
        roi = {
            "x": request.roi.x,
            "y": request.roi.y,
            "width": request.roi.width,
            "height": request.roi.height,
        }

    # Prepare parameters
    params = request.params if hasattr(request, "params") and request.params else {}

    # Add threshold parameters to params if provided
    if hasattr(request, "threshold1"):
        params.setdefault("canny_low", request.threshold1)
    if hasattr(request, "threshold2"):
        params.setdefault("canny_high", request.threshold2)

    # Get method
    method = request.method.lower() if hasattr(request, "method") else "canny"

    # Get preprocessing options
    preprocessing = request.preprocessing if hasattr(request, "preprocessing") else None

    # Service handles all edge detection logic, history recording, and thumbnail creation
    result, thumbnail_base64, processing_time = vision_service.edge_detect(
        image_id=request.image_id,
        method=method,
        params=params,
        roi=roi,
        preprocessing=preprocessing,
        record_history=True,
    )

    return {
        "success": result["success"],
        "edges_found": result["edges_found"],
        "contour_count": result["contour_count"],
        "contours": result["contours"][:10],  # Limit to first 10 for response size
        "edge_pixels": result["edge_pixels"],
        "edge_ratio": result["edge_ratio"],
        "processing_time_ms": processing_time,
        "thumbnail_base64": thumbnail_base64,
        "visualization": (
            result["visualization"] if params.get("include_visualization", False) else None
        ),
    }


@router.post("/blob-detect")
@safe_endpoint
async def blob_detect(request: BlobDetectRequest, image_manager=Depends(get_image_manager)) -> dict:
    """Perform blob detection"""
    # Placeholder implementation
    return {
        "success": True,
        "blob_count": 0,
        "blobs": [],
        "processing_time_ms": 0,
        "message": "Blob detection not yet implemented",
    }
