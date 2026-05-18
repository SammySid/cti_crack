import math
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.calculations import find_cwt, solve_off_design_cwt
from core.merkel_engine import merkel_kavl
from core.psychro_engine import psychrometrics
from services.atc105_service import calculate_atc105

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
        return calculate_atc105(req)
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=400, detail=f"ATC-105 error: {exc}\n{traceback.format_exc()}")
