"""Verifikon që prezantimi i gjeneruar është i plotë dhe pajtohet me punimin.

    python docs/thesis/check_slides.py [shtegu.pptx]

Sllajdet i lexojnë shifrat nga të njëjtët skedarë si kapitujt, përmes të njëjtit
ngarkues, ndaj një shifër e vjetruar nuk mund të ekzistojë — ajo garanci vjen nga
ndërtimi dhe nuk ka nevojë për kontroll. Ajo që s'e garanton askush është nëse
prezantimi është **i përdorshëm**, dhe ato mangësi zbulohen para komisionit.

Kontrollohen katër gjëra:

**Që çdo figurë e kërkuar ekziston.** `build_slides` e shënon një figurë të
munguar drejt në sllajd, që të mos kalojë heshtazi; ky kontroll e rrëzon
ndërtimin në vend që të mbetet aty.

**Që çdo sllajd ka shënim folësi.** Sllajdet mbajnë pak fjalë me qëllim, ndaj
argumenti jeton te shënimet. Një sllajd pa shënim është një sllajd të cilin
folësi do ta improvizojë.

**Që asnjë kuti teksti nuk është bosh.** Një kuti bosh nuk duket në PowerPoint
derisa dikush klikon mbi të, dhe në projeksion shfaqet si vend i zbrazët.

**Që shifrat kryesore pajtohen me punimin.** Numri i mostrave, i depove dhe i
vendeve të gjetura shfaqet në të dy artefaktet; nëse ndahen, njëri prej tyre është
ndërtuar nga të dhëna të vjetruara.

Del me kod jo-zero që kontrolli të mund të hyjë në CI bashkë me atë të formatit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from build_slides import FIGURES, OUTPUT
from chapters import _load
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

MISSING = re.compile(r"\[MUNGON figura ([^\]]+)\]")

#: Sa sllajde e bëjnë një mbrojtje bachelor-i: mjaft për argumentin, jo aq sa të
#: mos mbarojnë brenda kohës. Kufijtë janë të gjerë me qëllim — kontrolli kap
#: gabimin e ndërtuesit, nuk redakton dramaturgjinë e autorit.
FEWEST = 10
MOST = 25


def _figure_names() -> list[str]:
    """Emrat e figurave që `build_slides` u referohet, lexuar nga burimi.

    Lexohet si tekst e jo duke ndërtuar prezantimin dy herë: ndërtimi është i
    shtrenjtë dhe kontrolli duhet të mund të ekzekutohet mbi një skedar që
    ekziston tashmë.
    """
    source = (Path(__file__).parent / "build_slides.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r'_picture\(slide, "([^"]+)"', source)))


def _check_figures() -> list[str]:
    problems = []
    for name in _figure_names():
        if not (Path(FIGURES) / name).is_file():
            problems.append(f"figura {name} u kërkua por nuk gjendet te figures/")
    return problems


def _check_slides(deck: Presentation) -> list[str]:
    problems = []
    count = len(deck.slides)
    if not FEWEST <= count <= MOST:
        problems.append(f"{count} sllajde, pritej mes {FEWEST} dhe {MOST}")

    for number, slide in enumerate(deck.slides, 1):
        if not slide.has_notes_slide or not slide.notes_slide.notes_text_frame.text.strip():
            problems.append(f"sllajdi {number} nuk ka shënim folësi")

        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE or shape.has_table:
                continue
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text
            if not text.strip():
                problems.append(f"sllajdi {number} ka një kuti teksti bosh")
            found = MISSING.search(text)
            if found:
                problems.append(f"sllajdi {number}: {found.group(0)}")
    return problems


def _check_figures_agree(deck: Presentation) -> list[str]:
    """Shifrat që shfaqen në të dy artefaktet duhet të jenë të njëjtat.

    Krahasimi bëhet me tekstin e renderuar e jo me burimin, sepse pikërisht
    renderimi është ai që sheh komisioni. Hapësira jo-thyese dhe ajo e zakonshme
    barazohen: `build_slides` i ndan mijëshet për lexim, `chapters` jo.
    """
    words = " ".join(
        shape.text_frame.text
        for slide in deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
    ).replace(" ", " ")

    dataset = _load("mlcq_dataset.json")
    refactoring = _load("refactoring_evaluation.json")
    expected = {
        "mostrat e matura": dataset["rows"],
        "depot": dataset["repositories"],
        "vendet e gjetura": refactoring["detected"],
        "të transformuarat": refactoring["applied"],
    }

    problems = []
    for label, value in expected.items():
        spaced = f"{value:,}".replace(",", " ")
        if spaced not in words and str(value) not in words:
            problems.append(f"{label} ({value}) nuk shfaqet në asnjë sllajd")
    return problems


def report(path: Path) -> list[str]:
    deck = Presentation(str(path))
    return _check_figures() + _check_slides(deck) + _check_figures_agree(deck)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(OUTPUT)
    if not path.exists():
        print(f"Prezantimi nuk ekziston: {path}. Ndërtoje me build_slides.py.")
        return 1

    problems = report(path)
    if problems:
        print(f"Prezantimi ka mangësi te {path.name}:")
        for problem in problems:
            print(f"  {problem}")
        return 1

    deck = Presentation(str(path))
    print(f"Prezantimi është i plotë: {len(deck.slides)} sllajde, të gjitha me shënim folësi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
