"""Approach B at the point of use: the fitted models applied to code being read.

The evaluation answers what the classifier achieves on MLCQ. Until it can be
pointed at the file a developer has open, that is a statement about a table, and
the interface can show Approach A explaining itself while Approach B is present
only as a column of past scores. This module closes that gap, and doing so forces
three questions the evaluation never had to answer.

**Which model.** Not the one the scores describe. Those come from out-of-fold
predictions and characterise the procedure (``training.fit_final`` says so at
length); what is deployed is the same pipeline refitted with nothing held back.
A verdict produced here is therefore a useful reading and *not* evidence of
accuracy, and ``scores_are_out_of_fold`` in the manifest is what stops the two
from being confused.

**What to do with a measurement that was never taken.** ``dataset.row`` leaves a
metric empty rather than writing 0.0, and ``features.load`` drops such rows
instead of reading them as zeros. Serving keeps that rule: an entity missing any
feature gets no verdict and is counted as skipped. Imputing here would invent a
measurement and hide it inside a probability.

**What "typical" means.** ``explain`` needs the median of the rows the model was
fitted on, and the manifest does not carry it -- so it is recomputed from the
committed dataset, which is the very table ``fit_final`` was given. Recomputing
rather than storing keeps one definition of the median; the cost is that serving
needs ``mlcq_dataset.csv`` present, which a clean checkout has because
``data/results/`` is committed.

One limit is inherited whole from ``explain``: features that carry the same
information mask each other, so an entity can be flagged with nothing marked
decisive. That is reported as it stands rather than smoothed over.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from numpy.typing import NDArray
from sklearn.base import BaseEstimator

from javasmell.evaluation.scoring import PRIMARY_VARIANT, VARIANTS
from javasmell.ml.explain import DECISION, Contribution, explain, typical_values
from javasmell.ml.features import CLASS_LEVEL, load
from javasmell.ml.training import library_versions
from javasmell.model.entities import ClassInfo, MethodInfo, ProjectModel

#: The four smells MLCQ labels, hence the four models that exist.
SERVED = ("blob", "data class", "long method", "feature envy")


class ModelUnavailable(Exception):
    """A model cannot be served, carrying the reason a caller can show a user."""


@dataclass(frozen=True)
class SmellModel:
    """One fitted classifier with everything needed to apply and explain it."""

    smell: str
    estimator: BaseEstimator
    features: tuple[str, ...]
    #: Median of each feature over the rows this model was fitted on.
    typical: NDArray[np.float64]
    trained_on: int

    @property
    def is_class_level(self) -> bool:
        return self.smell in CLASS_LEVEL


@dataclass(frozen=True)
class Prediction:
    """What one model says about one entity, and which measurement carries it."""

    smell: str
    file_path: str
    class_name: str
    method: str | None
    start_line: int
    end_line: int
    probability: float
    flagged: bool
    #: Ranked by how much each measurement holds the verdict up. Empty unless flagged.
    contributions: tuple[Contribution, ...]

    @property
    def decisive(self) -> Contribution | None:
        """The measurement that, made typical, would reverse the verdict."""
        return next((c for c in self.contributions if c.decisive), None)


@dataclass(frozen=True)
class ModelReport:
    """One model's pass over a project, including what it declined to judge."""

    smell: str
    predictions: tuple[Prediction, ...]
    #: Entities of the right kind that the model was asked about.
    considered: int
    #: Of those, the ones missing a measurement and therefore not judged.
    incomplete: int


def slug(smell: str) -> str:
    """The filename ``scripts/train_models.py`` writes for a smell."""
    return smell.replace(" ", "_")


def rule_equivalent(smell: str) -> tuple[str, ...]:
    """The detectors that answer the same question as this model.

    The two approaches name things differently -- reviewers labelled ``blob``
    where the strategy is called ``GodClass`` -- and the mapping between them is
    already fixed by ``scoring.VARIANTS``, which is what every reported
    comparison of A against B was computed through. It travels with the
    prediction so a caller can line the two up without being told the mapping a
    second time, in a second place, that could then disagree.

    Only the primary variant is offered. The second one Blob carries adds this
    project's own Large Class to a published strategy, and a reader comparing
    approaches should be shown the published one.
    """
    return VARIANTS[smell][PRIMARY_VARIANT]


def load_model(models_dir: Path, dataset_csv: Path, smell: str) -> SmellModel:
    """Read one model and its manifest, refusing rather than guessing.

    The manifest is the authority on feature order: a bare estimator takes an
    unlabelled array and cannot say which column was WMC, so a mismatch between
    the array built here and the one it was fitted on would be silent. The
    library check is there for the same reason -- unpickling an estimator built
    by a different scikit-learn is undefined rather than merely risky, and a
    verdict from a model that unpickled wrong is worse than no verdict at all.
    """
    manifest_path = models_dir / f"{slug(smell)}.json"
    model_path = models_dir / f"{slug(smell)}.joblib"
    if not manifest_path.is_file() or not model_path.is_file():
        raise ModelUnavailable(f"no trained model for {smell!r}; run scripts/train_models.py")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded: dict[str, str] = manifest["libraries"]
    running = library_versions()
    differing = sorted(name for name, version in recorded.items() if running.get(name) != version)
    if differing:
        raise ModelUnavailable(
            f"{smell!r} was fitted with a different {', '.join(differing)}; retrain first"
        )

    if not dataset_csv.is_file():
        raise ModelUnavailable(f"{dataset_csv.name} is needed to explain a verdict")

    features: tuple[str, ...] = tuple(manifest["features"])
    return SmellModel(
        smell=smell,
        estimator=joblib.load(model_path),
        features=features,
        typical=medians(dataset_csv, smell, manifest["label"], features),
        trained_on=int(manifest["trained_on"]),
    )


