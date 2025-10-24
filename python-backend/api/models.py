"""
Pydantic models for API requests and responses
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Enums
class TemplateMethod(str, Enum):
    TM_CCOEFF = "TM_CCOEFF"
    TM_CCOEFF_NORMED = "TM_CCOEFF_NORMED"
    TM_CCORR = "TM_CCORR"
    TM_CCORR_NORMED = "TM_CCORR_NORMED"
    TM_SQDIFF = "TM_SQDIFF"
    TM_SQDIFF_NORMED = "TM_SQDIFF_NORMED"


class InspectionResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


# Common models
class ROI(BaseModel):
    """Region of Interest"""

    x: int = Field(..., ge=0, description="X coordinate")
    y: int = Field(..., ge=0, description="Y coordinate")
    width: int = Field(..., gt=0, description="Width")
    height: int = Field(..., gt=0, description="Height")


class Point(BaseModel):
    """2D Point"""

    x: float
    y: float


class Size(BaseModel):
    """Image size"""

    width: int
    height: int


class BoundingBox(BaseModel):
    """Bounding box for detected objects"""

    top_left: Point
    bottom_right: Point


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
    multi_scale: bool = False
    scale_range: Optional[List[float]] = [0.8, 1.2]
    rotation: bool = False
    rotation_range: Optional[List[float]] = [-10, 10]


class TemplateMatchResult(BaseModel):
    """Single template match result"""

    position: Point
    score: float
    scale: float = 1.0
    rotation: float = 0.0
    bounding_box: BoundingBox


class TemplateMatchResponse(BaseModel):
    """Response from template matching"""

    success: bool
    found: bool
    matches: List[TemplateMatchResult]
    processing_time_ms: int
    thumbnail_base64: str


class EdgeDetectRequest(BaseModel):
    """Request for edge detection"""

    image_id: str
    method: str = "canny"

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


class BlobDetectRequest(BaseModel):
    """Request for blob detection"""

    image_id: str
    min_area: Optional[int] = 100
    max_area: Optional[int] = 10000
    circularity: Optional[float] = None


# History models
class InspectionRecord(BaseModel):
    """Single inspection record"""

    id: str
    timestamp: datetime
    image_id: str
    result: InspectionResult
    summary: str
    thumbnail_base64: Optional[str] = None
    processing_time_ms: int
    detections: List[Dict[str, Any]]


class HistoryResponse(BaseModel):
    """Response with inspection history"""

    inspections: List[InspectionRecord]
    statistics: Dict[str, Any]


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
    show_overlays: bool
    verbose_logging: bool


# Result merger models
class DetectionResult(BaseModel):
    """Single detection result for merger"""

    node_id: str
    name: str
    type: str
    found: bool
    score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class MergedResults(BaseModel):
    """Merged results from multiple detections"""

    image_id: str
    all_detections: List[DetectionResult]
    summary: Dict[str, Any]
    result: InspectionResult
    failed_checks: List[str]


# Image processing models
class ROIExtractRequest(BaseModel):
    """Request to extract ROI from image"""

    image_id: str
    roi: ROI


class ROIExtractResponse(BaseModel):
    """Response from ROI extraction"""

    success: bool
    image_id: str
    thumbnail_base64: str
    metadata: Dict[str, Any]
