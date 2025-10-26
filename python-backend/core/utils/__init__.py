"""
Utility modules for core functionality.

This package contains reusable utility classes and helper functions
to reduce code duplication and improve maintainability.

Modules:
- camera_identifier: Parse camera ID strings
- color_utils: HSV color definitions and utilities
- coordinate_adjuster: ROI coordinate adjustment
- decorators: Utility decorators (timer, etc.)
- enum_converter: Enum parsing and conversion
- image_utils: Deprecated image utilities wrapper
- params_processor: Parameter processing utilities
- roi_handler: ROI extraction and validation
"""

from .camera_identifier import CameraIdentifier
from .color_utils import (
    COLOR_DEFINITIONS,
    count_colors_vectorized,
    create_color_mask_vectorized,
    get_available_colors,
    hsv_to_color_name,
    is_achromatic,
    is_color_match,
)
from .coordinate_adjuster import CoordinateAdjuster
from .decorators import timer
from .enum_converter import EnumConverter
from .image_utils import ImageUtils
from .params_processor import ParamsProcessor
from .roi_handler import ROIHandler

__all__ = [
    "CameraIdentifier",
    "COLOR_DEFINITIONS",
    "count_colors_vectorized",
    "create_color_mask_vectorized",
    "get_available_colors",
    "hsv_to_color_name",
    "is_achromatic",
    "is_color_match",
    "CoordinateAdjuster",
    "timer",
    "EnumConverter",
    "ImageUtils",
    "ParamsProcessor",
    "ROIHandler",
]
