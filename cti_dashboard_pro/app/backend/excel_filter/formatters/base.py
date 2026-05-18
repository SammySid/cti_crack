import pandas as pd

def _style_sheet(writer, sheet_name, df):
    workbook  = writer.book
    worksheet = writer.sheets[sheet_name]

    # ── Base formats ─────────────────────────────────────────────────────────
    header_fmt = workbook.add_format({
        'bold': True,
        'font_color': '#0F172A',
        'bg_color': '#DBEAFE',
        'border': 1,
        'border_color': '#BFDBFE',
        'align': 'center',
        'valign': 'vcenter',
    })
    data_fmt = workbook.add_format({
        'border': 1,
        'border_color': '#E2E8F0',
    })

    # ── Average-row formats ───────────────────────────────────────────────────
    avg_lbl_fmt = workbook.add_format({
        'bold': True,
        'font_color': '#FFFFFF',
        'bg_color': '#1E3A8A',
        'border': 1,
        'border_color': '#1E3A8A',
        'align': 'right',
        'valign': 'vcenter',
    })
    avg_num_fmt = workbook.add_format({
        'bold': True,
        'font_color': '#FFFFFF',
        'bg_color': '#1D4ED8',
        'border': 1,
        'border_color': '#1E3A8A',
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '0.0000',
    })
    avg_nil_fmt = workbook.add_format({
        'font_color': '#93C5FD',
        'bg_color': '#1E3A8A',
        'border': 1,
        'border_color': '#1E3A8A',
        'align': 'center',
        'valign': 'vcenter',
    })

    worksheet.freeze_panes(1, 0)
    worksheet.set_zoom(115)

    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(0, col_idx, col_name, header_fmt)
        max_len = max(
            len(str(col_name)),
            df[col_name].map(lambda x: len(str(x))).max() if not df.empty else 0
        )
        worksheet.set_column(col_idx, col_idx, min(max(max_len + 2, 12), 35), data_fmt)

    if len(df.columns) > 0 and len(df.index) > 0:
        worksheet.autofilter(0, 0, len(df.index), len(df.columns) - 1)

    # ── Average row ──────────────────────────────────────────────────────────
    _META_KEYWORDS = {'source', 'file', 'date', 'time', 'scan', 'number',
                      'sweep', 'address', 'model', 'serial', 'firmware'}

    avg_row_idx = len(df) + 1

    for col_idx, col_name in enumerate(df.columns):
        col_lower = str(col_name).strip().lower()
        is_meta   = any(kw in col_lower for kw in _META_KEYWORDS)

        if col_idx == 0:
            worksheet.write_string(avg_row_idx, col_idx, 'COLUMN AVERAGE', avg_lbl_fmt)
            continue

        if not is_meta:
            num_series = pd.to_numeric(df[col_name], errors='coerce')
            valid_frac = num_series.notna().sum() / max(len(df), 1)
            if valid_frac >= 0.5:
                avg_val = num_series.mean()
                if pd.notna(avg_val):
                    worksheet.write_number(avg_row_idx, col_idx, float(avg_val), avg_num_fmt)
                    continue

        worksheet.write_string(avg_row_idx, col_idx, '—', avg_nil_fmt)

    worksheet.set_row(avg_row_idx, 18)
