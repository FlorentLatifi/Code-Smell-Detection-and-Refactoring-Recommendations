"""Gjen fjalitë që punimi i thotë dy herë.

    python docs/thesis/check_repetition.py [shtegu.docx]

Mentorja kërkoi që punimi të mos e përsërisë veten, që lexuesi ta ruajë interesin
për atë që vjen më pas (VD-128). Një përsëritje nuk shihet gjatë shkrimit: fjalia e
dytë shkruhet javë pas së parës, në një kapitull tjetër, dhe secila duket e
arsyeshme në vendin e vet. Del në pah vetëm kur të dyja vihen krah për krah, dhe
këtë e bën ky kontroll mbi dokumentin e ndërtuar, jo mbi burimet Python, sepse
shumë fjali marrin formën përfundimtare vetëm kur u futen numrat.

Kontrollohen abstrakti, kapitujt 1–6 dhe shtojcat. Referencat, listat dhe fjalori
lihen jashtë, sepse aty përsëritja e formës është vetë formati. Abstrakti hyn,
sepse përfundimi mbyllej dikur me fjalinë e tij.

Raporton tri gjëra:
1. Çiftet e fjalive me ngjashmëri të paktën `SIMILAR`. Këto e rrëzojnë kontrollin.
2. Çiftet mes `REVIEW` dhe `SIMILAR`, për t'u lexuar. Nuk e rrëzojnë kontrollin,
   sepse në këtë brez dalin edhe fjali që ndajnë vetëm strukturën.
3. Frazat prej `PHRASE` ose më shumë fjalësh që dalin në më shumë se një fjali, po
   ashtu vetëm për lexim: një citim ose një term i përkufizuar përsëritet me të
   drejtë.

Kontrolli nuk e kap një ide të rithënë me fjalë të tjera. Ajo gjendet vetëm duke
lexuar, dhe VD-128 i gjeti shumicën pikërisht ashtu.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from build_thesis import FRONT_TITLE, OUTPUT
from docx import Document
from docx.text.paragraph import Paragraph

# Pragjet u zgjodhën mbi vetë këtë punim (VD-129), duke lexuar çdo çift mbi 0.40.
# Nga 0.55 e lart, secili çift ishte e njëjta fjali e thënë dy herë. Mes 0.40 dhe
# 0.55 dilnin kryesisht rithënie të pjesshme që vlen t'i lexosh, por edhe fjali që
# ndajnë vetëm një hapje («Asnjë erë nuk…», «Asnjë ribalancim nuk…»); prandaj ky
# brez listohet pa e rrëzuar kontrollin. Poshtë 0.40 nuk u shqyrtua.
SIMILAR = 0.55
REVIEW = 0.40

# Gjashtë fjalë, sepse një frazë më e shkurtër ndeshet shpesh edhe pa u përsëritur
# ideja: lidhje të zakonshme të gjuhës dhe emra metrikash me nyjat e tyre.
PHRASE = 6

# Fjalitë më të shkurtra janë kryesisht tregues («Të gjitha janë te Shtojca 8.3.»),
# dhe dy tregues të ngjashëm nuk janë përsëritje e përmbajtjes.
MIN_WORDS = 6

# Sa ndryshe mund të jenë dy fjali në gjatësi dhe në fjalor para se difflib-u të
# mos ia vlejë të thirret. Janë filtra shpejtësie, më të butë se `REVIEW`: një çift
# që i kalon ata nuk raportohet për sa kohë ngjashmëria nuk e arrin pragun.
MAX_LENGTH_GAP = 0.6
MIN_SHARED_VOCABULARY = 0.4

ABSTRACT = "Abstrakt"
CHAPTER = re.compile(r"^[1-68] ")
CAPTION = re.compile(r"^(Figura|Tabela) \d+\.")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇË«(])")


def sentences(path: Path) -> list[tuple[str, str]]:
    """Fjalitë e pjesës që kontrollohet, secila me nënkapitullin ku ndodhet."""
    doc = Document(str(path))
    found: list[tuple[str, str]] = []
    where = ""
    inside = False
    for child in doc.element.body.iterchildren():
        # Tabelat janë elemente të tjera dhe mbeten jashtë: një qelizë nuk është fjali.
        if child.tag.rsplit("}", 1)[-1] != "p":
            continue
        paragraph = Paragraph(child, doc)
        text = paragraph.text.strip()
        if not text:
            continue
        style = paragraph.style.name if paragraph.style is not None else ""
        if style == FRONT_TITLE:
            inside, where = text == ABSTRACT, text
            continue
        if style == "Heading 1":
            inside, where = bool(CHAPTER.match(text)), text
            continue
        if style.startswith("Heading"):
            where = text
            continue
        if not inside or CAPTION.match(text):
            continue
        for sentence in SENTENCE_END.split(text):
            sentence = sentence.strip()
            if len(sentence.split()) >= MIN_WORDS:
                found.append((where, sentence))
    return found


def _words(sentence: str) -> list[str]:
    return re.findall(r"\w+", sentence.lower())


def similar_pairs(words: list[list[str]]) -> list[tuple[float, int, int]]:
    """Çiftet me ngjashmëri të paktën `REVIEW`, nga më i ngjashmi."""
    vocabularies = [set(w) for w in words]
    pairs = []
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            a, b = words[i], words[j]
            if abs(len(a) - len(b)) > max(len(a), len(b)) * MAX_LENGTH_GAP:
                continue
            shared = len(vocabularies[i] & vocabularies[j])
            if shared / min(len(vocabularies[i]), len(vocabularies[j])) < MIN_SHARED_VOCABULARY:
                continue
            ratio = SequenceMatcher(None, a, b).ratio()
            if ratio >= REVIEW:
                pairs.append((ratio, i, j))
    return sorted(pairs, reverse=True)


def repeated_phrases(words: list[list[str]]) -> list[tuple[str, list[int]]]:
    """Frazat prej `PHRASE` fjalësh që dalin në më shumë se një fjali.

    N-gramet që mbivendosen mbi të njëjtat fjali janë një frazë e gjatë e prerë në
    copa, ndaj bashkohen dhe raportohet më e gjata prej tyre.
    """
    where: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for index, sentence in enumerate(words):
        for start in range(len(sentence) - PHRASE + 1):
            where[tuple(sentence[start : start + PHRASE])].add(index)
    by_sentences: dict[frozenset[int], list[tuple[str, ...]]] = defaultdict(list)
    for gram, indices in where.items():
        if len(indices) > 1:
            by_sentences[frozenset(indices)].append(gram)
    return sorted(
        (
            (" ".join(max(grams, key=lambda g: len(" ".join(g)))), sorted(indices))
            for indices, grams in by_sentences.items()
        ),
        key=lambda entry: (-len(entry[1]), entry[0]),
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(OUTPUT)
    if not path.exists():
        print(f"Dokumenti nuk ekziston: {path}. Ndërtoje me build_thesis.py.")
        return 1

    found = sentences(path)
    words = [_words(sentence) for _, sentence in found]
    pairs = similar_pairs(words)
    repeated = [pair for pair in pairs if pair[0] >= SIMILAR]
    review = [pair for pair in pairs if pair[0] < SIMILAR]

    def show(pair: tuple[float, int, int]) -> str:
        ratio, i, j = pair
        return (
            f"  [{ratio:.2f}]\n"
            f"    {found[i][0]}: {found[i][1]}\n"
            f"    {found[j][0]}: {found[j][1]}"
        )

    if repeated:
        pairs_found = (
            "Një çift fjalish thotë"
            if len(repeated) == 1
            else f"{len(repeated)} çifte fjalish thonë"
        )
        print(f"{pairs_found} të njëjtën gjë dy herë (ngjashmëri të paktën {SIMILAR}):")
        print("\n".join(show(pair) for pair in repeated))
    else:
        print(f"Asnjë fjali nuk thuhet dy herë: {len(found)} fjali të kontrolluara.")

    if review:
        print(f"\nPër lexim, ngjashmëri mes {REVIEW} dhe {SIMILAR}:")
        print("\n".join(show(pair) for pair in review))

    phrases = repeated_phrases(words)
    if phrases:
        print(f"\nPër lexim, fraza prej {PHRASE}+ fjalësh në më shumë se një fjali:")
        for phrase, indices in phrases:
            print(f"  «{phrase}»: " + "; ".join(found[i][0] for i in indices))

    return 1 if repeated else 0


if __name__ == "__main__":
    sys.exit(main())
