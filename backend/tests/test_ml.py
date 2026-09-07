"""Tests for Approach B's data loading and grouped evaluation.

The expected values are hand-derived from the tiny tables each test writes, and
the point of most of them is the split rather than the model: a leak here would
inflate every figure in the Results chapter and would not otherwise show up.
"""

from __future__ import annotations

import csv
import json

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold

from javasmell.evaluation.dataset import CLASS_METRICS, METHOD_METRICS, columns
from javasmell.ml import training
from javasmell.ml.features import feature_names, load
from javasmell.ml.training import (
    BASELINE,
    OutOfFold,
    agreement,
    combined,
    cross_validated,
    fit_final,
    importances,
    model_zoo,
    save_model,
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


def small_forest():
    """The zoo's forest with ten trees instead of three hundred.

    Permutation importance refits per fold and re-scores ten times per feature,
    so the shipped size turned one test into three quarters of the suite's
    runtime. What these tests check is the out-of-fold machinery around the
    model, not how many trees it has.
    """
    return RandomForestClassifier(
        n_estimators=10, class_weight="balanced", random_state=1, n_jobs=-1
    )


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


def test_cross_validation_hands_the_repositories_to_the_splitter(tmp_path, monkeypatch):
    """The grouping claim itself, read from the call `cross_validated` makes.

    The test above concludes that the split holds because the majority baseline
    predicts one way. That is true but indirect: it would keep passing if the
    splitter were swapped for a row-level one and the majority happened to land
    the same. Asserting disjointness against a splitter the test constructs
    itself would be no better -- it would check scikit-learn rather than this
    package. So the real call is intercepted, and both halves of the claim are
    read off it: that the repositories were passed at all, and that no fold put
    one on both sides. A leak here inflates every figure of Approach B (VD-12)
    and shows up nowhere else.
    """
    records = [
        {"repository": f"git@github.com:acme/{repo}.git", "smelly_mean": smelly}
        for repo in ("one", "two", "three", "four")
        for smelly in ("1", "0", "0")
    ]
    data = load(write_dataset(tmp_path / "d.csv", records), "blob")

    seen: list[tuple[object, list[int], list[int]]] = []
    real = GroupKFold

    class Watched(real):  # type: ignore[misc, valid-type]
        def split(self, x, y=None, groups=None):
            for train_index, test_index in super().split(x, y, groups):
                seen.append((groups, list(train_index), list(test_index)))
                yield train_index, test_index

    monkeypatch.setattr("javasmell.ml.training.GroupKFold", Watched)
    cross_validated(model_zoo()[BASELINE], data, folds=4)

    assert len(seen) == 4, "four repositories, four folds, one held out each time"
    for groups, train_index, test_index in seen:
        assert groups is not None, "the split was made without the repositories"
        trained_on = {groups[i] for i in train_index}
        tested_on = {groups[i] for i in test_index}
        assert not (trained_on & tested_on), "a repository appeared on both sides"


def test_the_deployed_model_is_fitted_on_every_row(tmp_path):
    """`fit_final` is the artefact that ships, and it holds nothing back.

    Its scores are never quoted -- those come from the out-of-fold pass -- but a
    model that shipped fitted on a subset would be a different model from the
    one the manifest describes.
    """
    records = [
        {
            "repository": f"git@github.com:acme/{repo}.git",
            "smelly_mean": smelly,
            "c_WMC": "90.0" if smelly == "1" else "2.0",
        }
        for repo in ("one", "two")
        for smelly in ("1", "1", "0")
    ]
    data = load(write_dataset(tmp_path / "d.csv", records), "blob")

    fitted = fit_final(model_zoo()["random_forest"], data)

    # Four of six rows are positive, so a majority-fitted model would say so for
    # everything; a real fit separates them on WMC, which is 90 against 2.
    assert fitted.predict(data.x).tolist() == data.y.tolist()


def test_the_manifest_travels_with_the_model(tmp_path):
    """A bare `.joblib` cannot say which column was WMC; the manifest must.

    The serving layer reads the feature order from here, and reading it from
    anywhere else is how a model was once asked for medians in one order and
    given them in another.
    """
    records = [{"repository": "git@github.com:acme/one.git", "smelly_mean": s} for s in "1100"]
    data = load(write_dataset(tmp_path / "d.csv", records), "blob")
    fitted = fit_final(model_zoo()[BASELINE], data)
    manifest = {"features": list(data.names), "label": "smelly_mean", "seed": 1}

    save_model(fitted, tmp_path / "models" / "blob.joblib", manifest)

    written = json.loads((tmp_path / "models" / "blob.json").read_text(encoding="utf-8"))
    assert written["features"] == list(data.names)
    assert joblib.load(tmp_path / "models" / "blob.joblib").predict(data.x).tolist() == [
        False,
        False,
        False,
        False,
    ]


def test_agreement_counts_the_four_cells_and_scores_kappa():
    """Hand-derived: 5 shared samples, 1 both, 1 rules only, 1 model only, 2 neither."""
    rules = {"a": True, "b": True, "c": False, "d": False, "e": False, "x": True}
    model = {"a": True, "b": False, "c": True, "d": False, "e": False, "y": True}

    counts = agreement(rules, model)

    assert counts["n"] == 5, "x and y are scored by only one side and drop out"
    assert counts["both"] == 1
    assert counts["only_rules"] == 1
    assert counts["only_model"] == 1
    assert counts["neither"] == 2
    # Observed agreement 3/5; both sides fire 2/5, so expected agreement is
    # (2*2 + 3*3) / 25 = 0.52, and kappa = (0.6 - 0.52) / (1 - 0.52) = 1/6.
    assert counts["kappa"] == pytest.approx(1 / 6)


def test_agreement_on_nothing_shared_reports_no_kappa():
    """Kappa over an empty set is undefined, and is left out rather than faked."""
    counts = agreement({"a": True}, {"b": False})

    assert counts["n"] == 0
    assert "kappa" not in counts


def test_a_deciding_feature_outranks_an_inert_one(tmp_path):
    """The ranking itself, which is what the feature-importance figure shows.

    This says nothing about *where* the importance was measured: it passes
    whether the held-out fold or the training fold is scored, because WMC
    decides the label either way. The out-of-fold property is a separate claim
    and is pinned separately, below.
    """
    records = [
        {
            "repository": f"git@github.com:acme/{repo}.git",
            "smelly_mean": smelly,
            # WMC decides the label; NOF is the same everywhere and decides nothing.
            "c_WMC": "90.0" if smelly == "1" else "2.0",
            "c_NOF": "5.0",
        }
        for repo in ("one", "two", "three", "four")
        for smelly in ("1", "1", "0", "0")
    ]
    data = load(write_dataset(tmp_path / "d.csv", records), "blob")

    scores = importances(small_forest(), data, folds=4)

    assert scores["c_WMC"] > scores["c_NOF"]
    assert scores["c_NOF"] == pytest.approx(0.0, abs=1e-9)


def test_importance_over_single_class_folds_is_zero_rather_than_undefined(tmp_path):
    """Every fold holding one label has no score to degrade, and none is invented.

    The counter of measured folds stays at zero here, and the division that
    averages them never happens. Returning zeros says "not measured" in the same
    shape as "measured as unimportant", which is the honest limit of what this
    function can report -- the caller sees a flat figure rather than a crash
    halfway through a training run.
    """
    records = [
        {"repository": f"git@github.com:acme/{repo}.git", "smelly_mean": "0"}
        for repo in ("one", "two", "three", "four")
        for _ in range(3)
    ]
    data = load(write_dataset(tmp_path / "d.csv", records), "blob")

    scores = importances(small_forest(), data, folds=4)

    assert set(scores) == set(data.names)
    assert all(value == 0.0 for value in scores.values())


def test_the_truth_is_keyed_the_same_way_as_the_prediction():
    """Both maps are read together by the agreement table, so they must align."""
    result = OutOfFold(
        y_true=np.array([True, False]),
        y_pred=np.array([False, False]),
        sample_ids=("a", "b"),
    )

    assert result.truth_by_sample() == {"a": True, "b": False}
    assert result.by_sample() == {"a": False, "b": False}


def test_importance_is_measured_on_the_fold_the_model_did_not_see(tmp_path, monkeypatch):
    """Read from the call itself, because the ranking cannot show this.

    The test above passes whichever fold is scored, so it does not protect the
    property that makes the figure meaningful. The impurity importance a forest
    reports for free is biased towards high-cardinality features -- every
    unbounded count such as CLOC or WMC -- and measuring on training rows
    reintroduces exactly that bias, which is what would make "did the model pick
    the metrics the strategies use?" unanswerable. So the call is intercepted and
    the sizes are compared: with four repositories the held-out fold is a quarter
    of the rows, and the training fold is the other three.
    """
    records = [
        {"repository": f"git@github.com:acme/{repo}.git", "smelly_mean": smelly}
        for repo in ("one", "two", "three", "four")
        for smelly in ("1", "1", "0", "0")
    ]
    data = load(write_dataset(tmp_path / "d.csv", records), "blob")

    scored: list[int] = []
    real = training.permutation_importance

    def watched(estimator, x, y, **kwargs):
        scored.append(len(x))
        return real(estimator, x, y, **kwargs)

    monkeypatch.setattr(training, "permutation_importance", watched)
    importances(small_forest(), data, folds=4)

    assert scored, "no fold was measured at all"
    held_out = len(data.y) // 4
    assert scored == [held_out] * len(scored), (
        f"importance was scored on {scored} rows; the held-out fold is {held_out}"
    )
