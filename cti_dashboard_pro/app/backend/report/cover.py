"""
cover.py — Canvas-level drawing for the full cover page.

The cover page is rendered 100% via the ReportLab canvas (in the
onFirstPage callback) so we get pixel-perfect layout without any
flowable height-management headaches.

Public API:
    draw_cover_canvas(canvas, doc, payload)  — call this from onFirstPage
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

_NAVY    = HexColor('#1e3a5f')
_BLUE    = HexColor('#1d4ed8')
_SKY     = HexColor('#dbeafe')
_SLATE   = HexColor('#475569')
_LIGHT   = HexColor('#64748b')
_BORDER  = HexColor('#cbd5e1')
_BODY    = HexColor('#0f172a')
_PANEL   = HexColor('#f0f6ff')
_TAGLINE = HexColor('#93c5fd')
_WHITE   = colors.white


def _draw_wrapped_text(canvas, text: str, x: float, y: float,
                       max_width: float, font: str, size: float,
                       color, line_height: float = None) -> float:
    """
    Draw text wrapping within max_width. Returns y after last line.
    Simple word-wrap (no hyphenation).
    """
    if line_height is None:
        line_height = size * 1.35
    canvas.setFont(font, size)
    canvas.setFillColor(color)
    words = text.split()
    current_line = ''
    lines = []
    for word in words:
        test = (current_line + ' ' + word).strip()
        if canvas.stringWidth(test, font, size) <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= line_height
    return y


def draw_cover_canvas(canvas, doc, payload: dict) -> None:
    """Draw the complete cover page on the ReportLab canvas."""
    canvas.saveState()
    W, H = A4
    L = R = 51.0

    # ── Top navy banner ───────────────────────────────────────────────────────
    band_h = 78.0
    canvas.setFillColor(_NAVY)
    canvas.rect(0, H - band_h, W, band_h, fill=1, stroke=0)

    canvas.setFont('Helvetica-Bold', 15)
    canvas.setFillColor(_WHITE)
    canvas.drawCentredString(W / 2, H - 34, 'SS COOLING TOWER CONSULTANTS')

    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(_TAGLINE)
    canvas.drawCentredString(
        W / 2, H - 54,
        'Thermal Design  \u00b7  CT Assessment & Upgrade  \u00b7  CT Testing  \u00b7  www.ssctc.org'
    )

    # Thin accent line below banner
    canvas.setStrokeColor(_BLUE)
    canvas.setLineWidth(2.5)
    canvas.line(L, H - band_h, W - R, H - band_h)

    # ── Report title block ────────────────────────────────────────────────────
    report_title = payload.get('report_title', 'CT PERFORMANCE EVALUATION REPORT')

    y = H - band_h - 38
    canvas.setFont('Helvetica-Bold', 22)
    canvas.setFillColor(_NAVY)
    canvas.drawCentredString(W / 2, y, report_title)

    y -= 20
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(_SLATE)
    canvas.drawCentredString(W / 2, y,
        'PRE-TEST  /  POST FAN CHANGE  /  POST DISTRIBUTION CHANGE')
    y -= 15
    canvas.drawCentredString(W / 2, y, '\u2014  THREE-STAGE SINGLE CELL ASSESSMENT  \u2014')

    # ── Divider ───────────────────────────────────────────────────────────────
    y -= 18
    canvas.setStrokeColor(_BORDER)
    canvas.setLineWidth(0.8)
    canvas.line(L, y, W - R, y)

    # ── Asset block (sky-blue) ────────────────────────────────────────────────
    asset = payload.get('asset', '\u2014')
    y -= 10
    bh = 50.0
    bx, by = L, y - bh
    bw = W - L - R

    canvas.setFillColor(_SKY)
    canvas.rect(bx, by, bw, bh, fill=1, stroke=0)
    canvas.setStrokeColor(_NAVY)
    canvas.setLineWidth(1.5)
    canvas.rect(bx, by, bw, bh, fill=0, stroke=1)

    canvas.setFont('Helvetica-Bold', 15)
    canvas.setFillColor(_NAVY)
    canvas.drawCentredString(W / 2, by + bh / 2 - 6, asset)

    y = by - 22

    # ── Metadata table ────────────────────────────────────────────────────────
    meta_rows = [
        ('OWNER / CLIENT',    payload.get('client', '\u2014')),
        ('TESTING AGENCY',    'SS COOLING TOWER CONSULTANTS (SSCTC)'),
        ('DATE OF TEST',      payload.get('test_date', '\u2014')),
        ('REPORT DATE',       payload.get('report_date', '\u2014')),
        ('ASSESSMENT METHOD', 'CTI ATC-105 Merkel Method \u2014 Applied independently to each of 3 test stages'),
    ]

    row_h   = 32.0
    tbl_w   = bw
    lw      = tbl_w * 0.30
    rw      = tbl_w * 0.70
    tbl_top = y
    tbl_bot = tbl_top - len(meta_rows) * row_h

    # Left column background
    canvas.setFillColor(_PANEL)
    canvas.rect(L, tbl_bot, lw, len(meta_rows) * row_h, fill=1, stroke=0)

    for i, (label, value) in enumerate(meta_rows):
        row_y = tbl_top - i * row_h
        row_bot = row_y - row_h

        # Row divider
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(L, row_bot, L + tbl_w, row_bot)

        # Label
        canvas.setFont('Helvetica-Bold', 8.5)
        canvas.setFillColor(_NAVY)
        canvas.drawString(L + 8, row_y - 20, label)

        # Value (with simple wrap)
        max_val_w = rw - 12
        canvas.setFont('Helvetica', 8.5)
        canvas.setFillColor(_BODY)
        val_x = L + lw + 8
        val_y = row_y - 13
        words = value.split()
        line, lines_acc = '', []
        for w_word in words:
            test_line = (line + ' ' + w_word).strip()
            if canvas.stringWidth(test_line, 'Helvetica', 8.5) <= max_val_w:
                line = test_line
            else:
                if line:
                    lines_acc.append(line)
                line = w_word
        if line:
            lines_acc.append(line)
        for li, txt in enumerate(lines_acc[:2]):   # max 2 lines
            canvas.drawString(val_x, val_y - li * 12, txt)

    # Table outer border
    canvas.setStrokeColor(_NAVY)
    canvas.setLineWidth(1.5)
    canvas.rect(L, tbl_bot, tbl_w, len(meta_rows) * row_h, fill=0, stroke=1)
    # Vertical divider between label/value cols
    canvas.setLineWidth(0.5)
    canvas.line(L + lw, tbl_bot, L + lw, tbl_top)

    y = tbl_bot - 22

    # ── Confidentiality notice ────────────────────────────────────────────────
    canvas.setFont('Helvetica-Oblique', 7.5)
    canvas.setFillColor(_SLATE)
    conf_lines = [
        'CONFIDENTIAL \u2014 This report is prepared exclusively for the above-named client',
        'by SS Cooling Tower Consultants.  It may not be reproduced, distributed, or',
        'disclosed to any third party without prior written consent of SSCTC.',
    ]
    for cl in conf_lines:
        canvas.drawCentredString(W / 2, y, cl)
        y -= 12

    # ── Bottom navy footer band ───────────────────────────────────────────────
    foot_h = 55.0
    canvas.setFillColor(_NAVY)
    canvas.rect(0, 0, W, foot_h, fill=1, stroke=0)

    canvas.setFont('Helvetica-Bold', 11)
    canvas.setFillColor(_WHITE)
    canvas.drawCentredString(W / 2, foot_h - 22, 'SS COOLING TOWER CONSULTANTS')

    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(_TAGLINE)
    canvas.drawCentredString(
        W / 2, foot_h - 38,
        'www.ssctc.org  \u00b7  Thermal Performance Testing & Engineering Services'
    )

    canvas.restoreState()
