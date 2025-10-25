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
                // Get image_id from message payload
                const imageId = msg.payload?.image_id;
                if (!imageId) {
                    throw new Error("No image_id in msg.payload");
                }

                node.status({fill: "blue", shape: "dot", text: "detecting edges..."});

                // Prepare request with explicit fields
                const requestData = {
                    image_id: imageId,
                    method: node.method,
                    // Map bounding_box from previous detection to roi parameter
                    roi: msg.payload?.bounding_box || null,
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

                // 0 objects = send nothing
                if (!result.objects || result.objects.length === 0) {
                    node.status({
                        fill: "yellow",
                        shape: "ring",
                        text: `no edges found | ${result.processing_time_ms}ms`
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
                        area: obj.area,
                        perimeter: obj.perimeter,
                        thumbnail: result.thumbnail_base64,  // MVP: same for all
                        properties: obj.properties,
                        contour: obj.contour || obj.raw_contour  // Include contour points (support both names)
                    };

                    // Metadata in root
                    outputMsg.success = true;
                    outputMsg.processing_time_ms = result.processing_time_ms;
                    outputMsg.node_name = node.name || "Edge Detection";

                    send(outputMsg);
                }

                node.status({
                    fill: "green",
                    shape: "dot",
                    text: `sent ${result.objects.length} messages | ${result.processing_time_ms}ms`
                });

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
