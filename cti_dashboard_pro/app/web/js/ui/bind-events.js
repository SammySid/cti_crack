import { INPUT_IDS, isCurveAffectingInput } from './constants.js';
import { generateReport, updateAtcPreview, syncDesignFromThermal, bindFilterUpload, previewAllTests } from './report.js';

export function bindEvents(ui) {
    const debouncedUpdateAll = ui.debounce(ui.updateAll, 300);

    // ── All canonical inputs (now all in the main panel) ─────────────────────
    INPUT_IDS.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('input', (e) => {
            let val = e.target.value;
            if (e.target.type === 'number') {
                const parsed = Number.parseFloat(e.target.value);
                if (!Number.isFinite(parsed)) return;
                val = parsed;
            }
            ui.inputs[id] = val;
            ui.saveInputs();
            ui.updateFastMetrics();
            if (isCurveAffectingInput(id)) debouncedUpdateAll();
        });
    });

    // ── Export / Reset buttons ───────────────────────────────────────────────
    document.getElementById('exportExcel')?.addEventListener('click', () => ui.exportData());
    document.getElementById('exportPDF')?.addEventListener('click',   () => window.print());
    document.getElementById('resetDefaults')?.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all parameters to default values?')) {
            localStorage.removeItem('sarma_thermal_inputs');
            location.reload();
        }
    });

    // ── Auto-Calibration (Fit Curve) ─────────────────────────────────────────
    document.getElementById('btnCalibrateC')?.addEventListener('click', async () => {
        const btn       = document.getElementById('btnCalibrateC');
        const targetCWT = parseFloat(document.getElementById('targetCWT').value);
        if (isNaN(targetCWT)) return alert('Please enter a valid Target CWT');

        btn.innerText = 'Fitting...';
        btn.disabled  = true;

        try {
            const range = ui.inputs.designHWT - ui.inputs.designCWT;
            const resp  = await fetch('/api/calculate/calibrate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    targetCWT:   targetCWT,
                    designWBT:   ui.inputs.designWBT,
                    designRange: range,
                    lgRatio:     ui.inputs.lgRatio,
                    constantM:   ui.inputs.constantM
                })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Calibration failed');

            const cInput    = document.getElementById('constantC');
            cInput.value    = data.constantC;
            ui.inputs.constantC = data.constantC;
            ui.saveInputs();
            ui.updateFastMetrics();
            debouncedUpdateAll();

            btn.innerText = 'Success!';
            setTimeout(() => { btn.innerText = 'Fit Curve'; btn.disabled = false; }, 1000);
        } catch (err) {
            alert('Calibration Error: ' + err.message);
            btn.innerText = 'Fit Curve';
            btn.disabled  = false;
        }
    });

    // ── Clear Safety Margins ─────────────────────────────────────────────────
    document.getElementById('btnClearMargins')?.addEventListener('click', () => {
        const marginIds = [
            'offsetWbt20',
            'off90r80', 'off90r100', 'off90r120',
            'off100r80', 'off100r100', 'off100r120',
            'off110r80', 'off110r100', 'off110r120'
        ];

        marginIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = 0;
            ui.inputs[id] = 0;
        });

        const constCEl = document.getElementById('constantC');
        if (constCEl) {
            const defaultValue = parseFloat(constCEl.defaultValue) || 2.51;
            constCEl.value      = defaultValue;
            ui.inputs.constantC = defaultValue;
            constCEl.classList.add('bg-amber-500/20');
            setTimeout(() => constCEl.classList.remove('bg-amber-500/20'), 500);
        }

        ui.saveInputs();
        ui.updateFastMetrics();
        debouncedUpdateAll();
    });

    // ── Tab navigation ───────────────────────────────────────────────────────
    document.getElementById('tabThermal')?.addEventListener('click',    () => ui.switchTab('thermal'));
    document.getElementById('tabPrediction')?.addEventListener('click', () => {
        ui.switchTab('prediction');
        ui.calculatePrediction();
    });
    document.getElementById('tabPsychro')?.addEventListener('click', () => ui.switchTab('psychro'));
    document.getElementById('tabFilter')?.addEventListener('click',   () => ui.switchTab('filter'));
    document.getElementById('tabReport')?.addEventListener('click',   () => ui.switchTab('report'));

    document.getElementById('generateReportBtn')?.addEventListener('click',  () => generateReport(ui));
    document.getElementById('previewAllTestsBtn')?.addEventListener('click', () => previewAllTests(ui));

    // ── ATC-105 Report Builder: live preview ──────────────────────────────────
    const atcInputIds = [
        'rep-design-wbt', 'rep-design-cwt', 'rep-design-hwt', 'rep-design-flow', 'rep-design-fanpow',
        'rep-design-lg', 'rep-density-override',
        'rep-test-wbt', 'rep-cwt', 'rep-hwt', 'rep-flow', 'rep-test-fanpow',
    ];
    const debouncedAtcPreview = ui.debounce(() => updateAtcPreview(ui), 500);
    atcInputIds.forEach(id => {
        document.getElementById(id)?.addEventListener('input', debouncedAtcPreview);
    });

    document.getElementById('rep-sync-from-thermal')?.addEventListener('click', () => syncDesignFromThermal(ui));
    bindFilterUpload(ui);

    // ── Filter tool ──────────────────────────────────────────────────────────
    document.getElementById('runFilterAction')?.addEventListener('click', () => ui.runFilterTool());
    document.getElementById('filterSourcePath')?.addEventListener('input', (e) => {
        ui.filterSettings.sourcePath = e.target.value.trim();
        ui.saveFilterSettings();
    });
    document.getElementById('filterStartTime')?.addEventListener('input', (e) => {
        ui.filterSettings.startTime = e.target.value;
        ui.saveFilterSettings();
    });
    document.getElementById('filterEndTime')?.addEventListener('input', (e) => {
        ui.filterSettings.endTime = e.target.value;
        ui.saveFilterSettings();
    });
    document.getElementById('filterProcessAll')?.addEventListener('change', (e) => {
        ui.filterSettings.processAll = e.target.checked;
        ui.saveFilterSettings();
        ui.bindFilterProcessAllToggle && ui.bindFilterProcessAllToggle();
    });
    ui.bindFilterProcessAllToggle();

    // ── Psychrometric calculator ─────────────────────────────────────────────
    ['p-dbt', 'p-wbt', 'p-alt'].forEach(id => {
        document.getElementById(id)?.addEventListener('input', ui.debounce(ui.calculatePsychrometrics, 150));
    });

    // ── Performance prediction ───────────────────────────────────────────────
    ['pred-wbt', 'pred-range', 'pred-lg', 'pred-c', 'pred-m'].forEach(id => {
        document.getElementById(id)?.addEventListener('input', ui.debounce(ui.calculatePrediction, 100));
    });

    // ── Print mode ───────────────────────────────────────────────────────────
    window.onbeforeprint = () => { ui.isPrinting = true;  ui.updateCharts(); };
    window.onafterprint  = () => { ui.isPrinting = false; ui.updateCharts(); };

    // ── Initialise ───────────────────────────────────────────────────────────
    ui.updateExportUiState('Calculating curves...');
    ui.updateFilterUiState('Filter tool ready.');
    ui.switchTab('thermal');
    ui.syncFilterSettingsToUi();
    ui.calculatePsychrometrics();
}
