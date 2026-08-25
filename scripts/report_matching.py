"""How many MLCQ samples reach an entity in our model, and why the rest do not.

Every precision and recall figure in the Results chapter is computed over the
samples that matched, so this number *is* the denominator of the evaluation.
Publishing it separately, before any performance figure, is what stops the
shortfall from being invisible.

    python scripts/report_matching.py

Reads the corpus as it stands and re-runs safely; the numbers grow as more
repositories are fetched, so the JSON records how much of the corpus was
present when it ran.

Matching needs the parse only (names and line spans), not the metrics, so
this script parses just the files that carry samples rather than whole
repositories. The rule evaluation cannot take that shortcut, because ATFD, DIT
and CBO are defined against the project's other types (VD-16).
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.corpus import Corpus, long_path  # noqa: E402
from javasmell.evaluation.matcher import (  # noqa: E402
    MatchOutcome,
    MatchResult,
    match_samples,
    summarise,
)
from javasmell.evaluation.mlcq import Sample, load_samples  # noqa: E402
from javasmell.model.entities import ProjectModel  # noqa: E402
from javasmell.parsing.java_parser import JavaParser  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

SUMMARY_NAME = "mlcq_matching.json"
FAILURES_NAME = "mlcq_matching_failures.csv"

FAILURE_COLUMNS = [
    "sample_id",
    "outcome",
    "smell",
    "entity_type",
    "repository",
    "path",
    "start_line",
    "end_line",
    "code_name",
    "detail",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def environment() -> dict[str, str]:
    """What a third party needs in order to get these numbers again."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = ""
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "commit": commit,
    }


def model_for(corpus: Corpus, samples: list[Sample]) -> ProjectModel:
    """Parse just the sampled files of one repository into a project model."""
    parser = JavaParser()
    project = ProjectModel(root=corpus.analysable_root(samples[0]))
    seen: set[str] = set()
    for sample in samples:
        path = str(long_path(corpus.source_path(sample)))
        if path in seen:
            continue
        seen.add(path)
        try:
            project.units.append(parser.parse_file(path))
        except (OSError, UnicodeDecodeError):
            continue
    return project


def match_corpus(corpus: Corpus, samples: list[Sample]) -> list[MatchResult]:
    by_repo: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        by_repo[sample.repository].append(sample)

    results: list[MatchResult] = []
    for repository in sorted(by_repo):
        available: list[Sample] = []
        for sample in by_repo[repository]:
            if corpus.has_source(sample):
                available.append(sample)
            else:
                results.append(
                    MatchResult(sample, MatchOutcome.NO_FILE, detail=sample.relative_path)
                )
        if available:
            results.extend(match_samples(model_for(corpus, available), available))
    return results


def breakdown(results: list[MatchResult], key: str) -> dict[str, dict[str, int]]:
    """Outcome counts split by one attribute of the sample."""
    table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for result in results:
        table[getattr(result.sample, key)][result.outcome.value] += 1
    return {group: dict(counts) for group, counts in sorted(table.items())}


def write_failures(path: Path, results: list[MatchResult]) -> int:
    failures = [r for r in results if not r.ok]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FAILURE_COLUMNS)
        for result in failures:
            sample = result.sample
            writer.writerow(
                [
                    sample.sample_id,
                    result.outcome.value,
                    sample.smell,
                    sample.entity_type,
                    sample.repository,
                    sample.path,
                    sample.start_line,
                    sample.end_line,
                    sample.code_name,
                    result.detail,
                ]
            )
    return len(failures)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.mlcq.exists():
        print(f"MLCQ not found at {args.mlcq}", file=sys.stderr)
        return 1

    samples = load_samples(args.mlcq)
    results = match_corpus(Corpus(args.corpus), samples)
    report = summarise(results)

    # Coverage is read back out of the results rather than measured separately:
    # a second pass over the filesystem would disagree with the first whenever
    # this runs while the corpus is still downloading, and quietly report a
    # match rate above 100%.
    present = [r for r in results if r.outcome is not MatchOutcome.NO_FILE]
    repositories = {r.sample.repository for r in results}
    repositories_present = {r.sample.repository for r in present}

    args.out.mkdir(parents=True, exist_ok=True)
    summary = {
        "environment": environment(),
        "corpus_coverage": {
            "samples_total": report.total,
            "samples_available": len(present),
            "repositories_total": len(repositories),
            "repositories_available": len(repositories_present),
        },
        "outcomes": {outcome.value: count for outcome, count in report.counts.items()},
        "match_rate": round(report.match_rate, 4),
        # Of the samples whose file we actually hold, the rate that measures
        # the matcher rather than the state of the download.
        "match_rate_of_available": round(report.matched / len(present) if present else 0.0, 4),
        "by_entity_type": breakdown(results, "entity_type"),
        "by_smell": breakdown(results, "smell"),
    }
    (args.out / SUMMARY_NAME).write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    failures = write_failures(args.out / FAILURES_NAME, results)

    print(
        f"Corpus coverage: {len(present)}/{report.total} samples "
        f"from {len(repositories_present)}/{len(repositories)} repositories"
    )
    print(report.describe())
    print(f"Matched, of those present: {summary['match_rate_of_available']:.1%}")
    print(f"\nWrote {args.out / SUMMARY_NAME} and {failures} failure rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
