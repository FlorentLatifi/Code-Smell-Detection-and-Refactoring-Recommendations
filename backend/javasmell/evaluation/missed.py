"""What the God Class strategy fails to flag, described rather than guessed.

:mod:`javasmell.evaluation.blocking` answers *which clause* stopped each miss.
That leaves the question a reader asks next and which a clause count cannot
reach: **what kind of class is a reviewer calling a blob when the strategy
disagrees?** Two answers are possible and they point at opposite work.

If the missed classes resemble the flagged ones on some dimension the strategy
never reads -- field count, response set, accessor count -- then the
measurement is incomplete and a clause is missing. If instead they resemble
ordinary classes on every dimension, then no threshold and no extra clause
reaches them, and the disagreement lives in the ground truth rather than in the
detector.

The module measures three things and derives no verdict of its own:

* a **size profile**, quartiles per group, so the missed instances can be put
  beside both the flagged ones and the classes reviewers called clean;
* a **separation** score per metric, the probability that a random miss
  outranks a random negative. That is the Mann-Whitney statistic, read exactly
  as an ROC area: 0.50 is no information, 1.00 is perfect ordering;
* **cohesion saturation**, because TCC has a defined value that no God Class
  clause can accept, and a class carrying it is unreachable at any threshold
  rather than merely far from one.

Every number comes from the committed feature table for the reason
:mod:`javasmell.evaluation.replay` gives: the detectors read nothing else
(VD-23), so this costs a second rather than a re-measurement.
"""

from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from javasmell.detectors.rules import god_class_clauses
from javasmell.detectors.thresholds import DEFAULT, Thresholds
from javasmell.evaluation.dataset import CLASS_METRICS, entities
from javasmell.evaluation.mlcq import Aggregation, Sample
from javasmell.evaluation.replay import replay
from javasmell.evaluation.scoring import recall_by_severity as _recall_by_severity

#: The value ``_tight_class_cohesion`` returns for a class with fewer than two
#: public instance methods. Bieman & Kang leave TCC undefined there -- cohesion
#: between method pairs needs pairs -- and the calculator resolves the gap
#: toward "perfectly cohesive". Every God Class clause wants TCC *below* a
#: threshold, so a class carrying this value sits outside the strategy's reach
#: however the thresholds are set. Static utility classes carry it by
#: construction, and those are classes a reviewer labels blob readily.
SATURATED_TCC = 1.0

#: Metrics printed beside a saturated class, chosen because they are the ones
#: that make the case: the class is large on every count and still unreachable.
SATURATED_COLUMNS = ("CLOC", "NOM", "NOF", "WMC")

#: The metrics a reader reaches for when asking "was this class big". The
#: "below the median negative" count is reported for these three only, because
#: the comparison is rhetorical as much as statistical and three numbers carry
#: it where seventeen would bury it.
SIZE_METRICS = ("CLOC", "NOM", "WMC")


@dataclass(frozen=True)
class Groups:
    """The four cells of one confusion matrix, each keeping its feature rows.

    The rows are kept rather than the counts because the counts are already in
    ``rules_evaluation.json``; what is new here is what the entities in each
    cell look like, and that needs the measurements.
    """

    caught: list[Mapping[str, str]] = field(default_factory=list)
    missed: list[Mapping[str, str]] = field(default_factory=list)
    spurious: list[Mapping[str, str]] = field(default_factory=list)
    negative: list[Mapping[str, str]] = field(default_factory=list)


def partition(
    dataset_path: str | Path,
    samples: Iterable[Sample],
    smell: str,
    variant: str,
    thresholds: Thresholds = DEFAULT,
    how: Aggregation = Aggregation.MEAN,
) -> Groups:
    """Split one smell's rows by what the reviewers said and what the rules said.

    The verdicts come from :func:`replay` rather than from a second evaluation
    written here, so these are the same cells ``evaluate_rules`` counts. A copy
    would be free to disagree, and one that disagreed by a single row would be
    very hard to notice.
    """
    with Path(dataset_path).open(encoding="utf-8", newline="") as handle:
        rows = {record["sample_id"]: record for record in csv.DictReader(handle)}

    groups = Groups()
    for prediction in replay(dataset_path, list(samples), thresholds):
        sample = prediction.sample
        record = rows.get(sample.sample_id)
        if sample.smell != smell or record is None:
            continue
        fired = prediction.fired[variant]
        if sample.is_smelly(how):
            (groups.caught if fired else groups.missed).append(record)
        else:
            (groups.spurious if fired else groups.negative).append(record)
    return groups


def _values(rows: Sequence[Mapping[str, str]], metric: str) -> list[float]:
    return sorted(float(row[f"c_{metric}"]) for row in rows if row[f"c_{metric}"] != "")


def quartiles(rows: Sequence[Mapping[str, str]], metric: str) -> tuple[float, float, float]:
    """Lower quartile, median and upper quartile, by nearest rank.

    Nearest rank rather than interpolation because these are counts -- methods,
    fields, lines -- and an interpolated 8.5 methods is a number no class has.
    """
    values = _values(rows, metric)
    if not values:
        return (float("nan"), float("nan"), float("nan"))

    def pick(share: float) -> float:
        return values[min(len(values) - 1, int(share * len(values)))]

    return pick(0.25), pick(0.5), pick(0.75)


