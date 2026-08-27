"""How much of what the detectors find, the engine can safely rewrite.

    python scripts/evaluate_refactorings.py

Writes ``data/results/refactoring_evaluation.json`` and a per-site CSV. This is
the claim Phase 3 exists to support: *of N detected sites, M were transformed
automatically, and K survived verification* -- together with the distribution of
reasons the rest were declined, which is a result rather than a defect list
(VD-28).

**Scope.** The files MLCQ reviewers examined: around 4500 samples across 522
repositories, deduplicated to the files that hold them. A defensible subset, and
one already established as the corpus for every other number in the thesis.

**Why one file at a time.** Unlike the metric evaluation, this needs no
project-wide context. Deep Nesting, Long Method and Brain Method are decided by
MAXNESTING, MLOC, CC and NOAV, every one of which the parser measures inside a
single method body. ATFD and CBO would need the whole project (VD-16), but no
transformation the engine automates depends on them, so the expensive pass is
not required here.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.analysis import analyze_source  # noqa: E402
from javasmell.detectors.rules import detect_in_class  # noqa: E402
from javasmell.evaluation.corpus import Corpus  # noqa: E402
from javasmell.evaluation.mlcq import load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import VARIANTS  # noqa: E402
from javasmell.refactor.base import Tally  # noqa: E402
from javasmell.refactor.edits import EditConflict, apply_edits  # noqa: E402
from javasmell.refactor.locate import find_site  # noqa: E402
from javasmell.refactor.registry import for_smell  # noqa: E402
from javasmell.refactor.verify import Verdict, check  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "refactoring_evaluation.json"
SITES_NAME = "refactoring_sites.csv"

SITE_COLUMNS = [
    "file",
    "class_name",
    "method",
    "smell",
    "refactoring",
    "applied",
    "refusal",
    "detail",
    "verdict",
    "errors_before",
    "errors_after",
    "introduced",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0, help="Only walk this many files")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip javac and stop at the parse check (much faster, much weaker)",
    )
    return parser


def sampled_files(mlcq: Path, corpus: Corpus) -> list[Path]:
    """Every distinct source file holding an MLCQ sample, in a stable order."""
    found: dict[str, Path] = {}
    for sample in load_samples(mlcq):
        if sample.smell not in VARIANTS or not corpus.has_source(sample):
            continue
        path = corpus.source_path(sample)
        found.setdefault(str(path), path)
    return [found[key] for key in sorted(found)]


def sites_in(source: bytes, path: str) -> list[tuple[str, str, str, str, int]]:
    """Every smell the engine automates, as (class, method, smell, refactoring, line)."""
    try:
        project = analyze_source(source.decode("utf-8"), path)
    except (UnicodeDecodeError, ValueError):
        return []

    found = []
    for unit in project.units:
        for cls in unit.classes:
            for smell in detect_in_class(cls):
                automated = for_smell(smell.smell_type)
                if automated is None or smell.method is None:
                    continue
                name = smell.method.partition("(")[0]
                found.append((cls.name, name, smell.smell_type, automated[0], smell.start_line))
    return found


def run(args: argparse.Namespace) -> tuple[Tally, list[dict[str, object]], Counter[str]]:
    corpus = Corpus(args.corpus)
    files = sampled_files(args.mlcq, corpus)
    if args.limit:
        files = files[: args.limit]

    javac = shutil.which("javac") if args.verify else None
    tally = Tally()
    verdicts: Counter[str] = Counter()
    rows: list[dict[str, object]] = []

    for number, path in enumerate(files, 1):
        try:
            source = Path(path).read_bytes()
        except OSError:
            continue

        for class_name, method, smell_type, refactoring, line in sites_in(source, str(path)):
            automated = for_smell(smell_type)
            if automated is None:
                continue
            _, transform = automated

            site = find_site(str(path), source, class_name, line, method)
            if site is None:
                # The detector and the fresh parse disagree about where the
                # method starts. Counted, never guessed at.
                tally.record_missing()
                continue

            outcome = transform(site)
            tally.record(outcome)

            verdict = Verdict.NOT_CHECKED
            errors_before = errors_after = 0
            introduced = ""
            if outcome.applied:
                try:
                    rewritten = apply_edits(source, outcome.edits)
                except (EditConflict, ValueError) as failure:
                    verdict = Verdict.BROKEN_SYNTAX
                    introduced = str(failure)
                else:
                    result = check(javac, source, rewritten, Path(path).name)
                    verdict = result.verdict
                    errors_before, errors_after = result.errors_before, result.errors_after
                    introduced = result.detail
                verdicts[verdict.value] += 1

            rows.append(
                {
                    "file": str(path),
                    "class_name": class_name,
                    "method": method,
                    "smell": smell_type,
                    "refactoring": refactoring,
                    "applied": int(outcome.applied),
                    "refusal": "" if outcome.refusal is None else outcome.refusal.value,
                    "detail": outcome.detail,
                    "verdict": verdict.value,
                    "errors_before": errors_before,
                    "errors_after": errors_after,
                    "introduced": introduced,
                }
            )

        if not args.quiet and number % 50 == 0:
            print(f"[{number}/{len(files)}] {tally.describe()}", flush=True)

    return tally, rows, verdicts


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.mlcq.exists():
        print(f"MLCQ csv not found: {args.mlcq}", file=sys.stderr)
        return 1
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 1

    tally, rows, verdicts = run(args)

    args.out.mkdir(parents=True, exist_ok=True)
    sites_path = args.out / SITES_NAME
    with sites_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SITE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    by_refactoring: Counter[str] = Counter(
        str(row["refactoring"]) for row in rows if row["applied"]
    )
    summary = {
        "detected": tally.detected,
        "applied": tally.applied,
        "refused": tally.refused,
        "unlocatable": tally.missing,
        "refused_by_reason": {r.value: n for r, n in sorted(tally.refused_by_reason.items())},
        "applied_by_refactoring": dict(sorted(by_refactoring.items())),
        "verdicts": dict(sorted(verdicts.items())),
        "verified_with_javac": args.verify,
        "environment": environment(),
    }
    result_path = args.out / RESULT_NAME
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print()
    print(tally.describe())
    for reason, count in sorted(tally.refused_by_reason.items(), key=lambda p: -p[1]):
        print(f"  declined, {reason.value:<22} {count}")
    print()
    for verdict, count in sorted(verdicts.items(), key=lambda p: -p[1]):
        print(f"  {verdict:<24} {count}")
    print()
    print(f"Wrote {result_path} and {sites_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
