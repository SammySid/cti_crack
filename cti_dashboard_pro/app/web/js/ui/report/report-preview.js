import { _n, _v, _getDesign, _buildPayloadForTest, _getOffsetsFromUi, _calcAtc } from './report-helpers.js';
import { _isTestEnabled } from './report-toggles.js';
import { _pvRenderCp1, _pvRenderCp2, _pvRenderCapChart, _pvRenderTrendChart } from './report-preview-charts.js';

export async function updateAtcPreview(ui) {
    const previewEl = document.getElementById('atcPreview');
    if (!previewEl) return;

    const design = _getDesign(ui);
    if (!design.flow) { previewEl.classList.add('hidden'); return; }

    const currentTest = {
        wbt:       _n('rep-test-wbt',    21.7),
        cwt:       _n('rep-cwt',         32.4),
        hwt:       _n('rep-hwt',         42.13),
        flow:      _n('rep-flow',        3680),
        fan_power: _n('rep-test-fanpow', 117),
    };

    try {
        const resp = await fetch('/api/calculate/atc105', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(_buildPayloadForTest(design, currentTest, _getOffsetsFromUi(ui))),
        });
        if (!resp.ok) return;
        const r = await resp.json();

        document.getElementById('atc-prev-range').innerText      = `${r.test_range?.toFixed(2) ?? '—'} °C`;
        document.getElementById('atc-prev-adjflow').innerText    = r.adj_flow?.toFixed(1)  ?? '—';
        document.getElementById('atc-prev-predcwt').innerText    = r.pred_cwt?.toFixed(2)  ?? '—';
        document.getElementById('atc-prev-shortfall').innerText  = r.shortfall?.toFixed(2) ?? '—';
        document.getElementById('atc-prev-capability').innerText = r.capability != null ? `${r.capability.toFixed(1)} %` : '—';

        previewEl.classList.remove('hidden');
    } catch (_) { /* silently ignore preview errors */ }
}

// ── Verdict / colour helpers ───────────────────────────────────────────────────
export function _capVerdict(v)   { return v >= 100 ? 'PASS' : v >= 95 ? 'MARGINAL' : 'FAIL'; }
export function _capBadgeCls(v)  { return v >= 100 ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : v >= 95 ? 'border-amber-500/30 bg-amber-500/10 text-amber-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'; }
export function _capTextCls(v)   { return v >= 100 ? 'text-emerald-400' : v >= 95 ? 'text-amber-400' : 'text-rose-400'; }
export function _sfTextCls(v)    { return v  > 0   ? 'text-rose-400'    : v  < 0  ? 'text-emerald-400' : 'text-slate-400'; }

