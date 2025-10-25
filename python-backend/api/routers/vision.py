"""
Vision API Router - Vision processing endpoints
"""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_image_manager,
    get_vision_service,
    roi_to_dict,
    validate_image_exists,
    validate_roi_bounds,
)
from api.exceptions import safe_endpoint
from api.models import (
    ArucoDetectRequest,
    ColorDetectRequest,
    EdgeDetectRequest,
    RotationDetectRequest,
    TemplateMatchRequest,
    VisionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/template-match")
@safe_endpoint
async def template_match(
    request: TemplateMatchRequest,
    vision_service=Depends(get_vision_service),
    image_manager=Depends(get_image_manager),
) -> VisionResponse:
    """
    Perform template matching on an image.

    INPUT constraints:
    - roi: Optional region to limit template search area

    OUTPUT results:
    - bounding_box: Location where template was found
    """
    # Validate image exists
    validate_image_exists(request.image_id, image_manager)

    # Validate ROI if provided
    if request.roi:
        validate_roi_bounds(request.roi, request.image_id, image_manager)

    # Convert ROI using helper (eliminates manual dict construction)
    roi_dict = roi_to_dict(request.roi)

    # Service handles all template matching logic, history recording, and thumbnail creation
    detected_objects, thumbnail_base64, processing_time = vision_service.template_match(
        image_id=request.image_id,
        template_id=request.template_id,
        method=request.method.value,
        threshold=request.threshold,
        roi=roi_dict,
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
    request: EdgeDetectRequest,
    vision_service=Depends(get_vision_service),
    image_manager=Depends(get_image_manager),
) -> VisionResponse:
    """
    Perform edge detection with multiple methods.

    INPUT constraints:
    - roi: Optional region to limit edge detection area

    OUTPUT results:
    - bounding_box: Bounding box of detected contour
    - contour: Actual contour points for precise shape representation
    """
    # Validate image exists
    validate_image_exists(request.image_id, image_manager)

    # Validate ROI if provided
    if request.roi:
        validate_roi_bounds(request.roi, request.image_id, image_manager)

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

    # Convert ROI using helper
    roi_dict = roi_to_dict(request.roi)

    # Service handles all edge detection logic, history recording, and thumbnail creation
    result, thumbnail_base64, processing_time = vision_service.edge_detect(
        image_id=request.image_id,
        method=request.method.lower(),
        params=params,
        preprocessing=preprocessing,
        roi=roi_dict,
        record_history=True,
    )

    return VisionResponse(
        objects=result["objects"],
        thumbnail_base64=thumbnail_base64,
        processing_time_ms=processing_time,
    )


@router.post("/color-detect")
@safe_endpoint
async def color_detect(
    request: ColorDetectRequest,
    vision_service=Depends(get_vision_service),
    image_manager=Depends(get_image_manager),
) -> VisionResponse:
    """
    Perform color detection with automatic dominant color recognition.

    INPUT constraints:
    - roi: Optional region for color analysis
    - contour: Optional contour points for precise masking (auto-used from msg.payload)

    OUTPUT results:
    - bounding_box: Region where color was analyzed
    """
    # Validate image exists
    validate_image_exists(request.image_id, image_manager)

    # Validate ROI if provided
    if request.roi:
        validate_roi_bounds(request.roi, request.image_id, image_manager)

    # Convert ROI using helper
    roi_dict = roi_to_dict(request.roi)

    # Call vision service
    detected_object, thumbnail_base64, processing_time = vision_service.color_detect(
        image_id=request.image_id,
        roi=roi_dict,
        contour=request.contour,
        use_contour_mask=request.use_contour_mask,
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


@router.post("/aruco-detect")
@safe_endpoint
async def aruco_detect(
    request: ArucoDetectRequest,
    vision_service=Depends(get_vision_service),
    image_manager=Depends(get_image_manager),
) -> VisionResponse:
    """
    Detect ArUco fiducial markers in image.

    INPUT constraints:
    - roi: Optional region to limit marker search area

    OUTPUT results:
    - bounding_box: Bounding box of detected marker
    - properties.marker_id: Unique marker ID
    - properties.corners: 4 corner points
    - rotation: Marker rotation in degrees (0-360)
    """
    # Validate image exists
    validate_image_exists(request.image_id, image_manager)

    # Validate ROI if provided
    if request.roi:
        validate_roi_bounds(request.roi, request.image_id, image_manager)

    # Service handles all ArUco detection logic, history recording, and thumbnail creation
    # Note: aruco_detect expects ROI as Pydantic model, not dict (different from other endpoints)
    detected_objects, thumbnail_base64, processing_time = vision_service.aruco_detect(
        image_id=request.image_id,
        dictionary=request.dictionary,
        roi=request.roi,
        params=request.params,
        record_history=True,
    )

    return VisionResponse(
        objects=detected_objects,
        thumbnail_base64=thumbnail_base64,
        processing_time_ms=processing_time,
    )


@router.post("/rotation-detect")
@safe_endpoint
async def rotation_detect(
    request: RotationDetectRequest,
    vision_service=Depends(get_vision_service),
    image_manager=Depends(get_image_manager),
) -> VisionResponse:
    """
    Detect rotation angle from contour points.

    INPUT constraints:
    - roi: Optional ROI for visualization context only (not a constraint)
    - contour: Required contour points from edge detection

    OUTPUT results:
    - rotation: Calculated rotation in degrees
    """
    # Validate image exists (needed for visualization)
    validate_image_exists(request.image_id, image_manager)

    # Validate ROI if provided (used for visualization context, not constraints)
    if request.roi:
        validate_roi_bounds(request.roi, request.image_id, image_manager)

    # Convert ROI using helper
    roi_dict = roi_to_dict(request.roi)

    # Service handles all rotation detection logic, history recording, and thumbnail creation
    detected_object, thumbnail_base64, processing_time = vision_service.rotation_detect(
        image_id=request.image_id,
        contour=request.contour,
        method=request.method,
        angle_range=request.angle_range,
        roi=roi_dict,
        record_history=True,
    )

    return VisionResponse(
        objects=[detected_object],
        thumbnail_base64=thumbnail_base64,
        processing_time_ms=processing_time,
    )
