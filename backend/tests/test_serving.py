"""Tests for applying a fitted model to code being read.

A random forest's probability cannot be derived by hand, so nothing here asserts
one. What is derived by hand is everything around it: which entities a model is
asked about, which it declines for want of a measurement, that the vector handed
to it is in the manifest's order, and that a refusal to load is a refusal rather
than a guess. Where a verdict itself is needed, the fixture uses a model whose
rule is known -- the same device `test_explain` uses.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier

from javasmell.ml.serving import (
    ModelUnavailable,
    SmellModel,
    load_model,
    measurement,
    predict,
    slug,
    vector,
)
from javasmell.model.entities import ClassInfo, CompilationUnit, MethodInfo, ProjectModel

FEATURES = ("c_WMC", "c_CBO", "m_MLOC")


def method(name: str, metrics: dict[str, float]) -> MethodInfo:
    return MethodInfo(
        name=name,
        return_type="void",
        parameters=[],
        modifiers=frozenset(),
        start_line=10,
        end_line=20,
        metrics=metrics,
    )


def klass(name: str, metrics: dict[str, float], methods: list[MethodInfo]) -> ClassInfo:
    return ClassInfo(
        name=name,
        kind="class",
        package="com.acme",
        file_path="Acme.java",
        modifiers=frozenset(),
        superclass=None,
        interfaces=[],
        fields=[],
        methods=methods,
        start_line=1,
        end_line=99,
        metrics=metrics,
    )


def project(classes: list[ClassInfo]) -> ProjectModel:
    model = ProjectModel(root=".")
    model.units.append(
        CompilationUnit(file_path="Acme.java", package="com.acme", imports=[], classes=classes)
    )
    return model


def served(smell: str, features: tuple[str, ...] = FEATURES) -> SmellModel:
    """A model whose rule is ``the first feature exceeds 10``.

    Trained on twenty rows so the median of each column is known: column 0 runs
    0..19 and has median 9.5, and the other two are constant.
    """
    padding = [1.0] * (len(features) - 1)
    x = np.array([[value, *padding] for value in range(20)], dtype=np.float64)
    estimator = DecisionTreeClassifier(random_state=0).fit(x, x[:, 0] > 10)
    return SmellModel(
        smell=smell,
        estimator=estimator,
        features=features,
        typical=np.array([9.5, *padding], dtype=np.float64),
        trained_on=20,
    )


# --- reading measurements off an entity ----------------------------------


def test_the_column_prefix_says_which_entity_was_measured() -> None:
    cls = klass("Acme", {"WMC": 12.0}, [])
    target = method("run", {"MLOC": 40.0})

    # c_ reads the class, m_ reads the method, and neither may read the other:
    # WMC exists on the class only, MLOC on the method only.
    assert measurement(cls, target, "c_WMC") == 12.0
    assert measurement(cls, target, "m_MLOC") == 40.0
    assert measurement(cls, target, "m_WMC") is None
    assert measurement(cls, target, "c_MLOC") is None


def test_a_class_level_entity_has_no_method_measurements() -> None:
    cls = klass("Acme", {"WMC": 12.0}, [])
    assert measurement(cls, None, "m_MLOC") is None


def test_the_vector_follows_the_manifest_order() -> None:
    cls = klass("Acme", {"WMC": 12.0, "CBO": 3.0}, [])
    target = method("run", {"MLOC": 40.0})

    # FEATURES is (c_WMC, c_CBO, m_MLOC), so the row is (12, 3, 40) in that
    # order and in no other -- a model cannot say which column was which.
    row = vector(cls, target, FEATURES)
    assert row is not None
    assert list(row) == [12.0, 3.0, 40.0]


def test_a_missing_measurement_yields_no_vector_rather_than_a_zero() -> None:
    cls = klass("Acme", {"WMC": 12.0}, [])  # CBO was never measured
    assert vector(cls, method("run", {"MLOC": 40.0}), FEATURES) is None


# --- applying a model to a project ---------------------------------------


def test_a_method_level_model_judges_every_method_and_no_class() -> None:
    cls = klass(
        "Acme",
        {"WMC": 12.0, "CBO": 3.0},
        [method("run", {"MLOC": 40.0}), method("stop", {"MLOC": 2.0})],
    )
    report = predict(served("long method"), project([cls]))

    # Two methods on one class: two entities considered, none skipped.
    assert (report.considered, report.incomplete) == (2, 0)
    assert {p.method for p in report.predictions} == {"run", "stop"}


def test_a_class_level_model_judges_the_class_and_not_its_methods() -> None:
    cls = klass("Acme", {"WMC": 12.0, "CBO": 3.0}, [method("run", {"MLOC": 40.0})])
    report = predict(served("blob", ("c_WMC", "c_CBO")), project([cls]))

    assert (report.considered, report.incomplete) == (1, 0)
    assert [p.method for p in report.predictions] == [None]


def test_entities_missing_a_measurement_are_counted_not_judged() -> None:
    complete = klass("Full", {"WMC": 12.0, "CBO": 3.0}, [method("run", {"MLOC": 40.0})])
    partial = klass("Partial", {"WMC": 12.0}, [method("run", {"MLOC": 40.0})])
    report = predict(served("long method"), project([complete, partial]))

    # Both methods are considered; only the one whose class has CBO is judged.
    assert (report.considered, report.incomplete) == (2, 1)
    assert [p.class_name for p in report.predictions] == ["Full"]


def test_the_verdict_follows_the_rule_the_model_was_given() -> None:
    cls = klass(
        "Acme",
        {"WMC": 18.0, "CBO": 1.0},  # 18 > 10, so the rule flags it
        [method("run", {"MLOC": 1.0})],
    )
    quiet = klass(
        "Quiet",
        {"WMC": 2.0, "CBO": 1.0},  # 2 <= 10, so it does not
        [method("run", {"MLOC": 1.0})],
    )
    report = predict(served("long method"), project([cls, quiet]))
    verdicts = {p.class_name: p.flagged for p in report.predictions}

    assert verdicts == {"Acme": True, "Quiet": False}


def test_only_a_flagged_entity_is_explained() -> None:
    cls = klass("Acme", {"WMC": 18.0, "CBO": 1.0}, [method("run", {"MLOC": 1.0})])
    quiet = klass("Quiet", {"WMC": 2.0, "CBO": 1.0}, [method("run", {"MLOC": 1.0})])
    report = predict(served("long method"), project([cls, quiet]))
    explained = {p.class_name: len(p.contributions) for p in report.predictions}

    # An explanation answers "why was this flagged"; there is no such question
    # for an entity that was not.
    assert explained["Quiet"] == 0
    assert explained["Acme"] == len(FEATURES)


def test_the_decisive_measurement_is_the_one_the_rule_uses() -> None:
    cls = klass("Acme", {"WMC": 18.0, "CBO": 1.0}, [method("run", {"MLOC": 1.0})])
    found = predict(served("long method"), project([cls])).predictions[0]
    decisive = found.decisive

    # WMC = 18 holds the verdict up: set to the median 9.5 it falls below the
    # rule's boundary of 10, and nothing else the model was given moves it.
    assert decisive is not None
    assert decisive.feature == "c_WMC"
    assert (decisive.value, decisive.typical) == (18.0, 9.5)


def test_every_decisive_measurement_outranks_every_other() -> None:
    """The property the response relies on when it sends only the top few.

    A decisive measurement takes the probability below the boundary and a
    non-decisive one leaves it above, so the first is always the larger drop.
    """
    cls = klass("Acme", {"WMC": 18.0, "CBO": 1.0}, [method("run", {"MLOC": 1.0})])
    ranked = predict(served("long method"), project([cls])).predictions[0].contributions
    positions = [index for index, c in enumerate(ranked) if c.decisive]

    assert positions == list(range(len(positions)))


def test_a_project_without_the_right_entities_yields_no_verdicts() -> None:
    """An empty answer, not a crash: `np.vstack` refuses an empty list."""
    report = predict(served("long method"), project([klass("Empty", {"WMC": 1.0}, [])]))

    assert report.predictions == ()
    assert (report.considered, report.incomplete) == (0, 0)


# --- refusing to load ----------------------------------------------------


def test_slug_matches_the_filename_training_writes() -> None:
    assert slug("data class") == "data_class"
    assert slug("blob") == "blob"


def test_an_absent_model_is_refused_with_a_reason(tmp_path: Path) -> None:
    with pytest.raises(ModelUnavailable, match="no trained model"):
        load_model(tmp_path, tmp_path / "dataset.csv", "blob")


def test_a_model_fitted_by_another_library_is_refused(tmp_path: Path) -> None:
    """Unpickling across scikit-learn versions is undefined, so it is not tried.

    A verdict from an estimator that unpickled wrong is worse than no verdict,
    and the manifest exists precisely so the mismatch can be seen first.
    """
    models = tmp_path
    (models / "blob.joblib").write_bytes(b"not actually a model")
    (models / "blob.json").write_text(
        json.dumps(
            {
                "features": ["c_WMC"],
                "label": "smelly_mean",
                "libraries": {"scikit-learn": "0.0.0-not-installed"},
                "trained_on": 20,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ModelUnavailable, match="scikit-learn"):
        load_model(models, models / "dataset.csv", "blob")
