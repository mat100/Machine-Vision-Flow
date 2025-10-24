"""
Overlay rendering utilities for vision detection results.

Provides consistent visualization of detection results across different
vision algorithms (template matching, edge detection, color detection).
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from api.models import VisionObject


class OverlayRenderer:
    """
    Renders detection results as overlays on images.

    Provides consistent styling and formatting for bounding boxes,
    labels, and other detection annotations.
    """

    # Default colors (BGR format)
    COLOR_SUCCESS = (0, 255, 0)  # Green
    COLOR_FAILURE = (0, 0, 255)  # Red
    COLOR_INFO = (255, 255, 0)  # Cyan

    def __init__(
        self,
        font=cv2.FONT_HERSHEY_SIMPLEX,
        font_scale: float = 0.5,
        thickness: int = 2,
        line_type=cv2.LINE_AA,
    ):
        """
        Initialize overlay renderer.

        Args:
            font: OpenCV font type
            font_scale: Font scale factor
            thickness: Line thickness for rectangles and text
            line_type: Line type for anti-aliasing
        """
        self.font = font
        self.font_scale = font_scale
        self.thickness = thickness
        self.line_type = line_type

    def draw_bounding_box(
        self,
        image: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Tuple[int, int, int] = COLOR_SUCCESS,
        thickness: Optional[int] = None,
    ) -> np.ndarray:
        """
        Draw a bounding box on the image.

        Args:
            image: Input image
            x: Top-left x coordinate
            y: Top-left y coordinate
            width: Box width
            height: Box height
            color: Box color in BGR format
            thickness: Line thickness (None = use default)

        Returns:
            Image with bounding box drawn
        """
        thickness = thickness or self.thickness
        pt1 = (x, y)
        pt2 = (x + width, y + height)
        cv2.rectangle(image, pt1, pt2, color, thickness, self.line_type)
        return image

    def draw_label(
        self,
        image: np.ndarray,
        text: str,
        x: int,
        y: int,
        color: Tuple[int, int, int] = COLOR_SUCCESS,
        background: bool = False,
    ) -> np.ndarray:
        """
        Draw text label on the image.

        Args:
            image: Input image
            text: Text to draw
            x: Text x coordinate
            y: Text y coordinate
            color: Text color in BGR format
            background: Whether to draw background rectangle

        Returns:
            Image with label drawn
        """
        if background:
            # Calculate text size for background
            (text_width, text_height), baseline = cv2.getTextSize(
                text, self.font, self.font_scale, self.thickness
            )
            # Draw background rectangle
            cv2.rectangle(
                image,
                (x, y - text_height - baseline),
                (x + text_width, y),
                color,
                -1,  # Filled
            )
            # Draw text in white over background
            text_color = (255, 255, 255)
        else:
            text_color = color

        cv2.putText(
            image,
            text,
            (x, y),
            self.font,
            self.font_scale,
            text_color,
            self.thickness,
            self.line_type,
        )
        return image

    def draw_confidence(
        self,
        image: np.ndarray,
        confidence: float,
        x: int,
        y: int,
        color: Tuple[int, int, int] = COLOR_SUCCESS,
    ) -> np.ndarray:
        """
        Draw confidence score above bounding box.

        Args:
            image: Input image
            confidence: Confidence value (0.0-1.0)
            x: X coordinate
            y: Y coordinate (top of bounding box)
            color: Text color

        Returns:
            Image with confidence drawn
        """
        text = f"{confidence:.2f}"
        return self.draw_label(image, text, x, y - 5, color)

    def draw_center_point(
        self,
        image: np.ndarray,
        center_x: float,
        center_y: float,
        color: Tuple[int, int, int] = COLOR_SUCCESS,
        radius: int = 3,
    ) -> np.ndarray:
        """
        Draw center point marker.

        Args:
            image: Input image
            center_x: Center x coordinate
            center_y: Center y coordinate
            color: Marker color
            radius: Circle radius

        Returns:
            Image with center point drawn
        """
        cv2.circle(
            image,
            (int(center_x), int(center_y)),
            radius,
            color,
            -1,  # Filled
            self.line_type,
        )
        return image

    def render_template_matches(self, image: np.ndarray, objects: List[VisionObject]) -> np.ndarray:
        """
        Render template matching results.

        Args:
            image: Input image
            objects: List of detected template matches

        Returns:
            Image with overlays
        """
        result = image.copy()
        for obj in objects:
            bbox = obj.bounding_box
            # Draw bounding box
            self.draw_bounding_box(
                result, bbox.x, bbox.y, bbox.width, bbox.height, self.COLOR_SUCCESS
            )
            # Draw confidence
            self.draw_confidence(result, obj.confidence, bbox.x, bbox.y, self.COLOR_SUCCESS)
        return result

    def render_edge_contours(
        self, image: np.ndarray, objects: List[VisionObject], show_centers: bool = True
    ) -> np.ndarray:
        """
        Render edge detection results.

        Args:
            image: Input image
            objects: List of detected contours
            show_centers: Whether to show center points

        Returns:
            Image with overlays
        """
        result = image.copy()
        for obj in objects:
            bbox = obj.bounding_box
            # Draw bounding box
            self.draw_bounding_box(result, bbox.x, bbox.y, bbox.width, bbox.height, self.COLOR_INFO)
            # Draw center if requested
            if show_centers:
                self.draw_center_point(result, obj.center.x, obj.center.y, self.COLOR_INFO)
        return result

    def render_color_detection(
        self,
        image: np.ndarray,
        obj: VisionObject,
        expected_color: Optional[str] = None,
    ) -> np.ndarray:
        """
        Render color detection results.

        Args:
            image: Input image
            obj: Detected color region object
            expected_color: Expected color (if color matching was performed)

        Returns:
            Image with overlays
        """
        result = image.copy()
        bbox = obj.bounding_box
        x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height

        # Determine color based on match status
        is_match = obj.properties.get("match", True)
        color = self.COLOR_SUCCESS if (is_match or expected_color is None) else self.COLOR_FAILURE

        # Draw ROI rectangle
        self.draw_bounding_box(result, x, y, w, h, color)

        # Add text with dominant color
        dominant_color = obj.properties.get("dominant_color", "unknown")
        confidence_pct = obj.confidence * 100
        text = f"{dominant_color} ({confidence_pct:.1f}%)"
        self.draw_label(result, text, x, y - 10, color)

        # Add match/fail indicator if expected color was provided
        if expected_color is not None:
            status_text = "MATCH" if is_match else "FAIL"
            self.draw_label(result, status_text, x, y + h + 25, color)

        return result

    def render_objects(
        self,
        image: np.ndarray,
        objects: List[VisionObject],
        object_type: Optional[str] = None,
        **kwargs,
    ) -> np.ndarray:
        """
        Auto-detect and render objects based on type.

        Args:
            image: Input image
            objects: List of vision objects
            object_type: Override object type detection
            **kwargs: Additional rendering options

        Returns:
            Image with appropriate overlays
        """
        if not objects:
            return image.copy()

        # Detect type from first object if not specified
        if object_type is None:
            object_type = objects[0].object_type

        # Route to appropriate renderer
        if object_type == "template_match":
            return self.render_template_matches(image, objects)
        elif object_type == "edge_contour":
            show_centers = kwargs.get("show_centers", True)
            return self.render_edge_contours(image, objects, show_centers)
        elif object_type == "color_region":
            expected_color = kwargs.get("expected_color", None)
            return self.render_color_detection(image, objects[0], expected_color)
        else:
            # Default: simple bounding boxes
            result = image.copy()
            for obj in objects:
                bbox = obj.bounding_box
                self.draw_bounding_box(
                    result, bbox.x, bbox.y, bbox.width, bbox.height, self.COLOR_INFO
                )
            return result
