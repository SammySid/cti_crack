"""
narrative.py — Pages 2-N: flowing narrative sections.

All sections flow continuously without forced page breaks between them.
A PageBreak() is appended at the very end to start the analysis section fresh.
"""
from reportlab.platypus import Paragraph, Spacer, PageBreak, KeepTogether

from .helpers import section_bar, sub_bar


def build_narrative(payload: dict, styles: dict) -> list:
    """Return a list of ReportLab flowables for the narrative section."""
    story = []

    def _keep(*items):
        return KeepTogether(list(items))

    # ── PREAMBLE ──────────────────────────────────────────────────────────────
    preamble = payload.get('preamble_paragraphs', [])
    bar = section_bar('PREAMBLE', styles)
    if preamble:
        first = Paragraph(preamble[0], styles['Body'])
        story.append(_keep(bar, Spacer(1, 4), first))
        for p in preamble[1:]:
            story.append(Paragraph(p, styles['Body']))
    else:
        story.append(bar)
    story.append(Spacer(1, 8))

    # ── MEMBERS PRESENT ───────────────────────────────────────────────────────
    members_client = payload.get('members_client', [])
    members_ssctc  = payload.get('members_ssctc', [])

    bar = section_bar('MEMBERS PRESENT FOR THE TEST', styles)
    story.append(_keep(bar, Spacer(1, 4)))

    # CLIENT sub-bar
    c_bar   = sub_bar('CLIENT', styles)
    c_items = [Paragraph(f'\u2022  {m}', styles['Bullet']) for m in members_client]
    if c_items:
        story.append(_keep(c_bar, Spacer(1, 2), c_items[0]))
        for item in c_items[1:]:
            story.append(item)
    else:
        story.append(c_bar)
    story.append(Spacer(1, 5))

    # SSCTC sub-bar
    s_bar   = sub_bar('SS COOLING TOWER CONSULTANTS (SSCTC)', styles)
    s_items = [Paragraph(f'\u2022  {m}', styles['Bullet']) for m in members_ssctc]
    if s_items:
        story.append(_keep(s_bar, Spacer(1, 2), s_items[0]))
        for item in s_items[1:]:
            story.append(item)
    else:
        story.append(s_bar)
    story.append(Spacer(1, 8))

    # ── ASSESSMENT METHOD & ANALYSIS ─────────────────────────────────────────
    assessment = payload.get('assessment_method', [])
    bar = section_bar('ASSESSMENT METHOD & ANALYSIS', styles)
    if assessment:
        first = Paragraph(assessment[0], styles['Body'])
        story.append(_keep(bar, Spacer(1, 4), first))
        for p in assessment[1:]:
            story.append(Paragraph(p, styles['Body']))
    else:
        story.append(bar)
    story.append(Spacer(1, 8))

    # ── INSTRUMENT PLACEMENT AND READINGS ────────────────────────────────────
    instrument = payload.get('instrument_placement', [])
    bar = section_bar('INSTRUMENT PLACEMENT AND READINGS', styles)
    if instrument:
        first = Paragraph(instrument[0], styles['Body'])
        story.append(_keep(bar, Spacer(1, 4), first))
        for p in instrument[1:]:
            story.append(Paragraph(p, styles['Body']))
    else:
        story.append(bar)
    story.append(Spacer(1, 8))

    # ── CONCLUSION AND REMARKS ────────────────────────────────────────────────
    conclusions = payload.get('conclusions', [])
    bar = section_bar('CONCLUSION AND REMARKS', styles)
    if conclusions:
        first = Paragraph(f'1.\u2003{conclusions[0]}', styles['Numbered'])
        story.append(_keep(bar, Spacer(1, 4), first))
        for i, c in enumerate(conclusions[1:], start=2):
            story.append(Paragraph(f'{i}.\u2003{c}', styles['Numbered']))
    else:
        story.append(bar)
    story.append(Spacer(1, 8))

    # ── SUGGESTIONS AND SPECIAL NOTES ────────────────────────────────────────
    suggestions = payload.get('suggestions', [])
    bar = section_bar('SUGGESTIONS AND SPECIAL NOTES', styles)
    if suggestions:
        first = Paragraph(f'1.\u2003{suggestions[0]}', styles['Numbered'])
        story.append(_keep(bar, Spacer(1, 4), first))
        for i, s in enumerate(suggestions[1:], start=2):
            story.append(Paragraph(f'{i}.\u2003{s}', styles['Numbered']))
    else:
        story.append(bar)
    story.append(Spacer(1, 8))

    story.append(PageBreak())
    return story
