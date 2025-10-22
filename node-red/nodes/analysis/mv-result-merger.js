module.exports = function(RED) {
    function MVResultMergerNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        // Configuration
        node.inputCount = parseInt(config.inputCount) || 2;
        node.timeout = parseInt(config.timeout) || 1000;
        node.ruleType = config.ruleType || 'all_pass';
        node.minRequired = parseInt(config.minRequired) || 1;
        node.customRule = config.customRule || '';
        node.saveToHistory = config.saveToHistory || false;
        node.apiUrl = config.apiUrl || 'http://localhost:8000';

        // State
        node.pendingMessages = new Map();
        node.timeouts = new Map();

        // Status
        node.status({fill: "grey", shape: "ring", text: `waiting for ${node.inputCount} inputs`});

        // Process input
        node.on('input', function(msg, send, done) {
            // For Node-RED 1.0+ compatibility
            send = send || function() { node.send.apply(node, arguments) };
            done = done || function(err) { if(err) node.error(err, msg) };

            // Get correlation ID (use image_id as correlation)
            const correlationId = msg.image_id || msg.payload?.image_id;
            if (!correlationId) {
                node.error("No image_id for correlation", msg);
                return done(new Error("No image_id for correlation"));
            }

            // Initialize pending messages for this correlation
            if (!node.pendingMessages.has(correlationId)) {
                node.pendingMessages.set(correlationId, []);

                // Set timeout
                const timeoutId = setTimeout(() => {
                    node.processResults(correlationId, send, done, true);
                }, node.timeout);
                node.timeouts.set(correlationId, timeoutId);
            }

            // Add message to pending
            const pending = node.pendingMessages.get(correlationId);
            pending.push(msg);

            // Update status
            node.status({
                fill: "blue",
                shape: "dot",
                text: `${correlationId.substring(0, 8)}: ${pending.length}/${node.inputCount}`
            });

            // Check if we have all inputs
            if (pending.length >= node.inputCount) {
                // Clear timeout
                const timeoutId = node.timeouts.get(correlationId);
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    node.timeouts.delete(correlationId);
                }

                // Process results
                node.processResults(correlationId, send, done, false);
            }
        });

        // Process accumulated results
        node.processResults = function(correlationId, send, done, isTimeout) {
            const messages = node.pendingMessages.get(correlationId) || [];

            if (messages.length === 0) {
                return;
            }

            // Collect all detections
            const allDetections = [];
            let thumbnail = null;

            messages.forEach(msg => {
                // Get detections from each message
                if (msg.detections && Array.isArray(msg.detections)) {
                    allDetections.push(...msg.detections);
                } else if (msg.payload?.detection) {
                    allDetections.push(msg.payload.detection);
                }

                // Get latest thumbnail
                if (msg.thumbnail || msg.payload?.thumbnail_base64) {
                    thumbnail = msg.thumbnail || msg.payload.thumbnail_base64;
                }
            });

            // Apply decision rule
            let result = 'FAIL';
            let failedChecks = [];

            switch (node.ruleType) {
                case 'all_pass':
                    result = allDetections.every(d => d.found) ? 'PASS' : 'FAIL';
                    failedChecks = allDetections.filter(d => !d.found).map(d => d.name || d.node_id);
                    break;

                case 'any_pass':
                    result = allDetections.some(d => d.found) ? 'PASS' : 'FAIL';
                    failedChecks = allDetections.filter(d => !d.found).map(d => d.name || d.node_id);
                    break;

                case 'min_count':
                    const passedCount = allDetections.filter(d => d.found).length;
                    result = passedCount >= node.minRequired ? 'PASS' : 'FAIL';
                    failedChecks = allDetections.filter(d => !d.found).map(d => d.name || d.node_id);
                    break;

                case 'custom':
                    try {
                        // Create function from custom rule
                        const evalFunc = new Function('detections', 'messages', node.customRule);
                        const customResult = evalFunc(allDetections, messages);
                        result = customResult ? 'PASS' : 'FAIL';
                    } catch (error) {
                        node.error(`Custom rule error: ${error.message}`);
                        result = 'ERROR';
                    }
                    break;
            }

            // Create summary
            const summary = {
                total_checks: allDetections.length,
                passed: allDetections.filter(d => d.found).length,
                failed: allDetections.filter(d => !d.found).length,
                success_rate: allDetections.length > 0
                    ? (allDetections.filter(d => d.found).length / allDetections.length)
                    : 0
            };

            // Build output message
            const outputMsg = {
                payload: {
                    image_id: correlationId,
                    all_detections: allDetections,
                    summary: summary,
                    result: result,
                    failed_checks: failedChecks,
                    timeout: isTimeout
                },
                image_id: correlationId,
                thumbnail: thumbnail
            };

            // Update status
            const statusColor = result === 'PASS' ? 'green' : 'red';
            const statusText = `${result}: ${summary.passed}/${summary.total_checks}`;
            node.status({fill: statusColor, shape: "dot", text: statusText});

            // Clean up
            node.pendingMessages.delete(correlationId);
            node.timeouts.delete(correlationId);

            // Send result
            send(outputMsg);

            // Save to history if configured
            if (node.saveToHistory && node.apiUrl) {
                node.saveToHistoryBuffer(correlationId, result, allDetections, thumbnail);
            }

            done();
        };

        // Save to history buffer
        node.saveToHistoryBuffer = async function(imageId, result, detections, thumbnail) {
            try {
                const axios = require('axios');

                // This would normally call the history API
                // For now, it's a placeholder
                node.log(`Would save to history: ${imageId} - ${result}`);

            } catch (error) {
                node.error(`Failed to save to history: ${error.message}`);
            }
        };

        // Clean up
        node.on('close', function(done) {
            // Clear all timeouts
            node.timeouts.forEach(timeout => clearTimeout(timeout));
            node.timeouts.clear();
            node.pendingMessages.clear();
            node.status({});
            done();
        });
    }

    RED.nodes.registerType("mv-result-merger", MVResultMergerNode);
}