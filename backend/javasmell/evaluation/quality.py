"""Whether an applied rewrite is one a developer would accept.

Phase 3 currently claims of its rewrites only that they *compile*, or in the
common case where a corpus file cannot compile alone, that they add no new kind
of error (VD-53, VD-55). That is a claim about the compiler, and it is silent on
the question a reader of the thesis actually has: does the rewritten code look
like something anyone would keep? A transformation can be perfectly
behaviour-preserving and still produce a method nobody would merge -- a fragment
lifted out at an arbitrary boundary, named for nothing, taking nine parameters.

Fowler defines a refactoring as a change that preserves observable behaviour
*and* improves internal structure. The engine measures the first half and
asserts nothing about the second. This module supplies the missing half the only
way it can be supplied without a second engine: a human reads a sample of the
diffs and judges them against a fixed rubric.

**Applied sites only.** Whether the engine was *right to decline* the fourteen
thousand refusals is a different question with a different design, and mixing
the two would produce a rate that answers neither. The refusal distribution is
already reported on its own (VD-28).

**Stratified, not proportional.** ExtractMethod is 93% of the applied sites, so
a proportional sample of sixty would carry two or three of everything else and
say nothing about them. Each transformation is sampled to the same depth and
reported separately; the pooled figure is reweighted by the true stratum sizes
rather than read off the sample, because the sample is deliberately not
representative of the population it was drawn from.

**The sheet is blind.** The rows the reviewer fills carry the diff and nothing
else -- no verdict from ``javac``, no resolution, no metric shift. Those are
joined back only at scoring time. A reviewer who can see that a rewrite compiled
is being told the answer to half the question before being asked it, and the
cross-tabulation of the two is one of the few interesting things this measure
produces: it is what says whether the compiler check is a proxy for acceptance
or merely correlated with it.
"""

from __future__ import annotations

import csv
import difflib
import math
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from javasmell.analysis import analyze_source

#: Sites drawn per transformation. Twenty is what one reviewer can read
#: attentively in a sitting, and reading sixty diffs carelessly measures
#: attention rather than the engine. Fixed here rather than defaulted in the
#: script so the number that produced the committed sheet is in the package.
SAMPLE_PER_REFACTORING = 20

#: Fixed so the sample is the same sample on any machine, as everything
#: empirical in this project must be (ENGINEERING.md section 3.5).
SAMPLE_SEED = 20260907


class Behaviour(StrEnum):
    """Does the rewrite do what the original did, as far as reading shows?

    The reviewer is not running the code; this is the judgement of someone
    reviewing a pull request, and ``UNCLEAR`` is a real answer rather than a
    refusal to answer -- a reviewer who cannot tell would not merge either.
    """

    PRESERVED = "preserved"
    UNCLEAR = "unclear"
    CHANGED = "changed"


class Benefit(StrEnum):
    """Is the internal structure better, the other half of Fowler's definition?

    ``NEUTRAL`` covers the rewrite that moves bytes without improving anything:
    the extracted method that is simply the first N lines, with no coherent
    responsibility. It is the outcome this measure exists to catch, because
    every automatic check in the pipeline scores it as a success.
    """

    IMPROVES = "improves"
    NEUTRAL = "neutral"
    WORSENS = "worsens"


class Acceptance(StrEnum):
    """Would the reviewer merge it, and at what cost?

    ``AFTER_EDIT`` is the interesting middle: a rewrite that is sound but named
    badly is worth counting apart both from one that ships and one that is
    thrown away, since naming is the part a deterministic engine cannot do and
    the part a human fixes in seconds.
    """

    AS_IS = "as_is"
    AFTER_EDIT = "after_edit"
    REJECT = "reject"


#: Column name -> the enumeration that validates it. The sheet is filled by
#: hand in a spreadsheet, so every value is checked on the way back in; a typo
#: that silently became a category would corrupt a number in the thesis.
DIMENSIONS: dict[str, type[StrEnum]] = {
    "behaviour": Behaviour,
    "benefit": Benefit,
    "acceptance": Acceptance,
}

SHEET_COLUMNS = [
    "review_id",
    "refactoring",
    "smell",
    "class_name",
    "method",
    "file",
    "ordinal",
    *DIMENSIONS,
    "note",
]


