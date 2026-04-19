"""
narrative.py — Pages 2-N: flowing narrative sections.

Sections flow continuously (no forced breaks between them).
A PageBreak is appended at the end to start the analysis section fresh.
"""
from reportlab.platypus import Paragraph, Spacer, PageBreak, KeepTogether

from .helpers import section_bar, sub_bar


def build_narrative(payload: dict, styles: dict) -> list:
    """Return flowables for all narrative sections."""
    story = []

    def _keep(*items):
        return KeepTogether(list(items))

    # ── PREAMBLE ──────────────────────────────────────────────────────────────
    preamble = payload.get('preamble_paragraphs', [])
    bar = section_bar('PREAMBLE', styles)
    if preamble:
        story.append(_keep(bar, Spacer(1, 5), Paragraph(preamble[0], styles['Body'])))
        for p in preamble[1:]:
            story.append(Paragraph(p, styles['Body']))
    else:
        story.append(bar)
    story.append(Spacer(1, 10))

    # ── MEMBERS PRESENT ───────────────────────────────────────────────────────
    members_client = payload.get('members_client', [])
    members_ssctc  = payload.get('members_ssctc', [])

    bar = section_bar('MEMBERS PRESENT FOR THE TEST', styles)
    story.append(_keep(bar, Spacer(1, 5)))

    c_bar   = sub_bar('CLIENT', styles)
    c_items = [Paragraph(f'\u2022  {m}', styles['Bullet']) for m in members_client]
    if c_items:
        story.append(_keep(c_bar, Spacer(1, 3), c_items[0]))
        for item in c_items[1:]:
            story.append(item)
    else:
        story.append(c_bar)
    story.append(Spacer(1, 6))

    s_bar   = sub_bar('SS COOLING TOWER CONSULTANTS (SSCTC)', styles)
    s_items = [Paragraph(f'\u2022  {m}', styles['Bullet']) for m in members_ssctc]
    if s_items:
        story.append(_keep(s_bar, Spacer(1, 3), s_items[0]))
        for item in s_items[1:]:
            story.append(item)
    else:
        story.append(s_bar)
    story.append(Spacer(1, 10))

    # ── ASSESSMENT METHOD & ANALYSIS ─────────────────────────────────────────
    assessment = payload.get('assessment_method', [])
    bar = section_bar('ASSESSMENT METHOD & ANALYSIS', styles)
    if assessment:
        story.append(_keep(bar, Spacer(1, 5), Paragraph(assessment[0], styles['Body'])))
        for p in assessment[1:]:
            story.append(Paragraph(p, styles['Body']))
    else:
        story.append(bar)
    story.append(Spacer(1, 10))

    # ── INSTRUMENT PLACEMENT AND READINGS ────────────────────────────────────
    instrument = payload.get('instrument_placement', [])
    bar = section_bar('INSTRUMENT PLACEMENT AND READINGS', styles)
    if instrument:
        story.append(_keep(bar, Spacer(1, 5), Paragraph(instrument[0], styles['Body'])))
        for p in instrument[1:]:
            story.append(Paragraph(p, styles['Body']))
    else:
        story.append(bar)
    story.append(Spacer(1, 10))

    # ── CONCLUSION AND REMARKS ────────────────────────────────────────────────
    conclusions = payload.get('conclusions', [])
    bar = section_bar('CONCLUSION AND REMARKS', styles)
    if conclusions:
        first = Paragraph(f'1.\u2003{conclusions[0]}', styles['Numbered'])
        story.append(_keep(bar, Spacer(1, 5), first))
        for i, c in enumerate(conclusions[1:], start=2):
            story.append(Paragraph(f'{i}.\u2003{c}', styles['Numbered']))
    else:
        story.append(bar)
    story.append(Spacer(1, 10))

    # ── SUGGESTIONS AND SPECIAL NOTES ────────────────────────────────────────
    suggestions = payload.get('suggestions', [])
    bar = section_bar('SUGGESTIONS AND SPECIAL NOTES', styles)
    if suggestions:
        first = Paragraph(f'1.\u2003{suggestions[0]}', styles['Numbered'])
        story.append(_keep(bar, Spacer(1, 5), first))
        for i, s in enumerate(suggestions[1:], start=2):
            story.append(Paragraph(f'{i}.\u2003{s}', styles['Numbered']))
    else:
        story.append(bar)
    story.append(Spacer(1, 10))

    return story
