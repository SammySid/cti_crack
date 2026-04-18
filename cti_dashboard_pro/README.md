# CTI Dashboard Pro — Full-Stack ATC-105 Performance Analysis Suite

`cti_dashboard_pro` is the **enterprise FastAPI-backed** evolution of the CTI Analysis Suite. It runs at **`https://ct.ftp.sh`** (Oracle UK VPS, protected by Authelia SSO).

---

## What it does

| Feature | Description |
|---|---|
| **Thermal Analysis** | Live Merkel-based performance curves at 90/100/110% flow — supply vs demand KaV/L, approach, range, CWT prediction |
| **Psychrometric Calculator** | Full Hyland-Wexler psychrometrics (DP, HR, RH, H, SV, density) with altitude correction |
| **Excel Data Filter** | Filters multi-file time-series `.xlsx` datasets by time window; interpolates, merges, exports consolidated workbook |
| **Excel Report Export** | Generates branded professional thermal report `.xlsx` from current analysis inputs |
| **ATC-105 PDF Report Engine** | Three-stage CTI ATC-105 evaluation (Pre-Test, Post-Fan Change, Post-Distribution Change) — full 5-step analysis per test, professional cross-plots, comparison table, and multi-test PDF report |
| **Excel Auto-Fill** | Upload filtered Excel output directly into the report builder to auto-populate test condition fields |

---

## ATC-105 Report Engine — Three-Stage Evaluation

The report builder evaluates **three independent test phases** (Pre, Post Fan Change, Post Distribution Change) each against the same design baseline, following the **CTI ATC-105 standard** exactly:

| Step | What happens |
|---|---|
| **STEP 1** | Computes 3×3 CWT grid (Table 1) from Merkel engine at test WBT — 3 ranges × 3 flows |
| **STEP 2** | Cross Plot 1 (CWT vs Range chart at test WBT) → Table 2 (CWT at test range for each flow, read from the chart) |
| **STEP 3** | Calculates Adjusted Water Flow: `Q_adj = Q_test × (Wd/Wt)^⅓ × ρ^⅓` |
| **STEP 4** | Cross Plot 2 (Water Flow vs CWT) — marks Q_adj on X-axis → reads Predicted CWT |
| **STEP 5** | Computes shortfall (`Test CWT − Predicted CWT`) and capability (`Q_adj / Q_pred × 100%`) |

All three tests run in **parallel API calls**. Each test gets its own complete set of cross-plots, tables, and result pages in the PDF. A final comparison table shows all three shortfalls and cumulative improvement.

### Tower Constants — C and m
`constant_c = 1.2` and `constant_m = 0.6` (CTI standard defaults for cross-flow fill) are applied internally. They are **not exposed as UI inputs**. The key calibration parameter is the **L/G ratio** — this must be set correctly for the specific tower being evaluated.

### Density Ratio Override
The backend auto-computes water density ratio using the Kell (1975) formula. Enter a value from ATC-105 standard tables (e.g., `1.0337`) in the **Density Ratio** field to match a specific CTI printout.

### Excel Auto-Fill
After running the Excel Data Filter tool, click **"Upload Filter Output → Auto-Fill"** in the Report Builder to automatically populate CWT, HWT, WBT, Flow, and Fan Power for the current test.

---

## Quick Start (Local)

```bash
pip install fastapi uvicorn pydantic python-multipart pandas openpyxl xlsxwriter python-dateutil jinja2 xhtml2pdf matplotlib
```

Then from `cti_dashboard_pro/`:
```bash
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```
Or run `start_dashboard.bat` (Windows).

---

## VPS Deployment

The app is containerised with Docker and deployed to **Oracle UK VPS**.

```bash
# Deploy immediately (commits, pushes, SSH-triggers VPS rebuild)
python deploy_pro_to_vps.py
```

Or push to `master` — the VPS auto-syncs within 5 minutes via `auto_sync.sh`.

See [`VPS_HOSTING_GUIDE.md`](../VPS_HOSTING_GUIDE.md) for full architecture.

---

## Engineering Reference

- [DOCUMENTATION.md](docs/DOCUMENTATION.md) — full API reference and architecture
- [COOLING_TOWER_FUNDAMENTALS.md](docs/COOLING_TOWER_FUNDAMENTALS.md) — first-principles physics guide
- [HANDOFF.md](../HANDOFF.md) — engine reverse-engineering history

---

## ⚠️ Critical — Do Not Touch

The Merkel engine (`core/merkel_engine.py`) and Psychrometrics engine (`core/psychro_engine.py`) achieved **100% accuracy** vs the CTI binary after extensive reverse-engineering and probing. **Never modify these engines.** All calculation improvements must go through the `ATC-105` layer in `main.py`, not the core engines.

Inside `core/`, always use **relative imports** (`from .psychro_engine import ...`) to prevent Python from creating duplicate module instances that would break the binary lookup tables.

### Accuracy Note
The Merkel model with correct L/G produces results within **0.03°C** of independently verified ATC-105 evaluations — well within the ±0.1°C measurement uncertainty of the test instruments. The small residual is inherent to the analytical model vs manufacturer empirical curves and cannot be reduced further without providing actual manufacturer performance curve data.
