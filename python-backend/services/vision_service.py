"""
Vision Service - Business logic for vision processing operations.

This service orchestrates vision processing operations including
template matching, edge detection, and other computer vision tasks.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from api.exceptions import ImageNotFoundException, TemplateNotFoundException
from api.models import ROI, Point, VisionObject
from core.history_buffer import HistoryBuffer
from core.image_manager import ImageManager
from core.roi_handler import ROIHandler
from core.template_manager import TemplateManager
from vision.color_detection import ColorDetector

logger = logging.getLogger(__name__)


class VisionService:
    """
    Service for vision processing operations.

    This service combines template matching, edge detection, and other
    vision algorithms with image management and history tracking.
    """

    def __init__(
        self,
        image_manager: ImageManager,
        template_manager: TemplateManager,
        history_buffer: HistoryBuffer,
    ):
        """
        Initialize vision service.

        Args:
            image_manager: Image manager instance
            template_manager: Template manager instance
            history_buffer: History buffer instance
        """
        self.image_manager = image_manager
        self.template_manager = template_manager
        self.history_buffer = history_buffer
        self.color_detector = ColorDetector()

    def template_match(
        self,
        image_id: str,
        template_id: str,
        method: str = "TM_CCOEFF_NORMED",
        threshold: float = 0.8,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
        """
        Perform template matching on an image.

        Args:
            image_id: Image identifier
            template_id: Template identifier
            method: OpenCV matching method
            threshold: Match threshold (0-1)
            record_history: Whether to record in history

        Returns:
            Tuple of (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
            TemplateNotFoundException: If template not found
        """
        start_time = time.time()

        # Get image
        image = self.image_manager.get(image_id)
        if image is None:
            raise ImageNotFoundException(image_id)

        # Get template
        template = self.template_manager.get_template(template_id)
        if template is None:
            raise TemplateNotFoundException(template_id)

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            search_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            search_gray = image

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template

        # Perform template matching
        cv_method = getattr(cv2, method)
        result = cv2.matchTemplate(search_gray, template_gray, cv_method)

        # Find matches above threshold
        detected_objects = []
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # For SQDIFF methods, lower is better
        if method in ["TM_SQDIFF", "TM_SQDIFF_NORMED"]:
            if min_val <= (1 - threshold):
                score = 1 - min_val
                loc = min_loc
            else:
                score = 0
                loc = None
        else:
            if max_val >= threshold:
                score = max_val
                loc = max_loc
            else:
                score = 0
                loc = None

        # Create DetectedObject if match found
        if loc is not None:
            x = loc[0]
            y = loc[1]
            w = template.shape[1]
            h = template.shape[0]

            detected_objects.append(
                VisionObject(
                    object_id="match_0",
                    object_type="template_match",
                    bounding_box=ROI(x=x, y=y, width=w, height=h),
                    center=Point(x=float(x + w // 2), y=float(y + h // 2)),
                    confidence=min(float(score), 1.0),  # Clamp to avoid floating point errors
                    rotation=0.0,
                    properties={
                        "template_id": template_id,
                        "method": method,
                        "scale": 1.0,
                        "raw_score": float(score),
                    },
                )
            )

        # Create result image with overlay
        result_image = image.copy()
        for obj in detected_objects:
            bbox = obj.bounding_box
            pt1 = (bbox.x, bbox.y)
            pt2 = (bbox.x + bbox.width, bbox.y + bbox.height)
            cv2.rectangle(result_image, pt1, pt2, (0, 255, 0), 2)
            cv2.putText(
                result_image,
                f"{obj.confidence:.2f}",
                (pt1[0], pt1[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

        # Create thumbnail (uses config width)
        _, thumbnail_base64 = self.image_manager.create_thumbnail(result_image)

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Add to history if requested
        if record_history:
            self.history_buffer.add_inspection(
                image_id=image_id,
                result="PASS" if detected_objects else "FAIL",
                detections=[
                    {
                        "type": "template_match",
                        "template_id": template_id,
                        "found": len(detected_objects) > 0,
                        "confidence": detected_objects[0].confidence if detected_objects else 0,
                        "count": len(detected_objects),
                    }
                ],
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Template matching: {len(detected_objects)} matches " f"in {processing_time}ms"
        )

        return detected_objects, thumbnail_base64, processing_time

    def learn_template_from_roi(
        self, image_id: str, roi: ROI, name: str, description: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Learn a template from an image region.

        Args:
            image_id: Source image identifier
            roi: ROI to extract as template
            name: Template name
            description: Optional description

        Returns:
            Tuple of (template_id, thumbnail_base64)

        Raises:
            ImageNotFoundException: If image not found
            ValueError: If ROI is invalid
        """
        # Get source image
        source_image = self.image_manager.get(image_id)
        if source_image is None:
            raise ImageNotFoundException(image_id)

        # Validate ROI
        is_valid, error_msg = ROIHandler.validate_roi(roi, source_image.shape)
        if not is_valid:
            raise ValueError(error_msg)

        # Learn template
        template_id = self.template_manager.learn_template(
            name=name, source_image=source_image, roi=roi.to_dict(), description=description
        )

        # Get thumbnail
        thumbnail_base64 = self.template_manager.create_template_thumbnail(template_id)

        logger.info(f"Template learned from ROI: {template_id}")
        return template_id, thumbnail_base64

    def edge_detect(
        self,
        image_id: str,
        method: str = "canny",
        params: Optional[Dict] = None,
        preprocessing: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[Dict, str, int]:
        """
        Perform edge detection on an image.

        Args:
            image_id: Image identifier
            method: Edge detection method (canny, sobel, laplacian, etc.)
            params: Method-specific parameters
            preprocessing: Optional preprocessing parameters
            record_history: Whether to record in history

        Returns:
            Tuple of (result_dict, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        import time

        from vision.edge_detection import EdgeDetector, EdgeMethod

        start_time = time.time()

        # Get image
        image = self.image_manager.get(image_id)
        if image is None:
            raise ImageNotFoundException(image_id)

        # Initialize edge detector
        detector = EdgeDetector()

        # Set default parameters if not provided
        if params is None:
            params = {}

        # Parse method
        try:
            edge_method = EdgeMethod(method.lower())
        except ValueError:
            edge_method = EdgeMethod.CANNY

        # Set default parameters based on method
        if edge_method == EdgeMethod.CANNY:
            from core.constants import VisionConstants

            params.setdefault("canny_low", VisionConstants.CANNY_LOW_THRESHOLD_DEFAULT)
            params.setdefault("canny_high", VisionConstants.CANNY_HIGH_THRESHOLD_DEFAULT)
        elif edge_method == EdgeMethod.SOBEL:
            params.setdefault("sobel_threshold", 50)
        elif edge_method == EdgeMethod.LAPLACIAN:
            params.setdefault("laplacian_threshold", 30)

        # Perform edge detection
        result = detector.detect(
            image=image, method=edge_method, params=params, preprocessing=preprocessing
        )

        # Create result image with overlay
        if result["visualization"] and "overlay" in result["visualization"]:
            import base64

            overlay_data = base64.b64decode(result["visualization"]["overlay"])
            nparr = np.frombuffer(overlay_data, np.uint8)
            result_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            result_image = image.copy()

        # Create thumbnail (uses config width)
        _, thumbnail_base64 = self.image_manager.create_thumbnail(result_image)

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Add to history if requested
        if record_history:
            object_count = len(result["objects"])
            self.history_buffer.add_inspection(
                image_id=image_id,
                result="PASS" if object_count > 0 else "FAIL",
                detections=[
                    {
                        "type": "edge_detection",
                        "method": edge_method.value,
                        "found": object_count > 0,
                        "contour_count": object_count,
                    }
                ],
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Edge detection completed: {len(result['objects'])} contours found "
            f"in {processing_time}ms"
        )

        return result, thumbnail_base64, processing_time

    def color_detect(
        self,
        image_id: str,
        roi: Optional[Dict[str, int]] = None,
        expected_color: Optional[str] = None,
        min_percentage: float = 50.0,
        method: str = "histogram",
        record_history: bool = True,
    ) -> Tuple[VisionObject, str, int]:
        """
        Perform color detection on an image.

        Args:
            image_id: Image identifier
            roi: Optional region of interest {x, y, width, height}
            expected_color: Expected color name (or None to just detect)
            min_percentage: Minimum percentage for color match
            method: Detection method ("histogram" or "kmeans")
            record_history: Whether to record in history

        Returns:
            Tuple of (detected_object, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        start_time = time.time()

        # Get image
        image = self.image_manager.get(image_id)
        if image is None:
            raise ImageNotFoundException(image_id)

        # Perform color detection
        result = self.color_detector.detect(
            image=image,
            roi=roi,
            expected_color=expected_color,
            min_percentage=min_percentage,
            method=method,
        )

        # Create VisionObject
        detected_object = VisionObject(
            object_id="color_0",
            object_type="color_region",
            bounding_box=ROI(**result["roi"]),
            center=Point(
                x=result["roi"]["x"] + result["roi"]["width"] / 2,
                y=result["roi"]["y"] + result["roi"]["height"] / 2,
            ),
            confidence=result["confidence"],
            area=float(result["analyzed_pixels"]),
            properties={
                "dominant_color": result["dominant_color"],
                "color_percentages": result["color_percentages"],
                "hsv_mean": result["hsv_mean"],
                "expected_color": result["expected_color"],
                "match": result["match"],
                "method": method,
            },
        )

        # Create visualization with color overlay
        result_image = image.copy()
        roi_info = result["roi"]
        x, y, w, h = roi_info["x"], roi_info["y"], roi_info["width"], roi_info["height"]

        # Draw ROI rectangle
        color = (0, 255, 0) if result["match"] or expected_color is None else (0, 0, 255)
        cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)

        # Add text with dominant color
        text = f"{result['dominant_color']} ({result['confidence']*100:.1f}%)"
        cv2.putText(
            result_image,
            text,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

        # Add match/fail indicator if expected color was provided
        if expected_color is not None:
            status_text = "MATCH" if result["match"] else "FAIL"
            cv2.putText(
                result_image,
                status_text,
                (x, y + h + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

        # Create thumbnail
        _, thumbnail_base64 = self.image_manager.create_thumbnail(result_image)

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Add to history if requested
        if record_history:
            inspection_result = "PASS" if result["match"] or expected_color is None else "FAIL"
            self.history_buffer.add_inspection(
                image_id=image_id,
                result=inspection_result,
                detections=[
                    {
                        "type": "color_detection",
                        "dominant_color": result["dominant_color"],
                        "expected_color": expected_color,
                        "match": result["match"],
                        "confidence": result["confidence"],
                    }
                ],
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Color detection completed: {result['dominant_color']} "
            f"({result['confidence']*100:.1f}%) in {processing_time}ms"
        )

        return detected_object, thumbnail_base64, processing_time
