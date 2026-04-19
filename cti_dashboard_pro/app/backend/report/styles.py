"""
styles.py — Full colour palette + all ParagraphStyle definitions.

Design system: Deep Navy  #0d2137
               Teal       #0e7490  (sub-bars, table headers, step badges, borders)
               Gold       #b45309  (title rule, conclusion-card accent)
"""
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Colour palette ─────────────────────────────────────────────────────────────
NAVY    = HexColor('#0d2137')   # Deep navy — section bars, page chrome
TEAL    = HexColor('#0e7490')   # Teal — sub-bars, table headers, step badges
TEAL_LT = HexColor('#0891b2')   # Lighter teal — step-header panel bg border
GOLD    = HexColor('#b45309')   # Amber gold — title rule, conclusion accent
SKY     = HexColor('#ecfeff')   # Pale cyan — asset block, summary-bar bg
PANEL   = HexColor('#f0f9ff')   # Pale blue — step desc bg, calc panel, card
PAPER   = HexColor('#f8fafc')   # Off-white — alternating table row
BORDER  = HexColor('#bae6fd')   # Light teal border
BORDER2 = HexColor('#cbd5e1')   # Subtle grey border
BODY    = HexColor('#1e293b')   # Body text
MUTED   = HexColor('#64748b')   # Captions, footer, labels
RED     = HexColor('#be123c')   # CWT shortfall value
BLUE    = HexColor('#1d4ed8')   # Capability % value
WHITE   = colors.white
BLACK   = HexColor('#0f172a')
TAGLINE = HexColor('#7dd3fc')   # Light-blue tagline on dark bands

COLORS = {
    'NAVY': NAVY, 'TEAL': TEAL, 'GOLD': GOLD, 'SKY': SKY,
    'PANEL': PANEL, 'PAPER': PAPER, 'BORDER': BORDER,
    'BODY': BODY, 'MUTED': MUTED, 'RED': RED, 'BLUE': BLUE,
    'WHITE': WHITE, 'BLACK': BLACK,
}

# Keep legacy aliases so any code that imports old names still works
STEEL  = HexColor('#e0eaf8')
SLATE  = MUTED
LIGHT  = MUTED
BORDER_OLD = BORDER2
BODY_COLOR = BODY


