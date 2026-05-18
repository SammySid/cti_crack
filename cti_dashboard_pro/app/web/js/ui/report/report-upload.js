import { updateAtcPreview } from './report-preview.js';

export function bindFilterUpload(ui) {
    const fileInput  = document.getElementById('rep-filter-upload');
    const parseBtn   = document.getElementById('rep-parse-excel-btn');
    const uploadLbl  = document.getElementById('rep-filter-upload-label');
    const previewEl  = document.getElementById('rep-parsed-preview');
    const statusEl   = document.getElementById('rep-parse-status');

    if (!fileInput || !parseBtn) return;

    fileInput.addEventListener('change', () => {
        const f = fileInput.files[0];
        if (f) {
            uploadLbl.textContent = f.name;
            parseBtn.disabled = false;
        } else {
            uploadLbl.textContent = 'Click to select Master Filtered Excel (.xlsx)';
            parseBtn.disabled = true;
        }
        previewEl.classList.add('hidden');
        if (statusEl) { statusEl.classList.add('hidden'); }
    });

    parseBtn.addEventListener('click', async () => {
        const f = fileInput.files[0];
        if (!f) return;

        parseBtn.textContent = 'Parsing…';
        parseBtn.disabled = true;
        previewEl.classList.add('hidden');
        if (statusEl) { statusEl.classList.add('hidden'); statusEl.className = 'text-[10px] hidden'; }

        try {
            const formData = new FormData();
            formData.append('file', f);

            const resp = await fetch('/api/parse-filter-excel', { method: 'POST', body: formData });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${resp.status}`);
            }
            const data = await resp.json();

            const fills = [
                { id: 'rep-cwt',      val: data.cwt,       label: 'CWT',       unit: '°C' },
                { id: 'rep-hwt',      val: data.hwt,       label: 'HWT',       unit: '°C' },
                { id: 'rep-test-wbt', val: data.wbt,       label: 'WBT',       unit: '°C' },
                { id: 'rep-flow',     val: data.flow,      label: 'Flow',      unit: 'm³/hr' },
                { id: 'rep-test-fanpow', val: data.fan_power, label: 'Fan Power', unit: 'kW' },
            ];

            let filled = 0;
            previewEl.innerHTML = '';
            for (const { id, val, label, unit } of fills) {
                if (val == null) continue;
                const el = document.getElementById(id);
                if (el) { el.value = val; filled++; }

                const card = document.createElement('div');
                card.className = 'bg-slate-900/60 rounded-xl p-2 border border-cyan-500/20 text-center';
                card.innerHTML = `<p class="text-[10px] text-slate-400 uppercase tracking-widest font-bold">${label}</p>
                                  <p class="text-sm font-black text-cyan-300 font-mono">${val} <span class="text-xs text-slate-400">${unit}</span></p>`;
                previewEl.appendChild(card);
            }

            previewEl.classList.toggle('hidden', filled === 0);

            if (statusEl) {
                statusEl.textContent = filled > 0
                    ? `Filled ${filled} field(s) from ${f.name}. Review before generating.`
                    : 'No CWT/HWT/WBT columns found in this file. Please fill test conditions manually.';
                statusEl.className = `text-[10px] ${filled > 0 ? 'text-cyan-400' : 'text-amber-400'}`;
                statusEl.classList.remove('hidden');
            }

            updateAtcPreview(ui);

        } catch (err) {
            if (statusEl) {
                statusEl.textContent = `Parse error: ${err.message}`;
                statusEl.className = 'text-[10px] text-rose-400';
                statusEl.classList.remove('hidden');
            }
        } finally {
            parseBtn.textContent = 'Parse & Auto-Fill';
            parseBtn.disabled = false;
        }
    });
}
