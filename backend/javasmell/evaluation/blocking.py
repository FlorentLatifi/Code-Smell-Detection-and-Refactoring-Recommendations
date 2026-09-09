"""Why the conjunction strategies miss what they miss.

The Results chapter reports that the God Class strategy reaches a recall under
0.10 against MLCQ, and Feature Envy is not far better. Both figures are
accurate and both are useless on their own: a reader learns that nine of ten
reviewed blobs go unflagged and nothing about *what* would have to change.

A detection strategy from Lanza & Marinescu is a conjunction, so a miss is never
diffuse. Exactly one clause, or two, or all three, failed to hold, and which
ones failed is recorded in the measurements the evaluation already stores. The
question this module answers is therefore not "is recall low" but "is recall low
because the thresholds are severe, or because one particular measurement is
never large enough".

**The two answers point at different work.** If misses spread evenly across the
clauses, the strategy is simply strict and a calibration would move it. If they
concentrate on one clause, that measurement is the ceiling, and for ATFD in
particular the ceiling would be architectural: the parser records syntactic
facts and deliberately resolves no symbols, so foreign data access is
undercounted by construction and no threshold can recover it.

**Only conjunctions.** Long Method is a single clause, so "which clause blocked
it" has one possible answer and asking is theatre. Data Class mixes a
conjunction with a disjunction, where "the blocking clause" is not well defined
without deciding which branch was closer, and inventing that rule here would
produce a number whose meaning depends on the invention.
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from javasmell.detectors.base import Condition
from javasmell.detectors.rules import feature_envy_clauses, god_class_clauses
from javasmell.detectors.thresholds import DEFAULT, Thresholds
from javasmell.evaluation.dataset import entities
from javasmell.evaluation.mlcq import Aggregation, Sample

#: MLCQ smell -> the strategy whose clauses explain a miss. Only the two pure
#: conjunctions appear; see the module docstring for why the others do not.
CONJUNCTIONS = {
    "blob": "GodClass",
    "feature envy": "FeatureEnvy",
}


@dataclass(frozen=True)
class Miss:
    """One reviewed instance the strategy did not flag, and what stopped it."""

    sample_id: str
    smell: str
    severity: str
    #: Metric names of the clauses that did not hold, in strategy order.
    failed: tuple[str, ...]
    #: Per failed clause, how far the measurement fell short as a ratio in
    #: (0, 1]: 1.0 would be exactly at the threshold, 0.5 half way there.
    shortfall: Mapping[str, float]

    @property
    def only_blocker(self) -> str | None:
        """The single clause responsible, when there is exactly one."""
        return self.failed[0] if len(self.failed) == 1 else None


def _shortfall(clause: Condition) -> float:
    """How close an unsatisfied clause came, as a ratio in (0, 1].

    Expressed so that both directions read the same way: for a clause that wants
    a large value it is measured over threshold, and for one that wants a small
    value it is threshold over measured. A clause that wants ``TCC < 0.33`` and
    met 0.66 is at 0.5, exactly as a clause that wants ``ATFD > 4`` and met 2.

    ``excess`` on :class:`Condition` computes the same ratio for a *satisfied*
    clause; this is its mirror, and the two are deliberately the same quantity
    so that "how far past" and "how far short" are comparable numbers.
    """
    if clause.operator in (">", ">="):
        return clause.value / clause.threshold if clause.threshold > 0 else 1.0
    if clause.value <= 0:
        return 1.0
    return clause.threshold / clause.value


def clauses_for(strategy: str, record: Mapping[str, str], t: Thresholds) -> list[Condition]:
    """The clauses of one strategy, measured from a stored row."""
    if strategy not in set(CONJUNCTIONS.values()):
        # Kontrolluar para se te preket rreshti: nje strategji e panjohur duhet
        # te ndalojë ketu, jo te dale si rresht i keqformuar disa hapa me tutje.
        raise ValueError(f"no clause list for {strategy!r}")
    cls, method = entities(record)
    if strategy == "GodClass":
        return god_class_clauses(cls, t)
    return [] if method is None else feature_envy_clauses(method, t)


def misses(
    dataset_path: str | Path,
    samples: Iterable[Sample],
    thresholds: Thresholds = DEFAULT,
    how: Aggregation = Aggregation.MEAN,
) -> list[Miss]:
    """Every reviewed positive the conjunction failed to flag, with its blockers.

    Read from the stored feature table rather than the corpus, for the reason
    ``replay`` gives: every field these clauses touch is a column of that table
    (VD-23), so this costs a second instead of ninety-five minutes.
    """
    by_id = {sample.sample_id: sample for sample in samples}
    found: list[Miss] = []
    with Path(dataset_path).open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            sample = by_id.get(record["sample_id"])
            if sample is None:
                continue
            strategy = CONJUNCTIONS.get(sample.smell)
            if strategy is None or not sample.is_smelly(how):
                continue
            clauses = clauses_for(strategy, record, thresholds)
            failed = [clause for clause in clauses if not clause.satisfied]
            if not clauses or not failed:
                continue
            severity = sample.severity_label(how)
            found.append(
                Miss(
                    sample_id=sample.sample_id,
                    smell=sample.smell,
                    severity="" if severity is None else severity,
                    failed=tuple(clause.metric for clause in failed),
                    shortfall={clause.metric: round(_shortfall(clause), 4) for clause in failed},
                )
            )
    return found


def summarise(found: Sequence[Miss]) -> dict[str, object]:
    """Per smell: how many clauses blocked, which ones, and how close they came.

    ``median_shortfall`` is reported only for the misses a single clause
    blocked, because a miss with two failing clauses has no single distance and
    averaging the two would invent one.
    """
    result: dict[str, object] = {}
    for smell in sorted({miss.smell for miss in found}):
        group = [miss for miss in found if miss.smell == smell]
        blockers = Counter(len(miss.failed) for miss in group)
        alone = [miss for miss in group if miss.only_blocker is not None]
        by_clause = Counter(miss.failed[0] for miss in alone)

        distances: dict[str, float] = {}
        for metric in by_clause:
            values = sorted(miss.shortfall[metric] for miss in alone if miss.only_blocker == metric)
            middle = len(values) // 2
            distances[metric] = round(
                values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2,
                4,
            )

        result[smell] = {
            "missed": len(group),
            "blocked_by_one_clause": len(alone),
            "clauses_failing": {str(k): v for k, v in sorted(blockers.items())},
            "sole_blocker": dict(by_clause.most_common()),
            "median_shortfall": distances,
        }
    return result
