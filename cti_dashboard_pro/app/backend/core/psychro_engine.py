import math
import struct
import os

HW_WATER_C8  = -5800.2206
HW_WATER_C9  = -5.516256
HW_WATER_C10 = -0.048640239
HW_WATER_C11 = 4.1764768e-5
HW_WATER_C12 = -1.4452093e-8
HW_WATER_C13 = 6.5459673

HW_ICE_C8 = -5674.5359
HW_ICE_C9 = 6.3925247 - math.log(1000)
HW_ICE_C10 = -0.0096778430
HW_ICE_C11 = 6.2215701e-7
HW_ICE_C12 = 2.0747825e-9
HW_ICE_C13 = -9.484024e-13
HW_ICE_C14 = 4.1635019

DP_WATER = {"C14": 6.54, "C15": 14.526, "C16": 0.7389, "C17": 0.09486, "C18": 0.4569, "n": 0.1984}
DP_ICE = {"C14": 6.09, "C15": 12.608, "C16": 0.4959}

L0 = 2501.0
CpS = 1.805
CpW = 4.186
L_COEFF = 2.381
MW_MA = 0.62198
Ra = 0.287055

F_ALT_T_MIN    = -5
F_ALT_T_STEP   = 1
F_ALT_T_N      = 65
F_ALT_A_STEP   = 500
F_ALT_N_ALT    = 4

_fAlt = None

def init_psychro_engine(bin_path):
    global _fAlt
    try:
        with open(bin_path, 'rb') as f:
            buf = f.read()
            count = len(buf) // 8
            _fAlt = struct.unpack(f"{count}d", buf)
    except Exception as e:
        _fAlt = None
        print(f"Psychro lookup table unavailable ({bin_path}). Using fallback: {e}")

def f_enhance_at_p(t_celsius, p):
    if not _fAlt or len(_fAlt) < (F_ALT_N_ALT * F_ALT_T_N):
        return 1.0

    alt_m = (1.0 - math.pow(p / 101.325, 1.0 / 5.2559)) / 2.25577e-5

    t_float = (t_celsius - F_ALT_T_MIN) / F_ALT_T_STEP
    t_lo = max(0, min(F_ALT_T_N - 2, int(math.floor(t_float))))
    frac_t = max(0.0, min(1.0, t_float - t_lo))

    a_float = alt_m / F_ALT_A_STEP
    a_lo = max(0, min(F_ALT_N_ALT - 2, int(math.floor(a_float))))
    frac_a = max(0.0, min(1.0, a_float - a_lo))

    base_lo = a_lo * F_ALT_T_N
    base_hi = base_lo + F_ALT_T_N
    
    fLo = _fAlt[base_lo + t_lo] + frac_t * (_fAlt[base_lo + t_lo + 1] - _fAlt[base_lo + t_lo])
    fHi = _fAlt[base_hi + t_lo] + frac_t * (_fAlt[base_hi + t_lo + 1] - _fAlt[base_hi + t_lo])
    return fLo + frac_a * (fHi - fLo)

def pws_kpa(t_celsius):
    t_k = t_celsius + 273.15
    if t_k <= 0: return 0.0

    if t_celsius >= 0:
        lnPws = HW_WATER_C8 / t_k + HW_WATER_C9 + HW_WATER_C10 * t_k + \
            HW_WATER_C11 * t_k * t_k + HW_WATER_C12 * math.pow(t_k, 3) + \
            HW_WATER_C13 * math.log(t_k)
    else:
        lnPws = HW_ICE_C8 / t_k + HW_ICE_C9 + HW_ICE_C10 * t_k + \
            HW_ICE_C11 * t_k * t_k + HW_ICE_C12 * math.pow(t_k, 3) + \
            HW_ICE_C13 * math.pow(t_k, 4) + HW_ICE_C14 * math.log(t_k)

    return math.exp(lnPws)

