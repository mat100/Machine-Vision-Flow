module.exports = function(RED) {
    const axios = require('axios');

    function MVCameraCaptureNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.cameraId = config.cameraId || 'test';
        node.apiUrl = config.apiUrl || 'http://localhost:8000';
        node.autoConnect = config.autoConnect || false;

        // Status
        node.status({fill: "grey", shape: "ring", text: "ready"});

        // Connect to camera on startup if autoConnect
        if (node.autoConnect && node.cameraId) {
            connectCamera();
        }

        // Connect to camera
        async function connectCamera() {
            try {
                const response = await axios.post(
                    `${node.apiUrl}/api/camera/connect`,
                    {
                        camera_id: node.cameraId,
                        resolution: config.resolution
                    }
                );

                if (response.data.success) {
                    node.status({fill: "green", shape: "dot", text: `connected: ${node.cameraId}`});
                    node.log(`Camera connected: ${node.cameraId}`);
                }
            } catch (error) {
                node.error(`Failed to connect camera: ${error.message}`);
                node.status({fill: "red", shape: "ring", text: "connection failed"});
            }
        }

        // Capture image on input
        node.on('input', async function(msg, send, done) {
            // For Node-RED 1.0+ compatibility
            send = send || function() { node.send.apply(node, arguments) };
            done = done || function(err) { if(err) node.error(err, msg) };

            node.status({fill: "blue", shape: "dot", text: "capturing..."});

            try {
                // Use camera ID from msg or config
                const cameraId = msg.cameraId || node.cameraId;

                // Capture image
                const response = await axios.post(
                    `${node.apiUrl}/api/camera/capture`,
                    null,
                    {
                        params: { camera_id: cameraId }
                    }
                );

                if (response.data.success) {
                    // Build output message
                    msg.payload = {
                        image_id: response.data.image_id,
                        timestamp: response.data.timestamp,
                        thumbnail_base64: response.data.thumbnail_base64,
                        metadata: response.data.metadata
                    };

                    // Store image_id for downstream nodes
                    msg.image_id = response.data.image_id;
                    msg.thumbnail = response.data.thumbnail_base64;

                    node.status({
                        fill: "green",
                        shape: "dot",
                        text: `captured: ${response.data.image_id.substring(0, 8)}...`
                    });

                    send(msg);
                    done();
                } else {
                    throw new Error('Capture failed');
                }

            } catch (error) {
                const errorMsg = error.response?.data?.detail || error.message;
                node.error(`Capture failed: ${errorMsg}`, msg);
                node.status({fill: "red", shape: "dot", text: "capture failed"});
                done(error);
            }
        });

        // Clean up on close
        node.on('close', async function(done) {
            // Disconnect camera if needed
            if (node.cameraId && node.cameraId !== 'test') {
                try {
                    await axios.delete(`${node.apiUrl}/api/camera/disconnect/${node.cameraId}`);
                    node.log(`Camera disconnected: ${node.cameraId}`);
                } catch (error) {
                    // Ignore disconnect errors
                }
            }
            done();
        });
    }

    RED.nodes.registerType("mv-camera-capture", MVCameraCaptureNode);
}