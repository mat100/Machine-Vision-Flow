module.exports = function(RED) {
    const axios = require('axios');

    function MVTemplateMatchNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.templateId = config.templateId;
        node.templateSource = config.templateSource || 'library';
        node.threshold = parseFloat(config.threshold) || 0.8;
        node.method = config.method || 'TM_CCOEFF_NORMED';
        node.roiEnabled = config.roiEnabled || false;
        node.roi = config.roi || {};
        node.multiScale = config.multiScale || false;
        node.scaleRange = config.scaleRange || [0.8, 1.2];

        // Status
        node.status({fill: "grey", shape: "ring", text: "ready"});

        // Process input
        node.on('input', async function(msg, send, done) {
            // For Node-RED 1.0+ compatibility
            send = send || function() { node.send.apply(node, arguments) };
            done = done || function(err) { if(err) node.error(err, msg) };

            // Check for image_id
            const imageId = msg.image_id || msg.payload?.image_id;
            if (!imageId) {
                node.error("No image_id provided", msg);
                node.status({fill: "red", shape: "dot", text: "missing image_id"});
                return done(new Error("No image_id provided"));
            }

            // Get template ID
            const templateId = msg.templateId || node.templateId;
            if (!templateId) {
                node.error("No template_id configured", msg);
                node.status({fill: "red", shape: "dot", text: "missing template"});
                return done(new Error("No template_id configured"));
            }

            node.status({fill: "blue", shape: "dot", text: "matching..."});

            try {
                // Prepare request
                const request = {
                    image_id: imageId,
                    template_id: templateId,
                    method: node.method,
                    threshold: node.threshold,
                    multi_scale: node.multiScale,
                    scale_range: node.scaleRange
                };

                // Add ROI if enabled
                if (node.roiEnabled && node.roi) {
                    request.roi = {
                        x: parseInt(node.roi.x) || 0,
                        y: parseInt(node.roi.y) || 0,
                        width: parseInt(node.roi.width) || 100,
                        height: parseInt(node.roi.height) || 100
                    };
                }

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/vision/template-match`,
                    request
                );

                if (response.data.success) {
                    // Add detection result to message
                    const detection = {
                        node_id: node.id,
                        name: config.name || "Template Match",
                        type: "template_match",
                        template_id: templateId,
                        found: response.data.found,
                        matches: response.data.matches,
                        processing_time_ms: response.data.processing_time_ms
                    };

                    // Build output message
                    msg.payload = {
                        image_id: imageId,
                        thumbnail_base64: response.data.thumbnail_base64,
                        detection: detection
                    };

                    // Add to detection chain
                    if (!msg.detections) {
                        msg.detections = [];
                    }
                    msg.detections.push(detection);

                    // Update thumbnail with overlay
                    msg.thumbnail = response.data.thumbnail_base64;

                    // Set status
                    const statusText = response.data.found
                        ? `found: ${response.data.matches.length} match(es)`
                        : "not found";
                    const statusColor = response.data.found ? "green" : "yellow";

                    node.status({
                        fill: statusColor,
                        shape: "dot",
                        text: statusText
                    });

                    send(msg);
                    done();
                } else {
                    throw new Error('Template matching failed');
                }

            } catch (error) {
                const errorMsg = error.response?.data?.detail || error.message;
                node.error(`Template matching failed: ${errorMsg}`, msg);
                node.status({fill: "red", shape: "dot", text: "matching failed"});

                // Still pass the message but mark as failed
                if (!msg.detections) {
                    msg.detections = [];
                }
                msg.detections.push({
                    node_id: node.id,
                    name: config.name || "Template Match",
                    type: "template_match",
                    found: false,
                    error: errorMsg
                });

                send(msg);
                done(error);
            }
        });

        // Clean up
        node.on('close', function(done) {
            node.status({});
            done();
        });
    }

    RED.nodes.registerType("mv-template-match", MVTemplateMatchNode);
}