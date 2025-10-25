# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MachineVisionFlow** is a modular industrial machine vision system inspired by Keyence and Cognex platforms. It provides a distributed architecture combining a FastAPI Python backend for computer vision processing with a Node-RED frontend for visual workflow programming.

**Architecture**: Service-oriented with clear separation between API layer, business logic (services), core infrastructure (managers), and vision algorithms.

**Key Components**:
- **Python Backend** (FastAPI): REST API on port 8000
- **Node-RED Dashboard**: Visual workflow interface on port 1880
- **Shared Memory**: Zero-copy image storage with LRU caching
- **Multi-Camera Support**: USB, IP cameras, and test image sources

## Essential Commands

### Development
```bash
# Start development mode with auto-reload (Python + Node-RED)
make dev

# Starts uvicorn with --reload for Python backend
# Starts nodemon for Node-RED with auto-restart on file changes
# Set MV_CONFIG_FILE to python-backend/config.dev.yaml
# Uses config.dev.yaml by default (debug mode, verbose logging)
```

### Service Management
```bash
make install    # Install Python venv + Node.js dependencies
make start      # Start both services (production mode)
make stop       # Stop both services
make status     # Check service status
make reload     # Stop and restart services
make logs       # Tail service logs (backend.log + node-red.log)
```

### Testing
```bash
# Run all tests
make test
# Or directly:
cd python-backend && source venv/bin/activate && python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/api/test_vision_api.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Test markers available: unit, integration, slow
python -m pytest -m "not slow" tests/
```

### Code Quality
```bash
make format       # Run black + isort on Python code
make lint         # Run flake8 linting
make setup-hooks  # Install pre-commit hooks

# Pre-commit runs automatically on git commit with:
# - black (line-length=100)
# - isort (--profile=black)
# - flake8 (--extend-ignore=E203,W503)
# - trailing-whitespace, end-of-file-fixer
# - check-yaml, check-merge-conflict
```

### Environment Setup
```bash
# Development uses config.dev.yaml (debug mode)
export MV_CONFIG_FILE=/home/cnc/MachineVisionFlow/python-backend/config.dev.yaml

# Production uses config.yaml (if it exists) or defaults
# Config precedence: env vars > YAML file > defaults
```

## Architecture Highlights

### Directory Structure
```
python-backend/
├── main.py                   # FastAPI app with lifespan management
├── config.py                 # Pydantic-based configuration
├── api/                      # REST API layer
│   ├── models.py            # Shared Pydantic models (ROI, VisionObject, VisionResponse)
│   ├── dependencies.py      # FastAPI dependency injection (get_managers, validate_*)
│   ├── exceptions.py        # Custom exceptions + handlers
│   └── routers/             # Endpoint routers (camera, vision, template, image, history, system)
├── core/                     # Core infrastructure
│   ├── camera_manager.py    # Multi-camera abstraction
│   ├── image_manager.py     # Shared memory storage + LRU cache
│   ├── template_manager.py  # Template file management
│   ├── history_buffer.py    # Time-series inspection tracking
│   ├── overlay_renderer.py  # Detection result visualization
│   ├── roi_handler.py       # ROI extraction and validation
│   └── constants.py         # System constants
├── services/                 # Business logic layer
│   ├── camera_service.py
│   ├── vision_service.py    # Orchestrates vision processing
│   └── image_service.py
└── vision/                   # Computer vision algorithms
    ├── edge_detection.py    # Canny, Sobel, Laplacian, Prewitt, Scharr
    ├── color_detection.py   # HSV-based color range detection
    ├── aruco_detection.py   # ArUco marker detection
    └── rotation_detection.py

node-red/
├── nodes/                    # Custom Node-RED nodes
│   ├── camera/              # mv-camera-capture, mv-image-simulator, mv-live-preview
│   ├── vision/              # mv-template-match, mv-edge-detect, mv-color-detect, etc.
│   └── output/              # mv-overlay
└── flows/                    # Node-RED workflow definitions
```

### Key Design Patterns

