// ── Time helpers — universal 12h, typeable, locale-independent ───────────────

/**
 * Accepts any reasonable time string the user might type and returns a
 * normalised "H:MM AM/PM" string.  Examples:
 *   "16:00"  → "4:00 PM"
 *   "4pm"    → "4:00 PM"
 *   "4:30pm" → "4:30 PM"
 *   "430"    → "4:30 AM"  (4 digits = HHMM)
 *   "4"      → "4:00 AM"
 *   "4:00 PM"→ "4:00 PM"  (already correct — unchanged)
 */
function _normalizeTimeText(raw) {
    if (!raw) return '';
    const str = String(raw).trim().toLowerCase().replace(/\s+/g, '');

    const hasPm = str.includes('pm');
    const hasAm = str.includes('am');
    const is12h = hasPm || hasAm;

    // Strip am/pm suffix letters
    const digits = str.replace(/[apm]/g, '').trim();

    let h, m;
    if (digits.includes(':')) {
        const [hStr, mStr] = digits.split(':');
        h = parseInt(hStr, 10) || 0;
        m = parseInt(mStr, 10) || 0;
    } else if (digits.length >= 3) {
        // e.g. "430" or "1600"
        const padded = digits.padStart(4, '0');
        h = parseInt(padded.slice(0, -2), 10) || 0;
        m = parseInt(padded.slice(-2), 10) || 0;
    } else {
        h = parseInt(digits, 10) || 0;
        m = 0;
    }

    if (m > 59) m = 59;

    let ampm;
    if (is12h) {
        ampm = hasPm ? 'PM' : 'AM';
        if (h === 0) h = 12;
        if (h > 12)  h = h % 12 || 12;
    } else {
        ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12 || 12;
    }

    return `${h}:${String(m).padStart(2, '0')} ${ampm}`;
}

// ── UI state ─────────────────────────────────────────────────────────────────
export function updateFilterUiState(ui, message = '') {
    const filterStatus = document.getElementById('filterStatus');
    const panelStatus  = document.getElementById('filterPanelStatus');
    const runBtn       = document.getElementById('runFilterAction');

    if (runBtn) {
        runBtn.disabled = ui.isFiltering;
        runBtn.classList.toggle('opacity-50',        ui.isFiltering);
        runBtn.classList.toggle('cursor-not-allowed', ui.isFiltering);
        runBtn.innerText = ui.isFiltering ? 'Processing...' : 'Generate Filtered Excel';
    }

    const resolvedMessage = message || (ui.isFiltering ? 'Processing uploaded files...' : 'Filter tool ready.');
    if (filterStatus) filterStatus.innerText = resolvedMessage;
    if (panelStatus)  panelStatus.innerText  = resolvedMessage;
}

// ── Process-All toggle ────────────────────────────────────────────────────────
function _applyProcessAllState(isAll) {
    ['filterStartTime', 'filterEndTime'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.disabled           = isAll;
        el.style.opacity      = isAll ? '0.35' : '';
        el.style.pointerEvents = isAll ? 'none'  : '';
    });
}

export function bindFilterProcessAllToggle() {
    const chk = document.getElementById('filterProcessAll');
    if (chk) {
        chk.addEventListener('change', () => _applyProcessAllState(chk.checked));
    }
}

// ── Sync stored settings → UI ─────────────────────────────────────────────────
export function syncFilterSettingsToUi(ui) {
    const pathInput     = document.getElementById('filterSourcePath');
    const destPathInput = document.getElementById('filterDestPath');
    const startInput    = document.getElementById('filterStartTime');
    const endInput      = document.getElementById('filterEndTime');
    const processAllChk = document.getElementById('filterProcessAll');

    if (pathInput)     pathInput.value     = ui.filterSettings.sourcePath || '';
    if (destPathInput) destPathInput.value = ui.filterSettings.destPath   || '';

    // Restore saved times, normalising to 12h display regardless of what was stored
    if (startInput) startInput.value = _normalizeTimeText(ui.filterSettings.startTime || '4:00 PM');
    if (endInput)   endInput.value   = _normalizeTimeText(ui.filterSettings.endTime   || '5:00 PM');

    // Wire blur normalisation so typing "16:00" auto-converts to "4:00 PM" on focus-out
    [startInput, endInput].forEach(el => {
        if (!el) return;
        el.addEventListener('blur', () => {
            const n = _normalizeTimeText(el.value);
            if (n) el.value = n;
        });
    });

    if (processAllChk) {
        processAllChk.checked = ui.filterSettings.processAll || false;
        _applyProcessAllState(processAllChk.checked);
    }
}

