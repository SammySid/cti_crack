"""
styles.py — All colour constants and ParagraphStyle definitions.
"""
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = HexColor('#1e3a5f')   # Section bars, table headers, borders
BLUE   = HexColor('#1d4ed8')   # STEP badge background, accent borders
SKY    = HexColor('#dbeafe')   # Asset block background, light row highlight
STEEL  = HexColor('#e0eaf8')   # Sub-section bar background
PAPER  = HexColor('#f8fafc')   # Alternating table row background
PANEL  = HexColor('#f0f6ff')   # Result card, calc panel background
SLATE  = HexColor('#475569')   # Secondary body text
LIGHT  = HexColor('#64748b')   # Footer, captions, labels
BORDER = HexColor('#cbd5e1')   # Table cell borders
RED    = HexColor('#b91c1c')   # CWT Shortfall value
WHITE  = colors.white
BLACK  = HexColor('#0f172a')
BODY_COLOR = HexColor('#1e293b')

COLORS = {
    'NAVY': NAVY, 'BLUE': BLUE, 'SKY': SKY, 'STEEL': STEEL,
    'PAPER': PAPER, 'PANEL': PANEL, 'SLATE': SLATE, 'LIGHT': LIGHT,
    'BORDER': BORDER, 'RED': RED, 'WHITE': WHITE, 'BLACK': BLACK,
}


