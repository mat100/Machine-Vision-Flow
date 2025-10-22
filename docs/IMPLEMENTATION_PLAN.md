# Machine Vision Flow - Implementation Plan

## Project Overview

Modular Machine Vision system inspired by Keyence and Cognex, built on combination of Node-RED (UI/orchestration) and Python backend (CV processing).

## System Architecture

### Key Architecture - Parallel Detection
```
                    ┌→ [Template Match A] →┐
[Camera Capture] →──├→ [Template Match B] →├→ [Result Merger] → [Decision]
                    └→ [Edge Detection]   →┘
```
- **Direct Connection**: Camera node output connects directly to multiple Detection nodes
- **Parallel Processing**: Each Detection node calls Python backend independently
- **Result Merger**: Waits for all results and combines them according to custom rules

### Node-RED (Frontend/UI)
- Visual workflow designer for building vision pipelines
- Dashboard UI for monitoring and control
- Integration with `node-red-contrib-image-output` for inline previews
- Vision operation configuration directly in node properties
- **Each detection has its own node** for maximum flexibility

### Python Backend (CV Processing)
- FastAPI server with REST API (+ WebSocket for streaming in future)
- OpenCV + PyTorch for computer vision
- Monolithic server with async processing for 1-2 cameras
- Shared memory for efficient image passing (local deployment)
- **Parallel detection processing** using asyncio
- **Adaptive buffer sizing** for variable throughput
- **Circular buffer** for short-term inspection history

## Key Features

### Efficient Data Transfer
- **Full resolution images:** Shared memory (zero-copy for local deployment)
- **Between Node-RED nodes:** Image ID + base64 thumbnail
- **Thumbnails:** Configurable resolution (160-640px), for visualization only
- **Buffer management:** LRU cache with max memory size + reference counting

### Result Chain Management
- Accumulation of all operation results
- Each node adds its results to previous ones
- Enables pipeline branching based on results
- Operation history for debugging

### Template Management
- **Combined approach** for template management:
  - Directory with files (`/templates/*.png`)
  - Upload directly in Node-RED node configuration
  - Learning mode - mark area on live image
- **Template caching** in Python backend
- **REST API** for template management

### Inspection History
- **Circular buffer** for last N inspections (configurable)
- In-memory storage (no database)
- Contains: results, thumbnails, timestamps, metadata
- Accessible via Node-RED dashboard

### Live Preview
- **Periodic refresh** (configurable interval 0.5-10s)
- Dashboard component with auto-refresh
- Endpoint `/api/camera/preview/{camera_id}`
- Thumbnail size for fast transfer

### Debug Mode
- **Intermediate results visualization** on each node
- Integration with node-red-contrib-image-output
- Overlay with debug info (processing time, scores, ROI)
- Option to save debug images

## Project Structure

```
MachineVisionFlow/
├── python-backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── config.yaml
│   ├── templates/                 # Template images storage
│   │   └── README.md
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── camera.py          # Camera endpoints
│   │   │   ├── vision.py          # Vision processing endpoints
│   │   │   ├── template.py        # Template management endpoints
│   │   │   ├── history.py         # Inspection history endpoints
│   │   │   └── system.py          # System status/performance
│   │   └── models.py              # Pydantic models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── image_manager.py       # Shared memory + LRU cache
│   │   ├── camera_manager.py      # Camera abstraction
│   │   ├── template_manager.py    # Template storage and caching
│   │   ├── history_buffer.py      # Circular buffer for history
│   │   ├── result_chain.py        # Result accumulation
│   │   └── thumbnail.py           # Thumbnail generator
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── base.py                # VisionTool interface
│   │   ├── template_matching.py   # Template matching algorithms
│   │   ├── edge_detection.py      # Edge/contour detection
│   │   ├── blob_detection.py      # Blob analysis
│   │   ├── calibration.py         # Camera calibration
│   │   └── preprocessing.py       # Filters, morphology
│   └── utils/
│       ├── __init__.py
│       ├── performance.py         # Profiling and monitoring
│       ├── debug_overlay.py       # Debug visualization
│       └── error_handling.py      # Error strategies
│
├── node-red/
│   ├── package.json
│   ├── settings.js
│   ├── flows/
│   │   └── examples/
│   │       ├── basic-inspection.json
│   │       ├── multi-detection.json
│   │       └── pcb-inspection.json
│   ├── nodes/
│   │   ├── camera/
│   │   │   ├── mv-camera-capture/    # Capture from camera
│   │   │   └── mv-image-simulator/   # Load from files
│   │   ├── vision/
│   │   │   ├── mv-template-match/    # Template matching
│   │   │   ├── mv-edge-detect/       # Edge detection
│   │   │   ├── mv-blob-detect/       # Blob analysis
│   │   │   ├── mv-preprocessing/     # Image preprocessing
│   │   │   └── mv-calibration/       # Calibration
│   │   ├── analysis/
│   │   │   ├── mv-result-merger/     # Combine multiple detections
│   │   │   └── mv-decision/          # Pass/Fail logic
│   │   └── output/
│   │       ├── mv-overlay/           # Draw results on image
│   │       └── mv-dashboard/         # Dashboard display
│   └── dashboard/
│       └── ui-templates/
│
├── docker-compose.yml
├── docs/
└── examples/
```

