"""
Camera-related API models.

This module contains request and response models for camera operations:
- Camera information and connection
- Image capture parameters
- Capture responses
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .common import ROI, Size


class CameraInfo(BaseModel):
    """Camera information"""

    id: str
    name: str
    type: str
    resolution: Size
    connected: bool


class CameraConnectRequest(BaseModel):
    """Request to connect to camera"""

    camera_id: str
    resolution: Optional[Size] = None


class CaptureParams(BaseModel):
    """Camera capture parameters."""

    class Config:
        extra = "forbid"

    roi: Optional[ROI] = Field(
        None, description="Region of interest to extract from captured image"
    )
    # Future parameters could include: resolution, format, exposure, etc.


class CaptureRequest(BaseModel):
    """Request to capture image from camera"""

    camera_id: str = Field(
        description="Camera identifier (e.g., 'usb_0', 'ip_192.168.1.100', 'test')"
    )
    params: Optional[CaptureParams] = Field(None, description="Capture parameters (ROI, etc.)")


class CameraCaptureResponse(BaseModel):
    """Response from camera capture"""

    success: bool
    image_id: str
    timestamp: datetime
    thumbnail_base64: str
    metadata: Dict[str, Any]
