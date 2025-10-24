# Machine Vision Flow

Modular Machine Vision system inspired by Keyence and Cognex, built on Node-RED (UI/orchestration) and Python backend (CV processing).

> **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, code style, and how to submit pull requests.

## 🚀 Quick Start

### Fastest way - Makefile

```bash
# Install dependencies
make install

# Start system
make start

# Check status
make status

# Stop system
make stop
```

After starting, available at:
- **Python Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Node-RED**: http://localhost:1880

## 📋 Available Commands

### Makefile (recommended)
```bash
make help          # Show help
make install       # Install dependencies
make start         # Start system
make stop          # Stop system
make restart       # Restart system
make status        # Check status
make logs          # View logs
make clean         # Clean temp files
make dev           # Development mode with live logs
make test          # Run tests
```

### Shell scripts (alternative)
```bash
make start      # Start services
make stop       # Stop services
make status     # System status
make logs       # View logs
make dev        # Development mode with auto-reload
```

### Systemd services (for production)
See [`systemd/README.md`](systemd/README.md) for detailed instructions.

Quick start:
```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable machinevisionflow-backend machinevisionflow-nodered
sudo systemctl start machinevisionflow-backend machinevisionflow-nodered

# Check status
sudo systemctl status machinevisionflow-backend
```

## 🏗️ Architecture

### Main Components
- **Node-RED**: Visual workflow designer for building inspection pipelines
- **Python Backend**: FastAPI server with OpenCV for Computer Vision processing
- **REST API**: Communication between Node-RED and Python
- **Shared Memory**: Efficient image passing without copying

### Parallel Detection
```
[Trigger] → [Camera Capture] → [Parallel Detections] → [Result Merger] → [Decision]
                           ↓
                    ┌→ [Template Match 1] →┐
                    ├→ [Template Match 2] →├→ [Merger waits] → [Pass/Fail]
                    └→ [Edge Detection]   →┘
```

### Message Flow
```javascript
// From Camera node
msg = {
    image_id: "uuid",
    thumbnail: "base64...",
}

// From Detection node
msg = {
    image_id: "uuid",
    detections: [
        { node_id: "tm1", found: true, score: 0.92 },
        { node_id: "edge", contour_count: 15 }
    ]
}

// From Result Merger
msg = {
    result: "PASS",
    summary: { passed: 2, failed: 0 }
}
```

## ✨ Features

### ✅ Implemented
- **Camera Management**: USB cameras, IP cameras, test images
- **Live Preview**: MJPEG streaming at 1280x720, 15 FPS for camera setup
- **Template Matching**: Multi-scale, ROI support, various methods
- **Edge Detection**: 6 methods (Canny, Sobel, Laplacian, etc.)
- **Result Merger**: Custom JavaScript rules for evaluation
- **Image Buffer**: Shared memory with LRU cache
- **History Buffer**: Circular buffer for inspections
- **Template Manager**: Upload, learn, manage templates
- **Node-RED Nodes**: Camera, Template Match, Edge Detect, Result Merger, Live Preview

### 🚧 Planned
- Blob Detection (object detection and counting)
- OCR module (Tesseract)
- Barcode/QR reader
- Color Detection
- Pattern Recognition (circles, squares)
- Object Tracking
- Measurement Tools

## 🔧 Installation

### Requirements
- Python 3.8+
- Node.js 16+
- npm
- OpenCV dependencies

### Automatic Installation
```bash
make install
```

### Manual Installation

#### Python Backend
```bash
cd python-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Node-RED
```bash
# Global Node-RED installation
npm install -g node-red

# Machine Vision nodes
cd ~/.node-red
npm install /path/to/MachineVisionFlow/node-red
npm install node-red-contrib-image-output
```

## 📖 Usage

### 1. Import example flow

After starting, open Node-RED (http://localhost:1880):
1. Menu → Import → Examples
2. Select flow (basic-inspection, edge-detection)
3. Click Import
4. Deploy

### 2. Configure nodes

Double-click on node to open configuration:
- **Camera Capture**: Select camera from dropdown menu
- **Template Match**: Set template, threshold, ROI
- **Edge Detect**: Select method, set parameters
- **Result Merger**: Define evaluation rules

### 3. Run inspection

Click "Manual Trigger" (inject node) to start detection.

## 📹 Live Preview

The system includes MJPEG live preview for camera setup and positioning:

### Features
- **Resolution**: 1280x720 @ 15 FPS
- **Format**: MJPEG stream (works in any browser)
- **Single camera**: Resource-efficient streaming
- **Dashboard integration**: Full control UI

### Testing Live Preview
```bash
# Test MJPEG streaming
./scripts/test-live-preview.sh

