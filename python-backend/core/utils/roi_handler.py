"""
Region of Interest (ROI) handler for the Machine Vision Flow system.

Provides utility functions for ROI validation and image extraction.
Works with the unified ROI Pydantic model from schemas.

NOTE: This handler contains only actively used functions.
      ROI geometric operations (intersection, union, etc.) are in the ROI model itself.
"""

import logging
from typing import Dict, Optional, Tuple, Union

import numpy as np

from schemas import ROI

logger = logging.getLogger(__name__)


class ROIHandler:
    """
    Handler for ROI validation and image extraction operations.

    Provides two core functions:
    - validate_roi: Validate ROI against image bounds and size constraints
    - extract_roi: Extract rectangular region from image with safe clipping
    """

    @staticmethod
    def validate_roi(
        roi: Union[ROI, Dict],
        image_shape: Optional[Tuple[int, ...]] = None,
        min_size: int = 1,
        max_size: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate ROI parameters.

        Args:
            roi: ROI object or dictionary
            image_shape: Optional image shape (height, width, ...)
            min_size: Minimum width/height
            max_size: Maximum width/height

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Convert to ROI object if needed
        if isinstance(roi, dict):
            try:
                roi = ROI.from_dict(roi)
            except (KeyError, ValueError) as e:
                return False, f"Invalid ROI format: {e}"

        # Check basic validity
        if roi.width < min_size or roi.height < min_size:
            return False, f"ROI too small: {roi.width}x{roi.height} (min: {min_size})"

        if max_size and (roi.width > max_size or roi.height > max_size):
            return False, f"ROI too large: {roi.width}x{roi.height} (max: {max_size})"

        if roi.x < 0 or roi.y < 0:
            return False, f"ROI has negative coordinates: ({roi.x}, {roi.y})"

        # Check against image bounds if provided
        if image_shape:
            img_height = image_shape[0]
            img_width = image_shape[1] if len(image_shape) > 1 else image_shape[0]

            if not roi.is_valid(img_width, img_height):
                return False, f"ROI {roi.to_dict()} exceeds image bounds {img_width}x{img_height}"

        return True, None

    @staticmethod
    def extract_roi(
        image: np.ndarray, roi: Union[ROI, Dict], safe_mode: bool = True, padding_value: int = 0
    ) -> Optional[np.ndarray]:
        """
        Extract ROI from image.

        Args:
            image: Input image
            roi: ROI object or dictionary
            safe_mode: If True, clip ROI to image bounds
            padding_value: Value to use for padding if ROI extends beyond image

        Returns:
            Extracted ROI or None if invalid
        """
        # Convert to ROI object if needed
        if isinstance(roi, dict):
            roi = ROI.from_dict(roi)

        img_height, img_width = image.shape[:2]

        if safe_mode:
            # Clip ROI to image bounds
            roi = roi.clip(img_width, img_height)

            if roi.width <= 0 or roi.height <= 0:
                logger.warning(f"ROI becomes empty after clipping: {roi.to_dict()}")
                return None

            return image[roi.y : roi.y2, roi.x : roi.x2].copy()

        else:
            # Strict mode - check bounds
            is_valid, error_msg = ROIHandler.validate_roi(roi, image.shape)
            if not is_valid:
                logger.warning(f"Invalid ROI: {error_msg}")
                return None

            return image[roi.y : roi.y2, roi.x : roi.x2].copy()
