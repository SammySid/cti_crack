import time
import uuid
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.report_service import generate_pdf_report

router = APIRouter()

_PDF_STORE: dict[str, tuple[bytes, str, float]] = {}
_PDF_STORE_LOCK = threading.Lock()

def _cleanup_pdf_store():
    while True:
        time.sleep(60)
        now = time.time()
        with _PDF_STORE_LOCK:
            expired = [k for k, (_, _, exp) in _PDF_STORE.items() if now > exp]
            for k in expired:
                del _PDF_STORE[k]

threading.Thread(target=_cleanup_pdf_store, daemon=True).start()

@router.post("/generate-pdf-report")
def api_generate_pdf_report(payload: dict):
    try:
        pdf_bytes = generate_pdf_report(payload)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {str(e)}\n{traceback.format_exc()}")

    token = uuid.uuid4().hex
    filename = payload.get("_filename", "CTI_Performance_Report_ATC105.pdf")
    expiry = time.time() + 300

    with _PDF_STORE_LOCK:
        _PDF_STORE[token] = (pdf_bytes, filename, expiry)

    return {"token": token, "filename": filename}

@router.get("/download-pdf/{token}")
def api_download_pdf(token: str):
    with _PDF_STORE_LOCK:
        entry = _PDF_STORE.pop(token, None)

    if entry is None:
        raise HTTPException(status_code=404, detail="PDF token not found or already downloaded.")

    pdf_bytes, filename, expiry = entry
    if time.time() > expiry:
        raise HTTPException(status_code=410, detail="PDF token has expired. Please regenerate.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