## API Design

### REST Endpoints

```python
# Camera management
POST   /api/camera/list              # List available cameras
POST   /api/camera/connect           # Connect to camera
POST   /api/camera/capture           # Capture frame
GET    /api/camera/preview/{id}      # Live preview (auto-refresh)
DELETE /api/camera/disconnect/{id}   # Disconnect camera

# Vision processing - each node calls its endpoint
POST   /api/vision/template-match    # Template matching
POST   /api/vision/edge-detect       # Edge detection
POST   /api/vision/blob-detect       # Blob analysis
POST   /api/vision/preprocess        # Image preprocessing
POST   /api/vision/calibrate         # Camera calibration

# Template management
GET    /api/template/list            # List all templates
POST   /api/template/upload          # Upload new template
POST   /api/template/learn           # Learn from live image
GET    /api/template/{id}/image      # Get template image
DELETE /api/template/{id}            # Delete template

# History management
GET    /api/history/recent           # Last N inspections
GET    /api/history/{id}             # Specific inspection detail
POST   /api/history/clear            # Clear history

# Image management
GET    /api/image/{id}/data          # Get full image
GET    /api/image/{id}/thumbnail     # Get thumbnail
GET    /api/image/{id}/metadata      # Image metadata
DELETE /api/image/{id}               # Delete from buffer

# System
GET    /api/system/status            # System status
GET    /api/system/performance       # Performance metrics
POST   /api/system/debug/{enable}    # Enable/disable debug mode
```

### Data Formats

#### Message format between Node-RED nodes

**From Camera node (sent to ALL connected detection nodes):**
```javascript
msg.payload = {
    image_id: "uuid-v4",
    timestamp: 1234567890,
    thumbnail_base64: "data:image/jpeg;base64,...",
    metadata: {
        width: 1920,
        height: 1080,
        camera: "Camera_1"
    }
}
```

**From each Detection node:**
```javascript
msg.payload = {
    image_id: "uuid-v4",
    thumbnail_base64: "data:image/jpeg;base64,...", // with result overlay
    detection: {
        node_id: "template_match_1",
        name: "Screw Top-Left",
        type: "template_match",
        params: {threshold: 0.8, template: "screw_1"},
        duration_ms: 45,
        result: {
            found: true,
            position: {x: 100, y: 200},
            score: 0.95
        }
    }
}
```

**From Result Merger node (combines all detections):**
```javascript
msg.payload = {
    image_id: "uuid-v4",
    all_detections: [
        {name: "Screw 1", found: true, score: 0.92},
        {name: "Screw 2", found: true, score: 0.88},
        {name: "Hole", found: false}
    ],
    summary: {
        total_checks: 3,
        passed: 2,
        failed: 1,
        success_rate: 0.67
    },
    result: "FAIL",  // based on custom rules
    failed_checks: ["Hole"]
}
```

## Parallel Detection - Implementation Details

### How Multiple Detections on Single Image Work

1. **Camera Capture** captures image and stores it in Python backend
2. **Python returns image_id**, which is used for all detections
3. **Node-RED automatically** sends msg to all connected nodes
4. **Each Detection node** independently calls Python API with same image_id
5. **Python processes** all requests in parallel (async)
6. **Result Merger** waits for all results and combines them

### Example Node-RED Flows

#### Simple check - 3 screws
```
                    ┌→ [Template: Screw 1] →┐
[Camera Capture] →──├→ [Template: Screw 2] →├→ [Merger] → [Pass/Fail]
                    └→ [Template: Screw 3] →┘
```

