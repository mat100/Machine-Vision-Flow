"""
Template-related API models.

This module contains request and response models for template operations:
- Template information
- Template upload and learning
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .common import ROI, Size


class TemplateInfo(BaseModel):
    """Template information"""

    id: str
    name: str
    description: Optional[str] = None
    size: Size
    created_at: datetime


class TemplateUploadResponse(BaseModel):
    """Response from template upload"""

    success: bool
    template_id: str
    name: str
    size: Size


class TemplateLearnRequest(BaseModel):
    """Request to learn template from image"""

    image_id: str
    name: str
    roi: ROI
    description: Optional[str] = None
