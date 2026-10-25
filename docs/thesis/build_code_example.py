"""Figura e shembullit të kodit Java para dhe pas rishkrimit (Nënkapitulli 4.7).

    PYTHONPATH=backend python docs/thesis/build_code_example.py

Mentorja kërkoi më 15 tetor 2026 një shembull konkret kodi para dhe pas refaktorimit.
Shembulli nuk shkruhet me dorë: metoda lexohet nga korpusi, rishkrimi prodhohet nga
i njëjti motor dhe i njëjti plan që përdor rreshti i komandës, dhe figura vizatohet
nga ato dy tekste. Kështu ajo që tregon punimi është ajo që motori bën vërtet, dhe
një ndryshim i motorit e ndryshon edhe figurën herën tjetër që ndërtohet.

Metoda është `DistributedRegion.checkForLimitedOrNoAccess` nga Apache Geode, njëri
nga rishkrimet e Guard Clauses që leximi i Nënkapitullit 5.4 i pranoi ashtu si janë
(`data/results/rewrite_quality_sample.csv`). Kërkon korpusin, sepse kodi i huaj nuk
shpërndahet me depon (Nënkapitulli 4.12).
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from javasmell.analysis import analyze_path  # noqa: E402
from javasmell.detectors.rules import detect_all  # noqa: E402
from javasmell.detectors.thresholds import DEFAULT  # noqa: E402
from javasmell.refactor.patch import plan  # noqa: E402

SOURCE = (
    ROOT
    / "data/corpus/apache__geode__8fd839e8b73e/geode-core/src/main/java/org/apache/geode"
    / "internal/cache/DistributedRegion.java"
)
METHOD = "checkForLimitedOrNoAccess"
SMELL = "DeepNesting"
OUTPUT = Path(__file__).resolve().parent / "figures" / "shembull_guard_clauses.png"

# Gjerësia me të cilën figura futet në dokument, në inç. E njëjta vlerë i jepet
# `figure` te kapitulli, që shkronjat të dalin në faqe me madhësinë e llogaritur këtu.
WIDTH_IN = 6.1
PADDING_PT = 6.0
# Gjerësia e një shenje të DejaVu Sans Mono, si pjesë e madhësisë së shkronjës.
ADVANCE = 0.602
LINE_HEIGHT = 1.32

# Shkallë gri dhe një ngjyrë theksuese, si te figurat e tjera: punimi shtypet.
ADDED = "#e3efe6"
REMOVED = "#f6e1dd"
FRAME = "#bfbfbf"

plt.rcParams["font.serif"] = ["Times New Roman", "Liberation Serif", "DejaVu Serif"]


def _method_lines(text: str) -> list[str]:
    """Rreshtat e metodës, nga anotimi para saj deri te kllapa që e mbyll."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if f" {METHOD}(" in line and "void" in line)
    if lines[start - 1].strip().startswith("@"):
        start -= 1
    depth, end = 0, start
    for end in range(start, len(lines)):
        depth += lines[end].count("{") - lines[end].count("}")
        if depth == 0 and "{" in "".join(lines[start : end + 1]):
            break
    block = lines[start : end + 1]
    indent = min(len(line) - len(line.lstrip()) for line in block if line.strip())
    return [line[indent:] for line in block]


def _rewritten() -> tuple[list[str], list[str]]:
    """Metoda para dhe pas, ashtu si e jep plani i motorit për atë vend të vetëm."""
    project = analyze_path(str(SOURCE))
    smells = [
        smell
        for smell in detect_all(project, DEFAULT)
        if smell.smell_type == SMELL and (smell.method or "").split("(")[0] == METHOD
    ]
    if len(smells) != 1:
        raise SystemExit(f"pritej një gjetje {SMELL} te {METHOD}, u gjetën {len(smells)}")
    result = plan(Path(project.root), smells, javac=None)
    if len(result.patches) != 1:
        raise SystemExit(f"motori nuk e rishkroi {METHOD}: {result.declines or result.dropped}")
    patch = result.patches[0]
    before = _method_lines(patch.before.decode("utf-8"))
    after = _method_lines(patch.after.decode("utf-8"))
    return before, after


def _changed(before: list[str], after: list[str]) -> tuple[set[int], set[int]]:
    """Rreshtat që ndryshuan përtej dhëmbëzimit, në secilën anë.

    Roja e zbret gjithë trupin një nivel, ndaj krahasimi i rreshtave të plotë do t'i
    shënonte të gjithë si të ndryshuar. Krahasohen pa hapësirat e fillimit, që të
    theksohet vetëm ajo që motori shkroi vërtet.
    """
    matcher = difflib.SequenceMatcher(
        a=[line.strip() for line in before], b=[line.strip() for line in after], autojunk=False
    )
    removed: set[int] = set()
    added: set[int] = set()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            removed.update(range(i1, i2))
            added.update(range(j1, j2))
    return removed, added


def draw(before: list[str], after: list[str]) -> None:
    removed, added = _changed(before, after)
    longest = max(len(line) for line in before + after)
    usable = WIDTH_IN * 72 - 2 * PADDING_PT
    size = usable / (longest * ADVANCE)
    step = size * LINE_HEIGHT
    heading = 11.0
    panels = [("Para rishkrimit", before, removed, REMOVED),
              ("Pas Replace Nested Conditional with Guard Clauses", after, added, ADDED)]  # fmt: skip
    height = 4 + sum(heading + 2 * PADDING_PT + step * len(lines) + 8 for _, lines, _, _ in panels)

    fig = plt.figure(figsize=(WIDTH_IN, height / 72), dpi=300)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, WIDTH_IN * 72)
    ax.set_ylim(height, 0)
    ax.axis("off")

    y = 4.0
    for title, lines, marked, colour in panels:
        ax.text(0, y + heading * 0.8, title, family="serif", fontsize=10, fontweight="bold",
                va="baseline")  # fmt: skip
        y += heading + 2
        box = step * len(lines) + 2 * PADDING_PT
        ax.add_patch(Rectangle((0.5, y), WIDTH_IN * 72 - 1, box, fill=False, edgecolor=FRAME, lw=0.6))
        for index, line in enumerate(lines):
            top = y + PADDING_PT + index * step
            if index in marked:
                ax.add_patch(Rectangle((1, top), WIDTH_IN * 72 - 2, step, color=colour, lw=0))
            ax.text(PADDING_PT, top + step * 0.78, line, family="DejaVu Sans Mono", fontsize=size,
                    va="baseline")  # fmt: skip
        y += box + 8

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=300)
    plt.close(fig)


def main() -> int:
    if not SOURCE.exists():
        print(f"mungon korpusi: {SOURCE}. Shkarkoje me scripts/fetch_corpus.py.", file=sys.stderr)
        return 1
    before, after = _rewritten()
    draw(before, after)
    print(f"U gjenerua: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
