module.exports = function(RED) {
    const axios = require('axios');

    function MVColorDetectNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.expectedColor = config.expectedColor || '';  // Empty = any color
        node.minPercentage = parseFloat(config.minPercentage) || 50.0;
        node.method = config.method || 'histogram';
        node.useContourMask = config.useContourMask !== false;  // Default true

        node.status({fill: "grey", shape: "ring", text: "ready"});

        node.on('input', async function(msg, send, done) {
            send = send || function() { node.send.apply(node, arguments) };
            done = done || function(err) { if(err) node.error(err, msg) };

            try {
                // Get image_id from message
                const imageId = msg.image_id || msg.payload?.image_id;
                if (!imageId) {
                    throw new Error("No image_id in message");
                }

                node.status({fill: "blue", shape: "dot", text: "detecting color..."});

                // Get ROI from payload.bounding_box (from previous detection) or explicit msg.roi
                let roi = null;
                let contour = null;
                if (msg.payload?.bounding_box) {
                    roi = msg.payload.bounding_box;
                    contour = msg.payload.contour;  // Extract contour from edge detection
                } else if (msg.roi) {
                    roi = msg.roi;
                }

                // Build request
                const requestData = {
                    image_id: imageId,
                    roi: roi,
                    contour: contour,
                    use_contour_mask: node.useContourMask,
                    expected_color: node.expectedColor || null,
                    min_percentage: node.minPercentage,
                    method: node.method
                };

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/vision/color-detect`,
                    requestData,
                    {
                        timeout: 30000,
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }
                );

                const result = response.data;

                // 0 objects = send nothing (color not found or doesn't match)
                if (!result.objects || result.objects.length === 0) {
                    // Get actual color from properties if mismatch
                    const actualColor = node.expectedColor ? 'mismatch' : 'none';
                    node.status({
                        fill: "yellow",
                        shape: "ring",
                        text: actualColor
                    });
                    done();
                    return;
                }

                // Color detection returns exactly 1 object
                const obj = result.objects[0];
                const timestamp = msg.payload?.timestamp || new Date().toISOString();

                // Get dominant color for status
                const dominantColor = obj.properties.dominant_color || 'unknown';
                const confidence = (obj.confidence * 100).toFixed(1);

                // Build VisionObject in payload
                msg.payload = {
                    object_id: obj.object_id,
                    object_type: obj.object_type,
                    image_id: imageId,
                    timestamp: timestamp,
                    bounding_box: obj.bounding_box,
                    center: obj.center,
                    confidence: obj.confidence,
                    thumbnail: result.thumbnail_base64,
                    properties: obj.properties
                };

                // Metadata in root
                msg.success = true;
                msg.processing_time_ms = result.processing_time_ms;
                msg.node_name = node.name || "Color Detection";

                // Update status
                const statusText = node.expectedColor
                    ? `✓ ${dominantColor} (${confidence}%)`
                    : `${dominantColor} (${confidence}%)`;
                node.status({
                    fill: "green",
                    shape: "dot",
                    text: statusText
                });

                send(msg);
                done();

            } catch (error) {
                const errorMsg = error.response?.data?.detail || error.message;
                node.error(`Color detection failed: ${errorMsg}`, msg);
                node.status({fill: "red", shape: "ring", text: "error"});
                done(error);
            }
        });

        node.on('close', function() {
            node.status({});
        });
    }

    RED.nodes.registerType("mv-color-detect", MVColorDetectNode);
}
