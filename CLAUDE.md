# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Machine Vision Flow

Modular machine vision system inspired by Keyence/Cognex industrial vision. Node-RED provides visual workflow programming, Python FastAPI backend handles computer vision processing.

## Common Commands

### Development (most common)

**VSCode Development (recommended):**
```bash
# 1. Open project in VSCode
# 2. Press F5 → Select "Debug: Full Stack (Python + Node-RED)"
# 3. Set breakpoints in Python code and debug!
# See .vscode/README.md for details
```

**Production mode (no debugging):**
```bash
# Quick start both services
make start          # Start both services in background
make status         # Check if services are running
make logs           # View logs from both services
make stop           # Stop both services

# After code changes
make reload         # Restart both services (no reinstall)
```

### Installation/Setup
```bash
# First time setup
make install        # Install both backends

# After adding new dependencies
make reinstall-backend    # Update Python packages
make reinstall-nodered    # Update Node-RED nodes
```

### Testing
```bash
make test                              # Run all tests
cd python-backend && python -m pytest  # Direct pytest
python -m pytest tests/test_specific.py::test_function  # Single test
```

### Manual Start (without Make)
```bash
# Python backend (port 8000)
cd python-backend
source venv/bin/activate  # or python3 -m venv venv first
python3 main.py

# Node-RED (port 1880)
node-red
```

## Architecture Overview

### System Design Principles
- **Node-RED = Orchestration Only**: All CV processing in Python, Node-RED just coordinates workflow
- **Shared Memory Images**: Full images in shared memory, only UUIDs passed around
- **Base64 Thumbnails**: Only small previews (320px) sent to Node-RED
- **Message-Driven**: Manual triggers, not automatic/periodic capture
- **One Object Per Message**: Detection nodes send N messages for N detected objects
- **Unified Message Format**: All nodes use VisionObject in msg.payload

### Core Components

#### Python Backend (`python-backend/`)
- **main.py:195** - FastAPI app with global manager instances
- **core/image_manager.py:307** - Shared memory storage, LRU cache, thumbnails
- **core/camera_manager.py:341** - USB/IP/test camera abstraction, MJPEG streaming
- **core/template_manager.py:324** - Template file storage, learning from ROI
- **core/history_buffer.py:334** - Circular buffer for inspection records
- **api/models.py:60** - VisionObject and VisionResponse (standard interface)
- **api/routers/camera.py:250+** - Capture, preview, stream endpoints
- **api/routers/vision.py:300+** - Template match, edge detect, color detect endpoints
- **vision/edge_detection.py:392** - Canny, Sobel, Laplacian methods
- **vision/color_detection.py** - Histogram and K-means dominant color detection
- **vision/color_definitions.py** - Standard HSV color ranges (10 colors)
- **vision/aruco_detection.py** - ArUco fiducial marker detection (OpenCV 4.8.1+)
- **vision/rotation_detection.py** - Object rotation analysis (min_area_rect, ellipse_fit, PCA)
- **services/vision_service.py** - Business logic for all vision operations

#### Node-RED Custom Nodes (`node-red/nodes/`)
- **camera/mv-camera-capture** - Triggers capture, returns VisionObject with image_id
- **vision/mv-template-match** - Template matching, sends N messages for N matches
- **vision/mv-edge-detect** - Edge detection with 6 methods, sends N messages for N contours
- **vision/mv-color-detect** - Dominant color detection, auto-uses msg.payload.bounding_box if present
- **vision/mv-aruco-detect** - ArUco marker detection, sends N messages for N markers, supports ROI
- **vision/mv-rotation-detect** - Rotation analysis from contours, supports reference objects
- **vision/mv-roi-extract** - Extracts ROI from full image for focused processing
- **output/mv-overlay** - Annotates images with detection results

### Data Flow Patterns

**Pattern 1: Simple Sequential Processing**
```
[Trigger] → [Camera Capture] → VisionObject with image_id
                    ↓
            [Template Match] → sends N messages (one per match)
                    ↓
            [Application Logic] → decides PASS/FAIL based on objects
```

**Pattern 2: Parallel Detection Branches**
```
[Camera Capture] → VisionObject
         ↓
         ├→ [Edge Detect] → N messages (contours)
         ├→ [Template Match] → N messages (matches)
         └→ [Color Detect] → 1 message (if found)
              ↓ ↓ ↓
         [Application aggregates results]
```

**Pattern 3: ROI-based Color Analysis**
```
[Camera Capture] → full image
       ↓
[Edge Detect] → finds 3 contours, sends 3 messages (each with bounding_box + contour)
       ↓ ↓ ↓
  [Color Detect] → automatically analyzes contour area from each message
       ↓ ↓ ↓
  [Application Logic] → counts red regions, decides PASS/FAIL

Note: Color Detect automatically uses msg.payload.contour for precise masking,
      falling back to bounding_box if contour not present. Analyzes only pixels
      inside the actual contour shape, excluding background within the bbox.
```

