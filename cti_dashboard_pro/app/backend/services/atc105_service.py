import math
from core.calculations import find_cwt
from core.merkel_engine import merkel_kavl
from core.psychro_engine import psychrometrics

def _lerp(x, x0, x1, y0, y1):
    if x1 == x0: return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

def _interp_curve(x, xs, ys):
    n = len(xs)
    if x <= xs[0]:
        slope = (ys[1] - ys[0]) / (xs[1] - xs[0]) if xs[1] != xs[0] else 0
        return ys[0] + slope * (x - xs[0])
    if x >= xs[-1]:
        slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) if xs[-1] != xs[-2] else 0
        return ys[-1] + slope * (x - xs[-1])
    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            return _lerp(x, xs[i], xs[i + 1], ys[i], ys[i + 1])
    return ys[-1]

def _exit_air_density(wbt, hwt, cwt, lg):
    p_in = psychrometrics(wbt, wbt)
    h_in = p_in["H"]
    h_out = h_in + lg * 4.186 * (hwt - cwt)
    low, high = 5.0, 95.0
    for _ in range(50):
        mid = (low + high) / 2
        if psychrometrics(mid, mid)["H"] > h_out:
            high = mid
        else:
            low = mid
    return psychrometrics((low + high) / 2, (low + high) / 2)["Dens"]