// ── Per-test calculation walkthrough table (injected as innerHTML) ─────────────
export function _buildPvCalcTable(d, t, r) {
    const f2 = v => v != null ? Number(v).toFixed(2) : '—';
    const f1 = v => v != null ? Number(v).toFixed(1) : '—';
    const sfCls  = r.shortfall  > 0 ? 'text-rose-400'    : 'text-emerald-400';
    const capCls = r.capability >= 100 ? 'text-emerald-400' : r.capability >= 95 ? 'text-amber-400' : 'text-rose-400';

    const rows = [
        ['①', 'Test Range',              'Actual temperature drop across the tower.',                                       `HWT − CWT = ${f2(t.hwt)} − ${f2(t.cwt)}`,                             `<span class="text-slate-200 font-bold">${f2(r.test_range)} °C</span>`],
        ['②', 'Adjusted Water Flow',     'Normalise measured flow to design fan power &amp; water density (Kell 1975).',   `${f1(t.flow)} × (${f2(d.fan_power)}/${f2(t.fan_power)})^⅓ × ρ^⅓`,    `<span class="text-slate-200 font-bold">${f1(r.adj_flow)} m³/hr</span>`],
        ['③', 'Cross Plot 1 → Table 2',  'Build 3×3 CWT grid at test WBT. Interpolate at actual test range % across 3 flows → 3 CP2 curve points.',  `test_range_pct = ${f2(r.test_range_pct)}% → see CP1 chart`,   `<span class="text-slate-400">3 pts →</span>`],
        ['④', 'Pred. CWT (Cross Plot 2)','Plot Flow vs CWT from CP1 intersections. Read Predicted CWT at Q_adj on the performance curve.',            `Q_adj = ${f1(r.adj_flow)} m³/hr → on curve`,                  `<span class="text-cyan-300 font-bold">${f2(r.pred_cwt)} °C</span>`],
        ['⑤', 'Shortfall',               '+ve = underperforming. −ve = tower exceeds spec.',                                                          `Test CWT ${f2(t.cwt)} − Pred. CWT ${f2(r.pred_cwt)}`,         `<span class="${sfCls} font-bold">${r.shortfall > 0 ? '+' : ''}${f2(r.shortfall)} °C</span>`],
        ['⑥', 'Capability (ATC-105 §C)', '≥ 100% = tower meets contractual thermal rating.',                                                          `Q_adj / Q_pred_at_testCWT × 100 = ${f1(r.adj_flow)} / ${f1(r.pred_flow)} × 100`, `<span class="${capCls} font-bold">${f1(r.capability)} %</span>`],
    ];

    return `<table class="w-full divide-y divide-white/5">
        <thead class="bg-slate-900/60">
            <tr>
                <th class="px-3 py-2 text-left text-[10px] font-black uppercase tracking-widest text-slate-500 w-6">#</th>
                <th class="px-3 py-2 text-left text-[10px] font-black uppercase tracking-widest text-slate-400">Step</th>
                <th class="px-3 py-2 text-left text-[10px] font-black uppercase tracking-widest text-slate-400 hidden md:table-cell">What It Means</th>
                <th class="px-3 py-2 text-left text-[10px] font-black uppercase tracking-widest text-slate-400 hidden lg:table-cell">Formula / Working</th>
                <th class="px-3 py-2 text-right text-[10px] font-black uppercase tracking-widest text-slate-400">Result</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-white/[0.04]">
            ${rows.map(([n, step, meaning, formula, result]) => `
            <tr class="hover:bg-white/[0.02]">
                <td class="px-3 py-2.5 text-xs font-mono text-slate-500">${n}</td>
                <td class="px-3 py-2.5 text-xs font-mono text-slate-200 font-bold whitespace-nowrap">${step}</td>
                <td class="px-3 py-2.5 text-xs text-slate-400 hidden md:table-cell leading-relaxed">${meaning}</td>
                <td class="px-3 py-2.5 text-[11px] font-mono text-slate-400 hidden lg:table-cell">${formula}</td>
                <td class="px-3 py-2.5 text-xs font-mono text-right">${result}</td>
            </tr>`).join('')}
        </tbody>
    </table>`;
}