**Pattern 4: ArUco Reference with Rotation Analysis**
```
[Camera Capture] → full image
       ↓
       ├→ [ArUco Detect] → finds reference marker, sends marker with rotation
       │        ↓
       │   [Set Reference] → stores marker as msg.reference_object
       │        ↓
       └→ [Edge Detect] → finds object contours
                ↓ ↓ ↓
         [Rotation Detect] → calculates rotation relative to reference
                ↓ ↓ ↓
         [Application Logic] → checks if object rotation matches expected angle

Note: ArUco markers provide absolute rotation reference. Rotation Detect can
      calculate relative rotation by comparing object angle to reference marker.
      Both nodes support ROI from msg.payload.bounding_box for focused analysis.
```

### Unified Message Format

**ALL vision nodes use this standard format:**

```javascript
// msg.payload = VisionObject (always)
msg.payload = {
    object_id: "contour_0",           // Unique ID for this object
    object_type: "edge_contour",      // Type: camera_capture | edge_contour | template_match |
                                      //       color_region | aruco_marker | rotation_analysis
    image_id: "uuid-of-full-image",   // Reference to shared memory image
    timestamp: "2025-10-24T10:30:00", // ISO format
    bounding_box: {x, y, width, height},
    center: {x, y},
    confidence: 0.95,                 // 0.0-1.0
    area: 30000.0,                    // Optional
    perimeter: 700.0,                 // Optional
    rotation: 45.0,                   // Optional - rotation in degrees (0-360)
    contour: [[x1,y1], [x2,y2], ...], // Optional - contour points (from edge detection)
    thumbnail: "base64...",           // 320px preview with overlays
    properties: {}                    // Node-specific data
}

// Metadata in message root
msg.success = true;
msg.processing_time_ms = 45;
msg.node_name = "Edge Detection";
```

**Important Rules:**
- **1 object = 1 message**: Detection nodes send multiple messages if they find multiple objects
- **0 objects = send nothing**: No message is sent if nothing is detected
- **No arrays**: No `msg.objects[]` or `msg.detections[]` arrays
- **Data in payload**: All vision data goes in `msg.payload` as VisionObject
- **Metadata in root**: Processing info (success, time, node name) in `msg.*`

## Key Technical Details

### Image Management Strategy
- **Full Images**: Stored in Python shared memory (max 100 images, 1GB)
- **Thumbnails**: Base64-encoded 320px width for UI display
- **Image IDs**: UUIDs reference shared memory locations
- **Cleanup**: LRU eviction when limits reached

### Standard Object Interface

All vision detection APIs use a unified format:

**VisionObject** - Universal object representation (Python model):
```python
{
    "object_id": "contour_0",
    "object_type": "edge_contour" | "template_match" | "color_region" |
                   "camera_capture" | "aruco_marker" | "rotation_analysis",
    "image_id": "uuid",  # Optional, added by Node-RED
    "timestamp": "2025-10-24T10:30:00",  # Optional, added by Node-RED
    "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 150},
    "center": {"x": 200, "y": 125},
    "confidence": 0.85,  # 0.0-1.0
    "area": 30000.0,     # Optional
    "perimeter": 700.0,  # Optional
    "rotation": 0.0,     # Optional - rotation in degrees (0-360)
    "properties": {},    # Type-specific data
    "contour": []        # Optional, for edge detection
}
```

**VisionResponse** - Standard API response (Python model):
```python
{
    "objects": [VisionObject, ...],  # List of detected objects (can be empty)
    "thumbnail_base64": "...",       # 320px preview with overlays
    "processing_time_ms": 45
}
```

### API Endpoints
```
POST /api/camera/capture?camera_id=test     # Returns image_id + thumbnail
POST /api/vision/template-match             # Template matching with ROI
POST /api/vision/edge-detect                # Edge detection (6 methods)
POST /api/vision/color-detect               # Dominant color detection (auto)
POST /api/vision/aruco-detect               # ArUco marker detection with ROI support
POST /api/vision/rotation-detect            # Rotation analysis from contours
GET  /api/camera/stream/{id}                # MJPEG live stream
POST /api/templates/learn                   # Learn template from ROI
```

### Color Detection

**Available Colors** (predefined HSV ranges):
- Chromatic: red, orange, yellow, green, cyan, blue, purple
- Achromatic: white, black, gray

**Detection Methods**:
- `histogram` - Fast histogram peak detection
- `kmeans` - K-means clustering (more accurate, slower)

