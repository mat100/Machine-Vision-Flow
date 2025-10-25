"""
Camera identifier parsing and formatting utilities.

Provides unified camera ID handling to eliminate duplicated string parsing logic.
"""

import logging
from typing import Tuple, Union

logger = logging.getLogger(__name__)


class CameraIdentifier:
    """
    Utilities for parsing and formatting camera identifiers.

    Camera ID formats:
    - "usb_N" - USB camera at index N (e.g., "usb_0", "usb_1")
    - "test" - Test/simulator camera
    - "ip_ADDRESS" - IP camera (future support)

    Default fallback: "usb_0"
    """

    # Camera type constants
    TYPE_USB = "usb"
    TYPE_TEST = "test"
    TYPE_IP = "ip"

    @staticmethod
    def parse(camera_id: str) -> Tuple[str, Union[int, str, None]]:
        """
        Parse camera ID into type and source.

        Args:
            camera_id: Camera identifier string

        Returns:
            Tuple of (camera_type, source)
            - camera_type: "usb", "test", or "ip"
            - source: int for USB index, str for IP address, None for test

        Examples:
            >>> CameraIdentifier.parse("usb_0")
            ("usb", 0)
            >>> CameraIdentifier.parse("usb_1")
            ("usb", 1)
            >>> CameraIdentifier.parse("test")
            ("test", None)
            >>> CameraIdentifier.parse("invalid")
            ("usb", 0)  # Default fallback
        """
        if not camera_id:
            logger.warning("Empty camera_id provided, defaulting to usb_0")
            return (CameraIdentifier.TYPE_USB, 0)

        # Test camera
        if camera_id == CameraIdentifier.TYPE_TEST:
            return (CameraIdentifier.TYPE_TEST, None)

        # USB camera
        if camera_id.startswith(f"{CameraIdentifier.TYPE_USB}_"):
            try:
                source = int(camera_id.split("_")[1])
                return (CameraIdentifier.TYPE_USB, source)
            except (IndexError, ValueError) as e:
                logger.warning(f"Invalid USB camera ID '{camera_id}': {e}, defaulting to usb_0")
                return (CameraIdentifier.TYPE_USB, 0)

        # IP camera (future)
        if camera_id.startswith(f"{CameraIdentifier.TYPE_IP}_"):
            try:
                ip_address = camera_id.split("_", 1)[1]
                return (CameraIdentifier.TYPE_IP, ip_address)
            except IndexError as e:
                logger.warning(f"Invalid IP camera ID '{camera_id}': {e}")
                return (CameraIdentifier.TYPE_USB, 0)

        # Unknown format - default to USB 0
        logger.warning(f"Unknown camera ID format '{camera_id}', defaulting to usb_0")
        return (CameraIdentifier.TYPE_USB, 0)

    @staticmethod
    def format(camera_type: str, source: Union[int, str, None] = None) -> str:
        """
        Format camera type and source into camera ID.

        Args:
            camera_type: Camera type ("usb", "test", "ip")
            source: Camera source (int for USB, str for IP, None for test)

        Returns:
            Formatted camera ID string

        Examples:
            >>> CameraIdentifier.format("usb", 0)
            "usb_0"
            >>> CameraIdentifier.format("usb", 1)
            "usb_1"
            >>> CameraIdentifier.format("test")
            "test"
            >>> CameraIdentifier.format("ip", "192.168.1.100")
            "ip_192.168.1.100"
        """
        if camera_type == CameraIdentifier.TYPE_TEST:
            return CameraIdentifier.TYPE_TEST

        if camera_type == CameraIdentifier.TYPE_USB:
            if source is None:
                source = 0
            return f"{CameraIdentifier.TYPE_USB}_{source}"

        if camera_type == CameraIdentifier.TYPE_IP:
            if source is None:
                raise ValueError("IP camera requires source address")
            return f"{CameraIdentifier.TYPE_IP}_{source}"

        raise ValueError(f"Unknown camera type: {camera_type}")

    @staticmethod
    def validate(camera_id: str) -> bool:
        """
        Validate camera ID format.

        Args:
            camera_id: Camera identifier to validate

        Returns:
            True if valid format, False otherwise
        """
        if not camera_id:
            return False

        # Test camera
        if camera_id == CameraIdentifier.TYPE_TEST:
            return True

        # USB camera
        if camera_id.startswith(f"{CameraIdentifier.TYPE_USB}_"):
            try:
                int(camera_id.split("_")[1])
                return True
            except (IndexError, ValueError):
                return False

        # IP camera
        if camera_id.startswith(f"{CameraIdentifier.TYPE_IP}_"):
            parts = camera_id.split("_", 1)
            return len(parts) == 2 and len(parts[1]) > 0

        return False

    @staticmethod
    def is_test_camera(camera_id: str) -> bool:
        """Check if camera ID is test camera."""
        return camera_id == CameraIdentifier.TYPE_TEST

    @staticmethod
    def is_usb_camera(camera_id: str) -> bool:
        """Check if camera ID is USB camera."""
        return camera_id.startswith(f"{CameraIdentifier.TYPE_USB}_")

    @staticmethod
    def is_ip_camera(camera_id: str) -> bool:
        """Check if camera ID is IP camera."""
        return camera_id.startswith(f"{CameraIdentifier.TYPE_IP}_")
