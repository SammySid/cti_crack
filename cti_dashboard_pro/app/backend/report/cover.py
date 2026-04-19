"""
cover.py — Full cover page drawn entirely on the ReportLab canvas.

Content block is vertically centred between the top navy band and the
bottom navy footer so there is no awkward whitespace on any asset.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

_NAVY    = HexColor('#0d2137')
_TEAL    = HexColor('#0e7490')
_GOLD    = HexColor('#b45309')
_SKY     = HexColor('#ecfeff')
_PANEL   = HexColor('#f0f9ff')
_MUTED   = HexColor('#64748b')
_BODY    = HexColor('#1e293b')
_BORDER2 = HexColor('#cbd5e1')
_TAGLINE = HexColor('#7dd3fc')
_WHITE   = colors.white


def draw_cover_canvas(canvas, doc, payload: dict) -> None:
    canvas.saveState()
    W, H = A4
    L = R = 48.0

    # ── Two navy bands ────────────────────────────────────────────────────────
    TOP_H  = 78.0
    BOT_H  = 58.0
    canvas.setFillColor(_NAVY)
    canvas.rect(0, H - TOP_H, W, TOP_H, fill=1, stroke=0)
    canvas.rect(0, 0, W, BOT_H, fill=1, stroke=0)

    # Gold rule immediately below top band
    canvas.setStrokeColor(_GOLD)
    canvas.setLineWidth(2.5)
    canvas.line(L, H - TOP_H, W - R, H - TOP_H)

    # Gold rule immediately above bottom band
    canvas.setStrokeColor(_GOLD)
    canvas.setLineWidth(2.0)
    canvas.line(0, BOT_H, W, BOT_H)

    # Company name + tagline in top band
    canvas.setFont('Helvetica-Bold', 16)
    canvas.setFillColor(_WHITE)
    canvas.drawCentredString(W / 2, H - 34, 'SS COOLING TOWER CONSULTANTS')
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(_TAGLINE)
    canvas.drawCentredString(
        W / 2, H - 54,
        'Thermal Design  \u00b7  CT Assessment & Upgrade  \u00b7  CT Testing  \u00b7  www.ssctc.org',
    )

    # Company name + tagline in bottom band
    canvas.setFont('Helvetica-Bold', 11)
    canvas.setFillColor(_WHITE)
    canvas.drawCentredString(W / 2, BOT_H - 22, 'SS COOLING TOWER CONSULTANTS')
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(_TAGLINE)
    canvas.drawCentredString(
        W / 2, BOT_H - 38,
        'www.ssctc.org  \u00b7  Thermal Performance Testing & Engineering Services',
    )

    # ── Measure content block height so we can centre it ─────────────────────
    #   title_h         ≈ 28 (22pt leading) + 10 (gold rule gap) + 16 + 15 + 14
    #   asset_gap       = 14
    #   asset_h         = 52
    #   gap_after_asset = 16
    #   meta_rows       = 5 × 32
    #   gap_after_meta  = 16
    #   conf_lines      = 3 × 12 = 36
    TITLE_BLOCK_H  = 28 + 10 + 16 + 15 + 14   # 83
    ASSET_BLOCK_H  = 52
    META_ROWS      = 5
    META_ROW_H     = 32
    META_H         = META_ROWS * META_ROW_H     # 160
    CONF_H         = 3 * 12                     # 36
    GAP_ASSET      = 16
    GAP_META       = 16
    GAP_CONF       = 16

    TOTAL_CONTENT = (TITLE_BLOCK_H + GAP_ASSET + ASSET_BLOCK_H
                     + GAP_META + META_H + GAP_CONF + CONF_H)

    USABLE_H = H - TOP_H - BOT_H
    TOP_PAD  = (USABLE_H - TOTAL_CONTENT) / 2   # centre the block

    # Anchor: y decreases downward (canvas y increases upward)
    y = H - TOP_H - TOP_PAD                     # top of content block

    # ── Report title ──────────────────────────────────────────────────────────
    report_title = payload.get('report_title', 'CT PERFORMANCE EVALUATION REPORT')
    canvas.setFont('Helvetica-Bold', 22)
    canvas.setFillColor(_NAVY)
    canvas.drawCentredString(W / 2, y - 28, report_title)

    # Gold rule below title
    canvas.setStrokeColor(_GOLD)
    canvas.setLineWidth(1.8)
    canvas.line(L + 20, y - 38, W - R - 20, y - 38)

    # Sub-title lines
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(_MUTED)
    canvas.drawCentredString(W / 2, y - 56,
        'PRE-TEST  /  POST FAN CHANGE  /  POST DISTRIBUTION CHANGE')
    canvas.drawCentredString(W / 2, y - 72,
        '\u2014  THREE-STAGE SINGLE CELL ASSESSMENT  \u2014')

    # Teal divider
    canvas.setStrokeColor(_TEAL)
    canvas.setLineWidth(0.6)
    canvas.line(L, y - TITLE_BLOCK_H, W - R, y - TITLE_BLOCK_H)

    # ── Asset block ───────────────────────────────────────────────────────────
    asset = payload.get('asset', '\u2014')
    bx  = L
    by  = y - TITLE_BLOCK_H - GAP_ASSET - ASSET_BLOCK_H
    bw  = W - L - R

    canvas.setFillColor(_SKY)
    canvas.rect(bx, by, bw, ASSET_BLOCK_H, fill=1, stroke=0)
    canvas.setStrokeColor(_NAVY)
    canvas.setLineWidth(1.2)
    canvas.rect(bx, by, bw, ASSET_BLOCK_H, fill=0, stroke=1)
    canvas.setStrokeColor(_TEAL)
    canvas.setLineWidth(5)
    canvas.line(bx, by, bx, by + ASSET_BLOCK_H)

    canvas.setFont('Helvetica-Bold', 16)
    canvas.setFillColor(_NAVY)
    canvas.drawCentredString(W / 2, by + ASSET_BLOCK_H / 2 - 7, asset)

    # ── Metadata table ────────────────────────────────────────────────────────
    meta_rows = [
        ('OWNER / CLIENT',    payload.get('client', '\u2014')),
        ('TESTING AGENCY',    'SS COOLING TOWER CONSULTANTS (SSCTC)'),
        ('DATE OF TEST',      payload.get('test_date', '\u2014')),
        ('REPORT DATE',       payload.get('report_date', '\u2014')),
        ('ASSESSMENT METHOD', 'CTI ATC-105 Merkel Method \u2014 Applied independently to each of 3 test stages'),
    ]
    tbl_top = by - GAP_META
    tbl_bot = tbl_top - META_H
    lw = bw * 0.28
    rw = bw * 0.72

    canvas.setFillColor(_PANEL)
    canvas.rect(L, tbl_bot, lw, META_H, fill=1, stroke=0)

    for i, (label, value) in enumerate(meta_rows):
        row_y = tbl_top - i * META_ROW_H

        canvas.setStrokeColor(_BORDER2)
        canvas.setLineWidth(0.4)
        canvas.line(L, row_y - META_ROW_H, L + bw, row_y - META_ROW_H)

        canvas.setFont('Helvetica-Bold', 8.5)
        canvas.setFillColor(_TEAL)
        canvas.drawString(L + 10, row_y - 20, label)

        canvas.setFont('Helvetica', 8.5)
        canvas.setFillColor(_BODY)
        val_x  = L + lw + 10
        max_w  = rw - 14
        words  = value.split()
        line, lines_acc = '', []
        for word in words:
            test = (line + ' ' + word).strip()
            if canvas.stringWidth(test, 'Helvetica', 8.5) <= max_w:
                line = test
            else:
                if line: lines_acc.append(line)
                line = word
        if line: lines_acc.append(line)
        for li, txt in enumerate(lines_acc[:2]):
            canvas.drawString(val_x, row_y - 13 - li * 12, txt)

    # Table outer border + column divider + teal left accent
    canvas.setStrokeColor(_NAVY)
    canvas.setLineWidth(1.2)
    canvas.rect(L, tbl_bot, bw, META_H, fill=0, stroke=1)
    canvas.setStrokeColor(_BORDER2)
    canvas.setLineWidth(0.5)
    canvas.line(L + lw, tbl_bot, L + lw, tbl_top)
    canvas.setStrokeColor(_TEAL)
    canvas.setLineWidth(4)
    canvas.line(L, tbl_bot, L, tbl_top)

    # ── Confidentiality notice ────────────────────────────────────────────────
    conf_y = tbl_bot - GAP_CONF
    canvas.setFont('Helvetica-Oblique', 7.5)
    canvas.setFillColor(_MUTED)
    for line in [
        'CONFIDENTIAL \u2014 This report is prepared exclusively for the above-named client',
        'by SS Cooling Tower Consultants. It may not be reproduced, distributed, or',
        'disclosed to any third party without prior written consent of SSCTC.',
    ]:
        canvas.drawCentredString(W / 2, conf_y, line)
        conf_y -= 12

    canvas.restoreState()
