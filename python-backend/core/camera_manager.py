"""
Camera Manager - Handles multiple camera types (USB, IP, etc.)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np
from threading import Lock, Thread
from queue import Queue
import time

logger = logging.getLogger(__name__)


class CameraType(Enum):
    USB = "usb"
    IP = "ip"
    FILE = "file"


@dataclass
class CameraConfig:
    """Camera configuration"""
    id: str
    name: str
    type: CameraType
    source: Any  # int for USB, str for IP/file
    resolution: tuple = (1920, 1080)
    fps: int = 30


class Camera:
    """Base camera class"""

    def __init__(self, config: CameraConfig):
        self.config = config
        self.cap = None
        self.connected = False
        self.lock = Lock()
        self.last_frame = None
        self.last_capture_time = 0

    def connect(self) -> bool:
        """Connect to camera"""
        try:
            with self.lock:
                if self.config.type == CameraType.USB:
                    self.cap = cv2.VideoCapture(self.config.source)
                elif self.config.type == CameraType.IP:
                    self.cap = cv2.VideoCapture(self.config.source)
                elif self.config.type == CameraType.FILE:
                    self.cap = cv2.VideoCapture(self.config.source)
                else:
                    return False

                if self.cap and self.cap.isOpened():
                    # Set resolution
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
                    self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)

                    self.connected = True
                    logger.info(f"Camera {self.config.id} connected")
                    return True

                return False

        except Exception as e:
            logger.error(f"Failed to connect camera {self.config.id}: {e}")
            return False

    def disconnect(self):
        """Disconnect camera"""
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None
            self.connected = False
            logger.info(f"Camera {self.config.id} disconnected")

    def capture(self) -> Optional[np.ndarray]:
        """Capture single frame"""
        if not self.connected:
            return None

        with self.lock:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.last_frame = frame
                    self.last_capture_time = time.time()
                    return frame

        return None

    def get_preview(self) -> Optional[np.ndarray]:
        """Get preview frame (can be cached)"""
        # Keep a very short cache based on target FPS to avoid stale frames
        cache_ttl = 1.0 / max(self.config.fps, 1)
        if self.last_frame is not None and (time.time() - self.last_capture_time) < cache_ttl:
            return self.last_frame

        # Otherwise capture new frame
        return self.capture()


class CameraManager:
    """Manages multiple cameras"""

    def __init__(self, default_resolution: Dict[str, int] = None):
        self.cameras: Dict[str, Camera] = {}
        self.lock = Lock()
        self.default_resolution = (
            (default_resolution['width'], default_resolution['height'])
            if default_resolution
            else (1920, 1080)
        )

        # Preview thread
        self.preview_thread = None
        self.preview_queue = Queue()
        self.preview_running = False

        logger.info("Camera Manager initialized")

    def list_available_cameras(self) -> List[Dict[str, Any]]:
        """List available cameras"""
        cameras = []

        # Always add test camera option
        cameras.append({
            'id': 'test',
            'name': 'Test Image Generator',
            'type': 'test',
            'connected': True,
            'resolution': {
                'width': 1920,
                'height': 1080
            }
        })

        # Check USB cameras (typically 0-4 for better performance)
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Try to read actual resolution
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                    cameras.append({
                        'id': f'usb_{i}',
                        'name': f'USB Camera {i}',
                        'type': 'usb',
                        'source': i,
                        'connected': False,  # Not yet connected (just available)
                        'resolution': {
                            'width': width if width > 0 else 1920,
                            'height': height if height > 0 else 1080
                        }
                    })
                    cap.release()
            except Exception as e:
                logger.debug(f"Camera index {i} not available: {e}")
                continue

        # Add currently connected cameras
        with self.lock:
            for cam_id, camera in self.cameras.items():
                # Skip if already in list (e.g., USB cameras)
                if not any(c['id'] == cam_id for c in cameras):
                    cameras.append({
                        'id': cam_id,
                        'name': camera.config.name,
                        'type': camera.config.type.value,
                        'connected': camera.connected,
                        'resolution': {
                            'width': camera.config.resolution[0],
                            'height': camera.config.resolution[1]
                        }
                    })
                else:
                    # Update connection status for existing camera
                    for c in cameras:
                        if c['id'] == cam_id:
                            c['connected'] = camera.connected
                            break

        return cameras

    def connect_camera(
        self,
        camera_id: str,
        camera_type: str = "usb",
        source: Any = 0,
        name: Optional[str] = None,
        resolution: Optional[tuple] = None
    ) -> bool:
        """Connect to a camera"""
        with self.lock:
            # Check if already connected
            if camera_id in self.cameras and self.cameras[camera_id].connected:
                logger.warning(f"Camera {camera_id} already connected")
                return True

            # Create camera configuration
            config = CameraConfig(
                id=camera_id,
                name=name or camera_id,
                type=CameraType(camera_type),
                source=source,
                resolution=resolution or self.default_resolution
            )

            # Create and connect camera
            camera = Camera(config)
            if camera.connect():
                self.cameras[camera_id] = camera
                return True

            return False

    def disconnect_camera(self, camera_id: str) -> bool:
        """Disconnect a camera"""
        with self.lock:
            if camera_id in self.cameras:
                self.cameras[camera_id].disconnect()
                del self.cameras[camera_id]
                return True
            return False

    def capture(self, camera_id: str) -> Optional[np.ndarray]:
        """Capture frame from specific camera"""
        with self.lock:
            if camera_id in self.cameras:
                return self.cameras[camera_id].capture()

        logger.warning(f"Camera {camera_id} not found")
        return None

    def get_preview(self, camera_id: str) -> Optional[np.ndarray]:
        """Get preview frame from camera"""
        with self.lock:
            if camera_id in self.cameras:
                return self.cameras[camera_id].get_preview()

        return None

    def start_preview_stream(self, camera_id: str, interval_ms: int = 2000):
        """Start preview stream for a camera"""
        if self.preview_running:
            self.stop_preview_stream()

        self.preview_running = True
        self.preview_thread = Thread(
            target=self._preview_worker,
            args=(camera_id, interval_ms),
            daemon=True
        )
        self.preview_thread.start()
        logger.info(f"Preview stream started for camera {camera_id}")

    def stop_preview_stream(self):
        """Stop preview stream"""
        self.preview_running = False
        if self.preview_thread:
            self.preview_thread.join(timeout=2)
        logger.info("Preview stream stopped")

    def _preview_worker(self, camera_id: str, interval_ms: int):
        """Worker thread for preview streaming"""
        interval_sec = interval_ms / 1000.0

        while self.preview_running:
            frame = self.get_preview(camera_id)
            if frame is not None:
                self.preview_queue.put(frame)

            time.sleep(interval_sec)

    def get_camera_info(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get camera information"""
        with self.lock:
            if camera_id in self.cameras:
                camera = self.cameras[camera_id]
                return {
                    'id': camera.config.id,
                    'name': camera.config.name,
                    'type': camera.config.type.value,
                    'resolution': {
                        'width': camera.config.resolution[0],
                        'height': camera.config.resolution[1]
                    },
                    'fps': camera.config.fps,
                    'connected': camera.connected
                }

        return None

    async def cleanup(self):
        """Clean up all cameras"""
        logger.info("Cleaning up Camera Manager...")

        # Stop preview stream
        self.stop_preview_stream()

        # Disconnect all cameras
        with self.lock:
            for camera_id in list(self.cameras.keys()):
                self.cameras[camera_id].disconnect()
            self.cameras.clear()

        logger.info("Camera Manager cleanup complete")

    def create_test_image(self, text: str = "Test Image") -> np.ndarray:
        """Create a test image for development"""
        # Create a 1920x1080 test image
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # Add gradient background
        for i in range(1080):
            img[i, :] = [i * 255 // 1080, 100, 255 - i * 255 // 1080]

        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, text, (600, 540), font, 3, (255, 255, 255), 3)

        # Add timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(img, timestamp, (50, 50), font, 1, (255, 255, 255), 2)

        # Add grid
        for x in range(0, 1920, 192):
            cv2.line(img, (x, 0), (x, 1080), (50, 50, 50), 1)
        for y in range(0, 1080, 108):
            cv2.line(img, (0, y), (1920, y), (50, 50, 50), 1)

        return img