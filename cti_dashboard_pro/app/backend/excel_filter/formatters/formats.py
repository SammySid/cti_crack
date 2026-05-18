def get_format_dict(workbook):
    return {
        'title_fmt':       workbook.add_format({'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter', 'border': 1}),
        'cwt_header_fmt':  workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BDD7EE'}),
        'hwt_header_fmt':  workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FCE4D6'}),
        'dbt_header_fmt':  workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#EDEDED'}),
        'wbt_header_fmt':  workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF2CC'}),
        'vel_header_fmt':  workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BDD7EE'}),
        'temp_header_fmt': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FCE4D6'}),
        'date_time_fmt':   workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF59D'}),
        'sensor_fmt':      workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF59D'}),
        'data_fmt':        workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.00'}),
        'str_data_fmt':    workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
        'avg_label_fmt':   workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bg_color': '#D9D9D9'}),
    }

def get_avg_val_fmts(workbook):
    return {
        'cwt':     workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BDD7EE', 'num_format': '0.00'}),
        'hwt':     workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FCE4D6', 'num_format': '0.00'}),
        'dbt':     workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#EDEDED', 'num_format': '0.00'}),
        'wbt':     workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF2CC', 'num_format': '0.00'}),
        'vel':     workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#BDD7EE', 'num_format': '0.00'}),
        'temp':    workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FCE4D6', 'num_format': '0.00'}),
        'default': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#E2EFDA', 'num_format': '0.00'}),
    }
