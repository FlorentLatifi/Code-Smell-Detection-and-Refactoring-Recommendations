"""Confidence intervals for a score, by resampling repositories.

A single MCC says nothing about how firm it is, and the sets behind the ones in
this project are small enough for that to matter: the rarest smell carries 72
positive samples. Without an interval, a gap of 0.02 between two models and a
gap of 0.25 between two approaches are presented with equal confidence.

**The unit resampled is the repository, not the sample.** Samples drawn from one
project are not independent -- that is the whole reason the evaluation splits on
repository (VD-12) -- so resampling rows would break the assumption the grouped
split exists to protect and produce intervals far too narrow to be honest.
Drawing whole repositories with replacement keeps that dependence intact.

What an interval from here covers, and what it does not: predictions are made
once and held fixed while the evaluation set is resampled, so the interval is
the uncertainty of scoring a finite set of projects. It does *not* include the
variance of retraining on a different sample of projects, which would mean
repeating the cross-validation inside every draw. Every interval this module
produces is therefore a lower bound on the true uncertainty, and callers report
it as one.

This lives in the package rather than in the script that first needed it, for
the reason ``replay`` does: the second caller would otherwise copy it, and a
copy is how two counters drift apart (VD-21).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from javasmell.evaluation.scoring import confusion

# A 95% interval, which is what a reader expects unless told otherwise.
LOW_PERCENTILE = 2.5
HIGH_PERCENTILE = 97.5
RESAMPLES = 2000


@dataclass(frozen=True)
class Interval:
    """A percentile interval and the number of draws that produced it."""

    low: float
    high: float
    median: float
    resamples_used: int
    share_positive: float | None = None

    @property
    def excludes_zero(self) -> bool:
        """Whether the whole interval sits on one side of zero.

        Only meaningful for an interval over a difference; for a difference that
        straddles zero the two things being compared are not distinguishable at
        this level of evidence.
        """
        return self.low > 0.0 or self.high < 0.0

    def to_dict(self) -> dict[str, float | int | None]:
        return {
            "low": self.low,
            "high": self.high,
            "median": self.median,
            "resamples_used": self.resamples_used,
            "share_positive": self.share_positive,
        }


def mcc(truth: NDArray[np.bool_], predicted: NDArray[np.bool_]) -> float | None:
    """MCC through the same ``confusion`` every other score in the project uses."""
    return confusion(zip(truth.tolist(), predicted.tolist(), strict=True)).mcc


def group_positions(groups: Sequence[str]) -> dict[str, NDArray[np.intp]]:
    """Row positions belonging to each repository, so a draw is an array lookup."""
    found: dict[str, list[int]] = defaultdict(list)
    for row, name in enumerate(groups):
        found[name].append(row)
    return {name: np.array(rows, dtype=np.intp) for name, rows in found.items()}


def draw(
    names: Sequence[str],
    positions: dict[str, NDArray[np.intp]],
    rng: np.random.Generator,
) -> NDArray[np.intp]:
    """One bootstrap draw: as many whole repositories as there are, with replacement."""
    chosen = rng.integers(0, len(names), size=len(names))
    return np.concatenate([positions[names[index]] for index in chosen])


def percentile_interval(values: Sequence[float], share_positive: float | None = None) -> Interval:
    """The interval over the draws that produced a defined score.

    A draw can miss a rare positive class entirely, leaving MCC undefined. Those
    draws are excluded and counted rather than read as zero, which would drag
    the interval down and understate the estimate.
    """
    array = np.array(values, dtype=np.float64)
    return Interval(
        low=float(np.percentile(array, LOW_PERCENTILE)),
        high=float(np.percentile(array, HIGH_PERCENTILE)),
        median=float(np.median(array)),
        resamples_used=len(values),
        share_positive=share_positive,
    )


def resample(
    truth: NDArray[np.bool_],
    predictions: dict[str, NDArray[np.bool_]],
    groups: Sequence[str],
    against: Sequence[str] = (),
    reference: str = "model",
    resamples: int = RESAMPLES,
    seed: int = 0,
) -> dict[str, Interval]:
    """An interval per predictor, plus a paired one per named comparison.

    Every predictor is scored on the *same* draw, which is what makes a paired
    difference meaningful: two approaches judged on the same samples must be
    resampled on the same samples too. Building a difference from two
    independent intervals would be needlessly wide and would answer a question
    nobody asked.

    Keys of the returned mapping are the predictor names, plus
    ``difference_<reference>_minus_<name>`` for each entry of ``against``.
    """
    rng = np.random.default_rng(seed)
    positions = group_positions(groups)
    names = tuple(sorted(positions))
    collected: dict[str, list[float]] = {name: [] for name in predictions}
    differences: dict[str, list[float]] = {name: [] for name in against}

    for _ in range(resamples):
        rows = draw(names, positions, rng)
        drawn = truth[rows]
        scores = {name: mcc(drawn, predicted[rows]) for name, predicted in predictions.items()}
        for name, score in scores.items():
            if score is not None:
                collected[name].append(score)
        base = scores.get(reference)
        if base is None:
            continue
        for name in differences:
            other = scores.get(name)
            if other is not None:
                differences[name].append(base - other)

    result = {name: percentile_interval(values) for name, values in collected.items() if values}
    for name, values in differences.items():
        if not values:
            continue
        # An interval clearing zero and a sign kept in every draw say the same
        # thing twice, and readers look for different ones.
        share = float(np.mean(np.array(values) > 0.0))
        result[f"difference_{reference}_minus_{name}"] = percentile_interval(values, share)
    return result
