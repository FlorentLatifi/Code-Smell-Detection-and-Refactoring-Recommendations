"""Approach B: the models, and the only split that does not flatter them.

Two things here are load-bearing for the thesis rather than for the code.

*The majority classifier is not decoration.* On a set where 78% of the labels
are "none", a model that has learned nothing can post a respectable accuracy,
and the only way a reader can tell the difference is to see what predicting the
majority class scores on the very same split. It is reported for every smell.

*The split is grouped by repository (VD-12).* Samples from one project share
authors, conventions and often copy-pasted code; a random row-level split puts
near-duplicates on both sides and inflates every figure. Grouping by repository
is the difference between "the model generalises to a new project" and "the
model recognises this project", and only the first is a claim worth making.

Scoring reuses ``evaluation.scoring.confusion``, the function that scores the
rule detectors, so the A-versus-B table compares two approaches rather than two
definitions of precision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import sklearn
from numpy.typing import NDArray
from sklearn.base import BaseEstimator, clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from javasmell.evaluation.scoring import Confusion, confusion
from javasmell.ml.features import Dataset

SEED = 20260826
FOLDS = 5
PERMUTATION_REPEATS = 10

BASELINE = "majority"


def model_zoo(seed: int = SEED) -> dict[str, BaseEstimator]:
    """The four models, in increasing order of what they are allowed to learn.

    No neural network: the data set is small, the features are tabular, and a
    reviewer can ask why a Random Forest fired and get an answer. That is worth
    more here than a point of F1 (see the roadmap, Phase 2).

    Every model that can express a class weight is given a balanced one. The
    alternative -- oversampling the minority -- would duplicate rows across the
    fold boundary and quietly undo the grouping above.
    """
    return {
        BASELINE: DummyClassifier(strategy="most_frequent"),
        "logistic": Pipeline(
            [
                # Only the linear model needs this; the trees are invariant to
                # monotone rescaling and LCOM would otherwise dominate TCC by
                # three orders of magnitude.
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=seed, n_jobs=-1
        ),
        "gradient_boosting": HistGradientBoostingClassifier(
            class_weight="balanced", random_state=seed
        ),
    }


@dataclass(frozen=True)
class OutOfFold:
    """Every sample predicted exactly once, by a model that never saw its project."""

    y_true: NDArray[np.bool_]
    y_pred: NDArray[np.bool_]
    sample_ids: tuple[str, ...]

    def confusion(self) -> Confusion:
        return confusion(zip(self.y_true.tolist(), self.y_pred.tolist(), strict=True))

    def by_sample(self) -> dict[str, bool]:
        return dict(zip(self.sample_ids, self.y_pred.tolist(), strict=True))

    def truth_by_sample(self) -> dict[str, bool]:
        """The label each sample carried, keyed the same way as the prediction."""
        return dict(zip(self.sample_ids, self.y_true.tolist(), strict=True))


def usable_folds(data: Dataset, folds: int = FOLDS) -> int:
    """GroupKFold cannot make more folds than there are repositories."""
    return min(folds, data.n_groups)


def cross_validated(model: BaseEstimator, data: Dataset, folds: int = FOLDS) -> OutOfFold:
    """Collect out-of-fold predictions over a repository-grouped split.

    Predicting each sample once, from a model trained without its repository,
    gives one prediction per sample -- the same shape the rule detectors produce
    -- so the two approaches can be compared sample by sample and not merely
    summary by summary.
    """
    splitter = GroupKFold(n_splits=usable_folds(data, folds))
    predicted = np.zeros(len(data.y), dtype=np.bool_)
    for train_index, test_index in splitter.split(data.x, data.y, data.groups):
        fitted = clone(model)
        fitted.fit(data.x[train_index], data.y[train_index])
        predicted[test_index] = fitted.predict(data.x[test_index]).astype(np.bool_)
    return OutOfFold(y_true=data.y, y_pred=predicted, sample_ids=data.sample_ids)


def importances(
    model: BaseEstimator, data: Dataset, folds: int = FOLDS, seed: int = SEED
) -> dict[str, float]:
    """Permutation importance, measured on each held-out fold and averaged.

    Measured on data the model was not fitted on, because the impurity-based
    importance a forest reports for free is biased towards high-cardinality
    features -- here, every unbounded count such as CLOC or WMC -- which is
    exactly the bias that would make the answer to "did the model choose the
    metrics the detection strategies use?" meaningless.
    """
    splitter = GroupKFold(n_splits=usable_folds(data, folds))
    totals = np.zeros(len(data.names), dtype=np.float64)
    measured = 0
    for train_index, test_index in splitter.split(data.x, data.y, data.groups):
        if len(set(data.y[test_index].tolist())) < 2:
            # A fold with one class present has no score to degrade.
            continue
        fitted = clone(model)
        fitted.fit(data.x[train_index], data.y[train_index])
        result = permutation_importance(
            fitted,
            data.x[test_index],
            data.y[test_index],
            n_repeats=PERMUTATION_REPEATS,
            random_state=seed,
            scoring="matthews_corrcoef",
        )
        totals += result.importances_mean
        measured += 1
    if not measured:
        return dict.fromkeys(data.names, 0.0)
    return dict(zip(data.names, (totals / measured).tolist(), strict=True))


def agreement(rules: dict[str, bool], model: dict[str, bool]) -> dict[str, float | int]:
    """How the two approaches' verdicts relate, on the samples both of them scored.

    Cohen's kappa rather than raw agreement, because two detectors that both
    almost never fire agree on 90% of a set where 78% of the labels are "none"
    while having learned nothing from each other. The four cells are reported
    beside it: the interesting question for the thesis is not how often A and B
    agree but what each one catches alone.
    """
    shared = sorted(set(rules) & set(model))
    both = only_rules = only_model = neither = 0
    for sample_id in shared:
        a, b = rules[sample_id], model[sample_id]
        if a and b:
            both += 1
        elif a:
            only_rules += 1
        elif b:
            only_model += 1
        else:
            neither += 1

    counts: dict[str, float | int] = {
        "n": len(shared),
        "both": both,
        "only_rules": only_rules,
        "only_model": only_model,
        "neither": neither,
    }
    if shared:
        counts["kappa"] = float(
            cohen_kappa_score([rules[i] for i in shared], [model[i] for i in shared])
        )
    return counts


def fit_final(model: BaseEstimator, data: Dataset) -> BaseEstimator:
    """Fit on everything, producing the model that ships.

    This is deliberately not the model the scores describe. Those come from
    out-of-fold predictions, and they characterise the *procedure*: what one
    gets by training this pipeline on some projects and applying it to a project
    it has never seen. The artefact below is that same procedure run once more
    with no data held back, which is the right thing to deploy and the wrong
    thing to quote a number for. Nothing here may be re-scored on the training
    rows, and the manifest says so.
    """
    fitted = clone(model)
    fitted.fit(data.x, data.y)
    return fitted


def save_model(fitted: BaseEstimator, path: Path, manifest: dict[str, object]) -> None:
    """Write the fitted model beside a manifest describing how to use it.

    A bare ``.joblib`` is close to useless six months later: it takes an
    unlabelled array and cannot say which column was WMC. The manifest carries
    the feature order, the label, the seed and the library versions, because
    unpickling an estimator built by a different scikit-learn is undefined
    rather than merely risky.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted, path)
    path.with_suffix(".json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def library_versions() -> dict[str, str]:
    return {
        "scikit-learn": sklearn.__version__,
        "numpy": np.__version__,
        "joblib": joblib.__version__,
    }


def combined(
    rules: dict[str, bool], model: dict[str, bool], truth: dict[str, bool]
) -> dict[str, object]:
    """Score the two approaches taken together, both ways.

    The Results chapter observes that for Feature Envy the rule catches cases the
    model misses, and says a union of the two "would make practical sense". That
    is a claim, and until it is scored it is only a hope: a union inherits both
    approaches' false positives along with their true ones, and on a set where
    most labels are negative that trade is not obviously good.

    Both directions are reported because they answer different questions. The
    union asks whether the two approaches see different things and adding them
    helps recall; the intersection asks whether agreement between them is a
    stronger signal than either alone, which is what a user who wants few false
    alarms would want to know.
    """
    shared = sorted(set(rules) & set(model) & set(truth))
    union = confusion((truth[i], rules[i] or model[i]) for i in shared)
    intersection = confusion((truth[i], rules[i] and model[i]) for i in shared)
    return {
        "n": len(shared),
        "union": union.to_dict(),
        "intersection": intersection.to_dict(),
    }