def calculate_atc105(req) -> dict:
    design_range = req.design_hwt - req.design_cwt
    test_range   = req.test_hwt  - req.test_cwt
    test_range_pct = (test_range / design_range) * 100.0

    range_pcts = [80.0, 100.0, 120.0]
    flow_pcts  = [90,   100,   110]

    ranges_abs = {int(rp): round(design_range * rp / 100.0, 3) for rp in range_pcts}
    flows_m3h = {fp: round(req.design_flow * fp / 100.0, 2) for fp in flow_pcts}

    base_inputs = {
        "lgRatio":    req.lg_ratio,
        "constantC":  req.constant_c,
        "constantM":  req.constant_m,
        "designHWT":  req.design_hwt,
        "designCWT":  req.design_cwt,
    }

    table1 = {}
    for fp in flow_pcts:
        table1[fp] = {}
        for rp in range_pcts:
            val = find_cwt(base_inputs, req.test_wbt, rp, fp)
            table1[fp][int(rp)] = round(val, 3) if not math.isnan(val) else None

    _offsets = {
        90:  (req.off90r80,  req.off90r100,  req.off90r120),
        100: (req.off100r80, req.off100r100, req.off100r120),
        110: (req.off110r80, req.off110r100, req.off110r120),
    }
    _has_offsets = req.offset_wbt20 != 0 or any(v != 0 for g in _offsets.values() for v in g)
    if _has_offsets:
        if req.design_wbt != 20:
            _wbt_slope       = req.offset_wbt20 / (20.0 - req.design_wbt)
            _wbt_correction  = _wbt_slope * (req.test_wbt - req.design_wbt)
            _tilt_multiplier = (req.test_wbt - req.design_wbt) / (20.0 - req.design_wbt)
        else:
            _wbt_correction  = req.offset_wbt20 if req.test_wbt == 20 else 0.0
            _tilt_multiplier = 1.0 if req.test_wbt == 20 else 0.0
        for fp in flow_pcts:
            o80, o100, o120 = _offsets[fp]
            for rp_key, raw_off in zip([80, 100, 120], [o80, o100, o120]):
                if table1[fp][rp_key] is not None:
                    table1[fp][rp_key] = round(
                        table1[fp][rp_key] + _wbt_correction + raw_off * _tilt_multiplier, 3
                    )

    cross1 = {}
    for fp in flow_pcts:
        r80, r100, r120 = table1[fp][80], table1[fp][100], table1[fp][120]
        if any(v is None for v in [r80, r100, r120]):
            cross1[fp] = None
            continue
        if test_range_pct <= 100.0:
            cwt = _lerp(test_range_pct, 80.0, 100.0, r80, r100)
        else:
            cwt = _lerp(test_range_pct, 100.0, 120.0, r100, r120)
        cross1[fp] = round(cwt, 3)

    cross2_direct = {}
    for fp in flow_pcts:
        val = find_cwt(base_inputs, req.test_wbt, test_range_pct, fp)
        cross2_direct[fp] = round(val, 3) if not math.isnan(val) else cross1.get(fp)

    # Apply offsets to direct cross-plot 2 values if needed
    if _has_offsets:
        for fp in flow_pcts:
            if cross2_direct[fp] is not None:
                o80, o100, o120 = _offsets[fp]
                if test_range_pct <= 100.0:
                    raw_off = o80 + (o100 - o80) * (test_range_pct - 80.0) / 20.0
                else:
                    raw_off = o100 + (o120 - o100) * (test_range_pct - 100.0) / 20.0
                cross2_direct[fp] = round(cross2_direct[fp] + _wbt_correction + raw_off * _tilt_multiplier, 3)

    cp2_flows = [flows_m3h[fp] for fp in flow_pcts]
    cp2_cwts  = [cross2_direct[fp] for fp in flow_pcts]

    if req.test_lg_ratio is not None:
        effective_test_lg = req.test_lg_ratio
    else:
        effective_test_lg = req.lg_ratio * (req.test_flow / req.design_flow)

    density_test = _exit_air_density(req.test_wbt, req.test_hwt, req.test_cwt, effective_test_lg)
    density_design = _exit_air_density(req.design_wbt, req.design_hwt, req.design_cwt, req.lg_ratio)
    density_ratio  = density_test / density_design

    effective_density_ratio = req.density_ratio_override if req.density_ratio_override else density_ratio

    if req.test_lg_ratio is not None:
        final_test_lg = req.test_lg_ratio
    else:
        g_ratio = (effective_density_ratio) ** (2/3) * (req.test_fan_power / req.design_fan_power) ** (1/3)
        l_ratio = req.test_flow / req.design_flow
        final_test_lg = req.lg_ratio * (l_ratio / g_ratio) if g_ratio > 0 else req.lg_ratio

    adj_flow = (req.test_flow
                * (req.design_fan_power / req.test_fan_power) ** (1 / 3)
                * effective_density_ratio ** (1 / 3))

    valid_pairs = [(f, c) for f, c in zip(cp2_flows, cp2_cwts) if c is not None]
    vf = [p[0] for p in valid_pairs]
    vc = [p[1] for p in valid_pairs]

    pred_cwt  = round(_interp_curve(adj_flow, vf, vc), 3) if vf else None
    pred_flow = round(_interp_curve(req.test_cwt, vc, vf), 2) if vf else None

    shortfall  = round(req.test_cwt - pred_cwt, 3) if pred_cwt is not None else None
    capability = round((adj_flow / pred_flow) * 100, 1) if pred_flow and pred_flow > 0 else None

    appM_cwt_design_pred = None
    appM_cwd             = None
    try:
        test_lg = final_test_lg
        kavl_result = merkel_kavl(req.test_hwt, req.test_cwt, req.test_wbt, test_lg)

        if kavl_result and kavl_result.get("valid"):
            kavl_test = kavl_result["kavl"]
            if test_lg > 0 and req.constant_m > 0 and kavl_test > 0:
                c_effective = kavl_test / math.pow(test_lg, -req.constant_m)
                design_range_val = req.design_hwt - req.design_cwt
                design_lg        = req.lg_ratio

                supply_kavl_design = c_effective * math.pow(design_lg, -req.constant_m)

                if supply_kavl_design > 0:
                    low_ap, high_ap = 0.01, 80.0
                    best_cwt_d, best_diff = float('nan'), float('inf')
                    tolerance = 1e-7

                    for _ in range(120):
                        mid_ap = (low_ap + high_ap) / 2.0
                        g_cwt  = req.design_wbt + mid_ap
                        g_hwt  = g_cwt + design_range_val

                        try:
                            d_kavl = merkel_kavl(g_hwt, g_cwt, req.design_wbt, design_lg)
                            demand = d_kavl["kavl"] if d_kavl and d_kavl.get("valid") else float('nan')
                        except Exception:
                            demand = float('nan')

                        if math.isnan(demand) or demand <= 0:
                            low_ap = mid_ap
                            continue

                        diff = abs(demand - supply_kavl_design)
                        if diff < best_diff:
                            best_diff, best_cwt_d = diff, g_cwt

                        if diff < tolerance:
                            break

                        if demand > supply_kavl_design:
                            low_ap = mid_ap
                        else:
                            high_ap = mid_ap

                    if not math.isnan(best_cwt_d) and best_diff < 0.5:
                        appM_cwt_design_pred = round(best_cwt_d, 3)
                        appM_cwd = round(appM_cwt_design_pred - req.design_cwt, 3)
    except Exception:
        pass

    return {
        "design_range": round(design_range, 3),
        "test_range": round(test_range, 3),
        "test_range_pct": round(test_range_pct, 2),
        "ranges_abs": ranges_abs,
        "flows_m3h": flows_m3h,
        "table1": {str(fp): {str(int(rp)): table1[fp][int(rp)] for rp in range_pcts} for fp in flow_pcts},
        "cross_plot_1": {
            "ranges_abs": [ranges_abs[int(rp)] for rp in range_pcts],
            "cwt_90": [table1[90][int(rp)] for rp in range_pcts],
            "cwt_100": [table1[100][int(rp)] for rp in range_pcts],
            "cwt_110": [table1[110][int(rp)] for rp in range_pcts],
            "test_range": round(test_range, 3),
            "f90_cwt": cross1[90],
            "f100_cwt": cross1[100],
            "f110_cwt": cross1[110],
        },
        "cross_plot_2": {
            "flows": cp2_flows,
            "cwts": cp2_cwts,
            "adj_flow": round(adj_flow, 2),
            "pred_flow": pred_flow,
            "pred_cwt": pred_cwt,
            "test_cwt": req.test_cwt,
            "design_cwt": req.design_cwt,
        },
        "density_test": round(density_test, 4),
        "density_design": round(density_design, 4),
        "density_ratio": round(density_ratio, 6),
        "density_ratio_used": round(effective_density_ratio, 6),
        "adj_flow": round(adj_flow, 2),
        "pred_cwt": pred_cwt,
        "pred_flow": pred_flow,
        "shortfall": shortfall,
        "capability": capability,
        "appM_cwt_design_pred": appM_cwt_design_pred,
        "appM_cwd": appM_cwd,
        "design_wbt": req.design_wbt,
        "design_cwt": req.design_cwt,
        "design_hwt": req.design_hwt,
        "design_flow": req.design_flow,
        "test_wbt": req.test_wbt,
        "test_cwt": req.test_cwt,
        "test_hwt": req.test_hwt,
        "test_flow": req.test_flow,
        "offsets_applied": {
            "offset_wbt20": req.offset_wbt20,
            "off90r80": req.off90r80, "off90r100": req.off90r100, "off90r120": req.off90r120,
            "off100r80": req.off100r80, "off100r100": req.off100r100, "off100r120": req.off100r120,
            "off110r80": req.off110r80, "off110r100": req.off110r100, "off110r120": req.off110r120,
        } if _has_offsets else {},
    }
