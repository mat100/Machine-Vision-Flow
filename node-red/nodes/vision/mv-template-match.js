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
                // Map bounding_box from previous detection to roi parameter
                const request = {
                    image_id: imageId,
                    template_id: templateId,
                    method: node.method,
                    threshold: node.threshold,
                    roi: msg.payload?.bounding_box || null,  // Use bounding_box from VisionObject as roi constraint
                    multi_scale: node.multiScale,
                    scale_range: node.scaleRange
                };

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/vision/template-match`,
                    request
                );

                const result = response.data;

                // 0 objects = send nothing
                if (!result.objects || result.objects.length === 0) {
                    node.status({
                        fill: "yellow",
                        shape: "ring",
                        text: `not found | ${result.processing_time_ms}ms`
                    });
                    done();
                    return;
                }

                // Send N messages for N objects
                const timestamp = msg.payload?.timestamp || new Date().toISOString();

                for (let i = 0; i < result.objects.length; i++) {
                    const obj = result.objects[i];
                    const outputMsg = RED.util.cloneMessage(msg);

                    // Build VisionObject in payload
                    outputMsg.payload = {
                        object_id: obj.object_id,
                        object_type: obj.object_type,
                        image_id: imageId,
                        timestamp: timestamp,
                        bounding_box: obj.bounding_box,
                        center: obj.center,
                        confidence: obj.confidence,
                        thumbnail: result.thumbnail_base64,  // MVP: same for all
                        properties: obj.properties
                    };

                    // Metadata in root
                    outputMsg.success = true;
                    outputMsg.processing_time_ms = result.processing_time_ms;
                    outputMsg.node_name = node.name || "Template Match";

                    send(outputMsg);
                }

                node.status({
                    fill: "green",
                    shape: "dot",
                    text: `sent ${result.objects.length} messages | ${result.processing_time_ms}ms`
                });

                done();

            } catch (error) {
                const errorMsg = error.response?.data?.detail || error.message;
                node.error(`Template matching failed: ${errorMsg}`, msg);
                node.status({fill: "red", shape: "ring", text: "error"});
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
