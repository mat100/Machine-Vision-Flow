"""
Camera API Router
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime
import numpy as np
import cv2
import asyncio
import time

from api.models import (
    CameraInfo,
    CameraConnectRequest,
    CameraCaptureResponse,
    Size
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_managers(request: Request):
    """Get managers from app state"""
    return {
        'image_manager': request.app.state.image_manager(),
        'camera_manager': request.app.state.camera_manager(),
        'config': request.app.state.config
    }


@router.post("/list")
async def list_cameras(managers=Depends(get_managers)) -> List[CameraInfo]:
    """List available cameras"""
    try:
        camera_manager = managers['camera_manager']
        cameras = camera_manager.list_available_cameras()

        return [
            CameraInfo(
                id=cam['id'],
                name=cam['name'],
                type=cam['type'],
                resolution=Size(
                    width=cam.get('resolution', {}).get('width', 1920),
                    height=cam.get('resolution', {}).get('height', 1080)
                ),
                connected=cam.get('connected', False)
            )
            for cam in cameras
        ]

    except Exception as e:
        logger.error(f"Failed to list cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect_camera(
    request: CameraConnectRequest,
    managers=Depends(get_managers)
) -> dict:
    """Connect to a camera"""
    try:
        camera_manager = managers['camera_manager']

        # Parse camera ID to get type and source
        if request.camera_id.startswith("usb_"):
            camera_type = "usb"
            source = int(request.camera_id.split("_")[1])
        else:
            camera_type = "usb"  # Default
            source = 0

        resolution = None
        if request.resolution:
            resolution = (request.resolution.width, request.resolution.height)

        success = camera_manager.connect_camera(
            camera_id=request.camera_id,
            camera_type=camera_type,
            source=source,
            resolution=resolution
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to connect camera")

        return {
            "success": True,
            "message": f"Camera {request.camera_id} connected"
        }

    except Exception as e:
        logger.error(f"Failed to connect camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture")
async def capture_image(
    camera_id: str,
    managers=Depends(get_managers)
) -> CameraCaptureResponse:
    """Capture image from camera"""
    try:
        camera_manager = managers['camera_manager']
        image_manager = managers['image_manager']
        config = managers['config']

        # Capture image
        image = camera_manager.capture(camera_id)

        if image is None:
            # Try test image for development
            logger.warning(f"Camera {camera_id} not found, using test image")
            image = camera_manager.create_test_image(f"Camera: {camera_id}")

        # Store in image manager
        metadata = {
            'camera_id': camera_id,
            'timestamp': datetime.now().isoformat()
        }
        image_id = image_manager.store(image, metadata)

        # Create thumbnail
        thumbnail_width = config['image_buffer']['thumbnail_width']
        _, thumbnail_base64 = image_manager.create_thumbnail(image, thumbnail_width)

        return CameraCaptureResponse(
            success=True,
            image_id=image_id,
            timestamp=datetime.now(),
            thumbnail_base64=thumbnail_base64,
            metadata={
                'camera_id': camera_id,
                'width': image.shape[1],
                'height': image.shape[0]
            }
        )

    except Exception as e:
        logger.error(f"Failed to capture image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{camera_id}")
async def get_preview(
    camera_id: str,
    managers=Depends(get_managers)
) -> dict:
    """Get preview image from camera"""
    try:
        camera_manager = managers['camera_manager']
        image_manager = managers['image_manager']
        config = managers['config']

        # Get preview frame
        image = camera_manager.get_preview(camera_id)

        if image is None:
            # Use test image
            image = camera_manager.create_test_image(f"Preview: {camera_id}")

        # Create thumbnail
        thumbnail_width = config['image_buffer']['thumbnail_width']
        _, thumbnail_base64 = image_manager.create_thumbnail(image, thumbnail_width)

        return {
            "success": True,
            "thumbnail_base64": thumbnail_base64,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect/{camera_id}")
async def disconnect_camera(
    camera_id: str,
    managers=Depends(get_managers)
) -> dict:
    """Disconnect camera"""
    try:
        camera_manager = managers['camera_manager']

        success = camera_manager.disconnect_camera(camera_id)

        if not success:
            raise HTTPException(status_code=404, detail="Camera not found")

        return {
            "success": True,
            "message": f"Camera {camera_id} disconnected"
        }

    except Exception as e:
        logger.error(f"Failed to disconnect camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Store active streams to limit concurrent connections
active_streams = {}


@router.get("/stream/{camera_id}")
async def stream_mjpeg(
    camera_id: str,
    managers=Depends(get_managers)
):
    """
    Stream MJPEG video from camera for live preview.

    Returns a multipart/x-mixed-replace stream of JPEG frames.
    Resolution: 1280x720
    FPS: 15
    """
    camera_manager = managers['camera_manager']
    config = managers['config']

    # Check if stream already exists for another camera (single stream limitation)
    if active_streams and camera_id not in active_streams:
        # Stop other streams
        for stream_id in list(active_streams.keys()):
            active_streams[stream_id] = False
        active_streams.clear()

    # Mark this stream as active
    active_streams[camera_id] = True

    # Get preview settings from config or use defaults
    preview_resolution = config.get('preview', {}).get('resolution', [1280, 720])
    preview_fps = config.get('preview', {}).get('fps', 15)
    preview_quality = config.get('preview', {}).get('quality', 85)

    frame_interval = 1.0 / preview_fps  # Time between frames

    async def generate():
        """Generate MJPEG frames"""
        last_frame_time = 0

        try:
            while active_streams.get(camera_id, False):
                current_time = time.time()

                # Limit frame rate
                if current_time - last_frame_time < frame_interval:
                    await asyncio.sleep(frame_interval - (current_time - last_frame_time))

                # Get frame from camera
                frame = camera_manager.get_preview(camera_id)

                if frame is None:
                    # Use test image if camera not available
                    frame = camera_manager.create_test_image(
                        f"Live Preview: {camera_id}\nTime: {datetime.now().strftime('%H:%M:%S')}"
                    )

                # Resize frame to target resolution
                if frame.shape[:2] != (preview_resolution[1], preview_resolution[0]):
                    frame = cv2.resize(frame, tuple(preview_resolution))

                # Encode frame as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), preview_quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)

                # Yield frame in MJPEG format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       buffer.tobytes() +
                       b'\r\n')

                last_frame_time = time.time()

        except Exception as e:
            logger.error(f"Error in MJPEG stream: {e}")
        finally:
            # Clean up stream
            if camera_id in active_streams:
                del active_streams[camera_id]
            logger.info(f"MJPEG stream ended for camera {camera_id}")

    # Return streaming response
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'close',
        }
    )


@router.post("/stream/stop/{camera_id}")
async def stop_stream(camera_id: str) -> dict:
    """Stop MJPEG stream for a camera"""
    if camera_id in active_streams:
        active_streams[camera_id] = False
        return {"success": True, "message": f"Stream stopped for camera {camera_id}"}
    return {"success": False, "message": "Stream not found"}