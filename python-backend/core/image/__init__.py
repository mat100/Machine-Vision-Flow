"""
Image processing utilities - modular architecture.

This package provides focused image processing utilities:
- converters: Format conversions (NumPy, PIL, base64, color spaces)
- processors: Image operations (thumbnail, resize, overlay, ROI extraction)
- geometry: Geometric calculations (angles, contour properties)

For backwards compatibility, all utilities are also re-exported from this module.
"""

from core.image.converters import ImageConverters
from core.image.geometry import ImageGeometry
from core.image.processors import ImageProcessors

__all__ = ["ImageConverters", "ImageProcessors", "ImageGeometry"]
