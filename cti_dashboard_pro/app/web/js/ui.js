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

                // Check only the offsets that actually affect THIS flow (mirrors backend logic)
                const wbtTilt = ui.inputs.offsetWbt20 !== 0;
                const flowOffsetKeys = {
                    90:  ['off90r80',  'off90r100',  'off90r120'],
                    100: ['off100r80', 'off100r100', 'off100r120'],
                    110: ['off110r80', 'off110r100', 'off110r120'],
                };
                const hasOffsets = wbtTilt || (flowOffsetKeys[flowPercent] || []).some(k => ui.inputs[k] !== 0);
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
                    // Global check — any offset across any flow active?
                    // Must be done here (not per-flow) to avoid race: last flow to
                    // return could be one with no offsets, wrongly clearing baseCurveData.
                    const GLOBAL_OFFSET_KEYS = [
                        'offsetWbt20',
                        'off90r80',  'off90r100',  'off90r120',
                        'off100r80', 'off100r100', 'off100r120',
                        'off110r80', 'off110r100', 'off110r120',
                    ];
                    const anyOffsetActive = GLOBAL_OFFSET_KEYS.some(k => ui.inputs[k] !== 0);
                    if (anyOffsetActive) {
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
        const OFFSET_KEYS = [
            'offsetWbt20',
            'off90r80',  'off90r100',  'off90r120',
            'off100r80', 'off100r100', 'off100r120',
            'off110r80', 'off110r100', 'off110r120'
        ];
        const hasOffsets = OFFSET_KEYS.some(k => ui.inputs[k] !== 0);

        // Show/hide trigger button
        const btnWrap = document.getElementById('marginImpactBtnWrap');
        if (btnWrap) {
            if (hasOffsets && ui.baseCurveData) btnWrap.classList.remove('hidden');
            else                                btnWrap.classList.add('hidden');
        }

        if (!hasOffsets || !ui.baseCurveData) return;

        // Subtitle
        const subtitle = document.getElementById('marginModalSubtitle');
        const activeCount = OFFSET_KEYS.filter(k => ui.inputs[k] !== 0).length;
        if (subtitle) subtitle.textContent =
            `${activeCount} active margin${activeCount > 1 ? 's' : ''} applied · 100% Range CWT comparison at 0.5°C resolution`;

        // Build all modal content in marginModalBody
        const body = document.getElementById('marginModalBody');
        if (!body) return;

        // ── 1. Applied Margins Summary Grid ──────────────────────────────
        const flows3  = [90, 100, 110];
        const ranges3 = [80, 100, 120];
        const rLabels = { 80: '80% Range', 100: '100% Range', 120: '120% Range' };
        const fColors = { 90: '#10b981', 100: '#06b6d4', 110: '#f59e0b' };

        function marginVal(f, r) {
            if (f === 'wbt20') return ui.inputs.offsetWbt20;
            const k = `off${f}r${r}`;
            return ui.inputs[k] || 0;
        }
        function marginCell(val, isKey) {
            const nonZero = Math.abs(val) > 0.001;
            const bg  = nonZero ? (isKey ? 'bg-amber-500/20 border-amber-500/40' : 'bg-amber-500/10 border-amber-500/20')
                                : 'bg-white/[0.03] border-white/8';
            const txt = nonZero ? (isKey ? 'text-amber-300 font-black' : 'text-amber-400 font-bold')
                                : 'text-slate-600 font-semibold';
            const prefix = val > 0 ? '+' : '';
            return `<div class="rounded-lg border px-2 py-1.5 text-center font-mono text-[11px] ${bg} ${txt}">
                        ${nonZero ? prefix + val.toFixed(2) + '°C' : '—'}
                    </div>`;
        }

        let gridRows = '';
        flows3.forEach(f => {
            gridRows += `<div class="contents">
                <div class="flex items-center px-2 py-1 text-[10px] font-black uppercase tracking-wider" style="color:${fColors[f]}">${f}% Flow</div>`;
            ranges3.forEach(r => {
                const val = marginVal(f, r);
                const isKey = (f === 100 && r === 100); // the "contractual" cell
                gridRows += marginCell(val, isKey);
            });
            gridRows += `</div>`;
        });

        const wbtTilt = ui.inputs.offsetWbt20;

        // ── 2. WBT points at 0.5°C ───────────────────────────────────────
        const wbtPoints = [];
        for (let w = ui.inputs.axXMin; w <= ui.inputs.axXMax + 0.01; w += 0.5) {
            wbtPoints.push(Math.round(w * 10) / 10);
        }
        const dWBT = Math.round(ui.inputs.designWBT * 10) / 10;
        if (!wbtPoints.some(p => Math.abs(p - dWBT) < 0.01)) {
            wbtPoints.push(dWBT);
            wbtPoints.sort((a, b) => a - b);
        }

        // Lookup helper
        function lookup(arr, wbt, key) {
            if (!arr || !arr.length) return null;
            return arr.reduce((p, c) => Math.abs(c.wbt - wbt) < Math.abs(p.wbt - wbt) ? c : p)[key];
        }

        // Store wbt/delta data for filter
        ui._marginTableData = wbtPoints.map(wbt => {
            const isDesign = Math.abs(wbt - dWBT) < 0.01;
            const row = { wbt, isDesign, cells: [] };
            flows3.forEach(f => {
                const base   = lookup(ui.baseCurveData[f], wbt, 'range100');
                const margin = lookup(ui.curveData[f],     wbt, 'range100');
                const delta  = (base != null && margin != null) ? margin - base : null;
                row.cells.push({ f, base, margin, delta });
            });
            return row;
        });

        // ── 3. Build compact active-offsets pill bar ─────────────────────
        const offsetDefs = [
            { key: 'off90r80',   label: '90%F · 80%R',  color: 'emerald' },
            { key: 'off90r100',  label: '90%F · 100%R', color: 'emerald' },
            { key: 'off90r120',  label: '90%F · 120%R', color: 'emerald' },
            { key: 'off100r80',  label: '100%F · 80%R', color: 'cyan'    },
            { key: 'off100r100', label: '100%F · 100%R',color: 'cyan'    },
            { key: 'off100r120', label: '100%F · 120%R',color: 'cyan'    },
            { key: 'off110r80',  label: '110%F · 80%R', color: 'amber'   },
            { key: 'off110r100', label: '110%F · 100%R',color: 'amber'   },
            { key: 'off110r120', label: '110%F · 120%R',color: 'amber'   },
        ];
        const colorMap = {
            emerald: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
            cyan:    'bg-cyan-500/15 border-cyan-500/30 text-cyan-300',
            amber:   'bg-amber-500/15 border-amber-500/30 text-amber-300',
        };
        const activePills = offsetDefs
            .filter(d => ui.inputs[d.key] !== 0)
            .map(d => {
                const v = ui.inputs[d.key];
                const prefix = v > 0 ? '+' : '';
                return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[10px] font-black font-mono ${colorMap[d.color]}">
                    <span class="font-sans uppercase tracking-wider text-[8px] opacity-70">${d.label}</span>
                    ${prefix}${v.toFixed(2)}°C
                </span>`;
            });
        const wbtPill = Math.abs(wbtTilt) > 0.001
            ? `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border bg-violet-500/15 border-violet-500/30 text-violet-300 text-[10px] font-black font-mono">
                   <span class="font-sans uppercase tracking-wider text-[8px] opacity-70">WBT Tilt @20°C</span>
                   +${wbtTilt.toFixed(2)}°C
               </span>`
            : '';
        const pillsHtml = (activePills.length || wbtPill)
            ? `<div class="flex flex-wrap items-center gap-2 mb-4 pb-3.5 border-b border-white/8">
                   <span class="text-[9px] font-black uppercase tracking-widest text-slate-600 shrink-0">Active offsets:</span>
                   ${activePills.join('')}${wbtPill}
               </div>`
            : '';

        // ── 4. Assemble full modal body ───────────────────────────────────
        const st = ui._marginModalState;

        body.innerHTML = `
        ${pillsHtml}
        <!-- Table Controls -->
        <div class="flex flex-wrap items-center gap-2 mb-3">
            <span class="text-[9px] font-black uppercase tracking-wider text-slate-500 mr-1">Show flows:</span>
            ${flows3.map(f => {
                const on = st.flows.has(f);
                const cls = on
                    ? (f===90  ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                      :f===100 ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400'
                               : 'bg-amber-500/20 border-amber-500/40 text-amber-400')
                    : 'bg-white/5 border-white/10 text-slate-600';
                return `<button onclick="window._toggleMarginFlow(${f}); event.stopPropagation();"
                            class="px-3 py-1 rounded-lg border text-[10px] font-black uppercase tracking-wider transition-all ${cls}">
                            ${f}% Flow
                        </button>`;
            }).join('')}
            <div class="ml-auto">
                <button onclick="window._toggleMarginChangedOnly(); event.stopPropagation();"
                    class="px-3 py-1 rounded-lg border text-[10px] font-black uppercase tracking-wider transition-all
                           ${st.changedOnly ? 'bg-violet-500/20 border-violet-500/40 text-violet-400' : 'bg-white/5 border-white/10 text-slate-500'}">
                    ${st.changedOnly ? '✓ Changed rows only' : 'All rows'}
                </button>
            </div>
        </div>

        <!-- Table -->
        <div id="marginTableWrap"></div>`;

        // Render table separately (also called on toggle)
        ui._renderMarginTable();
    },

    _renderMarginTable: () => {
        const wrap = document.getElementById('marginTableWrap');
        if (!wrap || !ui._marginTableData) return;

        const st     = ui._marginModalState;
        const flows3 = [90, 100, 110];
        const fMeta  = {
            90:  { label: '90% Flow',  groupBg: 'bg-emerald-500/10', groupTxt: 'text-emerald-300', groupBorder: 'border-emerald-500/20', valCls: 'text-emerald-200' },
            100: { label: '100% Flow', groupBg: 'bg-cyan-500/10',    groupTxt: 'text-cyan-300',    groupBorder: 'border-cyan-500/20',    valCls: 'text-cyan-200'    },
            110: { label: '110% Flow', groupBg: 'bg-amber-500/10',   groupTxt: 'text-amber-300',   groupBorder: 'border-amber-500/20',   valCls: 'text-amber-200'   },
        };
        const visFlows = flows3.filter(f => st.flows.has(f));
        const dWBT = Math.round(ui.inputs.designWBT * 10) / 10;

        // Filter rows
        let rows = ui._marginTableData;
        if (st.changedOnly) {
            rows = rows.filter(r => r.isDesign || r.cells.some(c =>
                visFlows.includes(c.f) && c.delta != null && Math.abs(c.delta) >= 0.01
            ));
        }

        const colCount = 1 + visFlows.length * 3;

        // ── thead: row1 = group labels, row2 = sub-column labels ──────────
        // Row 1 — WBT + flow group headers
        let theadR1 = `
            <tr style="background:#0d1117">
                <th rowspan="2"
                    class="px-4 py-3 text-left align-bottom sticky left-0 z-30 border-r border-white/8 min-w-[80px]"
                    style="background:#0d1117">
                    <span class="text-[10px] font-black uppercase tracking-widest text-slate-300">WBT</span><br>
                    <span class="text-[9px] font-semibold text-slate-600 normal-case tracking-normal">(°C)</span>
                </th>`;
        visFlows.forEach(f => {
            const m = fMeta[f];
            theadR1 += `
                <th colspan="3"
                    class="px-3 py-2.5 text-center border-l border-white/8 border-b border-white/10 ${m.groupBg}"
                    style="background-color: var(--tw-bg-opacity, inherit)">
                    <span class="text-[11px] font-black uppercase tracking-wider ${m.groupTxt}">${m.label}</span>
                </th>`;
        });
        theadR1 += `</tr>`;

        // Row 2 — sub-column labels (solid bg to prevent bleed-through on scroll)
        const subBgMap = { 90: '#0d1f18', 100: '#0d1c24', 110: '#1f1a0d' };
        let theadR2 = `<tr style="background:#0d1117; box-shadow:0 3px 10px rgba(0,0,0,0.7)">`;
        visFlows.forEach(f => {
            const solidBg = subBgMap[f] || '#0d1117';
            theadR2 += `
                <th class="px-3 py-2 text-right border-l border-white/8 border-b-2 border-white/10" style="background:${solidBg}">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-200">Base</span>
                    <span class="block text-[8px] font-medium text-slate-500 normal-case tracking-normal">no margin</span>
                </th>
                <th class="px-3 py-2 text-right border-b-2 border-white/10" style="background:${solidBg}">
                    <span class="text-[10px] font-bold uppercase tracking-wider ${fMeta[f].groupTxt}">Margin</span>
                    <span class="block text-[8px] font-medium text-slate-500 normal-case tracking-normal">with offset</span>
                </th>
                <th class="px-3 py-2 text-center border-r border-white/8 border-b-2 border-white/10" style="background:${solidBg}">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-200">Δ</span>
                    <span class="block text-[8px] font-medium text-slate-500 normal-case tracking-normal">delta °C</span>
                </th>`;
        });
        theadR2 += `</tr>`;

        // ── tbody ──────────────────────────────────────────────────────────
        let tbody = '';
        if (rows.length === 0) {
            tbody = `<tr>
                <td colspan="${colCount}"
                    class="px-4 py-8 text-center text-[12px] text-slate-600 italic">
                    No rows with active delta in selected flows.<br>
                    <span class="text-[10px]">Disable "Changed rows only" to see all WBT points.</span>
                </td>
            </tr>`;
        } else {
            rows.forEach((row, i) => {
                const { wbt, isDesign } = row;
                const isEven = i % 2 === 0;
                const trBg   = isDesign ? 'bg-emerald-950/40' : (isEven ? '' : 'bg-white/[0.018]');
                const trBorder = isDesign ? 'border-y-2 border-emerald-500/30' : 'border-b border-white/[0.06]';

                // WBT cell — inline bg required for sticky to be opaque
                const wbtBg = isDesign ? '#0a1f14' : (isEven ? '#0d1117' : '#0e1219');
                let cells = `
                    <td class="px-4 py-2 sticky left-0 z-10 border-r border-white/8"
                        style="background:${wbtBg}">
                        <span class="font-mono font-black text-[13px] ${isDesign ? 'text-white' : 'text-slate-300'}">${wbt.toFixed(1)}</span>
                        ${isDesign ? `<span class="ml-1 text-emerald-400 text-[10px] font-black">★</span>` : ''}
                    </td>`;

                row.cells.filter(c => visFlows.includes(c.f)).forEach((c, ci) => {
                    const m = fMeta[c.f];
                    if (c.base == null || c.margin == null) {
                        cells += `<td colspan="3" class="px-3 py-2 text-center text-slate-700 border-l border-white/8 text-[11px]">—</td>`;
                        return;
                    }
                    const isGuaranteed = isDesign && c.f === 100 && Math.abs(c.delta) < 0.05;
                    const sign  = c.delta >= 0 ? '+' : '';
                    const dAbs  = Math.abs(c.delta);

                    // Delta pill
                    let deltaPill;
                    if (isGuaranteed) {
                        deltaPill = `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-black bg-emerald-500/20 border border-emerald-500/30 text-emerald-300">✓ locked</span>`;
                    } else if (dAbs < 0.01) {
                        deltaPill = `<span class="text-slate-600 font-mono text-[11px]">—</span>`;
                    } else {
                        const pillBg  = c.delta > 0 ? 'bg-amber-500/15 border-amber-500/25 text-amber-300' : 'bg-sky-500/15 border-sky-500/25 text-sky-300';
                        deltaPill = `<span class="inline-flex items-center px-1.5 py-0.5 rounded font-mono font-bold text-[11px] border ${pillBg}">${sign}${c.delta.toFixed(2)}</span>`;
                    }

                    cells += `
                        <td class="px-3 py-2 text-right font-mono text-[12px] font-semibold text-slate-300 border-l border-white/8">
                            ${c.base.toFixed(2)}
                        </td>
                        <td class="px-3 py-2 text-right font-mono text-[12px] font-black ${m.valCls}">
                            ${c.margin.toFixed(2)}
                        </td>
                        <td class="px-3 py-2 text-center border-r border-white/8">
                            ${deltaPill}
                        </td>`;
                });

                tbody += `<tr class="${trBg} ${trBorder}">${cells}</tr>`;
            });
        }

        const minW = 160 + visFlows.length * 210;
        wrap.innerHTML = `
            <div class="rounded-2xl border border-white/10 overflow-auto" style="max-height:55vh">
                <table class="w-full border-collapse" style="min-width:${minW}px">
                    <thead class="sticky top-0 z-20">${theadR1}${theadR2}</thead>
                    <tbody>${tbody}</tbody>
                </table>
            </div>
            <div class="flex items-center justify-between mt-2 px-1">
                <p class="text-[9px] text-slate-700">
                    ★ Design WBT ${dWBT.toFixed(1)}°C — 100% Flow Δ must show ✓ locked (anchored tilt guarantee).
                </p>
                <p class="text-[9px] text-slate-600">
                    ${rows.length} / ${ui._marginTableData.length} rows shown
                </p>
            </div>`;
    }
};

// ── Margin Modal global state & toggle handlers ────────────────────────────
ui._marginModalState = { flows: new Set([90, 100, 110]), changedOnly: false };
ui._marginTableData  = null;

window._toggleMarginFlow = function(pct) {
    const st = ui._marginModalState;
    if (st.flows.has(pct)) {
        if (st.flows.size > 1) st.flows.delete(pct); // keep at least 1
    } else {
        st.flows.add(pct);
    }
    // Re-render just controls + table (re-call full render to refresh button states)
    ui.renderMarginComparison();
};

window._toggleMarginChangedOnly = function() {
    ui._marginModalState.changedOnly = !ui._marginModalState.changedOnly;
    ui.renderMarginComparison();
};

window.addEventListener('DOMContentLoaded', ui.init);
