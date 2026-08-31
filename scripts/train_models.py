"""Approach B: how well a classifier reproduces MLCQ's reviewers, and how it
compares to the rules.

    python scripts/train_models.py

Reads ``data/results/mlcq_dataset.csv`` -- the committed feature table, built
once by ``build_dataset.py`` -- and writes ``data/results/ml_evaluation.json``.
Seconds, not the 95 minutes the table cost, which is the whole point of having
committed it.

Every figure comes from out-of-fold predictions on a split grouped by repository
(VD-12), scored by the same ``confusion`` the rule detectors are scored by, so
the comparison table at the end is between two approaches and not between two
definitions of precision. The majority-class baseline is reported first for
every smell: on a set that is 78% "none" it is the only thing that says whether
a given F1 means anything at all.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import (  # noqa: E402
    PRIMARY_VARIANT,
    VARIANTS,
    Confusion,
    decode_verdict,
)
from javasmell.ml.features import DEFAULT_LABEL, load  # noqa: E402
from javasmell.ml.training import (  # noqa: E402
    BASELINE,
    FOLDS,
    SEED,
    agreement,
    combined,
    cross_validated,
    fit_final,
    importances,
    library_versions,
    model_zoo,
    save_model,
)

DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_RULES = Path("data/results/rules_evaluation_samples.csv")
DEFAULT_OUT = Path("data/results")
# Models are regenerated, not committed: seconds from the committed table, and a
# pickled estimator is undefined across scikit-learn versions anyway.
DEFAULT_MODELS = Path("data/models")

RESULT_NAME = "ml_evaluation.json"
TOP_FEATURES = 6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--folds", type=int, default=FOLDS)
    parser.add_argument(
        "--models",
        type=Path,
        default=DEFAULT_MODELS,
        help="Where to write the fitted models (regenerated, never committed)",
    )
    return parser


def _mcc(entry: dict[str, object]) -> float:
    """The MCC of one scored model, or a value that always ranks last.

    A confusion matrix with an empty margin reports None, and comparing that
    against a float is what picking the best model would otherwise do.
    """
    value = entry["mcc"]
    return float(value) if isinstance(value, (int, float)) else -1.0


def as_dict(matrix: Confusion) -> dict[str, object]:
    return {
        "tp": matrix.tp,
        "fp": matrix.fp,
        "fn": matrix.fn,
        "tn": matrix.tn,
        "precision": matrix.precision,
        "recall": matrix.recall,
        "f1": matrix.f1,
        "mcc": matrix.mcc,
        "accuracy": matrix.accuracy,
    }


def rule_verdicts(path: Path, smell: str) -> dict[str, bool]:
    """What Approach A predicted for each sample of one smell."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            record["sample_id"]: decode_verdict(record[f"fired_{PRIMARY_VARIANT}"])
            for record in csv.DictReader(handle)
            if record["smell"] == smell
        }


def cell(value: object) -> str:
    if value is None:
        return "  -- "
    if isinstance(value, float):
        return f"{value:6.3f}"
    return f"{value:>6}"


def report(results: dict[str, dict[str, object]]) -> None:
    print(f"\n{'smell':<14}{'model':<20}{'P':>8}{'R':>8}{'F1':>8}{'MCC':>8}")
    print("-" * 66)
    for smell, entry in results.items():
        models = entry["models"]
        assert isinstance(models, dict)
        for name, scores in models.items():
            print(
                f"{smell:<14}{name:<20}"
                f"{cell(scores['precision'])}{cell(scores['recall'])}"
                f"{cell(scores['f1'])}{cell(scores['mcc'])}"
            )
        print()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dataset.exists():
        print(f"dataset not found: {args.dataset}", file=sys.stderr)
        print("Run scripts/build_dataset.py first.", file=sys.stderr)
        return 1

    results: dict[str, dict[str, object]] = {}
    for smell in sorted(VARIANTS):
        data = load(args.dataset, smell, args.label)
        if data.positives < args.folds or data.n_groups < 2:
            print(f"{smell}: too few positives or repositories to split; skipped")
            continue

        print(f"{smell}: {data.describe()}", flush=True)
        scored: dict[str, dict[str, object]] = {}
        truth: dict[str, dict[str, bool]] = {}
        predictions: dict[str, dict[str, bool]] = {}
        for name, model in model_zoo().items():
            folded = cross_validated(model, data, args.folds)
            scored[name] = as_dict(folded.confusion())
            predictions[name] = folded.by_sample()
            truth[name] = folded.truth_by_sample()

        # "Best" is by MCC, the figure that is not fooled by the imbalance.
        ranked = [n for n in scored if n != BASELINE]
        best = max(ranked, key=lambda n: _mcc(scored[n]))

        ranking = sorted(
            importances(model_zoo()[best], data, args.folds).items(),
            key=lambda pair: pair[1],
            reverse=True,
        )
        results[smell] = {
            "data": {
                "samples": len(data.y),
                "positives": data.positives,
                "repositories": data.n_groups,
                "features": len(data.names),
                "dropped_unlabelled": data.dropped_unlabelled,
                "dropped_incomplete": data.dropped_incomplete,
            },
            "models": scored,
            "best_model": best,
            "importances": dict(ranking),
            "top_features": [name for name, _ in ranking[:TOP_FEATURES]],
            "vs_rules": agreement(rule_verdicts(args.rules, smell), predictions[best]),
            "combined": combined(rule_verdicts(args.rules, smell), predictions[best], truth[best]),
        }

        # The shipped model is fitted on everything; the scores above are not
        # its scores, they describe the procedure that produced it.
        slug = smell.replace(" ", "_")
        save_model(
            fit_final(model_zoo()[best], data),
            args.models / f"{slug}.joblib",
            {
                "smell": smell,
                "model": best,
                "features": list(data.names),
                "label": args.label,
                "seed": SEED,
                "trained_on": len(data.y),
                "libraries": library_versions(),
                "scores_are_out_of_fold": True,
                "environment": environment(),
            },
        )

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "per_smell": results,
        "label": args.label,
        "folds": args.folds,
        "seed": SEED,
        "environment": environment(),
    }
    path = args.out / RESULT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report(results)
    for smell, entry in results.items():
        print(f"{smell}: top features = {', '.join(entry['top_features'])}")  # type: ignore[arg-type]
    print()
    print(f"Wrote {path}; {len(results)} models in {args.models}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
