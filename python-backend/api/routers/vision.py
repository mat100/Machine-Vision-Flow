"""
Vision API Router - Vision processing endpoints
"""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import get_image_manager, get_vision_service, validate_vision_request
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
    # Unified validation and ROI conversion
    roi_dict = validate_vision_request(request.image_id, request.roi, image_manager)

    # Service handles all template matching logic, history recording, thumbnail
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
    # Unified validation and ROI conversion
    roi_dict = validate_vision_request(request.image_id, request.roi, image_manager)

    # Extract parameters using helper methods (eliminates 34 lines)
    params = request.get_detection_params()
    preprocessing = request.get_preprocessing_params()

    # Service handles all edge detection logic, history recording, thumbnail
    detected_objects, thumbnail_base64, processing_time = vision_service.edge_detect(
        image_id=request.image_id,
        method=request.method.lower(),
        params=params,
        preprocessing=preprocessing,
        roi=roi_dict,
        record_history=True,
    )

    return VisionResponse(
        objects=detected_objects,
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
    # Unified validation and ROI conversion
    roi_dict = validate_vision_request(request.image_id, request.roi, image_manager)

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
    # Unified validation (keep ROI as Pydantic model for service compatibility)
    validated_roi = validate_vision_request(
        request.image_id,
        request.roi,
        image_manager,
        convert_roi_to_dict=False,
    )

    # Service handles all ArUco detection logic, history recording, thumbnail
    detected_objects, thumbnail_base64, processing_time = vision_service.aruco_detect(
        image_id=request.image_id,
        dictionary=request.dictionary,
        roi=validated_roi,
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
    # Unified validation and ROI conversion
    roi_dict = validate_vision_request(request.image_id, request.roi, image_manager)

    # Service handles all rotation detection logic, history recording
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
