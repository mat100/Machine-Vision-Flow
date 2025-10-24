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
- **Parallel Processing**: Multiple detections run simultaneously on same image

### Core Components

#### Python Backend (`python-backend/`)
- **main.py:195** - FastAPI app with global manager instances
- **core/image_manager.py:307** - Shared memory storage, LRU cache, thumbnails
- **core/camera_manager.py:341** - USB/IP/test camera abstraction, MJPEG streaming
- **core/template_manager.py:324** - Template file storage, learning from ROI
- **core/history_buffer.py:334** - Circular buffer for inspection records
- **api/routers/camera.py:250+** - Capture, preview, stream endpoints
- **api/routers/vision.py:300+** - Template match, edge detect endpoints
- **vision/edge_detection.py:392** - Canny, Sobel, Laplacian methods

#### Node-RED Custom Nodes (`node-red/nodes/`)
- **camera/mv-camera-capture** - Triggers capture, returns image_id + thumbnail
- **vision/mv-template-match** - Calls template matching API with ROI/threshold
- **analysis/mv-result-merger** - Collects parallel results, applies pass/fail logic
- **output/mv-overlay** - Annotates images with detection results

### Data Flow Pattern
```
[Trigger] → [Camera: capture once] → image_id + thumbnail
                    ↓
         ┌→ [Detection 1] →┐
         ├→ [Detection 2] →├→ [Merger: wait & decide] → PASS/FAIL
         └→ [Detection 3] →┘
         (parallel processing)
```

### Message Structure Evolution
```javascript
// After camera capture
msg = {
    image_id: "uuid",
    thumbnail: "base64..."
}

// After each detection (accumulates)
msg.detections = [
    { node_id: "tm1", found: true, score: 0.92, position: {x,y} },
    { node_id: "tm2", found: false }
]

// After merger
msg.result = "PASS" // or "FAIL"
msg.summary = { passed: 2, failed: 1, total: 3 }
```

## Key Technical Details

### Image Management Strategy
- **Full Images**: Stored in Python shared memory (max 100 images, 1GB)
- **Thumbnails**: Base64-encoded 320px width for UI display
- **Image IDs**: UUIDs reference shared memory locations
- **Cleanup**: LRU eviction when limits reached

### Result Merger Logic
- Waits for N inputs or timeout (1000ms default)
- Decision rules: all_pass, any_pass, min_count, custom JavaScript
- Groups results by image_id for correlation
- Outputs combined result with all detection details

### API Endpoints
```
POST /api/camera/capture?camera_id=test     # Returns image_id + thumbnail
POST /api/vision/template-match             # Template matching with ROI
POST /api/vision/edge-detect                # Edge detection
GET  /api/camera/stream/{id}                # MJPEG live stream
POST /api/templates/learn                   # Learn template from ROI
```

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