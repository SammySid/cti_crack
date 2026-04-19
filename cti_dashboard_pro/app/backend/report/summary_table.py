"""
summary_table.py — Final data & conclusion comparison table page.
"""
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)

from .helpers import section_bar, sub_bar, AVAIL_W
from .styles import TEAL, NAVY, PANEL, PAPER, BORDER2, WHITE


def build_summary_table(payload: dict, styles: dict) -> list:
    story = [Spacer(1, 12)]  # small gap after narrative before section bar

    final_data = payload.get('final_data_table', [])
    data_notes = payload.get('data_notes', [])

    bar   = section_bar('FINAL DATA AND CONCLUSION OF PRE AND POST TEST', styles)
    intro = Paragraph(
        'The following table presents a consolidated comparison of all measured and calculated '
        'parameters across the three test stages conducted during this evaluation.',
        styles['Body'],
    )
    story.append(KeepTogether([bar, Spacer(1, 6), intro]))
    story.append(Spacer(1, 10))

    # ── Main 5-column comparison table ───────────────────────────────────────
    if final_data:
        headers = ['Parameter', 'Unit',
                   'TEST 1\nPre-Test',
                   'TEST 2\nPost Fan Change',
                   'TEST 3\nPost Distr.']
        cw = [AVAIL_W * 0.30, AVAIL_W * 0.11,
              AVAIL_W * 0.19, AVAIL_W * 0.21, AVAIL_W * 0.19]

        tbl_data = [[Paragraph(h, styles['TblHdr']) for h in headers]]
        for row in final_data:
            tbl_data.append([
                Paragraph(str(row.get('name', '\u2014')), styles['TblBodyL']),
                Paragraph(str(row.get('unit', '\u2014')), styles['TblBody']),
                Paragraph(str(row.get('test1', '\u2014')), styles['TblBody']),
                Paragraph(str(row.get('test2', '\u2014')), styles['TblBody']),
                Paragraph(str(row.get('test3', '\u2014')), styles['TblBody']),
            ])

        tbl = Table(tbl_data, colWidths=cw, repeatRows=1)
        cmds = [
            ('BACKGROUND',    (0, 0), (-1, 0),  TEAL),
            ('GRID',          (0, 0), (-1, -1), 0.4, BORDER2),
            ('BOX',           (0, 0), (-1, -1), 1.2, NAVY),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 7),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(final_data) + 1):
            cmds.append(('BACKGROUND', (0, i), (-1, i), PAPER if i % 2 == 0 else WHITE))
        tbl.setStyle(TableStyle(cmds))
        story.append(tbl)
        story.append(Spacer(1, 12))

    # ── Notes panel ───────────────────────────────────────────────────────────
    if data_notes:
        story.append(sub_bar('NOTES', styles))
        note_rows = [
            [Paragraph(f'{i + 1}.  {note}', styles['Body'])]
            for i, note in enumerate(data_notes)
        ]
        notes_body = Table(note_rows, colWidths=[AVAIL_W])
        notes_body.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), PANEL),
            ('BOX',           (0, 0), (-1, -1), 1.0, NAVY),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 14),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(notes_body)
        story.append(Spacer(1, 8))

    story.append(PageBreak())
    return story
