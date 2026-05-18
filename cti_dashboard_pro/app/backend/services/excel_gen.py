import json
import os
import shutil
import sys
import xlsxwriter


def sanitize_filename(value):
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(value).strip())
    return safe.strip('_') or 'Thermal_Analysis'


def _validate_payload(payload):
    required_top_level = ('inputs', 'data90', 'data100', 'data110')
    for key in required_top_level:
        if key not in payload:
            raise ValueError(f'Missing required key: {key}')

    inputs = payload.get('inputs')
    if not isinstance(inputs, dict):
        raise ValueError('inputs must be an object')

    for curve_key in ('data90', 'data100', 'data110'):
        curve = payload.get(curve_key)
        if not isinstance(curve, list) or not curve:
            raise ValueError(f'{curve_key} must be a non-empty array')


def generate_excel_from_payload(payload, output_file):
    _validate_payload(payload)

    inputs = payload['inputs']
    project_name = inputs.get('projectName', 'Thermal Analysis')
    client_name = inputs.get('companyName', 'Unknown Client')
    engineer_name = inputs.get('engineerName', 'N/A')
    report_date = inputs.get('date', 'N/A')

    workbook = xlsxwriter.Workbook(output_file)

    brand_fmt = workbook.add_format({
        'bold': True, 'font_size': 16, 'font_color': '#F8FAFC',
        'bg_color': '#0F172A', 'align': 'left', 'valign': 'vcenter'
    })
    meta_label_fmt = workbook.add_format({
        'bold': True, 'font_size': 9, 'font_color': '#475569',
        'bg_color': '#E2E8F0', 'border': 1, 'border_color': '#CBD5E1',
        'align': 'left', 'valign': 'vcenter'
    })
    meta_value_fmt = workbook.add_format({
        'font_size': 10, 'font_color': '#0F172A',
        'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#CBD5E1',
        'align': 'left', 'valign': 'vcenter', 'shrink': True
    })
    section_title_fmt = workbook.add_format({
        'bold': True, 'font_size': 11, 'font_color': '#0F172A',
        'bg_color': '#DBEAFE', 'border': 1, 'border_color': '#BFDBFE',
        'align': 'left', 'valign': 'vcenter'
    })
    helper_header_fmt = workbook.add_format({
        'bold': True, 'font_size': 9, 'font_color': '#1E293B',
        'bg_color': '#E2E8F0', 'border': 1, 'border_color': '#CBD5E1',
        'text_wrap': True, 'align': 'center', 'valign': 'vcenter'
    })
    helper_number_fmt = workbook.add_format({
        'num_format': '0.00', 'font_color': '#334155',
        'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0'
    })
    helper_percent_fmt = workbook.add_format({
        'num_format': '0.00%', 'font_color': '#334155',
        'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0'
    })
    editable_fmt = workbook.add_format({
        'num_format': '0.00', 'bg_color': '#FFF7ED',
        'border': 1, 'border_color': '#FDBA74'
    })
    wbt_fmt = workbook.add_format({
        'num_format': '0.00', 'bg_color': '#F8FAFC',
        'border': 1, 'border_color': '#E2E8F0'
    })
    note_fmt = workbook.add_format({'italic': True, 'font_color': '#475569', 'font_size': 9})
    kpi_label_fmt = workbook.add_format({
        'bold': True, 'font_size': 9, 'font_color': '#334155',
        'bg_color': '#EEF2FF', 'border': 1, 'border_color': '#C7D2FE'
    })
    kpi_value_fmt = workbook.add_format({
        'bold': True, 'font_size': 11, 'font_color': '#0F172A',
        'bg_color': '#FFFFFF', 'border': 1, 'border_color': '#C7D2FE',
        'num_format': '0.00'
    })

    def add_flow_sheet(sheet_name, data, flow_label):
        sheet = workbook.add_worksheet(sheet_name)
        helper_start_col = 13  # Column N
        table_start_row = 9
        data_start_row = table_start_row + 1

        sheet.hide_gridlines(2)
        sheet.set_zoom(115)
        sheet.set_row(0, 28)
        sheet.set_row(2, 22)
        sheet.set_row(3, 22)
        sheet.set_row(4, 22)
        sheet.set_row(8, 24)
        sheet.set_column('A:A', 16)
        sheet.set_column('B:B', 28)
        sheet.set_column('C:C', 14)
        sheet.set_column('D:D', 26)
        sheet.set_column('E:E', 2)
        sheet.set_column('F:M', 14)
        sheet.set_column('N:V', 15, None, {'hidden': True})

        sheet.merge_range('A1:V1', 'SS COOLING TOWER LTD | THERMAL PERFORMANCE REPORT', brand_fmt)
        sheet.write('A3', 'Project', meta_label_fmt)
        sheet.write('B3', project_name, meta_value_fmt)
        sheet.write('C3', 'Client', meta_label_fmt)
        sheet.write('D3', client_name, meta_value_fmt)
        sheet.write('A4', 'Lead Engineer', meta_label_fmt)
        sheet.write('B4', engineer_name, meta_value_fmt)
        sheet.write('C4', 'Report Date', meta_label_fmt)
        sheet.write('D4', report_date, meta_value_fmt)
        sheet.write('A5', 'Analysis Mode', meta_label_fmt)
        sheet.write('B5', flow_label, meta_value_fmt)
        sheet.write('C5', 'Data Source', meta_label_fmt)
        sheet.write('D5', 'Dashboard Export API', meta_value_fmt)
        sheet.merge_range('A7:D7', 'Performance Data (Editable CWT in columns B-D)', section_title_fmt)
        sheet.write('A8', 'Tip: helper analytics are available in hidden columns N-V. Unhide if needed.', note_fmt)

        table_columns = [
            {'header': 'Wet Bulb Temp (\u00b0C)'},
            {'header': 'Range 80% CWT (\u00b0C)'},
            {'header': 'Range 100% CWT (\u00b0C)'},
            {'header': 'Range 120% CWT (\u00b0C)'}
        ]

        row = data_start_row
        for point in data:
            excel_row = row + 1
            sheet.write_number(row, 0, float(point.get('wbt', 0) or 0), wbt_fmt)
            sheet.write_number(row, 1, float(point.get('range80', 0) or 0), editable_fmt)
            sheet.write_number(row, 2, float(point.get('range100', 0) or 0), editable_fmt)
            sheet.write_number(row, 3, float(point.get('range120', 0) or 0), editable_fmt)
            sheet.write_formula(row, helper_start_col + 0, f'=B{excel_row}-A{excel_row}', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 1, f'=C{excel_row}-A{excel_row}', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 2, f'=D{excel_row}-A{excel_row}', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 3, f'=C{excel_row}-B{excel_row}', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 4, f'=D{excel_row}-C{excel_row}', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 5, f'=AVERAGE(B{excel_row}:D{excel_row})', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 6, f'=D{excel_row}-B{excel_row}', helper_number_fmt)
            sheet.write_formula(row, helper_start_col + 7, f'=IFERROR((B{excel_row}-C{excel_row})/C{excel_row},0)', helper_percent_fmt)
            sheet.write_formula(row, helper_start_col + 8, f'=IFERROR((D{excel_row}-C{excel_row})/C{excel_row},0)', helper_percent_fmt)
            row += 1

        table_last_row = row - 1
        sheet.add_table(
            table_start_row,
            0,
            table_last_row,
            3,
            {'style': 'Table Style Light 11', 'columns': table_columns}
        )

        helper_headers = [
            'Approach 80% (B-A)',
            'Approach 100% (C-A)',
            'Approach 120% (D-A)',
            'Delta 100-80 (C-B)',
            'Delta 120-100 (D-C)',
            'Average CWT',
            'Span 120-80 (D-B)',
            '%Shift 80 vs 100',
            '%Shift 120 vs 100'
        ]
        for idx, header in enumerate(helper_headers):
            sheet.write(table_start_row, helper_start_col + idx, header, helper_header_fmt)

        data_first_excel_row = data_start_row + 1
        data_last_excel_row = table_last_row + 1
        sheet.merge_range('F25:M25', 'Performance Summary', section_title_fmt)
        sheet.write('F26', 'Avg Approach (100%)', kpi_label_fmt)
        sheet.write_formula('G26', f'=AVERAGE(O{data_first_excel_row}:O{data_last_excel_row})', kpi_value_fmt)
        sheet.write('I26', 'Avg CWT', kpi_label_fmt)
        sheet.write_formula('J26', f'=AVERAGE(S{data_first_excel_row}:S{data_last_excel_row})', kpi_value_fmt)
        sheet.write('L26', 'Max Span (120-80)', kpi_label_fmt)
        sheet.write_formula('M26', f'=MAX(T{data_first_excel_row}:T{data_last_excel_row})', kpi_value_fmt)

        sheet.write('F27', 'Avg Shift 80 vs 100', kpi_label_fmt)
        sheet.write_formula('G27', f'=AVERAGE(U{data_first_excel_row}:U{data_last_excel_row})', helper_percent_fmt)
        sheet.write('I27', 'Avg Shift 120 vs 100', kpi_label_fmt)
        sheet.write_formula('J27', f'=AVERAGE(V{data_first_excel_row}:V{data_last_excel_row})', helper_percent_fmt)
        sheet.write('L27', 'Data Points', kpi_label_fmt)
        sheet.write_formula('M27', f'=ROWS(A{data_first_excel_row}:A{data_last_excel_row})', kpi_value_fmt)

        # Keep layout clean without a pane divider crossing the chart.
        # If needed later, we can re-enable freeze panes below the chart area.

        # Create Chart
        chart = workbook.add_chart({'type': 'line'})
        series_colors = ['#0EA5E9', '#10B981', '#F59E0B']

        # Configure the series
        for i, color in enumerate(series_colors, start=1):
            chart.add_series({
                'name': [sheet_name, table_start_row, i],
                'categories': [sheet_name, data_start_row, 0, table_last_row, 0],
                'values': [sheet_name, data_start_row, i, table_last_row, i],
                'line': {'color': color, 'width': 2.5},
                'marker': {
                    'type': 'circle',
                    'size': 4,
                    'border': {'color': color},
                    'fill': {'color': '#FFFFFF'}
                }
            })

        chart.set_title({
            'name': f'Performance Curve - {flow_label}',
            'name_font': {'size': 11, 'bold': True, 'color': '#0F172A'}
        })
        chart.set_x_axis({
            'name': 'Wet Bulb Temperature (\u00b0C)',
            'name_font': {'size': 9, 'color': '#334155'},
            'num_font': {'size': 8, 'color': '#334155'},
            'line': {'color': '#CBD5E1'},
            'major_gridlines': {'visible': True, 'line': {'color': '#E2E8F0'}}
        })
        chart.set_y_axis({
            'name': 'Cold Water Temperature (\u00b0C)',
            'name_font': {'size': 9, 'color': '#334155'},
            'num_font': {'size': 8, 'color': '#334155'},
            'line': {'color': '#CBD5E1'},
            'major_gridlines': {'visible': True, 'line': {'color': '#E2E8F0'}}
        })
        chart.set_legend({'position': 'top', 'font': {'size': 8, 'color': '#334155'}})
        chart.set_plotarea({'fill': {'color': '#FFFFFF'}, 'border': {'none': True}})
        chart.set_chartarea({'fill': {'color': '#F8FAFC'}, 'border': {'none': True}})
        chart.set_size({'width': 820, 'height': 430})

        # Insert chart beside the data
        sheet.insert_chart('F3', chart, {'x_offset': 8, 'y_offset': 4})

    # Generate Sheets
    add_flow_sheet('Nominal Flow 100%', payload['data100'], 'Nominal (100%)')
    add_flow_sheet('Low Flow 90%', payload['data90'], 'Low (90%)')
    add_flow_sheet('High Flow 110%', payload['data110'], 'High (110%)')

    workbook.close()
    return output_file


def generate_excel(data_file='thermal_data.json', output_dir='reports', move_source_to_reports=True):
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found. Please export from the dashboard first.")
        return None

    with open(data_file, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    project_name = payload.get('inputs', {}).get('projectName', 'Thermal Analysis')
    safe_project_name = sanitize_filename(project_name)
    output_file = os.path.join(output_dir, f'Professional_Report_{safe_project_name}.xlsx')

    generate_excel_from_payload(payload, output_file)

    if move_source_to_reports:
        shutil.move(data_file, os.path.join(output_dir, os.path.basename(data_file)))

    print(f"Success! Professional Excel report created in: {output_dir}")
    if move_source_to_reports:
        print(f"Data source stored in: {output_dir}/{os.path.basename(data_file)}")
    return output_file


if __name__ == "__main__":
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'thermal_data.json'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'reports'
    generate_excel(data_file=data_file, output_dir=output_dir)
