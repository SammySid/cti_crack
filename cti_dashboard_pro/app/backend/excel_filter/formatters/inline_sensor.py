import re
import pandas as pd

def _create_inline_sensor_report(
    writer, master_df, sheet_name,
    date_col, time_col,
    cwt_cols, hwt_cols, dbt_cols, wbt_cols
):
    workbook        = writer.book
    safe_name       = sheet_name[:31]
    worksheet       = workbook.add_worksheet(safe_name)

    title_fmt       = workbook.add_format({'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    cwt_hdr_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BDD7EE'})
    hwt_hdr_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FCE4D6'})
    dbt_hdr_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#EDEDED'})
    wbt_hdr_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF2CC'})
    dt_hdr_fmt      = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF59D'})
    sensor_hdr_fmt  = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF59D'})
    data_num_fmt    = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.0000'})
    data_str_fmt    = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    avg_lbl_fmt     = workbook.add_format({'bold': True, 'align': 'right',  'valign': 'vcenter', 'border': 1, 'bg_color': '#D9D9D9'})
    avg_cwt_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BDD7EE', 'num_format': '0.0000'})
    avg_hwt_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FCE4D6', 'num_format': '0.0000'})
    avg_dbt_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#EDEDED', 'num_format': '0.0000'})
    avg_wbt_fmt     = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF2CC', 'num_format': '0.0000'})

    fmt_map = {
        'cwt': (cwt_hdr_fmt, avg_cwt_fmt, 'Cold Water Temp. (CWT)'),
        'hwt': (hwt_hdr_fmt, avg_hwt_fmt, 'Hot Water Temp. (HWT)'),
        'dbt': (dbt_hdr_fmt, avg_dbt_fmt, 'Dry Bulb Temp. (DBT)'),
        'wbt': (wbt_hdr_fmt, avg_wbt_fmt, 'Wet Bulb Temp. (WBT)'),
    }

    sections = [
        ('cwt', cwt_cols),
        ('hwt', hwt_cols),
        ('dbt', dbt_cols),
        ('wbt', wbt_cols),
    ]
    sensor_col_order = [c for _, cols in sections for c in cols]
    total_cols = 2 + len(sensor_col_order)

    worksheet.merge_range(0, 0, 0, total_cols - 1, 'Performance Test Consolidated Report', title_fmt)

    worksheet.write(1, 0, 'Date', dt_hdr_fmt)
    worksheet.write(1, 1, 'Time', dt_hdr_fmt)
    col_ptr = 2
    for tag, cols in sections:
        if not cols:
            continue
        hdr_fmt, _, label = fmt_map[tag]
        if len(cols) > 1:
            worksheet.merge_range(1, col_ptr, 1, col_ptr + len(cols) - 1, label, hdr_fmt)
        else:
            worksheet.write(1, col_ptr, label, hdr_fmt)
        col_ptr += len(cols)

    worksheet.merge_range(2, 0, 2, 1, 'Sensor No.', sensor_hdr_fmt)
    col_ptr = 2
    for tag, cols in sections:
        _, _, _ = fmt_map[tag]
        hdr_fmt = fmt_map[tag][0]
        for col_name in cols:
            m = re.match(r'(\d+)', str(col_name).strip())
            if m:
                label = m.group(1)
            else:
                label = str(col_name)[:12]
            if re.match(r'^\d+\.0$', label):
                label = label[:-2]
            worksheet.write_string(2, col_ptr, label, sensor_hdr_fmt)
            col_ptr += 1

    data = master_df[[date_col, time_col] + sensor_col_order].copy()
    data[time_col] = data[time_col].map(lambda x: str(x).split('.')[0] if pd.notna(x) else x)
    if pd.api.types.is_datetime64_any_dtype(data[date_col]):
        data[date_col] = data[date_col].dt.strftime('%d-%m-%Y')

    for r_idx in range(len(data)):
        target_row = r_idx + 3
        row = data.iloc[r_idx]
        dv = row[date_col]
        worksheet.write_string(target_row, 0,
            '' if (pd.isna(dv) or str(dv).lower() in ('nan', 'nat')) else str(dv), data_str_fmt)
        tv = row[time_col]
        worksheet.write_string(target_row, 1,
            '' if (pd.isna(tv) or str(tv).lower() in ('nan', 'nat')) else str(tv), data_str_fmt)
        for ci, col_name in enumerate(sensor_col_order):
            val = row[col_name]
            if pd.isna(val) or str(val).lower() in ('nan', 'nat'):
                worksheet.write_string(target_row, 2 + ci, '', data_str_fmt)
            else:
                try:
                    worksheet.write_number(target_row, 2 + ci, float(val), data_num_fmt)
                except (TypeError, ValueError):
                    worksheet.write_string(target_row, 2 + ci, str(val), data_str_fmt)

    worksheet.set_column(0, 1, 14)
    worksheet.set_column(2, total_cols - 1, 10)

    n_data = len(data)
    avg_row       = n_data + 4
    tot_avg_row   = n_data + 5

    worksheet.write(avg_row,     0, '', avg_lbl_fmt)
    worksheet.write(avg_row,     1, 'Average',       avg_lbl_fmt)
    worksheet.write(tot_avg_row, 0, '', avg_lbl_fmt)
    worksheet.write(tot_avg_row, 1, 'Total Average', avg_lbl_fmt)

    col_ptr = 2
    for tag, cols in sections:
        if not cols:
            continue
        _, avg_fmt, _ = fmt_map[tag]
        section_avgs = []
        for col_name in cols:
            series = pd.to_numeric(master_df[col_name], errors='coerce')
            avg_val = series.mean()
            if pd.notna(avg_val):
                worksheet.write_number(avg_row, col_ptr, float(avg_val), avg_fmt)
                section_avgs.append(avg_val)
            else:
                worksheet.write_string(avg_row, col_ptr, '-', avg_fmt)
            col_ptr += 1
        total = sum(section_avgs) / len(section_avgs) if section_avgs else None
        sec_start = col_ptr - len(cols)
        sec_end   = col_ptr - 1
        if len(cols) > 1:
            val = float(total) if total is not None else '-'
            worksheet.merge_range(tot_avg_row, sec_start, tot_avg_row, sec_end, val, avg_fmt)
        elif len(cols) == 1:
            if total is not None:
                worksheet.write_number(tot_avg_row, sec_start, float(total), avg_fmt)
            else:
                worksheet.write_string(tot_avg_row, sec_start, '-', avg_fmt)