**1. Dependency Injection** (FastAPI-native)
```python
# All managers stored in app.state during lifespan startup
# Injected via dependencies.py helpers

def get_managers(request: Request) -> Managers:
    return Managers(
        image_manager=request.app.state.image_manager,
        camera_manager=request.app.state.camera_manager,
        template_manager=request.app.state.template_manager,
        history_buffer=request.app.state.history_buffer,
    )

# Use in routers:
def endpoint(vision_service: VisionService = Depends(get_vision_service)):
    ...
```

**2. Template Method Pattern** (Vision Processing)
All vision detection endpoints follow the same flow via `VisionService._execute_detection()`:
- Image retrieval from ImageManager
- ROI extraction if specified
- Algorithm-specific detection
- Coordinate adjustment (ROI offset)
- Overlay rendering
- Thumbnail generation
- History recording
- Response assembly

**3. Shared Memory Architecture**
Images stored in shared memory for zero-copy access across processes:
```python
# ImageManager uses multiprocessing.shared_memory
# LRU eviction at 90% capacity
# Reference counting for cleanup
image_id = image_manager.store(frame)  # Returns UUID
image = image_manager.get(image_id)     # Fast retrieval
```

**4. Unified API Models**
```python
# api/models.py defines shared schemas:
ROI           # Rectangular region with geometric operations
VisionObject  # Detection result with bounding_box, contour, confidence
VisionResponse # Container for objects + thumbnail + timing
```

### Data Flow Example (Vision Detection)

```
1. POST /api/vision/template-match
   Body: {image_id, template_id, roi}
   ↓
2. validate_vision_request()
   - Check image exists in ImageManager
   - Validate ROI bounds
   ↓
3. VisionService._execute_detection()
   - Get image from shared memory
   - Extract ROI if specified
   - Run template matching algorithm
   - Adjust coordinates for ROI offset
   - Render overlay visualization
   - Generate thumbnail
   - Record to history buffer
   ↓
4. Return VisionResponse
   {objects: [...], thumbnail_base64: "...", processing_time_ms: 45}
```

### Configuration System

**Configuration Structure** (config.py):
- ImageConfig: max_images, max_memory_mb, thumbnail_width
- CameraConfig: default_camera, capture_timeout, stream_fps
- TemplateConfig: storage_path, max_file_size, allowed_formats
- VisionConfig: canny_thresholds, contour_limits, blur_size
- HistoryConfig: buffer_size, time_interval
- APIConfig: host, port, CORS, rate limiting
- SystemConfig: debug, log_level, worker_threads

**Configuration Sources** (priority order):
1. Environment variables with `MV_` prefix (nested: `MV_IMAGE__MAX_IMAGES=100`)
2. YAML file specified by `MV_CONFIG_FILE` env var
3. Code defaults

**Development vs Production**:
- `config.dev.yaml`: Debug mode, verbose logging, larger thumbnails, auto-reload
- `config.yaml`: Production settings (if exists)

## Development Guidelines

### Adding a New Vision Algorithm

1. Create detector module in `python-backend/vision/`:
```python
# vision/my_detection.py
def detect_my_feature(image, params):
    # Implement detection logic
    # Return list of VisionObject instances
    return [VisionObject(type="my_feature", bounding_box=..., confidence=...)]
```

2. Add endpoint in `api/routers/vision.py`:
```python
@router.post("/my-detect", response_model=VisionResponse)
async def detect_my_feature(
    request: MyDetectRequest,
    vision_service: VisionService = Depends(get_vision_service),
):
    # Use vision_service._execute_detection() for unified flow
    return await vision_service.my_detect(...)
```

3. Add service method in `services/vision_service.py`:
```python
async def my_detect(self, image_id: str, params: dict, roi: Optional[dict] = None):
    return await self._execute_detection(
        image_id=image_id,
        roi=roi,
        detector_func=lambda img: detect_my_feature(img, params),
        detector_name="my_feature",
    )
```

4. Create corresponding Node-RED node in `node-red/nodes/vision/`:
```javascript
// mv-my-detect.js + mv-my-detect.html
// Make HTTP POST to /api/vision/my-detect
```

### Working with Shared Memory Images

