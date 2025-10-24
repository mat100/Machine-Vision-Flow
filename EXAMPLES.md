# Machine Vision Flow - Examples

This document provides practical examples of common workflows using the unified message format.

## Example 1: Simple Template Matching

Capture image and find template matches.

```
[Inject] → [Camera Capture] → [Template Match] → [Debug]
```

**Flow behavior:**
- Camera Capture sends 1 message with full image as VisionObject
- Template Match receives image_id from msg.payload
- Template Match sends N messages (one per match found)
- Debug shows each match individually

## Example 2: Edge Detection with Filtering

Find contours and process only large ones.

```
[Inject] → [Camera Capture] → [Edge Detect] → [Switch] → [Debug]
                                                    ↓
                                              [Filter by area]
```

**Switch node configuration:**
```javascript
// Pass only objects with area > 5000
msg.payload.area > 5000
```

**Flow behavior:**
- Edge Detect sends N messages for N contours
- Switch filters based on msg.payload.area
- Only large contours pass through

## Example 3: ROI-based Color Analysis

Detect edges, then analyze color in each contour's bounding box.

```
[Inject] → [Camera Capture] → [Edge Detect] → [Color Detect] → [Function] → [Debug]
                                                                     ↓
                                                            [Count red regions]
```

**Function node (count red):**
```javascript
// Initialize counter in flow context
let redCount = flow.get('redCount') || 0;

// Check if dominant color is red
if (msg.payload.properties.dominant_color === 'red') {
    redCount++;
}

flow.set('redCount', redCount);
msg.payload.red_total = redCount;

return msg;
```

**Flow behavior:**
- Camera Capture: 1 message with full image
- Edge Detect: N messages (one per contour)
- Color Detect: Automatically analyzes msg.payload.bounding_box from each contour
- Color Detect: Sends 1 message per contour if color matches
- Function: Counts red regions across all messages
- Debug: Shows each red region

**Important:** Color Detect automatically uses `msg.payload.bounding_box` if present!

## Example 4: Parallel Detection with Join

Run multiple detections simultaneously and collect results.

```
                    ┌→ [Template Match "Hole"] →┐
[Camera Capture] → ├→ [Template Match "Pin"]  →├→ [Join] → [Function] → [Debug]
                    └→ [Edge Detect]           →┘              ↓
                                                         [Decide PASS/FAIL]
```

**Join node configuration:**
- Mode: Manual
- Combine each: msg.payload
- To create: Array
- After: 3 messages (or timeout)
- Group by: msg.payload.image_id

**Function node (decide):**
```javascript
// msg.payload is now array of all VisionObjects
const objects = msg.payload;

let holeFound = false;
let pinFound = false;
let edgeCount = 0;

for (let obj of objects) {
    if (obj.object_type === 'template_match') {
        if (obj.properties.template_name === 'Hole') {
            holeFound = true;
        }
        if (obj.properties.template_name === 'Pin') {
            pinFound = true;
        }
    }
    if (obj.object_type === 'edge_contour') {
        edgeCount++;
    }
}

// Decision logic
const result = holeFound && pinFound && edgeCount >= 4 ? "PASS" : "FAIL";

msg.payload = {
    result: result,
    hole_found: holeFound,
    pin_found: pinFound,
    edge_count: edgeCount,
    image_id: objects[0].image_id
};

return msg;
```

**Flow behavior:**
- Camera Capture: 1 message broadcasted to 3 branches
- Template Match nodes: Each sends N messages (may be 0)
- Edge Detect: Sends N messages
- Join: Waits for all results, groups by image_id
- Function: Analyzes all objects and decides PASS/FAIL

## Example 5: Sequential Processing with Context

Process objects one at a time, maintaining state.

```
[Camera Capture] → [Edge Detect] → [Color Detect] → [Function] → [Debug]
                                                          ↓
                                                  [Track statistics]
```

**Function node (statistics):**
```javascript
// Get statistics from flow context
let stats = flow.get('stats') || {
    total_objects: 0,
    red_objects: 0,
    blue_objects: 0,
    other_objects: 0
};

// Update based on current object
stats.total_objects++;
const color = msg.payload.properties.dominant_color;

if (color === 'red') {
    stats.red_objects++;
} else if (color === 'blue') {
    stats.blue_objects++;
} else {
    stats.other_objects++;
}

flow.set('stats', stats);

// Add stats to message
msg.payload.statistics = stats;

return msg;
```

**Flow behavior:**
- Each object flows through independently
- Function accumulates statistics across all objects
- Debug shows individual objects with running totals

## Key Patterns

### Pattern: Filter and Process
```
[Detection] → [Switch: area > 1000] → [Color Detect]
                    ↓
              [Switch: area < 1000] → [Debug: "too small"]
```

### Pattern: Conditional Branching
```
[Edge Detect] → [Switch]
                    ├→ [port 1: vertex_count === 4] → [Debug: "Rectangle"]
                    ├→ [port 2: vertex_count === 3] → [Debug: "Triangle"]
                    └→ [port 3: otherwise] → [Debug: "Other shape"]
```

### Pattern: Aggregate and Decide
```
[Multiple Detections] → [Join by image_id] → [Function: PASS/FAIL] → [MQTT Out]
```

## Message Structure Reference

All vision nodes use this format:

```javascript
msg.payload = {
    object_id: "contour_0",
    object_type: "edge_contour",
    image_id: "uuid",
    timestamp: "2025-10-24T10:30:00",
    bounding_box: {x: 100, y: 100, width: 50, height: 50},
    center: {x: 125, y: 125},
    confidence: 0.95,
    area: 2500.0,
    perimeter: 200.0,
    thumbnail: "base64...",
    properties: {
        // Node-specific data
    }
}

// Metadata in message root:
msg.success = true;
msg.processing_time_ms = 45;
msg.node_name = "Edge Detection";
```

## Important Notes

1. **No empty messages**: If a detection node finds 0 objects, it sends nothing
2. **One object per message**: N objects = N separate messages
3. **Automatic ROI**: Color Detect auto-uses `msg.payload.bounding_box` if present
4. **Join for aggregation**: Use Join node to collect multiple messages
5. **Context for state**: Use flow/global context to track data across messages