# Or directly in browser
http://localhost:8000/api/camera/stream/test
```

### Using in Node-RED
1. Import `flows/examples/live-preview.json`
2. Deploy flow
3. Open Dashboard (`/ui`)
4. Click "Start Preview"

## 📡 API Endpoints

### Camera
- `POST /api/camera/list` - List available cameras
- `POST /api/camera/capture` - Capture image
- `GET /api/camera/preview/{id}` - Static preview
- `GET /api/camera/stream/{id}` - MJPEG live stream
- `POST /api/camera/stream/stop/{id}` - Stop stream

### Vision Processing
- `POST /api/vision/template-match` - Template matching
- `POST /api/vision/edge-detect` - Edge detection
- `POST /api/vision/blob-detect` - Blob detection

### Templates
- `GET /api/templates` - List templates
- `POST /api/templates/upload` - Upload template
- `POST /api/templates/learn` - Learn from ROI

### History
- `GET /api/history/recent` - Recent inspections
- `GET /api/history/stats` - Statistics

## 🛠️ Development

### Project Structure
```
MachineVisionFlow/
├── Makefile               # Main control
├── scripts/               # Helper scripts
├── services/              # Systemd services
├── python-backend/        # FastAPI server
│   ├── api/              # API routers
│   ├── core/             # Core components
│   └── vision/           # CV algorithms
├── node-red/              # Node-RED nodes
│   ├── nodes/            # Custom nodes
│   └── flows/            # Example flows
└── docs/                  # Documentation
    ├── architecture/     # Technical docs
    └── templates/        # UI templates
```

### Adding New Vision Function

1. **Python module** in `python-backend/vision/`
2. **API endpoint** in `api/routers/vision.py`
3. **Node-RED node** in `node-red/nodes/vision/`
4. **Restart**: `make restart`

### When to Restart vs Reinstall

**Just restart services** (90% of cases):
- Changes in existing `.py` files
- Changes in logic, functions, API endpoints
- Changes in Node-RED `.js` or `.html` files
- Bug fixes and code modifications

```bash
# Python backend - stop (Ctrl+C) and restart
cd python-backend
python3 main.py

# Node-RED
node-red-restart
# or
sudo systemctl restart nodered

# Both services
make restart
```

**Reinstall required** (structural changes only):
- Added new Python package to `requirements.txt`
- Added new Node-RED node files
- Modified `package.json`

```bash
# Python dependencies
cd python-backend
python3 -m pip install -r requirements.txt

# Node-RED nodes
cd ~/.node-red
npm install /home/cnc/MachineVisionFlow/node-red
node-red-restart

# Everything
make install
```

### Development Tips

```bash
# Auto-reload Python backend
cd python-backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Watch logs
make logs

# Development mode
make dev
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
sudo lsof -i :8000
sudo lsof -i :1880
make stop
```

### Missing Dependencies
```bash
make clean
make install
```

### Node-RED Nodes Not Showing
```bash
cd ~/.node-red
rm -rf node_modules/node-red-contrib-machine-vision-flow
npm install /path/to/MachineVisionFlow/node-red
node-red-restart
```

### Cameras Not Detected
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and log in again
```

### Check Status
```bash
make status
```

Output shows:
- Service status (Running/Stopped)
- Available cameras
- System information
- Log files

## 📊 Example Usage

### Python API
```python
import requests

# Capture image
response = requests.post("http://localhost:8000/api/camera/capture?camera_id=test")
image_id = response.json()["image_id"]

# Template matching
match_request = {
    "image_id": image_id,
    "template_id": "tmpl_example",
    "threshold": 0.8
}

response = requests.post(
    "http://localhost:8000/api/vision/template-match",
    json=match_request
)

result = response.json()
print(f"Found: {result['found']}")
```

### Node-RED Flow
```json
[
    {
        "id": "trigger",
        "type": "inject",
        "name": "Manual Trigger"
    },
    {
        "id": "camera",
        "type": "mv-camera-capture",
        "cameraId": "test",
        "wires": [["template_match"]]
    },
    {
        "id": "template_match",
        "type": "mv-template-match",
        "templateId": "tmpl_screw",
        "threshold": 0.8
    }
]
```

## 📝 Configuration

### Python Backend
Configuration in `python-backend/config.yaml`:
- Server port
- Image buffer size
- Thumbnail resolution
- Camera defaults

### Node-RED
- Node configuration directly in UI
- Flow export/import via JSON
- Dashboard accessible at `/ui`

## 🔒 Security

- API runs on localhost only
- CORS enabled for Node-RED
- Shared memory for local processes only
- Systemd services run under user account

## 📄 License

MIT

## 📚 Documentation

Detailed documentation is available in the `/docs` directory:

- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Implementation Plan](docs/architecture/IMPLEMENTATION_PLAN.md)** - Technical implementation details
- **[Live Preview Guide](docs/architecture/LIVE_PREVIEW_FIX.md)** - Live preview implementation notes
- **[Dashboard Templates](docs/templates/)** - Node-RED Dashboard templates

## 🤝 Support

If you have issues:
1. Check logs: `make logs`
2. Check status: `make status`
3. Restart services: `make restart`
4. Review [documentation](docs/README.md)
5. Create issue on GitHub

## 🙏 Acknowledgments

Inspired by industrial systems from Keyence and Cognex.