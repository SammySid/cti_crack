"""
summary_table.py — Final Data & Conclusion comparison table page.
"""
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)
from reportlab.lib.colors import HexColor

from .helpers import section_bar, AVAIL_W
from .styles import NAVY, PANEL, PAPER, BORDER, WHITE


def build_summary_table(payload: dict, styles: dict) -> list:
    """Return flowables for the final data and conclusion table page."""
    story = []

    final_data = payload.get('final_data_table', [])
    data_notes = payload.get('data_notes', [])

    # Section bar + intro paragraph
    bar = section_bar('FINAL DATA AND CONCLUSION OF PRE AND POST TEST', styles)
    intro = Paragraph(
        'The following table presents a consolidated comparison of all measured and '
        'calculated parameters across the three test stages conducted during this evaluation.',
        styles['Body'],
    )
    story.append(KeepTogether([bar, Spacer(1, 6), intro]))
    story.append(Spacer(1, 10))

    # ── Main comparison table ─────────────────────────────────────────────────
    if final_data:
        headers = [
            'Parameter', 'Unit',
            'TEST 1\nPre-Test',
            'TEST 2\nPost Fan Change',
            'TEST 3\nPost Distr.',
        ]
        cw = [
            AVAIL_W * 0.30,
            AVAIL_W * 0.11,
            AVAIL_W * 0.19,
            AVAIL_W * 0.21,
            AVAIL_W * 0.19,
        ]

        tbl_data = [[Paragraph(h, styles['TblHdr']) for h in headers]]

        for i, row in enumerate(final_data):
            styled_row = [
                Paragraph(str(row.get('name', '\u2014')), styles['TblBodyL']),
                Paragraph(str(row.get('unit', '\u2014')), styles['TblBody']),
                Paragraph(str(row.get('test1', '\u2014')), styles['TblBody']),
                Paragraph(str(row.get('test2', '\u2014')), styles['TblBody']),
                Paragraph(str(row.get('test3', '\u2014')), styles['TblBody']),
            ]
            tbl_data.append(styled_row)

        tbl = Table(tbl_data, colWidths=cw, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0),  NAVY),
            ('GRID',          (0, 0), (-1, -1), 0.5, BORDER),
            ('BOX',           (0, 0), (-1, -1), 1.5, NAVY),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(final_data) + 1):
            bg = PAPER if i % 2 == 0 else WHITE
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)
        story.append(Spacer(1, 12))

    # ── Data notes panel ──────────────────────────────────────────────────────
    if data_notes:
        notes_bar = section_bar('NOTES', styles, indent=10)
        note_items = [
            Paragraph(f'{i + 1}.  {note}', styles['Body'])
            for i, note in enumerate(data_notes)
        ]
        panel_data = [[
            [notes_bar, Spacer(1, 6)] + note_items
        ]]
        panel = Table(panel_data, colWidths=[AVAIL_W])
        panel.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), PANEL),
            ('BOX',           (0, 0), (-1, -1), 1.0, NAVY),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ]))
        story.append(panel)
        story.append(Spacer(1, 8))

    story.append(PageBreak())
    return story
