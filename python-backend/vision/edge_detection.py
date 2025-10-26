"""
Edge detection algorithms for machine vision.
"""

from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from api.models import ROI, Point, VisionObject, VisionObjectType
from core.constants import EdgeDetectionDefaults
from core.enums import EdgeMethod
from core.image_utils import ImageUtils
from core.overlay_renderer import OverlayRenderer


class EdgeDetector:
    """Edge detection processor."""

    def __init__(self):
        """Initialize edge detector."""
        self.overlay_renderer = OverlayRenderer()

    def detect(
        self,
        image: np.ndarray,
        method: EdgeMethod = EdgeMethod.CANNY,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform edge detection on image.

        Args:
            image: Input image (BGR or grayscale)
            method: Edge detection method
            params: Method-specific and preprocessing parameters (unified)

        Returns:
            Dictionary with edge detection results
        """
        if params is None:
            params = {}

        # Preprocessing (using params instead of separate preprocessing dict)
        processed_image = self._preprocess(image, params)

        # Convert to grayscale if needed
        gray = ImageUtils.ensure_grayscale(processed_image)

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

        # Create visualization using OverlayRenderer
        show_centers = params.get("show_centers", EdgeDetectionDefaults.SHOW_CENTERS)
        image = self.overlay_renderer.render_edge_detection(
            processed_image, objects, show_centers=show_centers
        )

        return {
            "success": True,
            "method": method,
            "objects": objects,
            "image": image,
        }

    def _preprocess(self, image: np.ndarray, params: Optional[Dict[str, Any]]) -> np.ndarray:
        """
        Apply preprocessing to image using parameters from unified params dict.

        Args:
            image: Input image
            params: Unified parameters dict containing preprocessing options

        Returns:
            Preprocessed image
        """
        if not params:
            return image

        result = image.copy()

        # Gaussian blur
        if params.get("blur_enabled", False):
            kernel_size = int(params.get("blur_kernel", EdgeDetectionDefaults.BLUR_KERNEL_SIZE))
            if kernel_size % 2 == 0:
                kernel_size += 1  # Ensure odd kernel size
            result = cv2.GaussianBlur(result, (kernel_size, kernel_size), 0)

        # Bilateral filter (edge-preserving blur)
        if params.get("bilateral_enabled", False):
            d = int(params.get("bilateral_d", EdgeDetectionDefaults.BILATERAL_D))
            sigma_color = float(
                params.get(
                    "bilateral_sigma_color",
                    EdgeDetectionDefaults.BILATERAL_SIGMA_COLOR,
                )
            )
            sigma_space = float(
                params.get(
                    "bilateral_sigma_space",
                    EdgeDetectionDefaults.BILATERAL_SIGMA_SPACE,
                )
            )
            result = cv2.bilateralFilter(result, d, sigma_color, sigma_space)

        # Morphological operations
        if params.get("morphology_enabled", False):
            operation = params.get("morphology_operation", "close")
            kernel_size = int(
                params.get(
                    "morphology_kernel",
                    EdgeDetectionDefaults.MORPHOLOGY_KERNEL_SIZE,
                )
            )
            kernel = np.ones((kernel_size, kernel_size), np.uint8)

            if operation == "close":
                result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
            elif operation == "open":
                result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
            elif operation == "gradient":
                result = cv2.morphologyEx(result, cv2.MORPH_GRADIENT, kernel)

        # Histogram equalization
        if params.get("equalize_enabled", False):
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
        low_threshold = params.get("canny_low", EdgeDetectionDefaults.CANNY_LOW_THRESHOLD)
        high_threshold = params.get("canny_high", EdgeDetectionDefaults.CANNY_HIGH_THRESHOLD)
        aperture_size = params.get("canny_aperture", EdgeDetectionDefaults.CANNY_APERTURE_SIZE)
        l2_gradient = params.get("canny_l2_gradient", EdgeDetectionDefaults.CANNY_L2_GRADIENT)

        return cv2.Canny(
            gray,
            low_threshold,
            high_threshold,
            apertureSize=aperture_size,
            L2gradient=l2_gradient,
        )

    def _detect_sobel(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Sobel edge detection."""
        kernel_size = int(params.get("sobel_kernel", EdgeDetectionDefaults.SOBEL_KERNEL_SIZE))
        scale = float(params.get("sobel_scale", EdgeDetectionDefaults.SOBEL_SCALE))
        delta = float(params.get("sobel_delta", EdgeDetectionDefaults.SOBEL_DELTA))

        # Compute gradients
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=kernel_size, scale=scale, delta=delta)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=kernel_size, scale=scale, delta=delta)

        # Combine gradients
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Threshold
        threshold = float(params.get("sobel_threshold", EdgeDetectionDefaults.SOBEL_THRESHOLD))
        edges = np.uint8(magnitude > threshold) * 255

        return edges

    def _detect_laplacian(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Laplacian edge detection."""
        kernel_size = int(
            params.get("laplacian_kernel", EdgeDetectionDefaults.LAPLACIAN_KERNEL_SIZE)
        )
        scale = float(params.get("laplacian_scale", EdgeDetectionDefaults.LAPLACIAN_SCALE))
        delta = float(params.get("laplacian_delta", EdgeDetectionDefaults.LAPLACIAN_DELTA))

        # Apply Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=kernel_size, scale=scale, delta=delta)

        # Convert to absolute values and threshold
        laplacian = np.abs(laplacian)
        threshold = float(
            params.get("laplacian_threshold", EdgeDetectionDefaults.LAPLACIAN_THRESHOLD)
        )
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
        threshold = float(params.get("prewitt_threshold", EdgeDetectionDefaults.PREWITT_THRESHOLD))
        edges = np.uint8(magnitude > threshold) * 255

        return edges

    def _detect_scharr(self, gray: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply Scharr edge detection."""
        scale = float(params.get("scharr_scale", EdgeDetectionDefaults.SCHARR_SCALE))
        delta = float(params.get("scharr_delta", EdgeDetectionDefaults.SCHARR_DELTA))

        # Compute gradients using Scharr operator
        grad_x = cv2.Scharr(gray, cv2.CV_64F, 1, 0, scale=scale, delta=delta)
        grad_y = cv2.Scharr(gray, cv2.CV_64F, 0, 1, scale=scale, delta=delta)

        # Combine gradients
        magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Threshold
        threshold = float(params.get("scharr_threshold", EdgeDetectionDefaults.SCHARR_THRESHOLD))
        edges = np.uint8(magnitude > threshold) * 255

        return edges

    def _detect_morphological_gradient(
        self, gray: np.ndarray, params: Dict[str, Any]
    ) -> np.ndarray:
        """Apply morphological gradient edge detection."""
        kernel_size = int(params.get("morph_kernel", EdgeDetectionDefaults.MORPH_KERNEL_SIZE))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)

        # Morphological gradient
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)

        # Threshold
        threshold = float(params.get("morph_threshold", EdgeDetectionDefaults.MORPH_THRESHOLD))
        edges = np.uint8(gradient > threshold) * 255

        return edges

    def _filter_contours(self, contours: list, params: Dict[str, Any]) -> list:
        """Filter contours based on parameters."""
        min_area = float(params.get("min_contour_area", EdgeDetectionDefaults.MIN_CONTOUR_AREA))
        max_area = float(params.get("max_contour_area", float("inf")))
        min_perimeter = float(
            params.get(
                "min_contour_perimeter",
                EdgeDetectionDefaults.MIN_CONTOUR_PERIMETER,
            )
        )
        max_perimeter = float(params.get("max_contour_perimeter", float("inf")))

        filtered = []
        for contour in contours:
            # Calculate all contour properties using utility function
            props = ImageUtils.calculate_contour_properties(contour)
            area = props["area"]
            perimeter = props["perimeter"]

            # Apply filters
            if area < min_area or area > max_area:
                continue
            if perimeter < min_perimeter or perimeter > max_perimeter:
                continue

            # Extract individual properties
            cx, cy = props["center"]
            x, y, w, h = props["bounding_box"]

            # Approximated contour
            epsilon = EdgeDetectionDefaults.CONTOUR_APPROX_EPSILON * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Flatten contour from shape (N, 1, 2) to [[x, y], [x, y], ...]
            contour_points = contour.reshape(-1, 2).tolist()

            filtered.append(
                {
                    "contour": contour_points,
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
        max_contours = int(params.get("max_contours", EdgeDetectionDefaults.MAX_CONTOURS))
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
                contour=contour_dict["contour"],
            )
            objects.append(obj)
        return objects
