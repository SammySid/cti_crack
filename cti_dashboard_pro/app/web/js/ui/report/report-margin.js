// Margin Modal logic extracted from ui.js

export function fetchAndRenderBaseComparison(ui) {
    const OFFSET_KEYS = [
        'offsetWbt20',
        'off90r80',  'off90r100',  'off90r120',
        'off100r80', 'off100r100', 'off100r120',
        'off110r80', 'off110r100', 'off110r120'
    ];
    const baseInputs = { ...ui.inputs };
    OFFSET_KEYS.forEach(k => { baseInputs[k] = 0; });

    Promise.all([90, 100, 110].map(flow =>
        fetch('/api/calculate/curves', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: baseInputs, flowPercent: flow })
        }).then(r => r.json()).then(r => [flow, r.data])
    )).then(results => {
        ui.baseCurveData = Object.fromEntries(results);
        ui.renderMarginComparison();
    }).catch(e => {
        ui.baseCurveData = null;
        ui.renderMarginComparison();
    });
}

export function renderMarginComparison(ui) {
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
}

export function renderMarginTable(ui) {
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

export function bindMarginModalState(ui) {
    ui._marginModalState = { flows: new Set([90, 100, 110]), changedOnly: false };
    ui._marginTableData  = null;

    window._toggleMarginFlow = function(pct) {
        const st = ui._marginModalState;
        if (st.flows.has(pct)) {
            if (st.flows.size > 1) st.flows.delete(pct); // keep at least 1
        } else {
            st.flows.add(pct);
        }
        ui.renderMarginComparison();
    };

    window._toggleMarginChangedOnly = function() {
        ui._marginModalState.changedOnly = !ui._marginModalState.changedOnly;
        ui.renderMarginComparison();
    };
}
