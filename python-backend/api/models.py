"""
Pydantic models for API requests and responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Import enums from centralized location
# Re-export commonly used enums for convenience (backwards compatibility)
from core.enums import (
    AngleRange,
    ArucoDict,
    ColorMethod,
    RotationMethod,
    TemplateMethod,
    VisionObjectType,
)

# Import detection params from vision layer
# Safe to import now because vision modules use late imports (after class definitions)
from vision.aruco_detection import ArucoDetectionParams
from vision.color_detection import ColorDetectionParams
from vision.edge_detection import EdgeDetectionParams
from vision.rotation_detection import RotationDetectionParams
from vision.template_matching import TemplateMatchParams

#  Explicitly declare public API for re-export
__all__ = [
    "AngleRange",
    "ArucoDict",
    "ColorMethod",
    "RotationMethod",
    "TemplateMethod",
    "VisionObjectType",
    "EdgeDetectionParams",
    "ColorDetectionParams",
    "ArucoDetectionParams",
    "RotationDetectionParams",
]


# Common models
class ROI(BaseModel):
    """
    Region of Interest - unified implementation.

    Represents a rectangular region in an image with utility methods for
    geometric operations, validation, and conversions.
    """

    x: int = Field(..., ge=0, description="X coordinate")
    y: int = Field(..., ge=0, description="Y coordinate")
    width: int = Field(..., gt=0, description="Width")
    height: int = Field(..., gt=0, description="Height")

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for service layer compatibility."""
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ROI":
        """Create ROI from dictionary."""
        return cls(
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
        )

    @classmethod
    def from_points(cls, x1: int, y1: int, x2: int, y2: int) -> "ROI":
        """Create ROI from two corner points."""
        return cls(x=min(x1, x2), y=min(y1, y2), width=abs(x2 - x1), height=abs(y2 - y1))

    @property
    def x2(self) -> int:
        """Get right edge coordinate."""
        return self.x + self.width

    @property
    def y2(self) -> int:
        """Get bottom edge coordinate."""
        return self.y + self.height

    @property
    def center_point(self) -> tuple[int, int]:
        """Get center point of ROI as (x, y) tuple."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area_pixels(self) -> int:
        """Get area of ROI in pixels."""
        return self.width * self.height

    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside ROI."""
        return self.x <= x < self.x2 and self.y <= y < self.y2

    def intersects(self, other: "ROI") -> bool:
        """Check if this ROI intersects with another."""
        return not (
            self.x2 <= other.x or other.x2 <= self.x or self.y2 <= other.y or other.y2 <= self.y
        )

    def intersection(self, other: "ROI") -> Optional["ROI"]:
        """Get intersection with another ROI, or None if no intersection."""
        if not self.intersects(other):
            return None

        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)

        return ROI.from_points(x1, y1, x2, y2)

    def union(self, other: "ROI") -> "ROI":
        """Get union with another ROI (smallest rectangle containing both)."""
        x1 = min(self.x, other.x)
        y1 = min(self.y, other.y)
        x2 = max(self.x2, other.x2)
        y2 = max(self.y2, other.y2)

        return ROI.from_points(x1, y1, x2, y2)

    def scale(self, factor: float, from_center: bool = False) -> "ROI":
        """
        Scale ROI by factor.

        Args:
            factor: Scale factor (e.g., 1.5 for 150%)
            from_center: If True, scale from center; if False, scale from top-left

        Returns:
            New scaled ROI
        """
        new_width = int(self.width * factor)
        new_height = int(self.height * factor)

        if from_center:
            # Scale from center
            cx, cy = self.center_point
            new_x = cx - new_width // 2
            new_y = cy - new_height // 2
        else:
            # Scale from top-left
            new_x = self.x
            new_y = self.y

        return ROI(x=new_x, y=new_y, width=new_width, height=new_height)

    def expand(self, pixels: int) -> "ROI":
        """Expand ROI by pixels in all directions."""
        return ROI(
            x=self.x - pixels,
            y=self.y - pixels,
            width=self.width + 2 * pixels,
            height=self.height + 2 * pixels,
        )

    def clip(self, image_width: int, image_height: int) -> "ROI":
        """
        Clip ROI to image bounds.

        Args:
            image_width: Maximum width (image width)
            image_height: Maximum height (image height)

        Returns:
            Clipped ROI that fits within image bounds
        """
        x = max(0, min(self.x, image_width))
        y = max(0, min(self.y, image_height))
        x2 = max(0, min(self.x2, image_width))
        y2 = max(0, min(self.y2, image_height))

        return ROI.from_points(x, y, x2, y2)

    def is_valid(
        self, image_width: Optional[int] = None, image_height: Optional[int] = None
    ) -> bool:
        """
        Check if ROI is valid.

        Args:
            image_width: Optional image width for bounds checking
            image_height: Optional image height for bounds checking

        Returns:
            True if ROI is valid
        """
        # Basic validation (Pydantic already ensures width/height > 0 and x/y >= 0)
        # But we check again for runtime safety
        if self.width <= 0 or self.height <= 0:
            return False

        if self.x < 0 or self.y < 0:
            return False

        # Image bounds validation if provided
        if image_width is not None and self.x2 > image_width:
            return False

        if image_height is not None and self.y2 > image_height:
            return False

        return True