@dataclass(frozen=True)
class Site:
    """One row of ``refactoring_sites.csv``, addressable again afterwards.

    ``ordinal`` is the position among *all* of this file's rows, refusals
    included. That file carries no line number -- the gap VD-55 ran into -- so a
    class that overloads a method has two rows a name cannot tell apart. The
    evaluation writes one row per locatable site in the order the walk finds
    them, so position is the one key that is unambiguous without changing the
    schema of a file that took hours to produce.
    """

    file: str
    ordinal: int
    class_name: str
    method: str
    smell: str
    refactoring: str


@dataclass(frozen=True)
class Judgement:
    """One filled row of the review sheet.

    ``ordinal`` travels with the judgement so scoring can prove the sheet still
    describes the sample it was drawn from. A sheet filled by hand and a CSV
    regenerated later are two files nothing else ties together, and a silent
    mismatch would attach real judgements to the wrong rewrites.
    """

    review_id: str
    refactoring: str
    behaviour: Behaviour
    benefit: Benefit
    acceptance: Acceptance
    ordinal: int = -1
    note: str = ""


def applied_sites(path: str | Path) -> list[Site]:
    """Every rewrite the engine applied, keyed so it can be regenerated."""
    sites: list[Site] = []
    seen_per_file: Counter[str] = Counter()
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            ordinal = seen_per_file[row["file"]]
            seen_per_file[row["file"]] += 1
            if row["applied"] != "1":
                continue
            sites.append(
                Site(
                    file=row["file"],
                    ordinal=ordinal,
                    class_name=row["class_name"],
                    method=row["method"],
                    smell=row["smell"],
                    refactoring=row["refactoring"],
                )
            )
    return sites


def population(sites: Iterable[Site]) -> dict[str, int]:
    """How many applied sites each transformation has, for the reweighting."""
    return dict(Counter(site.refactoring for site in sites))


def stratified_sample(
    sites: Sequence[Site],
    per_refactoring: int = SAMPLE_PER_REFACTORING,
    seed: int = SAMPLE_SEED,
) -> list[Site]:
    """The same sites on every machine, ``per_refactoring`` of each kind.

    Sorted before drawing because ``refactoring_sites.csv`` is written in walk
    order, and a sample that depended on that order would change the moment a
    file was added to the corpus. A stratum smaller than the quota is taken
    whole, which is a smaller sample and not an error.
    """
    by_refactoring: dict[str, list[Site]] = {}
    for site in sites:
        by_refactoring.setdefault(site.refactoring, []).append(site)

    drawn: list[Site] = []
    for refactoring in sorted(by_refactoring):
        stratum = sorted(by_refactoring[refactoring], key=lambda s: (s.file, s.ordinal))
        rng = random.Random(f"{seed}-{refactoring}")
        take = min(per_refactoring, len(stratum))
        drawn.extend(sorted(rng.sample(stratum, take), key=lambda s: (s.file, s.ordinal)))
    return drawn


def counted_changes(diff: str) -> tuple[int, int]:
    """Rreshta të shtuar dhe të hequr, thjesht të numëruar.

    Numërim, jo gjykim: rreshtat janë aty te diff-i dhe rishikuesi do t'i numëronte
    vetë. Ndarja mes një rishkrimi që heq dhjetë rreshta dhe njërit që heq njëqind
    është gjëja e parë që i thotë sa i madh është ndryshimi para se ta lexojë.
    """
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and line[:3] != "+++")
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and line[:3] != "---")
    return added, removed


