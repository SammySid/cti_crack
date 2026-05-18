export function _isTestEnabled(n) {
    const el = document.getElementById(`rep-t${n}-enabled`);
    return el ? el.checked : true; // default true if element missing
}

export function _enabledCount() {
    return [1, 2, 3].filter(_isTestEnabled).length;
}

export function _updateActiveBadge() {
    const n   = _enabledCount();
    const el  = document.getElementById('rep-active-count-badge');
    if (!el) return;
    el.textContent = `${n} of 3 Active`;
    el.className   = [
        'ml-auto px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border',
        n === 3 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
        n === 0 ? 'bg-rose-500/10    border-rose-500/20    text-rose-400'    :
                  'bg-amber-500/10  border-amber-500/20   text-amber-400',
    ].join(' ');
}

export function _bindTestToggle(n) {
    const cb   = document.getElementById(`rep-t${n}-enabled`);
    const body = document.getElementById(`rep-t${n}-body`);
    const lbl  = document.getElementById(`rep-t${n}-toggle-label`);
    if (!cb) return;

    const applyState = () => {
        const on = cb.checked;
        if (body)  body.classList.toggle('test-card-disabled', !on);
        if (lbl) {
            lbl.textContent = on ? 'Active' : 'Skip';
            lbl.className   = `test-toggle-label ${on ? 'text-emerald-400' : 'text-slate-500'}`;
        }
        _updateActiveBadge();
    };
    cb.addEventListener('change', applyState);
    applyState(); // sync on init
}

export function bindTestToggles() {
    [1, 2, 3].forEach(_bindTestToggle);
}
