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
from api.models import BoundingBox, Point, TemplateMatchResult
from core.history_buffer import HistoryBuffer
from core.image_manager import ImageManager
from core.roi_handler import ROI, ROIHandler
from core.template_manager import TemplateManager

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

    def template_match(
        self,
        image_id: str,
        template_id: str,
        method: str = "TM_CCOEFF_NORMED",
        threshold: float = 0.8,
        roi: Optional[ROI] = None,
        record_history: bool = True,
    ) -> Tuple[List[TemplateMatchResult], str, int]:
        """
        Perform template matching on an image.

        Args:
            image_id: Image identifier
            template_id: Template identifier
            method: OpenCV matching method
            threshold: Match threshold (0-1)
            roi: Optional ROI to search in
            record_history: Whether to record in history

        Returns:
            Tuple of (matches, thumbnail_base64, processing_time_ms)

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

        # Apply ROI if specified
        roi_offset = (0, 0)
        if roi:
            search_image = ROIHandler.extract_roi(image, roi, safe_mode=True)
            if search_image is None:
                raise ValueError("Invalid ROI parameters")
            roi_offset = (roi.x, roi.y)
        else:
            search_image = image

        # Convert to grayscale if needed
        if len(search_image.shape) == 3:
            search_gray = cv2.cvtColor(search_image, cv2.COLOR_BGR2GRAY)
        else:
            search_gray = search_image

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template

        # Perform template matching
        cv_method = getattr(cv2, method)
        result = cv2.matchTemplate(search_gray, template_gray, cv_method)

        # Find matches above threshold
        matches = []
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

        # Create result if match found
        if loc is not None:
            # Adjust for ROI offset
            x = loc[0] + roi_offset[0]
            y = loc[1] + roi_offset[1]

            matches.append(
                TemplateMatchResult(
                    position=Point(
                        x=float(x + template.shape[1] // 2), y=float(y + template.shape[0] // 2)
                    ),
                    score=float(score),
                    scale=1.0,
                    rotation=0.0,
                    bounding_box=BoundingBox(
                        top_left=Point(x=float(x), y=float(y)),
                        bottom_right=Point(
                            x=float(x + template.shape[1]), y=float(y + template.shape[0])
                        ),
                    ),
                )
            )

        # Create result image with overlay
        result_image = image.copy()
        for match in matches:
            pt1 = (int(match.bounding_box.top_left.x), int(match.bounding_box.top_left.y))
            pt2 = (int(match.bounding_box.bottom_right.x), int(match.bounding_box.bottom_right.y))
            cv2.rectangle(result_image, pt1, pt2, (0, 255, 0), 2)
            cv2.putText(
                result_image,
                f"{match.score:.2f}",
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
                result="PASS" if matches else "FAIL",
                detections=[
                    {
                        "type": "template_match",
                        "template_id": template_id,
                        "found": len(matches) > 0,
                        "score": matches[0].score if matches else 0,
                        "count": len(matches),
                    }
                ],
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Template matching completed: {len(matches)} matches found " f"in {processing_time}ms"
        )

        return matches, thumbnail_base64, processing_time

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
        roi: Optional[Dict] = None,
        preprocessing: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[Dict, str, int]:
        """
        Perform edge detection on an image.

        Args:
            image_id: Image identifier
            method: Edge detection method (canny, sobel, laplacian, etc.)
            params: Method-specific parameters
            roi: Optional ROI dictionary
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
            image=image, method=edge_method, params=params, roi=roi, preprocessing=preprocessing
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
            self.history_buffer.add_inspection(
                image_id=image_id,
                result="PASS" if result["edges_found"] else "FAIL",
                detections=[
                    {
                        "type": "edge_detection",
                        "method": edge_method.value,
                        "found": result["edges_found"],
                        "contour_count": result["contour_count"],
                        "edge_ratio": result["edge_ratio"],
                    }
                ],
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Edge detection completed: {result['contour_count']} contours found "
            f"in {processing_time}ms"
        )

        return result, thumbnail_base64, processing_time
