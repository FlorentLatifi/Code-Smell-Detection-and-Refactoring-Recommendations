"""The committed feature table, as the matrices scikit-learn expects.

Reading goes through the column names ``evaluation.dataset`` writes, so a metric
that is renamed or dropped fails loudly here instead of quietly training a model
on one feature fewer than the last run used.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from javasmell.evaluation.dataset import CLASS_METRICS, METHOD_METRICS

# Blob and Data Class are properties of a class; Long Method and Feature Envy of
# a method. Two feature spaces, therefore two kinds of model -- but the method
# models see their class as well, because Feature Envy is precisely a claim
# about the relationship between a method and the class holding it, and a long
# method inside a God Class is not the same observation as one in a small
# helper.
CLASS_LEVEL = ("blob", "data class")
METHOD_LEVEL = ("long method", "feature envy")

DEFAULT_LABEL = "smelly_mean"


def feature_names(smell: str) -> tuple[str, ...]:
    class_features = tuple(f"c_{name}" for name in CLASS_METRICS)
    if smell in CLASS_LEVEL:
        return class_features
    return class_features + tuple(f"m_{name}" for name in METHOD_METRICS)


@dataclass(frozen=True)
class Dataset:
    """One smell's supervised problem, ready for a grouped split."""

    x: NDArray[np.float64]
    y: NDArray[np.bool_]
    groups: NDArray[np.str_]
    names: tuple[str, ...]
    sample_ids: tuple[str, ...]
    dropped_unlabelled: int
    dropped_incomplete: int

    @property
    def positives(self) -> int:
        return int(self.y.sum())

    @property
    def n_groups(self) -> int:
        return len(set(self.groups.tolist()))

    def describe(self) -> str:
        share = self.positives / len(self.y) if len(self.y) else 0.0
        return (
            f"{len(self.y)} samples, {self.positives} positive ({share:.1%}), "
            f"{self.n_groups} repositories, {len(self.names)} features"
        )


def load(csv_path: str | Path, smell: str, label: str = DEFAULT_LABEL) -> Dataset:
    """Every row for one smell, with its features, label and grouping key.

    Rows the aggregation strategy refuses to label are dropped rather than read
    as negatives, exactly as ``scoring.score`` drops them: an unresolved
    disagreement between reviewers is missing ground truth, not evidence of a
    clean entity. Both counts are kept so the denominator can be stated.
    """
    names = feature_names(smell)
    rows: list[list[float]] = []
    labels: list[bool] = []
    groups: list[str] = []
    ids: list[str] = []
    unlabelled = incomplete = 0

    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            if record["smell"] != smell:
                continue
            if not record[label]:
                unlabelled += 1
                continue
            values = [record[name] for name in names]
            if any(value == "" for value in values):
                incomplete += 1
                continue
            rows.append([float(value) for value in values])
            labels.append(record[label] == "1")
            groups.append(record["repository"])
            ids.append(record["sample_id"])

    return Dataset(
        x=np.array(rows, dtype=np.float64).reshape(len(rows), len(names)),
        y=np.array(labels, dtype=np.bool_),
        groups=np.array(groups, dtype=np.str_),
        names=names,
        sample_ids=tuple(ids),
        dropped_unlabelled=unlabelled,
        dropped_incomplete=incomplete,
    )
