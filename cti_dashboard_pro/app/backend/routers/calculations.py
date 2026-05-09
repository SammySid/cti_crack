import math
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.calculations import find_cwt, solve_off_design_cwt
from core.merkel_engine import merkel_kavl
from core.psychro_engine import psychrometrics

router = APIRouter()

def _model_to_dict(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

# Pydantic models for API
class PsychroRequest(BaseModel):
    dbt: float
    wbt: float
    alt: float = 0.0

class PredictRequest(BaseModel):
    wbt: float
    range: float
    lg: float
    constC: float
    constM: float

class CurveInputs(BaseModel):
    axXMin: float
    axXMax: float
    lgRatio: float
    constantC: float
    constantM: float
    designHWT: float
    designCWT: float
    designWBT: float = 28.5
    offsetWbt20: float = 0.0
    off90r80: float = 0.0
    off90r100: float = 0.0
    off90r120: float = 0.0
    off100r80: float = 0.0
    off100r100: float = 0.0
    off100r120: float = 0.0
    off110r80: float = 0.0
    off110r100: float = 0.0
    off110r120: float = 0.0

class CurveRequest(BaseModel):
    inputs: CurveInputs
    flowPercent: int

class CalibrateRequest(BaseModel):
    targetCWT: float
    designWBT: float
    designRange: float
    lgRatio: float
    constantM: float

class KaVLRequest(BaseModel):
    wbt: float
    hwt: float
    cwt: float
    lg: float

class Atc105Request(BaseModel):
    design_wbt: float
    design_cwt: float
    design_hwt: float
    design_flow: float
    design_fan_power: float = 117.0
    test_wbt: float
    test_cwt: float
    test_hwt: float
    test_flow: float
    test_fan_power: float = 117.0
    lg_ratio: float
    test_lg_ratio: float | None = None
    constant_c: float = 1.2
    constant_m: float = 0.6
    density_ratio_override: float | None = None
    offset_wbt20: float = 0.0
    off90r80: float = 0.0
    off90r100: float = 0.0
    off90r120: float = 0.0
    off100r80: float = 0.0
    off100r100: float = 0.0
    off100r120: float = 0.0
    off110r80: float = 0.0
    off110r100: float = 0.0
    off110r120: float = 0.0

@router.post("/calculate/kavl")
async def api_calc_kavl(req: KaVLRequest):
    try:
        res = merkel_kavl(req.hwt, req.cwt, req.wbt, req.lg)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate/psychro")
async def api_calc_psychro(req: PsychroRequest):
    try:
        res = psychrometrics(req.dbt, req.wbt, req.alt)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate/predict")
async def api_calc_predict(req: PredictRequest):
    try:
        res = solve_off_design_cwt(req.wbt, req.range, req.lg, req.constC, req.constM)
        if not res:
            raise HTTPException(status_code=400, detail="Cannot solve prediction for given parameters.")
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate/calibrate")
async def api_calc_calibrate(req: CalibrateRequest):
    try:
        from core.calculations import calculate_demand_kavl
        target_hwt = req.targetCWT + req.designRange
        demand_kavl = calculate_demand_kavl(req.designWBT, target_hwt, req.targetCWT, req.lgRatio)
        
        if math.isnan(demand_kavl) or demand_kavl <= 0:
            raise ValueError("Invalid thermodynamics for given target CWT. Demand KaV/L did not converge.")

        constant_c = demand_kavl / math.pow(req.lgRatio, -req.constantM)
        
        return {"constantC": round(constant_c, 4), "demandKavl": round(demand_kavl, 4)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate/curves")
async def api_calc_curves(req: CurveRequest):
    try:
        data = []
        wbt_start = req.inputs.axXMin
        wbt_end = req.inputs.axXMax
        if wbt_start >= wbt_end:
            raise ValueError("Invalid axis range")

        wbt = wbt_start
        inputs_dict = _model_to_dict(req.inputs)
        while wbt <= wbt_end:
            wbt_val = float(f"{wbt:.2f}")
            cwt80 = find_cwt(inputs_dict, wbt_val, 80, req.flowPercent)
            cwt100 = find_cwt(inputs_dict, wbt_val, 100, req.flowPercent)
            cwt120 = find_cwt(inputs_dict, wbt_val, 120, req.flowPercent)

            if not (math.isnan(cwt80) or math.isnan(cwt100) or math.isnan(cwt120)):
                if inputs_dict.get('designWBT') != 20:
                    wbt_slope = req.inputs.offsetWbt20 / (20.0 - req.inputs.designWBT)
                    wbt_correction = wbt_slope * (wbt_val - req.inputs.designWBT)
                else:
                    wbt_correction = req.inputs.offsetWbt20 if wbt_val == 20 else 0
                
                raw_off80 = raw_off100 = raw_off120 = 0.0
                if req.flowPercent == 90:
                    raw_off80, raw_off100, raw_off120 = req.inputs.off90r80, req.inputs.off90r100, req.inputs.off90r120
                elif req.flowPercent == 100:
                    raw_off80, raw_off100, raw_off120 = req.inputs.off100r80, req.inputs.off100r100, req.inputs.off100r120
                elif req.flowPercent == 110:
                    raw_off80, raw_off100, raw_off120 = req.inputs.off110r80, req.inputs.off110r100, req.inputs.off110r120

                if inputs_dict.get('designWBT') != 20:
                    tilt_multiplier = (wbt_val - req.inputs.designWBT) / (20.0 - req.inputs.designWBT)
                else:
                    tilt_multiplier = 1.0 if wbt_val == 20 else 0.0

                cwt80 = round(cwt80 + wbt_correction + (raw_off80 * tilt_multiplier), 3)
                cwt100 = round(cwt100 + wbt_correction + (raw_off100 * tilt_multiplier), 3)
                cwt120 = round(cwt120 + wbt_correction + (raw_off120 * tilt_multiplier), 3)

                data.append({
                    "wbt": wbt_val,
                    "range80": cwt80,
                    "range100": cwt100,
                    "range120": cwt120
                })
            wbt += 0.25

        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate/atc105")
async def api_calc_atc105(req: Atc105Request):
    try:
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
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=400, detail=f"ATC-105 error: {exc}\n{traceback.format_exc()}")
