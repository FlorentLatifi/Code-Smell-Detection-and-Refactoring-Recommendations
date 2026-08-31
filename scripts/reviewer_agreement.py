"""The ceiling every detector score should be read against.

    python scripts/reviewer_agreement.py

Reads the raw MLCQ review file and writes ``data/results/reviewer_agreement.json``.
Seconds.

This is the one script here that needs ``data/raw/MLCQCodeSmellSamples.csv``
rather than the committed feature table: the table carries the *aggregated*
label for each sample, and agreement is a question about the individual reviews
that the aggregation collapsed. Download it once from the MLCQ dataset (see
``fetch_corpus.py`` for the address); nothing else in the pipeline is affected
if this file is absent, and the thesis section that uses it omits itself.

Why it matters: an MCC of 0.71 against a label the reviewers themselves
reproduce at 0.75 is a very different result from the same number against a
label they reproduce perfectly. Without this figure the Results chapter reports
scores with no scale, and a reader has no way to tell a good detector from an
unreachable target.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.agreement import ceiling  # noqa: E402
from javasmell.evaluation.mlcq import load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import VARIANTS  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_OUT = Path("data/results")
RESULT_NAME = "reviewer_agreement.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def report(results: dict[str, dict[str, object]]) -> None:
    print(f"\n{'smell':<14}{'MCC':>8}{'accuracy':>10}{'pairs':>8}{'one review':>12}")
    print("-" * 52)
    for smell, entry in results.items():
        mcc = entry["mcc"]
        accuracy = entry["accuracy"]
        print(
            f"{smell:<14}"
            f"{(f'{mcc:.3f}' if mcc is not None else '  --'):>8}"
            f"{(f'{accuracy:.3f}' if accuracy is not None else '  --'):>10}"
            f"{entry['pairs']:>8}"
            f"{entry['samples_with_one_review']:>12}"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.mlcq.exists():
        print(f"MLCQ not found at {args.mlcq}", file=sys.stderr)
        print("Download it from https://doi.org/10.5281/zenodo.3590101", file=sys.stderr)
        return 1

    samples = [s for s in load_samples(args.mlcq) if s.smell in VARIANTS]
    measured = ceiling(samples, sorted(VARIANTS))
    results = {smell: found.to_dict() for smell, found in measured.items()}
    report(results)

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "environment": environment(),
        "question": "binary presence, pooled over every pair of reviews on a sample",
        "per_smell": results,
    }
    destination = args.out / RESULT_NAME
    destination.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Wrote {destination}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
