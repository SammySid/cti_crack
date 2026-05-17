import re
from typing import List, Any
import pandas as pd
from dateutil import parser

def normalize_column_names(columns):
    """
    Holistically standardizes column names to prevent Pandas concat mismatch issues.
    Fixes trailing spaces, case-sensitivity (Time vs TIME), and normalizes sensor names.
    """
    new_cols = []
    for c in columns:
        c_str = str(c).strip()
        c_lower = c_str.lower()
        
        # Force strict exact matching for core columns
        if 'time' in c_lower and 'stamp' not in c_lower and 'comment' not in c_lower:
            new_cols.append('Time')
        elif 'date' == c_lower:
            new_cols.append('Date')
        else:
            # Fix channels (e.g., 'ch 1', 'CH1 ', 'ch1' -> 'CH1')
            c_str = re.sub(r'(?i)^ch\s*(\d+)$', r'CH\1', c_str)
            # Collapse multiple spaces into one
            c_str = re.sub(r'\s+', ' ', c_str)
            new_cols.append(c_str)
            
    return new_cols

def _parse_user_time(time_str):
    """Parse a user-supplied time string. Returns None if the string is empty (meaning 'no filter')."""
    value = str(time_str or '').strip().lower().replace('.', ':')
    if not value:
        return None

    if re.match(r'^\d{1,2}(:00)?$', value):
        hour = int(value.split(':')[0])
        if 1 <= hour <= 7:
            value = f'{hour + 12}:00'
        else:
            value = f'{hour}:00'

    return parser.parse(value).time()

def _parse_times(series):
    parsed = pd.to_datetime(series, format='%H:%M:%S', errors='coerce').dt.time
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(series.loc[missing].astype(str), errors='coerce').dt.time
    return parsed

def _merge_sensor_dfs(dfs, date_col, time_col):
    if not dfs:
        return pd.DataFrame()

    working: List[Any] = []
    for df in dfs:
        copy_df = df.copy()
        dt_str = copy_df[date_col].astype(str) + ' ' + copy_df[time_col].astype(str)
        merge_key = pd.to_datetime(dt_str, dayfirst=True, errors='coerce').dt.floor('min')
        copy_df['_merge_key'] = merge_key.astype(object)
        
        fallback = copy_df[date_col].map(lambda x: str(x).strip()) + '_' + copy_df[time_col].map(lambda x: str(x)[:5])
        copy_df.loc[copy_df['_merge_key'].isna(), '_merge_key'] = fallback.loc[copy_df['_merge_key'].isna()]
        
        # Remove empty rows and drop duplicates on the merge key to prevent Cartesian explosion
        copy_df = copy_df[copy_df['_merge_key'] != 'nan_nan'].copy()
        copy_df.drop_duplicates(subset=['_merge_key'], keep='last', inplace=True)
        
        working.append(copy_df)

    merged = working[0]
    for df in working[1:]:
        merged = pd.merge(merged, df, on='_merge_key', how='outer', suffixes=('', '_y'))
        merged[date_col] = merged[date_col].combine_first(merged[date_col + '_y'])
        merged[time_col] = merged[time_col].combine_first(merged[time_col + '_y'])
        merged.drop(columns=[date_col + '_y', time_col + '_y'], inplace=True)

    merged.sort_values(by='_merge_key', inplace=True)
    merged.drop(columns=['_merge_key'], inplace=True)
    merged.reset_index(drop=True, inplace=True)
    return merged
