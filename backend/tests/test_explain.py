"""Tests for the per-instance explanation.

The expectations are derived from a model whose rule is known, not from a run: a
decision tree trained on a table where one column decides everything must report
that column and no other.
"""

from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from javasmell.ml.explain import DECISION, explain, explain_many, typical_values

NAMES = ("decisive", "noise")


def table() -> np.ndarray:
    """Twenty rows where the first column decides and the second alternates.

    The second column must be *independent* of the label, not merely a different
    name for it: a first draft used the same counter twice, and a feature that
    carries the same information as the deciding one is indistinguishable from it
    -- which is the limitation this method has and the fixture must not hide.
    """
    return np.array([[value, value % 2] for value in range(20)], dtype=np.float64)


def trained() -> DecisionTreeClassifier:
    """A tree over that table. The label is exactly ``decisive > 10``."""
    x = table()
    return DecisionTreeClassifier(random_state=0).fit(x, x[:, 0] > 10)


def test_the_measurement_that_carries_the_verdict_ranks_first() -> None:
    model = trained()
    typical = typical_values(table())

    # Median of 0..19 is 9.5, which is below the boundary of 10: replacing the
    # deciding column with it must take the prediction across.
    assert typical[0] == 9.5

    ranked = explain(model, np.array([18.0, 1.0]), typical, NAMES)
    assert ranked[0].feature == "decisive"
    assert ranked[0].drop == 1.0
    assert ranked[0].decisive is True


def test_a_measurement_the_model_ignores_contributes_nothing() -> None:
    model = trained()
    ranked = explain(model, np.array([18.0, 1.0]), typical_values(table()), NAMES)
    noise = next(c for c in ranked if c.feature == "noise")
    assert noise.drop == 0.0
    assert noise.decisive is False


def test_every_feature_is_reported_even_when_it_does_nothing() -> None:
    """A reader who asks why has to see what was considered and dismissed."""
    model = trained()
    ranked = explain(model, np.array([18.0, 1.0]), typical_values(table()), NAMES)
    assert {c.feature for c in ranked} == set(NAMES)


def test_the_value_and_the_typical_value_travel_with_the_contribution() -> None:
    """The explanation has to be readable without the table beside it."""
    model = trained()
    ranked = explain(model, np.array([18.0, 1.0]), typical_values(table()), NAMES)
    decisive = next(c for c in ranked if c.feature == "decisive")
    assert (decisive.value, decisive.typical) == (18.0, 9.5)


def test_an_entity_the_model_does_not_flag_has_no_decisive_measurement() -> None:
    """Nothing can be decisive when the verdict was negative to begin with."""
    model = trained()
    ranked = explain(model, np.array([2.0, 1.0]), typical_values(table()), NAMES)
    assert model.predict_proba(np.array([[2.0, 1.0]]))[0, 1] < DECISION
    assert not any(c.decisive for c in ranked)


def test_explaining_many_agrees_with_explaining_one() -> None:
    """The batched path is an optimisation, so it has to be indistinguishable.

    Explaining a project one entity at a time spends almost all of its time
    entering scikit-learn -- 162 seconds against 5 for the parse, on a 447-class
    project -- so `predict` explains the flagged entities together. That is only
    allowed to be faster, never different, and a fixture whose rule is known
    cannot show the difference: the rows here straddle the boundary in both
    directions so agreement is tested where the verdict actually turns.
    """
    model = trained()
    typical = typical_values(table())
    rows = np.array([[value, value % 2] for value in range(20)], dtype=np.float64)

    batched = explain_many(model, rows, typical, NAMES)
    one_by_one = [explain(model, row, typical, NAMES) for row in rows]

    assert batched == one_by_one


def test_explaining_nothing_is_not_an_error() -> None:
    """A project where the model flagged no entity still has to come back."""
    assert explain_many(trained(), np.empty((0, 2)), typical_values(table()), NAMES) == []
