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

#  Explicitly declare public API for re-export
__all__ = [
    "AngleRange",
    "ArucoDict",
    "ColorMethod",
    "RotationMethod",
    "TemplateMethod",
    "VisionObjectType",
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
    template_id: str
    method: TemplateMethod = TemplateMethod.TM_CCOEFF_NORMED
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    roi: Optional[ROI] = Field(None, description="Region of interest to limit search area")
    multi_scale: bool = False
    scale_range: Optional[List[float]] = [0.8, 1.2]
    rotation: bool = False
    rotation_range: Optional[List[float]] = [-10, 10]


class EdgeDetectRequest(BaseModel):
    """Request for edge detection"""

    image_id: str
    method: str = "canny"
    roi: Optional[ROI] = Field(None, description="Region of interest to limit search area")

    # Canny parameters
    canny_low: Optional[int] = Field(50, ge=0, le=255, description="Canny low threshold")
    canny_high: Optional[int] = Field(150, ge=0, le=255, description="Canny high threshold")

    # Sobel parameters
    sobel_threshold: Optional[float] = Field(50, ge=0, description="Sobel threshold")
    sobel_kernel: Optional[int] = Field(3, ge=1, description="Sobel kernel size")

    # Laplacian parameters
    laplacian_threshold: Optional[float] = Field(30, ge=0, description="Laplacian threshold")
    laplacian_kernel: Optional[int] = Field(3, ge=1, description="Laplacian kernel size")

    # Prewitt parameters
    prewitt_threshold: Optional[float] = Field(50, ge=0, description="Prewitt threshold")

    # Scharr parameters
    scharr_threshold: Optional[float] = Field(50, ge=0, description="Scharr threshold")

    # Morphological gradient parameters
    morph_threshold: Optional[float] = Field(
        30, ge=0, description="Morphological gradient threshold"
    )
    morph_kernel: Optional[int] = Field(3, ge=1, description="Morphological gradient kernel size")

    # Contour filtering parameters
    min_contour_area: Optional[float] = Field(10, ge=0, description="Minimum contour area")
    max_contour_area: Optional[float] = Field(100000, ge=0, description="Maximum contour area")
    min_contour_perimeter: Optional[float] = Field(0, ge=0, description="Minimum contour perimeter")
    max_contour_perimeter: Optional[float] = Field(
        float("inf"), description="Maximum contour perimeter"
    )
    max_contours: Optional[int] = Field(
        100, ge=1, description="Maximum number of contours to return"
    )
    show_centers: Optional[bool] = Field(True, description="Show contour centers in visualization")

    # Preprocessing options
    blur_enabled: Optional[bool] = Field(False, description="Enable Gaussian blur preprocessing")
    blur_kernel: Optional[int] = Field(
        5, ge=3, description="Gaussian blur kernel size (odd number)"
    )
    bilateral_enabled: Optional[bool] = Field(
        False, description="Enable bilateral filter preprocessing"
    )
    bilateral_d: Optional[int] = Field(9, ge=1, description="Bilateral filter diameter")
    bilateral_sigma_color: Optional[float] = Field(
        75, ge=0, description="Bilateral filter sigma color"
    )
    bilateral_sigma_space: Optional[float] = Field(
        75, ge=0, description="Bilateral filter sigma space"
    )
    morphology_enabled: Optional[bool] = Field(
        False, description="Enable morphological preprocessing"
    )
    morphology_operation: Optional[str] = Field(
        "close", description="Morphological operation (close/open/gradient)"
    )
    morphology_kernel: Optional[int] = Field(3, ge=1, description="Morphological kernel size")
    equalize_enabled: Optional[bool] = Field(False, description="Enable histogram equalization")

    def get_detection_params(self) -> Dict[str, Any]:
        """
        Extract all parameters as dict (detection + preprocessing unified).

        Eliminates manual parameter dict construction in vision.py endpoint.

        Returns:
            Dictionary with method-specific, filtering, and preprocessing parameters
        """
        return {
            # Method-specific parameters
            "canny_low": self.canny_low,
            "canny_high": self.canny_high,
            "sobel_threshold": self.sobel_threshold,
            "sobel_kernel": self.sobel_kernel,
            "laplacian_threshold": self.laplacian_threshold,
            "laplacian_kernel": self.laplacian_kernel,
            "prewitt_threshold": self.prewitt_threshold,
            "scharr_threshold": self.scharr_threshold,
            "morph_threshold": self.morph_threshold,
            "morph_kernel": self.morph_kernel,
            # Filtering parameters
            "min_contour_area": self.min_contour_area,
            "max_contour_area": self.max_contour_area,
            "min_contour_perimeter": self.min_contour_perimeter,
            "max_contour_perimeter": self.max_contour_perimeter,
            "max_contours": self.max_contours,
            "show_centers": self.show_centers,
            # Preprocessing parameters (unified)
            "blur_enabled": self.blur_enabled,
            "blur_kernel": self.blur_kernel,
            "bilateral_enabled": self.bilateral_enabled,
            "bilateral_d": self.bilateral_d,
            "bilateral_sigma_color": self.bilateral_sigma_color,
            "bilateral_sigma_space": self.bilateral_sigma_space,
            "morphology_enabled": self.morphology_enabled,
            "morphology_operation": self.morphology_operation,
            "morphology_kernel": self.morphology_kernel,
            "equalize_enabled": self.equalize_enabled,
        }


class ColorDetectRequest(BaseModel):
    """Request for color detection"""

    image_id: str = Field(..., description="ID of the image to analyze")
    roi: Optional[ROI] = Field(None, description="Region of interest (if None, analyze full image)")
    expected_color: Optional[str] = Field(
        None, description="Expected color name (red, blue, green, etc.) or None to just detect"
    )
    min_percentage: float = Field(
        50.0, ge=0.0, le=100.0, description="Minimum percentage for match"
    )
    method: ColorMethod = Field(
        ColorMethod.HISTOGRAM, description="Detection method: histogram (fast) or kmeans (accurate)"
    )
    use_contour_mask: bool = Field(
        True, description="Use contour mask instead of full bounding box when contour is available"
    )
    contour: Optional[List] = Field(
        None, description="Contour points for masking (from edge detection)"
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
    dictionary: ArucoDict = Field(ArucoDict.DICT_4X4_50, description="ArUco dictionary type")
    roi: Optional[ROI] = Field(None, description="Region of interest to search in")
    params: Optional[Dict[str, Any]] = Field(None, description="Detection parameters")


class RotationDetectRequest(BaseModel):
    """Request for rotation detection"""

    image_id: str = Field(..., description="ID of the image for visualization")
    contour: List = Field(..., description="Contour points [[x1,y1], [x2,y2], ...]", min_length=5)
    method: RotationMethod = Field(
        RotationMethod.MIN_AREA_RECT,
        description="Detection method: min_area_rect, ellipse_fit, pca",
    )
    angle_range: AngleRange = Field(
        AngleRange.RANGE_0_360, description="Angle output range: 0_360, -180_180, or 0_180"
    )
    roi: Optional[ROI] = Field(None, description="Optional ROI for visualization context")

    @field_validator("contour")
    @classmethod
    def validate_contour(cls, v):
        """Validate contour has minimum required points."""
        if len(v) < 5:
            raise ValueError(
                f"Contour must have at least 5 points for rotation detection, got {len(v)}"
            )
        return v
