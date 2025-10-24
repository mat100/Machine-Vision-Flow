"""
Edge detection algorithms for machine vision.
"""

import base64
from enum import Enum
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from api.models import ROI, Point, VisionObject, VisionObjectType


class EdgeMethod(str, Enum):
    """Available edge detection methods."""

    CANNY = "canny"
    SOBEL = "sobel"
    LAPLACIAN = "laplacian"
    PREWITT = "prewitt"
    SCHARR = "scharr"
    MORPHOLOGICAL_GRADIENT = "morphological_gradient"


class EdgeDetector:
    """Edge detection processor."""

    def __init__(self):
        """Initialize edge detector."""

    def detect(
        self,
        image: np.ndarray,
        method: EdgeMethod = EdgeMethod.CANNY,
        params: Optional[Dict[str, Any]] = None,
        preprocessing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform edge detection on image.

        Args:
            image: Input image (BGR or grayscale)
            method: Edge detection method
            params: Method-specific parameters
            preprocessing: Preprocessing options (blur, threshold, etc.)

        Returns:
            Dictionary with edge detection results
        """
        if params is None:
            params = {}

        # Preprocessing
        processed_image = self._preprocess(image, preprocessing)

        # Convert to grayscale if needed
        if len(processed_image.shape) == 3:
            gray = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = processed_image

        # Apply edge detection
        if method == EdgeMethod.CANNY:
            edges = self._detect_canny(gray, params)
        elif method == EdgeMethod.SOBEL:
            edges = self._detect_sobel(gray, params)
        elif method == EdgeMethod.LAPLACIAN:
            edges = self._detect_laplacian(gray, params)
        elif method == EdgeMethod.PREWITT:
            edges = self._detect_prewitt(gray, params)
        elif method == EdgeMethod.SCHARR:
            edges = self._detect_scharr(gray, params)
        elif method == EdgeMethod.MORPHOLOGICAL_GRADIENT:
            edges = self._detect_morphological_gradient(gray, params)
        else:
            raise ValueError(f"Unknown edge detection method: {method}")

        # Find contours on the edge image
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter and analyze contours
        filtered_contours = self._filter_contours(contours, params)

        # Convert to DetectedObject instances
        objects = self._contours_to_objects(filtered_contours, method.value)

        # Create visualization
        visualization = self._create_visualization(
            processed_image, edges, filtered_contours, params
        )

        return {
            "success": True,
            "method": method,
            "objects": objects,
            "visualization": visualization,
        }

    def _preprocess(self, image: np.ndarray, preprocessing: Optional[Dict[str, Any]]) -> np.ndarray:
        """Apply preprocessing to image."""
        if not preprocessing:
            return image

        result = image.copy()

        # Gaussian blur
        if preprocessing.get("blur_enabled", False):
            kernel_size = int(preprocessing.get("blur_kernel", 5))
            if kernel_size % 2 == 0:
                kernel_size += 1  # Ensure odd kernel size
            result = cv2.GaussianBlur(result, (kernel_size, kernel_size), 0)

        # Bilateral filter (edge-preserving blur)
        if preprocessing.get("bilateral_enabled", False):
            d = int(preprocessing.get("bilateral_d", 9))
            sigma_color = float(preprocessing.get("bilateral_sigma_color", 75))
            sigma_space = float(preprocessing.get("bilateral_sigma_space", 75))
            result = cv2.bilateralFilter(result, d, sigma_color, sigma_space)

        # Morphological operations
        if preprocessing.get("morphology_enabled", False):
            operation = preprocessing.get("morphology_operation", "close")
            kernel_size = int(preprocessing.get("morphology_kernel", 3))
            kernel = np.ones((kernel_size, kernel_size), np.uint8)

            if operation == "close":
                result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
            elif operation == "open":
                result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
            elif operation == "gradient":
                result = cv2.morphologyEx(result, cv2.MORPH_GRADIENT, kernel)

        # Histogram equalization
        if preprocessing.get("equalize_enabled", False):
            if len(result.shape) == 3:
                # Convert to LAB and equalize L channel
                lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
                lightness, a, b = cv2.split(lab)
                lightness = cv2.equalizeHist(lightness)
                result = cv2.cvtColor(cv2.merge([lightness, a, b]), cv2.COLOR_LAB2BGR)
            else:
                result = cv2.equalizeHist(result)

        return result

    def _detect_canny(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Canny edge detection."""
        low_threshold = params.get("canny_low", 50)
        high_threshold = params.get("canny_high", 150)
        aperture_size = params.get("canny_aperture", 3)
        l2_gradient = params.get("canny_l2_gradient", False)

        return cv2.Canny(
            gray, low_threshold, high_threshold, apertureSize=aperture_size, L2gradient=l2_gradient
        )

    def _detect_sobel(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Sobel edge detection."""
        kernel_size = int(params.get("sobel_kernel", 3))
        scale = float(params.get("sobel_scale", 1))
        delta = float(params.get("sobel_delta", 0))

        # Compute gradients
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=kernel_size, scale=scale, delta=delta)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=kernel_size, scale=scale, delta=delta)

        # Combine gradients
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Threshold
        threshold = float(params.get("sobel_threshold", 50))
        edges = np.uint8(magnitude > threshold) * 255

        return edges

    def _detect_laplacian(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Laplacian edge detection."""
        kernel_size = int(params.get("laplacian_kernel", 3))
        scale = float(params.get("laplacian_scale", 1))
        delta = float(params.get("laplacian_delta", 0))

        # Apply Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=kernel_size, scale=scale, delta=delta)

        # Convert to absolute values and threshold
        laplacian = np.abs(laplacian)
        threshold = float(params.get("laplacian_threshold", 30))
        edges = np.uint8(laplacian > threshold) * 255

        return edges

    def _detect_prewitt(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Prewitt edge detection."""
        # Prewitt kernels
        kernel_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
        kernel_y = np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], dtype=np.float32)

        # Apply filters
        grad_x = cv2.filter2D(gray, cv2.CV_32F, kernel_x)
        grad_y = cv2.filter2D(gray, cv2.CV_32F, kernel_y)

        # Combine gradients
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Threshold
        threshold = float(params.get("prewitt_threshold", 50))
        edges = np.uint8(magnitude > threshold) * 255

        return edges

    def _detect_scharr(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Scharr edge detection."""
        scale = float(params.get("scharr_scale", 1))
        delta = float(params.get("scharr_delta", 0))

        # Compute gradients using Scharr operator
        grad_x = cv2.Scharr(gray, cv2.CV_64F, 1, 0, scale=scale, delta=delta)
        grad_y = cv2.Scharr(gray, cv2.CV_64F, 0, 1, scale=scale, delta=delta)

        # Combine gradients
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Threshold
        threshold = float(params.get("scharr_threshold", 50))
        edges = np.uint8(magnitude > threshold) * 255

        return edges

    def _detect_morphological_gradient(
        self, gray: np.ndarray, params: Dict[str, Any]
    ) -> np.ndarray:
        """Apply morphological gradient edge detection."""
        kernel_size = int(params.get("morph_kernel", 3))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)

        # Morphological gradient
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)

        # Threshold
        threshold = float(params.get("morph_threshold", 30))
        edges = np.uint8(gradient > threshold) * 255

        return edges

    def _filter_contours(self, contours: list, params: Dict[str, Any]) -> list:
        """Filter contours based on parameters."""
        min_area = float(params.get("min_contour_area", 10))
        max_area = float(params.get("max_contour_area", float("inf")))
        min_perimeter = float(params.get("min_contour_perimeter", 0))
        max_perimeter = float(params.get("max_contour_perimeter", float("inf")))

        filtered = []
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)

            # Apply filters
            if area < min_area or area > max_area:
                continue
            if perimeter < min_perimeter or perimeter > max_perimeter:
                continue

            # Calculate properties
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = 0, 0

            # Bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Approximated contour
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)

            filtered.append(
                {
                    "contour": contour.tolist(),
                    "area": float(area),
                    "perimeter": float(perimeter),
                    "center": {"x": cx, "y": cy},
                    "bounding_box": {"x": x, "y": y, "width": w, "height": h},
                    "vertex_count": len(approx),
                    "is_closed": True,
                }
            )

        # Sort by area (largest first)
        filtered.sort(key=lambda x: x["area"], reverse=True)

        # Limit number of contours
        max_contours = int(params.get("max_contours", 100))
        return filtered[:max_contours]

    def _contours_to_objects(self, contours: list, method: str) -> List[VisionObject]:
        """Convert contour dicts to VisionObject instances."""
        objects = []
        for i, contour_dict in enumerate(contours):
            obj = VisionObject(
                object_id=f"contour_{i}",
                object_type=VisionObjectType.EDGE_CONTOUR.value,
                bounding_box=ROI(**contour_dict["bounding_box"]),
                center=Point(**contour_dict["center"]),
                confidence=1.0,  # Contours are binary (found/not found)
                area=contour_dict["area"],
                perimeter=contour_dict["perimeter"],
                properties={
                    "method": method,
                    "vertex_count": contour_dict["vertex_count"],
                    "is_closed": contour_dict["is_closed"],
                },
                raw_contour=contour_dict["contour"],
            )
            objects.append(obj)
        return objects

    def _create_visualization(
        self, original: np.ndarray, edges: np.ndarray, contours: list, params: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create visualization images."""
        visualization = {}

        # Edge image
        edge_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        _, buffer = cv2.imencode(".png", edge_colored)
        visualization["edges"] = base64.b64encode(buffer).decode("utf-8")

        # Overlay on original
        if len(original.shape) == 2:
            overlay = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
        else:
            overlay = original.copy()

        # Draw contours
        for i, contour_info in enumerate(contours):
            contour = np.array(contour_info["contour"], dtype=np.int32)
            color = (0, 255, 0) if i == 0 else (0, 255, 255)  # Green for largest, yellow for others
            cv2.drawContours(overlay, [contour], -1, color, 2)

            # Draw bounding box
            bbox = contour_info["bounding_box"]
            cv2.rectangle(
                overlay,
                (bbox["x"], bbox["y"]),
                (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
                (255, 0, 0),
                1,
            )

            # Draw center point
            if params.get("show_centers", True):
                center = contour_info["center"]
                cv2.circle(overlay, (center["x"], center["y"]), 3, (0, 0, 255), -1)

        # Add text info
        text = f"Contours: {len(contours)}"
        cv2.putText(overlay, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        _, buffer = cv2.imencode(".png", overlay)
        visualization["overlay"] = base64.b64encode(buffer).decode("utf-8")

        return visualization
