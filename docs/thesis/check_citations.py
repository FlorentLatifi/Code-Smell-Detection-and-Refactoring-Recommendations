"""Verifikon që teksti i punimit dhe lista e referencave thonë të njëjtën gjë.

Shablloni i UBT-së e kërkon shprehimisht: te «Referencat» shkojnë vetëm burimet e
cituara në tekst, ndërsa çdo burim i lexuar por i pacituar shkon te «Bibliografia».
Rrjedhimisht një referencë e palistuar dhe një referencë e pacituar janë të dyja
gabime formati, jo shije.

`build_thesis.build_references` e pretendon tashmë këtë koherencë — lista renderohet
nga `references.py` në vend që të shtypet në dokument, «që një citim i shtuar në tekst
dhe një citim i shtuar në listë të mos ndahen nga njëri-tjetri». Renderimi e siguron
vetëm gjysmën: numrat dhe renditja. Gjysma tjetër, që të dy anët të përmbajnë të
njëjtat burime, nuk e siguron dot asgjë përveç një kontrolli, sepse citimi jeton në
prozë dhe referenca në një listë Python.

    python docs/thesis/check_citations.py

Që nga VD-152 punimi citon me numra IEEE, por kapitujt mbeten të shkruar me autor dhe
vit: «Fowler (2018)», «(Lanza & Marinescu, 2006)». Ajo trajtë është çelësi që lidh
citimin me hyrjen e `references.py`; numri nuk caktohet dot pa e lexuar tekstin, sepse
del nga radha e citimit të parë. Prandaj gramatika e citimit jeton këtu, dhe
`build_thesis` merr prej saj si numrat (`citation_numbers`) ashtu edhe tekstin me numra
(`numeric`). Kontrolli dhe ndërtimi e lexojnë citimin njësoj, ose nuk e lexojnë fare.

Kontrollohet edhe auditimi i numrave të faqeve: `references.py` deklaron cilat hyrje
janë rikontrolluar kundrejt botuesit dhe cilat jo, dhe një hyrje e re me faqe nuk
guxon të rrijë jashtë të dyja listave.

Del me kod jo-zero nëse ndonjëra anë ka diçka që tjetra nuk e ka, që kontrolli të
mund të hyjë në CI. Nuk e prek dokumentin dhe nuk e ndalon ndërtimin: gjatë shkrimit
një citim pa referencë është gjendje kalimtare normale, ndërsa para dorëzimit është
gabim. Ndërtimi e shtyp një citim të tillë si «[?]», që të mos kalojë pa u parë.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections.abc import Iterator

from build_thesis import ACKNOWLEDGEMENTS, GLOSSARY, INTRODUCTION
from chapters import (
    CHAPTER_2,
    CHAPTER_3,
    CHAPTER_4,
    chapter_6,
    abstract,
    chapter_5,
    chapter_8,
)
from references import PAGES_UNVERIFIED, PAGES_VERIFIED, all_references

# Një mbiemër: fillon me shkronjë të madhe dhe mund të jetë i përbërë
# («Di Nucci», «Arcelli Fontana», «Henderson-Sellers»), i lidhur me «&» ose me «dhe»,
# ose i ndjekur nga «et al.». Kapitujt e shkruajnë «&» brenda kllapave dhe lidhëzën e
# gjuhës së tekstit jashtë tyre: «(Lanza & Marinescu, 2006)», por «Lanza dhe Marinescu
# (2006)». Apostrofi tipografik hyn si escape sepse ndryshe nuk
# dallohet nga apostrofi ASCII që qëndron pranë tij në të njëjtën klasë.
#
# Hapësira brenda një emri nuk e kalon rreshtin. Vargjet e kapitujve bashkohen me
# një kthim rreshti, dhe me `\s` një qelizë tabele që mbaron me një kuantifikues
# («… > FEW») ngjitej me autorin e qelizës pasardhëse, që dilte «FEW Lanza &
# Marinescu» (VD-129).
GAP = r"[^\S\n]+"
WORD = r"[A-ZÇË][\w\u2019'\-]*"
NAME = rf"{WORD}(?:{GAP}(?:(?:&|dhe){GAP})?(?:et{GAP}al\.|{WORD}))*"

# Dy format e citimit në burim: «(Fowler, 2018)» dhe «Fowler (2018)», secila me faqe
# të mundshme, «(2006, p. 80)», që në IEEE bëhet «[5, p. 80]». Një shprehje e vetme, që
# citimet të dalin sipas radhës në tekst: numri IEEE është pikërisht ajo radhë. Format
# nuk mbivendosen, sepse e para fillon me kllapë dhe e dyta me shkronjë të madhe.
CITATION = re.compile(
    rf"\((?P<p_name>{NAME}),\s*(?P<p_year>\d{{4}})(?:,\s*p\.\s*(?P<p_page>\d+))?\)"
    rf"|(?P<n_name>{NAME})(?P<gap>\s+)\((?P<n_year>\d{{4}})(?:,\s*p\.\s*(?P<n_page>\d+))?\)"
)

# Ndarësit pas të cilëve nuk ka më mbiemër: gjithçka para tyre është autori i parë.
COAUTHOR_MARKERS = ("&", "dhe", "et")

# Sa gjatë mund të jetë një mbaresë shqipe e ngjitur me vizë te një mbiemër i huaj
# («Fowler-i», «Cohen-it», «Marinescu-t»). Kufiri e ndan mbaresën nga mbiemri i
# përbërë: «Henderson-Sellers» nuk shkurtohet, «Henderson-Sellers-it» po.
MAX_SUFFIX = 3

# Një varg faqesh në listë: IEEE i lidh me vizë të mesme («pp. 1143–1191»), ndërsa
# DOI-të përdorin vizë të shkurtër, ndaj një DOI nuk ngatërrohet me faqe.
PAGE_RANGE = re.compile(r"\d+–\d+")


def _fold(text: str) -> str:
    """Krahasim që nuk varet nga diakritika: «Mäntylä» dhe «Mantyla» janë një."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _first_author(name: str) -> str:
    """Mbiemri i autorit të parë nga një citim ose nga një referencë.

    Mban emrat e përbërë («Di Nucci») dhe e ndal te bashkautori i parë, sepse
    referenca dhe citimi e shkruajnë bashkautorin ndryshe: lista jep «& Kang, B.-K.»,
    teksti jep «& Kang» ose «et al.».
    """
    words: list[str] = []
    for word in name.replace(",", " ").split():
        if word in COAUTHOR_MARKERS:
            break
        words.append(word)
    return _fold(" ".join(words))


