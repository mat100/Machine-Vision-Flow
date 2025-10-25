"""
Rotation detection algorithms for machine vision.
Calculates object orientation from contours using various methods.
"""

import base64
from enum import Enum
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from api.models import ROI, Point, VisionObject, VisionObjectType


class RotationMethod(str, Enum):
    """Available rotation detection methods."""

    MIN_AREA_RECT = "min_area_rect"
    ELLIPSE_FIT = "ellipse_fit"
    PCA = "pca"


class AngleRange(str, Enum):
    """Angle output range options."""

    RANGE_0_360 = "0_360"  # 0 to 360 degrees
    RANGE_NEG180_180 = "-180_180"  # -180 to +180 degrees
    RANGE_0_180 = "0_180"  # 0 to 180 degrees (symmetric objects)


class RotationDetector:
    """Rotation detection processor."""

    def __init__(self):
        """Initialize rotation detector."""

    def detect(
        self,
        image: np.ndarray,
        contour: List,
        method: RotationMethod = RotationMethod.MIN_AREA_RECT,
        angle_range: AngleRange = AngleRange.RANGE_0_360,
        roi: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Detect rotation angle of object from contour.

        Args:
            image: Input image (for visualization)
            contour: Contour points [[x1,y1], [x2,y2], ...]
            method: Rotation calculation method
            angle_range: Output angle range format
            roi: Optional ROI for context (for visualization only)

        Returns:
            Dictionary with rotation detection results
        """
        # Convert contour to numpy array
        contour_array = np.array(contour, dtype=np.float32)

        if len(contour_array.shape) == 2:
            # Reshape to Nx1x2 if needed (OpenCV format)
            contour_array = contour_array.reshape((-1, 1, 2))

        # Validate contour has enough points
        if len(contour_array) < 5 and method == RotationMethod.ELLIPSE_FIT:
            raise ValueError(
                f"Ellipse fitting requires at least 5 points, got {len(contour_array)}"
            )

        if len(contour_array) < 3:
            raise ValueError(
                f"Rotation detection requires at least 3 points, got {len(contour_array)}"
            )

        # Calculate rotation based on method
        if method == RotationMethod.MIN_AREA_RECT:
            angle, center, confidence = self._detect_min_area_rect(contour_array)
        elif method == RotationMethod.ELLIPSE_FIT:
            angle, center, confidence = self._detect_ellipse_fit(contour_array)
        elif method == RotationMethod.PCA:
            angle, center, confidence = self._detect_pca(contour_array)
        else:
            raise ValueError(f"Unknown rotation method: {method}")

        # Convert angle to requested range
        angle = self._convert_angle_range(angle, angle_range)

        # Calculate bounding box from contour
        x, y, w, h = cv2.boundingRect(contour_array)

        # Calculate area and perimeter
        area = float(cv2.contourArea(contour_array))
        perimeter = float(cv2.arcLength(contour_array, True))

        # Create VisionObject
        obj = VisionObject(
            object_id="rotation_analysis",
            object_type=VisionObjectType.ROTATION_ANALYSIS.value,
            bounding_box=ROI(x=x, y=y, width=w, height=h),
            center=center,
            confidence=confidence,
            area=area,
            perimeter=perimeter,
            rotation=angle,
            properties={
                "method": method.value,
                "angle_range": angle_range.value,
                "absolute_angle": angle,  # Same as rotation for now (reference added in Node-RED)
            },
            contour=contour,  # Preserve original contour
        )

        # Create visualization
        visualization = self._create_visualization(image, contour_array, angle, center, method, roi)

        return {
            "success": True,
            "method": method,
            "objects": [obj],
            "visualization": visualization,
        }

    def _detect_min_area_rect(self, contour: np.ndarray) -> tuple:
        """
        Detect rotation using minimum area rectangle.

        Args:
            contour: Contour points (Nx1x2)

        Returns:
            (angle, center, confidence)
        """
        # Fit minimum area rectangle
        rect = cv2.minAreaRect(contour)
        center_tuple, (width, height), angle = rect

        # OpenCV's minAreaRect returns angle in range -90 to 0
        # Convert to 0-360 range with 0° = horizontal right
        # Note: OpenCV angle is from the horizontal to the first side (width side)

        # Adjust based on aspect ratio
        if width < height:
            angle = angle + 90

        # Normalize to 0-360
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360

        center = Point(x=float(center_tuple[0]), y=float(center_tuple[1]))
        confidence = 1.0  # High confidence for geometric method

        return float(angle), center, confidence

    def _detect_ellipse_fit(self, contour: np.ndarray) -> tuple:
        """
        Detect rotation using ellipse fitting.

        Args:
            contour: Contour points (Nx1x2), must have >= 5 points

        Returns:
            (angle, center, confidence)
        """
        # Fit ellipse
        ellipse = cv2.fitEllipse(contour)
        center_tuple, axes, angle = ellipse

        # OpenCV's fitEllipse returns angle in range 0-180
        # This is the angle of the major axis from horizontal

        # Normalize to 0-360 (ellipse is symmetric, so 0-180 is sufficient)
        # But we'll keep it in 0-360 for consistency
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360

        center = Point(x=float(center_tuple[0]), y=float(center_tuple[1]))

        # Calculate confidence based on how well ellipse fits the contour
        # (simplified - could be improved with actual error metric)
        confidence = 0.9

        return float(angle), center, confidence

    def _detect_pca(self, contour: np.ndarray) -> tuple:
        """
        Detect rotation using PCA (Principal Component Analysis).
        Most robust method - finds dominant orientation axis.

        Args:
            contour: Contour points (Nx1x2)

        Returns:
            (angle, center, confidence)
        """
        # Reshape contour to 2D array of points
        points = contour.reshape(-1, 2).astype(np.float32)

        # Calculate mean (center)
        mean = np.mean(points, axis=0)
        center = Point(x=float(mean[0]), y=float(mean[1]))

        # Center the points
        centered_points = points - mean

        # Calculate covariance matrix
        cov_matrix = np.cov(centered_points.T)

        # Get eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)

        # Sort by eigenvalue (largest first)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Principal component (dominant direction)
        principal_axis = eigenvectors[:, 0]

        # Calculate angle from principal axis
        angle_rad = np.arctan2(principal_axis[1], principal_axis[0])
        angle = float(np.degrees(angle_rad))

        # Normalize to 0-360
        if angle < 0:
            angle += 360.0

        # Calculate confidence from eigenvalue ratio
        # Higher ratio = more elongated = more confident in rotation
        if eigenvalues[1] > 0:
            ratio = eigenvalues[0] / eigenvalues[1]
            confidence = min(1.0, ratio / 10.0)  # Normalize (arbitrary scaling)
        else:
            confidence = 1.0

        return angle, center, confidence

    def _convert_angle_range(self, angle: float, range_type: AngleRange) -> float:
        """
        Convert angle to requested range.

        Args:
            angle: Input angle (assumed 0-360)
            range_type: Desired output range

        Returns:
            Angle in requested range
        """
        if range_type == AngleRange.RANGE_0_360:
            # Already in 0-360
            while angle < 0:
                angle += 360
            while angle >= 360:
                angle -= 360
            return angle

        elif range_type == AngleRange.RANGE_NEG180_180:
            # Convert to -180 to +180
            while angle < -180:
                angle += 360
            while angle > 180:
                angle -= 360
            return angle

        elif range_type == AngleRange.RANGE_0_180:
            # Convert to 0-180 (symmetric)
            while angle < 0:
                angle += 180
            while angle >= 180:
                angle -= 180
            return angle

        return angle

    def _create_visualization(
        self,
        original: np.ndarray,
        contour: np.ndarray,
        angle: float,
        center: Point,
        method: RotationMethod,
        roi: Optional[Dict[str, int]],
    ) -> Dict[str, str]:
        """Create visualization images."""
        visualization = {}

        # If ROI provided, crop to ROI and adjust coordinates
        if roi:
            # Extract ROI region
            x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
            roi_image = original[y : y + h, x : x + w].copy()

            # Convert to BGR if grayscale
            if len(roi_image.shape) == 2:
                overlay = cv2.cvtColor(roi_image, cv2.COLOR_GRAY2BGR)
            else:
                overlay = roi_image.copy()

            # Adjust contour coordinates to be relative to ROI
            # Contour has shape (N, 1, 2) in OpenCV format
            contour_roi = contour.copy()
            contour_roi[:, 0, 0] -= x  # Subtract ROI x offset
            contour_roi[:, 0, 1] -= y  # Subtract ROI y offset

            # Adjust center to be relative to ROI
            center_roi = (int(center.x - x), int(center.y - y))
        else:
            # No ROI - use full image
            if len(original.shape) == 2:
                overlay = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
            else:
                overlay = original.copy()

            contour_roi = contour
            center_roi = (int(center.x), int(center.y))

        # Draw contour
        cv2.drawContours(overlay, [contour_roi.astype(np.int32)], -1, (0, 255, 255), 2)  # Cyan

        # Draw center point
        cv2.circle(overlay, center_roi, 5, (0, 0, 255), -1)  # Red

        # Draw rotation indicator (line from center showing angle)
        line_length = 50
        angle_rad = np.radians(angle)
        end_x = int(center_roi[0] + line_length * np.cos(angle_rad))
        end_y = int(center_roi[1] + line_length * np.sin(angle_rad))
        cv2.arrowedLine(overlay, center_roi, (end_x, end_y), (0, 255, 0), 3, tipLength=0.3)

        # Add text info
        text = f"Rotation: {angle:.1f}deg ({method.value})"
        cv2.putText(overlay, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Encode to base64
        _, buffer = cv2.imencode(".png", overlay)
        visualization["overlay"] = base64.b64encode(buffer).decode("utf-8")

        return visualization
