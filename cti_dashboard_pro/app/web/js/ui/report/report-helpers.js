export function _v(id, fallback = '') {
    const el = document.getElementById(id);
    if (!el) return fallback;
    return el.value ?? fallback;
}

export function _n(id, fallback = 0) {
    const v = parseFloat(_v(id, String(fallback)));
    return isFinite(v) ? v : fallback;
}

export function _lines(id) {
    return _v(id, '').split('\n').map(s => s.trim()).filter(Boolean);
}

export function _getOffsetsFromUi(ui) {
    const i = ui?.inputs ?? {};
    return {
        offset_wbt20: parseFloat(i.offsetWbt20) || 0,
        off90r80:     parseFloat(i.off90r80)    || 0,
        off90r100:    parseFloat(i.off90r100)   || 0,
        off90r120:    parseFloat(i.off90r120)   || 0,
        off100r80:    parseFloat(i.off100r80)   || 0,
        off100r100:   parseFloat(i.off100r100)  || 0,
        off100r120:   parseFloat(i.off100r120)  || 0,
        off110r80:    parseFloat(i.off110r80)   || 0,
        off110r100:   parseFloat(i.off110r100)  || 0,
        off110r120:   parseFloat(i.off110r120)  || 0,
    };
}

export function _getDesign(ui) {
    const designFlow = _n('rep-design-flow', 3863.6);
    return {
        wbt:              _n('rep-design-wbt',    29),
        cwt:              _n('rep-design-cwt',    33),
        hwt:              _n('rep-design-hwt',    43),
        flow:             designFlow,
        fan_power:        _n('rep-design-fanpow', 117),
        lg:               _n('rep-design-lg',     ui?.inputs?.lgRatio ?? 1.5),
        constant_c:       _n('rep-design-c',      ui?.inputs?.constantC ?? 1.2),
        constant_m:       _n('rep-design-m',      ui?.inputs?.constantM ?? 0.6),
        density_override: _n('rep-density-override', 0) || null,
    };
}

export function _buildPayloadForTest(design, test, offsets = {}) {
    return {
        design_wbt:             design.wbt,
        design_cwt:             design.cwt,
        design_hwt:             design.hwt,
        design_flow:            design.flow,
        design_fan_power:       design.fan_power,
        test_wbt:               test.wbt,
        test_cwt:               test.cwt,
        test_hwt:               test.hwt,
        test_flow:              test.flow,
        test_fan_power:         test.fan_power,
        lg_ratio:               design.lg,
        constant_c:             design.constant_c,
        constant_m:             design.constant_m,
        density_ratio_override: design.density_override,
        ...offsets,
    };
}

export async function _calcAtc(design, test, offsets = {}) {
    const resp = await fetch('/api/calculate/atc105', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(_buildPayloadForTest(design, test, offsets)),
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `ATC-105 API error ${resp.status}`);
    }
    return resp.json();
}
