"""
Color detection algorithms for machine vision.

Provides automatic dominant color detection using histogram analysis
and k-means clustering.
"""

from typing import Dict, Optional

import cv2
import numpy as np
from sklearn.cluster import KMeans

from vision.color_definitions import get_available_colors, hsv_to_color_name


class ColorDetector:
    """Color detection processor using histogram and k-means methods."""

    def __init__(self):
        """Initialize color detector."""
        pass

    def detect(
        self,
        image: np.ndarray,
        roi: Optional[Dict[str, int]] = None,
        expected_color: Optional[str] = None,
        min_percentage: float = 50.0,
        method: str = "histogram",
    ) -> Dict:
        """
        Detect dominant color in image or ROI.

        Args:
            image: Input image (BGR format)
            roi: Optional region of interest {x, y, width, height}
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

        # Detect dominant colors
        if method == "kmeans":
            color_info = self._detect_kmeans(hsv)
        else:  # histogram (default)
            color_info = self._detect_histogram(hsv)

        # Check if it matches expected color
        match = False
        if expected_color is not None:
            dominant_color = color_info["dominant_color"]
            dominant_percentage = color_info["color_percentages"].get(dominant_color, 0)
            match = (dominant_color == expected_color) and (dominant_percentage >= min_percentage)

        return {
            "success": True,
            "roi": {"x": x, "y": y, "width": w, "height": h},
            "dominant_color": color_info["dominant_color"],
            "color_percentages": color_info["all_colors"],
            "hsv_mean": color_info.get("hsv_mean", [0, 0, 0]),
            "analyzed_pixels": int(roi_image.shape[0] * roi_image.shape[1]),
            "expected_color": expected_color,
            "match": match,
            "confidence": color_info["color_percentages"].get(color_info["dominant_color"], 0)
            / 100.0,
        }

    def _detect_histogram(self, hsv: np.ndarray) -> Dict:
        """
        Detect dominant color using histogram peak detection (fast).

        Args:
            hsv: HSV image

        Returns:
            Dictionary with color information
        """
        h, s, v = cv2.split(hsv)

        # Calculate pixel counts for each color
        color_counts = {color: 0 for color in get_available_colors()}
        total_pixels = hsv.shape[0] * hsv.shape[1]

        # Iterate through pixels and count matches
        for i in range(hsv.shape[0]):
            for j in range(hsv.shape[1]):
                pixel_h = h[i, j]
                pixel_s = s[i, j]
                pixel_v = v[i, j]

                color_name = hsv_to_color_name(pixel_h, pixel_s, pixel_v)
                if color_name:
                    color_counts[color_name] += 1

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

    def _detect_kmeans(self, hsv: np.ndarray, k: int = 3) -> Dict:
        """
        Detect dominant colors using k-means clustering (more accurate, slower).

        Args:
            hsv: HSV image
            k: Number of clusters (dominant colors to find)

        Returns:
            Dictionary with color information
        """
        # Reshape image to list of pixels
        pixels = hsv.reshape(-1, 3)
        pixels = np.float32(pixels)

        # Perform k-means clustering
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
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
