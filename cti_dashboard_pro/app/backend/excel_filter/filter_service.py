import os
from io import BytesIO
from datetime import datetime
import pandas as pd

from .readers import _detect_excel_engine, _read_excel_with_time_header, extract_supported_files, SUPPORTED_EXTENSIONS
from .cleaners import _parse_user_time, _parse_times, normalize_column_names
from .report_formatter import _style_sheet, _create_report_layout

def generate_filtered_workbook(file_items, start_time_str, end_time_str):
    if not file_items:
        raise ValueError('Please upload at least one Excel, CSV or ZIP file.')

    start_time = _parse_user_time(start_time_str)
    end_time = _parse_user_time(end_time_str)
    apply_time_filter = (start_time is not None) and (end_time is not None)

    if apply_time_filter and start_time > end_time:
        raise ValueError('Start time must be earlier than or equal to end time.')

    filtered_dataframes = []
    global_min_time = None
    global_max_time = None

    # We now support ZIP files, so we extract all valid files from file_items
    processed_files = []
    for file_name, file_bytes in file_items:
        for ext_name, ext_bytes in extract_supported_files(file_name, file_bytes):
            processed_files.append((ext_name, ext_bytes))

    if not processed_files:
         raise ValueError('No valid .xlsx, .xls, or .csv files found in the uploaded data (or within the ZIP archive).')

    for file_name, file_bytes in processed_files:
        try:
            engine = _detect_excel_engine(file_name)
            df, time_col = _read_excel_with_time_header(file_bytes, engine=engine)
            if df is None:
                continue

            # Apply holistic schema normalizer to fix spacing, capitalization, and formatting inconsistencies
            df.columns = normalize_column_names(df.columns)
            
            # Re-detect time_col after normalization since its name might have changed (e.g. 'Time ' -> 'Time')
            time_col = next((c for c in df.columns if c == 'Time'), None)

            # OL / overrange value cleanup
            OL_THRESHOLD = 1e15
            num_cols = df.select_dtypes(include='number').columns
            df[num_cols] = df[num_cols].where(df[num_cols].abs() < OL_THRESHOLD, other=float('nan'))
            
            for _col in df.select_dtypes(include='object').columns:
                try:
                    _ns = pd.to_numeric(df[_col], errors='coerce')
                    _mask = _ns.abs() >= OL_THRESHOLD
                    if _mask.any():
                        df[_col] = df[_col].astype(object)
                        df.loc[_mask, _col] = float('nan')
                except Exception:
                    pass

            has_date_col = any('date' in str(c).lower() for c in df.columns)
            if time_col and not has_date_col:
                dt_series = pd.to_datetime(df[time_col], errors='coerce')
                if dt_series.notna().any():
                    insert_pos = df.columns.get_loc(time_col) + 1
                    df.insert(insert_pos,     'Date', dt_series.dt.strftime('%d-%m-%Y'))
                    df.insert(insert_pos + 1, 'Time', dt_series.dt.strftime('%H:%M:%S'))
                    time_col = 'Time'

            if apply_time_filter and time_col:
                parsed_times = _parse_times(df[time_col])
                
                valid_times = parsed_times.dropna()
                if not valid_times.empty:
                    f_min = valid_times.min()
                    f_max = valid_times.max()
                    if global_min_time is None or f_min < global_min_time:
                        global_min_time = f_min
                    if global_max_time is None or f_max > global_max_time:
                        global_max_time = f_max

                mask = (parsed_times >= start_time) & (parsed_times <= end_time)
                filtered_df = df[mask.fillna(False)].copy()
            else:
                filtered_df = df.copy()

            if len(filtered_df) == 0:
                continue

            filtered_df.insert(0, 'Source File', file_name)
            filtered_dataframes.append(filtered_df)
        except Exception:
            continue

    if not filtered_dataframes:
        if apply_time_filter:
            if global_min_time and global_max_time:
                min_str = global_min_time.strftime('%I:%M %p').lstrip('0')
                max_str = global_max_time.strftime('%I:%M %p').lstrip('0')
                raise ValueError(f"No rows match the filter ({start_time_str} to {end_time_str}). The uploaded data ranges from {min_str} to {max_str}.")
            else:
                raise ValueError('No rows matched the selected time range in uploaded files.')
        else:
            raise ValueError('No valid data found in the uploaded/selected files.')

    master_df = pd.concat(filtered_dataframes, ignore_index=True)
    master_df.dropna(axis=1, how='all', inplace=True)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        master_df.to_excel(writer, sheet_name='Filtered Data', index=False)
        _style_sheet(writer, 'Filtered Data', master_df)
        
        date_col = next((c for c in master_df.columns if 'date' in str(c).lower()), None)
        if date_col:
            dt_series = pd.to_datetime(master_df[date_col], dayfirst=True, errors='coerce')
            unique_dt_list = dt_series.dropna().dt.normalize().unique()
            unique_dt_list = sorted(unique_dt_list)
            
            if len(unique_dt_list) == 1:
                d_str = unique_dt_list[0].strftime('%d-%m-%Y')
                _create_report_layout(writer, master_df, d_str)
            elif len(unique_dt_list) > 1:
                for dt_val in unique_dt_list:
                    d_str = dt_val.strftime('%d-%m-%Y')
                    mask = dt_series.dt.strftime('%d-%m-%Y') == d_str
                    date_df = master_df[mask].copy()
                    _create_report_layout(writer, date_df, f'{d_str}')
            else:
                _create_report_layout(writer, master_df, 'Consolidated')
        else:
            _create_report_layout(writer, master_df, 'Consolidated')

    if apply_time_filter:
        safe_start = start_time.strftime('%H%M')
        safe_end = end_time.strftime('%H%M')
        file_name = f'Master_Filtered_{safe_start}_to_{safe_end}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    else:
        file_name = f'Master_All_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return file_name, buffer.getvalue()


def generate_filtered_workbook_from_directory(input_dir, start_time_str, end_time_str):
    if not input_dir:
        raise ValueError('Source folder path is required.')
    if not os.path.isdir(input_dir):
        raise ValueError('Source folder path does not exist.')

    file_items = []
    # Include .zip files for local directory scanning too!
    LOCAL_EXTS = SUPPORTED_EXTENSIONS + ('.zip',)
    
    for name in os.listdir(input_dir):
        if name.startswith('~'):
            continue
        if not name.lower().endswith(LOCAL_EXTS):
            continue
        file_path = os.path.join(input_dir, name)
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                file_items.append((name, f.read()))

    if not file_items:
        raise ValueError('No valid .xlsx, .xls, .csv, or .zip files found in the source folder.')

    return generate_filtered_workbook(file_items, start_time_str, end_time_str)
