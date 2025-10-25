"""
Image format conversion utilities.

Handles conversions between different image formats:
- NumPy arrays (OpenCV BGR format)
- PIL Images (RGB format)
- Base64 encoded strings
- Grayscale/color conversions
"""

import base64
import io
import logging
from typing import Union

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImageConverters:
    """Utilities for converting between image formats."""

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
        image: Union[np.ndarray, Image.Image, bytes], format: str = "JPEG", quality: int = 85
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
                return base64.b64encode(image).decode("utf-8")

            # Convert numpy to PIL if needed
            if isinstance(image, np.ndarray):
                image = ImageConverters.numpy_to_pil(image)

            # Convert PIL Image to bytes
            buffer = io.BytesIO()
            save_kwargs = {"format": format}

            if format.upper() == "JPEG":
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True

            image.save(buffer, **save_kwargs)
            image_bytes = buffer.getvalue()

            return base64.b64encode(image_bytes).decode("utf-8")

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
            return ImageConverters.pil_to_numpy(image, bgr=True)

        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise

    @staticmethod
    def encode_image_to_base64(image: np.ndarray, format: str = ".png") -> str:
        """
        Encode OpenCV image (NumPy array) to base64 string.

        This is a simpler alternative to to_base64() specifically for OpenCV images,
        avoiding PIL conversion overhead.

        Args:
            image: OpenCV image (NumPy array)
            format: Image format ('.png', '.jpg', etc.)

        Returns:
            Base64 encoded string
        """
        try:
            _, buffer = cv2.imencode(format, image)
            return base64.b64encode(buffer).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}")
            raise

    @staticmethod
    def ensure_bgr(image: np.ndarray) -> np.ndarray:
        """
        Ensure image is in BGR format (convert from grayscale if needed).

        Args:
            image: Input image (grayscale or BGR)

        Returns:
            Image in BGR format
        """
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image.copy()

    @staticmethod
    def ensure_grayscale(image: np.ndarray) -> np.ndarray:
        """
        Ensure image is grayscale (convert from BGR if needed).

        Args:
            image: Input image (grayscale or BGR)

        Returns:
            Grayscale image
        """
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image.copy()
