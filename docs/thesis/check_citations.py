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

Del me kod jo-zero nëse ndonjëra anë ka diçka që tjetra nuk e ka, që kontrolli të
mund të hyjë në CI. Nuk e prek dokumentin dhe nuk e ndalon ndërtimin: gjatë shkrimit
një citim pa referencë është gjendje kalimtare normale, ndërsa para dorëzimit është
gabim.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections.abc import Iterator

from build_thesis import (
    ABSTRACT,
    ACKNOWLEDGEMENTS,
    FIGURE_LIST,
    GLOSSARY,
    INTRODUCTION,
    TABLE_LIST,
)
from chapters import CHAPTER_2, CHAPTER_3, CHAPTER_4, CHAPTER_6, chapter_5
from references import all_references

# Një mbiemër: fillon me shkronjë të madhe dhe mund të jetë i përbërë
# («Di Nucci», «Arcelli Fontana», «Henderson-Sellers»), i lidhur me «&» ose i
# ndjekur nga «et al.». Apostrofi tipografik hyn si escape sepse ndryshe nuk
# dallohet nga apostrofi ASCII që qëndron pranë tij në të njëjtën klasë.
WORD = r"[A-ZÇË][\w\u2019'\-]*"
NAME = rf"{WORD}(?:\s+(?:&\s+)?(?:et\s+al\.|{WORD}))*"

# Dy format që lejon shablloni: «Fowler (2018)» dhe «(Fowler, 2018)».
NARRATIVE = re.compile(rf"({NAME})\s+\((\d{{4}})\)")
PARENTHETICAL = re.compile(rf"\(({NAME}),\s*(\d{{4}})\)")

# Ndarësit pas të cilëve nuk ka më mbiemër: gjithçka para tyre është autori i parë.
COAUTHOR_MARKERS = ("&", "et")

# Sa gjatë mund të jetë një mbaresë shqipe e ngjitur me vizë te një mbiemër i huaj
# («Fowler-i», «Cohen-it», «Marinescu-t»). Kufiri e ndan mbaresën nga mbiemri i
# përbërë: «Henderson-Sellers» nuk shkurtohet, «Henderson-Sellers-it» po.
MAX_SUFFIX = 3


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


def thesis_text() -> str:
    """I tërë teksti që shkon në dokument, si një varg i vetëm."""
    sources = [
        ABSTRACT,
        ACKNOWLEDGEMENTS,
        FIGURE_LIST,
        TABLE_LIST,
        GLOSSARY,
        INTRODUCTION,
        CHAPTER_2,
        CHAPTER_3,
        CHAPTER_4,
        chapter_5(),
        CHAPTER_6,
    ]
    return "\n".join(_strings(sources))


def citations(text: str) -> set[tuple[str, str]]:
    """Çiftet (mbiemri i autorit të parë, viti) që teksti i citon."""
    found = set()
    for pattern in (NARRATIVE, PARENTHETICAL):
        for name, year in pattern.findall(text):
            found.add((_first_author(name), year))
    return found


def listed() -> dict[tuple[str, str], str]:
    """Çiftet (mbiemri, viti) të listës së referencave, te referenca e plotë.

    Viti është numri i parë katërshifror i hyrjes, sepse formati i shabllonit e vë
    vitin menjëherë pas autorëve. Burimet elektronike pa vit mbeten me vit bosh dhe
    krahasohen vetëm me mbiemrin.
    """
    entries = {}
    for reference in all_references():
        author = _first_author(reference.split(",")[0])
        year = re.search(r"\b(?:19|20)\d{2}\b", reference)
        entries[(author, year.group() if year else "")] = reference
    return entries


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


def report() -> list[str]:
    """Mospërputhjet mes tekstit dhe listës, si rreshta gati për t'u shtypur."""
    text = thesis_text()
    references = listed()
    known_authors = {author for author, _ in references}
    cited = {(_undeclined(author, known_authors), year) for author, year in citations(text)}

    # Një burim elektronik citohet pa vit, ndaj për të kërkohet vetëm mbiemri diku
    # në tekst. Kjo është kontroll më i dobët se çifti (mbiemër, vit), por është i
    # vetmi që i përshtatet një burimi që nuk ka vit botimi.
    folded = _fold(text)
    problems = []

    for key, reference in sorted(references.items()):
        author, year = key
        found = author in folded if year == "" else key in cited
        if not found:
            problems.append(f"  e listuar por e pacituar: {reference}")

    for author, year in sorted(cited):
        if (author, year) in references or (author, "") in references:
            continue
        hint = " (viti nuk përputhet me listën)" if author in known_authors else ""
        problems.append(f"  e cituar por e palistuar: {author} {year}{hint}")

    return problems


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