Always use ImageManager for image storage/retrieval:
```python
# Store (returns UUID)
image_id = image_manager.store(frame)

# Retrieve (fast, zero-copy)
image = image_manager.get(image_id)

# Check existence
if image_manager.has_image(image_id):
    ...

# Cleanup handled automatically via LRU
```

### Testing Patterns

Test fixtures are available in `python-backend/tests/conftest.py`:
- `test_image`, `test_template`: Synthetic test images
- `image_manager`, `camera_manager`, etc.: Real manager instances
- `mock_*`: Mock managers for unit tests

```python
# Example test structure
def test_vision_detection(vision_service, test_image, image_manager):
    # Store test image
    image_id = image_manager.store(test_image)

    # Run detection
    result = await vision_service.edge_detect(image_id, method="canny")

    # Assertions
    assert len(result.objects) > 0
    assert result.processing_time_ms > 0
```

### Error Handling

Use unified validation helpers from `api/dependencies.py`:
```python
# Validate image exists
validate_image_exists(image_id, image_manager)

# Validate ROI bounds
validate_roi_bounds(roi, image_id, image_manager)

# Or combined validation
validate_vision_request(image_id, roi, image_manager)
```

Custom exceptions in `api/exceptions.py`:
- `ImageNotFoundException`
- `CameraConnectionException`
- `TemplateNotFoundException`
- `ROIValidationException`

All routers should use `@safe_endpoint` decorator for consistent error handling.

### Debugging Tips

**Development mode** (`make dev`):
- Python backend: Auto-reloads on `.py` changes (uvicorn --reload)
- Node-RED: Auto-restarts on `.js`/`.html` changes (nodemon)
- Logs to console with DEBUG level
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Check service health**:
```bash
curl http://localhost:8000/api/system/health
curl http://localhost:8000/api/system/info
```

**Inspect shared memory**:
```python
# In Python shell
from core.image_manager import ImageManager
mgr = ImageManager.get_instance()  # If singleton pattern used
print(mgr.list_images())
print(mgr.get_stats())
```

**View logs**:
```bash
make logs  # Tail both backend and Node-RED logs
# Or individually:
tail -f var/log/backend.log
tail -f var/log/node-red.log
```

### Pre-commit Hooks

Hooks enforce code quality before commits:
- **black**: Format Python code (line-length=100)
- **isort**: Sort imports (--profile=black)
- **flake8**: Lint Python (ignore E203, W503)
- **trailing-whitespace**, **end-of-file-fixer**: Cleanup
- **check-yaml**, **check-merge-conflict**: Safety checks

Install with `make setup-hooks` or manually:
```bash
cd python-backend
source venv/bin/activate
pip install pre-commit black isort flake8
pre_commit install
```

## Node-RED Integration

Custom nodes communicate with FastAPI backend via HTTP:
```javascript
// Example: mv-template-match.js
axios.post('http://localhost:8000/api/vision/template-match', {
    image_id: msg.image_id,
    template_id: msg.template_id,
    roi: msg.roi
})
.then(response => {
    msg.payload = response.data;
    node.send(msg);
});
```

Node structure:
- `nodes/*/mv-*.js`: Node logic (JavaScript)
- `nodes/*/mv-*.html`: Node UI definition
- `nodes/lib/vision-utils.js`: Shared utilities

## Common Pitfalls

1. **Image not in cache**: Images evicted by LRU. Increase `max_images` or `max_memory_mb` in config.
2. **ROI out of bounds**: Always validate ROI against image dimensions before processing.
3. **Camera connection fails**: Check camera permissions, USB enumeration, or use `test` camera for development.
4. **Import errors**: Ensure `python-backend/` is in PYTHONPATH or run from that directory.
5. **Config not loaded**: Set `MV_CONFIG_FILE` env var before starting services.

## Performance Considerations

- **Shared memory**: Images stored without copying between processes
- **LRU caching**: Automatic eviction at 90% memory threshold
- **Thumbnail caching**: Base64-encoded thumbnails cached in ImageManager
- **Async processing**: FastAPI endpoints use async/await for non-blocking I/O
- **Template matching**: Can be slow on large images; use ROI to constrain search area

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **OpenCV Python**: https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html
- **Node-RED Custom Nodes**: https://nodered.org/docs/creating-nodes/
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
