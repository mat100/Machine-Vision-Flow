"""
Image API Router - Image processing operations
"""

import logging

import cv2
from fastapi import APIRouter, Depends

from api.dependencies import get_image_service
from api.exceptions import safe_endpoint
from core.image_utils import ImageUtils
from schemas import ROIExtractRequest, ROIExtractResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract-roi")
@safe_endpoint
async def extract_roi(
    request: ROIExtractRequest, image_service=Depends(get_image_service)
) -> ROIExtractResponse:
    """
    Extract Region of Interest thumbnail from an image.

    This endpoint extracts a rectangular region from an existing image
    and returns a thumbnail of that region. The original image_id remains
    unchanged, only the roi and thumbnail are updated.

    Args:
        request: ROI extraction request with image_id and roi coordinates
        image_service: Image service dependency

    Returns:
        ROIExtractResponse with thumbnail and clipped bounding_box
    """
    # Extract ROI from source image (clipped to image bounds)
    # request.roi is already a Pydantic ROI model - pass directly
    roi_image = image_service.get_image_with_roi(
        image_id=request.image_id, roi=request.roi, safe_mode=True
    )

    # Create thumbnail directly from the cropped image
    from core.constants import ImageConstants

    # Resize to thumbnail size (max width 320px)
    height, width = roi_image.shape[:2]
    max_width = ImageConstants.DEFAULT_THUMBNAIL_WIDTH
    if width > max_width:
        scale = max_width / width
        new_width = max_width
        new_height = int(height * scale)
        thumbnail_image = cv2.resize(roi_image, (new_width, new_height))
    else:
        thumbnail_image = roi_image

    # Encode to base64 using utility function
    thumbnail = ImageUtils.encode_image_to_base64(thumbnail_image, ".jpg")

    # Get actual clipped bounding box
    original_image = image_service.get_image(request.image_id)
    img_height, img_width = original_image.shape[:2]

    clipped_bbox = request.roi.model_copy()
    clipped_bbox.x = max(0, min(clipped_bbox.x, img_width - 1))
    clipped_bbox.y = max(0, min(clipped_bbox.y, img_height - 1))
    clipped_bbox.width = min(clipped_bbox.width, img_width - clipped_bbox.x)
    clipped_bbox.height = min(clipped_bbox.height, img_height - clipped_bbox.y)

    logger.info(
        f"Extracted ROI thumbnail from {request.image_id}: "
        f"{clipped_bbox.width}x{clipped_bbox.height} at ({clipped_bbox.x},{clipped_bbox.y})"
    )

    return ROIExtractResponse(success=True, thumbnail=thumbnail, bounding_box=clipped_bbox)
