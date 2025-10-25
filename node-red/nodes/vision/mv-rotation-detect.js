module.exports = function(RED) {
    const axios = require('axios');

    function MVRotationDetectNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.method = config.method || 'min_area_rect';
        node.angleRange = config.angleRange || '0_360';

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

                // Get contour from message
                const contour = msg.payload?.contour;
                if (!contour || !Array.isArray(contour)) {
                    throw new Error("No contour found in msg.payload.contour");
                }

                node.status({fill: "blue", shape: "dot", text: "analyzing rotation..."});

                // Prepare request
                const requestData = {
                    image_id: imageId,
                    contour: contour,
                    method: node.method,
                    angle_range: node.angleRange,
                    roi: msg.payload?.bounding_box || null
                };

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/vision/rotation-detect`,
                    requestData,
                    {
                        timeout: 30000,
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }
                );

                const result = response.data;

                if (!result.objects || result.objects.length === 0) {
                    throw new Error("No rotation analysis result");
                }

                const obj = result.objects[0];
                const timestamp = msg.payload?.timestamp || new Date().toISOString();

                // Build output message - preserve original payload and add rotation
                const outputMsg = RED.util.cloneMessage(msg);

                // Update payload with rotation information
                outputMsg.payload.rotation = obj.rotation;
                outputMsg.payload.rotation_confidence = obj.confidence;
                outputMsg.payload.properties = {
                    ...outputMsg.payload.properties,
                    rotation_method: obj.properties.method,
                    rotation_angle_range: obj.properties.angle_range,
                    absolute_angle: obj.properties.absolute_angle
                };

                // Calculate relative rotation if reference_object exists
                if (msg.reference_object && typeof msg.reference_object.rotation === 'number') {
                    let relativeAngle = obj.rotation - msg.reference_object.rotation;

                    // Normalize based on angle range setting
                    if (node.angleRange === '0_360') {
                        while (relativeAngle < 0) relativeAngle += 360;
                        while (relativeAngle >= 360) relativeAngle -= 360;
                    } else if (node.angleRange === '-180_180') {
                        while (relativeAngle < -180) relativeAngle += 360;
                        while (relativeAngle > 180) relativeAngle -= 360;
                    } else if (node.angleRange === '0_180') {
                        while (relativeAngle < 0) relativeAngle += 180;
                        while (relativeAngle >= 180) relativeAngle -= 180;
                    }

                    outputMsg.payload.rotation_relative = relativeAngle;
                    outputMsg.payload.properties.reference_angle = msg.reference_object.rotation;
                    outputMsg.payload.properties.reference_marker_id = msg.reference_object.marker_id;
                }

                // Update thumbnail
                outputMsg.payload.thumbnail = result.thumbnail_base64;

                // Preserve reference_object for downstream nodes
                if (msg.reference_object) {
                    outputMsg.reference_object = msg.reference_object;
                }

                // Metadata in root
                outputMsg.success = true;
                outputMsg.processing_time_ms = result.processing_time_ms;
                outputMsg.node_name = node.name || "Rotation Detection";

                // Status message
                let statusText = `${obj.rotation.toFixed(1)}°`;
                if (outputMsg.payload.rotation_relative !== undefined) {
                    statusText += ` (Δ${outputMsg.payload.rotation_relative.toFixed(1)}°)`;
                }
                statusText += ` | ${result.processing_time_ms}ms`;

                node.status({
                    fill: "green",
                    shape: "dot",
                    text: statusText
                });

                send(outputMsg);
                done();

            } catch (error) {
                node.status({fill: "red", shape: "ring", text: "error"});

                let errorMessage = "Rotation detection failed: ";
                if (error.response) {
                    errorMessage += error.response.data?.detail || error.response.statusText;
                    node.error(errorMessage, msg);
                } else if (error.request) {
                    errorMessage += "No response from server";
                    node.error(errorMessage, msg);
                } else {
                    errorMessage += error.message;
                    node.error(errorMessage, msg);
                }

                done(error);
            }
        });

        node.on('close', function() {
            node.status({});
        });
    }

    RED.nodes.registerType("mv-rotation-detect", MVRotationDetectNode);
}
