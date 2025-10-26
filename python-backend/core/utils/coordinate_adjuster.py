"""
Coordinate adjustment utilities.

Handles coordinate transformations when ROI (Region of Interest) is used,
adjusting bounding boxes, centers, and contours to account for ROI offset.
"""

from typing import List, Tuple

from schemas import VisionObject


class CoordinateAdjuster:
    """
    Utility class for adjusting coordinates based on ROI offset.

    When detection is performed on a ROI subset of an image, all detected
    coordinates are relative to the ROI. This class adjusts them back to
    the original image coordinate system.
    """

    @staticmethod
    def adjust_for_roi_offset(objects: List[VisionObject], roi_offset: Tuple[int, int]) -> None:
        """
        Adjust object coordinates to account for ROI offset.

        Modifies VisionObject instances in-place by adding the ROI offset
        to all coordinate values (bounding_box, center, contour points).

        Args:
            objects: List of VisionObject instances to adjust
            roi_offset: Tuple of (x_offset, y_offset) from ROI position

        Example:
            >>> objects = [VisionObject(...)]  # Objects detected in ROI
            >>> roi_offset = (100, 50)  # ROI started at x=100, y=50
            >>> CoordinateAdjuster.adjust_for_roi_offset(objects, roi_offset)
            >>> # All object coordinates now relative to full image
        """
        if roi_offset == (0, 0):
            return  # No adjustment needed

        x_offset, y_offset = roi_offset

        for obj in objects:
            # Adjust bounding box position
            obj.bounding_box.x += x_offset
            obj.bounding_box.y += y_offset

            # Adjust center point
            obj.center.x += x_offset
            obj.center.y += y_offset

            # Adjust contour points if present
            if hasattr(obj, "contour") and obj.contour:
                obj.contour = [[x + x_offset, y + y_offset] for x, y in obj.contour]

    @staticmethod
    def extract_roi_offset(roi: dict) -> Tuple[int, int]:
        """
        Extract offset coordinates from ROI dictionary.

        Args:
            roi: Dictionary with 'x' and 'y' keys, or None

        Returns:
            Tuple of (x_offset, y_offset), or (0, 0) if roi is None

        Example:
            >>> roi = {"x": 100, "y": 50, "width": 200, "height": 150}
            >>> offset = CoordinateAdjuster.extract_roi_offset(roi)
            >>> # Returns (100, 50)
        """
        if roi is None:
            return (0, 0)
        return (roi.get("x", 0), roi.get("y", 0))
