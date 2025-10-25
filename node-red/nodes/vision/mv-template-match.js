module.exports = function(RED) {
    const {
        setNodeStatus,
        createVisionObjectMessage,
        callVisionAPI,
        getImageId,
        getTimestamp
    } = require('../lib/vision-utils');

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

        // Set initial status
        setNodeStatus(node, 'ready');

        // Process input
        node.on('input', async function(msg, send, done) {
            // For Node-RED 1.0+ compatibility
            send = send || function() { node.send.apply(node, arguments) };
            done = done || function(err) { if(err) node.error(err, msg) };

            // Extract image_id using utility
            const imageId = getImageId(msg);
            if (!imageId) {
                node.error("No image_id provided", msg);
                setNodeStatus(node, 'error', 'missing image_id');
                return done(new Error("No image_id provided"));
            }

            // Get template ID
            const templateId = msg.templateId || node.templateId;
            if (!templateId) {
                node.error("No template_id configured", msg);
                setNodeStatus(node, 'error', 'missing template');
                return done(new Error("No template_id configured"));
            }

            // Prepare request
            // Map bounding_box from previous detection to roi parameter (INPUT constraint)
            const requestData = {
                image_id: imageId,
                template_id: templateId,
                method: node.method,
                threshold: node.threshold,
                roi: msg.payload?.bounding_box || null,  // Use bounding_box from VisionObject as roi constraint
                multi_scale: node.multiScale,
                scale_range: node.scaleRange
            };

            try {
                // Call API with unified error handling
                const result = await callVisionAPI({
                    node: node,
                    endpoint: '/api/vision/template-match',
                    requestData: requestData,
                    apiUrl: node.apiUrl,
                    done: done
                });

                // 0 objects = send nothing
                if (!result.objects || result.objects.length === 0) {
                    setNodeStatus(node, 'no_results', 'not found', result.processing_time_ms);
                    done();
                    return;
                }

                // Send N messages for N objects using utility function
                const timestamp = getTimestamp(msg);

                for (let i = 0; i < result.objects.length; i++) {
                    const obj = result.objects[i];

                    // Use utility to create standardized VisionObject message
                    const outputMsg = createVisionObjectMessage(
                        obj,
                        imageId,
                        timestamp,
                        result.thumbnail_base64,
                        msg,
                        RED
                    );

                    // Add metadata in root
                    outputMsg.success = true;
                    outputMsg.processing_time_ms = result.processing_time_ms;
                    outputMsg.node_name = node.name || "Template Match";

                    send(outputMsg);
                }

                // Update status with count
                const countMsg = `${result.objects.length} match${result.objects.length > 1 ? 'es' : ''}`;
                setNodeStatus(node, 'success', countMsg, result.processing_time_ms);

                done();

            } catch (error) {
                // Error already handled by callVisionAPI
                // Just ensure done is called (may have been called already)
                if (!error.handledByUtils) {
                    done(error);
                }
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
