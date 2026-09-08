"""This project's detectors against PMD, on the same ground truth.

    python scripts/fetch_pmd.py                     # once
    python scripts/compare_with_pmd.py              # hours

Writes ``data/results/pmd_comparison.json`` and ``pmd_comparison_samples.csv``.

**The question.** Chapter 5 compares Approach A against Approach B and both
against MLCQ. That establishes which of the two is better *here*; it says
nothing about whether either is worth having next to a tool a developer can
already install. This script answers the question a committee will ask.

**Why it is a fair comparison and where it is not.** Both sides are scored on
the same 4 534 samples, through the same ``scoring.score``, under the same
aggregation, from the same file: this script recomputes *both* columns from
``rules_evaluation_samples.csv`` rather than quoting one from a previous run, so
the two cannot drift apart. PMD sees the same repositories.

It is not fair in one direction and the thesis says so rather than hiding it.
PMD analyses one compilation unit at a time and is given no compiled classpath,
because the corpus holds no build files (VD-53). Its ``GodClass`` needs ATFD,
which is defined against the project's other types, so PMD computes it from what
one file shows. This project's detectors get the whole project (VD-16). The
handicap is real, it favours this project, and it cannot be removed without
building 513 repositories at their historical commits.

**PMD runs at its shipped defaults.** No property is overridden anywhere in
``pmd_ruleset.xml``. Fitting PMD's thresholds to MLCQ would measure a tool
nobody runs, and would be the same defect as tuning our own thresholds to make a
test pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.corpus import Corpus  # noqa: E402
from javasmell.evaluation.external import (  # noqa: E402
    entity_key,
    entity_of,
    parse_report,
    rules_at,
)
from javasmell.evaluation.mlcq import Aggregation, Sample, load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import Confusion, Prediction, score  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")
DEFAULT_SCORED = Path("data/results/rules_evaluation_samples.csv")
DEFAULT_RULESET = Path("scripts/pmd_ruleset.xml")
DEFAULT_PMD = Path("data/tools/pmd-bin-7.27.0/bin")

RESULT_NAME = "pmd_comparison.json"
SAMPLES_NAME = "pmd_comparison_samples.csv"
PARTIAL_NAME = "pmd_comparison_samples.csv.part"
PROGRESS_NAME = "pmd_comparison_progress.json"

#: Which PMD rules stand for which MLCQ smell, and under what name the result is
#: reported. ``blob`` gets two variants for the same reason this project's own
#: detector does: the strategy alone, and the strategy widened by a size rule.
#:
#: ``feature envy`` has no entry PMD can satisfy. LawOfDemeter is its nearest
#: neighbour and measures message chains, not foreign data access, so it is
#: reported under the name ``law_of_demeter`` and never as a Feature Envy
#: detector. Naming it ``strategy`` would smuggle a claim into a column header.
PMD_VARIANTS: dict[str, dict[str, tuple[str, ...]]] = {
    "blob": {"strategy": ("GodClass",), "with_size": ("GodClass", "NcssCount")},
    "data class": {"strategy": ("DataClass",)},
    "long method": {"strategy": ("NcssCount",)},
    "feature envy": {"law_of_demeter": ("LawOfDemeter",)},
}

#: The variant of *this project's* detectors each PMD variant is set beside.
#: Feature envy has no PMD counterpart, so the pairing is deliberately absent
#: rather than pointed at a rule that measures something else.
OURS_FOR: dict[tuple[str, str], str] = {
    ("blob", "strategy"): "fired_strategy",
    ("blob", "with_size"): "fired_with_size",
    ("data class", "strategy"): "fired_strategy",
    ("long method", "strategy"): "fired_strategy",
}

SAMPLE_COLUMNS = ["sample_id", "smell", "variant", "fired_pmd", "fired_ours", "actual"]

#: A repository that will not finish is a repository whose result is unknown,
#: and unknown is recorded rather than read as "PMD found nothing".
PMD_TIMEOUT_S = 1800


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--scored", type=Path, default=DEFAULT_SCORED)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--pmd", type=Path, default=DEFAULT_PMD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0, help="Only this many repositories")
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    return parser


def launcher(directory: Path) -> Path:
    """PMD's entry point, whose name differs by platform."""
    windows = directory / "pmd.bat"
    return windows if windows.exists() else directory / "pmd"


