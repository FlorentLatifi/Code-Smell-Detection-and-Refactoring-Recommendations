"""Why the model flagged *this* entity, in the same terms the rules answer in.

Approach A answers the question by construction: it reports the clauses it
evaluated with the values that satisfied them, so a developer reads ``WMC = 62
(>= 47)`` and knows what to change. Approach B wins on every smell and says
nothing. That asymmetry is the standard objection to machine-learned smell
detection, and permutation importance does not answer it: it says which measure
matters across the corpus, not why this class was flagged.

**The method: one measurement at a time, set to typical.** For a flagged entity,
each feature in turn is replaced by the median of the training set and the model
is asked again. The drop in predicted probability is that feature's contribution,
and a feature whose replacement takes the verdict below the decision boundary is
one that, on its own, explains the flag.

Three reasons for this rather than something better known:

* **It is exact.** No sampling, no surrogate model, no approximation with its own
  error to explain. The number reported is a difference between two predictions
  the model actually made.
* **It is model-agnostic.** The best model differs per smell -- gradient boosting
  for three, random forest for one -- and a method tied to one family would leave
  the comparison uneven.
* **It answers in the reader's units.** "If CLOC were typical, this would not be
  flagged" is the same shape of statement as a detection strategy's clause, which
  is what makes the two approaches comparable at all.

The cost is that it treats features one at a time and cannot see that two of them
carry the same information: where CLOC and NOM both say "large", replacing either
alone may move nothing, and the entity looks unexplained. That is a real limit and
is reported with the result rather than worked around.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from sklearn.base import BaseEstimator, clone
from sklearn.model_selection import GroupKFold

# The verdict boundary. Not tunable here: the evaluation scores `predict`, so an
# explanation must be about the same boundary that produced the number reported.
DECISION = 0.5


@dataclass(frozen=True)
class Contribution:
    """One measurement's share of a single verdict."""

    feature: str
    value: float
    typical: float
    #: How far the predicted probability falls when the measurement is made typical.
    drop: float
    #: Whether that alone takes the prediction below the decision boundary.
    decisive: bool


def typical_values(x: NDArray[np.float64]) -> NDArray[np.float64]:
    """The median of each feature over the training rows.

    The median rather than the mean, for the same reason the metric shifts are
    reported as medians: these distributions are long-tailed, and a mean "typical
    class" would be one no repository contains.
    """
    return np.median(x, axis=0)


def explain(
    model: BaseEstimator,
    row: NDArray[np.float64],
    typical: NDArray[np.float64],
    names: tuple[str, ...],
) -> list[Contribution]:
    """Rank the measurements by how much each one holds the verdict up."""
    base = float(model.predict_proba(row.reshape(1, -1))[0, 1])

    perturbed = np.repeat(row.reshape(1, -1), len(names), axis=0)
    for index in range(len(names)):
        perturbed[index, index] = typical[index]
    after = model.predict_proba(perturbed)[:, 1]

    contributions = [
        Contribution(
            feature=names[index],
            value=float(row[index]),
            typical=float(typical[index]),
            drop=round(base - float(after[index]), 4),
            decisive=base >= DECISION > float(after[index]),
        )
        for index in range(len(names))
    ]
    return sorted(contributions, key=lambda c: (-c.drop, c.feature))


def decisive_over_folds(
    model: BaseEstimator,
    x: NDArray[np.float64],
    y: NDArray[np.bool_],
    groups: NDArray[np.str_],
    names: tuple[str, ...],
    folds: int,
) -> dict[str, object]:
    """How often a single measurement carries the verdict, over the whole corpus.

    Explained out of fold, exactly as the verdicts are scored: each flagged entity
    is explained by a model that never saw its repository. Explaining with a model
    fitted on everything would describe reasoning the reported numbers never came
    from.

    Two figures come back. The share of flagged entities where **some** single
    measurement, set to typical, takes the verdict back across the boundary --
    that is how often the model has an answer a developer can act on. And how
    often each measurement is the one that does it.
    """
    splitter = GroupKFold(n_splits=min(folds, len(set(groups.tolist()))))
    flagged = 0
    explained = 0
    counted: dict[str, int] = dict.fromkeys(names, 0)

    for train_index, test_index in splitter.split(x, y, groups):
        fitted = clone(model)
        fitted.fit(x[train_index], y[train_index])
        typical = typical_values(x[train_index])

        predicted = fitted.predict(x[test_index]).astype(bool)
        for position, is_flagged in enumerate(predicted):
            if not is_flagged:
                continue
            flagged += 1
            ranked = explain(fitted, x[test_index][position], typical, names)
            decisive = [c for c in ranked if c.decisive]
            if decisive:
                explained += 1
                counted[decisive[0].feature] += 1

    return {
        "flagged": flagged,
        "explained": explained,
        "share": round(explained / flagged, 4) if flagged else None,
        "decisive_feature": dict(
            sorted(((k, v) for k, v in counted.items() if v), key=lambda p: -p[1])
        ),
    }
