// worker.js - Re-written to act as an async proxy to the secure Python Backend

self.onmessage = async function (e) {
    const { type, payload } = e.data;

    try {
        if (type === 'INIT') {
            // Signal to main thread that we are ready
            self.postMessage({ type: 'READY' });
        }
        else if (type === 'CALCULATE_CURVE') {
            const { inputs, flowPercent, requestId } = payload;

            // Make an HTTP POST to the new secure Python API wrapper
            const response = await fetch('/api/calculate/curves', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    inputs: {
                        axXMin: Number(inputs.axXMin),
                        axXMax: Number(inputs.axXMax),
                        lgRatio: Number(inputs.lgRatio),
                        constantC: Number(inputs.constantC),
                        constantM: Number(inputs.constantM),
                        designHWT: Number(inputs.designHWT),
                        designCWT: Number(inputs.designCWT)
                    },
                    flowPercent: flowPercent
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to calculate curve on server.');
            }

            const result = await response.json();
            const data = result.data;

            self.postMessage({
                type: 'CURVE_RESULT',
                payload: { flowPercent, data, requestId }
            });
        }
    } catch (error) {
        self.postMessage({
            type: 'ERROR',
            payload: { message: error?.message || 'Worker server calculation failed.' }
        });
    }
};