// ── Multi-test comparison table (injected as innerHTML) ────────────────────────
export function _buildComparisonTable(t1, t2, t3, r1, r2, r3, en1=true, en2=true, en3=true) {
    const f2 = v => v != null ? Number(v).toFixed(2) : '—';
    const f1 = v => v != null ? Number(v).toFixed(1) : '—';
    const _na = (en, val) => en ? val : '<span class="text-slate-600">N/A</span>';
    const imp21 = (r1 && r2 && en1 && en2) ? (r1.shortfall - r2.shortfall).toFixed(2) : '—';
    const imp32 = (r2 && r3 && en2 && en3) ? (r2.shortfall - r3.shortfall).toFixed(2) : '—';
    const imp31 = (r1 && r3 && en1 && en3) ? (r1.shortfall - r3.shortfall).toFixed(2) : '—';

    const capCls = v => { const n = parseFloat(v); return n >= 100 ? 'text-emerald-400' : n >= 95 ? 'text-amber-400' : 'text-rose-400'; };
    const sfCls  = v => { const n = parseFloat(v); return n > 0 ? 'text-rose-400' : n < 0 ? 'text-emerald-400' : 'text-slate-400'; };
    const impCls = v => { const n = parseFloat(v); return n > 0 ? 'text-emerald-400' : n < 0 ? 'text-rose-400' : 'text-slate-400'; };

    const rows = [
        ['Water Flow',                   'm³/hr', _na(en1,f1(t1.flow)),       _na(en2,f1(t2.flow)),       _na(en3,f1(t3.flow)),       ''],
        ['WBT — Wet Bulb Temp.',         '°C',    _na(en1,f2(t1.wbt)),        _na(en2,f2(t2.wbt)),        _na(en3,f2(t3.wbt)),        ''],
        ['HWT — Hot Water Temp.',        '°C',    _na(en1,f2(t1.hwt)),        _na(en2,f2(t2.hwt)),        _na(en3,f2(t3.hwt)),        ''],
        ['CWT — Cold Water Temp.',       '°C',    _na(en1,f2(t1.cwt)),        _na(en2,f2(t2.cwt)),        _na(en3,f2(t3.cwt)),        ''],
        ['Fan Power at Motor Inlet',     'kW',    _na(en1,f2(t1.fan_power)),  _na(en2,f2(t2.fan_power)),  _na(en3,f2(t3.fan_power)),  ''],
        ['Range (HWT−CWT)',              '°C',    _na(en1,f2(r1?.test_range)),_na(en2,f2(r2?.test_range)),_na(en3,f2(r3?.test_range)),''],
        ['Approach (CWT−WBT)',           '°C',    _na(en1,f2(t1.cwt-t1.wbt)),_na(en2,f2(t2.cwt-t2.wbt)),_na(en3,f2(t3.cwt-t3.wbt)),''],
        ['Adjusted Water Flow',          'm\u00b3/hr', _na(en1,f1(r1?.adj_flow)),  _na(en2,f1(r2?.adj_flow)),  _na(en3,f1(r3?.adj_flow)),  ''],
        ['Predicted CWT (CP2)',          '\u00b0C',    _na(en1,f2(r1?.pred_cwt)),  _na(en2,f2(r2?.pred_cwt)),  _na(en3,f2(r3?.pred_cwt)),  ''],
        ['CWT Shortfall \u2014 App. C',       '\u00b0C',    _na(en1,r1 ? `${r1.shortfall>0?'+':''}${f2(r1.shortfall)}`:'—'), _na(en2,r2?`${r2.shortfall>0?'+':''}${f2(r2.shortfall)}`:'—'), _na(en3,r3?`${r3.shortfall>0?'+':''}${f2(r3.shortfall)}`:'—'), 'sf'],
        ['CW Deviation \u2014 App. M (pg64)',  '\u00b0C',    _na(en1,r1?.appM_cwd!=null?`${r1.appM_cwd>0?'+':''}${f2(r1.appM_cwd)}`:'—'), _na(en2,r2?.appM_cwd!=null?`${r2.appM_cwd>0?'+':''}${f2(r2.appM_cwd)}`:'—'), _na(en3,r3?.appM_cwd!=null?`${r3.appM_cwd>0?'+':''}${f2(r3.appM_cwd)}`:'—'), 'appM'],
        ['Capability',                   '%',     _na(en1,f1(r1?.capability)),_na(en2,f1(r2?.capability)),_na(en3,f1(r3?.capability)),'cap'],
        ['Improvement vs Previous Test', '\u00b0C',    '\u2014',               imp21 !== '\u2014' ? `+${imp21}` : '\u2014', imp32 !== '\u2014' ? `+${imp32}` : '\u2014', 'imp'],
        ['Cumulative Improvement vs T1', '\u00b0C',    '\u2014',               imp21 !== '\u2014' ? `+${imp21}` : '\u2014', imp31 !== '\u2014' ? `+${imp31}` : '\u2014', 'imp'],
    ];

    const rowHtml = rows.map(([param, unit, v1, v2, v3, type]) => {
        const bg   = type === 'sf'   ? 'bg-yellow-500/5'  :
                     type === 'appM' ? 'bg-amber-500/5'   :
                     type === 'imp'  ? 'bg-emerald-500/5' : '';
        const _cls = (v) => type === 'cap'  ? capCls(v) :
                            type === 'sf'   ? sfCls(v)  :
                            type === 'appM' ? sfCls(v)  :
                            type === 'imp'  ? impCls(v) : 'text-slate-300';
        const c1 = _cls(v1), c2 = _cls(v2), c3 = _cls(v3);
        const labelCls = type === 'appM' ? 'text-amber-300/80' : 'text-slate-300';
        return `<tr class="hover:bg-white/[0.02] ${bg}">
            <td class="px-3 py-2 text-xs font-mono ${labelCls}">${param}</td>
            <td class="px-3 py-2 text-xs font-mono text-center text-slate-500">${unit}</td>
            <td class="px-3 py-2 text-xs font-mono text-right ${c1}">${v1}</td>
            <td class="px-3 py-2 text-xs font-mono text-right ${c2}">${v2}</td>
            <td class="px-3 py-2 text-xs font-mono text-right ${c3} font-bold">${v3}</td>
        </tr>`;
    }).join('');

    return `<thead>
            <tr class="border-b border-white/10 bg-slate-900/60">
                <th class="px-3 py-2.5 text-left text-[10px] font-black uppercase tracking-widest text-slate-400">Parameter</th>
                <th class="px-3 py-2.5 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">Unit</th>
                <th class="px-3 py-2.5 text-right text-[10px] font-black uppercase tracking-widest text-slate-300">Test 1<br><span class="text-slate-500 font-normal normal-case tracking-normal">Pre-Baseline</span></th>
                <th class="px-3 py-2.5 text-right text-[10px] font-black uppercase tracking-widest text-slate-300">Test 2<br><span class="text-slate-500 font-normal normal-case tracking-normal">Post Fan Pitch</span></th>
                <th class="px-3 py-2.5 text-right text-[10px] font-black uppercase tracking-widest text-cyan-400">Test 3 ★<br><span class="text-slate-500 font-normal normal-case tracking-normal">Post Fill Dist.</span></th>
            </tr>
        </thead>
        <tbody class="divide-y divide-white/[0.04]">${rowHtml}</tbody>`;
}

