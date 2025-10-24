module.exports = function(RED) {
    const axios = require('axios');

    function MVEdgeDetectNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.method = config.method || 'canny';
        node.cannyLow = config.cannyLow || 50;
        node.cannyHigh = config.cannyHigh || 150;
        node.sobelThreshold = config.sobelThreshold || 50;
        node.laplacianThreshold = config.laplacianThreshold || 30;

        // Preprocessing options
        node.blurEnabled = config.blurEnabled || false;
        node.blurKernel = config.blurKernel || 5;
        node.bilateralEnabled = config.bilateralEnabled || false;
        node.morphologyEnabled = config.morphologyEnabled || false;
        node.morphologyOperation = config.morphologyOperation || 'close';

        // Contour filters
        node.minContourArea = config.minContourArea || 10;
        node.maxContourArea = config.maxContourArea || 100000;
        node.maxContours = config.maxContours || 20;

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

                node.status({fill: "blue", shape: "dot", text: "detecting edges..."});

                // Prepare request
                const requestData = {
                    image_id: imageId,
                    method: node.method,
                    threshold1: node.cannyLow,
                    threshold2: node.cannyHigh
                };

                // Add preprocessing if enabled
                const preprocessing = {};
                if (node.blurEnabled) {
                    preprocessing.blur_enabled = true;
                    preprocessing.blur_kernel = parseInt(node.blurKernel) || 5;
                }
                if (node.bilateralEnabled) {
                    preprocessing.bilateral_enabled = true;
                }
                if (node.morphologyEnabled) {
                    preprocessing.morphology_enabled = true;
                    preprocessing.morphology_operation = node.morphologyOperation;
                }

                if (Object.keys(preprocessing).length > 0) {
                    requestData.preprocessing = preprocessing;
                }

                // Add parameters based on method
                const params = {
                    min_contour_area: parseInt(node.minContourArea) || 10,
                    max_contour_area: parseInt(node.maxContourArea) || 100000,
                    max_contours: parseInt(node.maxContours) || 20,
                    show_centers: true
                };

                if (node.method === 'canny') {
                    params.canny_low = node.cannyLow;
                    params.canny_high = node.cannyHigh;
                } else if (node.method === 'sobel') {
                    params.sobel_threshold = node.sobelThreshold;
                } else if (node.method === 'laplacian') {
                    params.laplacian_threshold = node.laplacianThreshold;
                }

                requestData.params = params;

                // Call API
                const response = await axios.post(
                    `${node.apiUrl}/api/vision/edge-detect`,
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
                if (result.edges_found) {
                    node.status({
                        fill: "green",
                        shape: "dot",
                        text: `${result.contour_count} contours found`
                    });
                } else {
                    node.status({
                        fill: "yellow",
                        shape: "ring",
                        text: "no edges found"
                    });
                }

                // Build detection object
                const detection = {
                    node_id: node.id,
                    name: node.name || "Edge Detection",
                    type: "edge_detection",
                    method: node.method,
                    params: {
                        method: node.method,
                        preprocessing: preprocessing
                    },
                    duration_ms: result.processing_time_ms,
                    result: {
                        found: result.edges_found,
                        contour_count: result.contour_count,
                        edge_pixels: result.edge_pixels,
                        edge_ratio: result.edge_ratio,
                        contours: result.contours || []
                    }
                };

                // Add detection to message chain
                if (!msg.detections) {
                    msg.detections = [];
                }
                msg.detections.push(detection);

                // Update message
                msg.payload = {
                    image_id: imageId,
                    detection: detection,
                    thumbnail_base64: result.thumbnail_base64
                };

                // Add thumbnail for display
                if (result.thumbnail_base64) {
                    msg.thumbnail = result.thumbnail_base64;
                }

                send(msg);
                done();

            } catch (error) {
                node.status({fill: "red", shape: "ring", text: "error"});

                let errorMessage = "Edge detection failed: ";
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

    RED.nodes.registerType("mv-edge-detect", MVEdgeDetectNode);
}
