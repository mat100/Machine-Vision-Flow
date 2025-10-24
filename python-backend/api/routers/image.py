"""
Image API Router - Image processing operations
"""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import get_image_service
from api.exceptions import safe_endpoint
from api.models import ROIExtractRequest, ROIExtractResponse
from core.roi_handler import ROI

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract-roi")
@safe_endpoint
async def extract_roi(
    request: ROIExtractRequest, image_service=Depends(get_image_service)
) -> ROIExtractResponse:
    """
    Extract Region of Interest from an image and store it as a new image.

    This endpoint extracts a rectangular region from an existing image
    and stores it as a separate image in the image manager.

    Args:
        request: ROI extraction request with image_id and roi coordinates
        image_service: Image service dependency

    Returns:
        ROIExtractResponse with new image_id, thumbnail, and metadata
    """
    # Convert request ROI to ROI object
    roi = ROI(
        x=request.roi.x,
        y=request.roi.y,
        width=request.roi.width,
        height=request.roi.height,
    )

    # Extract ROI from source image
    roi_image = image_service.get_image_with_roi(
        image_id=request.image_id, roi=roi, safe_mode=True  # Clip to image bounds if needed
    )

    # Store extracted ROI as new image
    metadata = {
        "source_image_id": request.image_id,
        "roi": roi.to_dict(),
        "operation": "roi_extract",
    }

    new_image_id = image_service.store_image(roi_image, metadata=metadata)

    # Create thumbnail for the extracted ROI
    thumbnail_base64 = image_service.create_thumbnail(new_image_id)

    logger.info(
        f"Extracted ROI from {request.image_id} -> {new_image_id}: "
        f"{roi.width}x{roi.height} at ({roi.x},{roi.y})"
    )

    return ROIExtractResponse(
        success=True, image_id=new_image_id, thumbnail_base64=thumbnail_base64, metadata=metadata
    )