// ── Design conditions grid (injected as innerHTML) ─────────────────────────────
export function _buildDesignGrid(design) {
    const f2 = v => v != null ? Number(v).toFixed(2) : '—';
    const items = [
        ['WBT °C',      f2(design.wbt),              'Design wet-bulb temperature'],
        ['CWT °C',      f2(design.cwt),              'Target cold water temperature'],
        ['HWT °C',      f2(design.hwt),              'Design hot water temperature'],
        ['Flow m³/hr',  Number(design.flow).toFixed(1), 'Water flow at 100% design'],
        ['Fan Power kW',f2(design.fan_power),         'Design fan shaft power'],
        ['L/G Ratio',   f2(design.lg),               'Liquid-to-gas ratio'],
    ];
    return items.map(([label, val, title]) =>
        `<div class="rounded-lg bg-slate-900/60 border border-white/5 p-2.5 text-center" title="${title}">
            <p class="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">${label}</p>
            <p class="text-sm font-black font-mono text-slate-200">${val}</p>
        </div>`
    ).join('');
}

// ── Results preview — full in-browser report document ─────────────────────────
export async function previewAllTests(ui) {
    const btn      = document.getElementById('previewAllTestsBtn');
    const errorEl  = document.getElementById('previewError');
    const origHtml = btn.innerHTML;

    const _set  = (id, val) => { const el = document.getElementById(id); if (el) el.innerHTML = val; };
    const _text = (id, val) => { const el = document.getElementById(id); if (el) el.innerText  = val; };

    btn.innerHTML = `<svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Calculating…`;
    btn.disabled = true;
    if (errorEl) errorEl.classList.add('hidden');

    try {
        const design = _getDesign(ui);
        if (!design.flow) throw new Error('Design flow (Step 3) is required.');

        const t1 = { flow: _n('rep-t1-flow',2998),    wbt: _n('rep-t1-wbt',25.25),  hwt: _n('rep-t1-hwt',44.67), cwt: _n('rep-t1-cwt',35.08), fan_power: _n('rep-t1-fanpow',97.04) };
        const t2 = { flow: _n('rep-t2-flow',3067.21),  wbt: _n('rep-t2-wbt',24.22),  hwt: _n('rep-t2-hwt',43.21), cwt: _n('rep-t2-cwt',32.89), fan_power: _n('rep-t2-fanpow',116.24) };
        const t3 = { flow: _n('rep-flow',3680),         wbt: _n('rep-test-wbt',21.7), hwt: _n('rep-hwt',42.13),   cwt: _n('rep-cwt',32.4),     fan_power: _n('rep-test-fanpow',117) };

        // ── Only calculate enabled tests ──────────────────────────────────────
        const en1 = _isTestEnabled(1), en2 = _isTestEnabled(2), en3 = _isTestEnabled(3);
        if (!en1 && !en2 && !en3) throw new Error('Please enable at least one test (T1 / T2 / T3) before running verification.');

        const offsets = _getOffsetsFromUi(ui);
        const _maybeCalc = (enabled, t) => enabled ? _calcAtc(design, t, offsets) : Promise.resolve(null);
        const [r1, r2, r3] = await Promise.all([
            _maybeCalc(en1, t1), _maybeCalc(en2, t2), _maybeCalc(en3, t3),
        ]);

        // ── Document header ────────────────────────────────────────────────────
        _text('pv-doc-title',    _v('rep-title',       'CT PERFORMANCE EVALUATION REPORT'));
        _text('pv-doc-client',   _v('rep-client',      '—'));
        _text('pv-doc-asset',    _v('rep-asset',       '—'));
        _text('pv-doc-repdate',  _v('rep-report-date', '—'));
        _text('pv-doc-testdate', _v('rep-test-date',   '—'));

        const overallEl = document.getElementById('pv-overall-verdict');
        if (overallEl) {
            // Use the last enabled test's capability for the overall verdict
            const lastR = en3 ? r3 : en2 ? r2 : r1;
            const isPass = lastR.capability >= 100;
            const isMarg = lastR.capability >= 95;
            overallEl.textContent = isPass ? 'OVERALL: PASS ✓' : isMarg ? 'OVERALL: MARGINAL' : 'OVERALL: FAIL ✗';
            const badgeCls = isPass
                ? 'border-emerald-500/50 text-emerald-300 bg-emerald-500/10 shadow-[0_0_24px_rgba(16,185,129,0.18)] verd-pass'
                : isMarg
                ? 'border-amber-500/40  text-amber-300  bg-amber-500/10'
                : 'border-rose-500/40   text-rose-300   bg-rose-500/10';
            overallEl.className = `inline-block px-6 py-3 rounded-2xl text-base font-black uppercase tracking-widest border-2 ${badgeCls}`;
        }

        // ── Tests-conducted counter (dynamic) ──────────────────────────────────
        const activeCount = [en1, en2, en3].filter(Boolean).length;
        _text('pv-tests-conducted', `${activeCount} of 3 Complete`);

        // ── Executive summary ──────────────────────────────────────────────────
        [[r1,en1,'pv-cap1','pv-verdict1'],[r2,en2,'pv-cap2','pv-verdict2'],[r3,en3,'pv-cap3','pv-verdict3']].forEach(([r, en, capId, verdId]) => {
            const capEl  = document.getElementById(capId);
            if (capEl)  { capEl.textContent  = en ? `${r.capability?.toFixed(1) ?? '—'} %` : 'N/A'; capEl.className = `text-2xl font-black font-mono ${en ? _capTextCls(r.capability) : 'text-slate-600'}`; }
            const verdEl = document.getElementById(verdId);
            if (verdEl) { verdEl.textContent = en ? _capVerdict(r.capability) : 'Skipped'; verdEl.className = `text-[11px] font-black uppercase mt-1 ${en ? _capTextCls(r.capability) : 'text-slate-600'}`; }
        });
        _pvRenderCapChart([en1 ? r1?.capability : null, en2 ? r2?.capability : null, en3 ? r3?.capability : null]);

        // ── Design conditions ──────────────────────────────────────────────────
        const designGrid = document.getElementById('pv-design-grid');
        if (designGrid) designGrid.innerHTML = _buildDesignGrid(design);
        _text('pv-design-note', `Merkel constants: C = ${design.constant_c}, m = ${design.constant_m} · Design range = ${(design.hwt - design.cwt).toFixed(2)} °C · 90% flow = ${(design.flow * 0.9).toFixed(1)} · 100% = ${design.flow.toFixed(1)} · 110% = ${(design.flow * 1.1).toFixed(1)} m³/hr · Density: Kell (1975)`);

        // ── Per-test sections ──────────────────────────────────────────────────
        const f2 = v => v != null ? Number(v).toFixed(2) : '—';
        const f1 = v => v != null ? Number(v).toFixed(1) : '—';

        [['1',t1,r1,en1],['2',t2,r2,en2],['3',t3,r3,en3]].forEach(([p, t, r, en]) => {
            // Find the wrapping section (pv1/pv2/pv3 result cards in the preview panel)
            const sectionEl = document.getElementById(`pv${p}-calc-table`)?.closest?.('.rounded-3xl');
            if (sectionEl) sectionEl.style.display = en ? '' : 'none';

            if (!en || !r) return; // skip rendering for disabled tests

            // Measured inputs
            _text(`pv${p}-in-wbt`,    `${f2(t.wbt)} °C`);
            _text(`pv${p}-in-hwt`,    `${f2(t.hwt)} °C`);
            _text(`pv${p}-in-cwt`,    `${f2(t.cwt)} °C`);
            _text(`pv${p}-in-flow`,   `${f1(t.flow)} m³/hr`);
            _text(`pv${p}-in-fanpow`, `${f2(t.fan_power)} kW`);

            // Calc walkthrough table
            const calcDiv = document.getElementById(`pv${p}-calc-table`);
            if (calcDiv) calcDiv.innerHTML = _buildPvCalcTable(design, t, r);

            // CP1 WBT label
            _text(`pv${p}-cp1-wbt`, `${f2(t.wbt)} °C`);

            // Charts
            if (r.cross_plot_1) _pvRenderCp1(`pv${p}-cp1`, r.cross_plot_1, t.wbt);
            if (r.cross_plot_2) _pvRenderCp2(`pv${p}-cp2`, r.cross_plot_2);

            // Results strip
            _text(`pv${p}-range`, `${f2(r.test_range)} \u00b0C`);
            _text(`pv${p}-flow`,  `${f1(r.adj_flow)} m\u00b3/hr`);
            _text(`pv${p}-cwt`,   `${f2(r.pred_cwt)} \u00b0C`);

            const sfEl = document.getElementById(`pv${p}-shortfall`);
            if (sfEl) { sfEl.textContent = `${r.shortfall > 0 ? '+' : ''}${f2(r.shortfall)} \u00b0C`; sfEl.className = `text-sm font-black font-mono ${_sfTextCls(r.shortfall)}`; }

            // ── Appendix M: Cold Water Temperature Deviation ──────────────────
            const appMEl = document.getElementById(`pv${p}-appM-cwd`);
            if (appMEl) {
                const cwd = r.appM_cwd;
                if (cwd != null) {
                    appMEl.textContent = `${cwd > 0 ? '+' : ''}${f2(cwd)} \u00b0C`;
                    appMEl.className   = `text-sm font-black font-mono ${cwd > 0 ? 'text-rose-400' : 'text-emerald-400'}`;
                } else {
                    appMEl.textContent = '\u2014';
                    appMEl.className   = 'text-sm font-black font-mono text-slate-600';
                }
            }

            const capEl = document.getElementById(`pv${p}-cap`);
            if (capEl) { capEl.textContent = `${f1(r.capability)} %`; capEl.className = `text-sm font-black font-mono ${_capTextCls(r.capability)}`; }

            const badge = document.getElementById(`pv${p}-verdict-badge`);
            if (badge) { badge.textContent = _capVerdict(r.capability); badge.className = `px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border ${_capBadgeCls(r.capability)}`; }
        });

        // ── Improvement deltas (only between enabled tests) ────────────────────
        const imp21 = (en1 && en2 && r1 && r2) ? r1.shortfall - r2.shortfall : null;
        const imp32 = (en2 && en3 && r2 && r3) ? r2.shortfall - r3.shortfall : null;
        const imp31 = (en1 && en3 && r1 && r3) ? r1.shortfall - r3.shortfall : null;

        const _setImp = (id, val, large = false) => {
            const el = document.getElementById(id); if (!el) return;
            if (val == null) { el.textContent = '—'; el.className = `${large ? 'text-2xl' : 'text-xl'} font-black font-mono text-slate-600`; return; }
            const sign = val >= 0 ? '+' : '';
            el.textContent = `${sign}${val.toFixed(2)} °C`;
            el.className   = `${large ? 'text-2xl' : 'text-xl'} font-black font-mono ${val >= 0 ? 'text-emerald-400' : 'text-rose-400'}`;
        };
        _setImp('pv-imp21',     imp21);
        _setImp('pv-imp32',     imp32);
        _setImp('pv-cumulative',imp31, true);

        const _setTestImp = (id, val) => {
            const el = document.getElementById(id); if (!el) return;
            if (val == null) { el.textContent = '—'; el.className = 'text-[11px] font-black font-mono text-slate-600'; return; }
            el.textContent = `${val >= 0 ? '+' : ''}${val.toFixed(2)} °C`;
            el.className   = `text-[11px] font-black font-mono ${val >= 0 ? 'text-emerald-400' : 'text-rose-400'}`;
        };
        _setTestImp('pv2-imp', imp21);
        _setTestImp('pv3-imp', imp32);

        // ── Trend chart ────────────────────────────────────────────────────────
        _pvRenderTrendChart(
            [en1?r1?.shortfall:null, en2?r2?.shortfall:null, en3?r3?.shortfall:null],
            [en1?r1?.capability:null, en2?r2?.capability:null, en3?r3?.capability:null]
        );

        // ── Comparison table ───────────────────────────────────────────────────
        const compWrapper = document.getElementById('pv-comparison-table');
        if (compWrapper) compWrapper.innerHTML = _buildComparisonTable(t1, t2, t3, r1, r2, r3, en1, en2, en3);

        // ── Update modal header ────────────────────────────────────────────────
        const modalSubtitle = [_v('rep-client',''), _v('rep-asset',''), _v('rep-test-date','')].filter(Boolean).join(' · ');
        _text('pv-modal-subtitle', modalSubtitle || 'ATC-105 Report Preview');
        const mvEl = document.getElementById('pv-modal-verdict');
        if (mvEl) {
            const lastR = en3 ? r3 : en2 ? r2 : r1;
            const isPass = lastR.capability >= 100;
            const isMarg = lastR.capability >= 95;
            mvEl.textContent = isPass ? 'PASS ✓' : isMarg ? 'MARGINAL' : 'FAIL ✗';
            mvEl.className   = `shrink-0 ml-1 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border ${_capBadgeCls(lastR.capability)}`;
        }

        // ── Show "Re-open overlay" hint inside the step card ──────────────────
        const hintEl = document.getElementById('previewReadyHint');
        if (hintEl) { hintEl.classList.remove('hidden'); hintEl.classList.add('flex'); }

        // ── Open the preview modal ─────────────────────────────────────────────
        if (typeof openPreviewModal === 'function') openPreviewModal();

        // ── Update live Test-3 mini-preview card (use last enabled test) ───────
        const pvCard = document.getElementById('atcPreview');
        const liveR  = en3 ? r3 : en2 ? r2 : r1;
        if (pvCard && liveR) {
            _text('atc-prev-range',      liveR.test_range  != null ? `${liveR.test_range.toFixed(2)} °C` : '—');
            _text('atc-prev-adjflow',    liveR.adj_flow    != null ? liveR.adj_flow.toFixed(1)            : '—');
            _text('atc-prev-predcwt',    liveR.pred_cwt    != null ? liveR.pred_cwt.toFixed(2)            : '—');
            _text('atc-prev-shortfall',  liveR.shortfall   != null ? liveR.shortfall.toFixed(2)           : '—');
            _text('atc-prev-capability', liveR.capability  != null ? `${liveR.capability.toFixed(1)} %`   : '—');
            pvCard.classList.remove('hidden');
        }

    } catch (err) {
        if (errorEl) { errorEl.innerText = `Preview failed: ${err.message}`; errorEl.classList.remove('hidden'); }
    } finally {
        btn.innerHTML = origHtml;
        btn.disabled  = false;
    }
}