#### Complex PCB check
```
                    ┌→ [Template: CPU] ────────→┐
                    ├→ [Template: RAM] ────────→│
[Camera Capture] →──├→ [Blob: Count Capacitors]→├→ [Merger] → [Dashboard]
                    ├→ [Edge: Find Cracks] ────→│
                    └→ [Template: Connector] ──→┘
```

### ROI (Region of Interest) Configuration

Each detection node can set ROI - image area where to search:

```javascript
// Node-RED node configuration
{
    roi_enabled: true,
    roi: {
        x: 100,        // X position (pixels)
        y: 50,         // Y position (pixels)
        width: 400,    // Area width
        height: 300    // Area height
    }
}
```

ROI is validated against image resolution and visualized in debug mode.

### Result Merger - Rule Configuration

```javascript
// Example custom rules in Result Merger node
function evaluateResults(detections) {
    // All must pass
    if (config.rule === "all_pass") {
        return detections.every(d => d.found);
    }

    // At least X of Y
    if (config.rule === "min_count") {
        const passed = detections.filter(d => d.found).length;
        return passed >= config.min_required;
    }

    // Custom JavaScript
    if (config.rule === "custom") {
        // E.g. critical components must be found
        const critical = ["CPU", "RAM"];
        const critical_ok = detections
            .filter(d => critical.includes(d.name))
            .every(d => d.found);

        // Non-critical - 80% is enough
        const others = detections.filter(d => !critical.includes(d.name));
        const others_ok = others.filter(d => d.found).length / others.length >= 0.8;

        return critical_ok && others_ok;
    }
}
```

## Outputs and Integration

### Output Formats
- **Primarily Node-RED flow** - all results stay in Node-RED
- **Dashboard visualization** - real-time results display
- **No external protocols** - not Modbus, not OPC-UA
- **Ready for extension** - API prepared for future integrations

### Dashboard Components
- **Live Preview** - camera view with auto-refresh
- **Inspection Results** - current results with overlay
- **History View** - last N inspections
- **Statistics** - success rate, processing time
- **Template Manager** - template management and learning
- **Debug Panel** - intermediate results visualization

## Trigger Mechanism

### Manual Trigger via Node-RED Flow
- **Camera Capture node waits for input message** (msg object)
- Any incoming message triggers image capture and subsequent detection
- Trigger can come from:
  - Dashboard button (ui_button)
  - Inject node (for testing)
  - HTTP endpoint
  - MQTT topic
  - Any other Node-RED node

**Example flow with trigger:**
```
[Button/Inject/MQTT] → [Camera Capture] → [Detection nodes] → [Result]
         ↑
    msg trigger
```

Node doesn't work continuously, only when it receives input message.

## Implementation Status

### Phase 1: Core Infrastructure
- [x] FastAPI server setup
- [x] Shared memory image buffer
- [x] LRU cache implementation
- [x] Thumbnail generator
- [x] Basic error handling

### Phase 2: Camera Support
- [x] USB camera support (OpenCV)
- [x] IP camera support (RTSP/HTTP)
- [ ] GigE Vision support
- [x] Camera abstraction layer
- [x] Multi-camera management

### Phase 3: Vision Processing
- [x] Template matching (NCC, SAD, SSD)
- [x] Multi-scale matching
- [ ] Rotation invariant matching
- [x] Edge detection (6 methods)
- [ ] Blob detection
- [x] Camera calibration
- [x] Image preprocessing (filters, morphology)

### Phase 4: Node-RED Integration
- [x] Custom node base class
- [x] Camera nodes
- [x] Vision processing nodes
- [x] Result viewer nodes
- [x] Image simulator for testing

### Phase 5: User Experience
- [x] Basic/Advanced configuration mode
- [ ] Configuration presets
- [ ] Live preview
- [x] Dashboard components
- [x] Performance monitoring

## Technology Stack

### Python Backend
- **FastAPI** 0.104+ - REST API framework
- **OpenCV** 4.8+ - Computer vision
- **NumPy** - Numerical computing
- **Pillow** - Thumbnail generation
- **PyTorch** - For future ML features
- **uvicorn** - ASGI server
- **multiprocessing** - Shared memory

### Node-RED
- **Node-RED** 3.0+ - Flow-based programming
- **node-red-contrib-image-output** - Inline image preview
- **node-red-dashboard** - UI components
- **axios** - HTTP client for API calls

## Known Limitations

1. **Shared memory** works only for local deployment
2. **Monolithic server** can be bottleneck under high load (solution: Celery workers)
3. **REST API** not ideal for real-time streaming (solution: WebSocket in future)
4. **Node-RED** has limitations for complex UI (solution: custom dashboard components)