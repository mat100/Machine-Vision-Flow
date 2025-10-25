"""
Shared FastAPI dependencies for the Machine Vision Flow system.
Centralizes common dependencies to eliminate code duplication.
"""

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.models import ROI
from core.camera_manager import CameraManager
from core.history_buffer import HistoryBuffer
from core.image_manager import ImageManager
from core.template_manager import TemplateManager

# Import services
from services.camera_service import CameraService
from services.image_service import ImageService
from services.vision_service import VisionService

logger = logging.getLogger(__name__)

# Optional security bearer for future use
security = HTTPBearer(auto_error=False)


class Managers:
    """Container for all manager instances."""

    def __init__(
        self,
        image_manager: ImageManager,
        camera_manager: CameraManager,
        template_manager: TemplateManager,
        history_buffer: HistoryBuffer,
    ):
        self.image_manager = image_manager
        self.camera_manager = camera_manager
        self.template_manager = template_manager
        self.history_buffer = history_buffer


def get_managers(request: Request) -> Managers:
    """
    Get all manager instances from app state.

    Args:
        request: FastAPI request object

    Returns:
        Managers container with all manager instances

    Raises:
        HTTPException: If managers not initialized
    """
    try:
        return Managers(
            image_manager=request.app.state.image_manager,
            camera_manager=request.app.state.camera_manager,
            template_manager=request.app.state.template_manager,
            history_buffer=request.app.state.history_buffer,
        )
    except AttributeError as e:
        logger.error(f"Managers not initialized in app state: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error: Managers not initialized"
        )


def get_image_manager(managers: Managers = Depends(get_managers)) -> ImageManager:
    """Get ImageManager instance."""
    return managers.image_manager


def get_camera_manager(managers: Managers = Depends(get_managers)) -> CameraManager:
    """Get CameraManager instance."""
    return managers.camera_manager


def get_template_manager(managers: Managers = Depends(get_managers)) -> TemplateManager:
    """Get TemplateManager instance."""
    return managers.template_manager


def get_history_buffer(managers: Managers = Depends(get_managers)) -> HistoryBuffer:
    """Get HistoryBuffer instance."""
    return managers.history_buffer


# Common query parameters
def common_pagination(
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
) -> Dict[str, int]:
    """Common pagination parameters."""
    return {"offset": offset, "limit": limit}


def image_id_param(image_id: str = Path(..., description="Unique image identifier")) -> str:
    """Common image ID path parameter."""
    return image_id


def camera_id_param(camera_id: str = Query("test", description="Camera identifier")) -> str:
    """Common camera ID query parameter."""
    return camera_id


def optional_roi_params(
    x: Optional[int] = Query(None, ge=0, description="ROI x coordinate"),
    y: Optional[int] = Query(None, ge=0, description="ROI y coordinate"),
    width: Optional[int] = Query(None, ge=1, description="ROI width"),
    height: Optional[int] = Query(None, ge=1, description="ROI height"),
) -> Optional[Dict[str, int]]:
    """Optional ROI query parameters."""
    if all(v is not None for v in [x, y, width, height]):
        return {"x": x, "y": y, "width": width, "height": height}
    elif any(v is not None for v in [x, y, width, height]):
        # Partial ROI parameters - invalid
        raise HTTPException(
            status_code=400, detail="ROI requires all parameters (x, y, width, height) or none"
        )
    return None


def validate_template_exists(
    template_id: str = Path(..., description="Template identifier"),
    template_manager: TemplateManager = Depends(get_template_manager),
) -> str:
    """
    Validate that template exists.

    Args:
        template_id: Template identifier
        template_manager: TemplateManager instance

    Returns:
        Validated template_id

    Raises:
        HTTPException: If template not found
    """
    templates = template_manager.list_templates()
    if not any(t["id"] == template_id for t in templates):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template_id


def validate_image_exists(
    image_id: str,
    image_manager: ImageManager,
) -> str:
    """
    Validate that image exists in shared memory.

    Args:
        image_id: Image identifier
        image_manager: ImageManager instance

    Returns:
        Validated image_id

    Raises:
        HTTPException: If image not found
    """
    # ImageManager.get() returns None if image doesn't exist
    if image_manager.get(image_id) is None:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found in cache")
    return image_id


