"""
Image processing utilities for the Machine Vision Flow system.
Centralizes common image operations to eliminate code duplication.
"""

import base64
import io
import logging
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)


class ImageUtils:
    """Utility class for common image processing operations."""

    @staticmethod
    def numpy_to_pil(image: np.ndarray) -> Image.Image:
        """
        Convert NumPy array (OpenCV format) to PIL Image.

        Args:
            image: NumPy array in BGR format (OpenCV)

        Returns:
            PIL Image in RGB format
        """
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        return Image.fromarray(image_rgb)

    @staticmethod
    def pil_to_numpy(image: Image.Image, bgr: bool = True) -> np.ndarray:
        """
        Convert PIL Image to NumPy array.

        Args:
            image: PIL Image
            bgr: If True, convert to BGR format (OpenCV), else keep RGB

        Returns:
            NumPy array
        """
        array = np.array(image)

        # Convert RGB to BGR if needed
        if bgr and len(array.shape) == 3 and array.shape[2] == 3:
            array = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)

        return array

    @staticmethod
    def to_base64(
        image: Union[np.ndarray, Image.Image, bytes],
        format: str = 'JPEG',
        quality: int = 85
    ) -> str:
        """
        Convert image to base64 string.

        Args:
            image: Input image (NumPy array, PIL Image, or raw bytes)
            format: Image format (JPEG, PNG, etc.)
            quality: JPEG quality (1-100, ignored for PNG)

        Returns:
            Base64 encoded string
        """
        try:
            # If already bytes, directly encode
            if isinstance(image, bytes):
                return base64.b64encode(image).decode('utf-8')

            # Convert numpy to PIL if needed
            if isinstance(image, np.ndarray):
                image = ImageUtils.numpy_to_pil(image)

            # Convert PIL Image to bytes
            buffer = io.BytesIO()
            save_kwargs = {'format': format}

            if format.upper() == 'JPEG':
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True

            image.save(buffer, **save_kwargs)
            image_bytes = buffer.getvalue()

            return base64.b64encode(image_bytes).decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            raise

    @staticmethod
    def from_base64(base64_string: str) -> np.ndarray:
        """
        Convert base64 string to NumPy array.

        Args:
            base64_string: Base64 encoded image

        Returns:
            NumPy array in BGR format (OpenCV)
        """
        try:
            # Decode base64
            image_bytes = base64.b64decode(base64_string)

            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to NumPy array (BGR for OpenCV)
            return ImageUtils.pil_to_numpy(image, bgr=True)

        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise

    @staticmethod
    def create_thumbnail(
        image: Union[np.ndarray, Image.Image],
        width: int = 320,
        maintain_aspect: bool = True
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
                pil_image = ImageUtils.numpy_to_pil(image)
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
            thumb_array = ImageUtils.pil_to_numpy(pil_image)

            # Convert to base64
            thumb_base64 = ImageUtils.to_base64(pil_image, format='JPEG', quality=70)

            return thumb_array, thumb_base64

        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            raise

    @staticmethod
    def resize_image(
        image: np.ndarray,
        width: Optional[int] = None,
        height: Optional[int] = None,
        max_dimension: Optional[int] = None
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

    @staticmethod
    def draw_overlay(
        image: np.ndarray,
        overlays: list,
        copy: bool = True
    ) -> np.ndarray:
        """
        Draw overlays (rectangles, text, etc.) on image.

        Args:
            image: Input image
            overlays: List of overlay dictionaries
            copy: If True, work on copy of image

        Returns:
            Image with overlays
        """
        if copy:
            image = image.copy()

        for overlay in overlays:
            overlay_type = overlay.get('type')

            if overlay_type == 'rectangle':
                cv2.rectangle(
                    image,
                    (overlay['x'], overlay['y']),
                    (overlay['x'] + overlay['width'], overlay['y'] + overlay['height']),
                    overlay.get('color', (0, 255, 0)),
                    overlay.get('thickness', 2)
                )

            elif overlay_type == 'text':
                cv2.putText(
                    image,
                    overlay['text'],
                    (overlay['x'], overlay['y']),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    overlay.get('scale', 1.0),
                    overlay.get('color', (0, 255, 0)),
                    overlay.get('thickness', 2)
                )

            elif overlay_type == 'circle':
                cv2.circle(
                    image,
                    (overlay['x'], overlay['y']),
                    overlay['radius'],
                    overlay.get('color', (0, 255, 0)),
                    overlay.get('thickness', 2)
                )

            elif overlay_type == 'line':
                cv2.line(
                    image,
                    (overlay['x1'], overlay['y1']),
                    (overlay['x2'], overlay['y2']),
                    overlay.get('color', (0, 255, 0)),
                    overlay.get('thickness', 2)
                )

        return image

    @staticmethod
    def extract_roi(
        image: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int,
        safe: bool = True
    ) -> Optional[np.ndarray]:
        """
        Extract Region of Interest from image.

        Args:
            image: Input image
            x: ROI x coordinate
            y: ROI y coordinate
            width: ROI width
            height: ROI height
            safe: If True, clip ROI to image bounds

        Returns:
            ROI as NumPy array or None if invalid
        """
        img_height, img_width = image.shape[:2]

        if safe:
            # Clip ROI to image bounds
            x = max(0, min(x, img_width))
            y = max(0, min(y, img_height))
            x2 = max(0, min(x + width, img_width))
            y2 = max(0, min(y + height, img_height))

            if x2 <= x or y2 <= y:
                logger.warning(f"Invalid ROI after clipping: {x},{y},{x2},{y2}")
                return None

            return image[y:y2, x:x2].copy()
        else:
            # Strict bounds checking
            if x < 0 or y < 0 or x + width > img_width or y + height > img_height:
                logger.warning(f"ROI out of bounds: {x},{y},{width},{height} for image {img_width}x{img_height}")
                return None

            return image[y:y+height, x:x+width].copy()