class Point(BaseModel):
    """2D Point"""

    x: float
    y: float


class Size(BaseModel):
    """Image size"""

    width: int
    height: int


# Standard vision detection models
class VisionObject(BaseModel):
    """
    Universal interface for any vision processing object.
    (camera capture, contour, template, color region, etc.)
    Provides standardized location, geometry, and quality information.
    """

    # Identification
    object_id: str = Field(..., description="Unique ID of this object")
    object_type: str = Field(
        ...,
        description="Type: camera_capture, edge_contour, template_match, etc.",
    )

    # Position & Geometry
    bounding_box: ROI = Field(
        ..., description="Bounding box of detected object in {x, y, width, height} format"
    )
    center: Point = Field(..., description="Center point of the object")

    # Quality
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 - 1.0)")

    # Optional geometry
    area: Optional[float] = Field(None, description="Area in pixels")
    perimeter: Optional[float] = Field(None, description="Perimeter in pixels")
    rotation: Optional[float] = Field(None, description="Rotation in degrees (0-360)")

    # Type-specific properties
    properties: Dict[str, Any] = Field(default_factory=dict, description="Type-specific properties")

    # Raw data (optional)
    contour: Optional[List] = Field(None, description="Contour points for edge detection")


class VisionResponse(BaseModel):
    """Simplified response for all vision processing APIs"""

    objects: List[VisionObject] = Field(default_factory=list, description="List of vision objects")
    thumbnail_base64: str = Field(..., description="Base64-encoded thumbnail with visualization")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


# Camera models
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


# Template models
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


# Vision processing models
class TemplateMatchRequest(BaseModel):
    """Request for template matching"""

    image_id: str
    roi: Optional[ROI] = Field(None, description="Region of interest to limit search area")
    params: TemplateMatchParams = Field(
        description="Template matching parameters (template_id is required)"
    )


class EdgeDetectRequest(BaseModel):
    """Request for edge detection"""

    image_id: str
    roi: Optional[ROI] = Field(None, description="Region of interest to limit search area")
    params: EdgeDetectionParams = Field(
        default_factory=EdgeDetectionParams,
        description="Edge detection parameters (method, filtering, preprocessing)",
    )


class ColorDetectRequest(BaseModel):
    """Request for color detection"""

    image_id: str = Field(..., description="ID of the image to analyze")
    roi: Optional[ROI] = Field(None, description="Region of interest (if None, analyze full image)")
    expected_color: Optional[str] = Field(
        None, description="Expected color name (red, blue, green, etc.) or None to just detect"
    )
    contour: Optional[List] = Field(
        None, description="Contour points for masking (from edge detection)"
    )
    params: Optional[ColorDetectionParams] = Field(
        None,
        description=(
            "Color detection parameters (method, thresholds, "
            "kmeans settings, defaults applied if None)"
        ),
    )


# System models
class SystemStatus(BaseModel):
    """System status information"""

    status: str
    uptime: float
    memory_usage: Dict[str, float]
    active_cameras: int
    buffer_usage: Dict[str, Any]


class PerformanceMetrics(BaseModel):
    """Performance metrics"""

    avg_processing_time: float
    total_inspections: int
    success_rate: float
    operations_per_minute: float


class DebugSettings(BaseModel):
    """Debug settings"""

    enabled: bool
    save_images: bool
    show_visualizations: bool
    verbose_logging: bool


# Image processing models
class ROIExtractRequest(BaseModel):
    """Request to extract ROI from image"""

    image_id: str
    roi: ROI = Field(..., description="Region of interest to extract")


class ROIExtractResponse(BaseModel):
    """Response from ROI extraction"""

    success: bool
    thumbnail: str
    bounding_box: ROI


class ArucoDetectRequest(BaseModel):
    """Request for ArUco marker detection"""

    image_id: str = Field(..., description="ID of the image to analyze")
    roi: Optional[ROI] = Field(None, description="Region of interest to search in")
    params: Optional[ArucoDetectionParams] = Field(
        None,
        description=(
            "ArUco detection parameters (dictionary type, "
            "detector settings, defaults applied if None)"
        ),
    )


class RotationDetectRequest(BaseModel):
    """Request for rotation detection"""

    image_id: str = Field(..., description="ID of the image for visualization")
    contour: List = Field(..., description="Contour points [[x1,y1], [x2,y2], ...]", min_length=5)
    roi: Optional[ROI] = Field(None, description="Optional ROI for visualization context")
    params: Optional[RotationDetectionParams] = Field(
        None,
        description="Rotation detection parameters (method, angle range, defaults applied if None)",
    )

    @field_validator("contour")
    @classmethod
    def validate_contour(cls, v):
        """Validate contour has minimum required points."""
        if len(v) < 5:
            raise ValueError(
                f"Contour must have at least 5 points for rotation detection, got {len(v)}"
            )
        return v
