import { calculations } from './calculations.js';

// Setup message listener for the worker
self.onmessage = async function (e) {
    const { type, payload } = e.data;

    try {
        if (type === 'INIT') {
            const { psychroLibPath, merkelLibPath } = payload;
            // The worker needs to initialize the binary tables independently of the main thread
            await calculations.init(psychroLibPath, merkelLibPath);
            self.postMessage({ type: 'READY' });
        }
        else if (type === 'CALCULATE_CURVE') {
            const { inputs, flowPercent, requestId } = payload;

            const data = [];
            const wbtStart = Number(inputs.axXMin);
            const wbtEnd = Number(inputs.axXMax);
            if (!Number.isFinite(wbtStart) || !Number.isFinite(wbtEnd) || wbtStart >= wbtEnd) {
                throw new Error('Invalid axis range for curve calculation.');
            }

            // Perform the heavy number-crunching isolated away from the Main UI thread
            for (let wbt = wbtStart; wbt <= wbtEnd; wbt += 0.25) {
                const point = { wbt: parseFloat(wbt.toFixed(2)) };
                const cwt80 = calculations.findCWT(inputs, wbt, 80, flowPercent);
                const cwt100 = calculations.findCWT(inputs, wbt, 100, flowPercent);
                const cwt120 = calculations.findCWT(inputs, wbt, 120, flowPercent);

                if (!isNaN(cwt80) && !isNaN(cwt100) && !isNaN(cwt120)) {
                    point.range80 = cwt80;
                    point.range100 = cwt100;
                    point.range120 = cwt120;
                    data.push(point);
                }
            }

            self.postMessage({
                type: 'CURVE_RESULT',
                payload: { flowPercent, data, requestId }
            });
        }
    } catch (error) {
        self.postMessage({
            type: 'ERROR',
            payload: { message: error?.message || 'Worker calculation failed.' }
        });
    }
};
