"""
Image processing utilities for the Machine Vision Flow system.

DEPRECATED: This module is maintained for backwards compatibility only.
Please use the focused modules in core.image instead:
- core.image.converters.ImageConverters
- core.image.processors.ImageProcessors
- core.image.geometry.ImageGeometry

This file re-exports all functionality from the new modules.
"""

import warnings

from core.image.converters import ImageConverters
from core.image.geometry import ImageGeometry
from core.image.processors import ImageProcessors

# Issue deprecation warning
warnings.warn(
    "core.image_utils.ImageUtils is deprecated. "
    "Please use core.image.converters.ImageConverters, "
    "core.image.processors.ImageProcessors, or "
    "core.image.geometry.ImageGeometry directly.",
    DeprecationWarning,
    stacklevel=2,
)


class ImageUtils:
    """
    Utility class for common image processing operations.

    DEPRECATED: Use focused classes from core.image package instead.
    """

    # Re-export all methods from ImageConverters
    numpy_to_pil = staticmethod(ImageConverters.numpy_to_pil)
    pil_to_numpy = staticmethod(ImageConverters.pil_to_numpy)
    to_base64 = staticmethod(ImageConverters.to_base64)
    from_base64 = staticmethod(ImageConverters.from_base64)
    encode_image_to_base64 = staticmethod(ImageConverters.encode_image_to_base64)
    ensure_bgr = staticmethod(ImageConverters.ensure_bgr)
    ensure_grayscale = staticmethod(ImageConverters.ensure_grayscale)

    # Re-export all methods from ImageProcessors
    create_thumbnail = staticmethod(ImageProcessors.create_thumbnail)
    resize_image = staticmethod(ImageProcessors.resize_image)
    extract_roi = staticmethod(ImageProcessors.extract_roi)

    # Re-export all methods from ImageGeometry
    normalize_angle = staticmethod(ImageGeometry.normalize_angle)
    calculate_contour_properties = staticmethod(ImageGeometry.calculate_contour_properties)


# For convenience, also allow direct imports
__all__ = ["ImageUtils", "ImageConverters", "ImageProcessors", "ImageGeometry"]
