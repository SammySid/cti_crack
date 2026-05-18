import { _n, _v, _lines, _getDesign, _getOffsetsFromUi, _calcAtc } from './report-helpers.js';
import { _isTestEnabled } from './report-toggles.js';

export async function generateReport(ui, sourceBtn = null) {
    const btn = sourceBtn;
    const statusEl = document.getElementById('reportStatus');
    const originalHtml = btn ? btn.innerHTML : '';

    const setStatus = (msg, isError = false) => {
        if (statusEl) {
            statusEl.innerText = msg;
            statusEl.classList.remove('hidden', 'text-cyan-400', 'text-rose-400');
            statusEl.classList.add(isError ? 'text-rose-400' : 'text-cyan-400');
        }
    };

    if (btn) {
        btn.innerHTML = `<svg class="animate-spin w-5 h-5 inline mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            Calculating…`;
        btn.disabled = true;
    }
    setStatus('Running ATC-105 calculations for all 3 tests…');

    try {
        // ── Shared design conditions ──────────────────────────────────────
        const design = _getDesign(ui);
        if (!design.flow) throw new Error('Design flow is required.');

        // ── Three test datasets ───────────────────────────────────────────
        const t1 = {
            flow:      _n('rep-t1-flow',   2998),
            wbt:       _n('rep-t1-wbt',    25.25),
            hwt:       _n('rep-t1-hwt',    44.67),
            cwt:       _n('rep-t1-cwt',    35.08),
            fan_power: _n('rep-t1-fanpow', 97.04),
        };
        const t2 = {
            flow:      _n('rep-t2-flow',   3067.21),
            wbt:       _n('rep-t2-wbt',    24.22),
            hwt:       _n('rep-t2-hwt',    43.21),
            cwt:       _n('rep-t2-cwt',    32.89),
            fan_power: _n('rep-t2-fanpow', 116.24),
        };
        const t3 = {
            flow:      _n('rep-flow',        3680),
            wbt:       _n('rep-test-wbt',    21.7),
            hwt:       _n('rep-hwt',         42.13),
            cwt:       _n('rep-cwt',         32.4),
            fan_power: _n('rep-test-fanpow', 117),
        };

        // ── Respect test toggles ──────────────────────────────────────────────
        const gr_en1 = _isTestEnabled(1), gr_en2 = _isTestEnabled(2), gr_en3 = _isTestEnabled(3);
        if (!gr_en1 && !gr_en2 && !gr_en3) throw new Error('Please enable at least one test (T1 / T2 / T3) before generating the report.');

        // ── Run only enabled ATC-105 calculations in parallel ─────────────────
        const offsets = _getOffsetsFromUi(ui);
        const _maybeCalcR = (en, t) => en ? _calcAtc(design, t, offsets) : Promise.resolve(null);
        const [atc_pre, atc_post, atc_dist] = await Promise.all([
            _maybeCalcR(gr_en1, t1),
            _maybeCalcR(gr_en2, t2),
            _maybeCalcR(gr_en3, t3),
        ]);

        // Annotate fan powers (not in API response; needed for table)
        if (atc_pre)  { atc_pre.fan_power_design  = design.fan_power; atc_pre.fan_power_test  = t1.fan_power; }
        if (atc_post) { atc_post.fan_power_design = design.fan_power; atc_post.fan_power_test = t2.fan_power; }
        if (atc_dist) { atc_dist.fan_power_design = design.fan_power; atc_dist.fan_power_test = t3.fan_power; }

        // Update live preview card with last enabled test
        const liveAtc = gr_en3 ? atc_dist : gr_en2 ? atc_post : atc_pre;
        const pv = document.getElementById('atcPreview');
        if (pv && liveAtc) {
            document.getElementById('atc-prev-range').innerText      = `${liveAtc.test_range?.toFixed(2) ?? '—'} °C`;
            document.getElementById('atc-prev-adjflow').innerText    = liveAtc.adj_flow?.toFixed(1)  ?? '—';
            document.getElementById('atc-prev-predcwt').innerText    = liveAtc.pred_cwt?.toFixed(2)  ?? '—';
            document.getElementById('atc-prev-shortfall').innerText  = liveAtc.shortfall?.toFixed(2) ?? '—';
            document.getElementById('atc-prev-capability').innerText = liveAtc.capability != null ? `${liveAtc.capability.toFixed(1)} %` : '—';
            pv.classList.remove('hidden');
        }

        if (btn) {
            btn.innerHTML = `<svg class="animate-spin w-5 h-5 inline mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                Generating PDF…`;
        }
        setStatus('ATC-105 calculated for all tests. Rendering PDF…');

        // ── Derived values ────────────────────────────────────────────────
        // Air flow is no longer a UI input; fan area is still collected for
        // velocity calculation if needed, but air flow rows are omitted from table.
        const airArea = _n('rep-fan-area', 92.25);

        const sf1 = atc_pre?.shortfall;
        const sf2 = atc_post?.shortfall;
        const sf3 = atc_dist?.shortfall;

        const imp_2v1  = (sf1 != null && sf2 != null) ? parseFloat((sf1 - sf2).toFixed(2)) : '—';
        const imp_3v2  = (sf2 != null && sf3 != null) ? parseFloat((sf2 - sf3).toFixed(2)) : '—';
        const imp_3v1  = (sf1 != null && sf3 != null) ? parseFloat((sf1 - sf3).toFixed(2)) : '—';

        // ── Multi-test comparison table (all 3 shortfalls now populated) ──
        const final_data_table = [
            { name: 'Water Flow',               unit: 'M3/hr',
              test1: t1.flow,   test2: t2.flow,   test3: t3.flow },
            { name: 'WBT',                      unit: 'Deg.C',
              test1: t1.wbt,    test2: t2.wbt,    test3: t3.wbt },
            { name: 'HWT',                      unit: 'Deg.C',
              test1: t1.hwt,    test2: t2.hwt,    test3: t3.hwt },
            { name: 'CWT',                      unit: 'Deg.C',
              test1: t1.cwt,    test2: t2.cwt,    test3: t3.cwt },
            { name: 'Fan Power At Motor Inlet', unit: 'KW',
              test1: t1.fan_power, test2: t2.fan_power, test3: t3.fan_power },
            { name: 'Range',                    unit: 'Deg.C',
              test1: parseFloat((t1.hwt - t1.cwt).toFixed(2)),
              test2: parseFloat((t2.hwt - t2.cwt).toFixed(2)),
              test3: parseFloat((t3.hwt - t3.cwt).toFixed(2)) },
            { name: 'Approach',                 unit: 'Deg.C',
              test1: parseFloat((t1.cwt - t1.wbt).toFixed(2)),
              test2: parseFloat((t2.cwt - t2.wbt).toFixed(2)),
              test3: parseFloat((t3.cwt - t3.wbt).toFixed(2)) },
            { name: 'CWT Deviation from Design', unit: 'Deg.C',
              test1: sf1 != null ? sf1.toFixed(2) : '—',
              test2: sf2 != null ? sf2.toFixed(2) : '—',
              test3: sf3 != null ? sf3.toFixed(2) : '—' },
            { name: 'Capability',               unit: '%',
              test1: atc_pre?.capability  != null ? atc_pre.capability.toFixed(1)  : '—',
              test2: atc_post?.capability != null ? atc_post.capability.toFixed(1) : '—',
              test3: atc_dist?.capability != null ? atc_dist.capability.toFixed(1) : '—' },
            { name: 'Improvement vs Previous Test', unit: 'Deg.C',
              test1: '—', test2: imp_2v1, test3: imp_3v2 },
            { name: 'Cumulative Improvement vs Test 1', unit: 'Deg.C',
              test1: '—', test2: imp_2v1, test3: imp_3v1 },
        ];

        // ── Full PDF payload ──────────────────────────────────────────────
        const pdfPayload = {
            // Cover
            report_title: _v('rep-title', 'CT PERFORMANCE EVALUATION REPORT'),
            client:       _v('rep-client'),
            asset:        _v('rep-asset'),
            test_date:    _v('rep-test-date'),
            report_date:  _v('rep-report-date'),

            // Narrative
            preamble_paragraphs: _lines('rep-preamble'),
            conclusions:         _lines('rep-conclusions'),
            members_client:      _lines('rep-members-client'),
            members_ssctc:       _lines('rep-members-ssctc'),

            // Standard sections
            assessment_method: [
                `Pre test was conducted on ${_v('rep-test-date')}.`,
                'Cell has been isolated at the basin level for collection of cold water directly from the rain zone.',
                'All required data was collected and reports have been prepared for each test stage.',
                'Since different conditions apply in each test, both pre and post tests have been compared to the design conditions. The difference between pre and post tests has been established accordingly.',
            ],
            instrument_placement: [
                'Air flow was measured using Data Logging anemometer as per CTI ATC-143 Method of equal area — 10 traverses per quadrant (40 readings total for one fan).',
                'Hot water temperature was taken at inlet of the hot water to the cooling tower.',
                'Cold water temperature: 24 RTD sensors placed at air-inlet sides of the isolated cell (12 per side).',
                'Water flow was measured using UFM (GE Make) on the riser.',
                'WBT/DBT was measured using wet-bulb automatic stations recording every minute.',
                'Power to the fan motor was noted from the client MCC.',
            ],
            suggestions: _lines('rep-data-notes'),

            // Three independent ATC-105 analyses
            atc105_pre:  atc_pre,
            atc105_post: atc_post,
            atc105_dist: atc_dist,

            // Comparison table (all three shortfalls populated)
            final_data_table,
            data_notes: _lines('rep-data-notes'),

            // Fan area (air flow no longer collected as UI input)
            airflow: {
                area: airArea,
            },
        };

        // ── POST to generate PDF (Step 1: server stores PDF, returns token) ─
        // We use a two-step token download instead of a blob:// URL so that
        // external download managers like IDM can fetch the file via a real
        // HTTP GET URL without running into the blob:// sandbox restriction.
        const safeName = _v('rep-client', 'Report').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 40);
        const filename  = `ATC105_${safeName}_${_v('rep-test-date', '').replace(/\s/g, '_')}.pdf`;
        pdfPayload._filename = filename;  // tell backend what filename to serve

        const pdfResp = await fetch('/api/generate-pdf-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pdfPayload),
        });

        if (!pdfResp.ok) {
            const err = await pdfResp.text();
            throw new Error(`PDF generation failed (${pdfResp.status}): ${err}`);
        }

        const { token } = await pdfResp.json();

        // Step 2: navigate to the real GET URL — IDM/browsers download this
        // as a normal file without any blob:// sandbox restriction.
        window.location.href = `/api/download-pdf/${token}`;

        setStatus(`PDF generated successfully — ${filename}`);

    } catch (err) {
        console.error('Report generation failed:', err);
        setStatus(`Error: ${err.message}`, true);
        alert(`Failed to generate report:\n${err.message}`);
    } finally {
        if (btn) {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    }
}
