"""
Template matching algorithms for machine vision.

Provides template matching using OpenCV with multiple correlation methods.
"""

import logging
from typing import Any, Dict

import cv2
import numpy as np
from pydantic import BaseModel, Field

from core.enums import TemplateMethod


class TemplateMatchParams(BaseModel):
    """
    Template matching parameters.

    Supports multiple OpenCV matching methods with configurable thresholds.
    """

    class Config:
        extra = "forbid"

    def to_dict(self) -> Dict[str, Any]:
        """Export to dict for detector functions."""
        data = self.model_dump(exclude_none=True)
        # Convert enum to string for OpenCV
        if "method" in data and hasattr(data["method"], "value"):
            data["method"] = data["method"].value
        return data

    template_id: str = Field(description="Template identifier to match against")
    method: TemplateMethod = Field(
        default=TemplateMethod.TM_CCOEFF_NORMED, description="OpenCV template matching method"
    )
    threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Match confidence threshold (0.0 to 1.0)",
    )
    multi_scale: bool = Field(default=False, description="Enable multi-scale template matching")
    scale_range: list = Field(
        default=[0.8, 1.2], description="Scale range for multi-scale matching [min, max]"
    )
    scale_steps: int = Field(
        default=5, ge=2, le=20, description="Number of scale steps for multi-scale matching"
    )


class TemplateDetector:
    """Template matching processor using OpenCV methods."""

    def __init__(self):
        """Initialize template detector."""
        from core.overlay_renderer import OverlayRenderer

        self.logger = logging.getLogger(__name__)
        self.overlay_renderer = OverlayRenderer()

    def detect(
        self,
        image: np.ndarray,
        template: np.ndarray,
        template_id: str,
        params: Dict[str, Any],
    ) -> Dict:
        """
        Perform template matching on image.

        Args:
            image: Input image (BGR format)
            template: Template image to search for
            template_id: Template identifier for metadata
            params: Detection parameters dict

        Returns:
            Dictionary with detection results
        """
        from schemas import ROI, Point, VisionObject, VisionObjectType

        # Extract params
        method = params.get("method", "TM_CCOEFF_NORMED")
        threshold = params.get("threshold", 0.8)

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

        # Create VisionObject if match found
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
            result_image = self.overlay_renderer.render_template_matches(image, detected_objects)
        else:
            result_image = image.copy()

        return {
            "success": True,
            "objects": detected_objects,
            "image": result_image,
        }
