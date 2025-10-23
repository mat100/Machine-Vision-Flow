"""
Machine Vision Flow - Main FastAPI Application
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import routers
from api.routers import camera, vision, template, history, system

# Import core components
from core.image_manager import ImageManager
from core.camera_manager import CameraManager
from core.template_manager import TemplateManager
from core.history_buffer import HistoryBuffer

# Import configuration and exception handlers
from config import get_settings, Settings
from api.exceptions import register_exception_handlers

# Get configuration
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.system.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress watchfiles debug messages
logging.getLogger("watchfiles").setLevel(logging.WARNING)

# Initialize managers
image_manager = None
camera_manager = None
template_manager = None
history_buffer = None
shutdown_event = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global image_manager, camera_manager, template_manager, history_buffer

    # Startup
    logger.info("Starting Machine Vision Flow server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.system.debug}")

    # Initialize managers with Pydantic config
    image_manager = ImageManager(
        max_size_mb=settings.image.max_memory_mb,
        max_images=settings.image.max_images
    )

    camera_manager = CameraManager()

    template_manager = TemplateManager(
        storage_path=settings.template.storage_path
    )

    history_buffer = HistoryBuffer(
        max_size=settings.history.buffer_size
    )

    logger.info("All managers initialized successfully")

    # Store managers in app state for access by routers
    app.state.image_manager = image_manager
    app.state.camera_manager = camera_manager
    app.state.template_manager = template_manager
    app.state.history_buffer = history_buffer
    app.state.config = settings.to_dict()
    app.state.debug = settings.system.debug

    yield

    # Shutdown
    logger.info("Shutting down Machine Vision Flow server...")

    # Cleanup managers - ensure camera is properly released
    try:
        if camera_manager:
            logger.info("Releasing all cameras...")
            await camera_manager.cleanup()
            # Give cameras time to fully release
            await asyncio.sleep(0.5)
        if image_manager:
            logger.info("Cleaning up image manager...")
            image_manager.cleanup()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

    logger.info("Server shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Machine Vision Flow",
    description="Modular Machine Vision System inspired by Keyence and Cognex",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Node-RED
if settings.api.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(camera.router, prefix="/api/camera", tags=["Camera"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"])
app.include_router(template.router, prefix="/api/template", tags=["Template"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(system.router, prefix="/api/system", tags=["System"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "Machine Vision Flow",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "camera": "/api/camera",
            "vision": "/api/vision",
            "template": "/api/template",
            "history": "/api/history",
            "system": "/api/system",
            "docs": "/docs"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "image_manager": hasattr(app.state, 'image_manager') and app.state.image_manager is not None,
            "camera_manager": hasattr(app.state, 'camera_manager') and app.state.camera_manager is not None,
            "template_manager": hasattr(app.state, 'template_manager') and app.state.template_manager is not None,
            "history_buffer": hasattr(app.state, 'history_buffer') and app.state.history_buffer is not None
        }
    }

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Note: Managers are set in lifespan handler above

def handle_signal(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()
    # Force exit after timeout
    import threading
    def force_exit():
        import time
        time.sleep(10)  # Give 10 seconds for graceful shutdown
        logger.warning("Forcing exit after timeout")
        sys.exit(1)
    threading.Thread(target=force_exit, daemon=True).start()

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    reload_excludes = [
        "*.log",
        "*.pyc",
        "__pycache__",
        ".git",
        ".venv",
        "venv"
    ] if settings.system.debug else None

    # Configure server with proper shutdown handling
    server_config = uvicorn.Config(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.system.debug,
        reload_excludes=reload_excludes,
        log_level="info",
        loop="asyncio"
    )

    server = uvicorn.Server(server_config)

    # Run server with proper signal handling
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server exiting...")