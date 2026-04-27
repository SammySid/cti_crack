// Native calculations removed for IP Security. Driven by Backend API now.
import { charts } from './charts.js';
import { bindEvents } from './ui/bind-events.js';
import { switchTab } from './ui/tabs.js';
import { setSidebarOpen, initMobileNavigation } from './ui/mobile-nav.js';
import { formatPsychroValue, calculatePsychrometrics } from './ui/psychro.js';
import { updateFilterUiState, syncFilterSettingsToUi, runFilterTool, bindFilterProcessAllToggle } from './ui/filter.js';
import { updateExportUiState, getDownloadFileName, downloadBlob, exportData } from './ui/export.js';
import { calculatePrediction } from './ui/prediction.js';

export const ui = {
    inputs: {
        companyName: 'SS Cooling tower LTD',
        engineerName: 'Suresh Sarma',
        projectName: 'IDCT Thermal Performance Curves',
        date: new Date().toISOString().split('T')[0],
        lgRatio: 1.7,
        designWBT: 28.6,
        designCWT: 33,
        designHWT: 43,
        designWaterFlow: 3860,
        constantC: 2.51,
        constantM: 0.66,
        axXMin: 18,
        axXMax: 30,
        axYMin: 25,
        axYMax: 38,
        offsetWbt20: 0.0,
        off90r80: 0.0,
        off90r100: 0.0,
        off90r120: 0.0,
        off100r80: 0.0,
        off100r100: 0.0,
        off100r120: 0.0,
        off110r80: 0.0,
        off110r100: 0.0,
        off110r120: 0.0
    },
    filterSettings: {
        sourcePath: '',
        startTime: '16:00',
        endTime: '17:00',
        processAll: false
    },
    workerReady: false,
    enginesReady: false,
    isPrinting: false,
    isCalculating: false,
    isExporting: false,
    isFiltering: false,
    isSidebarOpen: false,
    curveRequestId: 0,
    activeTab: 'thermal',
    curveData: { 90: [], 100: [], 110: [] },
    baseCurveData: null,
    lastCurveSignature: '',
    pendingFlows: new Set(),
    curveReadyResolvers: [],

    init: async () => {
        ui.loadInputs();
        ui.loadFilterSettings();
        ui.enginesReady = true;
        ui.bindEvents();

        // Setup the calculation Web Worker
        ui.worker = new Worker('./js/worker.js', { type: 'module' });

        // Listen for computation results
        ui.worker.onmessage = (e) => {
            if (e.data.type === 'READY') {
                ui.workerReady = true;
                ui.updateAll();
            } else if (e.data.type === 'ERROR') {
                ui.isCalculating = false;
                ui.resolveCurveWaiters(false);
                ui.updateExportUiState(e.data.payload?.message || 'Engine error. Please refresh and retry.');
            } else if (e.data.type === 'CURVE_RESULT') {
                const { flowPercent, data, requestId } = e.data.payload;
                if (requestId !== ui.curveRequestId) {
                    return;
                }

                const index = flowPercent === 90 ? 0 : flowPercent === 100 ? 1 : 2;
                ui.curveData[flowPercent] = data;
                ui.pendingFlows.delete(flowPercent);

                const hasOffsets = Object.keys(ui.inputs).some(k => (k.startsWith('offset') || k.startsWith('off')) && ui.inputs[k] !== 0);
                const titleText = hasOffsets ? 
                    [`Curve ${index + 1} (${flowPercent}% Flow)`, '(Safety Margins Applied)'] : 
                    `Curve ${index + 1} (${flowPercent}% Flow)`;

                charts.render(
                    `chart${index + 1}`,
                    data,
                    titleText,
                    ui.inputs.axXMin,
                    ui.inputs.axXMax,
                    ui.inputs.axYMin,
                    ui.inputs.axYMax,
                    ui.isPrinting || false
                );

                if (ui.pendingFlows.size === 0) {
                    ui.isCalculating = false;
                    ui.resolveCurveWaiters(true);
                    ui.updateExportUiState('Curves ready. Export is enabled.');
                    // Fetch base (no-offset) curves for comparison table if any offset is active
                    if (hasOffsets) {
                        ui.fetchAndRenderBaseComparison();
                    } else {
                        ui.baseCurveData = null;
                        ui.renderMarginComparison();
                    }
                } else {
                    const completed = 3 - ui.pendingFlows.size;
                    ui.updateExportUiState(`Calculating curves (${completed}/3 complete)...`);
                }
            }
        };
        ui.worker.onerror = (error) => {
            console.error('Worker runtime error', error);
            ui.isCalculating = false;
            ui.resolveCurveWaiters(false);
            ui.updateExportUiState('Engine crashed. Refresh the dashboard to recover.');
        };

        // Initialize worker databases
        ui.worker.postMessage({
            type: 'INIT',
            payload: { psychroLibPath: '../data/psychro_f_alt.bin', merkelLibPath: '../data/merkel_poly.bin' }
        });

        ui.updateExportUiState('Initializing calculation engine...');
    },

    saveInputs: () => {
        localStorage.setItem('sarma_thermal_inputs', JSON.stringify(ui.inputs));
    },

    loadInputs: () => {
        const saved = localStorage.getItem('sarma_thermal_inputs');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                // Merge saved values into defaults to handle schema updates
                ui.inputs = { ...ui.inputs, ...parsed };

                // Update DOM elements to reflect loaded values
                Object.keys(ui.inputs).forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        if (el.type === 'date') el.value = ui.inputs[id];
                        else el.value = ui.inputs[id];
                    }
                });
            } catch (e) {
                console.error('Error loading saved inputs', e);
            }
        }
    },

    saveFilterSettings: () => {
        localStorage.setItem('sarma_filter_settings', JSON.stringify(ui.filterSettings));
    },

    loadFilterSettings: () => {
        const saved = localStorage.getItem('sarma_filter_settings');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                ui.filterSettings = { ...ui.filterSettings, ...parsed };
            } catch (e) {
                console.error('Error loading filter settings', e);
            }
        }
    },

    debounce: (fn, ms) => {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), ms);
        };
    },

    bindEvents: () => bindEvents(ui),

    updateFastMetrics: async () => {
        const approach = ui.inputs.designCWT - ui.inputs.designWBT;
        const range = ui.inputs.designHWT - ui.inputs.designCWT;
        const supplyKaVL = ui.inputs.constantC * Math.pow(ui.inputs.lgRatio, -ui.inputs.constantM);

        document.getElementById('displaySupply').innerText = Number.isFinite(supplyKaVL) ? supplyKaVL.toFixed(5) : '--';
        document.getElementById('displayApproach').innerText = Number.isFinite(approach) ? approach.toFixed(2) : '--';
        document.getElementById('displayRange').innerText = Number.isFinite(range) ? range.toFixed(2) : '--';

        try {
            const resp = await fetch('/api/calculate/kavl', {
                method: 'POST',
                headers:{ 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wbt: ui.inputs.designWBT,
                    hwt: ui.inputs.designHWT,
                    cwt: ui.inputs.designCWT,
                    lg: ui.inputs.lgRatio
                })
            });
            if (resp.ok) {
                const res = await resp.json();
                document.getElementById('displayDemand').innerText = (res.valid && Number.isFinite(res.kavl)) ? res.kavl.toFixed(5) : '--';
            }
        } catch (err) {
            document.getElementById('displayDemand').innerText = '--';
        }

        // Sync Professional Print Header
        document.getElementById('printProject').innerText = ui.inputs.projectName;
        document.getElementById('printClient').innerText = ui.inputs.companyName;
        document.getElementById('printEngineer').innerText = ui.inputs.engineerName;
        document.getElementById('printDate').innerText = ui.inputs.date;
    },

    updateAll: () => {
        ui.updateFastMetrics();
        // Generate and update charts asynchronously via worker
        ui.updateCharts();
    },

    updateCharts: () => {
        if (!ui.workerReady) return;

        const flows = [90, 100, 110];
        const requestId = ++ui.curveRequestId;

        const axisInputs = ['axXMin', 'axXMax', 'axYMin', 'axYMax'];
        if (axisInputs.some((id) => Number.isNaN(ui.inputs[id]))) {
            ui.updateExportUiState('Axis values must be numeric.');
            return;
        }
        if (ui.inputs.axXMin >= ui.inputs.axXMax) {
            [ui.inputs.axXMin, ui.inputs.axXMax] = [ui.inputs.axXMax - 1, ui.inputs.axXMax];
        }
        if (ui.inputs.axYMin >= ui.inputs.axYMax) {
            [ui.inputs.axYMin, ui.inputs.axYMax] = [ui.inputs.axYMax - 1, ui.inputs.axYMax];
        }

        const curveSignature = JSON.stringify({
            lgRatio: ui.inputs.lgRatio,
            designWBT: ui.inputs.designWBT,
            designCWT: ui.inputs.designCWT,
            designHWT: ui.inputs.designHWT,
            designWaterFlow: ui.inputs.designWaterFlow,
            constantC: ui.inputs.constantC,
            constantM: ui.inputs.constantM,
            axXMin: ui.inputs.axXMin,
            axXMax: ui.inputs.axXMax,
            axYMin: ui.inputs.axYMin,
            axYMax: ui.inputs.axYMax,
            offsetWbt20: ui.inputs.offsetWbt20,
            off90r80: ui.inputs.off90r80,
            off90r100: ui.inputs.off90r100,
            off90r120: ui.inputs.off90r120,
            off100r80: ui.inputs.off100r80,
            off100r100: ui.inputs.off100r100,
            off100r120: ui.inputs.off100r120,
            off110r80: ui.inputs.off110r80,
            off110r100: ui.inputs.off110r100,
            off110r120: ui.inputs.off110r120,
            isPrinting: ui.isPrinting
        });
        if (ui.areCurvesReady() && ui.lastCurveSignature === curveSignature) {
            return;
        }
        ui.lastCurveSignature = curveSignature;

        ui.isCalculating = true;
        ui.curveData = { 90: [], 100: [], 110: [] };
        ui.pendingFlows = new Set(flows);
        ui.updateExportUiState('Calculating curves (0/3 complete)...');

        flows.forEach((flow) => {
            // Offload the massive iterative integration logic to a background worker
            // Prevents UI freezes on large resolution charts
            ui.worker.postMessage({
                type: 'CALCULATE_CURVE',
                payload: { inputs: ui.inputs, flowPercent: flow, requestId }
            });
        });
    },

    areCurvesReady: () => {
        return (
            ui.workerReady &&
            !ui.isCalculating &&
            ui.curveData[90].length > 0 &&
            ui.curveData[100].length > 0 &&
            ui.curveData[110].length > 0
        );
    },

    waitForCurves: (timeoutMs = 120000) => {
        if (ui.areCurvesReady()) {
            return Promise.resolve(true);
        }

        return new Promise((resolve, reject) => {
            const waiter = {
                complete: (success) => {
                    clearTimeout(timer);
                    resolve(success);
                }
            };

            const timer = setTimeout(() => {
                ui.curveReadyResolvers = ui.curveReadyResolvers.filter((w) => w !== waiter);
                reject(new Error('Timed out while waiting for curves to finish.'));
            }, timeoutMs);

            ui.curveReadyResolvers.push(waiter);
        });
    },

    resolveCurveWaiters: (success) => {
        const waiters = ui.curveReadyResolvers.splice(0);
        waiters.forEach((waiter) => waiter.complete(success));
    },

    updateExportUiState: (statusMessage = '') => updateExportUiState(ui, statusMessage),
    getDownloadFileName,
    downloadBlob,
    switchTab: (tabId) => switchTab(ui, tabId),
    updateFilterUiState: (message = '') => updateFilterUiState(ui, message),
    syncFilterSettingsToUi: () => syncFilterSettingsToUi(ui),
    formatPsychroValue,
    calculatePsychrometrics: () => calculatePsychrometrics(ui),
    calculatePrediction: () => calculatePrediction(ui),
    runFilterTool: () => runFilterTool(ui),
    bindFilterProcessAllToggle: () => bindFilterProcessAllToggle(),
    exportData: () => exportData(ui),
    setSidebarOpen: (open) => setSidebarOpen(ui, open),
    initMobileNavigation: () => initMobileNavigation(ui),

    // ── Margin Comparison Table ────────────────────────────────────────────
    fetchAndRenderBaseComparison: async () => {
        const OFFSET_KEYS = [
            'offsetWbt20',
            'off90r80',  'off90r100',  'off90r120',
            'off100r80', 'off100r100', 'off100r120',
            'off110r80', 'off110r100', 'off110r120'
        ];
        const baseInputs = { ...ui.inputs };
        OFFSET_KEYS.forEach(k => { baseInputs[k] = 0; });

        try {
            const results = await Promise.all([90, 100, 110].map(flow =>
                fetch('/api/calculate/curves', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ inputs: baseInputs, flowPercent: flow })
                }).then(r => r.json()).then(r => [flow, r.data])
            ));
            ui.baseCurveData = Object.fromEntries(results);
        } catch (e) {
            ui.baseCurveData = null;
        }
        ui.renderMarginComparison();
    },

    renderMarginComparison: () => {
        const el = document.getElementById('marginComparison');
        if (!el) return;

        const OFFSET_KEYS = [
            'offsetWbt20',
            'off90r80',  'off90r100',  'off90r120',
            'off100r80', 'off100r100', 'off100r120',
            'off110r80', 'off110r100', 'off110r120'
        ];
        const hasOffsets = OFFSET_KEYS.some(k => ui.inputs[k] !== 0);

        if (!hasOffsets || !ui.baseCurveData) {
            el.innerHTML = '';
            el.classList.add('hidden');
            return;
        }

        // WBT points: step through axis range, always include design WBT
        const step = Math.max(1, Math.round((ui.inputs.axXMax - ui.inputs.axXMin) / 9));
        const pts = new Set();
        for (let w = ui.inputs.axXMin; w <= ui.inputs.axXMax + 0.01; w += step) {
            pts.add(Math.round(w * 10) / 10);
        }
        pts.add(Math.round(ui.inputs.designWBT * 10) / 10);
        const wbtPoints = [...pts].sort((a, b) => a - b);

        // Lookup closest data point in a curve array
        function lookup(curveArr, wbt, key) {
            if (!curveArr || !curveArr.length) return null;
            return curveArr.reduce((prev, curr) =>
                Math.abs(curr.wbt - wbt) < Math.abs(prev.wbt - wbt) ? curr : prev
            )[key];
        }

        const flows   = [90, 100, 110];
        const fColors = ['text-emerald-400', 'text-cyan-400', 'text-amber-400'];
        const vColors = ['text-emerald-300', 'text-cyan-300',  'text-amber-300'];

        let rows = '';
        wbtPoints.forEach(wbt => {
            const isDesign = Math.abs(wbt - ui.inputs.designWBT) < 0.06;
            const trCls = isDesign
                ? 'bg-emerald-950/40 border-y border-emerald-500/25'
                : 'border-b border-white/5';

            let cells = `<td class="px-2 py-1.5 font-black ${isDesign ? 'text-slate-200' : 'text-slate-400'} whitespace-nowrap">
                            ${wbt.toFixed(1)}${isDesign ? ' <span class="text-emerald-500 text-[8px]">★</span>' : ''}
                         </td>`;

            flows.forEach((flow, fi) => {
                const base   = lookup(ui.baseCurveData[flow], wbt, 'range100');
                const offset = lookup(ui.curveData[flow],     wbt, 'range100');
                if (base == null || offset == null) {
                    cells += `<td class="px-2 py-1.5 text-center text-slate-600">—</td>`;
                    return;
                }
                const delta   = offset - base;
                const deltaAbs = Math.abs(delta);

                let deltaHtml;
                if (isDesign && flow === 100 && deltaAbs < 0.05) {
                    deltaHtml = `<span class="text-emerald-400 font-black">✓ guaranteed</span>`;
                } else {
                    const sign = delta >= 0 ? '+' : '';
                    const dCls = deltaAbs < 0.01 ? 'text-slate-600'
                               : delta > 0       ? 'text-amber-400'
                                                 : 'text-sky-400';
                    deltaHtml = `<span class="${dCls}">${sign}${delta.toFixed(2)}</span>`;
                }

                cells += `
                    <td class="px-2 py-1.5 text-center">
                        <span class="text-slate-500">${base.toFixed(2)}</span>
                        <span class="text-slate-600 mx-0.5">→</span>
                        <span class="${vColors[fi]} font-bold">${offset.toFixed(2)}</span>
                        <span class="block text-[9px] leading-none mt-0.5">${deltaHtml}</span>
                    </td>`;
            });

            rows += `<tr class="${trCls}">${cells}</tr>`;
        });

        el.innerHTML = `
            <div class="mt-4 pt-4 border-t border-white/5">
                <div class="flex items-center gap-2 mb-2.5">
                    <span class="w-1 h-3 bg-amber-500/70 rounded-full"></span>
                    <p class="text-[9px] font-black uppercase tracking-[0.2em] text-amber-400">Margin Impact — 100% Range CWT</p>
                    <span class="text-[8px] text-slate-600 normal-case font-normal tracking-normal">(base → with margins, Δ per WBT)</span>
                </div>
                <div class="overflow-x-auto rounded-xl border border-white/5 bg-slate-900/30">
                    <table class="w-full text-[10px] font-mono border-collapse">
                        <thead>
                            <tr class="border-b border-white/10 bg-slate-900/60">
                                <th class="px-2 py-1.5 text-left text-[9px] text-slate-500 font-black uppercase">WBT °C</th>
                                <th class="px-2 py-1.5 text-center ${fColors[0]} text-[9px] font-black uppercase">90% Flow</th>
                                <th class="px-2 py-1.5 text-center ${fColors[1]} text-[9px] font-black uppercase">100% Flow</th>
                                <th class="px-2 py-1.5 text-center ${fColors[2]} text-[9px] font-black uppercase">110% Flow</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                <p class="text-[8px] text-slate-600 mt-1.5 px-1">★ = Design WBT. 100% flow at design WBT must show ✓ guaranteed (anchored tilt — no contractual shift).</p>
            </div>`;
        el.classList.remove('hidden');
    }
};

window.addEventListener('DOMContentLoaded', ui.init);
