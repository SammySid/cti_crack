import { _getOffsetsFromUi } from './report-helpers.js';
import { updateAtcPreview } from './report-preview.js';

export function launchReportFromThermal(ui) {
    // Pre-fill all design fields in the Report Builder from Thermal Analysis
    syncDesignFromThermal(ui);

    // Show the "Loaded from Thermal Analysis" notice banner
    const banner = document.getElementById('trm-loaded-banner');
    if (banner) { banner.classList.remove('hidden'); banner.classList.add('flex'); }

    // Switch to the Report Builder tab
    const tab = document.getElementById('tabReport');
    if (tab) tab.click();

    // Scroll to top of the page so the user sees the banner
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

export function syncDesignFromThermal(ui) {
    const map = {
        'rep-design-wbt':    'designWBT',
        'rep-design-cwt':    'designCWT',
        'rep-design-hwt':    'designHWT',
        'rep-design-flow':   'designWaterFlow',
        'rep-design-fanpow': 'designFanPower',
        'rep-design-lg':     'lgRatio',
        'rep-design-c':      'constantC',
        'rep-design-m':      'constantM',
    };
    Object.entries(map).forEach(([repId, uiKey]) => {
        const el = document.getElementById(repId);
        if (el && ui.inputs[uiKey] !== undefined) el.value = ui.inputs[uiKey];
    });

    // ── Render active safety margins strip in Report Builder ──────────────────
    _renderMarginsStrip(ui);

    updateAtcPreview(ui);
}

function _renderMarginsStrip(ui) {
    const strip = document.getElementById('rep-margins-strip');
    const pills = document.getElementById('rep-margins-pills');
    if (!strip || !pills) return;

    const offsets = _getOffsetsFromUi(ui);
    const anyActive = Object.values(offsets).some(v => v !== 0);

    strip.classList.toggle('hidden', !anyActive);
    if (!anyActive) return;

    const flowLabels = { off90r80: '90%·R80', off90r100: '90%·R100', off90r120: '90%·R120',
                         off100r80: '100%·R80', off100r100: '100%·R100', off100r120: '100%·R120',
                         off110r80: '110%·R80', off110r100: '110%·R100', off110r120: '110%·R120' };

    const html = [];
    if (offsets.offset_wbt20 !== 0) {
        html.push(`<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-amber-500/30 bg-amber-500/10 text-[10px] font-mono">
            <span class="text-amber-500/70 font-black uppercase tracking-wide">@20°C anchor</span>
            <span class="text-amber-300 font-bold">${offsets.offset_wbt20 > 0 ? '+' : ''}${offsets.offset_wbt20}</span>
        </span>`);
    }
    Object.entries(flowLabels).forEach(([key, label]) => {
        if (offsets[key] !== 0) {
            html.push(`<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-amber-500/30 bg-amber-500/10 text-[10px] font-mono">
                <span class="text-amber-500/70 font-black uppercase tracking-wide">${label}</span>
                <span class="text-amber-300 font-bold">${offsets[key] > 0 ? '+' : ''}${offsets[key]}</span>
            </span>`);
        }
    });
    pills.innerHTML = html.join('');
}
