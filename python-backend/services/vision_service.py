"""
Vision Service - Business logic for vision processing operations.

This service orchestrates vision processing operations including
template matching, edge detection, and other computer vision tasks.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union

import cv2

from api.exceptions import ImageNotFoundException, TemplateNotFoundException
from api.models import (
    ROI,
    AngleRange,
    ArucoDict,
    ColorMethod,
    Point,
    RotationMethod,
    VisionObject,
    VisionObjectType,
)
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

    def _execute_detection(
        self,
        image_id: str,
        detector_func,
        roi: Optional[Dict] = None,
        record_history: bool = True,
        history_type: str = "detection",
        **detector_kwargs,
    ) -> Tuple[any, str, int]:
        """
        Template method for vision detection operations.

        This method encapsulates common logic:
        - Image retrieval
        - ROI extraction
        - Coordinate adjustment
        - Thumbnail generation
        - History recording

        Args:
            image_id: Image identifier
            detector_func: Detection function to execute
                (receives image, returns result dict/objects)
            roi: Optional region of interest
            record_history: Whether to record in history
            history_type: Type of detection for history logging
            **detector_kwargs: Additional kwargs passed to detector function

        Returns:
            Tuple of (detection_result, thumbnail_base64, processing_time_ms)
        """
        with timer() as t:
            # Get image
            full_image = self.image_manager.get(image_id)
            if full_image is None:
                raise ImageNotFoundException(image_id)

            # Extract ROI if specified
            roi_offset = (0, 0)
            if roi:
                roi_obj = ROI.from_dict(roi) if isinstance(roi, dict) else roi
                image = ROIHandler.extract_roi(full_image, roi_obj, safe_mode=True)
                roi_offset = (roi_obj.x, roi_obj.y)
            else:
                image = full_image

            # Execute detection
            result = detector_func(image, **detector_kwargs)

            # Adjust coordinates if ROI was used
            if roi_offset != (0, 0):
                result = self._adjust_coordinates_for_roi(result, roi_offset)

            # Generate thumbnail
            thumbnail_base64 = self._create_detection_thumbnail(result, image)

        # Read processing time AFTER with block (timer updates in finally)
        processing_time_ms = t["ms"]

        # Record history if requested
        if record_history:
            self._record_detection_history(
                image_id, result, history_type, processing_time_ms, thumbnail_base64
            )

        return result, thumbnail_base64, processing_time_ms

    def _adjust_coordinates_for_roi(self, result, roi_offset):
        """Adjust object coordinates by ROI offset."""
        # Handle different result types
        if isinstance(result, dict) and "objects" in result:
            # Result with objects list
            for obj in result["objects"]:
                self._adjust_object_coordinates(obj, roi_offset)
            return result
        elif isinstance(result, list):
            # Direct list of objects
            for obj in result:
                self._adjust_object_coordinates(obj, roi_offset)
            return result
        elif isinstance(result, VisionObject):
            # Single object
            self._adjust_object_coordinates(result, roi_offset)
            return result
        else:
            # Unknown format, return as-is
            return result

    def _adjust_object_coordinates(self, obj: VisionObject, roi_offset: Tuple[int, int]):
        """Adjust single object coordinates by ROI offset."""
        obj.bounding_box.x += roi_offset[0]
        obj.bounding_box.y += roi_offset[1]
        obj.center.x += roi_offset[0]
        obj.center.y += roi_offset[1]

        # Adjust contour points if present
        if hasattr(obj, "contour") and obj.contour:
            obj.contour = [[x + roi_offset[0], y + roi_offset[1]] for x, y in obj.contour]

    def _create_detection_thumbnail(self, result, processed_image) -> str:
        """Create thumbnail from detection result."""
        # Check if result has annotated image
        if isinstance(result, dict) and "image" in result:
            _, thumbnail_base64 = self.image_manager.create_thumbnail(result["image"])
            return thumbnail_base64

        # Fallback: use processed image
        _, thumbnail_base64 = self.image_manager.create_thumbnail(processed_image)
        return thumbnail_base64

    def _record_detection_history(
        self, image_id: str, result, detection_type: str, processing_time_ms: int, thumbnail: str
    ):
        """Record detection in history buffer."""
        # Determine object count
        if isinstance(result, dict) and "objects" in result:
            object_count = len(result["objects"])
        elif isinstance(result, list):
            object_count = len(result)
        elif isinstance(result, VisionObject):
            object_count = 1
        else:
            object_count = 0

        self.history_buffer.add_inspection(
            image_id=image_id,
            result="PASS" if object_count > 0 else "FAIL",
            detections=[
                {
                    "type": detection_type,
                    "found": object_count > 0,
                    "count": object_count,
                }
            ],
            processing_time_ms=processing_time_ms,
            thumbnail_base64=thumbnail,
        )

    def template_match(
        self,
        image_id: str,
        template_id: str,
        method: str = "TM_CCOEFF_NORMED",
        threshold: float = 0.8,
        roi: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
        """
        Perform template matching on an image.

        Args:
            image_id: Image identifier
            template_id: Template identifier
            method: OpenCV matching method
            threshold: Match threshold (0-1)
            roi: Optional region of interest to limit search area (dict with x, y, width, height)
            record_history: Whether to record in history

        Returns:
            Tuple of (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
            TemplateNotFoundException: If template not found
        """
        # Get template first (before detector function)
        template = self.template_manager.get_template(template_id)
        if template is None:
            raise TemplateNotFoundException(template_id)

        # Create detector function that performs template matching
        def detect_func(image):
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

            # Create DetectedObject if match found (with local coordinates)
            if loc is not None:
                x = loc[0]
                y = loc[1]
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

            # Create visualization
            if detected_objects:
                result_image = self.overlay_renderer.render_template_matches(
                    image, detected_objects
                )
            else:
                result_image = image.copy()

            # Return result in format expected by _execute_detection
            return {
                "objects": detected_objects,
                "visualization": {"has_overlay": True, "image": result_image},
            }

        # Execute using template method - it handles ROI, coordinate adjustment, thumbnail, history
        result, thumbnail_base64, processing_time = self._execute_detection(
            image_id=image_id,
            detector_func=detect_func,
            roi=roi,
            record_history=False,  # We'll do custom history recording
            history_type="template_match",
        )

        detected_objects = result["objects"]

        # Custom history recording for template match (includes template_id and confidence)
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

        logger.debug(f"Template matching: {len(detected_objects)} matches in {processing_time}ms")

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
        roi: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
        """
        Perform edge detection on an image.

        Args:
            image_id: Image identifier
            method: Edge detection method (canny, sobel, laplacian, etc.)
            params: Method-specific parameters
            preprocessing: Optional preprocessing parameters
            roi: Optional region of interest to limit detection area
            record_history: Whether to record in history

        Returns:
            Tuple of (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        from core.constants import EdgeDetectionDefaults
        from core.enums import EdgeMethod
        from vision.edge_detection import EdgeDetector

        # Parse method
        try:
            edge_method = EdgeMethod(method.lower())
        except ValueError:
            edge_method = EdgeMethod.CANNY

        # Set default parameters if not provided
        if params is None:
            params = {}

        # Set method-specific defaults using constants
        if edge_method == EdgeMethod.CANNY:
            params.setdefault("canny_low", EdgeDetectionDefaults.CANNY_LOW_THRESHOLD)
            params.setdefault("canny_high", EdgeDetectionDefaults.CANNY_HIGH_THRESHOLD)
        elif edge_method == EdgeMethod.SOBEL:
            params.setdefault("sobel_threshold", EdgeDetectionDefaults.SOBEL_THRESHOLD)
        elif edge_method == EdgeMethod.LAPLACIAN:
            params.setdefault("laplacian_threshold", EdgeDetectionDefaults.LAPLACIAN_THRESHOLD)

        # Create detector function
        def detect_func(image):
            detector = EdgeDetector()
            return detector.detect(
                image=image, method=edge_method, params=params, preprocessing=preprocessing
            )

        # Execute using template method
        result, thumbnail_base64, processing_time = self._execute_detection(
            image_id=image_id,
            detector_func=detect_func,
            roi=roi,
            record_history=record_history,
            history_type="edge_detection",
        )

        logger.debug(
            f"Edge detection completed: {len(result['objects'])} contours "
            f"found in {processing_time}ms"
        )

        # Return List[VisionObject] directly (not Dict) for consistency
        return result["objects"], thumbnail_base64, processing_time

    def color_detect(
        self,
        image_id: str,
        roi: Optional[Dict[str, int]] = None,
        contour: Optional[list] = None,
        use_contour_mask: bool = True,
        expected_color: Optional[str] = None,
        min_percentage: float = 50.0,
        method: Union[ColorMethod, str] = ColorMethod.HISTOGRAM,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
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
            Tuple of (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """

        # Create detector function
        def detect_func(image):
            # Convert ColorMethod enum to string if needed
            method_str = method.value if isinstance(method, ColorMethod) else method
            return self.color_detector.detect(
                image=image,
                roi=roi,
                contour_points=contour,
                use_contour_mask=use_contour_mask,
                expected_color=expected_color,
                min_percentage=min_percentage,
                method=method_str,
            )

        # Execute using template method (handles image retrieval, thumbnail, timing)
        result, thumbnail_base64, processing_time = self._execute_detection(
            image_id=image_id,
            detector_func=detect_func,
            roi=None,  # ColorDetector handles ROI internally
            record_history=False,  # Custom history recording below
            history_type="color_detection",
        )

        detected_object = result["objects"][0]

        # Custom history recording (PASS/FAIL based on match OR no expected color)
        if record_history:
            is_match = detected_object.properties.get("match", False)
            inspection_result = "PASS" if (is_match or expected_color is None) else "FAIL"
            self.history_buffer.add_inspection(
                image_id=image_id,
                result=inspection_result,
                detections=[
                    {
                        "type": "color_detection",
                        "dominant_color": detected_object.properties["dominant_color"],
                        "expected_color": expected_color,
                        "match": is_match,
                        "confidence": detected_object.confidence,
                    }
                ],
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Color detection completed: {detected_object.properties['dominant_color']} "
            f"({detected_object.confidence*100:.1f}%) in {processing_time}ms"
        )

        return [detected_object], thumbnail_base64, processing_time

    def aruco_detect(
        self,
        image_id: str,
        dictionary: Union[ArucoDict, str] = ArucoDict.DICT_4X4_50,
        roi: Optional[Dict] = None,
        params: Optional[Dict] = None,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
        """
        Detect ArUco markers in image.

        Args:
            image_id: ID of the image to process
            dictionary: ArUco dictionary type
            roi: Optional region of interest to search in (dict with x, y, width, height)
            params: Detection parameters
            record_history: Whether to record in history buffer

        Returns:
            (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        from core.constants import ArucoDetectionDefaults

        # Set default dictionary
        if dictionary is None:
            dictionary = ArucoDetectionDefaults.DEFAULT_DICTIONARY

        # Convert ArucoDict enum to string if needed
        dictionary_str = dictionary.value if isinstance(dictionary, ArucoDict) else dictionary

        # Create detector function
        def detect_func(image):
            return self.aruco_detector.detect(image, dictionary=dictionary_str, params=params or {})

        # Execute using template method
        result, thumbnail_base64, processing_time = self._execute_detection(
            image_id=image_id,
            detector_func=detect_func,
            roi=roi,
            record_history=record_history,
            history_type="aruco_detection",
        )

        logger.debug(
            f"ArUco detection completed: {len(result['objects'])} markers "
            f"in {processing_time}ms"
        )

        return result["objects"], thumbnail_base64, processing_time

    def rotation_detect(
        self,
        image_id: str,
        contour: List,
        method: Union[RotationMethod, str] = RotationMethod.MIN_AREA_RECT,
        angle_range: Union[AngleRange, str] = AngleRange.RANGE_0_360,
        roi: Optional[Dict[str, int]] = None,
        record_history: bool = True,
    ) -> Tuple[List[VisionObject], str, int]:
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
            (detected_objects, thumbnail_base64, processing_time_ms)

        Raises:
            ImageNotFoundException: If image not found
        """
        # Convert string to enum if needed (API provides enums, but backwards compatibility)
        if isinstance(method, str):
            try:
                method_enum = RotationMethod(method)
            except ValueError:
                method_enum = RotationMethod.MIN_AREA_RECT
        else:
            method_enum = method

        if isinstance(angle_range, str):
            try:
                range_enum = AngleRange(angle_range)
            except ValueError:
                range_enum = AngleRange.RANGE_0_360
        else:
            range_enum = angle_range

        # Create detector function
        def detect_func(image):
            return self.rotation_detector.detect(
                image, contour=contour, method=method_enum, angle_range=range_enum, roi=roi
            )

        # Execute using template method (handles image retrieval, thumbnail, timing)
        result, thumbnail_base64, processing_time = self._execute_detection(
            image_id=image_id,
            detector_func=detect_func,
            roi=None,  # RotationDetector handles ROI for visualization
            record_history=False,  # Custom history recording below
            history_type="rotation_analysis",
        )

        detected_object = result["objects"][0]

        # Custom history recording (rotation always succeeds if contour valid)
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
                processing_time_ms=processing_time,
                thumbnail_base64=thumbnail_base64,
            )

        logger.debug(
            f"Rotation detection completed: {detected_object.rotation:.1f}° "
            f"({method}) in {processing_time}ms"
        )

        return [detected_object], thumbnail_base64, processing_time
