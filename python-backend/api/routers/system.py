"""
System API Router - Status and performance monitoring
"""

import logging
import psutil
import time
from fastapi import APIRouter, Request, Depends
from datetime import datetime

from api.models import SystemStatus, PerformanceMetrics, DebugSettings
from api.dependencies import (
    get_managers,
    get_image_manager,
    get_camera_manager,
    get_history_buffer
)
from api.exceptions import safe_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()

# Track start time
START_TIME = time.time()


@router.get("/status")
@safe_endpoint
async def get_status(
    image_manager = Depends(get_image_manager),
    camera_manager = Depends(get_camera_manager)
) -> SystemStatus:
    """Get system status"""
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


@router.get("/performance")
@safe_endpoint
async def get_performance(history_buffer = Depends(get_history_buffer)) -> PerformanceMetrics:
    """Get performance metrics"""
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


@router.post("/debug/{enable}")
@safe_endpoint
async def set_debug_mode(
    enable: bool,
    request: Request
) -> DebugSettings:
    """Enable or disable debug mode"""
    # Access config from app state
    config = request.app.state.config

    # Update debug settings if available
    if 'debug' in config:
        config['debug']['save_debug_images'] = enable
        config['debug']['show_overlays'] = enable

    # Configure logging level
    log_level = logging.DEBUG if enable else logging.INFO
    logging.getLogger().setLevel(log_level)

    logger.info(f"Debug mode {'enabled' if enable else 'disabled'}")

    return DebugSettings(
        enabled=enable,
        save_images=config.get('debug', {}).get('save_debug_images', enable),
        show_overlays=config.get('debug', {}).get('show_overlays', enable),
        verbose_logging=enable
    )


@router.get("/config")
@safe_endpoint
async def get_config(request: Request) -> dict:
    """Get current configuration"""
    return request.app.state.config


@router.get("/health")
async def health_check() -> dict:
    """Simple health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }