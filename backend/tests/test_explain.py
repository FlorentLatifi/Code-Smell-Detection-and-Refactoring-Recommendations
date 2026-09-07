"""Tests for the per-instance explanation.

The expectations are derived from a model whose rule is known, not from a run: a
decision tree trained on a table where one column decides everything must report
that column and no other.
"""

from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from javasmell.ml import explain as explain_module
from javasmell.ml.explain import (
    DECISION,
    decisive_over_folds,
    explain,
    explain_many,
    typical_values,
)

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


def grouped_table() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Four repositories of five rows each, where the first column decides.

    The label is ``decisive > 10``, the same rule the tests above use, so every
    repository carries both classes and no fold is degenerate.
    """
    x = np.array([[value, value % 2] for value in range(20)], dtype=np.float64)
    y = x[:, 0] > 10
    groups = np.array([f"repo-{value % 4}" for value in range(20)], dtype=np.str_)
    return x, y, groups


def test_every_flagged_entity_is_explained_by_the_column_that_decides() -> None:
    """The figure counts *predictions*, not labels, so the count is not asserted.

    A first draft equated `flagged` with the nine rows labelled positive. It is
    not that: each entity is judged by a model trained without its repository,
    and how many of the nine that model recovers depends on where the tree puts
    its split in each fold. What is derivable without simulating four trees is
    the property the figure exists to report -- that where the model does flag,
    a single measurement set to its typical value takes the verdict back. The
    training median of a fold drawn from 0..19 falls at or below 10, which is
    the rule's own boundary, so `decisive` carries every flag and `noise`, which
    the label does not depend on, carries none.
    """
    x, y, groups = grouped_table()

    result = decisive_over_folds(
        DecisionTreeClassifier(random_state=0), x, y, groups, NAMES, folds=4
    )

    assert 0 < result["flagged"] <= len(y)
    assert result["explained"] == result["flagged"]
    assert result["share"] == 1.0
    assert result["decisive_feature"] == {"decisive": result["flagged"]}


def test_a_measurement_that_never_decides_is_left_out_of_the_tally() -> None:
    """The per-feature counts carry only what actually carried a verdict.

    Reporting every name with a zero beside it would bury the answer among the
    measurements that had nothing to do with it.
    """
    x, y, groups = grouped_table()

    result = decisive_over_folds(
        DecisionTreeClassifier(random_state=0), x, y, groups, NAMES, folds=4
    )

    assert "noise" not in result["decisive_feature"]


def test_nothing_flagged_reports_no_share_rather_than_zero(monkeypatch) -> None:
    """A share of "none flagged" is not zero: it is undefined, and says so.

    Zero would read as "the model flags entities and explains none of them",
    which is the opposite diagnosis from "the model flagged nothing at all".
    """
    x, _, groups = grouped_table()
    never = np.zeros(len(x), dtype=np.bool_)

    result = decisive_over_folds(
        DecisionTreeClassifier(random_state=0), x, never, groups, NAMES, folds=4
    )

    assert result["flagged"] == 0
    assert result["explained"] == 0
    assert result["share"] is None
    assert result["decisive_feature"] == {}


def test_the_typical_values_come_from_the_training_rows_only(monkeypatch) -> None:
    """The median an explanation compares against must not have seen the fold.

    Explaining with medians drawn from the whole corpus would leak the held-out
    repository into the explanation of its own entities -- quietly, because the
    verdicts would not change and only the reasons would.
    """
    x, y, groups = grouped_table()

    sizes: list[int] = []
    real = explain_module.typical_values

    def watched(rows):
        sizes.append(len(rows))
        return real(rows)

    monkeypatch.setattr(explain_module, "typical_values", watched)
    decisive_over_folds(DecisionTreeClassifier(random_state=0), x, y, groups, NAMES, folds=4)

    assert sizes, "no fold was fitted"
    trained_on = len(x) - len(x) // 4
    assert sizes == [trained_on] * len(sizes), (
        f"medians were taken from {sizes} rows; a training fold is {trained_on}"
    )
