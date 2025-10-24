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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/template-match")
@safe_endpoint
async def template_match(
    request: TemplateMatchRequest, vision_service=Depends(get_vision_service)
) -> TemplateMatchResponse:
    """Perform template matching"""
    # Service handles all template matching logic, history recording, and thumbnail creation
    matches, thumbnail_base64, processing_time = vision_service.template_match(
        image_id=request.image_id,
        template_id=request.template_id,
        method=request.method.value,
        threshold=request.threshold,
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
    # Build params dict from explicit fields
    params = {
        # Method-specific parameters
        "canny_low": request.canny_low,
        "canny_high": request.canny_high,
        "sobel_threshold": request.sobel_threshold,
        "sobel_kernel": request.sobel_kernel,
        "laplacian_threshold": request.laplacian_threshold,
        "laplacian_kernel": request.laplacian_kernel,
        "prewitt_threshold": request.prewitt_threshold,
        "scharr_threshold": request.scharr_threshold,
        "morph_threshold": request.morph_threshold,
        "morph_kernel": request.morph_kernel,
        # Filtering parameters
        "min_contour_area": request.min_contour_area,
        "max_contour_area": request.max_contour_area,
        "min_contour_perimeter": request.min_contour_perimeter,
        "max_contour_perimeter": request.max_contour_perimeter,
        "max_contours": request.max_contours,
        "show_centers": request.show_centers,
    }

    # Build preprocessing dict from explicit fields
    preprocessing = {
        "blur_enabled": request.blur_enabled,
        "blur_kernel": request.blur_kernel,
        "bilateral_enabled": request.bilateral_enabled,
        "bilateral_d": request.bilateral_d,
        "bilateral_sigma_color": request.bilateral_sigma_color,
        "bilateral_sigma_space": request.bilateral_sigma_space,
        "morphology_enabled": request.morphology_enabled,
        "morphology_operation": request.morphology_operation,
        "morphology_kernel": request.morphology_kernel,
        "equalize_enabled": request.equalize_enabled,
    }

    # Service handles all edge detection logic, history recording, and thumbnail creation
    result, thumbnail_base64, processing_time = vision_service.edge_detect(
        image_id=request.image_id,
        method=request.method.lower(),
        params=params,
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
