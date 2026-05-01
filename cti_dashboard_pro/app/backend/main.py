import os
import sys
import tempfile
import math
import uuid
import time
import threading
import sqlite3
import urllib.request
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend and core to path so imports work happily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from core.calculations import init as init_engines, find_cwt, solve_off_design_cwt
from core.merkel_engine import merkel_kavl
from core.psychro_engine import psychrometrics
from excel_gen import generate_excel_from_payload, sanitize_filename
from excel_filter_service import generate_filtered_workbook, generate_filtered_workbook_from_directory
from report_service import generate_pdf_report


def _model_to_dict(model: BaseModel) -> dict:
    # Support both Pydantic v1 (`dict`) and v2 (`model_dump`) at runtime.
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

app = FastAPI(
    title="SS Cooling Tower API",
    docs_url=None,    # Disable /docs in production
    redoc_url=None,   # Disable /redoc in production
    openapi_url=None, # Disable /openapi.json schema dump
)

# ── 📊 Analytics Engine (Bulletproof Tracking) ────────────────────────────────
DB_PATH = Path(__file__).resolve().parent / "analytics.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ip_address TEXT,
            location TEXT,
            user_agent TEXT,
            method TEXT,
            path TEXT,
            query_params TEXT,
            status_code INTEGER,
            process_time_ms REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

