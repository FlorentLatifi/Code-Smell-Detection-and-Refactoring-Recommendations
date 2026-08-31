"""How firm is each number in the Results chapter.

    python scripts/bootstrap_intervals.py

Reads the committed ``mlcq_dataset.csv``, ``rules_evaluation_samples.csv`` and
``threshold_sweep.json``; writes ``data/results/bootstrap_intervals.json``.
Under a minute, because thresholds play no part in the measuring (VD-23) and the
feature table is already built.

Two questions, one run.

**How firm is a single score.** Every MCC in the chapter is a point estimate over
a set whose rarest positive class is 72 samples. The statistics live in
``evaluation.intervals``, which resamples whole repositories rather than rows and
explains there why that is the only defensible unit.

**How much of B's margin is the approach and how much is the threshold.** The
rules are scored twice: once at the published threshold, and once at the value
the project's own sweep found most favourable. The second is *not* a value to
adopt -- picking it because it scores best on the evaluation set is exactly the
test-set fitting §5.5 refuses -- it is the control that separates "the classifier
is better" from "the published threshold was a poor fit for this corpus". Where
the paired difference still clears zero against the swept rule, the finding is
about the two approaches. Where it does not, the chapter has to say so.

Both differences are paired: the two approaches predict the same samples, so they
are scored on the same draw and their correlation is kept.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.detectors.rules import detect_entity  # noqa: E402
from javasmell.detectors.thresholds import DEFAULT as PUBLISHED  # noqa: E402
from javasmell.evaluation.dataset import entities  # noqa: E402
from javasmell.evaluation.intervals import RESAMPLES, mcc, resample  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import (  # noqa: E402
    PRIMARY_VARIANT,
    VARIANTS,
    decode_verdict,
)
from javasmell.ml.features import DEFAULT_LABEL, load  # noqa: E402
from javasmell.ml.training import BASELINE, FOLDS, SEED, cross_validated, model_zoo  # noqa: E402

DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_RULES = Path("data/results/rules_evaluation_samples.csv")
DEFAULT_SWEEP = Path("data/results/threshold_sweep.json")
DEFAULT_OUT = Path("data/results")
RESULT_NAME = "bootstrap_intervals.json"

SMELLS = ("blob", "data class", "feature envy", "long method")
# The rules under both readings, in the order the chapter presents them.
COMPARED = ("rules", "rules_swept")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--folds", type=int, default=FOLDS)
    parser.add_argument("--resamples", type=int, default=RESAMPLES)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def rule_predictions(path: Path, smell: str) -> dict[str, bool]:
    """What Approach A predicted for each sample, as the rules run recorded it."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            record["sample_id"]: decode_verdict(record[f"fired_{PRIMARY_VARIANT}"])
            for record in csv.DictReader(handle)
            if record["smell"] == smell
        }


def best_swept(sweep_path: Path, smell: str) -> tuple[str, float] | None:
    """The knob and value that scored highest anywhere in the published sweep."""
    if not sweep_path.exists():
        return None
    sweep = json.loads(sweep_path.read_text(encoding="utf-8"))
    scored = [
        (point["mcc"], knob, float(point["value"]))
        for knob, points in sweep["per_smell"].get(smell, {}).items()
        for point in points
        if point["mcc"] is not None
    ]
    if not scored:
        return None
    _, knob, value = max(scored)
    return knob, value


def swept_predictions(dataset_path: Path, smell: str, knob: str, value: float) -> dict[str, bool]:
    """Rerun the real detector at one shifted threshold, from the stored table.

    Calls ``detect_entity`` instead of reimplementing the rule, so this cannot
    drift from what the detector does. The raw MLCQ file is not needed: only the
    labels live there, and those already sit in the table.
    """
    thresholds = replace(PUBLISHED, **{knob: value})
    wanted = set(VARIANTS[smell][PRIMARY_VARIANT])
    with dataset_path.open(encoding="utf-8", newline="") as handle:
        return {
            record["sample_id"]: any(
                smell_found.smell_type in wanted
                for smell_found in detect_entity(*entities(record), thresholds)
            )
            for record in csv.DictReader(handle)
            if record["smell"] == smell
        }


