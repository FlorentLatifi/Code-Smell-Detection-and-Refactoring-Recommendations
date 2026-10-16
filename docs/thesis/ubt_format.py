"""The UBT formatting rules, traced to the university's own template.

Every number here comes from one source: `UBT Instruksione per teme_v2 (8) (2)
(6) (2) (1).doc`, supplied by the author on 2026-09-03. Its file metadata records
`Template: UBT Thesis Structure[3]`, i.e. it was itself produced from UBT's
thesis template rather than written free-hand, which is why its page geometry is
trusted here as the template's, not just as one document's habit.

Two kinds of fact live in that file, and they reach this module differently.

**Stated as text**, under its own «INSTRUKSIONE» heading: body text Times New
Roman 12pt, chapter titles Times New Roman 14pt bold capitals, subheadings
Times New Roman 12pt bold, page numbers bottom-right, text justified, line
spacing at least 1.5, every chapter starting on a new page, and three distinct
page-numbering regimes — none on the cover, one running from the Abstract
through the Glossary, another restarting at the first chapter. These transcribe
directly.

**Read from the document's own geometry**, because the instructions never state
it in words: the page is U.S. Letter (612×792pt, confirmed already correct in
this build), and all four margins measure 85.05pt uniformly — 3.00cm to three
decimal places (85.05 / 72in * 2.54cm/in = 3.0004cm). The constants below keep
the value in points rather than converting to `Cm(3.0)`: OOXML stores margins in
twentieths of a point, and 85.05pt lands exactly on that grid (1701 twips)
while `Cm(3.0)` does not (1700.79 twips, which Word then has to round on its
own), so points is the unit the source measurement is actually in and the unit
that survives a save/reload unchanged. Extracted 2026-09-03 via Word COM
automation, since the file is a legacy `.doc` that python-docx cannot open.

The source file is not committed. It is UBT's own instructional document, not
this thesis's content, and it lives outside this repository — a decision
recorded in full, with these values, as VD-62 in `docs/DECISIONS.md`.

`CAPTION_SIZE` is the one constant below the instructions never mention: they
require a numbered caption on every figure and table but never state its size.
11pt was the author's own choice — smaller than body text, as captions
conventionally are — and is kept here unchanged rather than invented a
provenance it doesn't have.

`HEADING_2_SIZE` and `HEADING_3_SIZE` come from a third source, the mentor, who
on 2026-10-16 set Heading 2 to Times New Roman 13pt and Heading 3 to Times New
Roman 12pt, both black, in the mentor's own copy of the thesis (VD-152). The template's
«subheadings 12pt» therefore still holds for Heading 3 and is overridden for
Heading 2, which is one point larger so the two levels can be told apart.

The margins come from the mentor's copy too, and no longer from the template
measurement above. That copy stores 1699 twips (84.95pt, 2.997cm) on every side
instead of 1701, and the author chose to follow it (VD-152). The 0.1pt cannot be
seen, but it decides where pages break: with the template's 1701, heading 5.1 fell
one page later than in the mentor's PDF. The measurement is kept above as the
record of where «3cm» came from.
"""

from __future__ import annotations

from docx.shared import Inches, Pt, Twips

FONT = "Times New Roman"
BODY_SIZE = Pt(12)
TITLE_SIZE = Pt(14)
CAPTION_SIZE = Pt(11)  # not in the instructions; the author's own choice (see above)
HEADING_2_SIZE = Pt(13)  # the mentor's, not the template's (see above)
HEADING_3_SIZE = Pt(12)
MIN_LINE_SPACING = 1.5

PAGE_WIDTH = Inches(8.5)
PAGE_HEIGHT = Inches(11)

# The mentor's 1699 twips, not the template's 1701 (see above).
MARGIN_TOP = Twips(1699)
MARGIN_BOTTOM = Twips(1699)
MARGIN_LEFT = Twips(1699)
MARGIN_RIGHT = Twips(1699)