def introduced_members(before: bytes, after: bytes, path: str = "<memory>") -> tuple[str, ...]:
    """Nënshkrimet që ekzistojnë pas rishkrimit dhe nuk ekzistonin para tij.

    Emërtimi është pjesa që një transformim deterministik nuk e bën, ndaj është
    gjëja e parë që një rishikues kërkon dhe më e lehta për t'u humbur brenda një
    hunk-u pesëdhjetë rreshtash. Nxjerrja e saj nuk shton informacion: gjithçka
    këtu duket te diff-i sipër.

    Verbëria që kërkon VD-72 është për **verdiktet** — javac, zgjidhja e erës,
    lëvizja e metrikës — dhe asnjëri prej tyre nuk shfaqet këtu.
    """

    def members(source: bytes) -> set[str] | None:
        """``None`` kur skedari nuk parsohet, e jo bashkësi e zbrazët.

        Bashkësia e zbrazët do të thoshte «asnjë metodë», dhe zbritja e saj nga
        ana tjetër do të raportonte çdo metodë të skedarit si të shtuar nga
        rishkrimi. Mosdija dhe mungesa nuk janë e njëjta gjë.
        """
        try:
            project = analyze_source(source.decode("utf-8"), path)
        except (UnicodeDecodeError, ValueError):
            return None
        found = set()
        for unit in project.units:
            for cls in unit.classes:
                for method in cls.methods:
                    types = ", ".join(p.type_name for p in method.parameters)
                    prefix = "" if method.return_type is None else f"{method.return_type} "
                    found.add(f"{prefix}{cls.name}.{method.name}({types})")
        return found

    old, new = members(before), members(after)
    if old is None or new is None:
        return ()
    return tuple(sorted(new - old))


def negated_guards(diff: str) -> int:
    """Sa kushte të shtuara janë mohim i një mohimi, p.sh. «if (!(a != b))».

    Guard clause-i ndërtohet duke e mbështjellë kushtin me `!(...)`, kurrë duke e
    përmbysur operatorin, sepse `a > b` te `a <= b` është i gabuar për NaN. Kjo e
    bën transformimin të saktë dhe herë-herë të vështirë për t'u lexuar. Numri
    thotë sa herë ndodhi; nëse kjo prish diçka, e thotë rishikuesi.
    """
    count = 0
    for line in diff.splitlines():
        if not line.startswith("+") or "!(" not in line:
            continue
        inner = line.partition("!(")[2]
        if "!" in inner or "!=" in inner:
            count += 1
    return count


def label_sample(sampled: Sequence[Site]) -> list[tuple[str, Site]]:
    """A short reading label per drawn site, numbered within its transformation.

    The obvious label -- transformation, ordinal and file name -- is not unique:
    two corpus projects both hold a ``MainActivity.java``, and both can have an
    applied site at the same position. Numbering within the stratum cannot
    collide by construction, and the label stays the same across runs because
    the sample does.

    The label is for reading and for citing a row in the thesis. The key that
    identifies the *site* remains the file and the ordinal, which is what
    scoring checks the sheet against.
    """
    numbered: list[tuple[str, Site]] = []
    counts: Counter[str] = Counter()
    for site in sampled:
        initials = "".join(c for c in site.refactoring if c.isupper())[:3] or "R"
        counts[initials] += 1
        numbered.append((f"{initials}{counts[initials]:02d}", site))
    return numbered


def diff_text(before: bytes, after: bytes, label: str, context: int = 6) -> str:
    """The rewrite as a diff meant to be read rather than applied.

    ``refactor.patch.unified`` produces the other kind: ``a/``-prefixed, minimal
    context, git's no-newline marker, everything ``git apply`` needs and nothing
    a reader does. Wider context here because judging whether an extracted block
    is a coherent unit needs the lines around it, and no marker because nothing
    applies this.
    """
    diff = difflib.unified_diff(
        before.decode("utf-8", errors="replace").splitlines(keepends=True),
        after.decode("utf-8", errors="replace").splitlines(keepends=True),
        fromfile=f"{label} (before)",
        tofile=f"{label} (after)",
        n=context,
    )
    return "".join(line if line.endswith("\n") else line + "\n" for line in diff)


