"""Which clause stops the conjunction strategies from firing.

    python scripts/blocking_conditions.py

Writes ``data/results/blocking_conditions.json`` and a per-miss CSV. Seconds:
every field the clauses read is a column of the committed feature table (VD-23),
so nothing is re-parsed and nothing is re-measured.

**The question.** Chapter 5 reports recall under 0.10 for God Class and not much
better for Feature Envy. That is a true number that tells a reader nothing about
what would have to change. A Lanza & Marinescu strategy is a conjunction, so
every miss has a named cause: one clause, or two, or all three, did not hold.
This counts them.

**What the answer decides.** Misses spread evenly over the clauses would say the
strategy is merely strict, and calibration would move it. Misses piled on one
clause say that measurement is the ceiling. For ATFD the difference matters more
than usual: the parser records syntactic facts and resolves no symbols by
design, so foreign data access is undercounted by construction, and no threshold
recovers what was never counted.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.detectors.thresholds import DEFAULT  # noqa: E402
from javasmell.evaluation.blocking import CONJUNCTIONS, misses, summarise  # noqa: E402
from javasmell.evaluation.mlcq import load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "blocking_conditions.json"
MISSES_NAME = "blocking_conditions_misses.csv"

MISS_COLUMNS = ["sample_id", "smell", "severity", "failed", "sole_blocker", "shortfall"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.mlcq, args.dataset):
        if not path.exists():
            print(f"not found: {path}", file=sys.stderr)
            return 1

    found = misses(args.dataset, load_samples(args.mlcq), DEFAULT)
    per_smell = summarise(found)

    args.out.mkdir(parents=True, exist_ok=True)
    misses_path = args.out / MISSES_NAME
    with misses_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MISS_COLUMNS)
        writer.writeheader()
        for miss in sorted(found, key=lambda m: (m.smell, m.sample_id)):
            writer.writerow(
                {
                    "sample_id": miss.sample_id,
                    "smell": miss.smell,
                    "severity": miss.severity,
                    "failed": " ".join(miss.failed),
                    "sole_blocker": miss.only_blocker or "",
                    "shortfall": " ".join(
                        f"{metric}={value:g}" for metric, value in sorted(miss.shortfall.items())
                    ),
                }
            )

    summary = {
        "strategies": dict(sorted(CONJUNCTIONS.items())),
        "by_smell": per_smell,
        "environment": environment(),
    }
    result_path = args.out / RESULT_NAME
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for smell, entry in per_smell.items():
        assert isinstance(entry, dict)
        print(f"\n{smell}: {entry['missed']} të humbura")
        print(f"  {entry['blocked_by_one_clause']} u bllokuan nga një klauzolë e vetme")
        for metric, count in entry["sole_blocker"].items():
            distance = entry["median_shortfall"][metric]
            print(f"    {metric:<6} {count:>5}   mediana e afrisë {distance:.2f}")
        spread = ", ".join(f"{k} klauzola: {v}" for k, v in entry["clauses_failing"].items())
        print(f"  shpërndarja: {spread}")
    print()
    print(f"Wrote {result_path} and {misses_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
