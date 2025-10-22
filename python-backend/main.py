"""
Machine Vision Flow - Main FastAPI Application
"""

import asyncio
import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import routers
from api.routers import camera, vision, template, history, system

# Import core components
from core.image_manager import ImageManager
from core.camera_manager import CameraManager
from core.template_manager import TemplateManager
from core.history_buffer import HistoryBuffer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()

# Initialize managers
image_manager = None
camera_manager = None
template_manager = None
history_buffer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global image_manager, camera_manager, template_manager, history_buffer

    # Startup
    logger.info("Starting Machine Vision Flow server...")

    # Initialize managers
    image_manager = ImageManager(
        max_size_mb=config['image_buffer']['max_size_mb'],
        max_images=config['image_buffer']['max_images']
    )

    camera_manager = CameraManager(
        default_resolution=config['camera']['default_resolution']
    )

    template_manager = TemplateManager(
        storage_path=config['template']['storage_path']
    )

    history_buffer = HistoryBuffer(
        max_size=config['history']['max_inspections']
    )

    logger.info("All managers initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Machine Vision Flow server...")

    # Cleanup managers
    if camera_manager:
        await camera_manager.cleanup()
    if image_manager:
        image_manager.cleanup()

    logger.info("Server shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Machine Vision Flow",
    description="Modular Machine Vision System inspired by Keyence and Cognex",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Node-RED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Node-RED URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            "image_manager": image_manager is not None,
            "camera_manager": camera_manager is not None,
            "template_manager": template_manager is not None,
            "history_buffer": history_buffer is not None
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

# Make managers accessible to routers
app.state.image_manager = lambda: image_manager
app.state.camera_manager = lambda: camera_manager
app.state.template_manager = lambda: template_manager
app.state.history_buffer = lambda: history_buffer
app.state.config = config

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config['server']['host'],
        port=config['server']['port'],
        reload=config['server']['debug'],
        log_level="info"
    )