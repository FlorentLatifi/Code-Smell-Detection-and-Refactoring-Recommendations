"""How well the rule-based detectors reproduce MLCQ's professional reviewers.

    python scripts/evaluate_rules.py

Writes ``data/results/rules_evaluation.json`` (the figures) and
``rules_evaluation_samples.csv`` (one row per scored sample, so any cell of the
table can be traced back to the code that produced it).

Unlike ``report_matching.py``, this cannot parse only the sampled files: ATFD,
CBO, DIT and TCC are defined against the other types of the project, so a class
measured in isolation would report metrics that are simply wrong (VD-16). Each
repository is therefore analysed whole, one at a time, and released before the
next. That is the run's entire cost: 690 000 Java files, about 95 minutes on a
laptop, single-threaded. Budget for it before Phase 5, whose threshold sweep
repeats this evaluation many times over -- the parse and the measurement do not
depend on the thresholds, so that sweep needs the measured entities cached
rather than this script run again per configuration.

Detection does not depend on how reviewer disagreement is resolved, so the
expensive pass runs once and every aggregation strategy is scored from its
output. The denominator is stated before any score: samples that never reached
an entity are reported, not quietly dropped.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.analysis import analyze_path  # noqa: E402
from javasmell.detectors.rules import detect_all  # noqa: E402
from javasmell.detectors.thresholds import DEFAULT, Thresholds  # noqa: E402
from javasmell.evaluation.corpus import Corpus  # noqa: E402
from javasmell.evaluation.matcher import ProjectIndex  # noqa: E402
from javasmell.evaluation.mlcq import Aggregation, Sample, load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import (  # noqa: E402
    PRIMARY_VARIANT,
    VARIANTS,
    Prediction,
    SmellIndex,
    recall_by_severity,
    score,
)

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

SUMMARY_NAME = "rules_evaluation.json"
SAMPLES_NAME = "rules_evaluation_samples.csv"

SAMPLE_COLUMNS = [
    "sample_id",
    "smell",
    "entity_type",
    "repository",
    "path",
    "start_line",
    "code_name",
    "reviews",
    "severity_mean",
    "unanimous",
    "fired_strategy",
    "fired_with_size",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit", type=int, default=0, help="Only score this many repositories (trial run)"
    )
    parser.add_argument("--quiet", action="store_true", help="No per-repository progress")
    return parser


def evaluate_repository(
    corpus: Corpus, samples: list[Sample], thresholds: Thresholds
) -> tuple[list[Prediction], dict[str, int]]:
    """Analyse one repository whole and score every sample that lands in it."""
    unreached: dict[str, int] = defaultdict(int)
    present = [s for s in samples if corpus.has_source(s)]
    if not present:
        unreached["no_file"] += len(samples)
        return [], dict(unreached)

    project = analyze_path(corpus.analysable_root(present[0]))
    index = ProjectIndex(project)
    smells = SmellIndex(detect_all(project, thresholds))

    predictions: list[Prediction] = []
    for sample in samples:
        if not corpus.has_source(sample):
            unreached["no_file"] += 1
            continue
        match = index.match(sample)
        if not match.ok or match.cls is None:
            unreached[match.outcome.value] += 1
            continue
        entity_line = match.cls.start_line if match.method is None else match.method.start_line
        fired = {
            name: smells.fired(match.cls.file_path, entity_line, detectors)
            for name, detectors in VARIANTS[sample.smell].items()
        }
        predictions.append(Prediction(sample=sample, fired=fired))
    return predictions, dict(unreached)


def evaluate(
    corpus: Corpus, samples: list[Sample], thresholds: Thresholds, limit: int, quiet: bool
) -> tuple[list[Prediction], dict[str, int]]:
    by_repo: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        by_repo[sample.repository].append(sample)

    repositories = sorted(by_repo)
    if limit:
        repositories = repositories[:limit]

    predictions: list[Prediction] = []
    unreached: dict[str, int] = defaultdict(int)
    for number, repository in enumerate(repositories, 1):
        got, missed = evaluate_repository(corpus, by_repo[repository], thresholds)
        predictions.extend(got)
        for reason, count in missed.items():
            unreached[reason] += count
        if not quiet:
            name = repository.partition(":")[2].removesuffix(".git")
            print(f"[{number}/{len(repositories)}] {name}: {len(got)} scored", flush=True)
    return predictions, dict(unreached)


def summarise(predictions: list[Prediction]) -> dict[str, dict[str, dict[str, object]]]:
    """Every figure, for every smell, variant and aggregation strategy."""
    per_smell: dict[str, dict[str, dict[str, object]]] = {}
    for smell, variants in VARIANTS.items():
        entry: dict[str, dict[str, object]] = {}
        for variant in variants:
            entry[variant] = {
                "by_aggregation": {
                    how.value: score(predictions, smell, variant, how).to_dict()
                    for how in Aggregation
                },
                "recall_by_severity": recall_by_severity(predictions, smell, variant),
            }
        per_smell[smell] = entry
    return per_smell


def write_samples(path: Path, predictions: list[Prediction]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(SAMPLE_COLUMNS)
        for prediction in predictions:
            sample = prediction.sample
            primary = prediction.fired[PRIMARY_VARIANT]
            writer.writerow(
                [
                    sample.sample_id,
                    sample.smell,
                    sample.entity_type,
                    sample.repository,
                    sample.path,
                    sample.start_line,
                    sample.code_name,
                    len(sample.reviews),
                    sample.severity_label(Aggregation.MEAN),
                    int(sample.is_unanimous),
                    int(primary),
                    int(prediction.fired.get("with_size", primary)),
                ]
            )


def cell(value: object) -> str:
    """A score, or a visible gap where the matrix leaves it undefined."""
    return "  --  " if value is None else f"{float(value):.3f}"  # type: ignore[arg-type]


def report(summary: dict[str, dict[str, dict[str, object]]]) -> None:
    header = f"{'smell':<14}{'variant':<12}{'P':>8}{'R':>8}{'F1':>8}{'MCC':>8}{'n+':>7}"
    print("\n" + header)
    print("-" * len(header))
    for smell, variants in summary.items():
        for variant, data in variants.items():
            by_aggregation = data["by_aggregation"]
            assert isinstance(by_aggregation, dict)
            m = by_aggregation[Aggregation.MEAN.value]
            print(
                f"{smell:<14}{variant:<12}{cell(m['precision']):>8}{cell(m['recall']):>8}"
                f"{cell(m['f1']):>8}{cell(m['mcc']):>8}{m['support_positive']:>7}"
            )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.mlcq.exists():
        print(f"MLCQ not found at {args.mlcq}", file=sys.stderr)
        return 1

    samples = [s for s in load_samples(args.mlcq) if s.smell in VARIANTS]
    predictions, unreached = evaluate(Corpus(args.corpus), samples, DEFAULT, args.limit, args.quiet)
    if not predictions:
        print("No sample could be scored; is the corpus fetched?", file=sys.stderr)
        return 1

    summary = summarise(predictions)
    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "environment": environment(),
        "thresholds": vars(DEFAULT),
        "scored": len(predictions),
        "unreached": unreached,
        "per_smell": summary,
    }
    (args.out / SUMMARY_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_samples(args.out / SAMPLES_NAME, predictions)

    print(f"\nScored {len(predictions)} samples; unreached: {unreached or 'none'}")
    report(summary)
    print(f"\nWrote {args.out / SUMMARY_NAME} and {args.out / SAMPLES_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
