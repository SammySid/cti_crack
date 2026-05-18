import pandas as pd
from typing import Dict, Any
from .formats import get_format_dict, get_avg_val_fmts

def _render_cwt_hwt_layout(
    writer, worksheet, master_df,
    water_df, air_df,
    cwt_cols, hwt_cols, dbt_cols, wbt_cols,
    date_col, time_col
):
    workbook = writer.book
    fmts = get_format_dict(workbook)
    avg_val_fmts = get_avg_val_fmts(workbook)

    max_rows = max(len(water_df), len(air_df))
    final_df_dict: Dict[str, Any] = {}
    if not water_df.empty:
        final_df_dict['Date_W'] = water_df[date_col].tolist() + [None] * (max_rows - len(water_df))
        final_df_dict['Time_W'] = water_df[time_col].tolist() + [None] * (max_rows - len(water_df))
        for col in cwt_cols:
            final_df_dict[col] = water_df[col].tolist() + [None] * (max_rows - len(water_df))
        for col in hwt_cols:
            final_df_dict[col] = water_df[col].tolist() + [None] * (max_rows - len(water_df))
    if not air_df.empty:
        final_df_dict['Date_A'] = air_df[date_col].tolist() + [None] * (max_rows - len(air_df))
        final_df_dict['Time_A'] = air_df[time_col].tolist() + [None] * (max_rows - len(air_df))
        for col in dbt_cols:
            final_df_dict[col] = air_df[col].tolist() + [None] * (max_rows - len(air_df))
        for col in wbt_cols:
            final_df_dict[col] = air_df[col].tolist() + [None] * (max_rows - len(air_df))

    final_df = pd.DataFrame(final_df_dict)

    total_cols = len(final_df.columns)
    if total_cols > 0:
        worksheet.merge_range(0, 0, 0, total_cols - 1, 'Performance Test Consolidated Report', fmts['title_fmt'])

    col_ptr: int = 0
    start_air: int = 0
    if not water_df.empty:
        worksheet.write(1, col_ptr, 'Date', fmts['date_time_fmt'])
        worksheet.write(1, col_ptr + 1, 'Time', fmts['date_time_fmt'])
        worksheet.merge_range(2, col_ptr, 2, col_ptr + 1, 'Sensor No.', fmts['sensor_fmt'])
        col_ptr += 2
        if cwt_cols:
            if len(cwt_cols) > 1:
                worksheet.merge_range(1, col_ptr, 1, col_ptr + len(cwt_cols) - 1, 'Cold Water Temp. (CWT)', fmts['cwt_header_fmt'])
            else:
                worksheet.write(1, col_ptr, 'Cold Water Temp. (CWT)', fmts['cwt_header_fmt'])
            for col in cwt_cols:
                worksheet.write(2, col_ptr, col, fmts['sensor_fmt'])
                col_ptr += 1
        if hwt_cols:
            if len(hwt_cols) > 1:
                worksheet.merge_range(1, col_ptr, 1, col_ptr + len(hwt_cols) - 1, 'Hot Water Temp. (HWT)', fmts['hwt_header_fmt'])
            else:
                worksheet.write(1, col_ptr, 'Hot Water Temp. (HWT)', fmts['hwt_header_fmt'])
            for col in hwt_cols:
                worksheet.write(2, col_ptr, col, fmts['hwt_header_fmt'])
                col_ptr += 1

    if not air_df.empty:
        start_air = int(col_ptr) if not water_df.empty else 0
        worksheet.write(1, start_air, 'Date', fmts['date_time_fmt'])
        worksheet.write(1, start_air + 1, 'Time', fmts['date_time_fmt'])
        worksheet.merge_range(2, start_air, 2, start_air + 1, 'Sensor No.', fmts['sensor_fmt'])
        col_ptr = start_air + 2
        if dbt_cols:
            if len(dbt_cols) > 1:
                worksheet.merge_range(1, col_ptr, 1, col_ptr + len(dbt_cols) - 1, 'Dry Bulb Temp. (DBT)', fmts['dbt_header_fmt'])
            else:
                worksheet.write(1, col_ptr, 'Dry Bulb Temp. (DBT)', fmts['dbt_header_fmt'])
            for col in dbt_cols:
                worksheet.write(2, col_ptr, col, fmts['dbt_header_fmt'])
                col_ptr += 1
        if wbt_cols:
            if len(wbt_cols) > 1:
                worksheet.merge_range(1, col_ptr, 1, col_ptr + len(wbt_cols) - 1, 'Wet Bulb Temp. (WBT)', fmts['wbt_header_fmt'])
            else:
                worksheet.write(1, col_ptr, 'Wet Bulb Temp. (WBT)', fmts['wbt_header_fmt'])
            for col in wbt_cols:
                worksheet.write(2, col_ptr, col, fmts['wbt_header_fmt'])
                col_ptr += 1

    for r_idx, row in final_df.iterrows():
        for c_idx, value in enumerate(row):
            target_row = r_idx + 3
            if pd.isna(value) or str(value).lower() == 'nan':
                worksheet.write(target_row, c_idx, '', fmts['data_fmt'])
            else:
                try:
                    worksheet.write_number(target_row, c_idx, float(value), fmts['data_fmt'])
                except (TypeError, ValueError):
                    worksheet.write_string(target_row, c_idx, str(value), fmts['data_fmt'])

    worksheet.set_column(0, max(total_cols - 1, 0), 12)

    avg_row_idx = max_rows + 5
    total_avg_row_idx = max_rows + 6

    if not water_df.empty:
        worksheet.write(avg_row_idx, 0, '', fmts['avg_label_fmt'])
        worksheet.write(avg_row_idx, 1, 'Average', fmts['avg_label_fmt'])
        worksheet.write(total_avg_row_idx, 0, '', fmts['avg_label_fmt'])
        worksheet.write(total_avg_row_idx, 1, 'Total Average', fmts['avg_label_fmt'])
    if not air_df.empty:
        worksheet.write(avg_row_idx, start_air, '', fmts['avg_label_fmt'])
        worksheet.write(avg_row_idx, start_air + 1, 'Average', fmts['avg_label_fmt'])
        worksheet.write(total_avg_row_idx, start_air, '', fmts['avg_label_fmt'])
        worksheet.write(total_avg_row_idx, start_air + 1, 'Total Average', fmts['avg_label_fmt'])

    cwt_avgs = []
    hwt_avgs = []
    dbt_avgs = []
    wbt_avgs = []

    for c_idx, col_name in enumerate(final_df.columns):
        if col_name in ['Date_W', 'Time_W', 'Date_A', 'Time_A']:
            continue

        col_series = pd.to_numeric(final_df[col_name], errors='coerce')
        avg_val = col_series.mean()
        fmt = avg_val_fmts['default']

        if col_name in cwt_cols:
            fmt = avg_val_fmts['cwt']
            if pd.notna(avg_val):
                cwt_avgs.append(avg_val)
        elif col_name in hwt_cols:
            fmt = avg_val_fmts['hwt']
            if pd.notna(avg_val):
                hwt_avgs.append(avg_val)
        elif col_name in dbt_cols:
            fmt = avg_val_fmts['dbt']
            if pd.notna(avg_val):
                dbt_avgs.append(avg_val)
        elif col_name in wbt_cols:
            fmt = avg_val_fmts['wbt']
            if pd.notna(avg_val):
                wbt_avgs.append(avg_val)

        if pd.notna(avg_val):
            worksheet.write_number(avg_row_idx, c_idx, float(avg_val), fmt)
        else:
            worksheet.write_string(avg_row_idx, c_idx, '-', fmt)

    def write_total_avg(avgs, cols, start_col_idx, fmt_key):
        if not cols:
            return
        total_avg = (sum(avgs) / len(avgs)) if avgs else None
        fmt = avg_val_fmts[fmt_key]
        end_col_idx = start_col_idx + len(cols) - 1
        if len(cols) > 1:
            if total_avg is not None:
                worksheet.merge_range(total_avg_row_idx, start_col_idx, total_avg_row_idx, end_col_idx, float(total_avg), fmt)
            else:
                worksheet.merge_range(total_avg_row_idx, start_col_idx, total_avg_row_idx, end_col_idx, '-', fmt)
        else:
            if total_avg is not None:
                worksheet.write_number(total_avg_row_idx, start_col_idx, float(total_avg), fmt)
            else:
                worksheet.write_string(total_avg_row_idx, start_col_idx, '-', fmt)

    if not water_df.empty:
        cidx = 2
        write_total_avg(cwt_avgs, cwt_cols, cidx, 'cwt')
        cidx += len(cwt_cols)
        write_total_avg(hwt_avgs, hwt_cols, cidx, 'hwt')
    if not air_df.empty:
        cidx = start_air + 2
        write_total_avg(dbt_avgs, dbt_cols, cidx, 'dbt')
        cidx += len(dbt_cols)
        write_total_avg(wbt_avgs, wbt_cols, cidx, 'wbt')