// ── Main filter action ────────────────────────────────────────────────────────
export async function runFilterTool(ui) {
    if (ui.isFiltering) return;

    const sourcePathInput = document.getElementById('filterSourcePath');
    const destPathInput   = document.getElementById('filterDestPath');
    const folderInput     = document.getElementById('filterExcelFolder');
    const filesInput      = document.getElementById('filterExcelFiles');
    const processAllChk   = document.getElementById('filterProcessAll');

    const processAll = processAllChk?.checked || false;
    const rawStart   = document.getElementById('filterStartTime')?.value?.trim() || '';
    const rawEnd     = document.getElementById('filterEndTime')?.value?.trim()   || '';
    const startTime  = processAll ? '' : (_normalizeTimeText(rawStart) || rawStart);
    const endTime    = processAll ? '' : (_normalizeTimeText(rawEnd)   || rawEnd);
    const sourcePath = sourcePathInput?.value?.trim() || '';
    const destPath   = destPathInput?.value?.trim()   || '';

    const folderFiles = folderInput?.files ? Array.from(folderInput.files) : [];
    const manualFiles = filesInput?.files  ? Array.from(filesInput.files)  : [];
    const files       = folderFiles.length > 0 ? folderFiles : manualFiles;
    const SUPPORTED_EXT = ['.xlsx', '.xls'];
    const excelFiles  = files.filter(f => SUPPORTED_EXT.some(ext => f.name.toLowerCase().endsWith(ext)));

    if (!processAll && (!startTime || !endTime)) {
        ui.updateFilterUiState('Please choose both start and end time, or enable "Process All".');
        return;
    }
    if (!sourcePath && excelFiles.length === 0) {
        ui.updateFilterUiState('Please provide source folder path or select files.');
        return;
    }

    ui.filterSettings = { sourcePath, destPath, startTime, endTime, processAll };
    ui.saveFilterSettings();

    ui.isFiltering = true;
    let finalMessage = '';
    ui.updateFilterUiState(sourcePath
        ? 'Scanning saved source folder and filtering data...'
        : `Scanning ${excelFiles.length} file(s) and filtering data...`);

    try {
        let response;
        if (sourcePath) {
            response = await fetch('/api/filter-excel-local', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ startTime, endTime, sourcePath, destPath })
            });
        } else {
            const formData = new FormData();
            formData.append('startTime', startTime);
            formData.append('endTime',   endTime);
            excelFiles.forEach(f => formData.append('files', f, f.name));
            response = await fetch('/api/filter-excel', { method: 'POST', body: formData });
        }

        if (!response.ok) {
            let message = `Filter failed with status ${response.status}`;
            const errorText = await response.text();
            if (errorText) {
                try {
                    const errorJson = JSON.parse(errorText);
                    message = errorJson.detail || errorJson.error || message;
                } catch { message = errorText; }
            }
            throw new Error(message);
        }

        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const result = await response.json();
            finalMessage = result.message || 'Filtered master Excel securely saved to destination.';
        } else {
            const blob     = await response.blob();
            const fileName = ui.getDownloadFileName(response.headers.get('content-disposition')) || 'Master_Filtered.xlsx';
            ui.downloadBlob(blob, fileName);
            finalMessage = 'Filtered master Excel downloaded successfully.';
        }

        if (folderInput) folderInput.value = '';
        if (filesInput)  filesInput.value  = '';
    } catch (error) {
        console.error('Filter export failed', error);
        finalMessage = error.message || 'Filtering failed. Please try again.';
    } finally {
        ui.isFiltering = false;
        ui.updateFilterUiState(finalMessage);
    }
}
