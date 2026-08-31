"""How well the reviewers agree with each other, on the detectors' own scale.

Every score in the Results chapter is measured against a ground truth built by
pooling human reviews, and those reviewers disagree: a quarter of the
multiply-reviewed samples in MLCQ carry more than one severity, and a quarter
disagree on the bare question of whether the smell is there at all. That sets a
ceiling. A detector cannot agree with a label better than the people who wrote
the label agree with each other, so an MCC of 0.71 read against a ceiling of 1.0
means something very different from the same number read against a ceiling of
0.75.

The ceiling is measured the same way everything else is: one reviewer is treated
as the truth and another as the prediction, and the pair is pushed through the
same ``confusion``. Both directions of each pair are counted, which makes the
matrix symmetric -- there is no reason to privilege either reviewer -- and makes
the resulting MCC a statement about the pair rather than about an ordering.

This is a *pooled* pairwise agreement, not Cohen's kappa between two fixed
raters, because MLCQ has no fixed pair: samples are reviewed by different
subsets of a reviewer panel. Pooling every pair is the honest reading of that
design, and it is reported per smell because the smells are not equally hard to
agree on.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations

from javasmell.evaluation.mlcq import SEVERITY_RANK, Sample
from javasmell.evaluation.scoring import Confusion, confusion


@dataclass(frozen=True)
class Agreement:
    """Pairwise reviewer agreement for one smell."""

    smell: str
    matrix: Confusion
    samples: int
    pairs: int
    samples_with_one_review: int

    def to_dict(self) -> dict[str, object]:
        return {
            "smell": self.smell,
            "samples": self.samples,
            "pairs": self.pairs,
            "samples_with_one_review": self.samples_with_one_review,
            "mcc": self.matrix.mcc,
            "accuracy": self.matrix.accuracy,
            "confusion": self.matrix.to_dict(),
        }


def _is_smelly(severity: str) -> bool:
    return SEVERITY_RANK[severity] > SEVERITY_RANK["none"]


def pairwise(samples: Iterable[Sample], smell: str) -> Agreement:
    """Agreement among reviewers of one smell, as a confusion matrix.

    A sample reviewed once contributes no pair and is counted separately rather
    than dropped silently: how much of the corpus carries a second opinion at
    all is part of what the ceiling means.
    """
    pairs: list[tuple[bool, bool]] = []
    counted = alone = 0
    for sample in samples:
        if sample.smell != smell:
            continue
        counted += 1
        verdicts = [_is_smelly(review.severity) for review in sample.reviews]
        if len(verdicts) < 2:
            alone += 1
            continue
        for first, second in combinations(verdicts, 2):
            # Both directions, so neither reviewer is treated as the authority.
            pairs.append((first, second))
            pairs.append((second, first))

    return Agreement(
        smell=smell,
        matrix=confusion(pairs),
        samples=counted,
        pairs=len(pairs) // 2,
        samples_with_one_review=alone,
    )


def ceiling(samples: Iterable[Sample], smells: Iterable[str]) -> dict[str, Agreement]:
    """One agreement per smell, from a single pass over the reviews."""
    held = list(samples)
    return {smell: pairwise(held, smell) for smell in smells}