def align(verdicts: dict[str, bool], sample_ids: tuple[str, ...]) -> np.ndarray | None:
    """Verdicts in the table's row order, or None when a sample is missing.

    A partial predictor is dropped rather than filled in: a missing verdict is
    an unanswered question, and reading it as "no smell" would invent a negative.
    """
    if not verdicts or not all(sample in verdicts for sample in sample_ids):
        return None
    return np.array([verdicts[sample] for sample in sample_ids], dtype=np.bool_)


def for_smell(smell: str, args: argparse.Namespace) -> dict[str, object]:
    data = load(args.dataset, smell, args.label)

    predictions: dict[str, np.ndarray] = {}
    point: dict[str, float | None] = {}
    for name, model in model_zoo(args.seed).items():
        if name == BASELINE:
            continue
        out_of_fold = cross_validated(model, data, args.folds)
        predictions[name] = out_of_fold.y_pred
        point[name] = out_of_fold.confusion().mcc

    best = max(point, key=lambda name: point[name] if point[name] is not None else -1.0)
    # An alias for whichever model the chapter reports, so every paired
    # difference is taken against the same one the comparison table shows.
    predictions["model"] = predictions[best]

    swept = best_swept(args.sweep, smell)
    knob, value = swept if swept else (None, None)
    candidates = {"rules": rule_predictions(args.rules, smell)}
    if knob is not None and value is not None:
        candidates["rules_swept"] = swept_predictions(args.dataset, smell, knob, value)

    for name, verdicts in candidates.items():
        aligned = align(verdicts, data.sample_ids)
        if aligned is not None:
            predictions[name] = aligned
            point[name] = mcc(data.y, aligned)

    intervals = resample(
        data.y,
        predictions,
        data.groups.tolist(),
        against=[name for name in COMPARED if name in predictions],
        resamples=args.resamples,
        seed=args.seed,
    )
    intervals.pop("model", None)

    return {
        "samples": len(data.y),
        "positives": data.positives,
        "repositories": data.n_groups,
        "best_model": best,
        "swept_knob": knob,
        "swept_value": value,
        "point": point,
        "intervals": {name: band.to_dict() for name, band in intervals.items()},
    }


def report(results: dict[str, dict[str, object]]) -> None:
    print(f"\n{'smell':<14}{'predictor':<20}{'MCC':>8}{'95% interval':>22}")
    print("-" * 64)
    for smell, entry in results.items():
        point = entry["point"]
        intervals = entry["intervals"]
        assert isinstance(point, dict)
        assert isinstance(intervals, dict)
        ordered = (*COMPARED, *sorted(n for n in point if n not in COMPARED))
        for name in ordered:
            if name not in intervals:
                continue
            band = intervals[name]
            value = point[name]
            shown = f"{value:.3f}" if value is not None else "   -- "
            span = f"[{band['low']:.3f}, {band['high']:.3f}]"
            print(f"{smell:<14}{name:<20}{shown:>8}{span:>22}")
        for name, caption in (("rules", "B - A published"), ("rules_swept", "B - A swept")):
            paired = intervals.get(f"difference_model_minus_{name}")
            if not paired:
                continue
            span = f"[{paired['low']:.3f}, {paired['high']:.3f}]"
            verdict = "clears zero" if paired["low"] > 0 else "STRADDLES ZERO"
            print(
                f"{'':<14}{caption:<20}{'':>8}{span:>22}"
                f"   {verdict}, sign kept in {paired['share_positive']:.1%}"
            )
        print()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dataset.exists():
        print(f"feature table missing: {args.dataset}", file=sys.stderr)
        print("Run scripts/build_dataset.py first", file=sys.stderr)
        return 1

    results = {smell: for_smell(smell, args) for smell in SMELLS}
    report(results)

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "environment": environment(),
        "resamples": args.resamples,
        "unit": "repository",
        "label": args.label,
        "per_smell": results,
    }
    destination = args.out / RESULT_NAME
    destination.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Wrote {destination}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
