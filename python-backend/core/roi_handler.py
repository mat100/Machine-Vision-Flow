"""
Region of Interest (ROI) handler for the Machine Vision Flow system.
Centralizes ROI validation, extraction, and manipulation.
"""

import logging
from typing import Optional, Dict, Tuple, Union
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ROI:
    """Region of Interest data class."""
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ROI':
        """Create ROI from dictionary."""
        return cls(
            x=int(data.get('x', 0)),
            y=int(data.get('y', 0)),
            width=int(data.get('width', 0)),
            height=int(data.get('height', 0))
        )

    @classmethod
    def from_points(cls, x1: int, y1: int, x2: int, y2: int) -> 'ROI':
        """Create ROI from two corner points."""
        return cls(
            x=min(x1, x2),
            y=min(y1, y2),
            width=abs(x2 - x1),
            height=abs(y2 - y1)
        )

    @property
    def x2(self) -> int:
        """Get right edge coordinate."""
        return self.x + self.width

    @property
    def y2(self) -> int:
        """Get bottom edge coordinate."""
        return self.y + self.height

    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of ROI."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """Get area of ROI."""
        return self.width * self.height

    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside ROI."""
        return self.x <= x < self.x2 and self.y <= y < self.y2

    def intersects(self, other: 'ROI') -> bool:
        """Check if this ROI intersects with another."""
        return not (
            self.x2 <= other.x or
            other.x2 <= self.x or
            self.y2 <= other.y or
            other.y2 <= self.y
        )

    def intersection(self, other: 'ROI') -> Optional['ROI']:
        """Get intersection with another ROI."""
        if not self.intersects(other):
            return None

        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)

        return ROI.from_points(x1, y1, x2, y2)

    def union(self, other: 'ROI') -> 'ROI':
        """Get union with another ROI."""
        x1 = min(self.x, other.x)
        y1 = min(self.y, other.y)
        x2 = max(self.x2, other.x2)
        y2 = max(self.y2, other.y2)

        return ROI.from_points(x1, y1, x2, y2)

    def scale(self, factor: float, center: bool = False) -> 'ROI':
        """Scale ROI by factor."""
        new_width = int(self.width * factor)
        new_height = int(self.height * factor)

        if center:
            # Scale from center
            cx, cy = self.center
            new_x = cx - new_width // 2
            new_y = cy - new_height // 2
        else:
            # Scale from top-left
            new_x = self.x
            new_y = self.y

        return ROI(new_x, new_y, new_width, new_height)

    def expand(self, pixels: int) -> 'ROI':
        """Expand ROI by pixels in all directions."""
        return ROI(
            self.x - pixels,
            self.y - pixels,
            self.width + 2 * pixels,
            self.height + 2 * pixels
        )

    def clip(self, image_width: int, image_height: int) -> 'ROI':
        """Clip ROI to image bounds."""
        x = max(0, min(self.x, image_width))
        y = max(0, min(self.y, image_height))
        x2 = max(0, min(self.x2, image_width))
        y2 = max(0, min(self.y2, image_height))

        return ROI.from_points(x, y, x2, y2)

    def is_valid(self, image_width: Optional[int] = None, image_height: Optional[int] = None) -> bool:
        """
        Check if ROI is valid.

        Args:
            image_width: Optional image width for bounds checking
            image_height: Optional image height for bounds checking

        Returns:
            True if ROI is valid
        """
        # Basic validation
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


class ROIHandler:
    """Handler for ROI operations."""

    @staticmethod
    def validate_roi(
        roi: Union[ROI, Dict],
        image_shape: Optional[Tuple[int, ...]] = None,
        min_size: int = 1,
        max_size: Optional[int] = None
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
        image: np.ndarray,
        roi: Union[ROI, Dict],
        safe_mode: bool = True,
        padding_value: int = 0
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

            return image[roi.y:roi.y2, roi.x:roi.x2].copy()

        else:
            # Strict mode - check bounds
            is_valid, error_msg = ROIHandler.validate_roi(roi, image.shape)
            if not is_valid:
                logger.warning(f"Invalid ROI: {error_msg}")
                return None

            return image[roi.y:roi.y2, roi.x:roi.x2].copy()

    @staticmethod
    def extract_multiple_rois(
        image: np.ndarray,
        rois: list,
        safe_mode: bool = True
    ) -> list:
        """
        Extract multiple ROIs from image.

        Args:
            image: Input image
            rois: List of ROI objects or dictionaries
            safe_mode: If True, clip ROIs to image bounds

        Returns:
            List of extracted ROI images
        """
        results = []
        for roi in rois:
            roi_image = ROIHandler.extract_roi(image, roi, safe_mode)
            if roi_image is not None:
                results.append(roi_image)
            else:
                logger.warning(f"Failed to extract ROI: {roi}")

        return results

    @staticmethod
    def apply_roi_mask(
        image: np.ndarray,
        roi: Union[ROI, Dict],
        mask_value: int = 0,
        invert: bool = False
    ) -> np.ndarray:
        """
        Apply ROI as mask to image.

        Args:
            image: Input image
            roi: ROI object or dictionary
            mask_value: Value to set outside ROI
            invert: If True, mask inside ROI instead

        Returns:
            Masked image
        """
        # Convert to ROI object if needed
        if isinstance(roi, dict):
            roi = ROI.from_dict(roi)

        masked = image.copy()
        mask = np.ones(image.shape[:2], dtype=bool)

        # Create mask
        mask[roi.y:roi.y2, roi.x:roi.x2] = False

        if invert:
            mask = ~mask

        # Apply mask
        if len(image.shape) == 3:
            masked[mask] = [mask_value] * image.shape[2]
        else:
            masked[mask] = mask_value

        return masked

    @staticmethod
    def merge_overlapping_rois(
        rois: list,
        overlap_threshold: float = 0.5
    ) -> list:
        """
        Merge overlapping ROIs.

        Args:
            rois: List of ROI objects or dictionaries
            overlap_threshold: Minimum overlap ratio to merge (0-1)

        Returns:
            List of merged ROIs
        """
        # Convert all to ROI objects
        roi_objects = []
        for roi in rois:
            if isinstance(roi, dict):
                roi_objects.append(ROI.from_dict(roi))
            else:
                roi_objects.append(roi)

        merged = []
        used = set()

        for i, roi1 in enumerate(roi_objects):
            if i in used:
                continue

            current = roi1
            merged_any = True

            while merged_any:
                merged_any = False
                for j, roi2 in enumerate(roi_objects):
                    if j <= i or j in used:
                        continue

                    intersection = current.intersection(roi2)
                    if intersection:
                        # Calculate overlap ratio
                        overlap_ratio = intersection.area / min(current.area, roi2.area)

                        if overlap_ratio >= overlap_threshold:
                            # Merge ROIs
                            current = current.union(roi2)
                            used.add(j)
                            merged_any = True

            merged.append(current)

        return merged