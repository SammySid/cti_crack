import math
import struct
import os

P_SEA_LEVEL_PSI  = 14.696
CHEBYSHEV_POINTS = [0.9, 0.6, 0.4, 0.1]
CP_DRY_AIR       = 0.24
H_FG             = 1061.0
CP_STEAM         = 0.444

T_MID    = 124.997
T_HALF   = 74.997
N_COEFF  = 19
ALT_STEP = 10
N_ALT    = 201

def alt_to_psi(alt_m):
    if alt_m == 0: return P_SEA_LEVEL_PSI
    x = (alt_m / 0.3048) / 10000.0
    return ((0.547462 * x - 7.67923) * x + 29.9309) * 0.491154 / (0.10803 * x + 1.0)

P_LEVELS = [alt_to_psi(i * ALT_STEP) for i in range(N_ALT)]

_coeffs = None

def init_merkel_engine(bin_path):
    global _coeffs
    try:
        with open(bin_path, 'rb') as f:
            buf = f.read()
            count = len(buf) // 8
            _coeffs = struct.unpack(f"{count}d", buf)
    except Exception as e:
        _coeffs = None
        print(f"Merkel coefficient table unavailable ({bin_path}). Using fallback: {e}")

def _cheb_eval(offset, x):
    x2 = 2 * x
    b1 = 0.0
    b2 = 0.0
    for k in range(N_COEFF - 1, 0, -1):
        b0 = x2 * b1 - b2 + _coeffs[offset + k]
        b2 = b1
        b1 = b0
    return x * b1 - b2 + _coeffs[offset]

def fpws_from_poly(t_f, p_psi):
    if not _coeffs or len(_coeffs) < (N_ALT * N_COEFF):
        t_c = (t_f - 32) / 1.8
        pws_kpa = 0.61078 * math.exp((17.2694 * t_c) / (t_c + 237.29))
        pws_psi = pws_kpa * 0.14503773773
        return min(pws_psi * 1.0005, p_psi * 0.98)

    x = (t_f - T_MID) / T_HALF

    lo = 0
    if p_psi >= P_LEVELS[0]:
        lo = 0
    elif p_psi <= P_LEVELS[N_ALT - 1]:
        lo = N_ALT - 2
    else:
        for k in range(N_ALT - 1):
            if p_psi >= P_LEVELS[k + 1]:
                lo = k
                break
    hi = lo + 1

    frac = (p_psi - P_LEVELS[lo]) / (P_LEVELS[hi] - P_LEVELS[lo])
    ln_lo = _cheb_eval(lo * N_COEFF, x)
    ln_hi = _cheb_eval(hi * N_COEFF, x)
    return math.exp(ln_lo + frac * (ln_hi - ln_lo))

def h_sat_imperial(p_psi, t_f):
    fpws = fpws_from_poly(t_f, p_psi)
    denom = p_psi - fpws
    if denom <= 0: return 999.0
    ws = 0.62198 * fpws / denom
    return CP_DRY_AIR * t_f + ws * (H_FG + CP_STEAM * t_f)

def merkel_kavl(hwt, cwt, wbt, lg, alt_m=0.0):
    if hwt <= cwt:
        return {"kavl": 0, "range": 0, "approach": 0, "P_kPa": 0, "valid": False,
                "error": "HWT must be greater than CWT"}
    if cwt <= wbt:
        return {"kavl": 0, "range": hwt - cwt, "approach": 0, "P_kPa": 0, "valid": False,
                "error": "CWT must be greater than WBT"}
    if lg <= 0:
        return {"kavl": 0, "range": hwt - cwt, "approach": cwt - wbt, "P_kPa": 0,
                "valid": False, "error": "L/G must be positive"}

    wbt_f = wbt * 1.8 + 32
    range_f = (hwt - cwt) * 1.8
    approach_f = (cwt - wbt) * 1.8
    cwt_f = wbt_f + approach_f

    if cwt_f + range_f >= 212.0:
        return {"kavl": 999.0, "range": hwt - cwt, "approach": cwt - wbt,
                "P_kPa": 101.325, "valid": False, "error": "HWT exceeds boiling point"}

    p_psi = alt_to_psi(alt_m)
    p_kpa = p_psi / 0.14503773773

    h_in = h_sat_imperial(p_psi, wbt_f)
    h_out = range_f * lg + h_in

    sum_val = 0
    for i in range(4):
        cheb = CHEBYSHEV_POINTS[i]
        h_sat_i = h_sat_imperial(p_psi, range_f * cheb + cwt_f)
        h_air_i = (h_out - h_in) * cheb + h_in
        df = h_sat_i - h_air_i
        if df <= 0:
            return {"kavl": 999.0, "range": hwt - cwt, "approach": cwt - wbt,
                    "P_kPa": round(p_kpa, 3), "valid": False,
                    "error": "Insufficient driving force (h_sat <= h_air)"}
        sum_val += 0.25 / df

    return {
        "kavl": round(sum_val * range_f, 5),
        "range": round(hwt - cwt, 2),
        "approach": round(cwt - wbt, 2),
        "P_kPa": round(p_kpa, 3),
        "valid": True,
        "error": None
    }
