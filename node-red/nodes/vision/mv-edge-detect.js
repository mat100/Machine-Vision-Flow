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

                // Prepare request with explicit fields
                const requestData = {
                    image_id: imageId,
                    method: node.method,
                    // Canny parameters
                    canny_low: parseInt(node.cannyLow) || 50,
                    canny_high: parseInt(node.cannyHigh) || 150,
                    // Sobel parameters
                    sobel_threshold: parseInt(node.sobelThreshold) || 50,
                    sobel_kernel: 3,
                    // Laplacian parameters
                    laplacian_threshold: parseInt(node.laplacianThreshold) || 30,
                    laplacian_kernel: 3,
                    // Prewitt parameters
                    prewitt_threshold: 50,
                    // Scharr parameters
                    scharr_threshold: 50,
                    // Morphological gradient parameters
                    morph_threshold: 30,
                    morph_kernel: 3,
                    // Contour filtering parameters
                    min_contour_area: parseInt(node.minContourArea) || 10,
                    max_contour_area: parseInt(node.maxContourArea) || 100000,
                    min_contour_perimeter: 0,
                    max_contour_perimeter: 999999,
                    max_contours: parseInt(node.maxContours) || 20,
                    show_centers: true,
                    // Preprocessing options
                    blur_enabled: node.blurEnabled || false,
                    blur_kernel: parseInt(node.blurKernel) || 5,
                    bilateral_enabled: node.bilateralEnabled || false,
                    bilateral_d: 9,
                    bilateral_sigma_color: 75,
                    bilateral_sigma_space: 75,
                    morphology_enabled: node.morphologyEnabled || false,
                    morphology_operation: node.morphologyOperation || 'close',
                    morphology_kernel: 3,
                    equalize_enabled: false
                };

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
                        min_contour_area: requestData.min_contour_area,
                        max_contour_area: requestData.max_contour_area
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
