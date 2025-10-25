module.exports = function(RED) {
    const axios = require('axios');

    function MVROIExtractNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.roi = config.roi || {x: 0, y: 0, width: 100, height: 100};

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

                node.status({fill: "blue", shape: "dot", text: "extracting ROI..."});

                // Prepare request
                const requestData = {
                    image_id: imageId,
                    roi: {
                        x: parseInt(node.roi.x) || 0,
                        y: parseInt(node.roi.y) || 0,
                        width: parseInt(node.roi.width) || 100,
                        height: parseInt(node.roi.height) || 100
                    }
                };

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/image/extract-roi`,
                    requestData,
                    {
                        timeout: 30000,
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }
                );

                const result = response.data;

                // Update status
                const processingTime = result.processing_time_ms || 0;
                node.status({
                    fill: "green",
                    shape: "dot",
                    text: `ROI extracted: ${requestData.roi.width}x${requestData.roi.height} | ${processingTime}ms`
                });

                // Update message with new image_id from extracted ROI
                msg.image_id = result.image_id;
                msg.thumbnail = result.thumbnail_base64;
                msg.payload = {
                    image_id: result.image_id,
                    thumbnail_base64: result.thumbnail_base64,
                    metadata: result.metadata,
                    source_image_id: imageId,
                    roi: requestData.roi
                };

                send(msg);
                done();

            } catch (error) {
                node.status({fill: "red", shape: "ring", text: "error"});

                let errorMessage = "ROI extraction failed: ";
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

    RED.nodes.registerType("mv-roi-extract", MVROIExtractNode);
}
