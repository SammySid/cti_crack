"""
helpers.py — Reusable ReportLab flowable builders.
"""
from reportlab.platypus import Paragraph, Table, TableStyle, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

from .styles import (
    NAVY, BLUE, SKY, STEEL, PANEL, BORDER, PAPER, RED,
    WHITE, SLATE, LIGHT, BODY_COLOR,
)

A4_W, A4_H = A4
L_MARGIN = R_MARGIN = 51
T_MARGIN = 51
B_MARGIN = 45
AVAIL_W = A4_W - L_MARGIN - R_MARGIN   # ≈ 493.27 pt


# ── Section / sub-section bars ────────────────────────────────────────────────

def section_bar(text: str, styles: dict, indent: int = 10) -> Table:
    """Dark navy bar with white bold text spanning the full content width."""
    t = Table(
        [[Paragraph(text, styles['SectionBar'])]],
        colWidths=[AVAIL_W],
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), indent),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ]))
    return t


def sub_bar(text: str, styles: dict, bg=None) -> Table:
    """Steel-blue (or custom) sub-section bar."""
    bg = bg or STEEL
    t = Table(
        [[Paragraph(text, styles['SubBar'])]],
        colWidths=[AVAIL_W],
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ]))
    return t


# ── Step header (badge + title) ───────────────────────────────────────────────

def step_header(step_num: str, title_text: str, styles: dict) -> Table:
    """Blue step-number badge next to a panel-background title row."""
    badge = Paragraph(f"STEP<br/>{step_num}", styles['StepBadge'])
    title = Paragraph(title_text, styles['StepTitle'])
    t = Table([[badge, title]], colWidths=[36, AVAIL_W - 36])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BLUE),
        ('BACKGROUND', (1, 0), (1, 0), PANEL),
        ('LEFTPADDING',   (0, 0), (0, 0), 4),
        ('RIGHTPADDING',  (0, 0), (0, 0), 4),
        ('LEFTPADDING',   (1, 0), (1, 0), 12),
        ('LINEBEFORE',    (1, 0), (1, 0), 3, BLUE),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


# ── Data table (NAVY header + alternating rows) ───────────────────────────────

