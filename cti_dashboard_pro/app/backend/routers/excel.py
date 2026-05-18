import os
import tempfile
import math
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from services.excel_gen import generate_excel_from_payload, sanitize_filename
from excel_filter import generate_filtered_workbook, generate_filtered_workbook_from_directory

router = APIRouter()

class ExcelExportRequest(BaseModel):
    inputs: dict
    curves: dict

class LocalFilterRequest(BaseModel):
    startTime: Optional[str] = ""
    endTime: Optional[str] = ""
    sourcePath: str
    destPath: Optional[str] = ""

@router.post("/export-excel")
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

@router.post("/parse-filter-excel")
async def api_parse_filter_excel(file: UploadFile = File(...)):
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

    if not avg_row_data:
        skip_kw = {'source', 'file', 'date', 'time', 'scan', 'number'}
        for col in df.columns:
            if any(k in str(col).lower() for k in skip_kw):
                continue
            series = pd.to_numeric(df[col], errors='coerce')
            series = series[series.abs() < 1e12]
            if series.notna().sum() >= 2:
                avg_row_data[str(col)] = round(float(series.mean()), 4)

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

@router.post("/filter-excel")
async def filter_excel(
    startTime: Optional[str] = Form(default=""),
    endTime: Optional[str] = Form(default=""),
    files: List[UploadFile] = File(...)
):
    SUPPORTED_EXT = ('.xlsx', '.xls', '.csv', '.zip')
    valid_files = [f for f in files if f.filename.lower().endswith(SUPPORTED_EXT)]
    if not valid_files:
        raise HTTPException(status_code=400, detail="Please upload valid .xlsx, .xls, .csv, or .zip files.")

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

@router.post("/filter-excel-local")
async def filter_excel_local(req: LocalFilterRequest):
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
