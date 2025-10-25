module.exports = function(RED) {
    const axios = require('axios');

    function MVArucoDetectNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.dictionary = config.dictionary || 'DICT_4X4_50';

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

                node.status({fill: "blue", shape: "dot", text: "detecting markers..."});

                // Extract ROI from payload (like color-detect does)
                let roi = null;
                if (msg.payload?.bounding_box) {
                    const bbox = msg.payload.bounding_box;
                    roi = {
                        x: bbox.x,
                        y: bbox.y,
                        width: bbox.width,
                        height: bbox.height
                    };
                } else if (msg.roi) {
                    roi = msg.roi;
                }

                // Prepare request
                const requestData = {
                    image_id: imageId,
                    dictionary: node.dictionary,
                    roi: roi,
                    params: {}
                };

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/vision/aruco-detect`,
                    requestData,
                    {
                        timeout: 30000,
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }
                );

                const result = response.data;

                // 0 markers = send nothing
                if (!result.objects || result.objects.length === 0) {
                    node.status({
                        fill: "yellow",
                        shape: "ring",
                        text: `no markers found | ${result.processing_time_ms}ms`
                    });
                    done();
                    return;
                }

                // Send N messages for N markers
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
                        area: obj.area,
                        perimeter: obj.perimeter,
                        rotation: obj.rotation,
                        thumbnail: result.thumbnail_base64,  // Same for all
                        properties: obj.properties
                    };

                    // Set reference_object for first marker (primary reference)
                    if (i === 0) {
                        outputMsg.reference_object = {
                            rotation: obj.rotation,
                            center: obj.center,
                            marker_id: obj.properties.marker_id,
                            object_type: obj.object_type
                        };
                    } else {
                        // Preserve reference_object from first marker
                        if (result.objects.length > 0) {
                            const firstMarker = result.objects[0];
                            outputMsg.reference_object = {
                                rotation: firstMarker.rotation,
                                center: firstMarker.center,
                                marker_id: firstMarker.properties.marker_id,
                                object_type: firstMarker.object_type
                            };
                        }
                    }

                    // Metadata in root
                    outputMsg.success = true;
                    outputMsg.processing_time_ms = result.processing_time_ms;
                    outputMsg.node_name = node.name || "ArUco Detection";

                    send(outputMsg);
                }

                node.status({
                    fill: "green",
                    shape: "dot",
                    text: `found ${result.objects.length} markers | ${result.processing_time_ms}ms`
                });

                done();

            } catch (error) {
                node.status({fill: "red", shape: "ring", text: "error"});

                let errorMessage = "ArUco detection failed: ";
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

    RED.nodes.registerType("mv-aruco-detect", MVArucoDetectNode);
}