def data_table(
    header_row: list,
    data_rows: list,
    col_widths: list,
    styles: dict,
    alt_bg=None,
) -> Table:
    """
    Builds a styled Table:  NAVY header row, alternating PAPER / WHITE body rows.
    header_row  — list of strings (raw text).
    data_rows   — list of lists of strings.
    col_widths  — list of floats that must sum to AVAIL_W.
    """
    alt_bg = alt_bg or PAPER

    tbl_data = [[Paragraph(str(h), styles['TblHdr']) for h in header_row]]
    for row in data_rows:
        styled = []
        for j, cell in enumerate(row):
            style_key = 'TblBodyL' if j == 0 else 'TblBody'
            styled.append(Paragraph(str(cell) if cell not in (None, '') else '—', styles[style_key]))
        tbl_data.append(styled)

    tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('GRID',          (0, 0), (-1, -1), 0.5, BORDER),
        ('BOX',           (0, 0), (-1, -1), 1.5, NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for i in range(1, len(data_rows) + 1):
        bg = alt_bg if i % 2 == 0 else WHITE
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ── Calculation panel (Step 3) ────────────────────────────────────────────────

def calc_panel(rows: list, total_row: tuple, styles: dict, w: float = AVAIL_W) -> Table:
    """
    Bordered light-blue panel for Step 3 inputs.
    rows       — list of (label_str, value_str) tuples (max 10 rows).
    total_row  — (label_str, value_str) rendered in NAVY-header style.
    """
    col_w1 = w * 0.70
    col_w2 = w * 0.30

    tbl_data = []
    for label, value in rows:
        tbl_data.append([
            Paragraph(label, styles['CalcLabel']),
            Paragraph(str(value), styles['CalcValue']),
        ])
    n = len(rows)
    tbl_data.append([
        Paragraph(total_row[0], styles['TblHdr']),
        Paragraph(str(total_row[1]), styles['TblHdr']),
    ])

    tbl = Table(tbl_data, colWidths=[col_w1, col_w2])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0),  (-1, n - 1), PANEL),
        ('BACKGROUND', (0, n),  (-1, n),     NAVY),
        ('GRID',          (0, 0), (-1, -1), 0.5, BORDER),
        ('BOX',           (0, 0), (-1, n),   1.5, NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tbl


# ── Result card (conclusion box) ──────────────────────────────────────────────

def result_card(
    test_label: str,
    shortfall,
    capability,
    adj_flow,
    pred_flow,
    test_cwt,
    pred_cwt,
    styles: dict,
    w: float = AVAIL_W,
) -> list:
    """
    Returns [header_table, body_table, summary_bar_table] — three flowables
    that together form the CWT Shortfall / Capability result card.
    """
    def _safe_fmt(val, decimals=2, fallback='—'):
        try:
            f = float(val)
            return f'{f:.{decimals}f}'
        except (TypeError, ValueError):
            return str(val) if val not in (None, '') else fallback

    sf_num_str = _safe_fmt(shortfall)
    cap_str    = _safe_fmt(capability, 1)
    adj_str    = _safe_fmt(adj_flow, 0)
    pf_str     = _safe_fmt(pred_flow, 0)
    tc_str     = _safe_fmt(test_cwt)
    pc_str     = _safe_fmt(pred_cwt)

    try:
        sf_disp = f"{float(shortfall):+.2f} °C"
    except (TypeError, ValueError):
        sf_disp = f"{shortfall} °C"
    cap_disp = f"{cap_str} %"

    # Header bar
    header = Table(
        [[Paragraph(f"CONCLUSION — {test_label}", styles['CardHeader'])]],
        colWidths=[w],
    )
    header.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
    ]))

    col_w = w / 2
    left_cells = [
        Paragraph("CWT SHORTFALL IN PERFORMANCE", styles['RcLabel']),
        Paragraph(sf_disp, styles['RcValueRed']),
        Paragraph(f"Test CWT ({tc_str}°C) vs Predicted CWT ({pc_str}°C)", styles['RcSub']),
    ]
    right_cells = [
        Paragraph("COOLING TOWER CAPABILITY", styles['RcLabel']),
        Paragraph(cap_disp, styles['RcValueBlue']),
        Paragraph(f"= {adj_str} / {pf_str} × 100", styles['RcSub']),
    ]

    body = Table([[left_cells, right_cells]], colWidths=[col_w, col_w])
    body.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), PANEL),
        ('LINEBEFORE',    (1, 0), (1, 0),   1.5, HexColor('#93c5fd')),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING',   (0, 0), (-1, -1), 16),
        ('BOX',           (0, 0), (-1, -1), 1.5, NAVY),
    ]))

    # Result summary bar
    try:
        sf_val  = float(shortfall)
        cap_val = float(capability)
        if sf_val < 0:
            summary_txt = (
                f"Tower is <b>BELOW specification</b> by {abs(sf_val):.2f}°C "
                f"— Capability: <b>{cap_val:.1f}%</b>"
            )
        elif sf_val == 0:
            summary_txt = f"Tower <b>MEETS design specification</b> — Capability: <b>{cap_val:.1f}%</b>"
        else:
            summary_txt = (
                f"Tower <b>EXCEEDS design</b> by {sf_val:.2f}°C "
                f"— Capability: <b>{cap_val:.1f}%</b>"
            )
    except (TypeError, ValueError):
        summary_txt = "ATC-105 Analysis Complete"

    summary_bar = Table(
        [[Paragraph(summary_txt, styles['ResultSummary'])]],
        colWidths=[w],
    )
    summary_bar.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), SKY),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('BOX',           (0, 0), (-1, -1), 1.0, NAVY),
    ]))

    return [header, body, summary_bar]
