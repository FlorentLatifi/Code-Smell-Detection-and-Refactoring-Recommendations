"""Verifikon që dokumenti i gjeneruar i përmbahet formatimit që kërkon UBT-ja.

    python docs/thesis/check_format.py [shtegu.docx]

`build_thesis.py` i zbaton këto rregulla; ky skript i **verifikon te skedari**, dhe
dallimi është i tërë qëllimi. Dokumenti nuk mbetet ashtu si u gjenerua: docstring-u
i ndërtuesit e thotë vetë se redaktimi i mëtejshëm bëhet në Word. Një rresht i
ngjitur nga diku tjetër e sjell fontin e vet, një titull i shtuar me dorë nuk merr
stilin e kreut, dhe asnjëra prej të dyjave nuk duket ndryshe në ekran derisa dikush
i mat. Komisioni e vlerëson përputhshmërinë me shabllonin, ndaj ato dallime
kushtojnë pikë.

Rregullat e kontrolluara vijnë nga `ubt_format.py`, jo nga `build_thesis.py`. Deri
më VD-62 vinin që andej, çka do të thoshte se ky kontroll verifikonte dokumentin
kundrejt vetes së ndërtuesit — një ndryshim aksidental i njërës do ta ndiqte
tjetra pa u vënë re. `ubt_format.py` i nxjerr nga vetë shablloni i UBT-së dhe
importohet nga të dy anët, ndaj tani janë dy zbatime të pavarura të të njëjtit
burim, jo njëri kontroll i tjetrit.

Rregullat: Times New Roman kudo; tekst 12pt i drejtuar me hapësirë rreshtash së
paku 1.5; tituj kapitujsh 14pt bold me shkronja kapitale, secili në faqe të re;
nëntituj 13pt (Heading 2) dhe 12pt (Heading 3) bold e të zinj, siç i caktoi
mentorja; përshkrime figurash e tituj tabelash 11pt në qendër, të numëruar pa
hapësira me fusha SEQ; tri regjime numërimi faqesh; numri i faqes poshtë djathtas;
faqe Letter (8.5×11 inç) me margjina 3cm nga të katër anët. Kontrollohet edhe që
lista e figurave dhe e tabelave në fillim të jenë fusha që Word-i i mbush nga
përshkrimet, dhe që rezultati i tyre të përputhet me atë që dokumenti përmban
vërtet; që citimet IEEE të numërohen sipas radhës së citimit të parë; dhe që
kopertinat të mos kenë paragraf bosh me ndërprerje faqeje (VD-152).

Kontrollohen edhe numërimi i njëpasnjëshëm i nënkapitujve dhe mungesa e krerëve pa
përmbajtje. Në fund listohen vendet `[PLOTËSO]` që i mbeten autorit: ato janë të
shënuara me qëllim dhe nuk e rrëzojnë kontrollin, por në një dokument prej dhjetëra
faqesh gjenden vetëm nga kush di t'i kërkojë.

Del me kod jo-zero po qe se ndonjë rregull thyhet, që kontrolli të mund të hyjë në
CI bashkë me atë të citimeve.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from build_thesis import FRONT_TITLE, OUTPUT
from check_citations import CITATION
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph
from ubt_format import (
    BODY_SIZE,
    CAPTION_SIZE,
    FONT,
    HEADING_2_SIZE,
    HEADING_3_SIZE,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    MIN_LINE_SPACING,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    TITLE_SIZE,
)

# Numërimi i tri regjimeve, sipas radhës së seksioneve: kopertina pa numra, ballina
# me romakë duke filluar nga I, kapitujt me arabë duke rifilluar nga 1.
EXPECTED_SECTIONS = (
    {"fmt": None, "start": None, "footer": False},
    {"fmt": "upperRoman", "start": "1", "footer": True},
    {"fmt": "decimal", "start": "1", "footer": True},
)

CAPTION = re.compile(r"^(Figura|Tabela) (\d+)\.")
CHAPTER_HEADING = re.compile(r"^\d+ ")

# Numri i faqes që Word-i i shton një hyrjeje të listës kur e rifreskon fushën.
PAGE_SUFFIX = re.compile(r"\t\S*$")

# Një citim IEEE në tekst, «[5]» ose «[5, p. 80]». «[?]» është citimi që ndërtimi nuk e
# gjeti në listë.
NUMERIC_CITATION = re.compile(r"\[(\d+|\?)(?:, p\. \d+)?\]")
# Hyrja e listës: «[5]», tabulatori, pastaj teksti.
REFERENCE_ENTRY = re.compile(r"^\[(\d+)\]\t")


def _size_ok(run, expected: Pt) -> bool:
    """Madhësia e shkronjave, duke lejuar trashëgiminë nga stili.

    `None` do të thotë «merre nga stili», dhe stilet i verifikon `_check_styles`.
    Kërkesa që çdo run ta mbajë vetë vlerën do të shënonte si gabim tekstin që Word
    e formaton saktë përmes stilit.
    """
    return run.font.size is None or run.font.size == expected


def _check_styles(doc: Document) -> list[str]:
    problems = []
    normal = doc.styles["Normal"]
    if normal.font.name != FONT:
        problems.append(f"stili Normal nuk është {FONT} por {normal.font.name}")
    if normal.font.size != BODY_SIZE:
        problems.append(f"stili Normal nuk është {BODY_SIZE.pt:g}pt")
    spacing = normal.paragraph_format.line_spacing
    if spacing < MIN_LINE_SPACING:
        problems.append(f"stili Normal ka hapësirë rreshtash {spacing}")

    for name, size, caps in (
        ("Heading 1", TITLE_SIZE, True),
        ("Heading 2", HEADING_2_SIZE, False),
        ("Heading 3", HEADING_3_SIZE, False),
    ):
        style = doc.styles[name]
        if style.font.name != FONT:
            problems.append(f"stili {name} nuk është {FONT}")
        if style.font.size != size:
            problems.append(f"stili {name} nuk është {size.pt:g}pt")
        if not style.font.bold:
            problems.append(f"stili {name} nuk është bold")
        if bool(style.font.all_caps) != caps:
            problems.append(f"stili {name} me all_caps={style.font.all_caps}, pritej {caps}")
        if style.paragraph_format.alignment != WD_ALIGN_PARAGRAPH.LEFT:
            problems.append(f"stili {name} nuk është i rreshtuar majtas")
        # Stilet e titujve të shabllonit të Word-it janë blu; mentorja i do të zinj.
        if style.font.color.type is not None and style.font.color.rgb != RGBColor(0, 0, 0):
            problems.append(f"stili {name} nuk është i zi")

    front = doc.styles[FRONT_TITLE]
    if front.font.name != FONT or front.font.size != TITLE_SIZE:
        problems.append(f"stili {FRONT_TITLE} nuk është {FONT} {TITLE_SIZE.pt:g}pt")
    if not front.font.bold or not front.font.all_caps:
        problems.append(f"stili {FRONT_TITLE} nuk është bold me shkronja kapitale")
    ppr = front.element.pPr
    if ppr is not None and ppr.find(qn("w:outlineLvl")) is not None:
        problems.append(f"stili {FRONT_TITLE} ka nivel skicimi, ndaj hyn në përmbajtje")
    return problems


def _check_fonts(doc: Document) -> list[str]:
    """Asnjë run me font tjetër, as në paragrafë as brenda qelizave të tabelave."""
    problems = []
    runs = [(p, r) for p in doc.paragraphs for r in p.runs]
    for grid in doc.tables:
        for row in grid.rows:
            for cell in row.cells:
                runs += [(p, r) for p in cell.paragraphs for r in p.runs]

    for paragraph, run in runs:
        if run.font.name not in (None, FONT):
            excerpt = (paragraph.text or run.text)[:40]
            problems.append(f"font {run.font.name} te «{excerpt}»")
    return problems


def _check_body(doc: Document) -> list[str]:
    """Teksti rrjedhës: 12pt, i drejtuar, me hapësirë rreshtash së paku 1.5."""
    problems = []
    for paragraph in doc.paragraphs:
        if not paragraph.text.strip() or paragraph.style.name != "Normal":
            continue
        if CAPTION.match(paragraph.text) or paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
            continue  # përshkrimet dhe kopertina kontrollohen veç
        excerpt = paragraph.text[:40]
        # Hyrjet e referencave, të njohura nga dhëmbëzimi i varur, janë majtas me
        # qëllim: një DOI i gjatë në fund të një rreshti të justifikuar i hap fjalët
        # para tij me boshllëqe të mëdha.
        first_line = paragraph.paragraph_format.first_line_indent
        hanging = first_line is not None and first_line < 0
        if paragraph.alignment not in (None, WD_ALIGN_PARAGRAPH.JUSTIFY) and not hanging:
            problems.append(f"paragraf i pa-drejtuar te «{excerpt}»")
        spacing = paragraph.paragraph_format.line_spacing
        if spacing is not None and spacing < MIN_LINE_SPACING:
            problems.append(f"hapësirë rreshtash {spacing} te «{excerpt}»")
        for run in paragraph.runs:
            if not _size_ok(run, BODY_SIZE):
                problems.append(f"madhësi {run.font.size.pt:g}pt te «{excerpt}»")
                break
    return problems


def _split_at_first_chapter(doc: Document) -> tuple[list, list]:
    """Ballina dhe trupi, të ndarë te kreu i Kapitullit 1.

    Ndarja nevojitet sepse te ballina rreshtat e listës së figurave dhe të tabelave
    e kanë të njëjtin tekst me përshkrimet e vërteta. Ata janë tekst rrjedhës e jo
    përshkrime, ndaj matja e tyre me rregullat e përshkrimit do të raportonte njëzet
    e një gabime që nuk ekzistojnë.
    """
    for index, paragraph in enumerate(doc.paragraphs):
        if paragraph.style.name == "Heading 1" and CHAPTER_HEADING.match(paragraph.text):
            return doc.paragraphs[:index], doc.paragraphs[index:]
    return doc.paragraphs, []


def _captions(doc: Document) -> list:
    """Përshkrimet e vërteta: ato brenda kapitujve, jo rreshtat e listave."""
    _, body_paragraphs = _split_at_first_chapter(doc)
    return [p for p in body_paragraphs if CAPTION.match(p.text)]


def _field_codes(paragraph) -> str:
    """Kodet e fushave të një paragrafi, «SEQ Figura \\* ARABIC», si një varg."""
    return " ".join(instr.text or "" for instr in paragraph._p.iter(qn("w:instrText")))


def _check_captions(doc: Document) -> list[str]:
    """Përshkrimet: në qendër, 11pt, dhe me numrin si fushë SEQ të llojit të vet.

    Lista e figurave dhe e tabelave i mbledh vetëm përshkrimet që kanë fushën: një
    përshkrim i shtypur me dorë në Word do të dukej njësoj, por do të mungonte në
    listë pa e vënë re askush.
    """
    problems = []
    for paragraph in _captions(doc):
        if paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER:
            problems.append(f"përshkrim jo në qendër: «{paragraph.text[:40]}»")
        for run in paragraph.runs:
            if not _size_ok(run, CAPTION_SIZE):
                problems.append(f"përshkrim {run.font.size.pt:g}pt: «{paragraph.text[:40]}»")
                break
        kind = CAPTION.match(paragraph.text).group(1)
        if f"SEQ {kind}" not in _field_codes(paragraph):
            problems.append(f"përshkrim pa fushën SEQ {kind}: «{paragraph.text[:40]}»")
    return problems


# Shenjat e Markdown-it që nuk guxojnë të mbërrijnë te faqja. Yjet e dyfishta i
# rendereron `body()` si të theksuara, ndaj një mbetje aty do të thotë shenjë e
# pambyllur. Backtick-u nuk renderohet dot fare: dokumenti lejon një font të
# vetëm, pra nuk ka monospace ku ta shndërrosh, dhe konventa e këtij punimi për
# identifikuesit janë thonjëzat «».
MARKERS = ("**", "`")


def _check_markup(doc: Document) -> list[str]:
    """No Markdown marker may survive into the page.

    The chapters are written with ``**emphasis**`` and the builder turns it into
    bold runs. When that failed, four paragraphs reached the document with the
    asterisks visible and every other check still passed: fonts, sizes,
    numbering and captions were all correct, and none of them reads punctuation.
    This is the check that would have caught it.
    """
    problems = []
    for marker in MARKERS:
        for paragraph in doc.paragraphs:
            if marker in paragraph.text:
                start = max(0, paragraph.text.index(marker) - 30)
                problems.append(f"shenjë «{marker}» e mbetur te «{paragraph.text[start:][:70]}»")
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if marker in cell.text:
                        problems.append(f"shenjë «{marker}» e mbetur te qeliza «{cell.text[:50]}»")
    return problems


def _check_numbering(doc: Document) -> list[str]:
    """Numrat e figurave dhe të tabelave ecin 1, 2, 3 sipas radhës së shfaqjes.

    Shablloni e kërkon numërimin sipas radhës ku lexuesi i takon. Kontrolli e ka
    kapur dokumentin duke e hapur me «Figura 5», sepse numrat ndiqnin radhën në të
    cilën ishin gjeneruar figurat, jo radhën e leximit.
    """
    problems = []
    counters = {"Figura": 0, "Tabela": 0}
    for paragraph in _captions(doc):
        match = CAPTION.match(paragraph.text)
        assert match is not None
        kind, number = match.group(1), int(match.group(2))
        counters[kind] += 1
        if number != counters[kind]:
            problems.append(f"{kind} {number} aty ku pritej {counters[kind]}")
    return problems


def _check_lists(doc: Document) -> list[str]:
    """Listat e ballinës janë fusha mbi përshkrimet, dhe përputhen me to.

    Që nga VD-152 secila listë është një fushë TOC `\\c` që Word-i e mbush nga fushat
    SEQ të përshkrimeve, si përmbajtjen nga titujt. Ndërtimi e shkruan rezultatin e
    fushës vetë, me të njëjtën ecje që bën renderimi, por nga një kalim tjetër mbi
    kapitujt; krahasimi verifikon se dy kalimet pajtohen. Pasi Word-i e rifreskon
    fushën, çdo hyrje merr pas një tabulatori numrin e faqes, që këtu hiqet.
    """
    front, _ = _split_at_first_chapter(doc)
    codes = " ".join(_field_codes(p) for p in front)
    problems = []
    for kind in ("Figura", "Tabela"):
        if not re.search(rf'TOC\s[^"]*\\c\s+"{kind}"', codes):
            problems.append(f'lista për «{kind}» nuk është fushë TOC \\c "{kind}"')
    declared = [PAGE_SUFFIX.sub("", p.text) for p in front if CAPTION.match(p.text)]
    actual = [p.text for p in _captions(doc)]
    for missing in sorted(set(declared) - set(actual)):
        problems.append(f"e listuar në ballinë por s'del në tekst: «{missing}»")
    for extra in sorted(set(actual) - set(declared)):
        problems.append(f"del në tekst por mungon në listën e ballinës: «{extra}»")
    return problems


def _check_sections(doc: Document) -> list[str]:
    problems = []
    if len(doc.sections) != len(EXPECTED_SECTIONS):
        return [f"{len(doc.sections)} seksione, pritej {len(EXPECTED_SECTIONS)}"]

    for index, (section, expected) in enumerate(zip(doc.sections, EXPECTED_SECTIONS, strict=True)):
        pg_num = section._sectPr.find(qn("w:pgNumType"))
        fmt = pg_num.get(qn("w:fmt")) if pg_num is not None else None
        start = pg_num.get(qn("w:start")) if pg_num is not None else None
        if fmt != expected["fmt"] or start != expected["start"]:
            problems.append(
                f"seksioni {index + 1}: numërim {fmt}/{start}, "
                f"pritej {expected['fmt']}/{expected['start']}"
            )

        footer = section.footer.paragraphs[0]
        has_field = "PAGE" in footer._p.xml
        if has_field != expected["footer"]:
            problems.append(
                f"seksioni {index + 1}: numër faqeje {has_field}, pritej {expected['footer']}"
            )
        if has_field and footer.alignment != WD_ALIGN_PARAGRAPH.RIGHT:
            problems.append(f"seksioni {index + 1}: numri i faqes nuk është djathtas")
    return problems


def _check_geometry(doc: Document) -> list[str]:
    """Madhësia e faqes dhe margjinat, në çdo seksion.

    `add_section` i trashëgon nga seksioni paraprak, ndaj një gabim këtu do të
    thotë se dikush e ka mbivendosur me dorë gjatë redaktimit, jo se ndërtuesi
    e ka humbur trashëgimin.
    """
    problems = []
    for index, section in enumerate(doc.sections):
        if section.page_width != PAGE_WIDTH or section.page_height != PAGE_HEIGHT:
            problems.append(
                f"seksioni {index + 1}: faqe {section.page_width} x "
                f"{section.page_height}, pritej {PAGE_WIDTH} x {PAGE_HEIGHT}"
            )
        margins = {
            "sipër": (section.top_margin, MARGIN_TOP),
            "poshtë": (section.bottom_margin, MARGIN_BOTTOM),
            "majtas": (section.left_margin, MARGIN_LEFT),
            "djathtas": (section.right_margin, MARGIN_RIGHT),
        }
        for side, (actual, expected) in margins.items():
            if actual != expected:
                problems.append(
                    f"seksioni {index + 1}: margjina {side} {actual}, pritej {expected}"
                )
    return problems


# Shablloni: «LISTA E TABELAVE ... Vjen menjeherë pas listës së figurave (nuk fillon
# në faqe të re)». Çdo titull tjetër fillon në faqe të re.
SAME_PAGE_TITLE = "Lista e tabelave"


def _check_page_breaks(doc: Document) -> list[str]:
    """Çdo titull fillon në faqe të re, përveç listës së tabelave."""
    problems = []
    for paragraph in doc.paragraphs:
        if paragraph.style.name not in ("Heading 1", FRONT_TITLE):
            continue
        breaks = bool(paragraph.paragraph_format.page_break_before)
        if paragraph.text.strip() == SAME_PAGE_TITLE:
            if breaks:
                problems.append(f"«{SAME_PAGE_TITLE}» fillon në faqe të re, shablloni nuk e do")
        elif not breaks:
            problems.append(f"kreu pa ndarje faqeje: «{paragraph.text[:40]}»")
    return problems


# Shablloni: «Abstrakti dhe mirënjohja nuk paraqiten në përmbajtje», ndërsa listat
# dhe fjalori «duhet të paraqiten në përmbajtje». Përmbajtja nuk e liston veten.
OUTSIDE_TOC = ("Abstrakt", "Mirënjohje", "Përmbajtja")
INSIDE_TOC = ("Lista e figurave", "Lista e tabelave", "Fjalori i termave")

# Rregulli është «një faqe», dhe faqja nuk matet dot pa e renderuar dokumentin.
# Kufiri është matja e renderimit në Word më 13 shtator 2026: 430 fjalë zunë dy
# faqe, dhe versioni i shkurtuar hyn në një me hapësirë të mbetur (VD-112).
ABSTRACT_MAX_WORDS = 360


def _check_front_titles(doc: Document) -> list[str]:
    """Cilët tituj hyjnë në përmbajtje dhe cilët jo, sipas stilit që mbajnë."""
    styles = {
        paragraph.text.strip(): paragraph.style.name
        for paragraph in doc.paragraphs
        if paragraph.text.strip() in OUTSIDE_TOC + INSIDE_TOC
    }
    problems = []
    for title in OUTSIDE_TOC:
        if styles.get(title) != FRONT_TITLE:
            problems.append(f"«{title}» duhet të jetë jashtë përmbajtjes (stili {FRONT_TITLE})")
    for title in INSIDE_TOC:
        if styles.get(title) != "Heading 1":
            problems.append(f"«{title}» duhet të hyjë në përmbajtje (stili Heading 1)")
    return problems


def _check_cover_font(doc: Document) -> list[str]:
    """Shablloni: «I gjithë teksti në këto 2 faqe: Times New Roman 14» (VD-113)."""
    problems = []
    for paragraph in doc.paragraphs:
        if paragraph.style.name == FRONT_TITLE:
            break
        for run in paragraph.runs:
            if not run.text.strip():
                continue
            if run.font.size != TITLE_SIZE or (run.font.name or FONT) != FONT:
                problems.append(
                    f"kopertina: «{paragraph.text.strip()[:40]}» nuk është {FONT} {TITLE_SIZE.pt:g}pt"
                )
                break
    return problems


def _check_mentioned_in_text(doc: Document) -> list[str]:
    """Çdo figurë dhe tabelë përmendet në tekst, jo vetëm në përshkrimin e vet.

    Shablloni e do secilën «të titulluar dhe të referuar në tekst». Pas «Tabela 1»
    nuk guxon të vijë shifër, që «Tabela 13» të mos numërohet si përmendje e saj.
    """
    _, chapters = _split_at_first_chapter(doc)
    captions, texts = [], []
    for paragraph in chapters:
        match = CAPTION.match(paragraph.text.strip())
        if match:
            captions.append((match.group(1), match.group(2)))
        else:
            texts.append(paragraph.text)
    joined = chr(10).join(texts)
    return [
        f"{kind} {number} nuk përmendet në tekst"
        for kind, number in captions
        if not re.search(f"{kind} {number}(?![0-9])", joined)
    ]


def _body_texts(doc: Document) -> list[tuple[str, str]]:
    """Teksti i trupit sipas radhës së leximit, si çifte (stili, teksti).

    Tabelat japin qelizat rresht pas rreshti, me stilin «tabelë»: një citim në qelizë
    numërohet aty ku e takon lexuesi, dhe `doc.paragraphs` nuk i përmban fare.
    """
    texts = []
    for element in doc.element.body.iterchildren():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph = Paragraph(element, doc)
            texts.append((paragraph.style.name, paragraph.text))
        elif tag == "tbl":
            for row in Table(element, doc).rows:
                texts.extend(("tabelë", cell.text) for cell in row.cells)
    return texts


def _check_citations(doc: Document) -> list[str]:
    """Citimet IEEE numërohen sipas radhës së citimit të parë, dhe lista u përgjigjet.

    Mentorja kërkoi IEEE më 16 tetor 2026: lista numërohet sipas radhës në të cilën
    burimi citohet për herë të parë, duke nisur nga Kapitulli 1 (VD-152). Ndërtimi e
    llogarit atë radhë nga burimi; ky kontroll e lexon nga dokumenti, ndaj kap edhe një
    paragraf të zhvendosur në Word, një citim të shtuar me dorë, «[?]» e një citimi pa
    referencë, ose një citim autor-vit që nuk u kthye në numër.
    """
    problems = []
    cited: list[str] = []
    listed: list[int] = []
    in_chapters = in_references = False
    for style, text in _body_texts(doc):
        if style == "Heading 1":
            in_chapters = in_chapters or bool(CHAPTER_HEADING.match(text))
            in_references = text.strip().endswith("Referencat")
            continue
        if in_references:
            entry = REFERENCE_ENTRY.match(text)
            if entry:
                listed.append(int(entry.group(1)))
            elif text.strip():
                problems.append(f"hyrje e listës pa numër: «{text[:50]}»")
            continue
        leftover = CITATION.search(text)
        if leftover:
            problems.append(f"citim autor-vit që nuk u bë numër: «{leftover.group(0)}»")
        if not in_chapters:
            continue
        for number in NUMERIC_CITATION.findall(text):
            if number == "?":
                problems.append(f"citim pa referencë: «{text[:50]}»")
            elif number not in cited:
                cited.append(number)

    for position, number in enumerate(cited, start=1):
        if number != str(position):
            problems.append(f"citimi i parë i [{number}] vjen aty ku pritej [{position}]")
            break
    if listed != list(range(1, len(listed) + 1)):
        problems.append(f"lista e referencave nuk numërohet 1, 2, 3…: {listed[:8]}…")
    for number in sorted({str(n) for n in listed} - set(cited), key=int):
        problems.append(f"referenca [{number}] nuk citohet te kapitujt")
    for number in sorted(set(cited) - {str(n) for n in listed}, key=int):
        problems.append(f"citimi [{number}] nuk ka hyrje në listë")
    return problems


def _check_cover_breaks(doc: Document) -> list[str]:
    """Faqja e brendshme hapet me ndarje te paragrafi i saj i parë, jo me paragraf bosh.

    Paragrafi bosh me ndërprerje faqeje, që ndërtimi e vinte mes dy kopertinave, dilte
    si faqe e zbrazët pas kopertinës kur ajo mbushej deri në fund; mentorja e hoqi më
    16 tetor 2026 dhe ia vuri ndarjen logos së faqes së brendshme (VD-152).
    """
    problems = []
    breaks = 0
    for paragraph in doc.paragraphs:
        if paragraph.style.name == FRONT_TITLE:
            break
        if paragraph._p.xpath(".//w:br[@w:type='page']"):
            problems.append("kopertinat ndahen me një paragraf me ndërprerje faqeje")
        if paragraph.paragraph_format.page_break_before:
            breaks += 1
    if breaks != 1:
        problems.append(f"kopertinat kanë {breaks} ndarje «page break before», pritej 1")
    return problems


def _check_update_fields(doc: Document) -> list[str]:
    """Word e plotëson përmbajtjen kur hapet, e nuk e lë tekstin zëvendësues."""
    flag = doc.settings.element.find(qn("w:updateFields"))
    if flag is None or flag.get(qn("w:val")) not in ("true", "1"):
        return ["dokumenti nuk i kërkon Word-it t'i përditësojë fushat, ndaj përmbajtja mbetet bosh"]
    return []


def _check_abstract_length(doc: Document) -> list[str]:
    words, inside = 0, False
    for paragraph in doc.paragraphs:
        if paragraph.style.name in (FRONT_TITLE, "Heading 1"):
            if inside:
                break
            inside = paragraph.text.strip() == "Abstrakt"
            continue
        if inside:
            words += len(re.findall(r"\w+", paragraph.text))
    if words > ABSTRACT_MAX_WORDS:
        return [f"abstrakti ka {words} fjalë, më shumë se {ABSTRACT_MAX_WORDS} që hyjnë në një faqe"]
    return []


def _check_numbering_of_sections(doc: Document) -> list[str]:
    """Nënkapitujt ecin 1, 2, 3 brenda kapitullit të tyre, pa kërcime.

    Numrat e nënkapitujve shkruhen me dorë te `chapters.py`, ndaj i ka të njëjtat
    mënyra për të dalë gabim që kishte numërimi i figurave para se të gjenerohej:
    një seksion i futur në mes dhe numrat e tjerë të palëvizur. Ndryshe nga
    figurat, këta nuk gjenerohen dot — numri i një nënkapitulli citohet në prozë
    dhe në planin e punimit — ndaj kontrollohen.
    """
    problems = []
    chapter = 0
    expected = 0
    for paragraph in doc.paragraphs:
        style = paragraph.style.name
        text = paragraph.text.strip()
        if style == "Heading 1" and CHAPTER_HEADING.match(text):
            chapter = int(text.split(" ", 1)[0])
            expected = 0
        elif style == "Heading 2" and chapter:
            number = text.split(" ", 1)[0]
            expected += 1
            if number != f"{chapter}.{expected}":
                problems.append(f"nënkapitulli «{number}» aty ku pritej {chapter}.{expected}")
                expected = int(number.rsplit(".", 1)[-1]) if "." in number else expected
    return problems


def _check_no_empty_headings(doc: Document) -> list[str]:
    """Asnjë kre pa asgjë nën të.

    Një kapitull që hapet drejt me nënkapitullin e vet nuk është bosh: përmbajtjen
    e mbajnë nënkapitujt. Bosh është ai pas të cilit vjen menjëherë një kre i të
    njëjtit nivel ose më i lartë, pra një titull që premton diçka që faqja nuk e
    mban — dhe që në përmbajtje duket njësoj si çdo tjetër.

    Ecja bëhet mbi trupin e dokumentit e jo mbi paragrafët, sepse një tabelë është
    përmbajtje po aq sa proza dhe nuk del fare te `doc.paragraphs`.
    """
    levels = {"Heading 1": 1, "Heading 2": 2}
    body: list[tuple[int | None, str]] = []
    for element in doc.element.body.iterchildren():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "tbl":
            body.append((None, ""))
        elif tag == "p":
            paragraph = Paragraph(element, doc)
            if not paragraph.text.strip():
                continue
            body.append((levels.get(paragraph.style.name), paragraph.text.strip()))

    problems = []
    for index, (level, text) in enumerate(body):
        if level is None:
            continue
        following = body[index + 1 :]
        empty = not following or (following[0][0] is not None and following[0][0] <= level)
        if empty:
            problems.append(f"kre pa përmbajtje: «{text[:40]}»")
    return problems


def remaining_todos(doc: Document) -> list[str]:
    """Vendet që autori duhet t'i plotësojë, si kujtesë e jo si gabim.

    Të shënuara me qëllim; raportohen sepse në një dokument prej dhjetëra faqesh
    ato gjenden vetëm nga kush di t'i kërkojë.

    Shënimi ka dy forma: «[PLOTËSO]» të vetëm, i ndjekur nga udhëzimi, dhe
    «[PLOTËSO: ...]» me arsyen brenda kllapave. E dyta u shpik për një seksion që
    priste një ekzekutim të gjatë dhe nuk numërohej fare, ndaj një seksion që
    priste **gjykimin e autorit** rrinte i padukshëm te lista e tij e vet. Të dyja
    janë vende ku dokumenti nuk ka mbaruar, ndaj të dyja numërohen.
    """
    marker = "[PLOTËSO"
    return [p.text.strip()[:70] for p in doc.paragraphs if marker in p.text]


def report(path: Path) -> list[str]:
    doc = Document(str(path))
    problems = []
    for check in (
        _check_styles,
        _check_fonts,
        _check_body,
        _check_captions,
        _check_markup,
        _check_numbering,
        _check_numbering_of_sections,
        _check_lists,
        _check_sections,
        _check_geometry,
        _check_page_breaks,
        _check_front_titles,
        _check_cover_font,
        _check_cover_breaks,
        _check_mentioned_in_text,
        _check_citations,
        _check_update_fields,
        _check_abstract_length,
    ):
        problems += [f"  {line}" for line in check(doc)]
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(OUTPUT)
    if not path.exists():
        print(f"Dokumenti nuk ekziston: {path}. Ndërtoje me build_thesis.py.")
        return 1

    problems = report(path)
    if problems:
        print(f"Formatimi devijon nga shablloni te {path.name}:")
        print("\n".join(problems))
        return 1

    print(f"Formatimi është sipas shabllonit: {path.name}")
    todos = remaining_todos(Document(str(path)))
    if todos:
        print(f"\nMbeten {len(todos)} vende për t'u plotësuar nga autori:")
        for entry in todos:
            print(f"  {entry}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