def build_styles() -> dict:
    """Return all ParagraphStyles keyed by name."""
    base = getSampleStyleSheet()
    S = {}

    # ── Body / general ─────────────────────────────────────────────────────────
    S['Body'] = ParagraphStyle(
        'Body', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=BODY, leading=14, spaceAfter=5,
    )

    # ── Section bars ───────────────────────────────────────────────────────────
    S['SectionBar'] = ParagraphStyle(          # navy bar, white bold text
        'SectionBar', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=WHITE, leading=15,
    )
    S['SubBar'] = ParagraphStyle(              # teal bar, white bold text
        'SubBar', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=WHITE, leading=13,
    )

    # ── Step elements ──────────────────────────────────────────────────────────
    S['StepBadge'] = ParagraphStyle(           # "STEP N" badge (teal bg)
        'StepBadge', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8,
        textColor=WHITE, leading=11, alignment=TA_CENTER,
    )
    S['StepTitle'] = ParagraphStyle(           # step title (right of badge)
        'StepTitle', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9.5,
        textColor=NAVY, leading=14,
    )
    S['StepDesc'] = ParagraphStyle(            # step description paragraph
        'StepDesc', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY, leading=14,
        leftIndent=14, spaceBefore=4, spaceAfter=8,
    )

    # ── Table ─────────────────────────────────────────────────────────────────
    S['TblHdr'] = ParagraphStyle(              # white on teal header
        'TblHdr', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5,
        textColor=WHITE, leading=12, alignment=TA_CENTER,
    )
    S['TblBody'] = ParagraphStyle(             # body cell (centred)
        'TblBody', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY, leading=12, alignment=TA_CENTER,
    )
    S['TblBodyL'] = ParagraphStyle(            # body cell (left, first col)
        'TblBodyL', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY, leading=12, alignment=TA_LEFT,
    )

    # ── Misc ──────────────────────────────────────────────────────────────────
    S['Caption'] = ParagraphStyle(
        'Caption', parent=base['Normal'],
        fontName='Helvetica-Oblique', fontSize=7,
        textColor=MUTED, leading=10, alignment=TA_CENTER, spaceAfter=4,
    )
    S['Bullet'] = ParagraphStyle(
        'Bullet', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=BODY, leading=14,
        leftIndent=16, firstLineIndent=-8, spaceAfter=2,
    )
    S['Numbered'] = ParagraphStyle(
        'Numbered', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=BODY, leading=14,
        leftIndent=20, firstLineIndent=-14, spaceAfter=3,
    )

    # ── Result card ───────────────────────────────────────────────────────────
    S['CardHeader'] = ParagraphStyle(
        'CardHeader', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=WHITE, leading=14,
    )
    S['RcLabel'] = ParagraphStyle(
        'RcLabel', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8,
        textColor=NAVY, leading=11, alignment=TA_CENTER, spaceBefore=2,
    )
    S['RcValueRed'] = ParagraphStyle(
        'RcValueRed', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=26,
        textColor=RED, leading=32, alignment=TA_CENTER,
    )
    S['RcValueBlue'] = ParagraphStyle(
        'RcValueBlue', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=26,
        textColor=BLUE, leading=32, alignment=TA_CENTER,
    )
    S['RcSub'] = ParagraphStyle(
        'RcSub', parent=base['Normal'],
        fontName='Helvetica', fontSize=7.5,
        textColor=MUTED, leading=10, alignment=TA_CENTER, spaceAfter=2,
    )
    S['ResultSummary'] = ParagraphStyle(
        'ResultSummary', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=NAVY, leading=14, alignment=TA_CENTER, spaceAfter=4,
    )

    # ── Calc panel ────────────────────────────────────────────────────────────
    S['CalcLabel'] = ParagraphStyle(
        'CalcLabel', parent=base['Normal'],
        fontName='Helvetica', fontSize=8,
        textColor=MUTED, leading=12,
    )
    S['CalcValue'] = ParagraphStyle(
        'CalcValue', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5,
        textColor=NAVY, leading=12, alignment=TA_RIGHT,
    )

    # ── Cover ─────────────────────────────────────────────────────────────────
    S['CoverCompany'] = ParagraphStyle(
        'CoverCompany', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=15,
        textColor=WHITE, leading=20, alignment=TA_CENTER,
    )
    S['CoverTagline'] = ParagraphStyle(
        'CoverTagline', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=TAGLINE, leading=13, alignment=TA_CENTER,
    )
    S['CoverTitle'] = ParagraphStyle(
        'CoverTitle', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=22,
        textColor=NAVY, leading=28, alignment=TA_CENTER, spaceAfter=6,
    )
    S['CoverSubTitle'] = ParagraphStyle(
        'CoverSubTitle', parent=base['Normal'],
        fontName='Helvetica', fontSize=10,
        textColor=MUTED, leading=15, alignment=TA_CENTER, spaceAfter=16,
    )
    S['CoverAsset'] = ParagraphStyle(
        'CoverAsset', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=16,
        textColor=NAVY, leading=22, alignment=TA_CENTER,
    )
    S['CoverMetaLabel'] = ParagraphStyle(
        'CoverMetaLabel', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5,
        textColor=TEAL, leading=13,
    )
    S['CoverMetaValue'] = ParagraphStyle(
        'CoverMetaValue', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY, leading=13,
    )
    S['CoverNote'] = ParagraphStyle(
        'CoverNote', parent=base['Normal'],
        fontName='Helvetica-Oblique', fontSize=7.5,
        textColor=MUTED, leading=12, alignment=TA_CENTER,
    )

    # ── End of report ─────────────────────────────────────────────────────────
    S['EndTitle'] = ParagraphStyle(
        'EndTitle', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=14,
        textColor=MUTED, leading=20, alignment=TA_CENTER,
        spaceBefore=20, spaceAfter=10,
    )
    S['EndSub'] = ParagraphStyle(
        'EndSub', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=HexColor('#94a3b8'), leading=14, alignment=TA_CENTER,
    )

    return S
