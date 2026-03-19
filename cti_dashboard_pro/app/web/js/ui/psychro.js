export function formatPsychroValue(value, suffix = '', decimals = 2) {
    if (value === undefined || value === null || Number.isNaN(value)) return '--';
    return `${Number(value).toFixed(decimals)}${suffix}`;
}

export async function calculatePsychrometrics(ui) {
    const statusEl = document.getElementById('psychroStatus');

    const dbt = parseFloat(document.getElementById('p-dbt')?.value ?? '35');
    const wbt = parseFloat(document.getElementById('p-wbt')?.value ?? '25');
    const alt = parseFloat(document.getElementById('p-alt')?.value ?? '0');
    const errorEl = document.getElementById('p-error');

    if (Number.isNaN(dbt) || Number.isNaN(wbt) || Number.isNaN(alt)) {
        if (statusEl) statusEl.innerText = 'Enter valid numeric inputs.';
        return;
    }
    if (wbt > dbt) {
        if (errorEl) errorEl.classList.remove('hidden');
        if (statusEl) statusEl.innerText = 'WBT cannot exceed DBT.';
        return;
    }
    if (errorEl) errorEl.classList.add('hidden');

    try {
        const response = await fetch('/api/calculate/psychro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dbt, wbt, alt })
        });
        
        if (!response.ok) throw new Error('Calculation failed on server');
        const result = await response.json();
        
        document.getElementById('out-hr').innerText = formatPsychroValue(result.HR, ' kg/kg', 5);
        document.getElementById('out-dp').innerText = formatPsychroValue(result.DP, ' °C', 2);
        document.getElementById('out-rh').innerText = formatPsychroValue(result.RH, ' %', 2);
        document.getElementById('out-h').innerText = formatPsychroValue(result.H, ' kJ/kg', 4);
        document.getElementById('out-sv').innerText = formatPsychroValue(result.SV, ' m3/kg', 4);
        document.getElementById('out-dens').innerText = formatPsychroValue(result.Dens, ' kg/m3', 5);
        document.getElementById('out-p').innerText = formatPsychroValue(result.P, ' kPa', 3);
        if (statusEl) statusEl.innerText = 'Calculated using secure Python Engine.';
    } catch (error) {
        console.error('Psychrometric calculation failed', error);
        if (statusEl) statusEl.innerText = 'Calculation failed. Check inputs and try again.';
    }
}
