"""Tests for Approach B's data loading and grouped evaluation.

The expected values are hand-derived from the tiny tables each test writes, and
the point of most of them is the split rather than the model: a leak here would
inflate every figure in the Results chapter and would not otherwise show up.
"""

from __future__ import annotations

import csv

import numpy as np

from javasmell.evaluation.dataset import CLASS_METRICS, METHOD_METRICS, columns
from javasmell.ml.features import feature_names, load
from javasmell.ml.training import (
    BASELINE,
    OutOfFold,
    combined,
    cross_validated,
    model_zoo,
    usable_folds,
)


def write_dataset(path, records):
    """Write a table with every declared column, filled from `records`."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns()))
        writer.writeheader()
        for index, overrides in enumerate(records):
            row = dict.fromkeys(columns(), "")
            row["sample_id"] = str(index)
            row["smell"] = "blob"
            row["entity_type"] = "class"
            row["repository"] = "git@github.com:acme/one.git"
            row["smelly_mean"] = "0"
            for name in CLASS_METRICS:
                row[f"c_{name}"] = "1.0"
            for name in METHOD_METRICS:
                row[f"m_{name}"] = "1.0"
            row.update(overrides)
            writer.writerow(row)
    return path


def test_class_smells_get_class_features_and_method_smells_get_both():
    """A method model sees its class; Feature Envy is a claim about the pair."""
    assert feature_names("blob") == tuple(f"c_{n}" for n in CLASS_METRICS)
    assert len(feature_names("blob")) == 17
    assert len(feature_names("long method")) == 17 + 9
    assert feature_names("long method")[17] == "m_ATFD"


def test_load_takes_one_smell_and_reports_what_it_dropped(tmp_path):
    path = write_dataset(
        tmp_path / "d.csv",
        [
            {"smell": "blob", "smelly_mean": "1"},
            {"smell": "blob", "smelly_mean": "0"},
            {"smell": "data class", "smelly_mean": "1"},  # a different problem
            {"smell": "blob", "smelly_mean": ""},  # reviewers unresolved
            {"smell": "blob", "smelly_mean": "1", "c_WMC": ""},  # never measured
        ],
    )

    data = load(path, "blob")

    assert len(data.y) == 2
    assert data.positives == 1
    assert data.dropped_unlabelled == 1
    assert data.dropped_incomplete == 1
    assert data.x.shape == (2, 17)


def test_an_unresolved_disagreement_is_not_read_as_a_clean_entity(tmp_path):
    """Dropping matches scoring.score; counting it as negative invents ground truth."""
    path = write_dataset(
        tmp_path / "d.csv",
        [{"smelly_mean": ""}, {"smelly_mean": ""}, {"smelly_mean": "1"}],
    )

    data = load(path, "blob")

    assert len(data.y) == 1
    assert data.positives == 1
    assert data.dropped_unlabelled == 2


def test_the_majority_baseline_is_always_available():
    """Without it an F1 of 0.85 cannot be told apart from guessing."""
    assert BASELINE in model_zoo()


def test_folds_never_exceed_the_number_of_repositories(tmp_path):
    path = write_dataset(
        tmp_path / "d.csv",
        [
            {"repository": f"git@github.com:acme/{name}.git"}
            for name in ("one", "one", "two", "two")
        ],
    )

    data = load(path, "blob")

    assert data.n_groups == 2
    assert usable_folds(data, folds=5) == 2


def test_every_sample_is_predicted_exactly_once_and_by_a_stranger(tmp_path):
    """Out-of-fold means no sample is scored by a model that saw its repository."""
    records = []
    for repo in ("one", "two", "three", "four"):
        for smelly in ("1", "0", "0"):
            records.append(
                {
                    "repository": f"git@github.com:acme/{repo}.git",
                    "smelly_mean": smelly,
                    "c_WMC": "90.0" if smelly == "1" else "2.0",
                }
            )
    path = write_dataset(tmp_path / "d.csv", records)
    data = load(path, "blob")

    result = cross_validated(model_zoo()[BASELINE], data, folds=4)

    assert len(result.y_pred) == len(data.y) == 12
    assert len(result.by_sample()) == 12
    # Every training fold is 3 repositories, 3 positive and 6 negative, so the
    # majority class is "not smelly" in all four of them.
    assert not result.y_pred.any()


def test_confusion_is_built_from_the_pairs_in_order():
    """4 positives, of which 2 predicted; 1 false alarm among the negatives."""
    result = OutOfFold(
        y_true=np.array([True, True, True, True, False, False], dtype=np.bool_),
        y_pred=np.array([True, True, False, False, True, False], dtype=np.bool_),
        sample_ids=("a", "b", "c", "d", "e", "f"),
    )

    matrix = result.confusion()

    assert (matrix.tp, matrix.fn, matrix.fp, matrix.tn) == (2, 2, 1, 1)
    assert matrix.precision == 2 / 3
    assert matrix.recall == 0.5


def test_the_union_and_the_intersection_are_scored_by_hand() -> None:
    """Four samples, worked out on paper.

    truth   A      B      union  intersection
    True    True   False  True   False
    True    False  True   True   False
    False   True   True   True   True
    False   False  False  False  False

    Union: two of the smelly samples are caught (TP=2, FN=0) and the clean one
    both approaches flagged is a false positive (FP=1, TN=1).
    Intersection: neither smelly sample is caught by both (TP=0, FN=2), and the
    one false positive they share survives (FP=1, TN=1).
    """
    rules = {"1": True, "2": False, "3": True, "4": False}
    model = {"1": False, "2": True, "3": True, "4": False}
    truth = {"1": True, "2": True, "3": False, "4": False}

    scored = combined(rules, model, truth)
    assert scored["n"] == 4

    union = scored["union"]
    assert isinstance(union, dict)
    assert (union["tp"], union["fn"], union["fp"], union["tn"]) == (2, 0, 1, 1)

    intersection = scored["intersection"]
    assert isinstance(intersection, dict)
    assert (intersection["tp"], intersection["fn"], intersection["fp"], intersection["tn"]) == (
        0,
        2,
        1,
        1,
    )


def test_a_sample_only_one_side_scored_is_left_out() -> None:
    """The union is taken over the samples both approaches judged, and no others."""
    scored = combined({"1": True, "2": True}, {"1": True}, {"1": True, "2": True})
    assert scored["n"] == 1