def build_styles() -> dict:
    """Build and return all ParagraphStyles keyed by name."""
    base = getSampleStyleSheet()
    S = {}

    # Body text
    S['Body'] = ParagraphStyle(
        'Body', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=BODY_COLOR, leading=14,
        spaceAfter=5,
    )

    # Section bar (white on navy)
    S['SectionBar'] = ParagraphStyle(
        'SectionBar', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9.5,
        textColor=WHITE, leading=14,
    )

    # Sub-section bar (white on steel-blue)
    S['SubBar'] = ParagraphStyle(
        'SubBar', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=WHITE, leading=13,
    )

    # STEP badge (centered, white on BLUE)
    S['StepBadge'] = ParagraphStyle(
        'StepBadge', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=7,
        textColor=WHITE, leading=10,
        alignment=TA_CENTER,
    )

    # Step title (bold, navy, right of badge)
    S['StepTitle'] = ParagraphStyle(
        'StepTitle', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=NAVY, leading=13,
    )

    # Step description paragraph
    S['StepDesc'] = ParagraphStyle(
        'StepDesc', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY_COLOR, leading=14,
        leftIndent=14, spaceBefore=4, spaceAfter=8,
    )

    # Table header (white on NAVY)
    S['TblHdr'] = ParagraphStyle(
        'TblHdr', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=WHITE, leading=13,
        alignment=TA_CENTER,
    )

    # Table body (centered)
    S['TblBody'] = ParagraphStyle(
        'TblBody', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY_COLOR, leading=13,
        alignment=TA_CENTER,
    )

    # Table body (left-aligned, first column)
    S['TblBodyL'] = ParagraphStyle(
        'TblBodyL', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY_COLOR, leading=13,
        alignment=TA_LEFT,
    )

    # Image/figure caption
    S['Caption'] = ParagraphStyle(
        'Caption', parent=base['Normal'],
        fontName='Helvetica-Oblique', fontSize=7,
        textColor=SLATE, leading=10,
        alignment=TA_CENTER, spaceAfter=4,
    )

    # Result card label
    S['RcLabel'] = ParagraphStyle(
        'RcLabel', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8,
        textColor=NAVY, leading=11,
        alignment=TA_CENTER, spaceBefore=2,
    )

    # Result card value — red (CWT shortfall)
    S['RcValueRed'] = ParagraphStyle(
        'RcValueRed', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=22,
        textColor=RED, leading=28,
        alignment=TA_CENTER,
    )

    # Result card value — blue (capability %)
    S['RcValueBlue'] = ParagraphStyle(
        'RcValueBlue', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=22,
        textColor=BLUE, leading=28,
        alignment=TA_CENTER,
    )

    # Result card sub-text
    S['RcSub'] = ParagraphStyle(
        'RcSub', parent=base['Normal'],
        fontName='Helvetica', fontSize=7,
        textColor=SLATE, leading=10,
        alignment=TA_CENTER, spaceAfter=2,
    )

    # Result card / section header (white on NAVY)
    S['CardHeader'] = ParagraphStyle(
        'CardHeader', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=WHITE, leading=14,
    )

    # Result summary bar (bold text on SKY background)
    S['ResultSummary'] = ParagraphStyle(
        'ResultSummary', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=NAVY, leading=14,
        alignment=TA_CENTER, spaceAfter=4,
    )

    # Cover: top company name (white)
    S['CoverCompany'] = ParagraphStyle(
        'CoverCompany', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=15,
        textColor=WHITE, leading=20,
        alignment=TA_CENTER,
    )

    # Cover: tagline (light blue)
    S['CoverTagline'] = ParagraphStyle(
        'CoverTagline', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=HexColor('#93c5fd'), leading=13,
        alignment=TA_CENTER,
    )

    # Cover: main report title
    S['CoverTitle'] = ParagraphStyle(
        'CoverTitle', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=20,
        textColor=NAVY, leading=26,
        alignment=TA_CENTER, spaceAfter=8,
    )

    # Cover: sub-title
    S['CoverSubTitle'] = ParagraphStyle(
        'CoverSubTitle', parent=base['Normal'],
        fontName='Helvetica', fontSize=10,
        textColor=SLATE, leading=15,
        alignment=TA_CENTER, spaceAfter=16,
    )

    # Cover: asset name
    S['CoverAsset'] = ParagraphStyle(
        'CoverAsset', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=14,
        textColor=NAVY, leading=20,
        alignment=TA_CENTER,
    )

    # Cover: metadata label (left col)
    S['CoverMetaLabel'] = ParagraphStyle(
        'CoverMetaLabel', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5,
        textColor=NAVY, leading=13,
    )

    # Cover: metadata value (right col)
    S['CoverMetaValue'] = ParagraphStyle(
        'CoverMetaValue', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=BODY_COLOR, leading=13,
    )

    # Cover: confidentiality notice (italic, slate)
    S['CoverNote'] = ParagraphStyle(
        'CoverNote', parent=base['Normal'],
        fontName='Helvetica-Oblique', fontSize=7.5,
        textColor=SLATE, leading=12,
        alignment=TA_CENTER,
    )

    # Bullet list item
    S['Bullet'] = ParagraphStyle(
        'Bullet', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=BODY_COLOR, leading=14,
        leftIndent=16, firstLineIndent=-8, spaceAfter=2,
    )

    # Numbered list item
    S['Numbered'] = ParagraphStyle(
        'Numbered', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=BODY_COLOR, leading=14,
        leftIndent=20, firstLineIndent=-14, spaceAfter=3,
    )

    # End of report title
    S['EndTitle'] = ParagraphStyle(
        'EndTitle', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=14,
        textColor=SLATE, leading=20,
        alignment=TA_CENTER, spaceBefore=20, spaceAfter=10,
    )

    # End of report sub-line
    S['EndSub'] = ParagraphStyle(
        'EndSub', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=LIGHT, leading=14,
        alignment=TA_CENTER,
    )

    # Calc panel label
    S['CalcLabel'] = ParagraphStyle(
        'CalcLabel', parent=base['Normal'],
        fontName='Helvetica', fontSize=8,
        textColor=SLATE, leading=12,
    )

    # Calc panel value (right-aligned, bold)
    S['CalcValue'] = ParagraphStyle(
        'CalcValue', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5,
        textColor=NAVY, leading=12,
        alignment=TA_RIGHT,
    )

    return S
