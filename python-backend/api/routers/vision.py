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
    ColorDetectRequest,
    EdgeDetectRequest,
    TemplateMatchRequest,
    VisionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/template-match")
@safe_endpoint
async def template_match(
    request: TemplateMatchRequest, vision_service=Depends(get_vision_service)
) -> VisionResponse:
    """Perform template matching"""
    # Service handles all template matching logic, history recording, and thumbnail creation
    detected_objects, thumbnail_base64, processing_time = vision_service.template_match(
        image_id=request.image_id,
        template_id=request.template_id,
        method=request.method.value,
        threshold=request.threshold,
        record_history=True,
    )

    return VisionResponse(
        objects=detected_objects,
        thumbnail_base64=thumbnail_base64,
        processing_time_ms=processing_time,
    )


@router.post("/edge-detect")
@safe_endpoint
async def edge_detect(
    request: EdgeDetectRequest, vision_service=Depends(get_vision_service)
) -> VisionResponse:
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

    return VisionResponse(
        objects=result["objects"],
        thumbnail_base64=thumbnail_base64,
        processing_time_ms=processing_time,
    )


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


@router.post("/color-detect")
@safe_endpoint
async def color_detect(
    request: ColorDetectRequest, vision_service=Depends(get_vision_service)
) -> VisionResponse:
    """Perform color detection with automatic dominant color recognition"""
    # Convert ROI model to dict if provided
    roi_dict = None
    if request.roi is not None:
        roi_dict = {
            "x": request.roi.x,
            "y": request.roi.y,
            "width": request.roi.width,
            "height": request.roi.height,
        }

    # Call vision service
    detected_object, thumbnail_base64, processing_time = vision_service.color_detect(
        image_id=request.image_id,
        roi=roi_dict,
        expected_color=request.expected_color,
        min_percentage=request.min_percentage,
        method=request.method,
        record_history=True,
    )

    # Return object only if match or no expected color
    objects = []
    if detected_object.properties["match"] or request.expected_color is None:
        objects = [detected_object]

    return VisionResponse(
        objects=objects,
        thumbnail_base64=thumbnail_base64,
        processing_time_ms=processing_time,
    )
