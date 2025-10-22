"""
System API Router - Status and performance monitoring
"""

import logging
import psutil
import time
from fastapi import APIRouter, Request, Depends
from datetime import datetime

from api.models import SystemStatus, PerformanceMetrics, DebugSettings

logger = logging.getLogger(__name__)

router = APIRouter()

# Track start time
START_TIME = time.time()


def get_managers(request: Request):
    """Get managers from app state"""
    return {
        'image_manager': request.app.state.image_manager(),
        'camera_manager': request.app.state.camera_manager(),
        'template_manager': request.app.state.template_manager(),
        'history_buffer': request.app.state.history_buffer(),
        'config': request.app.state.config
    }


@router.get("/status")
async def get_status(managers=Depends(get_managers)) -> SystemStatus:
    """Get system status"""
    try:
        image_manager = managers['image_manager']
        camera_manager = managers['camera_manager']

        # Get memory usage
        process = psutil.Process()
        memory_info = process.memory_info()

        # Get system memory
        virtual_memory = psutil.virtual_memory()

        # Count active cameras
        active_cameras = len([
            cam for cam_id, cam in camera_manager.cameras.items()
            if cam.connected
        ])

        # Get buffer usage
        buffer_stats = image_manager.get_stats()

        return SystemStatus(
            status="healthy",
            uptime=time.time() - START_TIME,
            memory_usage={
                'process_mb': memory_info.rss / 1024 / 1024,
                'system_percent': virtual_memory.percent,
                'available_mb': virtual_memory.available / 1024 / 1024
            },
            active_cameras=active_cameras,
            buffer_usage=buffer_stats
        )

    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return SystemStatus(
            status="error",
            uptime=time.time() - START_TIME,
            memory_usage={},
            active_cameras=0,
            buffer_usage={}
        )


@router.get("/performance")
async def get_performance(managers=Depends(get_managers)) -> PerformanceMetrics:
    """Get performance metrics"""
    try:
        history_buffer = managers['history_buffer']

        # Get statistics from history
        stats = history_buffer.get_statistics()

        # Calculate operations per minute
        uptime_minutes = (time.time() - START_TIME) / 60
        ops_per_minute = stats['total'] / uptime_minutes if uptime_minutes > 0 else 0

        return PerformanceMetrics(
            avg_processing_time=stats['avg_time_ms'],
            total_inspections=stats['total'],
            success_rate=stats['success_rate'],
            operations_per_minute=round(ops_per_minute, 2)
        )

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return PerformanceMetrics(
            avg_processing_time=0,
            total_inspections=0,
            success_rate=0,
            operations_per_minute=0
        )


@router.post("/debug/{enable}")
async def set_debug_mode(
    enable: bool,
    managers=Depends(get_managers)
) -> DebugSettings:
    """Enable or disable debug mode"""
    try:
        config = managers['config']

        # Update debug settings
        config['debug']['save_debug_images'] = enable
        config['debug']['show_overlays'] = enable

        # Configure logging level
        log_level = logging.DEBUG if enable else logging.INFO
        logging.getLogger().setLevel(log_level)

        logger.info(f"Debug mode {'enabled' if enable else 'disabled'}")

        return DebugSettings(
            enabled=enable,
            save_images=config['debug']['save_debug_images'],
            show_overlays=config['debug']['show_overlays'],
            verbose_logging=enable
        )

    except Exception as e:
        logger.error(f"Failed to set debug mode: {e}")
        raise


@router.get("/config")
async def get_config(managers=Depends(get_managers)) -> dict:
    """Get current configuration"""
    return managers['config']


@router.get("/health")
async def health_check() -> dict:
    """Simple health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }