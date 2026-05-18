// ── Preview chart registry — destroyed on each re-run ─────────────────────────
export const _pvCharts = {};

export function _pvChart(id, config) {
    if (_pvCharts[id]) { _pvCharts[id].destroy(); delete _pvCharts[id]; }
    const canvas = document.getElementById(id);
    if (!canvas) return;
    _pvCharts[id] = new Chart(canvas, config);
}

export const _pvTheme = {
    grid:  'rgba(148,163,184,0.10)',
    tick:  '#475569',
    label: '#64748b',
    text:  '#94a3b8',
};

// ── Cross Plot 1: CWT vs Range (3 flow curves + test-range marker) ─────────────
export function _pvRenderCp1(canvasId, cp1, testWbt) {
    const ranges = cp1.ranges_abs.map(Number);
    const y90    = cp1.cwt_90.map(Number);
    const y100   = cp1.cwt_100.map(Number);
    const y110   = cp1.cwt_110.map(Number);
    const testR  = Number(cp1.test_range);

    const allY = [...y90, ...y100, ...y110].filter(isFinite);
    const yMin = Math.floor(Math.min(...allY) - 0.5);
    const yMax = Math.ceil(Math.max(...allY)  + 0.5);
    const xMin = Math.min(...ranges) - 0.3;
    const xMax = Math.max(...ranges) + 0.3;

    const intPts = [
        cp1.f90_cwt  != null ? { x: testR, y: Number(cp1.f90_cwt)  } : null,
        cp1.f100_cwt != null ? { x: testR, y: Number(cp1.f100_cwt) } : null,
        cp1.f110_cwt != null ? { x: testR, y: Number(cp1.f110_cwt) } : null,
    ].filter(Boolean);

    _pvChart(canvasId, {
        type: 'scatter',
        data: { datasets: [
            { label: '90% Flow',  data: ranges.map((x,i) => ({x, y: y90[i]})),  borderColor: '#7c3aed', backgroundColor: '#7c3aed', showLine: true, borderWidth: 2, pointRadius: 3, tension: 0.3, fill: false },
            { label: '100% Flow', data: ranges.map((x,i) => ({x, y: y100[i]})), borderColor: '#16a34a', backgroundColor: '#16a34a', showLine: true, borderWidth: 2, pointRadius: 3, tension: 0.3, fill: false },
            { label: '110% Flow', data: ranges.map((x,i) => ({x, y: y110[i]})), borderColor: '#2563eb', backgroundColor: '#2563eb', showLine: true, borderWidth: 2, pointRadius: 3, tension: 0.3, fill: false },
            { label: `Test Range ${testR.toFixed(2)}°C`, data: [{x:testR,y:yMin},{x:testR,y:yMax}], borderColor: '#dc2626', showLine: true, borderWidth: 1.5, borderDash: [4,3], pointRadius: 0, fill: false },
            { label: 'CP1 → CP2 Points', data: intPts, borderColor: '#f59e0b', backgroundColor: '#f59e0b', showLine: false, pointRadius: 5, pointStyle: 'circle' },
        ]},
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: {
                legend: { display: true, position: 'top', align: 'start', labels: { color: _pvTheme.text, usePointStyle: true, font: { size: 9 }, padding: 8 } },
                tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: (${ctx.parsed.x?.toFixed(2)}, ${ctx.parsed.y?.toFixed(2)})` } },
            },
            scales: {
                x: { type: 'linear', min: xMin, max: xMax, title: { display: true, text: 'Range (°C)', color: _pvTheme.label, font: { size: 9 } }, grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
                y: { min: yMin, max: yMax,                  title: { display: true, text: 'CWT (°C)',   color: _pvTheme.label, font: { size: 9 } }, grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
            },
        },
    });
}

// ── Cross Plot 2: Flow vs CWT (tower performance curve + crosshair annotations) ─
export function _pvRenderCp2(canvasId, cp2) {
    const flows    = cp2.flows.map(Number);
    const cwts     = cp2.cwts.map(Number);
    const adjFlow  = Number(cp2.adj_flow);
    const predCwt  = Number(cp2.pred_cwt);
    const testCwt  = Number(cp2.test_cwt);
    const predFlow = cp2.pred_flow != null ? Number(cp2.pred_flow) : null;

    const allX = [adjFlow, predFlow ?? adjFlow, ...flows];
    const allY = [predCwt, testCwt, ...cwts];
    const xMin = Math.min(...allX) * 0.94;
    const xMax = Math.max(...allX) * 1.05;
    const yMin = Math.min(...allY) - 0.5;
    const yMax = Math.max(...allY) + 0.5;

    const datasets = [
        { label: 'Tower Perf. Curve', data: flows.map((x,i) => ({x, y:cwts[i]})), borderColor: '#06b6d4', backgroundColor: '#06b6d430', showLine: true, borderWidth: 2.5, pointRadius: 5, fill: false, tension: 0 },
        { label: `Q_adj = ${adjFlow.toFixed(1)} m³/hr`, data: [{x:adjFlow,y:yMin},{x:adjFlow,y:predCwt}], borderColor: '#ea580c', showLine: true, borderWidth: 1.5, borderDash: [5,3], pointRadius: 0, fill: false },
        { label: `Pred. CWT = ${predCwt.toFixed(2)} °C`, data: [{x:xMin,y:predCwt},{x:adjFlow,y:predCwt}], borderColor: '#06b6d4', showLine: true, borderWidth: 1.5, borderDash: [5,3], pointRadius: 0, fill: false },
        { label: `Test CWT = ${testCwt.toFixed(2)} °C`, data: predFlow != null ? [{x:xMin,y:testCwt},{x:predFlow,y:testCwt}] : [], borderColor: '#dc2626', showLine: true, borderWidth: 1.5, borderDash: [5,3], pointRadius: 0, fill: false },
        { label: 'Adj.Flow → Pred.CWT', data: [{x:adjFlow,y:predCwt}], borderColor: '#ea580c', backgroundColor: '#ea580c', showLine: false, pointRadius: 7, pointStyle: 'crossRot' },
    ];
    if (predFlow != null) {
        datasets.push({ label: `Pred. Flow = ${predFlow.toFixed(0)} m³/hr`, data: [{x:predFlow,y:yMin},{x:predFlow,y:testCwt}], borderColor: '#16a34a', showLine: true, borderWidth: 1.5, borderDash: [5,3], pointRadius: 0, fill: false });
        datasets.push({ label: 'Test CWT → Pred.Flow', data: [{x:predFlow,y:testCwt}], borderColor: '#dc2626', backgroundColor: '#dc2626', showLine: false, pointRadius: 7 });
    }

    _pvChart(canvasId, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: {
                legend: {
                    display: true, position: 'top', align: 'start',
                    labels: { color: _pvTheme.text, usePointStyle: true, font: { size: 9 }, padding: 8,
                        filter: item => !['Adj.Flow → Pred.CWT','Test CWT → Pred.Flow'].includes(item.text) },
                },
                tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: (${ctx.parsed.x?.toFixed(1)}, ${ctx.parsed.y?.toFixed(2)})` } },
            },
            scales: {
                x: { type: 'linear', min: xMin, max: xMax, title: { display: true, text: 'Water Flow (m³/hr)', color: _pvTheme.label, font: { size: 9 } }, grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
                y: { min: yMin, max: yMax,                  title: { display: true, text: 'CWT (°C)',           color: _pvTheme.label, font: { size: 9 } }, grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
            },
        },
    });
}

// ── Capability bar chart ───────────────────────────────────────────────────────
export function _pvRenderCapChart(caps) {
    const colors = caps.map(v => v >= 100 ? '#16a34a' : v >= 95 ? '#d97706' : '#dc2626');
    _pvChart('pv-cap-chart', {
        type: 'bar',
        data: {
            labels: ['Test 1 — Pre-Baseline', 'Test 2 — Post Fan Pitch', 'Test 3 — Post Fill Dist.'],
            datasets: [{ label: 'Capability (%)', data: caps, backgroundColor: colors.map(c => c + '40'), borderColor: colors, borderWidth: 2, borderRadius: 4 }],
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `Capability: ${ctx.parsed.y.toFixed(1)}%` } } },
            scales: {
                x: { grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
                y: { min: Math.min(80, ...caps) - 3, max: Math.max(110, ...caps) + 2, grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 }, callback: v => v + '%' } },
            },
        },
    });
}

// ── Trend line: shortfall + capability across 3 tests ─────────────────────────
export function _pvRenderTrendChart(shortfalls, caps) {
    _pvChart('pv-trend-chart', {
        type: 'line',
        data: {
            labels: ['Test 1 (Pre)', 'Test 2 (Post Fan)', 'Test 3 (Post Fill)'],
            datasets: [
                { label: 'Shortfall (°C)', data: shortfalls, borderColor: '#f59e0b', backgroundColor: '#f59e0b18', fill: true, borderWidth: 2, pointRadius: 5, tension: 0.3, yAxisID: 'y' },
                { label: 'Capability (%)', data: caps,       borderColor: '#06b6d4', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 5, tension: 0.3, yAxisID: 'y2', borderDash: [4,3] },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: { legend: { position: 'top', align: 'end', labels: { color: _pvTheme.text, usePointStyle: true, font: { size: 9 }, padding: 12 } } },
            scales: {
                x:  { grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
                y:  { position: 'left',  title: { display: true, text: 'Shortfall (°C)', color: _pvTheme.label, font: { size: 9 } }, grid: { color: _pvTheme.grid }, ticks: { color: _pvTheme.tick, font: { size: 9 } } },
                y2: { position: 'right', title: { display: true, text: 'Capability (%)', color: _pvTheme.label, font: { size: 9 } }, grid: { display: false }, ticks: { color: _pvTheme.tick, font: { size: 9 }, callback: v => v + '%' } },
            },
        },
    });
}