def _strings(item: object) -> Iterator[str]:
    """Çdo varg teksti brenda një elementi të kapitullit, sido që të jetë ndërtuar.

    Tabelat dhe titujt e figurave numërohen bashkë me prozën: një citim brenda një
    titulli figure është citim njësoj, dhe kalimi vetëm mbi paragrafët do ta linte
    jashtë.
    """
    if isinstance(item, str):
        yield item
    elif isinstance(item, (list, tuple)):
        for element in item:
            yield from _strings(element)


def chapter_text() -> str:
    """Kapitujt sipas radhës së leximit, si një varg; numrat IEEE dalin prej tij.

    Kapitulli 7 është vetë lista, ndaj mungon. Ballina mungon me qëllim: numërimi
    nis nga Kapitulli 1, edhe pse fjalori, para tij, citon Moha et al.
    """
    sources = [
        INTRODUCTION,
        CHAPTER_2,
        CHAPTER_3,
        CHAPTER_4,
        chapter_5(),
        chapter_6(),
        chapter_8(),
    ]
    return "\n".join(_strings(sources))


def thesis_text(chapters: str) -> str:
    """I tërë teksti që shkon në dokument, si një varg i vetëm."""
    return "\n".join(_strings([abstract(), ACKNOWLEDGEMENTS, GLOSSARY])) + "\n" + chapters


def _name_and_year(match: re.Match[str]) -> tuple[str, str]:
    """Mbiemri i autorit të parë dhe viti i një citimi, në cilëndo nga dy format."""
    if match["p_name"] is not None:
        return _first_author(match["p_name"]), match["p_year"]
    return _first_author(match["n_name"]), match["n_year"]


def citations(text: str) -> set[tuple[str, str]]:
    """Çiftet (mbiemri i autorit të parë, viti) që teksti i citon."""
    return {_name_and_year(match) for match in CITATION.finditer(text)}


def listed() -> dict[tuple[str, str], str]:
    """Çiftet (mbiemri, viti) të listës së referencave, te hyrja e plotë.

    Çelësi lexohet nga etiketa e hyrjes, «Lanza & Marinescu 2006», e jo nga vetë
    hyrja: IEEE e vë vitin në fund dhe mbiemrin pas inicialeve, dhe autori kolektiv
    («PMD Team») nuk ka inicialë fare.
    """
    return {reference_key(label): entry for label, entry in all_references()}


def reference_key(label: str) -> tuple[str, str]:
    """«Bieman & Kang 1995» -> ('bieman', '1995'), çelësi me të cilin krahasohet citimi."""
    author, _, year = label.rpartition(" ")
    return _first_author(author), year


