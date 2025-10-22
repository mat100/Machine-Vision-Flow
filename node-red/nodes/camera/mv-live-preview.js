/**
 * Machine Vision Live Preview Node
 * Provides MJPEG stream URL for camera live preview
 */

module.exports = function(RED) {
    function MVLivePreviewNode(config) {
        RED.nodes.createNode(this, config);

        const node = this;
        const apiUrl = config.apiUrl || 'http://localhost:8000';

        // Store configuration
        node.cameraId = config.cameraId || 'test';
        node.autoStart = config.autoStart || false;
        node.showControls = config.showControls || true;

        // Stream state
        node.streamActive = false;
        node.streamUrl = null;

        // Set initial status
        this.status({ fill: "grey", shape: "ring", text: "Ready" });

        // Start stream function
        function startStream(cameraId) {
            if (!cameraId) {
                node.error("No camera ID specified");
                node.status({ fill: "red", shape: "ring", text: "No camera" });
                return;
            }

            // Build MJPEG stream URL
            node.streamUrl = `${apiUrl}/api/camera/stream/${cameraId}`;
            node.streamActive = true;

            // Update status
            node.status({ fill: "green", shape: "dot", text: `Streaming: ${cameraId}` });

            // Send stream URL in message
            const msg = {
                payload: {
                    streaming: true,
                    camera_id: cameraId,
                    stream_url: node.streamUrl,
                    timestamp: new Date().toISOString()
                },
                stream_url: node.streamUrl,
                camera_id: cameraId
            };

            node.send(msg);
            node.log(`Started MJPEG stream for camera: ${cameraId}`);
        }

        // Stop stream function
        function stopStream() {
            if (node.streamActive && node.cameraId) {
                // Call stop endpoint
                const axios = require('axios');
                axios.post(`${apiUrl}/api/camera/stream/stop/${node.cameraId}`)
                    .then(response => {
                        node.log(`Stopped stream for camera: ${node.cameraId}`);
                    })
                    .catch(error => {
                        node.warn(`Failed to stop stream: ${error.message}`);
                    });
            }

            node.streamActive = false;
            node.streamUrl = null;
            node.status({ fill: "grey", shape: "ring", text: "Stopped" });

            // Send stop message
            const msg = {
                payload: {
                    streaming: false,
                    camera_id: node.cameraId,
                    timestamp: new Date().toISOString()
                },
                stream_url: null,  // Clear stream URL
                camera_id: node.cameraId
            };

            node.send(msg);
        }

        // Handle input messages
        node.on('input', function(msg) {
            // Check for control commands in message
            if (msg.payload) {
                // Start command
                if (msg.payload.command === 'start' || msg.payload.start === true) {
                    const cameraId = msg.payload.camera_id || msg.camera_id || node.cameraId;
                    startStream(cameraId);
                    return;
                }

                // Stop command
                if (msg.payload.command === 'stop' || msg.payload.stop === true) {
                    stopStream();
                    return;
                }

                // Camera selection
                if (msg.payload.camera_id) {
                    node.cameraId = msg.payload.camera_id;
                    if (node.streamActive) {
                        // Restart with new camera
                        stopStream();
                        setTimeout(() => startStream(node.cameraId), 500);
                    }
                    return;
                }
            }

            // Default action - toggle stream
            if (node.streamActive) {
                stopStream();
            } else {
                startStream(node.cameraId);
            }
        });

        // Auto-start if configured
        if (node.autoStart) {
            setTimeout(() => startStream(node.cameraId), 1000);
        }

        // Cleanup on node removal or redeploy
        node.on('close', function(done) {
            if (node.streamActive) {
                stopStream();
            }
            done();
        });
    }

    RED.nodes.registerType("mv-live-preview", MVLivePreviewNode);
};