def separation(
    missed: Sequence[Mapping[str, str]], negative: Sequence[Mapping[str, str]], metric: str
) -> float:
    """P(a missed instance outranks a class the reviewers called clean), ties split.

    The Mann-Whitney U statistic normalised by the pair count, which is the same
    quantity as the area under an ROC curve. Preferred to a difference of
    medians because it answers the operative question directly: could *any*
    threshold on this one metric tell the two groups apart.
    """
    misses = _values(missed, metric)
    cleans = _values(negative, metric)
    if not misses or not cleans:
        return float("nan")
    total = 0.0
    for value in misses:
        below = bisect_left(cleans, value)
        equal = bisect_right(cleans, value) - below
        total += below + equal / 2
    return total / (len(misses) * len(cleans))


def below_median(
    missed: Sequence[Mapping[str, str]], negative: Sequence[Mapping[str, str]], metric: str
) -> int:
    """How many misses are no larger than the median class the reviewers cleared.

    A blunter statement of what the profile already shows, kept because it is
    the one a reader remembers: a miss on this side of the line is not a blob
    the strategy was too strict about, it is a small class.
    """
    cleans = _values(negative, metric)
    if not cleans:
        return 0
    middle = cleans[min(len(cleans) - 1, len(cleans) // 2)]
    return sum(1 for value in _values(missed, metric) if value <= middle)


@dataclass(frozen=True)
class Saturated:
    """One miss the cohesion clause can never accept, whatever the threshold."""

    sample_id: str
    class_name: str
    path: str
    metrics: Mapping[str, float]
    #: Clauses of the God Class strategy this row failed, in strategy order.
    failed: tuple[str, ...]


def saturated_cohesion(
    missed: Sequence[Mapping[str, str]], thresholds: Thresholds = DEFAULT
) -> list[Saturated]:
    """Misses that pass the complexity clause but carry :data:`SATURATED_TCC`.

    Restricted to those that pass complexity on purpose. A small class with
    saturated cohesion is evidence of nothing, since it would fail on size
    anyway; a large one is a class the strategy cannot reach for a reason that
    has nothing to do with calibration.
    """
    found = []
    for record in missed:
        cls, _ = entities(record)
        if cls.metrics.get("TCC") != SATURATED_TCC:
            continue
        failed = tuple(
            clause.metric for clause in god_class_clauses(cls, thresholds) if not clause.satisfied
        )
        if "WMC" in failed:
            continue
        found.append(
            Saturated(
                sample_id=record["sample_id"],
                class_name=record["class_name"],
                path=record["path"],
                metrics={name: cls.metrics.get(name, 0.0) for name in SATURATED_COLUMNS},
                failed=failed,
            )
        )
    return sorted(found, key=lambda item: -item.metrics["WMC"])


def profile(groups: Groups, metrics: Sequence[str] = CLASS_METRICS) -> dict[str, object]:
    """Everything the module measures, in the shape the results file stores."""
    cells = {"caught": groups.caught, "missed": groups.missed, "negative": groups.negative}
    return {
        "support": {name: len(rows) for name, rows in cells.items()}
        | {"spurious": len(groups.spurious)},
        "quartiles": {
            metric: {
                name: [round(value, 4) for value in quartiles(rows, metric)]
                for name, rows in cells.items()
            }
            for metric in metrics
        },
        "separation": {
            metric: round(separation(groups.missed, groups.negative, metric), 4)
            for metric in metrics
        },
        "below_negative_median": {
            metric: below_median(groups.missed, groups.negative, metric)
            for metric in SIZE_METRICS
            if metric in metrics
        },
    }


def recall_by_severity(
    dataset_path: str | Path,
    samples: Iterable[Sample],
    smell: str,
    variant: str,
    thresholds: Thresholds = DEFAULT,
    how: Aggregation = Aggregation.MEAN,
) -> dict[str, dict[str, int | float | None]]:
    """Recall split by the severity the reviewers assigned, at one aggregation.

    ``scoring.recall_by_severity`` reports this split for the default
    aggregation only, and under MEAN there is barely a gradient left to see.
    Most MLCQ samples carry two reviews, so one "none" against one severe
    verdict averages down a whole step, and the severe end of the scale empties
    out: no blob sample survives MEAN as critical. Under MAX the labels keep
    their spread, and whether recall rises with severity is exactly the question
    of whether the strategy disagrees with reviewers at random or only where
    they were least sure themselves.
    """
    return _recall_by_severity(replay(dataset_path, list(samples), thresholds), smell, variant, how)


__all__ = [
    "SATURATED_COLUMNS",
    "SATURATED_TCC",
    "SIZE_METRICS",
    "Groups",
    "Saturated",
    "below_median",
    "partition",
    "profile",
    "quartiles",
    "recall_by_severity",
    "saturated_cohesion",
    "separation",
]
