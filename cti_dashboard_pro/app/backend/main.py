import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Add backend and core to path so imports work happily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from core.calculations import init as init_engines

from routers import calculations, excel, reports

app = FastAPI(
    title="SS Cooling Tower API",
    docs_url=None,    # Disable /docs in production
    redoc_url=None,   # Disable /redoc in production
    openapi_url=None, # Disable /openapi.json schema dump
)



# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers

app.include_router(calculations.router, prefix="/api", tags=["calculations"])
app.include_router(excel.router, prefix="/api", tags=["excel"])
app.include_router(reports.router, prefix="/api", tags=["reports"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "app" / "web"
DATA_ROOT = Path(__file__).resolve().parent / "core" / "data"

# Initialize engines on startup
@app.on_event("startup")
def startup_event():
    psychro_bin = DATA_ROOT / "psychro_f_alt.bin"
    merkel_bin = DATA_ROOT / "merkel_poly.bin"
    if psychro_bin.exists() and merkel_bin.exists():
        init_engines(str(psychro_bin), str(merkel_bin))
        print("Engines initialized successfully.")
    else:
        print("[WARNING] Could not find binary data files from", DATA_ROOT)

class CustomStaticFiles(StaticFiles):
    def file_response(self, full_path: str, stat_result, scope, status_code: int = 200):
        resp = super().file_response(full_path, stat_result, scope, status_code)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

# Serve UI
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(str(WEB_ROOT / "favicon.svg"), headers={"Cache-Control": "public, max-age=31536000, immutable"})

app.mount("/css", CustomStaticFiles(directory=str(WEB_ROOT / "css")), name="css")
app.mount("/js", CustomStaticFiles(directory=str(WEB_ROOT / "js")), name="js")

templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

if __name__ == "__main__":
    port = 8000
    print(f"Starting highly optimized FastAPI server on http://localhost:{port}")
    # Local mode automatically sets the ENABLE_LOCAL_WRITE flag so Windows batch users can filter excel 
    os.environ["ENABLE_LOCAL_WRITE"] = "1"
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
