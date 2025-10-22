# Node-RED Machine Vision Nodes

Custom Node-RED nodes for Machine Vision Flow system.

## Installation

### 1. Install Node-RED (if not already installed)

```bash
npm install -g node-red
```

### 2. Install Machine Vision nodes

```bash
# In Node-RED user directory (usually ~/.node-red)
cd ~/.node-red

# Install from local directory
npm install /path/to/MachineVisionFlow/node-red

# Or create symlink for development
npm link /path/to/MachineVisionFlow/node-red
```

### 3. Install dependencies

```bash
# Image output node for displaying thumbnails
npm install node-red-contrib-image-output

# Dashboard (optional, for UI)
npm install node-red-dashboard
```

### 4. Restart Node-RED

```bash
node-red-restart
# or
node-red-stop
node-red
```

## Available Nodes

### Camera Nodes
- **mv-camera-capture** - Capture image from camera
- **mv-image-simulator** - Generate test images

### Vision Nodes
- **mv-template-match** - Template matching with ROI and multi-scale
- **mv-edge-detect** - Edge detection (placeholder)

### Analysis Nodes
- **mv-result-merger** - Combine results from multiple detections

### Output Nodes
- **mv-overlay** - Prepare image with overlay for display

## Usage

### Basic flow

```
[Trigger] → [Camera Capture] → [Template Match] → [Result]
```

### Parallel detection

```
                    ┌→ [Template Match 1] →┐
[Camera Capture] →──├→ [Template Match 2] →├→ [Result Merger] → [Decision]
                    └→ [Template Match 3] →┘
```

### Import example

1. Open Node-RED UI (http://localhost:1880)
2. Menu → Import → Clipboard
3. Paste content from `flows/examples/basic-inspection.json`
4. Click Import
5. Deploy

## Node Configuration

### Camera Capture

- **Camera ID**: `test` for test image, `usb_0` for USB camera
- **API URL**: Python backend URL (default: http://localhost:8000)
- **Resolution**: Camera resolution
- **Auto Connect**: Connect on startup

### Template Match

- **Template**: Select from library or upload new
- **Threshold**: Match threshold (0.0-1.0)
- **Method**: Matching method (NCC recommended)
- **ROI**: Region of interest for searching
- **Multi-Scale**: Search at different scales

### Result Merger

- **Input Count**: Number of inputs to wait for
- **Timeout**: Maximum wait time
- **Rule Type**: Decision logic
  - All must pass
  - Any must pass
  - Minimum count
  - Custom JavaScript

## Message Format

### Camera Output
```javascript
msg = {
    payload: {
        image_id: "uuid",
        timestamp: "2024-01-15T10:30:00",
        thumbnail_base64: "data:image/jpeg;base64,...",
        metadata: {
            width: 1920,
            height: 1080
        }
    },
    image_id: "uuid",
    thumbnail: "base64..."
}
```

### Detection Output
```javascript
msg = {
    payload: {
        image_id: "uuid",
        detection: {
            node_id: "template_match_1",
            name: "Screw Check",
            found: true,
            score: 0.92,
            matches: [...]
        }
    },
    detections: [...]  // Accumulated detections
}
```

### Merger Output
```javascript
msg = {
    payload: {
        result: "PASS",  // or "FAIL"
        all_detections: [...],
        summary: {
            total_checks: 3,
            passed: 2,
            failed: 1
        },
        failed_checks: ["Hole"]
    }
}
}
```

## Displaying Images

To display thumbnails use `node-red-contrib-image-output`:

1. Connect image node after detection node
2. Set property to `thumbnail` or `msg.thumbnail`
3. Thumbnails will be displayed directly in the flow

## Dashboard

To create dashboard:

```bash
npm install node-red-dashboard
```

Then use dashboard nodes for:
- Trigger button
- Result display
- Statistics graphs
- Live preview

## Troubleshooting

### Nodes not showing
- Restart Node-RED
- Check console for errors
- Verify installation: `npm list node-red-contrib-machine-vision-flow`

### Connection refused
- Verify Python backend is running
- Check API URL in nodes (default: http://localhost:8000)

### Image not displaying
- Install `node-red-contrib-image-output`
- Check that msg contains `thumbnail` property

## Development

### Node structure

```
mv-node-name.js   // Node logic
mv-node-name.html // Node UI + help
```

### Adding new node

1. Create .js and .html files in appropriate directory
2. Add to package.json
3. Restart Node-RED

### Debug

In Node-RED settings.js:
```javascript
logging: {
    level: "debug"
}
```

## License

MIT