"""
Image processing operations.

Handles image manipulation tasks:
- Thumbnail creation
- Resizing
"""

import logging
from typing import Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from core.image.converters import numpy_to_pil, pil_to_numpy, to_base64

logger = logging.getLogger(__name__)


def create_thumbnail(
    image: Union[np.ndarray, Image.Image], width: int = 320, maintain_aspect: bool = True
) -> Tuple[np.ndarray, str]:
    """
    Create thumbnail from image.

    Args:
        image: Input image (NumPy array or PIL Image)
        width: Target width in pixels
        maintain_aspect: If True, maintain aspect ratio

    Returns:
        Tuple of (thumbnail as NumPy array, thumbnail as base64 string)
    """
    try:
        # Convert to PIL if needed
        if isinstance(image, np.ndarray):
            pil_image = numpy_to_pil(image)
        else:
            pil_image = image.copy()

        # Calculate new size
        if maintain_aspect:
            aspect_ratio = pil_image.height / pil_image.width
            height = int(width * aspect_ratio)
        else:
            height = width

        # Resize image
        pil_image.thumbnail((width, height), Image.Resampling.LANCZOS)

        # Convert to numpy array
        thumb_array = pil_to_numpy(pil_image)

        # Convert to base64
        thumb_base64 = to_base64(pil_image, format="JPEG", quality=70)

        return thumb_array, thumb_base64

    except Exception as e:
        logger.error(f"Failed to create thumbnail: {e}")
        raise


def resize_image(
    image: np.ndarray,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_dimension: Optional[int] = None,
) -> np.ndarray:
    """
    Resize image with various options.

    Args:
        image: Input image as NumPy array
        width: Target width (if height not specified, maintains aspect)
        height: Target height (if width not specified, maintains aspect)
        max_dimension: Maximum dimension (width or height)

    Returns:
        Resized image as NumPy array
    """
    h, w = image.shape[:2]

    if max_dimension:
        # Scale to fit within max_dimension
        scale = min(max_dimension / w, max_dimension / h)
        if scale < 1:
            width = int(w * scale)
            height = int(h * scale)
        else:
            return image

    elif width and not height:
        # Scale by width, maintain aspect
        height = int(h * width / w)

    elif height and not width:
        # Scale by height, maintain aspect
        width = int(w * height / h)

    elif not width and not height:
        return image

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
