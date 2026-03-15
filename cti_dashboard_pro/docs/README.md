# SS Cooling Tower Dashboard

Modern local dashboard for cooling tower thermal analysis, psychrometric calculations, and Excel reporting.

## Quick Start

- Run `start_dashboard.bat` from the project root.
- The launcher validates or installs Python and Node.js, installs Python dependencies, then starts the server.
- Open `http://localhost:8000`.

## Organized project layout

- Root: `start_dashboard.bat` only
- Web app: `app/web/`
- Python backend: `app/backend/`
- Utility scripts: `app/scripts/`
- Generated outputs: `app/reports/`
- Documentation: `docs/`

## Main runtime files

- `app/backend/dashboard_server.py`
- `app/backend/excel_gen.py`
- `app/backend/excel_filter_service.py`
- `app/web/index.html`
- `app/web/css/main.css`
- `app/web/js/`
- `app/scripts/test_backend.mjs`
- `app/scripts/generate_report.bat`

## API routes

- `POST /api/export-excel`
- `POST /api/filter-excel`
- `POST /api/filter-excel-local`

Full technical details: `docs/DOCUMENTATION.md`

