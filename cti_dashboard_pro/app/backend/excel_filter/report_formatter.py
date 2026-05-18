import re
import pandas as pd
from typing import List, Any
from .cleaners import _merge_sensor_dfs
from .formatters.base import _style_sheet
from .formatters.inline_sensor import _create_inline_sensor_report
from .formatters.generic_layout import _render_generic_layout
from .formatters.cwt_hwt_layout import _render_cwt_hwt_layout
from .formatters.helpers import _extract_generic_sensor_id

def _create_report_layout(writer, master_df, sheet_name='Report Layout'):
    if master_df.empty:
        return

    # Prefer exact-match 'date' / 'time' column names (e.g. synthetic 'Date',
    # 'Time' we insert) before falling back to partial-match columns like
    # 'Scan Sweep Time (Sec)' which would give wrong display values.
    date_col = (
        next((c for c in master_df.columns if str(c).strip().lower() == 'date'), None)
        or next((c for c in master_df.columns if 'date' in str(c).lower()), None)
    )
    time_col = (
        next((c for c in master_df.columns if str(c).strip().lower() == 'time'), None)
        or next((c for c in master_df.columns if 'time' in str(c).lower()), None)
    )
    if not date_col or not time_col:
        return

    # ── Detect inline sensor columns ────────────────────────────────────────
    # A "DAQ-style" file has sensor readings spread across COLUMNS rather than
    # across FILES.  Recognise this when column names themselves carry the
    # CWT / HWT / DBT / WBT tags (e.g. '102 (°C)- CWT A').
    _skip = {'Source File', date_col, time_col}
    inline_cwt = sorted([c for c in master_df.columns if 'cwt' in str(c).lower() and c not in _skip])
    inline_hwt = sorted([c for c in master_df.columns if 'hwt' in str(c).lower() and c not in _skip])
    inline_dbt = sorted([c for c in master_df.columns if 'dbt' in str(c).lower() and c not in _skip])
    inline_wbt = sorted([c for c in master_df.columns if 'wbt' in str(c).lower() and c not in _skip])
    has_inline = any([inline_cwt, inline_hwt, inline_dbt, inline_wbt])

    if has_inline:
        _create_inline_sensor_report(
            writer, master_df, sheet_name,
            date_col, time_col,
            inline_cwt, inline_hwt, inline_dbt, inline_wbt
        )
        return

    # Primary value column (NTC / anything with 'value')
    val_col = next((c for c in master_df.columns if 'ntc' in str(c).lower() or 'value' in str(c).lower()), None)
    if not val_col:
        val_col = next(
            (
                c for c in master_df.columns
                if c not in ['Source File', date_col, time_col] and pd.api.types.is_numeric_dtype(master_df[c])
            ),
            None
        )
    if not val_col:
        return

    # ── Categorise source files ─────────────────────────────────────────────
    cwt_dfs: List[Any] = []
    hwt_dfs: List[Any] = []
    dbt_dfs: List[Any] = []
    wbt_dfs: List[Any] = []
    unclassified_dfs: List[Any] = []   # files whose names lack CWT/HWT/DBT/WBT
    seen_sensors: set = set()

    for file_name, group in master_df.groupby('Source File'):
        lower_name = file_name.lower()
        is_classified = any(k in lower_name for k in ('cwt', 'hwt', 'dbt', 'wbt'))

        # Sensor ID
        if is_classified:
            matches = re.findall(r'\d{2,}', file_name) or re.findall(r'\d+', file_name)
            base_sensor = max(matches, key=lambda x: (len(x), int(x))) if matches else file_name.split('.')[0]
        else:
            base_sensor = _extract_generic_sensor_id(file_name)

        sensor_no = base_sensor
        counter = 1
        while sensor_no in seen_sensors:
            sensor_no = f"{base_sensor}_{counter}"
            counter += 1
        seen_sensors.add(sensor_no)

        subset = group[[date_col, time_col, val_col]].copy()
        subset.rename(columns={val_col: sensor_no}, inplace=True)
        subset[time_col] = subset[time_col].map(lambda x: str(x).split('.')[0] if pd.notna(x) else x)
        if pd.api.types.is_datetime64_any_dtype(subset[date_col]):
            subset[date_col] = subset[date_col].dt.strftime('%d-%m-%Y')

        if 'cwt' in lower_name:
            cwt_dfs.append(subset)
        elif 'hwt' in lower_name:
            hwt_dfs.append(subset)
        elif 'dbt' in lower_name:
            dbt_dfs.append(subset)
        elif 'wbt' in lower_name:
            wbt_dfs.append(subset)
        else:
            unclassified_dfs.append(subset)

    water_df   = _merge_sensor_dfs(cwt_dfs + hwt_dfs, date_col, time_col)
    air_df     = _merge_sensor_dfs(dbt_dfs + wbt_dfs, date_col, time_col)
    generic_df = _merge_sensor_dfs(unclassified_dfs, date_col, time_col)

    if water_df.empty and air_df.empty and generic_df.empty:
        return

    workbook = writer.book
    safe_sheet_name = sheet_name[:31]
    worksheet = workbook.add_worksheet(safe_sheet_name)

    if not generic_df.empty and water_df.empty and air_df.empty:
        _render_generic_layout(writer, worksheet, master_df, generic_df, date_col, time_col, val_col)
    else:
        cwt_cols = sorted([c for df in cwt_dfs for c in df.columns if c not in [date_col, time_col, '_merge_key']])
        hwt_cols = sorted([c for df in hwt_dfs for c in df.columns if c not in [date_col, time_col, '_merge_key']])
        dbt_cols = sorted([c for df in dbt_dfs for c in df.columns if c not in [date_col, time_col, '_merge_key']])
        wbt_cols = sorted([c for df in wbt_dfs for c in df.columns if c not in [date_col, time_col, '_merge_key']])
        _render_cwt_hwt_layout(writer, worksheet, master_df, water_df, air_df, cwt_cols, hwt_cols, dbt_cols, wbt_cols, date_col, time_col)
