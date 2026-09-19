"""Approach B restricted to the metrics the published strategy reads.

    python scripts/train_strategy_features.py

Reads ``data/results/mlcq_dataset.csv`` and writes
``data/results/ml_strategy_features.json``. Seconds.

PK2 asks whether a model trained on the same metrics beats the fixed thresholds.
The models of ``train_models.py`` see every metric the system measures, 17 for a
class and 26 for a method, while a strategy reads one to four of them. A win for
those models therefore mixes two effects: where the model puts the cut, and what
else it is allowed to look at. The thesis claimed the first one (VD-132), and
nothing measured it apart from the second.

This script does. Same models, same grouped folds, same seed, same scoring as
``train_models.py``; the only change is the columns. What this model gains over
the rule is what learning the thresholds buys. What the full model gains over
this one is what the extra metrics buy.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import VARIANTS, Confusion  # noqa: E402
from javasmell.ml.features import DEFAULT_LABEL, Dataset, load  # noqa: E402
from javasmell.ml.training import BASELINE, FOLDS, SEED, cross_validated, model_zoo  # noqa: E402

DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_OUT = Path("data/results")
RESULT_NAME = "ml_strategy_features.json"

# The metrics each published strategy reads, as columns of the feature table.
# Blob is scored against God Class (Lanza & Marinescu 2006, p. 80), Data Class
# against p. 88, Feature Envy against p. 84; Long Method is Fowler's size rule.
# The same clauses `detectors/rules.py` evaluates, and nothing more.
STRATEGY_FEATURES: dict[str, tuple[str, ...]] = {
    "blob": ("c_WMC", "c_TCC", "c_ATFD"),
    "data class": ("c_WOC", "c_NOPA", "c_NOAM", "c_WMC"),
    "feature envy": ("m_ATFD", "m_LAA", "m_FDP"),
    "long method": ("m_MLOC",),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--folds", type=int, default=FOLDS)
    return parser


def restricted(data: Dataset, columns: tuple[str, ...]) -> Dataset:
    """The same rows, keeping only ``columns``, in the order given."""
    missing = [name for name in columns if name not in data.names]
    if missing:
        raise SystemExit(f"feature table has no column(s) {missing}")
    index = [data.names.index(name) for name in columns]
    return replace(data, x=data.x[:, index], names=columns)


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
    }


def _mcc(entry: dict[str, object]) -> float:
    """As in ``train_models.py``: an undefined MCC ranks last, not first."""
    value = entry["mcc"]
    return float(value) if isinstance(value, int | float) else -1.0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dataset.exists():
        print(f"dataset not found: {args.dataset}", file=sys.stderr)
        print("Run scripts/build_dataset.py first.", file=sys.stderr)
        return 1

    results: dict[str, dict[str, object]] = {}
    for smell in sorted(VARIANTS):
        if smell not in STRATEGY_FEATURES:
            continue
        data = restricted(load(args.dataset, smell, args.label), STRATEGY_FEATURES[smell])
        if data.positives < args.folds or data.n_groups < 2:
            print(f"{smell}: too few positives or repositories to split; skipped")
            continue

        scored = {
            name: as_dict(cross_validated(model, data, args.folds).confusion())
            for name, model in model_zoo().items()
        }
        best = max((name for name in scored if name != BASELINE), key=lambda n: _mcc(scored[n]))
        results[smell] = {
            "features": list(data.names),
            "samples": len(data.y),
            "positives": data.positives,
            "models": scored,
            "best_model": best,
        }
        print(f"{smell}: {', '.join(data.names)} -> {best}, MCC {scored[best]['mcc']}")

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
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
