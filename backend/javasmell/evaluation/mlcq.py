"""Reading the MLCQ ground truth (Madeyski & Lewowski, 2020).

MLCQ ships reviews, not labels. Each code sample was rated independently by
several professional developers, and they disagree often enough that turning
reviews into a single label is a methodological choice rather than a parsing
detail: in the published data 25.9% of multiply-reviewed samples carry more
than one severity, and 25.6% disagree even on the binary question of whether
the smell is present at all.

That choice therefore lives here as an explicit, swappable strategy so the
Results chapter can report how sensitive the measured performance is to it,
instead of inheriting one silent convention.

The file itself has two traps worth naming, both of which cost a debugging
session if discovered later: it is semicolon-delimited despite the ``.csv``
extension, and it was written in a locale that uses a decimal comma, so
``is_from_industry_relevant_project`` contains values like ``0,5``.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# MLCQ's smell names mapped onto the detector names in
# ``javasmell.detectors.rules.REFACTORINGS``. Only these four smells have
# ground truth; the other four detectors this project implements are reported
# descriptively (see docs/DECISIONS.md, VD-05).
SMELL_TO_DETECTOR = {
    "blob": "GodClass",
    "data class": "DataClass",
    "long method": "LongMethod",
    "feature envy": "FeatureEnvy",
}

# Ordinal, because severity is ordered and the aggregation strategies need to
# do arithmetic on it. Matches javasmell.detectors.base.Severity from `minor`
# upwards; `none` has no counterpart there because a detector that finds
# nothing returns no Smell at all.
SEVERITY_RANK = {"none": 0, "minor": 1, "major": 2, "critical": 3}
RANK_TO_SEVERITY = {rank: name for name, rank in SEVERITY_RANK.items()}

CSV_DELIMITER = ";"


class Aggregation(StrEnum):
    """How several reviewers' severities collapse into one label.

    ``MEAN`` is the default. Majority voting (the obvious first choice) is
    undefined for the case that dominates this data set: 3511 of 4747
    multiply-reviewed samples have exactly two reviewers, so a disagreement has
    no majority to find. Rounding the mean half *up* resolves those ties toward
    the more severe label, which keeps a smell that one reviewer saw rather
    than discarding it.
    """

    MEAN = "mean"  # round half up: a tie counts as the smellier label
    MAX = "max"  # any reviewer who saw it is enough
    MIN = "min"  # only what every reviewer saw
    UNANIMOUS = "unanimous"  # discard disagreements entirely


@dataclass(frozen=True)
class Review:
    """One reviewer's verdict on one sample."""

    sample_id: str
    reviewer_id: str
    smell: str
    severity: str

    @property
    def rank(self) -> int:
        return SEVERITY_RANK[self.severity]


@dataclass(frozen=True)
class Sample:
    """One reviewed code entity, with every review it received.

    ``start_line``/``end_line`` are the reliable way to find this entity in the
    source; ``code_name`` is not (see :attr:`simple_name`).
    """

    sample_id: str
    smell: str
    entity_type: str  # "class" or "function"
    code_name: str
    repository: str  # as published: git@github.com:owner/name.git
    commit_hash: str
    path: str  # repository-relative, leading slash included
    start_line: int
    end_line: int
    reviews: tuple[Review, ...]

    @property
    def detector_name(self) -> str:
        """The name this project's detectors use for the same smell."""
        return SMELL_TO_DETECTOR[self.smell]

    @property
    def simple_name(self) -> str:
        """The bare entity name: no package, no owner, no parameter list.

        ``code_name`` is not one format but four, and which one appears carries
        no information we can use: ``a.b.C`` for types, ``a.b.C#m`` for most
        methods, ``a.b.C.m`` for every constructor and for 333 ordinary methods
        besides, each optionally followed by ``" int|String"``. Four rows even
        have an empty type segment (``a.b..m``), where the extraction tool
        evidently gave up. Only the final segment is dependable, which is why
        matching is anchored on the line range and uses the name to verify.
        """
        head, _, _ = self.code_name.partition(" ")
        return head.replace("#", ".").rpartition(".")[2]

    @property
    def owner_and_name(self) -> tuple[str, str]:
        """``apache/syncope`` from ``git@github.com:apache/syncope.git``."""
        _, _, tail = self.repository.partition(":")
        owner, _, name = tail.removesuffix(".git").partition("/")
        return owner, name

    @property
    def group(self) -> str:
        """Grouping key for leakage-free splits: the repository (VD-12)."""
        return self.repository

    @property
    def relative_path(self) -> str:
        return self.path.lstrip("/")

    @property
    def is_unanimous(self) -> bool:
        return len({r.severity for r in self.reviews}) == 1

    def severity_rank(self, how: Aggregation = Aggregation.MEAN) -> int | None:
        """The aggregated label, or None when the strategy rejects the sample."""
        ranks = [r.rank for r in self.reviews]
        if not ranks:
            return None
        if how is Aggregation.MAX:
            return max(ranks)
        if how is Aggregation.MIN:
            return min(ranks)
        if how is Aggregation.UNANIMOUS:
            return ranks[0] if self.is_unanimous else None
        # Mean, rounded half up. Python's round() is banker's rounding, which
        # would send a 0.5 tie *down* to "no smell", the opposite of intent.
        return int(sum(ranks) / len(ranks) + 0.5)

    def is_smelly(self, how: Aggregation = Aggregation.MEAN) -> bool | None:
        """Ground truth for the binary task the rule detectors perform."""
        rank = self.severity_rank(how)
        return None if rank is None else rank > SEVERITY_RANK["none"]

    def severity_label(self, how: Aggregation = Aggregation.MEAN) -> str | None:
        rank = self.severity_rank(how)
        return None if rank is None else RANK_TO_SEVERITY[rank]


def load_reviews(csv_path: str | Path) -> Iterator[tuple[Review, dict[str, str]]]:
    """Stream the raw file, yielding each review with the row it came from.

    Streaming rather than returning a list keeps the 7.5 MB file out of memory
    twice over when the caller only wants to group it.
    """
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=CSV_DELIMITER):
            review = Review(
                sample_id=row["sample_id"],
                reviewer_id=row["reviewer_id"],
                smell=row["smell"],
                severity=row["severity"],
            )
            yield review, row


def load_samples(csv_path: str | Path) -> list[Sample]:
    """Every reviewed sample, with its reviews gathered.

    A ``sample_id`` identifies one entity reviewed for one smell, so grouping
    by it is what turns 14739 review rows into 4770 labelled samples.
    """
    grouped: dict[str, list[Review]] = defaultdict(list)
    first_row: dict[str, dict[str, str]] = {}

    for review, row in load_reviews(csv_path):
        grouped[review.sample_id].append(review)
        first_row.setdefault(review.sample_id, row)

    samples = []
    for sample_id, reviews in grouped.items():
        row = first_row[sample_id]
        samples.append(
            Sample(
                sample_id=sample_id,
                smell=row["smell"],
                entity_type=row["type"],
                code_name=row["code_name"],
                repository=row["repository"],
                commit_hash=row["commit_hash"],
                path=row["path"],
                start_line=int(row["start_line"]),
                end_line=int(row["end_line"]),
                reviews=tuple(reviews),
            )
        )
    return samples


def repositories_by_sample_count(samples: Iterable[Sample]) -> list[tuple[str, int]]:
    """Repositories ordered by how many samples they contribute, most first.

    The corpus download is long and may be interrupted, so fetching in this
    order means whatever finished is the most useful subset available.
    """
    counts: dict[str, int] = defaultdict(int)
    for sample in samples:
        counts[sample.repository] += 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
