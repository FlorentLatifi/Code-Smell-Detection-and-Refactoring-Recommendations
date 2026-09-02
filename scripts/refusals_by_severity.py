"""Does the engine refuse precisely where the code is worst?

    python scripts/refusals_by_severity.py

Writes ``data/results/refusals_by_severity.json``.

The corpus run reports that 20.4% of detected sites were transformed and the rest
declined, and VD-28 established that a refusal is a correct outcome rather than a
defect. What neither says is *which* sites they were. A tool that rewrites the
mild cases and backs away from the severe ones is worth much less than that
single percentage suggests, and the percentage alone cannot tell the difference.

**Why this recomputes rather than joins.** ``refactoring_sites.csv`` carries the
outcome of every site but not its severity, and it carries no line number either
-- so joining it back to the detector output on (file, class, method, smell)
would be ambiguous exactly where a class overloads a method, which is common. So
both sides are derived together here, from the same pass, and no join is needed.

**Why that is affordable.** Only the verification step is expensive: `javac` runs
once per rewritten file and cost over twelve seconds on the largest generated
file in the corpus. Nothing here verifies. Whether a transformation *applies* and
why it *refuses* are decided by the parse tree alone, so this pass is minutes
where the full evaluation was hours.

**How it is checked.** ``applied`` and ``refused`` do not depend on `javac`, so
the totals here must equal the ones in ``refactoring_evaluation.json``. They are
compared, and a mismatch is reported rather than quietly averaged over -- it
would mean this pass and the committed one are not measuring the same corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_refactorings import sampled_files  # noqa: E402

from javasmell.analysis import analyze_source  # noqa: E402
from javasmell.detectors.base import Severity  # noqa: E402
from javasmell.detectors.rules import detect_in_class  # noqa: E402
from javasmell.evaluation.corpus import Corpus  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.parsing.java_parser import JavaParser  # noqa: E402
from javasmell.refactor.locate import FileIndex  # noqa: E402
from javasmell.refactor.registry import for_smell  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")
DEFAULT_EVALUATION = Path("data/results/refactoring_evaluation.json")

RESULT_NAME = "refusals_by_severity.json"

#: Worst first, which is the order the question is asked in.
LEVELS = (Severity.CRITICAL.value, Severity.MAJOR.value, Severity.MINOR.value)


@dataclass
class Tally:
    """One cell of the table: what happened to sites of one severity."""

    detected: int = 0
    applied: int = 0
    unlocatable: int = 0
    refused_by_reason: Counter[str] = field(default_factory=Counter)

    @property
    def refused(self) -> int:
        return sum(self.refused_by_reason.values())

    @property
    def rate(self) -> float | None:
        """Share of detected sites the engine rewrote, or None with nothing to divide."""
        judged = self.applied + self.refused
        return round(self.applied / judged, 4) if judged else None

    def to_json(self) -> dict[str, object]:
        return {
            "detected": self.detected,
            "applied": self.applied,
            "refused": self.refused,
            "unlocatable": self.unlocatable,
            "application_rate": self.rate,
            "refused_by_reason": dict(self.refused_by_reason.most_common()),
        }


def measure(files: list[Path], quiet: bool) -> tuple[dict[str, dict[str, Tally]], Tally]:
    """Every automatable site, tallied by smell and by severity.

    The site is located the same way the evaluation locates it -- through a
    :class:`FileIndex` built once per file -- so a site this pass cannot find is
    the same site that pass could not find, and both count it apart from the
    refusals rather than folding it in.
    """
    per_smell: dict[str, dict[str, Tally]] = {}
    overall = Tally()

    for number, path in enumerate(files, 1):
        try:
            source = path.read_bytes()
            project = analyze_source(source.decode("utf-8"), str(path))
        except (OSError, UnicodeDecodeError, ValueError):
            continue

        index = FileIndex(str(path), source, JavaParser().parse_tree(source))
        for unit in project.units:
            for cls in unit.classes:
                for smell in detect_in_class(cls):
                    automated = for_smell(smell.smell_type)
                    if automated is None or smell.method is None:
                        continue

                    level = smell.severity.value
                    cell = per_smell.setdefault(smell.smell_type, {}).setdefault(level, Tally())
                    cell.detected += 1
                    overall.detected += 1

                    name = smell.method.partition("(")[0]
                    site = index.find(cls.name, smell.start_line, name)
                    if site is None:
                        cell.unlocatable += 1
                        overall.unlocatable += 1
                        continue

                    outcome = automated[1](site)
                    if outcome.applied:
                        cell.applied += 1
                        overall.applied += 1
                    else:
                        reason = "unknown" if outcome.refusal is None else outcome.refusal.value
                        cell.refused_by_reason[reason] += 1
                        overall.refused_by_reason[reason] += 1

        if not quiet and number % 500 == 0:
            print(f"  {number}/{len(files)} files", flush=True)

    return per_smell, overall


def agrees_with_evaluation(overall: Tally, evaluation: Path) -> dict[str, object] | None:
    """Compare against the committed run, which measured the same two counts.

    ``applied`` and ``refused`` are decided before verification, so a full run
    with `javac` and this one without it must agree. Disagreement means the two
    passes did not see the same corpus, and that is worth more than any number
    below it.
    """
    if not evaluation.is_file():
        return None
    committed = json.loads(evaluation.read_text(encoding="utf-8"))
    same = (
        committed["applied"] == overall.applied
        and committed["refused"] == overall.refused
        and committed["unlocatable"] == overall.unlocatable
    )
    return {
        "agrees": same,
        "committed": {
            "applied": committed["applied"],
            "refused": committed["refused"],
            "unlocatable": committed["unlocatable"],
        },
        "here": {
            "applied": overall.applied,
            "refused": overall.refused,
            "unlocatable": overall.unlocatable,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--limit", type=int, default=None, help="First N files only")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.mlcq.exists():
        print(f"MLCQ csv not found: {args.mlcq}", file=sys.stderr)
        return 1
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 1

    started = time.perf_counter()
    files = sampled_files(args.mlcq, Corpus(args.corpus))
    if args.limit:
        files = files[: args.limit]
    if not args.quiet:
        print(f"{len(files)} files", flush=True)

    per_smell, overall = measure(files, args.quiet)
    check = None if args.limit else agrees_with_evaluation(overall, args.evaluation)

    print()
    print(f"{'smell':<20} {'severity':<10} {'sites':>7} {'applied':>8} {'rate':>7}")
    for smell in sorted(per_smell):
        for level in LEVELS:
            cell = per_smell[smell].get(level)
            if cell is None:
                continue
            rate = "-" if cell.rate is None else f"{cell.rate:.1%}"
            print(f"{smell:<20} {level:<10} {cell.detected:>7} {cell.applied:>8} {rate:>7}")

    if check is not None and not check["agrees"]:
        print("\nWARNING: totals differ from the committed evaluation", file=sys.stderr)
        print(f"  committed {check['committed']}  here {check['here']}", file=sys.stderr)

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "per_smell": {
            smell: {level: cell.to_json() for level, cell in sorted(levels.items())}
            for smell, levels in sorted(per_smell.items())
        },
        "overall": overall.to_json(),
        "files": len(files),
        "matches_full_evaluation": check,
        # Recorded so the reproduction table in the thesis quotes a measured
        # figure rather than a remembered one.
        "seconds": round(time.perf_counter() - started, 1),
        "environment": environment(),
    }
    path = args.out / RESULT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
