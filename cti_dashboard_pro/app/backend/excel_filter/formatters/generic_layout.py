import pandas as pd
from typing import List, Any
from .formats import get_format_dict, get_avg_val_fmts
from .helpers import _extract_generic_sensor_id
from ..cleaners import _merge_sensor_dfs

def _render_generic_layout(
    writer, worksheet, master_df, generic_df,
    date_col, time_col, val_col,
    total_cols_param=None
):
    workbook = writer.book
    fmts = get_format_dict(workbook)
    avg_val_fmts = get_avg_val_fmts(workbook)

    gen_sensor_cols = [c for c in generic_df.columns if c not in [date_col, time_col]]

    # Try to find a secondary numeric column (e.g. Tem_Value alongside Main_Value)
    secondary_val_col = next(
        (
            c for c in master_df.columns
            if c not in ['Source File', date_col, time_col, val_col]
            and pd.api.types.is_numeric_dtype(master_df[c])
            and 'no' not in c.lower()    # skip row-number columns like 'NO'
        ),
        None
    )

    # Build secondary (temperature) DF with same sensor IDs
    secondary_df = pd.DataFrame()
    sec_sensor_cols: List[str] = []
    if secondary_val_col:
        sec_dfs: List[Any] = []
        seen_sec: set = set()
        for file_name, group in master_df.groupby('Source File'):
            sec_id = _extract_generic_sensor_id(file_name)
            sno = sec_id
            sc = 1
            while sno in seen_sec:
                sno = f"{sec_id}_{sc}"
                sc += 1
            seen_sec.add(sno)
            s = group[[date_col, time_col, secondary_val_col]].copy()
            s.rename(columns={secondary_val_col: sno}, inplace=True)
            s[time_col] = s[time_col].map(lambda x: str(x).split('.')[0] if pd.notna(x) else x)
            if pd.api.types.is_datetime64_any_dtype(s[date_col]):
                s[date_col] = s[date_col].dt.strftime('%d-%m-%Y')
            sec_dfs.append(s)
        secondary_df = _merge_sensor_dfs(sec_dfs, date_col, time_col)
        sec_sensor_cols = [c for c in secondary_df.columns if c not in [date_col, time_col]]

    # ── Column layout dimensions ────────────────────────────────────────
    n_vel   = len(gen_sensor_cols)
    n_temp  = len(sec_sensor_cols)
    vel_start  = 2                                      # after Date + Time
    vel_end    = vel_start + n_vel - 1
    # Temperature section: skip 2 cols (Date + Time) after velocity section
    temp_start: Any = (vel_end + 3) if n_temp > 0 else None
    temp_end: Any   = (temp_start + n_temp - 1) if (n_temp > 0 and temp_start is not None) else None
    total_cols = vel_start + n_vel + (2 + n_temp if n_temp > 0 else 0)

    # ── Title ───────────────────────────────────────────────────────────
    worksheet.merge_range(0, 0, 0, total_cols - 1, 'Performance Test Consolidated Report', fmts['title_fmt'])

    # ── Velocity section (row 1 + row 2) ────────────────────────────────
    worksheet.write(1, 0, 'Date', fmts['date_time_fmt'])
    worksheet.write(1, 1, 'Time', fmts['date_time_fmt'])
    vel_label = f'Velocity / Main Value  [{val_col}]'
    if n_vel > 1:
        worksheet.merge_range(1, vel_start, 1, vel_end, vel_label, fmts['vel_header_fmt'])
    else:
        worksheet.write(1, vel_start, vel_label, fmts['vel_header_fmt'])
    worksheet.merge_range(2, 0, 2, 1, 'Sensor No.', fmts['sensor_fmt'])
    for ci, col_name in enumerate(gen_sensor_cols):
        worksheet.write(2, vel_start + ci, col_name, fmts['sensor_fmt'])

    # ── Temperature section (row 1 + row 2) ─────────────────────────────
    if n_temp > 0 and temp_start is not None and temp_end is not None:
        worksheet.write(1, temp_start - 2, 'Date', fmts['date_time_fmt'])
        worksheet.write(1, temp_start - 1, 'Time', fmts['date_time_fmt'])
        temp_label = f'Temperature  [{secondary_val_col}]'
        if n_temp > 1:
            worksheet.merge_range(1, temp_start, 1, temp_end, temp_label, fmts['temp_header_fmt'])
        else:
            worksheet.write(1, temp_start, temp_label, fmts['temp_header_fmt'])
        worksheet.merge_range(2, temp_start - 2, 2, temp_start - 1, 'Sensor No.', fmts['sensor_fmt'])
        for ci, col_name in enumerate(sec_sensor_cols):
            worksheet.write(2, temp_start + ci, col_name, fmts['sensor_fmt'])

    # ── Data rows ────────────────────────────────────────────────────────
    max_rows_gen = max(
        len(generic_df),
        len(secondary_df) if not secondary_df.empty else 0
    )

    def _write_cell(ws, row, col, val, num_fmt, s_fmt):
        if pd.isna(val) or str(val).lower() == 'nan':
            ws.write_string(row, col, '', s_fmt)
        else:
            try:
                ws.write_number(row, col, float(val), num_fmt)
            except (TypeError, ValueError):
                ws.write_string(row, col, str(val), s_fmt)

    for r_idx in range(max_rows_gen):
        target_row = r_idx + 3
        # Velocity rows
        if r_idx < len(generic_df):
            g_row = generic_df.iloc[r_idx]
            dv = g_row.get(date_col, '')
            worksheet.write_string(target_row, 0,
                '' if (pd.isna(dv) or str(dv).lower() == 'nan') else str(dv), fmts['str_data_fmt'])
            tv = g_row.get(time_col, '')
            worksheet.write_string(target_row, 1,
                '' if (pd.isna(tv) or str(tv).lower() == 'nan') else str(tv), fmts['str_data_fmt'])
            for ci, col_name in enumerate(gen_sensor_cols):
                _write_cell(worksheet, target_row, vel_start + ci, g_row.get(col_name), fmts['data_fmt'], fmts['str_data_fmt'])
        # Temperature rows
        if n_temp > 0 and not secondary_df.empty and temp_start is not None and r_idx < len(secondary_df):
            s_row = secondary_df.iloc[r_idx]
            dv2 = s_row.get(date_col, '')
            worksheet.write_string(target_row, temp_start - 2,
                '' if (pd.isna(dv2) or str(dv2).lower() == 'nan') else str(dv2), fmts['str_data_fmt'])
            tv2 = s_row.get(time_col, '')
            worksheet.write_string(target_row, temp_start - 1,
                '' if (pd.isna(tv2) or str(tv2).lower() == 'nan') else str(tv2), fmts['str_data_fmt'])
            for ci, col_name in enumerate(sec_sensor_cols):
                _write_cell(worksheet, target_row, temp_start + ci, s_row.get(col_name), fmts['data_fmt'], fmts['str_data_fmt'])

    worksheet.set_column(0, max(total_cols - 1, 0), 13)

    # ── Average rows ─────────────────────────────────────────────────────
    avg_row_idx       = max_rows_gen + 4
    total_avg_row_idx = max_rows_gen + 5

    # Velocity section labels
    worksheet.write(avg_row_idx,       0, '', fmts['avg_label_fmt'])
    worksheet.write(avg_row_idx,       1, 'Average',       fmts['avg_label_fmt'])
    worksheet.write(total_avg_row_idx, 0, '', fmts['avg_label_fmt'])
    worksheet.write(total_avg_row_idx, 1, 'Total Average', fmts['avg_label_fmt'])
    # Temperature section labels
    if n_temp > 0 and temp_start is not None:
        worksheet.write(avg_row_idx,       temp_start - 2, '', fmts['avg_label_fmt'])
        worksheet.write(avg_row_idx,       temp_start - 1, 'Average',       fmts['avg_label_fmt'])
        worksheet.write(total_avg_row_idx, temp_start - 2, '', fmts['avg_label_fmt'])
        worksheet.write(total_avg_row_idx, temp_start - 1, 'Total Average', fmts['avg_label_fmt'])

    def _write_section_avgs(df, cols, col_offset, avg_fmt_key):
        avgs = []
        fmt = avg_val_fmts[avg_fmt_key]
        for ci, col_name in enumerate(cols):
            series = pd.to_numeric(df[col_name], errors='coerce')
            avg_val = series.mean()
            if pd.notna(avg_val):
                worksheet.write_number(avg_row_idx, col_offset + ci, float(avg_val), fmt)
                avgs.append(avg_val)
            else:
                worksheet.write_string(avg_row_idx, col_offset + ci, '-', fmt)
        overall = sum(avgs) / len(avgs) if avgs else None
        if len(cols) > 1:
            val = float(overall) if overall is not None else '-'
            worksheet.merge_range(total_avg_row_idx, col_offset, total_avg_row_idx,
                                  col_offset + len(cols) - 1, val, fmt)
        elif len(cols) == 1:
            if overall is not None:
                worksheet.write_number(total_avg_row_idx, col_offset, float(overall), fmt)
            else:
                worksheet.write_string(total_avg_row_idx, col_offset, '-', fmt)

    _write_section_avgs(generic_df, gen_sensor_cols, vel_start, 'vel')
    if n_temp > 0 and not secondary_df.empty and temp_start is not None:
        _write_section_avgs(secondary_df, sec_sensor_cols, temp_start, 'temp')
