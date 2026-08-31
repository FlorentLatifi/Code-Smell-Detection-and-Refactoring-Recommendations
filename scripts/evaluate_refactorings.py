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
from javasmell.parsing.java_parser import JavaParser  # noqa: E402
from javasmell.refactor.base import Refusal, Tally  # noqa: E402
from javasmell.refactor.edits import EditConflict, apply_edits  # noqa: E402
from javasmell.refactor.locate import FileIndex  # noqa: E402
from javasmell.refactor.registry import for_smell  # noqa: E402
from javasmell.refactor.resolution import resolves  # noqa: E402
from javasmell.refactor.verify import Verdict, check, error_messages  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "refactoring_evaluation.json"
SITES_NAME = "refactoring_sites.csv"

# Nje ekzekutim mbi korpusin e plote zgjat ore. Rreshtat shkojne te nje skedar i
# pjesshem dhe e zevendesojne skedarin real vetem ne fund, dhe skedari i progresit
# lejon rifillimin -- nje ekzekutim u vra te skedari 400 nga 4409 dhe humbi
# gjithcka, sepse rreshtat mbaheshin ne memorie.
PARTIAL_NAME = "refactoring_sites.csv.part"
PROGRESS_NAME = "refactoring_progress.json"

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
    "resolution",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0, help="Only walk this many files")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Ignore any partial run and start over",
    )
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


def load_progress(path: Path, resume: bool) -> tuple[set[str], Tally, Counter[str], Counter[str]]:
    """What an interrupted run got through, if it is still usable.

    A run over the whole corpus takes hours, and one was killed at file 400 of
    4409 with everything lost, because the rows were held in memory until the
    end. The lesson had already been learned once for the feature table and not
    carried over here.
    """
    if not resume or not path.exists():
        return set(), Tally(), Counter(), Counter()
    stored = json.loads(path.read_text(encoding="utf-8"))
    if stored.get("columns") != SITE_COLUMNS:
        print("Partial run used a different schema; starting over.", file=sys.stderr)
        return set(), Tally(), Counter(), Counter()

    tally = Tally(
        detected=stored["detected"],
        applied=stored["applied"],
        missing=stored["missing"],
        refused_by_reason={Refusal(k): v for k, v in stored["refused_by_reason"].items()},
    )
    return (
        set(stored["files"]),
        tally,
        Counter(stored["verdicts"]),
        Counter(stored.get("resolution", {})),
    )


def save_progress(
    path: Path,
    done: set[str],
    tally: Tally,
    verdicts: Counter[str],
    resolutions: Counter[str],
) -> None:
    path.write_text(
        json.dumps(
            {
                "columns": SITE_COLUMNS,
                "files": sorted(done),
                "detected": tally.detected,
                "applied": tally.applied,
                "missing": tally.missing,
                "refused_by_reason": {r.value: n for r, n in tally.refused_by_reason.items()},
                "verdicts": dict(verdicts),
                "resolution": dict(resolutions),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> tuple[Tally, Counter[str], Counter[str], int]:
    corpus = Corpus(args.corpus)
    files = sampled_files(args.mlcq, corpus)
    if args.limit:
        files = files[: args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    partial_path = args.out / PARTIAL_NAME
    progress_path = args.out / PROGRESS_NAME
    done, tally, verdicts, resolutions = load_progress(progress_path, args.resume)
    if done:
        print(f"Resuming: {len(done)} files already written", flush=True)

    javac = shutil.which("javac") if args.verify else None
    handle = partial_path.open("a" if done else "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(handle, fieldnames=SITE_COLUMNS)
    if not done:
        writer.writeheader()

    for number, path in enumerate(files, 1):
        if str(path) in done:
            continue
        rows: list[dict[str, object]] = []
        try:
            source = Path(path).read_bytes()
        except OSError:
            done.add(str(path))
            continue

        # One baseline per file, not one per site: a file holds several sites
        # and its unrewritten state is the same for all of them.
        baseline: set[str] | None = None
        computed = False
        # Built once and shared with every site in this file. Walking the tree
        # per site cost six minutes on the largest generated file alone.
        index = FileIndex(str(path), source, JavaParser().parse_tree(source))

        for class_name, method, smell_type, refactoring, line in sites_in(source, str(path)):
            automated = for_smell(smell_type)
            if automated is None:
                continue
            _, transform = automated

            site = index.find(class_name, line, method)
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
            resolution = ""
            if outcome.applied:
                try:
                    rewritten = apply_edits(source, outcome.edits)
                except (EditConflict, ValueError) as failure:
                    verdict = Verdict.BROKEN_SYNTAX
                    introduced = str(failure)
                else:
                    # Correct and compiling is not the same as helpful: the
                    # rewritten entity is measured again and asked whether the
                    # detector still fires on it.
                    resolution = resolves(rewritten, class_name, method, smell_type).value
                    resolutions[resolution] += 1
                    if javac is not None and not computed:
                        baseline = error_messages(javac, source, Path(path).name)
                        computed = True
                    result = check(javac, source, rewritten, Path(path).name, baseline)
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
                    "resolution": resolution,
                }
            )

        # The file is finished: its rows go out now, not at the end of the run.
        writer.writerows(rows)
        handle.flush()
        done.add(str(path))
        save_progress(progress_path, done, tally, verdicts, resolutions)

        if not args.quiet and number % 50 == 0:
            print(f"[{number}/{len(files)}] {tally.describe()}", flush=True)

    handle.close()
    return tally, verdicts, resolutions, len(files)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.mlcq.exists():
        print(f"MLCQ csv not found: {args.mlcq}", file=sys.stderr)
        return 1
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 1

    tally, verdicts, resolutions, file_count = run(args)

    # Only now does the partial file become the committed one.
    sites_path = args.out / SITES_NAME
    (args.out / PARTIAL_NAME).replace(sites_path)
    (args.out / PROGRESS_NAME).unlink(missing_ok=True)

    with sites_path.open(encoding="utf-8", newline="") as handle:
        by_refactoring: Counter[str] = Counter(
            row["refactoring"] for row in csv.DictReader(handle) if row["applied"] == "1"
        )

    summary = {
        "files": file_count,
        "detected": tally.detected,
        "applied": tally.applied,
        "refused": tally.refused,
        "unlocatable": tally.missing,
        "refused_by_reason": {r.value: n for r, n in sorted(tally.refused_by_reason.items())},
        "applied_by_refactoring": dict(sorted(by_refactoring.items())),
        "verdicts": dict(sorted(verdicts.items())),
        "resolution": dict(sorted(resolutions.items())),
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
    for name, count in sorted(resolutions.items(), key=lambda p: -p[1]):
        print(f"  smell {name:<18} {count}")
    print()
    print(f"Wrote {result_path} and {sites_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
