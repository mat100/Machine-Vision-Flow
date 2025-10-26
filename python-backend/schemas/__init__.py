"""
Schemas Package

This package contains all Pydantic schemas for data validation and serialization,
organized by domain for better maintainability.

These schemas are shared across all application layers:
- API (routers, dependencies)
- Services (business logic)
- Core (infrastructure)
- Vision (detection algorithms)

Note: "schemas" (not "models") follows FastAPI best practices:
- schemas/ = Pydantic models for validation/serialization
- models/ or db/models/ = ORM/database models (not used in this project)
"""

# Re-export enums from centralized location for convenience (backwards compatibility)
from core.enums import (
    AngleRange,
    ArucoDict,
    ColorMethod,
    EdgeMethod,
    InspectionResult,
    RotationMethod,
    TemplateMethod,
    VisionObjectType,
)

# Import detection params from vision layer for convenience
# These are imported from vision modules, not duplicated here
from vision.aruco_detection import ArucoDetectionParams
from vision.color_detection import ColorDetectionParams
from vision.edge_detection import EdgeDetectionParams
from vision.rotation_detection import RotationDetectionParams
from vision.template_matching import TemplateMatchParams

# Base schemas
from .base import BaseDetectionParams

# Camera models
from .camera import (
    CameraCaptureResponse,
    CameraConnectRequest,
    CameraInfo,
    CaptureParams,
    CaptureRequest,
)

# Common models (core data structures)
from .common import ROI, Point, Size, VisionObject, VisionResponse

# Image processing models
from .image import ROIExtractRequest, ROIExtractResponse

# System models
from .system import DebugSettings, PerformanceMetrics, SystemStatus

# Template models
from .template import TemplateInfo, TemplateLearnRequest, TemplateUploadResponse

# Vision processing request models
from .vision import (
    ArucoDetectRequest,
    ColorDetectRequest,
    EdgeDetectRequest,
    RotationDetectRequest,
    TemplateMatchRequest,
)

# Explicitly declare public API for re-export
__all__ = [
    # Common models
    "ROI",
    "Point",
    "Size",
    "VisionObject",
    "VisionResponse",
    # Camera models
    "CameraInfo",
    "CameraConnectRequest",
    "CaptureParams",
    "CaptureRequest",
    "CameraCaptureResponse",
    # Template models
    "TemplateInfo",
    "TemplateUploadResponse",
    "TemplateLearnRequest",
    # Vision request models
    "TemplateMatchRequest",
    "EdgeDetectRequest",
    "ColorDetectRequest",
    "ArucoDetectRequest",
    "RotationDetectRequest",
    # System models
    "SystemStatus",
    "PerformanceMetrics",
    "DebugSettings",
    # Image models
    "ROIExtractRequest",
    "ROIExtractResponse",
    # Enums (re-exported from core.enums)
    "AngleRange",
    "ArucoDict",
    "ColorMethod",
    "EdgeMethod",
    "InspectionResult",
    "RotationMethod",
    "TemplateMethod",
    "VisionObjectType",
    # Base schemas
    "BaseDetectionParams",
    # Params (re-exported from vision modules)
    "EdgeDetectionParams",
    "ColorDetectionParams",
    "ArucoDetectionParams",
    "RotationDetectionParams",
    "TemplateMatchParams",
]