def run_pmd(pmd: Path, ruleset: Path, directory: Path, report: Path) -> tuple[bool, str]:
    """One repository through PMD, as a fixed argument list with a ceiling.

    Never a shell string and never without a timeout (ENGINEERING.md section 6).

    ``--no-fail-on-error`` matters more than it looks. Without it one source file
    PMD cannot parse ends the whole repository, and the first trial lost SapMachine
    -- the JDK, and one of the corpus's largest contributors of samples -- to a
    single file in the compiler's own tokenizer. Dropping a repository because one
    of its 60 000 files is awkward would bias the comparison in a way no reader
    could see. The unreadable files are counted instead, from the report's own
    error elements, and reported beside the scores.
    """
    command = [
        str(launcher(pmd)),
        "check",
        "-d",
        str(directory),
        "-R",
        str(ruleset),
        "-f",
        "xml",
        "-r",
        str(report),
        "--no-progress",
        "--no-cache",
        "--no-fail-on-error",
        "--no-fail-on-violation",
    ]
    try:
        finished = subprocess.run(
            command, capture_output=True, text=True, timeout=PMD_TIMEOUT_S, check=False
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except OSError as failure:
        return False, str(failure)
    if finished.returncode != 0:
        return False, f"exit {finished.returncode}: {finished.stderr.strip()[:200]}"
    return True, ""


def scored_rows(path: Path) -> dict[str, dict[str, str]]:
    """The samples Approach A was scored on, keyed by sample id."""
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["sample_id"]: row for row in csv.DictReader(handle)}


def load_progress(path: Path, resume: bool) -> tuple[set[str], int, int]:
    if not resume or not path.exists():
        return set(), 0, 0
    stored = json.loads(path.read_text(encoding="utf-8"))
    return set(stored["repositories"]), int(stored["offset"]), int(stored["pmd_errors"])


