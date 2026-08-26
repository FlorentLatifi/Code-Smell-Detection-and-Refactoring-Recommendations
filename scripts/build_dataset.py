"""The feature table: one row per MLCQ sample, labels beside measurements.

    python scripts/build_dataset.py

Writes ``data/results/mlcq_dataset.csv`` and a companion ``mlcq_dataset.json``
recording how it was produced.

This is the one expensive pass over the corpus -- 690 000 Java files, roughly 95
minutes -- and it exists so that nothing else has to repeat it. Three consumers
need exactly these rows:

* Approach B trains and cross-validates on them, grouped by repository (VD-12);
* the sensitivity analysis of the Results chapter replays the detectors over
  them at swept thresholds, which at 95 minutes per configuration would
  otherwise not be run at all;
* re-scoring Approach A after a detector change reads them back in seconds.

The third is possible because the rules consult nothing beyond ``metrics``,
``kind`` and a method's ``is_constructor``/``is_accessor``, and all of those are
columns here. The file is committed for the same reason the results are: a
committee member with a clean checkout can reproduce every downstream number
without the 4.4 GB corpus and without the 95 minutes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.corpus import Corpus  # noqa: E402
from javasmell.evaluation.dataset import columns, row  # noqa: E402
from javasmell.evaluation.mlcq import load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import VARIANTS  # noqa: E402
from javasmell.evaluation.walk import iter_repositories  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

DATASET_NAME = "mlcq_dataset.csv"
SUMMARY_NAME = "mlcq_dataset.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit", type=int, default=0, help="Only walk this many repositories (trial run)"
    )
    parser.add_argument("--quiet", action="store_true", help="No per-repository progress")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.mlcq.exists():
        print(f"MLCQ csv not found: {args.mlcq}", file=sys.stderr)
        return 1
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 1

    samples = [s for s in load_samples(args.mlcq) if s.smell in VARIANTS]
    args.out.mkdir(parents=True, exist_ok=True)
    dataset_path = args.out / DATASET_NAME

    written = 0
    unreached: dict[str, int] = defaultdict(int)
    by_smell: Counter[str] = Counter()
    by_entity: Counter[str] = Counter()
    repositories = 0

    # Rows are streamed rather than accumulated: the corpus does not fit in
    # memory and neither does a run that dies at repository 400 with nothing
    # written.
    with dataset_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns()))
        writer.writeheader()
        for analysed in iter_repositories(Corpus(args.corpus), samples, args.limit):
            repositories += 1
            for reason, count in analysed.unreached.items():
                unreached[reason] += count
            for resolved in analysed.matched:
                writer.writerow(row(resolved.sample, resolved.cls, resolved.method))
                written += 1
                by_smell[resolved.sample.smell] += 1
                by_entity[resolved.sample.entity_type] += 1
            handle.flush()
            if not args.quiet:
                print(
                    f"[{analysed.number}/{analysed.total}] {analysed.name}: "
                    f"{len(analysed.matched)} rows",
                    flush=True,
                )

    summary = {
        "rows": written,
        "samples_considered": len(samples),
        "repositories": repositories,
        "unreached": dict(sorted(unreached.items())),
        "by_smell": dict(sorted(by_smell.items())),
        "by_entity_type": dict(sorted(by_entity.items())),
        "columns": list(columns()),
        "environment": environment(),
    }
    summary_path = args.out / SUMMARY_NAME
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\n{written} rows from {repositories} repositories; unreached: {dict(unreached)}")
    print(f"Wrote {dataset_path} and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
