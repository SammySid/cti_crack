import os
import zipfile
from io import BytesIO
import pandas as pd

SUPPORTED_EXTENSIONS = ('.xlsx', '.xls', '.csv')

def _detect_excel_engine(file_name):
    """Return the pandas read_excel engine to use based on the file extension."""
    ext = os.path.splitext(file_name)[1].lower()
    if ext == '.xls':
        return 'xlrd'
    if ext == '.csv':
        return 'csv'
    return None

def _read_excel_bytes(file_bytes, engine=None, **kwargs):
    """Read excel or csv bytes into a DataFrame, trying the given engine first."""
    if engine == 'csv':
        try:
            return pd.read_csv(BytesIO(file_bytes), **kwargs)
        except Exception:
            return pd.read_csv(BytesIO(file_bytes), encoding='iso-8859-1', **kwargs)
            
    if engine:
        kwargs['engine'] = engine
    return pd.read_excel(BytesIO(file_bytes), **kwargs)

def _find_header_row(preview_df):
    for idx, row in preview_df.head(100).iterrows():
        non_empty = [v for v in row.values
                     if str(v).strip().lower() not in ('', 'nan', 'nat', 'none')]
        if len(non_empty) < 3:
            continue
        for cell in row.values:
            cell_str = str(cell).strip().lower()
            if 'time' in cell_str or 'date' in cell_str:
                return idx
    return None

def _get_time_column(df):
    for col in df.columns:
        if str(col).strip().lower() == 'time':
            return col
    for col in df.columns:
        if 'time' in str(col).strip().lower():
            return col
    return None

def _read_excel_with_time_header(file_bytes, engine=None):
    first_pass = _read_excel_bytes(file_bytes, engine=engine)
    time_col = _get_time_column(first_pass)
    if time_col:
        return first_pass, time_col

    preview = _read_excel_bytes(file_bytes, engine=engine, header=None, nrows=100)
    header_idx = _find_header_row(preview)
    if header_idx is None:
        for col in first_pass.columns:
            if pd.api.types.is_datetime64_any_dtype(first_pass[col]):
                return first_pass, col
        return first_pass, None

    adjusted = _read_excel_bytes(file_bytes, engine=engine, header=header_idx)
    time_col = _get_time_column(adjusted)
    if time_col:
        return adjusted, time_col
    for col in adjusted.columns:
        if pd.api.types.is_datetime64_any_dtype(adjusted[col]):
            return adjusted, col
    return adjusted, None

def extract_supported_files(file_name, file_bytes):
    """
    Yields (file_name, file_bytes) for valid files.
    If the file is a ZIP, extracts it in memory and yields its contents.
    """
    ext = os.path.splitext(file_name)[1].lower()
    if ext == '.zip':
        try:
            with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
                for zinfo in zf.infolist():
                    if zinfo.is_dir() or zinfo.filename.startswith('__MACOSX'):
                        continue
                    if zinfo.filename.lower().endswith(SUPPORTED_EXTENSIONS):
                        yield (os.path.basename(zinfo.filename), zf.read(zinfo))
        except zipfile.BadZipFile:
            pass # Invalid zip, just skip
    elif ext in SUPPORTED_EXTENSIONS:
        yield (file_name, file_bytes)