def validate_roi_bounds(
    roi: ROI,
    image_id: str,
    image_manager: ImageManager,
) -> ROI:
    """
    Validate that ROI fits within image bounds.

    Args:
        roi: ROI to validate
        image_id: Image identifier
        image_manager: ImageManager instance

    Returns:
        Validated ROI

    Raises:
        HTTPException: If ROI exceeds image bounds or image not found
    """
    # Get image to check dimensions
    image_data = image_manager.get(image_id)
    if image_data is None:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

    img_height, img_width = image_data.shape[:2]

    # Validate ROI against image dimensions
    if not roi.is_valid(img_width, img_height):
        raise HTTPException(
            status_code=400,
            detail=f"ROI {roi.to_dict()} exceeds image bounds ({img_width}x{img_height})",
        )

    return roi


def roi_to_dict(roi: Optional[ROI]) -> Optional[Dict[str, int]]:
    """
    Convert Pydantic ROI model to dict for service layer compatibility.

    This helper eliminates the repeated manual dict construction pattern
    found throughout the vision routers.

    Args:
        roi: Optional ROI model

    Returns:
        ROI as dict or None if roi is None
    """
    if roi is None:
        return None
    return roi.to_dict()


def validate_vision_request(
    image_id: str,
    roi: Optional[ROI],
    image_manager: ImageManager,
    convert_roi_to_dict: bool = True,
):
    """
    Unified validation for vision detection endpoints.

    Eliminates the repeated pattern of:
    - validate_image_exists()
    - validate_roi_bounds()
    - roi_to_dict()

    Args:
        image_id: Image identifier to validate
        roi: Optional ROI to validate
        image_manager: ImageManager instance
        convert_roi_to_dict: If True, returns dict; if False, returns ROI model

    Returns:
        ROI as dict or ROI model (based on convert_roi_to_dict), or None if roi is None

    Raises:
        HTTPException: If image not found or ROI invalid
    """
    # Validate image exists
    validate_image_exists(image_id, image_manager)

    # Validate ROI if provided
    if roi:
        validate_roi_bounds(roi, image_id, image_manager)

    # Convert ROI to dict or return as-is
    if convert_roi_to_dict:
        return roi_to_dict(roi)
    else:
        return roi


# Authentication dependency (placeholder for future implementation)
def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Optional authentication check.

    Returns:
        User ID if authenticated, None otherwise
    """
    if credentials:
        # TODO: Implement actual authentication logic
        # For now, just return the token as user_id
        return credentials.credentials
    return None


# Rate limiting dependency (placeholder)
def check_rate_limit(
    user_id: Optional[str] = Depends(optional_auth), request: Request = None
) -> None:
    """
    Check rate limits for the request.

    Args:
        user_id: Optional authenticated user ID
        request: FastAPI request object

    Raises:
        HTTPException: If rate limit exceeded
    """
    # TODO: Implement actual rate limiting
    # Could use Redis or in-memory store to track request counts


# Configuration access
@lru_cache()
def get_config(request: Request) -> Dict[str, Any]:
    """
    Get application configuration.

    Args:
        request: FastAPI request object

    Returns:
        Configuration dictionary
    """
    try:
        return request.app.state.config
    except AttributeError:
        logger.warning("Config not found in app state, using defaults")
        return {}


# Error response helper
def error_response(status_code: int, message: str, details: Optional[Dict] = None) -> HTTPException:
    """
    Create standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message
        details: Optional additional details

    Returns:
        HTTPException with structured error
    """
    content = {"error": message}
    if details:
        content["details"] = details

    return HTTPException(status_code=status_code, detail=content)


# Service layer dependencies
def get_camera_service(
    camera_manager: CameraManager = Depends(get_camera_manager),
    image_manager: ImageManager = Depends(get_image_manager),
) -> CameraService:
    """
    Get camera service instance.

    Args:
        camera_manager: Camera manager dependency
        image_manager: Image manager dependency

    Returns:
        CameraService instance
    """
    return CameraService(camera_manager=camera_manager, image_manager=image_manager)


def get_image_service(image_manager: ImageManager = Depends(get_image_manager)) -> ImageService:
    """
    Get image service instance.

    Args:
        image_manager: Image manager dependency

    Returns:
        ImageService instance
    """
    return ImageService(image_manager=image_manager)


def get_vision_service(
    image_manager: ImageManager = Depends(get_image_manager),
    template_manager: TemplateManager = Depends(get_template_manager),
    history_buffer: HistoryBuffer = Depends(get_history_buffer),
) -> VisionService:
    """
    Get vision service instance.

    Args:
        image_manager: Image manager dependency
        template_manager: Template manager dependency
        history_buffer: History buffer dependency

    Returns:
        VisionService instance
    """
    return VisionService(
        image_manager=image_manager,
        template_manager=template_manager,
        history_buffer=history_buffer,
    )