def save_progress(path: Path, done: set[str], offset: int, errors: int) -> None:
    path.write_text(
        json.dumps(
            {"repositories": sorted(done), "offset": offset, "pmd_errors": errors},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> tuple[int, int, list[str], list[str]]:
    corpus = Corpus(args.corpus)
    wanted = scored_rows(args.scored)
    samples = [s for s in load_samples(args.mlcq) if s.sample_id in wanted]

    by_repository: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        by_repository[sample.repository].append(sample)
    repositories = sorted(by_repository)
    if args.limit:
        repositories = repositories[: args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    partial = args.out / PARTIAL_NAME
    progress = args.out / PROGRESS_NAME
    done, offset, pmd_errors = load_progress(progress, args.resume)
    if done:
        print(f"Resuming: {len(done)} repositories already written", flush=True)
        with partial.open("r+b") as trim:
            trim.truncate(offset)

    handle = partial.open("a" if done else "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(handle, fieldnames=SAMPLE_COLUMNS)
    if not done:
        writer.writeheader()

    failures: list[str] = []
    recovered: list[str] = []
    for number, repository in enumerate(repositories, 1):
        if repository in done:
            continue
        group = by_repository[repository]
        directory = corpus.repo_dir(group[0])
        if not directory.is_dir():
            done.add(repository)
            failures.append(f"{repository}: not fetched")
            continue

        with tempfile.TemporaryDirectory() as scratch:
            report = Path(scratch) / "pmd.xml"
            ok, detail = run_pmd(args.pmd, args.ruleset, directory, report)
            if not ok:
                failures.append(f"{repository}: {detail}")
                done.add(repository)
                save_progress(progress, done, handle.tell(), pmd_errors)
                continue
            violations = parse_report(report, directory)
        pmd_errors += violations.errors
        if violations.recovered:
            recovered.append(repository)

        for sample in group:
            row = wanted[sample.sample_id]
            cls, method = entity_of(row["code_name"])
            fired = rules_at(violations, entity_key(row["path"], cls, method))
            for variant, rules in PMD_VARIANTS.get(sample.smell, {}).items():
                ours = OURS_FOR.get((sample.smell, variant))
                actual = sample.is_smelly(Aggregation.MEAN)
                writer.writerow(
                    {
                        "sample_id": sample.sample_id,
                        "smell": sample.smell,
                        "variant": variant,
                        "fired_pmd": int(bool(fired & set(rules))),
                        "fired_ours": "" if ours is None else row[ours],
                        "actual": "" if actual is None else int(actual),
                    }
                )
        handle.flush()
        done.add(repository)
        save_progress(progress, done, handle.tell(), pmd_errors)
        if number % 10 == 0:
            print(f"[{number}/{len(repositories)}] {len(failures)} failed", flush=True)

    handle.close()
    return len(repositories), pmd_errors, failures, recovered


def summarise(rows: list[dict[str, str]], samples: dict[str, Sample]) -> dict[str, object]:
    """Both sides scored through the same function, from the same rows."""
    result: dict[str, object] = {}
    for smell, variants in PMD_VARIANTS.items():
        for variant in variants:
            selected = [r for r in rows if r["smell"] == smell and r["variant"] == variant]
            if not selected:
                continue
            pmd = [
                Prediction(sample=samples[r["sample_id"]], fired={variant: r["fired_pmd"] == "1"})
                for r in selected
            ]
            entry: dict[str, object] = {
                "scored": len(selected),
                "pmd": _confusion(score(pmd, smell, variant)),
            }
            if selected[0]["fired_ours"] != "":
                ours = [
                    Prediction(
                        sample=samples[r["sample_id"]], fired={variant: r["fired_ours"] == "1"}
                    )
                    for r in selected
                ]
                entry["ours"] = _confusion(score(ours, smell, variant))
            result[f"{smell}/{variant}"] = entry
    return result


def _confusion(matrix: Confusion) -> dict[str, object]:
    """The matrix and its scores, with undefined left as null rather than zero."""
    return {
        "tp": matrix.tp,
        "fp": matrix.fp,
        "fn": matrix.fn,
        "tn": matrix.tn,
        "precision": matrix.precision,
        "recall": matrix.recall,
        "f1": matrix.f1,
        "mcc": matrix.mcc,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.mlcq, args.scored, args.ruleset):
        if not path.exists():
            print(f"not found: {path}", file=sys.stderr)
            return 1
    if not launcher(args.pmd).exists():
        print(f"PMD not found at {args.pmd}; run scripts/fetch_pmd.py", file=sys.stderr)
        return 1

    started = time.monotonic()
    repositories, pmd_errors, failures, recovered = run(args)
    elapsed = time.monotonic() - started

    sites = args.out / SAMPLES_NAME
    (args.out / PARTIAL_NAME).replace(sites)
    (args.out / PROGRESS_NAME).unlink(missing_ok=True)

    with sites.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    wanted = {r["sample_id"] for r in rows}
    samples = {s.sample_id: s for s in load_samples(args.mlcq) if s.sample_id in wanted}

    summary = {
        "pmd_version": "7.27.0",
        "repositories": repositories,
        "repositories_failed": failures,
        "files_pmd_could_not_read": pmd_errors,
        "reports_recovered": recovered,
        "seconds": round(elapsed, 1),
        "aggregation": str(Aggregation.MEAN),
        "by_smell": summarise(rows, samples),
        "environment": environment(),
    }
    result_path = args.out / RESULT_NAME
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print()
    print(f"{'smell / variant':<28}{'MCC PMD':>10}{'MCC ynë':>10}{'n':>8}")
    print("-" * 56)
    by_smell = summary["by_smell"]
    assert isinstance(by_smell, dict)
    for name, entry in by_smell.items():
        pmd_mcc = entry["pmd"]["mcc"]
        ours = entry.get("ours")
        ours_mcc = None if ours is None else ours["mcc"]
        print(
            f"{name:<28}"
            f"{('--' if pmd_mcc is None else f'{pmd_mcc:.3f}'):>10}"
            f"{('--' if ours_mcc is None else f'{ours_mcc:.3f}'):>10}"
            f"{entry['scored']:>8}"
        )
    print()
    print(f"Wrote {result_path} and {sites}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
