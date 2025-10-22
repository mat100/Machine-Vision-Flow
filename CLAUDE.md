# Machine Vision Flow - Project Guide

## Overview
This is a modular Machine Vision system inspired by Keyence and Cognex, built with Node-RED for visual workflow programming and Python backend for computer vision processing.

## Quick Start

### 1. Start Python Backend
```bash
cd python-backend
python3 -m pip install -r requirements.txt  # First time only
python3 main.py
```
The backend runs on http://localhost:8000

### 2. Install Node-RED Nodes
```bash
cd ~/.node-red
npm install /home/cnc/MachineVisionFlow/node-red
npm install node-red-contrib-image-output  # For image preview
node-red-restart
```

### 3. Import Example Flow
1. Open Node-RED UI (http://localhost:1880)
2. Menu → Import → Clipboard
3. Paste contents from `node-red/flows/examples/basic-inspection.json`
4. Deploy

## Architecture

### Key Design Decisions
- **Node-RED as UI Only**: All CV processing happens in Python backend, Node-RED is purely for workflow orchestration
- **REST API Communication**: FastAPI backend with REST endpoints (not WebSocket)
- **Shared Memory for Images**: Full images stored in shared memory, only image_id passed between services
- **Base64 for Thumbnails Only**: Thumbnails (160-640px) encoded in base64 for preview
- **No Buffer Node**: Node-RED natively splits messages to multiple outputs - no intermediate buffer needed
- **Manual Triggers**: Detection triggered by message input, not automatic/periodic

### System Flow
```
[Trigger Message] → [Camera Capture] → [Multiple Parallel Detections] → [Result Merger] → [Decision]
                           ↓
                    Returns image_id
                    + thumbnail_base64
                           ↓
                    ┌→ [Template Match 1] →┐
                    ├→ [Template Match 2] →├→ [Merger waits for all] → [Pass/Fail]
                    └→ [Template Match 3] →┘
```

### Message Structure
Each detection adds to the message chain:
```javascript
msg = {
    image_id: "uuid",
    thumbnail: "base64...",
    detections: [
        { node_id: "tm1", found: true, score: 0.92, ... },
        { node_id: "tm2", found: false, ... }
    ]
}
```

## Components

### Python Backend (`python-backend/`)
- **main.py**: FastAPI application entry point
- **core/image_manager.py**: Shared memory image storage with LRU cache
- **core/camera_manager.py**: Camera abstraction (USB/IP/test images)
- **core/template_manager.py**: Template storage and management
- **core/history_buffer.py**: Circular buffer for inspection history
- **api/routers/**: REST API endpoints

### Node-RED Nodes (`node-red/nodes/`)
- **mv-camera-capture**: Captures image on trigger message
- **mv-template-match**: Template matching with ROI support
- **mv-result-merger**: Waits for multiple detections, applies decision rules
- **mv-overlay**: Prepares thumbnail for display
- **mv-image-simulator**: Test image generation

## API Endpoints

### Camera
- `POST /api/camera/capture` - Capture image from camera
- `GET /api/camera/{camera_id}/preview` - Get live preview

### Vision
- `POST /api/vision/template-match` - Perform template matching
- `POST /api/vision/edge-detect` - Edge detection (placeholder)

### Templates
- `GET /api/templates` - List all templates
- `POST /api/templates/upload` - Upload new template
- `POST /api/templates/learn` - Learn template from image ROI

### History
- `GET /api/history/recent` - Get recent inspections
- `GET /api/history/stats` - Get statistics

## Key Features

### Parallel Detection
- Single image captured once
- Multiple detection nodes process in parallel
- Each adds results to message chain
- Result merger waits for all inputs

### Template Matching
- ROI (Region of Interest) support
- Multi-scale searching
- Multiple matching methods (NCC, CCOEFF, etc.)
- Threshold configuration

### Result Merger
- Configurable input count with timeout
- Decision rules:
  - All must pass
  - Any must pass
  - Minimum count
  - Custom JavaScript

### Efficient Image Handling
- Shared memory prevents copying
- Reference counting for cleanup
- Only thumbnails in base64
- Image IDs passed between services

## Development Tips

### Adding New Vision Node
1. Create `.js` and `.html` files in `node-red/nodes/vision/`
2. Add to `package.json`
3. Implement API endpoint in `python-backend/api/routers/vision.py`
4. Restart Node-RED

### Testing Without Camera
- Use `camera_id: "test"` for test images
- Image simulator node for patterns

### Debugging
- Check Python backend logs: `http://localhost:8000/docs`
- Node-RED debug panel for message inspection
- Enable debug logging in Node-RED settings

## Common Issues

### Nodes Not Appearing
- Restart Node-RED after installation
- Check `npm list node-red-contrib-machine-vision-flow`

### Connection Refused
- Ensure Python backend is running
- Check API URL in nodes (default: http://localhost:8000)

### Images Not Displaying
- Install `node-red-contrib-image-output`
- Verify `thumbnail` property in message

## Important Notes
- This system uses manual triggers (message-driven), not automatic capture
- All CV processing happens in Python, Node-RED is UI only
- Templates can be files, uploaded, or learned from ROI
- History is in-memory circular buffer (no database)
- Supports 1-2 cameras simultaneously

## Language Requirements
- **ALL text in the project MUST be in English**
- This includes: code comments, documentation, output messages, log messages, user interface, variable and function names, error messages, README files, and configuration files
- No Czech or other languages allowed in any part of the codebase

## Future Enhancements
- Edge detection implementation
- Neural network integration (PyTorch ready)
- Camera calibration support
- WebSocket for live preview
- Database for long-term history