def dpws_dt(t_celsius, pws_val):
    t_k = t_celsius + 273.15
    if t_k <= 0: return 0.0

    if t_celsius >= 0:
        dln = -HW_WATER_C8 / (t_k * t_k) + HW_WATER_C10 + \
            2 * HW_WATER_C11 * t_k + 3 * HW_WATER_C12 * t_k * t_k + \
            HW_WATER_C13 / t_k
    else:
        dln = -HW_ICE_C8 / (t_k * t_k) + HW_ICE_C10 + \
            2 * HW_ICE_C11 * t_k + 3 * HW_ICE_C12 * t_k * t_k + \
            4 * HW_ICE_C13 * math.pow(t_k, 3) + HW_ICE_C14 / t_k

    return dln * pws_val

def dew_point_explicit(pw_kpa):
    if pw_kpa <= 0: return 0.0

    alpha = math.log(pw_kpa)
    dp = DP_WATER["C14"] + DP_WATER["C15"] * alpha + \
        DP_WATER["C16"] * alpha * alpha + \
        DP_WATER["C17"] * math.pow(alpha, 3) + \
        DP_WATER["C18"] * math.pow(pw_kpa, DP_WATER["n"])

    if dp < 0:
        dp = DP_ICE["C14"] + DP_ICE["C15"] * alpha + DP_ICE["C16"] * alpha * alpha

    return dp

def dew_point_newton(w, p, f_init):
    if w <= 0: return 0.0

    denomCheck = (MW_MA + w) * f_init
    pw = p * w / denomCheck if denomCheck > 0 else 0
    dp = dew_point_explicit(pw)

    for _ in range(2):
        f_dp = f_enhance_at_p(dp, p)
        denomCheck = (MW_MA + w) * f_dp
        pw = p * w / denomCheck if denomCheck > 0 else 0
        dp = dew_point_explicit(pw)

    step = 1.0
    for _ in range(50):
        pws_dp = pws_kpa(dp)
        f_dp = f_enhance_at_p(dp, p)
        fpws_dp = f_dp * pws_dp
        denom_dp = p - fpws_dp

        if abs(denom_dp) < 1e-15: break

        w_dp = MW_MA * fpws_dp / denom_dp
        if w_dp <= 0: break

        if abs(w / w_dp - 1) < 1e-6: break
        if abs(step) < 0.0001: break

        dpws = dpws_dt(dp, pws_dp)
        dw_dp = MW_MA * f_dp * dpws * p / (denom_dp * denom_dp)

        if abs(dw_dp) < 1e-20: break

        step = (w - w_dp) / dw_dp
        dp += step

    return dp

def psychrometrics(dbt, wbt, alt_m=0.0):
    p = 101.325 * math.pow(1 - 2.25577e-5 * alt_m, 5.2559)
    pws_wbt = pws_kpa(wbt)
    f_wbt = f_enhance_at_p(wbt, p)

    fpws = f_wbt * pws_wbt
    ws = MW_MA * fpws / (p - fpws)

    denom = L0 + CpS * dbt - CpW * wbt
    w = ((L0 - L_COEFF * wbt) * ws - (dbt - wbt)) / denom
    if w < 0: w = 0.0

    dp = dew_point_newton(w, p, f_wbt)

    pws_dbt = pws_kpa(dbt)
    f_dbt = f_enhance_at_p(dbt, p)
    rh = 0.0
    if f_dbt * pws_dbt > 0:
        rh = 100.0 * (w / (MW_MA + w)) * p / (f_dbt * pws_dbt)

    h = 1.006 * dbt + w * (L0 + CpS * dbt)
    sv = Ra * (dbt + 273.15) * (1 + 1.6078 * w) / p
    dens = (1 + w) / sv

    return {
        "HR": round(w, 5),
        "DP": round(dp, 2),
        "RH": round(rh, 2),
        "H": round(h, 4),
        "SV": round(sv, 4),
        "Dens": round(dens, 5),
        "P": round(p, 3)
    }
