"""
Image processing API models.

This module contains models for image operations:
- ROI extraction requests and responses
"""

from pydantic import BaseModel, Field

from .common import ROI


class ROIExtractRequest(BaseModel):
    """Request to extract ROI from image"""

    image_id: str
    roi: ROI = Field(..., description="Region of interest to extract")


class ROIExtractResponse(BaseModel):
    """Response from ROI extraction"""

    success: bool
    thumbnail: str
    bounding_box: ROI
