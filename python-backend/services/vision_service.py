"""
Vision Service - Business logic for vision processing operations.

This service orchestrates vision processing operations including
template matching, edge detection, and other computer vision tasks.
"""

import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from api.exceptions import ImageNotFoundException, TemplateNotFoundException
from api.models import ROI, Point, VisionObject, VisionObjectType
from core.decorators import timer
from core.history_buffer import HistoryBuffer
from core.image_manager import ImageManager
from core.overlay_renderer import OverlayRenderer
from core.roi_handler import ROIHandler
from core.template_manager import TemplateManager
from vision.aruco_detection import ArucoDetector
from vision.color_detection import ColorDetector
from vision.rotation_detection import RotationDetector

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
        self.aruco_detector = ArucoDetector()
        self.rotation_detector = RotationDetector()
        self.overlay_renderer = OverlayRenderer()

    def template_match(
        self,
        image_id: str,
        template_id: str,
        method: str = "TM_CCOEFF_NORMED",
        threshold: float = 0.8,
        bounding_box: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
        """
        Perform template matching on an image.

        Args:
            image_id: Image identifier
            template_id: Template identifier
            method: OpenCV matching method
            threshold: Match threshold (0-1)
            bounding_box: Optional bounding box to limit search area (dict with x, y, width, height)
            record_history: Whether to record in history

        Returns:
            Tuple of (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
            TemplateNotFoundException: If template not found
        """
        from core.roi_handler import ROI, ROIHandler

        with timer() as t:
            # Get image
            full_image = self.image_manager.get(image_id)
            if full_image is None:
                raise ImageNotFoundException(image_id)

            # Extract ROI if bounding_box specified
            roi_offset = (0, 0)
            if bounding_box:
                roi = ROI(
                    x=bounding_box.get("x", 0),
                    y=bounding_box.get("y", 0),
                    width=bounding_box.get("width", full_image.shape[1]),
                    height=bounding_box.get("height", full_image.shape[0]),
                )
                image = ROIHandler.extract_roi(full_image, roi, safe_mode=True)
                roi_offset = (roi.x, roi.y)
            else:
                image = full_image

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
                x = loc[0] + roi_offset[0]
                y = loc[1] + roi_offset[1]
                w = template.shape[1]
                h = template.shape[0]

                detected_objects.append(
                    VisionObject(
                        object_id="match_0",
                        object_type=VisionObjectType.TEMPLATE_MATCH.value,
                        bounding_box=ROI(x=x, y=y, width=w, height=h),
                        center=Point(x=float(x + w // 2), y=float(y + h // 2)),
                        confidence=min(float(score), 1.0),
                        rotation=0.0,
                        properties={
                            "template_id": template_id,
                            "method": method,
                            "scale": 1.0,
                            "raw_score": float(score),
                        },
                    )
                )

            # Create result image with overlay on ROI area only
            # Render matches with local coordinates (before offset adjustment)
            if detected_objects:
                # Create temporary objects with local coordinates for rendering
                local_objects = []
                for obj in detected_objects:
                    local_obj = VisionObject(
                        object_id=obj.object_id,
                        object_type=obj.object_type,
                        bounding_box=ROI(
                            x=obj.bounding_box.x - roi_offset[0],
                            y=obj.bounding_box.y - roi_offset[1],
                            width=obj.bounding_box.width,
                            height=obj.bounding_box.height,
                        ),
                        center=Point(
                            x=obj.center.x - roi_offset[0], y=obj.center.y - roi_offset[1]
                        ),
                        confidence=obj.confidence,
                        properties=obj.properties,
                    )
                    local_objects.append(local_obj)
                result_image = self.overlay_renderer.render_template_matches(image, local_objects)
            else:
                result_image = image.copy()

            # Create thumbnail from ROI area (not full image)
            _, thumbnail_base64 = self.image_manager.create_thumbnail(result_image)

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
                processing_time_ms=t["ms"],
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(f"Template matching: {len(detected_objects)} matches in {t['ms']}ms")

        return detected_objects, thumbnail_base64, t["ms"]

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
        bounding_box: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[Dict, str, int]:
        """
        Perform edge detection on an image.

        Args:
            image_id: Image identifier
            method: Edge detection method (canny, sobel, laplacian, etc.)
            params: Method-specific parameters
            preprocessing: Optional preprocessing parameters
            bounding_box: Optional bounding box to limit detection area
                (dict with x, y, width, height)
            record_history: Whether to record in history

        Returns:
            Tuple of (result_dict, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        from core.roi_handler import ROI, ROIHandler
        from vision.edge_detection import EdgeDetector, EdgeMethod

        with timer() as t:
            # Get image
            full_image = self.image_manager.get(image_id)
            if full_image is None:
                raise ImageNotFoundException(image_id)

            # Extract ROI if bounding_box specified
            roi_offset = (0, 0)
            if bounding_box:
                roi = ROI(
                    x=bounding_box.get("x", 0),
                    y=bounding_box.get("y", 0),
                    width=bounding_box.get("width", full_image.shape[1]),
                    height=bounding_box.get("height", full_image.shape[0]),
                )
                image = ROIHandler.extract_roi(full_image, roi, safe_mode=True)
                roi_offset = (roi.x, roi.y)
            else:
                image = full_image

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

            # Adjust object coordinates if ROI was used
            if roi_offset != (0, 0):
                for obj in result["objects"]:
                    # Adjust bounding box
                    obj.bounding_box.x += roi_offset[0]
                    obj.bounding_box.y += roi_offset[1]
                    # Adjust center
                    obj.center.x += roi_offset[0]
                    obj.center.y += roi_offset[1]
                    # Adjust contour points if present
                    if hasattr(obj, "raw_contour") and obj.raw_contour:
                        obj.raw_contour = [
                            [x + roi_offset[0], y + roi_offset[1]] for x, y in obj.raw_contour
                        ]

            # Create result image with overlay - use ROI area only for thumbnail
            if result["visualization"] and "overlay" in result["visualization"]:
                import base64

                overlay_data = base64.b64decode(result["visualization"]["overlay"])
                nparr = np.frombuffer(overlay_data, np.uint8)
                result_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                result_image = image.copy()

            # Create thumbnail from ROI area (not full image)
            _, thumbnail_base64 = self.image_manager.create_thumbnail(result_image)

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
                processing_time_ms=t["ms"],
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Edge detection completed: {len(result['objects'])} contours found " f"in {t['ms']}ms"
        )

        return result, thumbnail_base64, t["ms"]

    def color_detect(
        self,
        image_id: str,
        roi: Optional[Dict[str, int]] = None,
        contour: Optional[list] = None,
        use_contour_mask: bool = True,
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
            contour: Optional contour points for masking
            use_contour_mask: Whether to use contour mask (if contour provided)
            expected_color: Expected color name (or None to just detect)
            min_percentage: Minimum percentage for color match
            method: Detection method ("histogram" or "kmeans")
            record_history: Whether to record in history

        Returns:
            Tuple of (detected_object, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        with timer() as t:
            # Get image
            image = self.image_manager.get(image_id)
            if image is None:
                raise ImageNotFoundException(image_id)

            # Perform color detection
            result = self.color_detector.detect(
                image=image,
                roi=roi,
                contour_points=contour,
                use_contour_mask=use_contour_mask,
                expected_color=expected_color,
                min_percentage=min_percentage,
                method=method,
            )

            # Create VisionObject
            detected_object = VisionObject(
                object_id="color_0",
                object_type=VisionObjectType.COLOR_REGION.value,
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
            result_image = self.overlay_renderer.render_color_detection(
                image, detected_object, expected_color, contour_points=contour
            )

            # Create thumbnail
            _, thumbnail_base64 = self.image_manager.create_thumbnail(result_image)

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
                processing_time_ms=t["ms"],
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Color detection completed: {result['dominant_color']} "
            f"({result['confidence']*100:.1f}%) in {t['ms']}ms"
        )

        return detected_object, thumbnail_base64, t["ms"]

    def aruco_detect(
        self,
        image_id: str,
        dictionary: str = "DICT_4X4_50",
        roi: Optional[ROI] = None,
        params: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
        """
        Detect ArUco markers in image.

        Args:
            image_id: ID of the image to process
            dictionary: ArUco dictionary type
            roi: Optional region of interest to search in
            params: Detection parameters
            record_history: Whether to record in history buffer

        Returns:
            (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        # Get image from manager
        image = self.image_manager.get(image_id)
        if image is None:
            raise ImageNotFoundException(image_id)

        # Extract ROI if specified
        image_to_process = image
        if roi:
            image_to_process = image[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]

        # Perform ArUco detection
        with timer() as t:
            result = self.aruco_detector.detect(
                image_to_process, dictionary=dictionary, params=params or {}
            )

        # Adjust coordinates if ROI was used
        if roi:
            for obj in result["objects"]:
                obj.center.x += roi.x
                obj.center.y += roi.y
                obj.bounding_box.x += roi.x
                obj.bounding_box.y += roi.y

        # Get visualization
        thumbnail_base64 = result["visualization"]["overlay"]

        # Record history if requested
        if record_history:
            from api.models import InspectionResult

            inspection_result = (
                InspectionResult.PASS if len(result["objects"]) > 0 else InspectionResult.FAIL
            )

            self.history_buffer.add_inspection(
                image_id=image_id,
                result=inspection_result,
                detections=[
                    {"type": "aruco_marker", "marker_id": obj.properties["marker_id"]}
                    for obj in result["objects"]
                ],
                processing_time_ms=t["ms"],
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(f"ArUco detection completed: {len(result['objects'])} markers in {t['ms']}ms")

        return result["objects"], thumbnail_base64, t["ms"]

    def rotation_detect(
        self,
        image_id: str,
        contour: List,
        method: str = "min_area_rect",
        angle_range: str = "0_360",
        roi: Optional[Dict[str, int]] = None,
        record_history: bool = True,
    ) -> Tuple[VisionObject, str, int]:
        """
        Detect rotation angle from contour.

        Args:
            image_id: ID of the image (for visualization)
            contour: Contour points [[x1,y1], [x2,y2], ...]
            method: Detection method (min_area_rect, ellipse_fit, pca)
            angle_range: Output angle range (0_360, -180_180, 0_180)
            roi: Optional ROI for visualization context
            record_history: Whether to record in history buffer

        Returns:
            (detected_object, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        # Get image from manager
        image = self.image_manager.get(image_id)
        if image is None:
            raise ImageNotFoundException(image_id)

        # Import enums
        from vision.rotation_detection import AngleRange, RotationMethod

        # Convert string to enum
        try:
            method_enum = RotationMethod(method)
        except ValueError:
            method_enum = RotationMethod.MIN_AREA_RECT

        try:
            range_enum = AngleRange(angle_range)
        except ValueError:
            range_enum = AngleRange.RANGE_0_360

        # Perform rotation detection
        with timer() as t:
            result = self.rotation_detector.detect(
                image, contour=contour, method=method_enum, angle_range=range_enum, roi=roi
            )

        # Get single object
        detected_object = result["objects"][0]

        # Get visualization and create thumbnail
        import base64

        overlay_data = base64.b64decode(result["visualization"]["overlay"])
        nparr = np.frombuffer(overlay_data, np.uint8)
        overlay_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Create thumbnail from overlay
        _, thumbnail_base64 = self.image_manager.create_thumbnail(overlay_image)

        # Record history if requested
        if record_history:
            from api.models import InspectionResult

            self.history_buffer.add_inspection(
                image_id=image_id,
                result=InspectionResult.PASS,  # Rotation always succeeds if contour valid
                detections=[
                    {
                        "type": "rotation_analysis",
                        "rotation": detected_object.rotation,
                        "method": method,
                        "confidence": detected_object.confidence,
                    }
                ],
                processing_time_ms=t["ms"],
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Rotation detection completed: {detected_object.rotation:.1f}° "
            f"({method}) in {t['ms']}ms"
        )

        return detected_object, thumbnail_base64, t["ms"]
