"""
Overlay rendering utilities for vision detection results.

Provides consistent visualization of detection results across different
vision algorithms (template matching, edge detection, color detection).
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from core.utils.image_utils import ImageUtils
from schemas import VisionObject


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
        contour_points: Optional[list] = None,
    ) -> np.ndarray:
        """
        Render color detection results.

        Args:
            image: Input image
            obj: Detected color region object
            expected_color: Expected color (if color matching was performed)
            contour_points: Optional contour points (to show analyzed region)

        Returns:
            Image with overlays
        """
        result = image.copy()
        bbox = obj.bounding_box
        x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height

        # Determine color based on match status
        is_match = obj.properties.get("match", True)
        color = self.COLOR_SUCCESS if (is_match or expected_color is None) else self.COLOR_FAILURE

        # Draw contour if used for masking
        if contour_points is not None:
            try:
                contour = np.array(contour_points, dtype=np.int32)
                # Draw cyan contour outline to show masked region (distinct from bbox)
                cv2.drawContours(result, [contour], -1, (255, 255, 0), 2)  # Cyan
            except Exception:
                pass  # Fall back to just bbox if contour drawing fails

        # Draw ROI rectangle (bounding box)
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

    def draw_contour(
        self,
        image: np.ndarray,
        contour: np.ndarray,
        color: Tuple[int, int, int] = COLOR_INFO,
        thickness: Optional[int] = None,
    ) -> np.ndarray:
        """
        Draw a contour on the image.

        Args:
            image: Input image
            contour: Contour points (OpenCV format)
            color: Contour color in BGR format
            thickness: Line thickness (None = use default)

        Returns:
            Image with contour drawn
        """
        thickness = thickness or self.thickness
        cv2.drawContours(image, [contour.astype(np.int32)], -1, color, thickness, self.line_type)
        return image

    def draw_rotation_indicator(
        self,
        image: np.ndarray,
        center_x: float,
        center_y: float,
        angle_deg: float,
        length: int = 50,
        color: Tuple[int, int, int] = (0, 165, 255),  # Orange
        thickness: Optional[int] = None,
        arrow_tip_length: float = 0.3,
    ) -> np.ndarray:
        """
        Draw rotation indicator arrow from center showing angle.

        Args:
            image: Input image
            center_x: Center x coordinate
            center_y: Center y coordinate
            angle_deg: Rotation angle in degrees
            length: Arrow length in pixels
            color: Arrow color
            thickness: Line thickness
            arrow_tip_length: Arrow tip size ratio

        Returns:
            Image with rotation arrow drawn
        """
        thickness = thickness or self.thickness
        center = (int(center_x), int(center_y))

        # Calculate end point from angle
        angle_rad = np.radians(angle_deg)
        end_x = int(center_x + length * np.cos(angle_rad))
        end_y = int(center_y + length * np.sin(angle_rad))

        # Draw arrowed line
        cv2.arrowedLine(
            image,
            center,
            (end_x, end_y),
            color,
            thickness,
            self.line_type,
            tipLength=arrow_tip_length,
        )

        return image

    def render_aruco_markers(
        self,
        image: np.ndarray,
        objects: List[VisionObject],
        show_ids: bool = True,
        show_rotation: bool = True,
    ) -> np.ndarray:
        """
        Render ArUco marker detection results.

        Args:
            image: Input image
            objects: List of detected ArUco markers
            show_ids: Whether to show marker IDs
            show_rotation: Whether to show rotation indicators

        Returns:
            Image with overlays
        """
        result = ImageUtils.ensure_bgr(image)

        for obj in objects:
            bbox = obj.bounding_box
            marker_id = obj.properties.get("marker_id", "?")
            corners = obj.properties.get("corners", None)

            # Draw marker corners if available
            if corners is not None:
                corners_array = np.array(corners, dtype=np.int32)
                # Draw marker outline
                cv2.polylines(result, [corners_array], True, self.COLOR_SUCCESS, 2, self.line_type)

            # Draw bounding box
            self.draw_bounding_box(
                result, bbox.x, bbox.y, bbox.width, bbox.height, self.COLOR_SUCCESS
            )

            # Draw marker ID
            if show_ids:
                text = f"ID:{marker_id}"
                self.draw_label(result, text, bbox.x, bbox.y - 10, self.COLOR_SUCCESS)

            # Draw rotation indicator
            if show_rotation and obj.rotation is not None:
                self.draw_center_point(
                    result, obj.center.x, obj.center.y, self.COLOR_INFO, radius=5
                )
                self.draw_rotation_indicator(
                    result, obj.center.x, obj.center.y, obj.rotation, length=40
                )

        # Add summary text
        text = f"Markers: {len(objects)}"
        cv2.putText(result, text, (10, 30), self.font, 1, (255, 255, 255), 2, self.line_type)

        return result

    def render_rotation_analysis(
        self,
        image: np.ndarray,
        obj: VisionObject,
        contour: Optional[np.ndarray] = None,
        method: str = "unknown",
    ) -> np.ndarray:
        """
        Render rotation detection results.

        Args:
            image: Input image
            obj: Rotation analysis object
            contour: Optional contour to draw
            method: Detection method name

        Returns:
            Image with overlays
        """
        result = ImageUtils.ensure_bgr(image)
        bbox = obj.bounding_box

        # Draw contour if provided
        if contour is not None:
            self.draw_contour(result, contour, (0, 255, 0), thickness=2)

        # Draw bounding box
        self.draw_bounding_box(result, bbox.x, bbox.y, bbox.width, bbox.height, self.COLOR_INFO)

        # Draw center point
        self.draw_center_point(result, obj.center.x, obj.center.y, (0, 0, 255), radius=5)

        # Draw rotation indicator
        if obj.rotation is not None:
            self.draw_rotation_indicator(
                result, obj.center.x, obj.center.y, obj.rotation, length=50
            )

        # Add rotation text
        text = f"Rotation: {obj.rotation:.1f}deg ({method})"
        cv2.putText(result, text, (10, 30), self.font, 0.7, (255, 255, 255), 2, self.line_type)

        return result

    def render_edge_detection(
        self,
        original: np.ndarray,
        objects: List[VisionObject],
        show_centers: bool = True,
    ) -> np.ndarray:
        """
        Render edge detection results with contours and annotations.

        Args:
            original: Original image
            objects: Detected contour objects
            show_centers: Whether to show center points

        Returns:
            Annotated image as np.ndarray
        """
        # Overlay on original
        overlay = ImageUtils.ensure_bgr(original)

        # Draw contours
        for i, obj in enumerate(objects):
            # Get contour from object if available
            contour_points = obj.contour
            if contour_points:
                contour = np.array(contour_points, dtype=np.int32)
                # Green for largest, yellow for others
                color = self.COLOR_SUCCESS if i == 0 else self.COLOR_INFO
                self.draw_contour(overlay, contour, color, thickness=2)

            # Draw bounding box
            bbox = obj.bounding_box
            self.draw_bounding_box(
                overlay, bbox.x, bbox.y, bbox.width, bbox.height, (255, 0, 0), thickness=1
            )

            # Draw center point
            if show_centers:
                self.draw_center_point(overlay, obj.center.x, obj.center.y, (0, 0, 255))

        # Add text info
        text = f"Contours: {len(objects)}"
        cv2.putText(overlay, text, (10, 30), self.font, 1, (255, 255, 255), 2, self.line_type)

        return overlay

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
        elif object_type == "aruco_marker":
            show_ids = kwargs.get("show_ids", True)
            show_rotation = kwargs.get("show_rotation", True)
            return self.render_aruco_markers(image, objects, show_ids, show_rotation)
        elif object_type == "rotation_analysis":
            contour = kwargs.get("contour", None)
            method = kwargs.get("method", "unknown")
            return self.render_rotation_analysis(image, objects[0], contour, method)
        else:
            # Default: simple bounding boxes
            result = image.copy()
            for obj in objects:
                bbox = obj.bounding_box
                self.draw_bounding_box(
                    result, bbox.x, bbox.y, bbox.width, bbox.height, self.COLOR_INFO
                )
            return result
