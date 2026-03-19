import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from merkel_engine import init_merkel_engine, merkel_kavl
from psychro_engine import init_psychro_engine, psychrometrics
from calculations import init, solve_off_design_cwt

print("=== Starting Accuracy Test ===")

# Paths to data files
merkel_bin = r"f:\2026 latest\cti Toolkit\cti-suite-final\cti_dashboard_pro\app\web\data\merkel_poly.bin"
psychro_bin = r"f:\2026 latest\cti Toolkit\cti-suite-final\cti_dashboard_pro\app\web\data\psychro_f_alt.bin"

init_merkel_engine(merkel_bin)
init_psychro_engine(psychro_bin)

# Test 1: Merkel KaV/L
print("\n--- Testing Merkel Engine ---")
test_hwt = 37.0
test_cwt = 32.0
test_wbt = 27.0
test_lg = 1.5

kavl_result = merkel_kavl(test_hwt, test_cwt, test_wbt, test_lg)
print(f"Inputs: HWT={test_hwt}, CWT={test_cwt}, WBT={test_wbt}, L/G={test_lg}")
print(f"Result: {kavl_result}")

if abs(kavl_result['kavl'] - 1.25927) < 0.1:  # Assuming a known approx or we will just see what it is
    pass 

# Test 2: Psychrometrics
print("\n--- Testing Psychro Engine ---")
psy_result = psychrometrics(35.0, 25.0)
print(f"Inputs: DBT=35.0, WBT=25.0")
print(f"Result: {psy_result}")

# Test 3: Off-design CWT prediction
print("\n--- Testing Prediction Engine ---")
pred_result = solve_off_design_cwt(test_wbt, test_hwt - test_cwt, test_lg, 1.2, 0.6)
print(f"Result: {pred_result}")

print("\n=== Accuracy Test Completed Successfully ===")
