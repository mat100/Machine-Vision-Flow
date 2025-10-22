"""
Vision API Router - Vision processing endpoints
"""

import logging
import time
from fastapi import APIRouter, HTTPException, Request, Depends
import cv2
import numpy as np

from api.models import (
    TemplateMatchRequest,
    TemplateMatchResponse,
    TemplateMatchResult,
    EdgeDetectRequest,
    BlobDetectRequest,
    Point,
    BoundingBox
)
from vision.edge_detection import EdgeDetector, EdgeMethod

logger = logging.getLogger(__name__)

router = APIRouter()


def get_managers(request: Request):
    """Get managers from app state"""
    return {
        'image_manager': request.app.state.image_manager(),
        'template_manager': request.app.state.template_manager(),
        'history_buffer': request.app.state.history_buffer(),
        'config': request.app.state.config
    }


@router.post("/template-match")
async def template_match(
    request: TemplateMatchRequest,
    managers=Depends(get_managers)
) -> TemplateMatchResponse:
    """Perform template matching"""
    try:
        start_time = time.time()

        image_manager = managers['image_manager']
        template_manager = managers['template_manager']
        config = managers['config']

        # Get image
        image = image_manager.get(request.image_id)
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")

        # Get template
        template = template_manager.get_template(request.template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")

        # Apply ROI if specified
        if request.roi:
            x = request.roi.x
            y = request.roi.y
            w = request.roi.width
            h = request.roi.height
            search_image = image[y:y+h, x:x+w].copy()
            roi_offset = (x, y)
        else:
            search_image = image
            roi_offset = (0, 0)

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
        method = getattr(cv2, request.method.value)
        result = cv2.matchTemplate(search_gray, template_gray, method)

        # Find matches above threshold
        matches = []
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # For SQDIFF methods, lower is better
        if request.method.value in ['TM_SQDIFF', 'TM_SQDIFF_NORMED']:
            if min_val <= (1 - request.threshold):
                score = 1 - min_val  # Convert to 0-1 where 1 is best
                loc = min_loc
            else:
                score = 0
                loc = None
        else:
            if max_val >= request.threshold:
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
                    position=Point(x=float(x + template.shape[1]//2),
                                 y=float(y + template.shape[0]//2)),
                    score=float(score),
                    scale=1.0,
                    rotation=0.0,
                    bounding_box=BoundingBox(
                        top_left=Point(x=float(x), y=float(y)),
                        bottom_right=Point(x=float(x + template.shape[1]),
                                         y=float(y + template.shape[0]))
                    )
                )
            )

        # Create result image with overlay
        result_image = image.copy()
        for match in matches:
            pt1 = (int(match.bounding_box.top_left.x),
                  int(match.bounding_box.top_left.y))
            pt2 = (int(match.bounding_box.bottom_right.x),
                  int(match.bounding_box.bottom_right.y))
            cv2.rectangle(result_image, pt1, pt2, (0, 255, 0), 2)

            # Add score text
            cv2.putText(result_image, f"{match.score:.2f}",
                       (pt1[0], pt1[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Create thumbnail
        _, thumbnail_base64 = image_manager.create_thumbnail(
            result_image,
            config['image_buffer']['thumbnail_width']
        )

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Add to history
        history_buffer = managers['history_buffer']
        history_buffer.add_inspection(
            image_id=request.image_id,
            result="PASS" if matches else "FAIL",
            detections=[{
                'type': 'template_match',
                'template_id': request.template_id,
                'found': len(matches) > 0,
                'score': matches[0].score if matches else 0,
                'count': len(matches)
            }],
            processing_time_ms=processing_time,
            thumbnail_base64=thumbnail_base64
        )

        return TemplateMatchResponse(
            success=True,
            found=len(matches) > 0,
            matches=matches,
            processing_time_ms=processing_time,
            thumbnail_base64=thumbnail_base64
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template matching failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edge-detect")
async def edge_detect(
    request: EdgeDetectRequest,
    managers=Depends(get_managers)
) -> dict:
    """Perform edge detection with multiple methods"""
    try:
        start_time = time.time()

        image_manager = managers['image_manager']
        config = managers['config']
        history_buffer = managers['history_buffer']

        # Get image
        image = image_manager.get(request.image_id)
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")

        # Initialize edge detector
        detector = EdgeDetector()

        # Prepare ROI if specified
        roi = None
        if request.roi:
            roi = {
                'x': request.roi.x,
                'y': request.roi.y,
                'width': request.roi.width,
                'height': request.roi.height
            }

        # Prepare parameters
        params = request.params if hasattr(request, 'params') and request.params else {}

        # Set default parameters based on method
        method = EdgeMethod(request.method.lower()) if hasattr(request, 'method') else EdgeMethod.CANNY

        if method == EdgeMethod.CANNY:
            params.setdefault('canny_low', request.threshold1 if hasattr(request, 'threshold1') else 50)
            params.setdefault('canny_high', request.threshold2 if hasattr(request, 'threshold2') else 150)
        elif method == EdgeMethod.SOBEL:
            params.setdefault('sobel_threshold', 50)
        elif method == EdgeMethod.LAPLACIAN:
            params.setdefault('laplacian_threshold', 30)

        # Prepare preprocessing options
        preprocessing = request.preprocessing if hasattr(request, 'preprocessing') else None

        # Perform edge detection
        result = detector.detect(
            image=image,
            method=method,
            params=params,
            roi=roi,
            preprocessing=preprocessing
        )

        # Create result image with overlay
        if result['visualization'] and 'overlay' in result['visualization']:
            import base64
            overlay_data = base64.b64decode(result['visualization']['overlay'])
            nparr = np.frombuffer(overlay_data, np.uint8)
            result_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            result_image = image.copy()

        # Create thumbnail
        _, thumbnail_base64 = image_manager.create_thumbnail(
            result_image,
            config['image_buffer']['thumbnail_width']
        )

        processing_time = int((time.time() - start_time) * 1000)

        # Add to history
        history_buffer.add_inspection(
            image_id=request.image_id,
            result="PASS" if result['edges_found'] else "FAIL",
            detections=[{
                'type': 'edge_detection',
                'method': method.value,
                'found': result['edges_found'],
                'contour_count': result['contour_count'],
                'edge_ratio': result['edge_ratio']
            }],
            processing_time_ms=processing_time,
            thumbnail_base64=thumbnail_base64
        )

        return {
            "success": result['success'],
            "edges_found": result['edges_found'],
            "contour_count": result['contour_count'],
            "contours": result['contours'][:10],  # Limit to first 10 for response size
            "edge_pixels": result['edge_pixels'],
            "edge_ratio": result['edge_ratio'],
            "processing_time_ms": processing_time,
            "thumbnail_base64": thumbnail_base64,
            "visualization": result['visualization'] if params.get('include_visualization', False) else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edge detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blob-detect")
async def blob_detect(
    request: BlobDetectRequest,
    managers=Depends(get_managers)
) -> dict:
    """Perform blob detection"""
    # Placeholder implementation
    return {
        "success": True,
        "blob_count": 0,
        "blobs": [],
        "processing_time_ms": 0,
        "message": "Blob detection not yet implemented"
    }