def read_judgements(path: str | Path) -> list[Judgement]:
    """The filled sheet, with every categorical value checked.

    A blank row is one the reviewer has not reached yet and is skipped, so
    scoring a half-filled sheet reports on the half that is filled instead of
    failing. A *wrong* value is not skipped: it raises, because a typo that fell
    through would land in the thesis as a category.
    """
    judgements: list[Judgement] = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            answers = {name: (row.get(name) or "").strip() for name in DIMENSIONS}
            if not any(answers.values()):
                continue
            for name, enumeration in DIMENSIONS.items():
                if answers[name] not in {member.value for member in enumeration}:
                    allowed = ", ".join(member.value for member in enumeration)
                    raise ValueError(
                        f"row {number}: {name}={answers[name]!r} is not one of: {allowed}"
                    )
            judgements.append(
                Judgement(
                    review_id=row["review_id"],
                    refactoring=row["refactoring"],
                    behaviour=Behaviour(answers["behaviour"]),
                    benefit=Benefit(answers["benefit"]),
                    acceptance=Acceptance(answers["acceptance"]),
                    ordinal=int(row["ordinal"]),
                    note=(row.get("note") or "").strip(),
                )
            )
    return judgements


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion (Wilson 1927).

    Not the textbook normal approximation, which at twenty observations and a
    proportion near either end produces bounds outside [0, 1] and coverage well
    below the nominal 95% -- the case Brown, Cai & DasGupta (2001) recommend
    against it for, and exactly the case here.
    """
    if total == 0:
        return (0.0, 1.0)
    phat = successes / total
    denominator = 1 + z**2 / total
    centre = (phat + z**2 / (2 * total)) / denominator
    spread = z * math.sqrt(phat * (1 - phat) / total + z**2 / (4 * total**2)) / denominator
    return (round(max(0.0, centre - spread), 4), round(min(1.0, centre + spread), 4))


def _counts(judgements: Sequence[Judgement], dimension: str) -> dict[str, int]:
    """Every category of a dimension, zeros included.

    A category nobody chose is a result -- "no reviewed rewrite changed
    behaviour" -- and it disappears from a plain Counter.
    """
    tally = Counter(str(getattr(judgement, dimension)) for judgement in judgements)
    return {member.value: tally.get(member.value, 0) for member in DIMENSIONS[dimension]}


def _cross_tab(
    judgements: Sequence[Judgement], verdicts: dict[str, str]
) -> dict[str, dict[str, int]]:
    """Acceptance against what the compiler said: the point of keeping the sheet blind.

    If every rewrite the compiler accepted is also one the reviewer would merge,
    the automatic verdict is a usable proxy and the thesis may say so. If the two
    disagree, the compiler check is measuring something narrower than it appears
    to, which is the more likely outcome and the more useful one to report.
    """
    table: dict[str, dict[str, int]] = {}
    for judgement in judgements:
        verdict = verdicts.get(judgement.review_id, "unknown")
        row = table.setdefault(verdict, {member.value: 0 for member in Acceptance})
        row[str(judgement.acceptance)] += 1
    return dict(sorted(table.items()))


def summarise(
    judgements: Sequence[Judgement],
    sizes: dict[str, int],
    verdicts: dict[str, str] | None = None,
) -> dict[str, object]:
    """The reviewed sample, per transformation and pooled.

    ``sizes`` is the true number of applied sites per transformation and does
    the reweighting: an acceptance rate read straight off a stratified sample
    would describe a population in which guard clauses are a third of all
    rewrites rather than 3% of them.
    """
    by_refactoring: dict[str, list[Judgement]] = {}
    for judgement in judgements:
        by_refactoring.setdefault(judgement.refactoring, []).append(judgement)

    per: dict[str, dict[str, object]] = {}
    for refactoring in sorted(by_refactoring):
        group = by_refactoring[refactoring]
        merged = sum(1 for j in group if j.acceptance is not Acceptance.REJECT)
        per[refactoring] = {
            "reviewed": len(group),
            "population": sizes.get(refactoring, 0),
            **{name: _counts(group, name) for name in DIMENSIONS},
            "acceptable": round(merged / len(group), 4),
            "acceptable_ci": list(wilson(merged, len(group))),
        }

    # None rather than zero when no stratum has a known size: the reweighting
    # cannot be done, and "0% acceptable" is a claim, not an absence of one.
    covered = sum(sizes.get(name, 0) for name in per)
    pooled: float | None = None
    if covered:
        pooled = round(
            sum(
                float(str(entry["acceptable"])) * sizes.get(name, 0) / covered
                for name, entry in per.items()
            ),
            4,
        )

    summary: dict[str, object] = {
        "reviewed": len(judgements),
        "by_refactoring": per,
        "acceptable_reweighted": pooled,
    }
    if verdicts is not None:
        summary["acceptance_by_verdict"] = _cross_tab(judgements, verdicts)
    return summary