**Contour Masking** (NEW):
- **Enabled (default)**: Analyzes only pixels inside contour shape - more accurate
- **Disabled**: Analyzes full bounding box rectangle - faster but includes background
- Automatically uses `msg.payload.contour` from edge detection
- Falls back to bounding box if no contour available
- Visualization: Cyan contour outline + colored bbox rectangle in thumbnails

**Two Modes**:
1. **Detection only**: Returns dominant color found (no expected color)
2. **Color matching**: Checks if dominant color matches expected color + min percentage

### ArUco Marker Detection

**What are ArUco Markers?**
- Fiducial markers (2D barcodes) for establishing reference coordinate systems
- Each marker has unique ID and known size/orientation
- Provides absolute rotation reference for measuring object angles

**Supported Dictionaries**:
- DICT_4X4_50, DICT_5X5_50, DICT_6X6_50 (most common)
- DICT_4X4_100, DICT_4X4_250, DICT_4X4_1000
- DICT_5X5_100, DICT_5X5_250, DICT_5X5_1000
- DICT_6X6_100, DICT_6X6_250, DICT_6X6_1000
- DICT_7X7_50, DICT_7X7_100, DICT_7X7_250, DICT_7X7_1000
- DICT_ARUCO_ORIGINAL

**ROI Support**:
- Automatically uses `msg.payload.bounding_box` to limit search area
- Improves performance and reduces false positives
- Coordinates adjusted from ROI-relative to absolute

**Output Properties**:
- `marker_id`: Unique marker ID from dictionary
- `corners`: 4 corner points [[x,y], [x,y], [x,y], [x,y]]
- `rotation`: Marker rotation in degrees (0-360)

### Rotation Detection

**What is Rotation Detection?**
- Calculates object orientation from contour points
- Three methods with different accuracy/speed tradeoffs
- Can calculate absolute or relative (to reference) rotation

**Detection Methods**:
- `min_area_rect` - Fast, uses minimum area rectangle (best for rectangular objects)
- `ellipse_fit` - Medium, fits ellipse to contour (best for elliptical/circular objects)
- `pca` - Robust, Principal Component Analysis (best for irregular shapes)

**Angle Ranges**:
- `0_360` - Returns 0° to 360° (default, 0° = horizontal right)
- `-180_180` - Returns -180° to +180° (symmetric range)
- `0_180` - Returns 0° to 180° (for symmetric objects)

**Reference Object Pattern**:
- Store ArUco marker in `msg.reference_object`
- Rotation Detect automatically uses it to calculate relative rotation
- Example: If reference is 45° and object is 90°, relative rotation = 45°

**ROI Support**:
- Accepts `roi` parameter for visualization context
- Thumbnail shows only ROI area with properly aligned overlays
- Coordinates automatically converted between absolute and ROI-relative

### Development Ports
- Python Backend: `http://localhost:8000`
- Node-RED UI: `http://localhost:1880`
- API Docs: `http://localhost:8000/docs`

### Configuration Files
- `python-backend/config.yaml` - Production settings
- `python-backend/config.dev.yaml` - Development settings (debug, auto-reload)
- `Makefile` - Primary control interface (40+ targets)

## Testing Without Hardware

Use `camera_id: "test"` to generate synthetic test images:
```bash
curl -X POST http://localhost:8000/api/camera/capture?camera_id=test
```

**Test Image Contents**:
- 3 ArUco markers (IDs: 0, 5, 17) with white borders for reliable detection
- 2 colored rectangles (red, blue)
- 1 circle
- Grid pattern background

**Note**: Test images include ArUco markers using OpenCV 4.8.1+ API (`generateImageMarker`).
If using older OpenCV, update `camera_manager.py` test image generation.

## Adding New Features

### New Vision Algorithm
1. Create module in `python-backend/vision/your_algorithm.py`
2. Add endpoint in `python-backend/api/routers/vision.py`
3. Create Node-RED node pair in `node-red/nodes/vision/`
4. Register in `node-red/package.json`
5. Run `make reload` to apply changes

### New Core Manager
1. Create class in `python-backend/core/your_manager.py`
2. Initialize in `main.py` lifespan handler
3. Access via `app.state.your_manager` in routers

## Language Requirement
**ALL code and documentation must be in English only.** No Czech or other languages in comments, variables, messages, or documentation.

## Important Notes
- Manual trigger system (not automatic capture)
- Parallel detection on single captured image
- In-memory history buffer (no database)
- Supports 1-2 cameras simultaneously
- Edge detection fully implemented with 6 methods
- Templates stored as files with JSON metadata
- ArUco detection requires OpenCV 4.8.1+ (uses new ArucoDetector API)
- Rotation detection supports 3 methods: min_area_rect, ellipse_fit, PCA
- Both ArUco and Rotation detection support ROI from msg.payload.bounding_box