def medians(
    dataset_csv: Path, smell: str, label: str, features: tuple[str, ...]
) -> NDArray[np.float64]:
    """The median of each of the model's columns, over the rows it was fitted on.

    The rows come from ``features.load``, so the selection is the fitted one --
    including the rows it drops for an unresolved label or a missing measurement,
    which a median taken over the raw file would wrongly include. The *columns*
    are then picked out by name, because the manifest and not this package
    decides which measurements a given model was given: reading them positionally
    would silently misalign every explanation the day the two disagree.
    """
    data = load(dataset_csv, smell, label)
    position = {name: index for index, name in enumerate(data.names)}
    missing = [name for name in features if name not in position]
    if missing:
        raise ModelUnavailable(f"{smell!r} names {', '.join(missing)}, absent from the dataset")

    typical = typical_values(data.x)
    return np.array([typical[position[name]] for name in features], dtype=np.float64)


@lru_cache(maxsize=4)
def _cached(models_dir: str, dataset_csv: str) -> tuple[SmellModel, ...]:
    return tuple(load_model(Path(models_dir), Path(dataset_csv), s) for s in SERVED)


def load_models(models_dir: Path, dataset_csv: Path) -> tuple[SmellModel, ...]:
    """All four models, read once per process.

    Loading costs about a second, most of it the medians; a single-user tool that
    paid that on every request would spend longer reading its own dataset than
    measuring the caller's code. What comes back is immutable, so sharing it
    across requests cannot leak state between them.
    """
    return _cached(str(models_dir), str(dataset_csv))


def measurement(cls: ClassInfo, method: MethodInfo | None, feature: str) -> float | None:
    """Read one dataset column off a measured entity.

    The ``c_``/``m_`` prefixes are the dataset's own encoding of which entity a
    metric was taken from, so reading them back is what keeps the vector aligned
    with the columns the model was fitted on.
    """
    prefix, _, name = feature.partition("_")
    if prefix == "c":
        return cls.metrics.get(name)
    return None if method is None else method.metrics.get(name)


def vector(
    cls: ClassInfo, method: MethodInfo | None, features: Sequence[str]
) -> NDArray[np.float64] | None:
    """The feature row for one entity, or ``None`` if any measurement is missing."""
    values: list[float] = []
    for feature in features:
        measured = measurement(cls, method, feature)
        if measured is None:
            return None
        values.append(float(measured))
    return np.array(values, dtype=np.float64)


def predict(model: SmellModel, project: ProjectModel) -> ModelReport:
    """Apply one model to every entity of the kind it judges.

    Entities are predicted in one batch rather than one at a time, because the
    cost of ``predict_proba`` is almost all setup and a large project has
    thousands of methods. Explanations are computed only for flagged entities,
    which is both what a reader asks for and what ``decisive_over_folds``
    measures over the corpus.
    """
    entities: list[tuple[ClassInfo, MethodInfo | None]] = []
    for cls in project.classes:
        if model.is_class_level:
            entities.append((cls, None))
        else:
            entities.extend((cls, method) for method in cls.methods)

    rows: list[NDArray[np.float64]] = []
    judged: list[tuple[ClassInfo, MethodInfo | None]] = []
    for cls, method in entities:
        row = vector(cls, method, model.features)
        if row is not None:
            rows.append(row)
            judged.append((cls, method))

    predictions: list[Prediction] = []
    if rows:
        matrix = np.vstack(rows)
        probabilities = model.estimator.predict_proba(matrix)[:, 1]
        for position, (cls, method) in enumerate(judged):
            probability = float(probabilities[position])
            flagged = probability >= DECISION
            contributions: tuple[Contribution, ...] = ()
            if flagged:
                contributions = tuple(
                    explain(model.estimator, matrix[position], model.typical, model.features)
                )
            predictions.append(
                Prediction(
                    smell=model.smell,
                    file_path=cls.file_path,
                    class_name=cls.name,
                    method=None if method is None else method.name,
                    start_line=cls.start_line if method is None else method.start_line,
                    end_line=cls.end_line if method is None else method.end_line,
                    probability=round(probability, 4),
                    flagged=flagged,
                    contributions=contributions,
                )
            )

    return ModelReport(
        smell=model.smell,
        predictions=tuple(predictions),
        considered=len(entities),
        incomplete=len(entities) - len(judged),
    )


def predict_all(models: Sequence[SmellModel], project: ProjectModel) -> list[ModelReport]:
    return [predict(model, project) for model in models]
