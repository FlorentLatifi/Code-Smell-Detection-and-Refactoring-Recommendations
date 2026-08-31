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
from dataclasses import dataclass, field

from javasmell.detectors.base import Smell
from javasmell.detectors.thresholds import Thresholds
from javasmell.evaluation.mlcq import SEVERITY_RANK, Aggregation, Sample

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
        self._by_site: dict[tuple[str, int], list[Smell]] = {}
        for smell in smells:
            self._by_site.setdefault((smell.file_path, smell.start_line), []).append(smell)

    def fired(self, file_path: str, start_line: int, detectors: tuple[str, ...]) -> bool:
        """Did any of ``detectors`` flag the entity starting at that line?"""
        found = self._by_site.get((file_path, start_line), [])
        return any(smell.smell_type in detectors for smell in found)

    def severity(
        self,
        file_path: str,
        start_line: int,
        detectors: tuple[str, ...],
        thresholds: Thresholds,
    ) -> str | None:
        """How severe those detectors called the entity, or None if none fired."""
        return worst_severity(self._by_site.get((file_path, start_line), []), detectors, thresholds)


def worst_severity(
    smells: Iterable[Smell], detectors: tuple[str, ...], thresholds: Thresholds
) -> str | None:
    """The most severe label among the detectors a variant answers with.

    A variant may join several detectors -- `blob` with size joins God Class and
    Large Class -- and then one entity carries two labels. The worse of the two is
    what the tool would show a user, and a severity measured differently from the
    one displayed would not be measuring the tool.

    One implementation, used by both the corpus pass and the replay. Two would be
    two chances for the severity in the results to stop matching the severity in
    the product, which is how the LOC counters drifted apart (VD-21).
    """
    matched = [s.severity_at(thresholds).value for s in smells if s.smell_type in detectors]
    return max(matched, key=lambda name: SEVERITY_RANK[name]) if matched else None


# Shkalla e ashpërsisë pa `none`: një detektor që nuk ndez nuk cakton ashpërsi,
# ndaj `none` s'është vlerë që sistemi e prodhon dot.
SEVERITY_SCALE = ("minor", "major", "critical")


@dataclass(frozen=True)
class Prediction:
    """What the rules said about one matched sample, per variant.

    ``severity`` carries the label the detector derived, per variant, and is None
    where nothing fired. It is kept beside ``fired`` because the two answer
    different questions -- *is there a smell* and *how bad* -- and VD-06 chose the
    MLCQ scale precisely so the second could be compared without translation.
    """

    sample: Sample
    fired: dict[str, bool]
    severity: dict[str, str | None] = field(default_factory=dict)


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


@dataclass(frozen=True)
class SeverityAgreement:
    """How the derived severity compares with the one the reviewers assigned.

    Measured only where both sides say there is a smell. Anywhere else the two
    scales are not comparable: the reviewers' ``none`` has no counterpart in a
    detector that did not fire, and counting a miss as a severity disagreement
    would fold recall into a measure that is not about recall.
    """

    matrix: dict[str, dict[str, int]]
    exact: float | None
    within_one: float | None
    kappa: float | None
    n: int

    def to_dict(self) -> dict[str, object]:
        def rounded(value: float | None) -> float | None:
            return None if value is None else round(value, 4)

        return {
            "matrix": self.matrix,
            "exact": rounded(self.exact),
            "within_one": rounded(self.within_one),
            "kappa_quadratic": rounded(self.kappa),
            "n": self.n,
        }


def weighted_kappa(pairs: Iterable[tuple[str, str]]) -> float | None:
    """Cohen's kappa with quadratic weights, over :data:`SEVERITY_SCALE`.

    Plain kappa treats "minor called critical" and "minor called major" as the
    same error, which on an ordered scale throws away the thing worth knowing.
    Quadratic weights charge a two-step miss four times a one-step miss, and are
    the usual choice for ordinal agreement.

    Written here rather than taken from scikit-learn because ``evaluation`` must
    not depend on it: ``ml/training.py`` is deliberately the only module that
    imports sklearn, so that the boundary stays one file wide.
    """
    observed = list(pairs)
    if not observed:
        return None

    size = len(SEVERITY_SCALE)
    index = {name: i for i, name in enumerate(SEVERITY_SCALE)}
    counts = [[0] * size for _ in range(size)]
    for actual, predicted in observed:
        counts[index[actual]][index[predicted]] += 1

    total = len(observed)
    rows = [sum(row) / total for row in counts]
    columns = [sum(counts[i][j] for i in range(size)) / total for j in range(size)]

    def weight(i: int, j: int) -> float:
        return ((i - j) ** 2) / ((size - 1) ** 2)

    cells = [(i, j) for i in range(size) for j in range(size)]
    disagreement = sum(weight(i, j) * counts[i][j] / total for i, j in cells)
    expected = sum(weight(i, j) * rows[i] * columns[j] for i, j in cells)
    # Të gjitha vlerësimet në një kuti të vetme: nuk ka mospajtim për të matur, dhe
    # pjesëtimi me zero do të jepte një kappa të shpikur në vend të një hendeku.
    return None if expected == 0 else 1 - disagreement / expected


def severity_agreement(
    predictions: Iterable[Prediction],
    smell: str,
    variant: str,
    how: Aggregation = Aggregation.MEAN,
) -> SeverityAgreement:
    """Compare derived severity with the reviewers', on the samples both flag."""
    pairs: list[tuple[str, str]] = []
    for prediction in predictions:
        if prediction.sample.smell != smell or not prediction.fired.get(variant):
            continue
        actual = prediction.sample.severity_label(how)
        predicted = prediction.severity.get(variant)
        if actual is None or predicted is None or actual == "none":
            continue
        pairs.append((actual, predicted))

    matrix = {actual: dict.fromkeys(SEVERITY_SCALE, 0) for actual in SEVERITY_SCALE}
    for actual, predicted in pairs:
        matrix[actual][predicted] += 1

    total = len(pairs)
    if total == 0:
        return SeverityAgreement(matrix=matrix, exact=None, within_one=None, kappa=None, n=0)

    rank = {name: i for i, name in enumerate(SEVERITY_SCALE)}
    exact = sum(1 for a, p in pairs if a == p) / total
    within_one = sum(1 for a, p in pairs if abs(rank[a] - rank[p]) <= 1) / total
    return SeverityAgreement(
        matrix=matrix,
        exact=exact,
        within_one=within_one,
        kappa=weighted_kappa(pairs),
        n=total,
    )