IP_CACHE = {}
def get_ip_details(ip):
    if ip in ["127.0.0.1", "localhost", "0.0.0.0", "unknown"] or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return "Local Network"
    if ip in IP_CACHE:
        return IP_CACHE[ip]
    try:
        req = urllib.request.Request(f"http://ip-api.com/json/{ip}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                info = f"{data.get('city')}, {data.get('countryCode')} ({data.get('isp')})"
                IP_CACHE[ip] = info
                return info
    except Exception:
        pass
    IP_CACHE[ip] = "Unknown Location"
    return "Unknown Location"

def log_request(ip, user_agent, method, path, query, status, process_time):
    def _write():
        try:
            location = get_ip_details(ip)
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            
            # Use Indian Standard Time (IST) which is UTC + 5:30
            IST = timezone(timedelta(hours=5, minutes=30))
            current_time = datetime.now(IST).strftime('%I:%M:%S %p, %d %b %Y')
            
            c.execute('''
                INSERT INTO access_logs (timestamp, ip_address, location, user_agent, method, path, query_params, status_code, process_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (current_time, ip, location, user_agent, method, path, query, status, process_time))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Analytics logging error: {e}")
    threading.Thread(target=_write, daemon=True).start()

@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # Ignore static files and high-frequency calculation API calls to prevent log spam
    noisy_routes = (
        "/css", 
        "/js", 
        "/api/calculate/curves", 
        "/api/calculate/kavl", 
        "/api/calculate/psychro", 
        "/api/calculate/predict"
    )
    
    if not request.url.path.startswith(noisy_routes) and "/analytics" not in request.url.path:
        ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            
        user_agent = request.headers.get("user-agent", "unknown")
        
        log_request(
            ip, user_agent, request.method, request.url.path, 
            str(request.query_params), response.status_code, process_time
        )
        
    return response

@app.get("/analytics")
def get_analytics(limit: int = 500):
    """Admin endpoint to view a powerful HTML analytics dashboard."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM access_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        
        # Calculate some summary stats for the dashboard
        total_hits = len(rows)
        unique_ips = len(set(r['ip_address'] for r in rows))
        
        paths = [r['path'] for r in rows]
        top_path = max(set(paths), key=paths.count) if paths else "N/A"
        
        conn.close()
        
        from fastapi.responses import HTMLResponse
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CTI Live Analytics</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #3b82f6; --accent-hover: #60a5fa; --border: #334155; }}
                body {{ font-family: 'Inter', -apple-system, sans-serif; background-color: var(--bg); color: var(--text); padding: 20px; margin: 0; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
                h2 {{ margin: 0; font-weight: 600; color: #fff; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }}
                .stat-card {{ background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                .stat-card h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
                .stat-card .value {{ font-size: 28px; font-weight: bold; color: var(--accent); }}
                table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                th, td {{ padding: 12px 15px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
                th {{ background-color: #0f172a; color: #cbd5e1; font-weight: 600; }}
                tr:hover {{ background-color: #2a3b54; }}
                .badge {{ background: #059669; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
                .path {{ font-family: monospace; color: #fbbf24; }}
                .agent {{ max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>⚡ CTI Dashboard Analytics</h2>
                <div style="color: #94a3b8; font-size: 14px;">Live Server Data</div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Recent Requests</h3>
                    <div class="value">{total_hits}</div>
                </div>
                <div class="stat-card">
                    <h3>Unique Visitors (IPs)</h3>
                    <div class="value">{unique_ips}</div>
                </div>
                <div class="stat-card">
                    <h3>Most Active Path</h3>
                    <div class="value" style="font-size: 18px; line-height: 32px;">{top_path}</div>
                </div>
            </div>

            <table>
                <tr>
                    <th>Time (IST)</th>
                    <th>IP Address</th>
                    <th>Location & ISP</th>
                    <th>Method</th>
                    <th>Path</th>
                    <th>Status</th>
                    <th>User Agent</th>
                </tr>
        """
        
        for r in rows:
            path_display = r['path']
            if r['query_params']:
                path_display += f"?{r['query_params']}"
                
            status_color = "#059669" if r['status_code'] < 400 else "#dc2626"
            
            html += f"""
                <tr>
                    <td style="color: #94a3b8;">{r['timestamp']}</td>
                    <td style="font-weight: 500;">{r['ip_address']}</td>
                    <td>{r['location']}</td>
                    <td><span class="badge" style="background: var(--accent);">{r['method']}</span></td>
                    <td class="path">{path_display}</td>
                    <td><span class="badge" style="background: {status_color};">{r['status_code']}</span></td>
                    <td class="agent" title="{r['user_agent']}">{r['user_agent']}</td>
                </tr>
            """
            
        html += """
            </table>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}




# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "app" / "web"
DATA_ROOT = Path(__file__).resolve().parent / "core" / "data"

# Initialize engines on startup
@app.on_event("startup")
def startup_event():
    psychro_bin = DATA_ROOT / "psychro_f_alt.bin"
    merkel_bin = DATA_ROOT / "merkel_poly.bin"
    if psychro_bin.exists() and merkel_bin.exists():
        init_engines(str(psychro_bin), str(merkel_bin))
        print("Engines initialized successfully.")
    else:
        print("[WARNING] Could not find binary data files from", DATA_ROOT)

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

class ExcelExportRequest(BaseModel):
    inputs: dict
    curves: dict

class LocalFilterRequest(BaseModel):
    startTime: Optional[str] = ""
    endTime: Optional[str] = ""
    sourcePath: str
    destPath: Optional[str] = ""

class KaVLRequest(BaseModel):
    wbt: float
    hwt: float
    cwt: float
    lg: float

class Atc105Request(BaseModel):
    # Design (nameplate / contract) conditions
    design_wbt: float
    design_cwt: float
    design_hwt: float
    design_flow: float         # m3/hr at 100% flow
    design_fan_power: float = 117.0  # kW
    # Test (site-measured) conditions
    test_wbt: float
    test_cwt: float
    test_hwt: float
    test_flow: float           # m3/hr
    test_fan_power: float = 117.0    # kW
    # Thermal model constants — C and m use sensible defaults if not supplied
    lg_ratio: float
    constant_c: float = 1.2
    constant_m: float = 0.6
    # Optional: override density ratio with value from ATC-105 standard tables
    # (default None → auto-computed from Kell 1975 water density formula)
    density_ratio_override: float | None = None
    # Safety margin offsets from Thermal Analysis (all optional, default 0)
    # Applied to Table 1 CWT values using same anchored-tilt model as curve generation:
    # zero correction at design_wbt, full offset_wbt20 at 20°C WBT.
    offset_wbt20: float = 0.0
    off90r80:     float = 0.0
    off90r100:    float = 0.0
    off90r120:    float = 0.0
    off100r80:    float = 0.0
    off100r100:   float = 0.0
    off100r120:   float = 0.0
    off110r80:    float = 0.0
    off110r100:   float = 0.0
    off110r120:   float = 0.0

# Calculation endpoints
@app.post("/api/calculate/kavl")
async def api_calc_kavl(req: KaVLRequest):
    try:
        res = merkel_kavl(req.hwt, req.cwt, req.wbt, req.lg)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/calculate/psychro")
async def api_calc_psychro(req: PsychroRequest):
    try:
        res = psychrometrics(req.dbt, req.wbt, req.alt)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/calculate/predict")
async def api_calc_predict(req: PredictRequest):
    try:
        res = solve_off_design_cwt(req.wbt, req.range, req.lg, req.constC, req.constM)
        if not res:
            raise HTTPException(status_code=400, detail="Cannot solve prediction for given parameters.")
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/calculate/calibrate")
async def api_calc_calibrate(req: CalibrateRequest):
    try:
        from core.calculations import calculate_demand_kavl
        target_hwt = req.targetCWT + req.designRange
        demand_kavl = calculate_demand_kavl(req.designWBT, target_hwt, req.targetCWT, req.lgRatio)
        
        if math.isnan(demand_kavl) or demand_kavl <= 0:
            raise ValueError("Invalid thermodynamics for given target CWT. Demand KaV/L did not converge.")

        # demand_kavl = C * (L/G)^-m
        # C = demand_kavl / ((L/G)^-m)
        constant_c = demand_kavl / math.pow(req.lgRatio, -req.constantM)
        
        return {"constantC": round(constant_c, 4), "demandKavl": round(demand_kavl, 4)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/api/calculate/curves")
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
            # Format wbt exactly like JS loop
            wbt_val = float(f"{wbt:.2f}")
            cwt80 = find_cwt(inputs_dict, wbt_val, 80, req.flowPercent)
            cwt100 = find_cwt(inputs_dict, wbt_val, 100, req.flowPercent)
            cwt120 = find_cwt(inputs_dict, wbt_val, 120, req.flowPercent)

            if not (math.isnan(cwt80) or math.isnan(cwt100) or math.isnan(cwt120)):
                # Apply Safety Offsets
                # 1. WBT Rotation: Anchor at designWBT=0 offset. At wbt=20, offset is offsetWbt20.
                if inputs_dict.get('designWBT') != 20:
                    wbt_slope = req.inputs.offsetWbt20 / (20.0 - req.inputs.designWBT)
                    wbt_correction = wbt_slope * (wbt_val - req.inputs.designWBT)
                else:
                    wbt_correction = req.inputs.offsetWbt20 if wbt_val == 20 else 0
                
                # 2. 3x3 Grid Offsets (Converted to Anchored Tilts)
                raw_off80 = raw_off100 = raw_off120 = 0.0
                if req.flowPercent == 90:
                    raw_off80 = req.inputs.off90r80
                    raw_off100 = req.inputs.off90r100
                    raw_off120 = req.inputs.off90r120
                elif req.flowPercent == 100:
                    raw_off80 = req.inputs.off100r80
                    raw_off100 = req.inputs.off100r100
                    raw_off120 = req.inputs.off100r120
                elif req.flowPercent == 110:
                    raw_off80 = req.inputs.off110r80
                    raw_off100 = req.inputs.off110r100
                    raw_off120 = req.inputs.off110r120

                # Calculate the tilt multiplier: 1.0 at WBT=20, 0.0 at DesignWBT
                if inputs_dict.get('designWBT') != 20:
                    tilt_multiplier = (wbt_val - req.inputs.designWBT) / (20.0 - req.inputs.designWBT)
                else:
                    tilt_multiplier = 1.0 if wbt_val == 20 else 0.0

                # Apply base WBT tilt and grid-specific tilted offsets
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

@app.post("/api/calculate/atc105")
async def api_calc_atc105(req: Atc105Request):
    """
    CTI ATC-105 Five-Step Performance Evaluation.
    Returns all intermediate tables, cross-plot data, adjusted flow,
    predicted CWT, shortfall and capability.
    """
    try:
        def _lerp(x, x0, x1, y0, y1):
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

        def _interp_curve(x, xs, ys):
            """Linear interpolation / extrapolation along a curve."""
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

        def _water_density(T):
            """Kell (1975) water density (kg/m³), valid 0–100 °C."""
            num = (999.83952 + 16.945176 * T - 7.9870401e-3 * T ** 2
                   - 46.170461e-6 * T ** 3 + 105.56302e-9 * T ** 4
                   - 280.54253e-12 * T ** 5)
            return num / (1 + 16.879850e-3 * T)

        design_range = req.design_hwt - req.design_cwt
        test_range   = req.test_hwt  - req.test_cwt
        test_range_pct = (test_range / design_range) * 100.0

        range_pcts = [80.0, 100.0, 120.0]   # % of design range
        flow_pcts  = [90,   100,   110]      # % of design flow

        # Absolute range values (°C)
        ranges_abs = {int(rp): round(design_range * rp / 100.0, 3) for rp in range_pcts}

        # Absolute flow values (m3/hr)
        flows_m3h = {fp: round(req.design_flow * fp / 100.0, 2) for fp in flow_pcts}

        # Inputs dict for find_cwt (uses design HWT/CWT to derive design_range internally)
        base_inputs = {
            "lgRatio":    req.lg_ratio,
            "constantC":  req.constant_c,
            "constantM":  req.constant_m,
            "designHWT":  req.design_hwt,
            "designCWT":  req.design_cwt,
        }

        # ── STEP 1: Table 1 – CWT at test WBT for 3 ranges × 3 flows ─────────
        table1 = {}
        for fp in flow_pcts:
            table1[fp] = {}
            for rp in range_pcts:
                val = find_cwt(base_inputs, req.test_wbt, rp, fp)
                table1[fp][int(rp)] = round(val, 3) if not math.isnan(val) else None

        # ── Apply safety margin offsets (if any non-zero) ─────────────────────
        # Same anchored-tilt model used by the Thermal Analysis curve generator:
        # offset = 0 at design_wbt, full offset_wbt20 at 20°C (linearly tapered).
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

        # ── STEP 2: Cross Plot 1 – interpolate at test_range_pct ─────────────
        cross1 = {}
        for fp in flow_pcts:
            r80  = table1[fp][80]
            r100 = table1[fp][100]
            r120 = table1[fp][120]
            if any(v is None for v in [r80, r100, r120]):
                cross1[fp] = None
                continue
            if test_range_pct <= 100.0:
                cwt = _lerp(test_range_pct, 80.0, 100.0, r80, r100)
            else:
                cwt = _lerp(test_range_pct, 100.0, 120.0, r100, r120)
            cross1[fp] = round(cwt, 3)

        cp2_flows = [flows_m3h[fp] for fp in flow_pcts]
        cp2_cwts  = [cross1[fp]   for fp in flow_pcts]

        # ── STEP 4: Adjusted water flow ───────────────────────────────────────
        avg_test_T   = (req.test_hwt   + req.test_cwt)   / 2.0
        avg_design_T = (req.design_hwt + req.design_cwt) / 2.0
        density_test   = _water_density(avg_test_T)
        density_design = _water_density(avg_design_T)
        density_ratio  = density_test / density_design

        # Use override if supplied (e.g., value from ATC-105 standard lookup tables)
        effective_density_ratio = req.density_ratio_override if req.density_ratio_override else density_ratio

        adj_flow = (req.test_flow
                    * (req.design_fan_power / req.test_fan_power) ** (1 / 3)
                    * effective_density_ratio ** (1 / 3))

        # ── STEP 5: Predict CWT at adj_flow, find pred_flow at design CWT ────
        valid_pairs = [(f, c) for f, c in zip(cp2_flows, cp2_cwts) if c is not None]
        vf = [p[0] for p in valid_pairs]
        vc = [p[1] for p in valid_pairs]

        pred_cwt  = round(_interp_curve(adj_flow,      vf, vc), 3) if vf else None
        # ATC-105 Appendix C: draw horizontal from Test CWT to the curve → read Predicted Flow
        pred_flow = round(_interp_curve(req.test_cwt, vc, vf), 2) if vf else None

        shortfall  = round(req.test_cwt - pred_cwt, 3) if pred_cwt is not None else None
        capability = round((adj_flow / pred_flow) * 100, 1) if pred_flow and pred_flow > 0 else None

        return {
            "design_range":    round(design_range, 3),
            "test_range":      round(test_range, 3),
            "test_range_pct":  round(test_range_pct, 2),
            "ranges_abs":      ranges_abs,
            "flows_m3h":       flows_m3h,
            # Table 1: {flow_pct: {range_pct: cwt}}
            "table1": {
                str(fp): {str(int(rp)): table1[fp][int(rp)] for rp in range_pcts}
                for fp in flow_pcts
            },
            # Cross Plot 1 series (for plotting)
            "cross_plot_1": {
                "ranges_abs":  [ranges_abs[int(rp)] for rp in range_pcts],
                "cwt_90":      [table1[90][int(rp)]  for rp in range_pcts],
                "cwt_100":     [table1[100][int(rp)] for rp in range_pcts],
                "cwt_110":     [table1[110][int(rp)] for rp in range_pcts],
                "test_range":  round(test_range, 3),
                "f90_cwt":     cross1[90],
                "f100_cwt":    cross1[100],
                "f110_cwt":    cross1[110],
            },
            # Cross Plot 2 data (for plotting)
            "cross_plot_2": {
                "flows":      cp2_flows,
                "cwts":       cp2_cwts,
                "adj_flow":   round(adj_flow, 2),
                "pred_flow":  pred_flow,
                "pred_cwt":   pred_cwt,
                "test_cwt":   req.test_cwt,
                "design_cwt": req.design_cwt,
            },
            # Density correction details
            "density_test":    round(density_test,   4),
            "density_design":  round(density_design, 4),
            "density_ratio":   round(density_ratio,  6),          # auto-computed (Kell 1975)
            "density_ratio_used": round(effective_density_ratio, 6),  # actual value used in adj_flow
            # Top-level summary
            "adj_flow":    round(adj_flow, 2),
            "pred_cwt":    pred_cwt,
            "pred_flow":   pred_flow,
            "shortfall":   shortfall,
            "capability":  capability,
            # Pass through request inputs for report template
            "design_wbt":  req.design_wbt,
            "design_cwt":  req.design_cwt,
            "design_hwt":  req.design_hwt,
            "design_flow": req.design_flow,
            "test_wbt":    req.test_wbt,
            "test_cwt":    req.test_cwt,
            "test_hwt":    req.test_hwt,
            "test_flow":   req.test_flow,
            # Safety margins applied (non-empty only if offsets were used)
            "offsets_applied": {
                "offset_wbt20": req.offset_wbt20,
                "off90r80":  req.off90r80,  "off90r100":  req.off90r100,  "off90r120":  req.off90r120,
                "off100r80": req.off100r80, "off100r100": req.off100r100, "off100r120": req.off100r120,
                "off110r80": req.off110r80, "off110r100": req.off110r100, "off110r120": req.off110r120,
            } if _has_offsets else {},
        }
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=400, detail=f"ATC-105 error: {exc}\n{traceback.format_exc()}")


# Excel Export 
@app.post("/api/export-excel")
async def export_excel(payload: dict):
    project_name = payload.get("inputs", {}).get("projectName", "Thermal Analysis")
    safe_name = sanitize_filename(project_name)
    download_name = f"Professional_Report_{safe_name}.xlsx"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = os.path.join(temp_dir, download_name)
            generate_excel_from_payload(payload, temp_output)
            with open(temp_output, "rb") as f:
                file_bytes = f.read()

        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to generate report: {exc}")

@app.post("/api/parse-filter-excel")
async def api_parse_filter_excel(file: UploadFile = File(...)):
    """
    Parse a Filter Tool output Excel and extract averaged test values
    (CWT, HWT, WBT, DBT, flow, fan power) for auto-filling the Report Builder.
    Reads the "Filtered Data" sheet and identifies the COLUMN AVERAGE row,
    then classifies columns by keyword (cwt/hwt/wbt/dbt) or by Source File name.
    """
    import pandas as pd
    from io import BytesIO

    content = await file.read()
    df = None
    for sheet_arg in ['Filtered Data', 0]:
        try:
            df = pd.read_excel(BytesIO(content), sheet_name=sheet_arg)
            break
        except Exception:
            continue
    if df is None:
        raise HTTPException(status_code=400, detail="Cannot read Excel file")

    # ── Locate the COLUMN AVERAGE row ────────────────────────────────────────
    avg_row_data: dict = {}
    for i in range(max(0, len(df) - 5), len(df)):
        first = str(df.iloc[i, 0]).strip().upper()
        if 'AVERAGE' in first:
            for col_idx, col_name in enumerate(df.columns):
                try:
                    fval = float(df.iloc[i, col_idx])
                    if math.isfinite(fval) and 0 < abs(fval) < 1e12:
                        avg_row_data[str(col_name)] = round(fval, 4)
                except (ValueError, TypeError):
                    pass
            break

    # Fallback: compute averages from all numeric data rows (skip OL values)
    if not avg_row_data:
        skip_kw = {'source', 'file', 'date', 'time', 'scan', 'number'}
        for col in df.columns:
            if any(k in str(col).lower() for k in skip_kw):
                continue
            series = pd.to_numeric(df[col], errors='coerce')
            series = series[series.abs() < 1e12]
            if series.notna().sum() >= 2:
                avg_row_data[str(col)] = round(float(series.mean()), 4)

    # ── Classify by column name keyword ──────────────────────────────────────
    cwt_vals, hwt_vals, wbt_vals, dbt_vals, flow_vals, power_vals = [], [], [], [], [], []
    for col_name, avg_val in avg_row_data.items():
        cl = col_name.lower()
        if 'cwt' in cl or 'cold' in cl:
            cwt_vals.append(avg_val)
        elif 'hwt' in cl or 'hot' in cl:
            hwt_vals.append(avg_val)
        elif 'wbt' in cl or 'wet' in cl:
            wbt_vals.append(avg_val)
        elif 'dbt' in cl or 'dry' in cl:
            dbt_vals.append(avg_val)
        elif 'flow' in cl:
            flow_vals.append(avg_val)
        elif 'kw' in cl or 'power' in cl:
            power_vals.append(avg_val)

    # ── Fallback: classify by Source File name (multi-file layout) ───────────
    if not any([cwt_vals, hwt_vals, wbt_vals]) and 'Source File' in df.columns:
        skip_kw2 = {'source file', 'date', 'time', 'scan'}
        val_col = next(
            (c for c in df.columns
             if c not in ['Source File'] and 'time' not in c.lower() and 'date' not in c.lower()
             and pd.api.types.is_numeric_dtype(df[c])), None)
        if val_col:
            for src_file, group in df.groupby('Source File'):
                src_lower = str(src_file).lower()
                series = pd.to_numeric(group[val_col], errors='coerce')
                series = series[series.abs() < 1e12]
                if series.notna().sum() < 2:
                    continue
                avg_v = round(float(series.mean()), 4)
                if 'cwt' in src_lower:
                    cwt_vals.append(avg_v)
                elif 'hwt' in src_lower:
                    hwt_vals.append(avg_v)
                elif 'wbt' in src_lower:
                    wbt_vals.append(avg_v)
                elif 'dbt' in src_lower:
                    dbt_vals.append(avg_v)

    def _mean(vals):
        return round(sum(vals) / len(vals), 3) if vals else None

    return {
        "cwt":        _mean(cwt_vals),
        "hwt":        _mean(hwt_vals),
        "wbt":        _mean(wbt_vals),
        "dbt":        _mean(dbt_vals),
        "flow":       _mean(flow_vals),
        "fan_power":  _mean(power_vals),
        "all_averages": avg_row_data,
        "columns": list(df.columns.astype(str)),
    }


# Filter Excel
@app.post("/api/filter-excel")
async def filter_excel(
    startTime: Optional[str] = Form(default=""),
    endTime: Optional[str] = Form(default=""),
    files: List[UploadFile] = File(...)
):
    SUPPORTED_EXT = ('.xlsx', '.xls')
    valid_files = [f for f in files if f.filename.lower().endswith(SUPPORTED_EXT)]
    if not valid_files:
        raise HTTPException(status_code=400, detail="Please upload valid .xlsx or .xls files.")

    file_items = []
    for f in valid_files:
        file_bytes = await f.read()
        file_items.append((f.filename, file_bytes))

    try:
        download_name, final_bytes = generate_filtered_workbook(file_items, startTime, endTime)
        return Response(
            content=final_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to filter files: {exc}")

# Local filter API (Secured)
@app.post("/api/filter-excel-local")
async def filter_excel_local(req: LocalFilterRequest):
    # SECURITY: Check environment variable to allow local file writing
    if os.environ.get("ENABLE_LOCAL_WRITE", "0") != "1":
        raise HTTPException(status_code=403, detail="Local file writing is disabled for security reasons on this server.")

    if not req.sourcePath:
        raise HTTPException(status_code=400, detail="sourcePath is required.")

    try:
        download_name, bg_bytes = generate_filtered_workbook_from_directory(req.sourcePath, req.startTime, req.endTime)
        
        dest_path = req.destPath.strip() if req.destPath else ""
        if dest_path:
            os.makedirs(dest_path, exist_ok=True)
            full_save_path = os.path.join(dest_path, download_name)
            with open(full_save_path, "wb") as f:
                f.write(bg_bytes)
            
            return {"message": f"Success! File saved directly to {dest_path}", "isFile": False}
        
        return Response(
            content=bg_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to filter files: {exc}")

# ── Temporary PDF store (token → bytes, expires after 5 min) ─────────────────
# This pattern avoids blob:// URLs which are inaccessible to external download
# managers (e.g. IDM) that try to re-fetch the URL in a separate process.
_PDF_STORE: dict[str, tuple[bytes, str, float]] = {}  # token → (bytes, filename, expiry)
_PDF_STORE_LOCK = threading.Lock()

def _cleanup_pdf_store():
    """Background thread: purge expired tokens every 60 seconds."""
    while True:
        time.sleep(60)
        now = time.time()
        with _PDF_STORE_LOCK:
            expired = [k for k, (_, _, exp) in _PDF_STORE.items() if now > exp]
            for k in expired:
                del _PDF_STORE[k]

threading.Thread(target=_cleanup_pdf_store, daemon=True).start()


@app.post("/api/generate-pdf-report")
def api_generate_pdf_report(payload: dict):
    """
    Step 1 of 2: Generate the ATC-105 PDF and store it server-side with a
    short-lived UUID token. Returns {"token": "...", "filename": "..."} so
    the frontend can redirect to /api/download-pdf/{token} — a plain GET URL
    that external download managers (IDM etc.) can fetch independently.
    """
    try:
        pdf_bytes = generate_pdf_report(payload)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {str(e)}\n{traceback.format_exc()}")

    token    = uuid.uuid4().hex
    filename = payload.get("_filename", "CTI_Performance_Report_ATC105.pdf")
    expiry   = time.time() + 300  # 5 minutes

    with _PDF_STORE_LOCK:
        _PDF_STORE[token] = (pdf_bytes, filename, expiry)

    return {"token": token, "filename": filename}


@app.get("/api/download-pdf/{token}")
def api_download_pdf(token: str):
    """
    Step 2 of 2: Serve the pre-generated PDF via a normal HTTP GET.
    This URL is a real server resource — IDM and other download managers
    can access it in a separate process without any blob:// restriction.
    Token is single-use: consumed on first download.
    """
    with _PDF_STORE_LOCK:
        entry = _PDF_STORE.pop(token, None)

    if entry is None:
        raise HTTPException(status_code=404, detail="PDF token not found or already downloaded.")

    pdf_bytes, filename, expiry = entry
    if time.time() > expiry:
        raise HTTPException(status_code=410, detail="PDF token has expired. Please regenerate.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# Serve UI
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(str(WEB_ROOT / "favicon.svg"))

app.mount("/css", StaticFiles(directory=str(WEB_ROOT / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(WEB_ROOT / "js")), name="js")

templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

if __name__ == "__main__":
    port = 8000
    print(f"Starting highly optimized FastAPI server on http://localhost:{port}")
    # Local mode automatically sets the ENABLE_LOCAL_WRITE flag so Windows batch users can filter excel 
    os.environ["ENABLE_LOCAL_WRITE"] = "1"
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