def citation_numbers(text: str) -> dict[tuple[str, str], int]:
    """Numri IEEE i çdo burimi të listuar: radha e citimit të tij të parë te `text`.

    Një citim që nuk gjendet në listë nuk merr numër, që numrat e listës të mbeten
    1, 2, 3 pa vrima. Atë e raporton `report`, dhe `numeric` e shtyp si «[?]».
    """
    references = listed()
    known = {author for author, _ in references}
    numbers: dict[tuple[str, str], int] = {}
    for match in CITATION.finditer(text):
        author, year = _name_and_year(match)
        key = (_undeclined(author, known), year)
        if key in references and key not in numbers:
            numbers[key] = len(numbers) + 1
    return numbers


def numeric(text: str, numbers: dict[tuple[str, str], int]) -> str:
    """Citimet e `text` në trajtën IEEE, me numrat e `citation_numbers`.

    «Fowler (2018)» bëhet «Fowler [2]», «(Lanza & Marinescu, 2006)» bëhet «[5]», dhe
    «Lanza dhe Marinescu (2006, p. 80)» bëhet «Lanza dhe Marinescu [5, p. 80]». Te
    citimi narrativ emri mbetet, sepse është pjesë e fjalisë; mbaresa shqipe e një
    emri të lakuar mbetet bashkë me të.
    """
    known = {author for author, _ in numbers}

    def replace(match: re.Match[str]) -> str:
        author, year = _name_and_year(match)
        number = numbers.get((_undeclined(author, known), year), "?")
        page = match["p_page"] or match["n_page"]
        label = f"[{number}, p. {page}]" if page else f"[{number}]"
        if match["p_name"] is not None:
            return label
        return f"{match['n_name']}{match['gap']}{label}"

    return CITATION.sub(replace, text)


def _undeclined(author: str, known: set[str]) -> str:
    """Mbiemri pa mbaresën shqipe, nëse heqja e saj jep një autor të listës.

    Proza është shqip dhe mbiemrat lakohen: teksti shkruan «Henderson-Sellers-it
    (1996)» për referencën «Henderson-Sellers, B. 1996». Pa këtë hap kontrolli do të
    ankohej për çdo citim të lakuar, pra do të ishte më i zhurmshëm se i dobishëm.

    Heqja lejohet vetëm kur mbetja është pikërisht një autor i listës, ndaj nuk mund
    të shpikë përputhje me një burim që nuk ekziston.
    """
    prefix, _, suffix = author.rpartition("-")
    if prefix and len(suffix) <= MAX_SUFFIX and prefix in known:
        return prefix
    return author


def _check_page_audit(references: dict[tuple[str, str], str]) -> list[str]:
    """Çdo referencë me numra faqesh është ose e verifikuar ose e shënuar si jo.

    `references.py` e ndan listën në të kontrolluara dhe të pakontrolluara kundrejt
    regjistrit të botuesit. Ajo ndarje është pretendim për saktësinë e punimit, ndaj
    trajtohet si kod: një referencë e re me faqe që nuk hyn në asnjërën listë do të
    thoshte heshtazi «e verifikuar», çka nuk është.
    """
    problems = []
    audited = {}
    for name in PAGES_VERIFIED + PAGES_UNVERIFIED:
        key = reference_key(name)
        if key not in references:
            problems.append(f"  auditimi i faqeve përmend një burim që s'është në listë: {name}")
        audited[key] = name

    for key, reference in sorted(references.items()):
        if PAGE_RANGE.search(reference) and key not in audited:
            problems.append(f"  referencë me faqe jashtë auditimit: {reference[:70]}")
    return problems


def report() -> list[str]:
    """Mospërputhjet mes tekstit dhe listës, si rreshta gati për t'u shtypur."""
    chapters = chapter_text()
    references = listed()
    known_authors = {author for author, _ in references}
    cited = {
        (_undeclined(author, known_authors), year)
        for author, year in citations(thesis_text(chapters))
    }
    # Një burim i cituar vetëm te ballina do të ishte në listë pa numër, sepse numrat
    # nisin nga Kapitulli 1.
    numbered = citation_numbers(chapters)
    problems = []

    for key, reference in sorted(references.items()):
        if key not in cited:
            problems.append(f"  e listuar por e pacituar: {reference}")
        elif key not in numbered:
            problems.append(f"  e cituar vetëm jashtë kapitujve, pa numër: {reference}")

    for author, year in sorted(cited):
        if (author, year) in references:
            continue
        hint = " (viti nuk përputhet me listën)" if author in known_authors else ""
        problems.append(f"  e cituar por e palistuar: {author} {year}{hint}")

    return problems + _check_page_audit(references)


def main() -> int:
    # Raporti përmban emra me diakritikë dhe tekst shqip; konsola e Windows-it
    # e nis me një kodim njëbajtësh dhe do t'i shtypte si pikëpyetje.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    problems = report()
    if not problems:
        print(f"Citimet janë koherente: {len(listed())} referenca, të gjitha të cituara.")
        return 0
    print("Teksti dhe lista e referencave nuk përputhen:")
    print("\n".join(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main())
