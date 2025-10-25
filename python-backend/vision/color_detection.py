"""
Color detection algorithms for machine vision.

Provides automatic dominant color detection using histogram analysis
and k-means clustering.
"""

import logging
from typing import Dict, Optional

import cv2
import numpy as np
from sklearn.cluster import KMeans

from api.models import ROI, Point, VisionObject, VisionObjectType
from core.constants import ColorDetectionDefaults
from vision.color_definitions import count_colors_vectorized, hsv_to_color_name


class ColorDetector:
    """Color detection processor using histogram and k-means methods."""

    def __init__(self):
        """Initialize color detector."""
        self.logger = logging.getLogger(__name__)

    def detect(
        self,
        image: np.ndarray,
        roi: Optional[Dict[str, int]] = None,
        contour_points: Optional[list] = None,
        use_contour_mask: bool = ColorDetectionDefaults.USE_CONTOUR_MASK,
        expected_color: Optional[str] = None,
        min_percentage: float = ColorDetectionDefaults.MIN_PERCENTAGE,
        method: str = ColorDetectionDefaults.DEFAULT_METHOD,
    ) -> Dict:
        """
        Detect dominant color in image or ROI.

        Args:
            image: Input image (BGR format)
            roi: Optional region of interest {x, y, width, height}
            contour_points: Optional contour points for masking
            use_contour_mask: Whether to use contour mask (if contour_points provided)
            expected_color: Expected color name (or None to just detect)
            min_percentage: Minimum percentage for color match
            method: Detection method ("histogram" or "kmeans")

        Returns:
            Dictionary with detection results
        """
        # Extract ROI if specified
        if roi is not None:
            x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
            roi_image = image[y : y + h, x : x + w]
        else:
            roi_image = image
            x, y, w, h = 0, 0, image.shape[1], image.shape[0]

        # Convert to HSV
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)

        # Create contour mask if requested and available
        mask = None
        analyzed_pixels = roi_image.shape[0] * roi_image.shape[1]

        if use_contour_mask and contour_points:
            try:
                # Convert contour to ROI-relative coordinates
                contour_array = np.array(contour_points)
                roi_contour = contour_array - [x, y]

                # Create binary mask
                mask = np.zeros(roi_image.shape[:2], dtype=np.uint8)
                cv2.fillPoly(mask, [roi_contour.astype(np.int32)], 255)

                # Count actual analyzed pixels
                analyzed_pixels = cv2.countNonZero(mask)
            except Exception as e:
                # If mask creation fails, fall back to full ROI
                self.logger.warning(f"Contour mask creation failed: {e}")
                mask = None

        # Detect dominant colors
        if method == "kmeans":
            color_info = self._detect_kmeans(hsv, mask)
        else:  # histogram (default)
            color_info = self._detect_histogram(hsv, mask)

        # Check if it matches expected color
        match = False
        if expected_color is not None:
            dominant_color = color_info["dominant_color"]
            dominant_percentage = color_info["color_percentages"].get(dominant_color, 0)
            match = (dominant_color == expected_color) and (dominant_percentage >= min_percentage)

        confidence = color_info["color_percentages"].get(color_info["dominant_color"], 0) / 100.0

        # Create VisionObject
        vision_object = VisionObject(
            object_id="color_0",
            object_type=VisionObjectType.COLOR_REGION.value,
            bounding_box=ROI(x=x, y=y, width=w, height=h),
            center=Point(x=float(x + w / 2), y=float(y + h / 2)),
            confidence=confidence,
            area=float(analyzed_pixels),
            properties={
                "dominant_color": color_info["dominant_color"],
                "color_percentages": color_info["all_colors"],
                "hsv_mean": color_info.get("hsv_mean", [0, 0, 0]),
                "expected_color": expected_color,
                "match": match,
                "method": method,
            },
        )

        # Create visualization
        visualization_image = self._create_visualization(
            image, roi_image, vision_object, expected_color, contour_points, x, y
        )

        return {
            "objects": [vision_object],
            "visualization": {"image": visualization_image},
            "success": True,
            "method": method,
        }

    def _detect_histogram(self, hsv: np.ndarray, mask: Optional[np.ndarray] = None) -> Dict:
        """
        Detect dominant color using histogram peak detection (fast).

        Uses vectorized NumPy operations for 10-50x performance improvement
        over nested Python loops.

        Args:
            hsv: HSV image
            mask: Optional binary mask (only analyze masked pixels)

        Returns:
            Dictionary with color information
        """
        h, s, v = cv2.split(hsv)

        # Apply mask if provided
        if mask is not None:
            # Extract only masked pixels to avoid counting zeros as black
            masked_pixels = hsv[mask > 0]
            if len(masked_pixels) == 0:
                # Empty mask, return default
                total_pixels = 1
                color_counts = {"black": 0}
            else:
                h_masked = masked_pixels[:, 0]
                s_masked = masked_pixels[:, 1]
                v_masked = masked_pixels[:, 2]
                total_pixels = len(masked_pixels)
                # Reshape back to 2D for vectorized counting
                h = h_masked.reshape(-1, 1)
                s = s_masked.reshape(-1, 1)
                v = v_masked.reshape(-1, 1)
                color_counts = count_colors_vectorized(h, s, v)
        else:
            total_pixels = hsv.shape[0] * hsv.shape[1]
            # Use vectorized color counting (much faster than pixel iteration)
            color_counts = count_colors_vectorized(h, s, v)

        # Calculate percentages
        color_percentages = {
            color: (count / total_pixels) * 100 for color, count in color_counts.items()
        }

        # Find dominant color
        dominant_color = max(color_percentages, key=color_percentages.get)

        # Calculate mean HSV for dominant color
        hsv_mean = [int(np.mean(h)), int(np.mean(s)), int(np.mean(v))]

        return {
            "dominant_color": dominant_color,
            "color_percentages": color_percentages,
            "all_colors": {k: round(v, 1) for k, v in color_percentages.items() if v > 0},
            "hsv_mean": hsv_mean,
        }

    def _detect_kmeans(
        self,
        hsv: np.ndarray,
        mask: Optional[np.ndarray] = None,
        k: int = ColorDetectionDefaults.KMEANS_CLUSTERS,
    ) -> Dict:
        """
        Detect dominant colors using k-means clustering (more accurate, slower).

        Args:
            hsv: HSV image
            mask: Optional binary mask (only analyze masked pixels)
            k: Number of clusters (dominant colors to find)

        Returns:
            Dictionary with color information
        """
        # Reshape image to list of pixels
        if mask is not None:
            # Extract only masked pixels
            pixels = hsv[mask > 0]
        else:
            pixels = hsv.reshape(-1, 3)
        pixels = np.float32(pixels)

        # Perform k-means clustering
        kmeans = KMeans(
            n_clusters=k,
            random_state=ColorDetectionDefaults.KMEANS_RANDOM_STATE,
            n_init=ColorDetectionDefaults.KMEANS_N_INIT,
        )
        kmeans.fit(pixels)

        # Get cluster centers and labels
        centers = kmeans.cluster_centers_
        labels = kmeans.labels_

        # Count pixels in each cluster
        label_counts = np.bincount(labels)
        total_pixels = len(labels)

        # Map each cluster center to a color name
        cluster_colors = []
        for i, center in enumerate(centers):
            h, s, v = center
            color_name = hsv_to_color_name(int(h), int(s), int(v))
            if color_name is None:
                color_name = "unknown"

            percentage = (label_counts[i] / total_pixels) * 100
            cluster_colors.append({"color": color_name, "percentage": percentage, "hsv": center})

        # Sort by percentage
        cluster_colors.sort(key=lambda x: x["percentage"], reverse=True)

        # Aggregate colors (multiple clusters might map to same color)
        color_percentages = {}
        for cluster in cluster_colors:
            color = cluster["color"]
            if color not in color_percentages:
                color_percentages[color] = 0
            color_percentages[color] += cluster["percentage"]

        # Find dominant color
        dominant_color = max(color_percentages, key=color_percentages.get)

        # Get HSV mean for dominant color
        dominant_cluster = cluster_colors[0]
        hsv_mean = [int(v) for v in dominant_cluster["hsv"]]

        return {
            "dominant_color": dominant_color,
            "color_percentages": color_percentages,
            "all_colors": {k: round(v, 1) for k, v in color_percentages.items() if v > 0},
            "hsv_mean": hsv_mean,
        }

    def _create_visualization(
        self,
        full_image: np.ndarray,
        roi_image: np.ndarray,
        obj: VisionObject,
        expected_color: Optional[str],
        contour_points: Optional[list],
        roi_x: int,
        roi_y: int,
    ) -> np.ndarray:
        """
        Create visualization overlay for color detection.

        Args:
            full_image: Full original image
            roi_image: ROI image that was analyzed
            obj: VisionObject with detection results
            expected_color: Expected color (if color matching)
            contour_points: Optional contour points for overlay
            roi_x: ROI x offset in full image
            roi_y: ROI y offset in full image

        Returns:
            Image with visualization overlay
        """
        # Convert grayscale to BGR if needed
        if len(full_image.shape) == 2:
            result = cv2.cvtColor(full_image, cv2.COLOR_GRAY2BGR)
        else:
            result = full_image.copy()

        bbox = obj.bounding_box
        x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height

        # Determine color based on match status
        is_match = obj.properties.get("match", True)
        color = (0, 255, 0) if (is_match or expected_color is None) else (0, 0, 255)  # Green or Red

        # Draw contour if used for masking
        if contour_points is not None:
            try:
                contour = np.array(contour_points, dtype=np.int32)
                # Draw cyan contour outline to show masked region
                cv2.drawContours(result, [contour], -1, (255, 255, 0), 2)  # Cyan
            except Exception:
                pass  # Fall back to just bbox

        # Draw bounding box
        cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)

        # Add text with dominant color
        dominant_color = obj.properties.get("dominant_color", "unknown")
        confidence_pct = obj.confidence * 100
        text = f"{dominant_color} ({confidence_pct:.1f}%)"
        cv2.putText(result, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Add match/fail indicator if expected color was provided
        if expected_color is not None:
            status_text = "MATCH" if is_match else "FAIL"
            cv2.putText(
                result, status_text, (x, y + h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )

        return result
