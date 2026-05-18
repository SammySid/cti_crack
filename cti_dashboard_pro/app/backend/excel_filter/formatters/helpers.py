import os
import re

def _extract_generic_sensor_id(file_name):
    """Best-effort short label from a filename with no CWT/HWT/DBT/WBT tag.
    Produces labels like 'Q1_A', 'Q2_B', 'Cell_C', or a fallback number.
    """
    stem = os.path.splitext(file_name)[0]
    # Pattern: "2nd quadrant reading Cell B …" → "Q2_B"
    quad = re.search(r'(\d+)\s*(?:st|nd|rd|th)\s+quadrant', stem, re.IGNORECASE)
    cell = re.search(r'[Cc]ell\s+([A-Za-z0-9]+)', stem)
    if quad and cell:
        return f"Q{quad.group(1)}_{cell.group(1)}"
    if cell:
        return f"Cell_{cell.group(1)}"
    # Fall back: 2+-digit number block
    matches = re.findall(r'\d{2,}', stem)
    if matches:
        return max(matches, key=lambda x: (len(x), int(x)))
    # Last resort: clean up the stem
    clean = re.sub(r'\s+', '_', stem.strip())
    return clean[:18] if len(clean) > 18 else clean
