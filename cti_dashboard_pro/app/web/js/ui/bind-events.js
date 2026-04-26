import { INPUT_IDS, isCurveAffectingInput } from './constants.js';
import { generateReport, updateAtcPreview, syncDesignFromThermal, bindFilterUpload, previewAllTests } from './report.js';

export function bindEvents(ui) {
    const debouncedUpdateAll = ui.debounce(ui.updateAll, 300);

    // ── Sidebar inputs (desktop) ──────────────────────────────────────────────
    INPUT_IDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', (e) => {
                let val = e.target.value;
                if (e.target.type === 'number') {
                    const parsed = Number.parseFloat(e.target.value);
                    if (!Number.isFinite(parsed)) return;
                    val = parsed;
                }
                ui.inputs[id] = val;
                ui.saveInputs();

                // Keep mobile mirror in sync (value only, no re-trigger)
                const mirror = document.querySelector(`[data-mobile-mirror="${id}"]`);
                if (mirror && mirror !== e.target) mirror.value = val;

                // Smarter Auto-Fill: Sync Target CWT for calibration automatically based on Safety Margin
                if (id === 'designCWT' || id === 'off100r100') {
                    const targetEl = document.getElementById('targetCWT');
                    if (targetEl) {
                        const targetVal = (ui.inputs.designCWT - (ui.inputs.off100r100 || 0)).toFixed(2);
                        targetEl.value = targetVal;
                        // Brief highlight to show it updated automatically
                        targetEl.classList.add('bg-emerald-500/20');
                        setTimeout(() => targetEl.classList.remove('bg-emerald-500/20'), 500);
                    }
                }

                ui.updateFastMetrics();
                if (isCurveAffectingInput(id)) debouncedUpdateAll();
            });
        }
    });

    // ── Mobile mirror inputs (inline panel — mobile/tablet only) ──────────────
    // These use data-mobile-mirror="<inputId>" instead of id to avoid duplicates.
    document.querySelectorAll('[data-mobile-mirror]').forEach(mirrorEl => {
        const id = mirrorEl.dataset.mobileMirror;
        if (!id) return;

        // Seed initial value from loaded inputs
        if (ui.inputs[id] !== undefined) mirrorEl.value = ui.inputs[id];

        mirrorEl.addEventListener('input', (e) => {
            let val = e.target.value;
            if (e.target.type === 'number') {
                const parsed = Number.parseFloat(e.target.value);
                if (!Number.isFinite(parsed)) return;
                val = parsed;
            }
            ui.inputs[id] = val;
            ui.saveInputs();

            // Keep sidebar canonical input in sync (value only, no re-trigger)
            const canonical = document.getElementById(id);
            if (canonical && canonical !== e.target) canonical.value = val;

            // Smarter Auto-Fill: Sync Target CWT for calibration automatically based on Safety Margin
            if (id === 'designCWT' || id === 'off100r100') {
                const targetEl = document.getElementById('targetCWT');
                if (targetEl) {
                    const targetVal = (ui.inputs.designCWT - (ui.inputs.off100r100 || 0)).toFixed(2);
                    targetEl.value = targetVal;
                    targetEl.classList.add('bg-emerald-500/20');
                    setTimeout(() => targetEl.classList.remove('bg-emerald-500/20'), 500);
                }
            }

            ui.updateFastMetrics();
            if (isCurveAffectingInput(id)) debouncedUpdateAll();
        });
    });

    // ── Desktop export buttons (sidebar) ─────────────────────────────────────
    document.getElementById('exportExcel')?.addEventListener('click', () => ui.exportData());
    document.getElementById('exportPDF')?.addEventListener('click',  () => window.print());
    document.getElementById('resetDefaults')?.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all parameters to default values?')) {
            localStorage.removeItem('sarma_thermal_inputs');
            location.reload();
        }
    });

    // ── Auto-Calibration ──────────────────────────────────────────────────────
    document.getElementById('btnCalibrateC')?.addEventListener('click', async () => {
        const btn = document.getElementById('btnCalibrateC');
        const targetCWT = parseFloat(document.getElementById('targetCWT').value);
        if (isNaN(targetCWT)) return alert('Please enter a valid Target CWT');
        
        btn.innerText = 'Fitting...';
        btn.disabled = true;
        
        try {
            const range = ui.inputs.designHWT - ui.inputs.designCWT;
            const resp = await fetch('/api/calculate/calibrate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    targetCWT: targetCWT,
                    designWBT: ui.inputs.designWBT,
                    designRange: range,
                    lgRatio: ui.inputs.lgRatio,
                    constantM: ui.inputs.constantM
                })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Calibration failed');
            
            // Update the constant C input and trigger UI update
            const cInput = document.getElementById('constantC');
            cInput.value = data.constantC;
            ui.inputs.constantC = data.constantC;
            ui.saveInputs();
            ui.updateFastMetrics();
            debouncedUpdateAll();
            
            btn.innerText = 'Success!';
            setTimeout(() => {
                btn.innerText = 'Fit Curve';
                btn.disabled = false;
            }, 1000);
        } catch (err) {
            alert('Calibration Error: ' + err.message);
            btn.innerText = 'Fit Curve';
            btn.disabled = false;
        }
    });

    // ── Clear Safety Margins & Reset Fit ──────────────────────────────────────
    document.getElementById('btnClearMargins')?.addEventListener('click', () => {
        const marginIds = [
            'offsetWbt20', 
            'off90r80', 'off90r100', 'off90r120',
            'off100r80', 'off100r100', 'off100r120',
            'off110r80', 'off110r100', 'off110r120'
        ];
        
        // Zero them out in UI and state
        marginIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = 0;
            ui.inputs[id] = 0;
        });
        
        // Auto-update Target CWT
        const targetEl = document.getElementById('targetCWT');
        if (targetEl) {
            targetEl.value = (ui.inputs.designCWT).toFixed(2);
            targetEl.classList.add('bg-emerald-500/20');
            setTimeout(() => targetEl.classList.remove('bg-emerald-500/20'), 500);
        }
        
        ui.saveInputs();
        
        // Automatically run Fit Curve to reset the constantC to standard performance
        const btnFit = document.getElementById('btnCalibrateC');
        if (btnFit) btnFit.click();
        
        // If not already updated by Fit Curve, update visually
        ui.updateFastMetrics();
        debouncedUpdateAll();
    });

    // ── Mobile export buttons (inline panel) ─────────────────────────────────
    document.getElementById('exportExcelMobile')?.addEventListener('click', () => ui.exportData());
    document.getElementById('exportPDFMobile')?.addEventListener('click',  () => window.print());

    // ── Tab navigation ───────────────────────────────────────────────────────
    document.getElementById('tabThermal')?.addEventListener('click',    () => ui.switchTab('thermal'));
    document.getElementById('tabPrediction')?.addEventListener('click', () => {
        ui.switchTab('prediction');
        ui.calculatePrediction();
    });
    document.getElementById('tabPsychro')?.addEventListener('click', () => ui.switchTab('psychro'));
    document.getElementById('tabFilter')?.addEventListener('click',   () => ui.switchTab('filter'));
    document.getElementById('tabReport')?.addEventListener('click',   () => ui.switchTab('report'));

    document.getElementById('generateReportBtn')?.addEventListener('click',   () => generateReport(ui));
    document.getElementById('previewAllTestsBtn')?.addEventListener('click', () => previewAllTests(ui));

    // ── ATC-105 Report Builder: live preview on input change ─────────────
    const atcInputIds = [
        'rep-design-wbt','rep-design-cwt','rep-design-hwt','rep-design-flow','rep-design-fanpow',
        'rep-design-lg','rep-density-override',
        'rep-test-wbt','rep-cwt','rep-hwt','rep-flow','rep-test-fanpow',
    ];
    const debouncedAtcPreview = ui.debounce(() => updateAtcPreview(ui), 500);
    atcInputIds.forEach(id => {
        document.getElementById(id)?.addEventListener('input', debouncedAtcPreview);
    });

    // Sync design values from Thermal tab into the Report tab
    document.getElementById('rep-sync-from-thermal')?.addEventListener('click', () => syncDesignFromThermal(ui));

    // Bind the Filter-Excel upload parser in the Report Builder
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
    // Init toggle state on load
    ui.bindFilterProcessAllToggle();


    // ── Psychrometric calculator ──────────────────────────────────────────────
    ['p-dbt', 'p-wbt', 'p-alt'].forEach((id) => {
        document.getElementById(id)?.addEventListener('input', ui.debounce(ui.calculatePsychrometrics, 150));
    });

    // ── Performance prediction ────────────────────────────────────────────────
    ['pred-wbt', 'pred-range', 'pred-lg', 'pred-c', 'pred-m'].forEach((id) => {
        document.getElementById(id)?.addEventListener('input', ui.debounce(ui.calculatePrediction, 100));
    });

    // ── Print mode ───────────────────────────────────────────────────────────
    window.onbeforeprint = () => { ui.isPrinting = true;  ui.updateCharts(); };
    window.onafterprint  = () => { ui.isPrinting = false; ui.updateCharts(); };

    // ── Initialise ───────────────────────────────────────────────────────────
    ui.initMobileNavigation();
    ui.updateExportUiState('Calculating curves...');
    ui.updateFilterUiState('Filter tool ready.');
    
    // Initial sync of Target CWT
    const targetEl = document.getElementById('targetCWT');
    if (targetEl) {
        targetEl.value = (ui.inputs.designCWT - (ui.inputs.off100r100 || 0)).toFixed(2);
    }
    
    ui.switchTab('thermal');
    ui.syncFilterSettingsToUi();
    ui.calculatePsychrometrics();
}
