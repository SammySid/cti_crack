"""
report_service.py — Main PDF report generator for CTI Dashboard Pro.

Public API (unchanged — main.py calls this):
    generate_pdf_report(payload: dict) -> bytes

Architecture:
  - Matplotlib chart functions are kept verbatim (unchanged).
  - PDF is built via ReportLab Platypus (replaces WeasyPrint + Jinja2).
  - Two-pass build gives accurate "Page X of Y" totals.
  - Cover page is drawn entirely on the ReportLab canvas (pixel-perfect).
  - Running header + footer on every page except the cover (page 1).
"""

import os
import io
import base64

from fastapi import HTTPException

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib import colors

from services.charting_service import create_cross_plot_1, create_cross_plot_2, create_blank_plot

from report.styles import build_styles
from report.cover import draw_cover_canvas
from report.narrative import build_narrative
from report.summary_table import build_summary_table
from report.test_section import build_test_section

A4_W, A4_H = A4


# ─────────────────────────────────────────────────────────────────────────────
# Per-test context builder (unchanged logic — generates all charts + data)
# ─────────────────────────────────────────────────────────────────────────────

def _build_test_context(atc: dict, label: str, design_flow_fallback, _f0) -> dict:
    """
    Build all template variables for one ATC-105 test result.
    Called once per test (pre / post-fan / post-distribution).
    """
    cp1 = atc.get("cross_plot_1", {})
    cp2 = atc.get("cross_plot_2", {})

    if not cp1 or not cp2:
        plot_1_b64 = create_blank_plot(f"Cross Plot 1 — {label} — No ATC-105 data provided")
        plot_2_b64 = create_blank_plot(f"Cross Plot 2 — {label} — No ATC-105 data provided")
    else:
        plot_1_b64 = create_cross_plot_1(cp1, label)
        plot_2_b64 = create_cross_plot_2(cp2, label)

    flows_m3h = atc.get("flows_m3h", {})
    intersect = {
        "f90_flow":  flows_m3h.get(90,  flows_m3h.get("90",  "—")),
        "f90_cwt":   cp1.get("f90_cwt",  "—"),
        "f100_flow": flows_m3h.get(100, flows_m3h.get("100", "—")),
        "f100_cwt":  cp1.get("f100_cwt", "—"),
        "f110_flow": flows_m3h.get(110, flows_m3h.get("110", "—")),
        "f110_cwt":  cp1.get("f110_cwt", "—"),
    }

    adj_flow   = atc.get("adj_flow",   "—")
    pred_cwt   = atc.get("pred_cwt",   "—")
    pred_flow  = atc.get("pred_flow",  "—")
    shortfall  = atc.get("shortfall",  "—")
    capability = atc.get("capability", "—")
    density_r  = atc.get("density_ratio_used", atc.get("density_ratio", "—"))

    test_cwt_raw = atc.get("test_cwt")
    test_wbt_raw = atc.get("test_wbt")
    test_cwt = test_cwt_raw if test_cwt_raw is not None else cp2.get("test_cwt", "—")

    try:
        test_approach = round(float(test_cwt_raw) - float(test_wbt_raw), 2)
    except (TypeError, ValueError):
        test_approach = "—"

    math_results = {
        "adj_flow":         adj_flow,
        "pred_cwt":         pred_cwt,
        "test_cwt":         test_cwt,
        "test_hwt":         atc.get("test_hwt", "—"),
        "test_approach":    test_approach,
        "shortfall":        shortfall,
        "capability":       capability,
        "density_ratio":    density_r,
        "pred_flow":        pred_flow,
        "test_wbt":         atc.get("test_wbt", "—"),
        "test_flow":        atc.get("test_flow", cp2.get("flows", [None])[0] if cp2.get("flows") else "—"),
        "fan_power_design": atc.get("fan_power_design", None),
        "fan_power_test":   atc.get("fan_power_test",   None),
    }

    table1_raw = atc.get("table1", {})
    ranges_abs = atc.get("ranges_abs", {})
    table1_rows = []

    def _fmt(val):
        try:
            return f"{float(val):.2f}"
        except (TypeError, ValueError):
            return str(val) if val else "—"

    for rp_key, rp_label in [("80", "80%"), ("100", "100%"), ("120", "120%")]:
        abs_rng = ranges_abs.get(int(rp_key), ranges_abs.get(rp_key, "—"))
        row = {
            "range_pct": rp_label,
            "range_abs": f"{abs_rng} °C" if abs_rng != "—" else "—",
            "cwt_90":  _fmt(table1_raw.get("90",  {}).get(rp_key)),
            "cwt_100": _fmt(table1_raw.get("100", {}).get(rp_key)),
            "cwt_110": _fmt(table1_raw.get("110", {}).get(rp_key)),
        }
        table1_rows.append(row)

    design_flow = atc.get("design_flow", design_flow_fallback)
    try:
        df_num = float(design_flow)
    except (TypeError, ValueError):
        df_num = 0.0

    try:
        design_approach = round(float(atc.get("design_cwt", 0)) - float(atc.get("design_wbt", 0)), 2)
    except (TypeError, ValueError):
        design_approach = "—"

    return {
        "label":            label,
        "design_approach":  design_approach,
        "plot_1":           plot_1_b64,
        "plot_2":           plot_2_b64,
        "table1_rows":      table1_rows,
        "intersect":        intersect,
        "math_results":     math_results,
        "test_range":       atc.get("test_range",   "—"),
        "design_range":     atc.get("design_range", "—"),
        "test_wbt":         atc.get("test_wbt",     "—"),
        "design_wbt":       atc.get("design_wbt",   "—"),
        "design_cwt":       atc.get("design_cwt",   "—"),
        "design_hwt":       atc.get("design_hwt",   "—"),
        "design_flow":      design_flow,
        "test_cwt":         test_cwt,
        "test_hwt":         atc.get("test_hwt",     "—"),
        "test_flow":        atc.get("test_flow",    "—"),
        "test_approach":    test_approach,
        "flow_90":          _f0(df_num * 0.9),
        "flow_100":         _f0(df_num),
        "flow_110":         _f0(df_num * 1.1),
        # Safety margins applied (passed through from ATC-105 API response)
        "offsets_applied":  atc.get("offsets_applied", {}),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Canvas callbacks
# ─────────────────────────────────────────────────────────────────────────────

def _make_canvas_callbacks(payload: dict, report_title: str, total_pages: list):
    """
    Returns (on_first_page, on_later_pages) canvas callbacks.
    total_pages is a mutable list [N] so it can be updated between passes.
    """
    _TEAL = HexColor('#0e7490')
    _NAVY = HexColor('#0d2137')
    _MUTED = HexColor('#64748b')
    _BORDER = HexColor('#cbd5e1')

    def _on_first_page(canvas, doc):
        draw_cover_canvas(canvas, doc, payload)

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        W, H = A4
        L = R = 48.0
        B = 44.0
        T = 48.0

        page_num = canvas.getPageNumber()

        # Running header — teal rule with company name left, tagline right
        y_hdr = H - T + 8
        canvas.setStrokeColor(_TEAL)
        canvas.setLineWidth(1.8)
        canvas.line(L, y_hdr, W - R, y_hdr)

        canvas.setFont('Helvetica-Bold', 7.5)
        canvas.setFillColor(_NAVY)
        canvas.drawString(L, y_hdr + 4, 'SS COOLING TOWER CONSULTANTS')

        canvas.setFont('Helvetica', 6.5)
        canvas.setFillColor(_MUTED)
        canvas.drawRightString(
            W - R, y_hdr + 4,
            'Thermal Design \u00b7 CT Assessment & Upgrade \u00b7 CT Testing \u00b7 www.ssctc.org',
        )

        # Footer — thin grey rule + centred details
        footer_y = B - 14
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(L, footer_y + 8, W - R, footer_y + 8)

        canvas.setFont('Helvetica', 6.5)
        canvas.setFillColor(_MUTED)
        total = total_pages[0] if total_pages[0] else '?'
        canvas.drawRightString(
            W - R, footer_y,
            f'SS COOLING TOWER CONSULTANTS  \u00b7  {report_title}  \u00b7  Page {page_num} of {total}',
        )

        canvas.restoreState()

    return _on_first_page, _on_later_pages


# ─────────────────────────────────────────────────────────────────────────────
# "End of Report" flowables
# ─────────────────────────────────────────────────────────────────────────────

def _end_of_report(payload: dict, styles: dict) -> list:
    report_date = payload.get('report_date', '')
    items = [
        Spacer(1, 30),
        Paragraph('\u2014\u2014\u2014  END OF REPORT  \u2014\u2014\u2014', styles['EndTitle']),
        Spacer(1, 8),
        Paragraph('SS COOLING TOWER CONSULTANTS', styles['EndSub']),
        Paragraph('www.ssctc.org', styles['EndSub']),
    ]
    if report_date:
        items.append(Paragraph(report_date, styles['EndSub']))
    return items


# ─────────────────────────────────────────────────────────────────────────────
# Main PDF generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf_report(payload: dict) -> bytes:
    """
    Build and return raw PDF bytes for the CTI performance report.

    Payload must include three ATC-105 results:
      atc105_pre  — Pre-test
      atc105_post — Post fan-change
      atc105_dist — Post distribution-change
    """
    # ── Format helpers ────────────────────────────────────────────────────────
    def _f2(v, unit=""):
        try:   return f"{float(v):.2f}{unit}"
        except (TypeError, ValueError): return str(v)

    def _f1(v, unit=""):
        try:   return f"{float(v):.1f}{unit}"
        except (TypeError, ValueError): return str(v)

    def _f0(v, unit=""):
        try:   return f"{float(v):.0f}{unit}"
        except (TypeError, ValueError): return str(v)

    # ── Resolve test results ──────────────────────────────────────────────────
    atc_pre  = payload.get("atc105_pre")
    atc_post = payload.get("atc105_post")
    atc_dist = payload.get("atc105_dist")

    if not atc_pre and not atc_post and not atc_dist:
        atc_dist = payload.get("atc105", {})

    primary = atc_dist or atc_post or atc_pre or {}
    design_flow_fallback = primary.get("design_flow", "—")

    # ── Build per-test contexts (generates matplotlib charts) ─────────────────
    test_label_pairs = [
        (atc_pre,  "TEST 1 \u2014 PRE TEST"),
        (atc_post, "TEST 2 \u2014 POST FAN CHANGE"),
        (atc_dist, "TEST 3 \u2014 POST DISTRIBUTION CHANGE"),
    ]
    test_ctxs = []
    for atc, label in test_label_pairs:
        if atc:
            try:
                test_ctxs.append(_build_test_context(atc, label, design_flow_fallback, _f0))
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Chart generation failed for {label}: {exc}")

    # ── Build ReportLab styles ─────────────────────────────────────────────────
    styles = build_styles()

    report_title = payload.get("report_title", "CT PERFORMANCE EVALUATION REPORT")

    # ── Story factory (called twice for two-pass build) ───────────────────────
    def _make_story() -> list:
        story = []

        # Page 1: cover (drawn on canvas — just occupy the page with a spacer)
        story.append(Spacer(1, 1))
        story.append(PageBreak())

        # Narrative pages
        story.extend(build_narrative(payload, styles))

        # Final data table page
        story.extend(build_summary_table(payload, styles))

        # Per-test ATC-105 analysis (4 pages each)
        for i, ctx in enumerate(test_ctxs):
            story.extend(build_test_section(ctx, styles))
            if i < len(test_ctxs) - 1:
                story.append(PageBreak())

        # End of report
        story.extend(_end_of_report(payload, styles))

        return story

    # ── Pass 1: count total pages ─────────────────────────────────────────────
    total_pages: list = [0]
    on_first, on_later = _make_canvas_callbacks(payload, report_title, total_pages)

    _MARGIN = dict(leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=44)

    buf1 = io.BytesIO()
    doc1 = SimpleDocTemplate(buf1, pagesize=A4, title=report_title, **_MARGIN)
    try:
        doc1.build(_make_story(), onFirstPage=on_first, onLaterPages=on_later)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF build (pass 1) failed: {exc}")

    total_pages[0] = doc1.page

    buf2 = io.BytesIO()
    doc2 = SimpleDocTemplate(buf2, pagesize=A4, title=report_title, **_MARGIN)
    try:
        doc2.build(_make_story(), onFirstPage=on_first, onLaterPages=on_later)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF build (pass 2) failed: {exc}")

    return buf2.getvalue()
