"""Turning detector output and MLCQ labels into the numbers of Chapter 5.

Kept out of the scripts because it is analysis, not orchestration, and because
every figure it produces has to be testable against a matrix worked out by
hand. The scripts decide *what* to run over; this module decides what the run
means.

The expensive part of an evaluation (parse, measure, detect) does not depend on
how reviewer disagreement is resolved, so it happens once and produces
:class:`Prediction` records. Every aggregation strategy is then scored from
those records, which is what makes the sensitivity table in the Results chapter
cheap enough to always report rather than a separate experiment.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from javasmell.detectors.base import Smell
from javasmell.evaluation.mlcq import Aggregation, Sample

# Which detector outputs answer each MLCQ smell (VD-22).
#
# `blob` carries two entries on purpose. The primary one is the published
# strategy of Lanza & Marinescu; the variant adds our size-only Large Class,
# which VD-09 deliberately keeps separate. Reporting both measures how much of
# what reviewers call a blob is explained by size alone. The other three smells
# map one-to-one: Brain Method needs no variant of its own because LOC > 35
# makes it a strict subset of Long Method's LOC > 30.
VARIANTS: dict[str, dict[str, tuple[str, ...]]] = {
    "blob": {
        "strategy": ("GodClass",),
        "with_size": ("GodClass", "LargeClass"),
    },
    "data class": {"strategy": ("DataClass",)},
    "long method": {"strategy": ("LongMethod",)},
    "feature envy": {"strategy": ("FeatureEnvy",)},
}

PRIMARY_VARIANT = "strategy"


class SmellIndex:
    """The smells one analysed project produced, keyed by where they landed.

    Both sides of the lookup come from the same ``ProjectModel``, so the file
    path needs no normalising: it is the identical string the parser recorded.
    """

    def __init__(self, smells: Iterable[Smell]) -> None:
        self._by_site: dict[tuple[str, int], set[str]] = {}
        for smell in smells:
            self._by_site.setdefault((smell.file_path, smell.start_line), set()).add(
                smell.smell_type
            )

    def fired(self, file_path: str, start_line: int, detectors: tuple[str, ...]) -> bool:
        """Did any of ``detectors`` flag the entity starting at that line?"""
        found = self._by_site.get((file_path, start_line))
        return found is not None and not found.isdisjoint(detectors)


@dataclass(frozen=True)
class Prediction:
    """What the rules said about one matched sample, per variant."""

    sample: Sample
    fired: dict[str, bool]


@dataclass(frozen=True)
class Confusion:
    """A binary confusion matrix and the scores derived from it.

    Both precision and MCC are undefined for some matrices rather than zero;
    they are reported as ``None`` so that a chapter table shows a gap instead
    of a misleading 0.0. MCC is included because it is the figure that does not
    flatter a detector on a data set where 78% of the labels are "none": a
    classifier that never fires scores 0 here and 0.88 on accuracy.
    """

    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def precision(self) -> float | None:
        predicted = self.tp + self.fp
        return self.tp / predicted if predicted else None

    @property
    def recall(self) -> float | None:
        actual = self.tp + self.fn
        return self.tp / actual if actual else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or p + r == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> float | None:
        return (self.tp + self.tn) / self.total if self.total else None

    @property
    def mcc(self) -> float | None:
        """Matthews correlation coefficient; None when a margin is empty."""
        denominator = math.sqrt(
            float(self.tp + self.fp)
            * float(self.tp + self.fn)
            * float(self.tn + self.fp)
            * float(self.tn + self.fn)
        )
        if denominator == 0:
            return None
        return (self.tp * self.tn - self.fp * self.fn) / denominator

    def to_dict(self) -> dict[str, object]:
        def rounded(value: float | None) -> float | None:
            return None if value is None else round(value, 4)

        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "support_positive": self.tp + self.fn,
            "precision": rounded(self.precision),
            "recall": rounded(self.recall),
            "f1": rounded(self.f1),
            "accuracy": rounded(self.accuracy),
            "mcc": rounded(self.mcc),
        }


def confusion(pairs: Iterable[tuple[bool, bool]]) -> Confusion:
    """Build a matrix from ``(actual, predicted)`` pairs."""
    tp = fp = fn = tn = 0
    for actual, predicted in pairs:
        if actual and predicted:
            tp += 1
        elif actual and not predicted:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    return Confusion(tp=tp, fp=fp, fn=fn, tn=tn)


def score(
    predictions: Iterable[Prediction],
    smell: str,
    variant: str,
    how: Aggregation = Aggregation.MEAN,
) -> Confusion:
    """Score one smell under one variant and one aggregation strategy.

    Samples the strategy refuses to label (``UNANIMOUS`` on a split review)
    are dropped rather than counted as negatives: treating an unresolved
    disagreement as "no smell" would silently invent ground truth.
    """
    pairs = []
    for prediction in predictions:
        if prediction.sample.smell != smell:
            continue
        actual = prediction.sample.is_smelly(how)
        if actual is None:
            continue
        pairs.append((actual, prediction.fired[variant]))
    return confusion(pairs)


def recall_by_severity(
    predictions: Iterable[Prediction],
    smell: str,
    variant: str,
    how: Aggregation = Aggregation.MEAN,
) -> dict[str, dict[str, int | float | None]]:
    """Caught versus missed at each severity the reviewers assigned.

    The question this answers is whether the rules degrade gracefully: a
    detector that finds the critical cases and misses the minor ones is far
    more useful than one with the same recall spread evenly, and the two are
    indistinguishable in a single F1.
    """
    buckets: dict[str, list[bool]] = {}
    for prediction in predictions:
        if prediction.sample.smell != smell:
            continue
        label = prediction.sample.severity_label(how)
        if label is None or label == "none":
            continue
        buckets.setdefault(label, []).append(prediction.fired[variant])
    return {
        label: {
            "support": len(hits),
            "caught": sum(hits),
            "recall": round(sum(hits) / len(hits), 4) if hits else None,
        }
        for label, hits in sorted(buckets.items())
    }


# ----------------------------------------------------------------------
# The CSV encoding of a verdict
# ----------------------------------------------------------------------
# Both directions live here because they are one contract. A reader that
# guessed "True" against a writer emitting "1" is not a crash: it silently
# reports that the detectors never fired, which reads as a finding rather than
# a bug. Decoding accepts either spelling and refuses anything else, so a
# changed format stops the run instead of zeroing a comparison table.
_TRUE = frozenset({"1", "True", "true"})
_FALSE = frozenset({"0", "False", "false"})


def encode_verdict(fired: bool) -> str:
    return "1" if fired else "0"


def decode_verdict(raw: str) -> bool:
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ValueError(f"not a detector verdict: {raw!r}")
