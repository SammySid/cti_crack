import { psychrometrics } from '../psychro-engine.js';

function clearPsychroOutputs() {
    const outputIds = ['out-hr', 'out-dp', 'out-rh', 'out-h', 'out-sv', 'out-dens', 'out-p'];
    outputIds.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerText = '--';
    });
}

export function formatPsychroValue(value, suffix = '', decimals = 2) {
    if (value === undefined || value === null || Number.isNaN(value)) return '--';
    return `${Number(value).toFixed(decimals)}${suffix}`;
}

export function calculatePsychrometrics(ui) {
    const statusEl = document.getElementById('psychroStatus');
    if (!ui.enginesReady) {
        if (statusEl) statusEl.innerText = 'Psychrometric engine is initializing...';
        return;
    }

    const dbt = parseFloat(document.getElementById('p-dbt')?.value ?? '35');
    const wbt = parseFloat(document.getElementById('p-wbt')?.value ?? '25');
    const alt = parseFloat(document.getElementById('p-alt')?.value ?? '0');
    const errorEl = document.getElementById('p-error');

    if (Number.isNaN(dbt) || Number.isNaN(wbt) || Number.isNaN(alt)) {
        if (statusEl) statusEl.innerText = 'Enter valid numeric inputs.';
        clearPsychroOutputs();
        return;
    }
    if (wbt > dbt) {
        if (errorEl) errorEl.classList.remove('hidden');
        if (statusEl) statusEl.innerText = 'WBT cannot exceed DBT.';
        clearPsychroOutputs();
        return;
    }
    if (errorEl) errorEl.classList.add('hidden');

    try {
        const result = psychrometrics(dbt, wbt, alt);
        document.getElementById('out-hr').innerText = ui.formatPsychroValue(result.HR, ' kg/kg', 5);
        document.getElementById('out-dp').innerText = ui.formatPsychroValue(result.DP, ' °C', 2);
        document.getElementById('out-rh').innerText = ui.formatPsychroValue(result.RH, ' %', 2);
        document.getElementById('out-h').innerText = ui.formatPsychroValue(result.H, ' kJ/kg', 4);
        document.getElementById('out-sv').innerText = ui.formatPsychroValue(result.SV, ' m3/kg', 4);
        document.getElementById('out-dens').innerText = ui.formatPsychroValue(result.Dens, ' kg/m3', 5);
        document.getElementById('out-p').innerText = ui.formatPsychroValue(result.P, ' kPa', 3);
        if (statusEl) statusEl.innerText = 'Calculated using CTI psychrometric engine.';
    } catch (error) {
        console.error('Psychrometric calculation failed', error);
        if (statusEl) statusEl.innerText = 'Calculation failed. Check inputs and try again.';
    }
}
