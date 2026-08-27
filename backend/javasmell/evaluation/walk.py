"""One traversal of the corpus, shared by everything that needs one.

Two scripts now walk the corpus -- one scores the rule detectors, one builds the
feature table -- and both need the same four steps: group the samples by
repository, analyse each repository whole, resolve every sample to an entity,
and count the ones that never got there. Writing that loop twice is how the two
LOC counters drifted apart (VD-21), and here the stakes are higher: a difference
in which samples reach an entity would silently change the denominator of one
result and not the other, and the two would no longer be comparable.

Whole repositories are analysed rather than the sampled files alone because
ATFD, CBO, DIT and TCC are defined against the other types of the project
(VD-16). Each project model is released before the next repository is opened;
the corpus is 4.4 GB and does not fit in memory at once.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Container, Iterable, Iterator
from dataclasses import dataclass

from javasmell.analysis import analyze_path
from javasmell.evaluation.corpus import Corpus
from javasmell.evaluation.matcher import ProjectIndex
from javasmell.evaluation.mlcq import Sample
from javasmell.model.entities import ClassInfo, MethodInfo, ProjectModel


@dataclass(frozen=True)
class Resolved:
    """A sample and the entity its reviewers were looking at.

    ``cls`` is never None: a sample that did not resolve is counted in
    ``unreached`` instead, so consumers never repeat that check.
    """

    sample: Sample
    cls: ClassInfo
    method: MethodInfo | None


@dataclass(frozen=True)
class AnalysedRepository:
    """One repository, measured, with its samples resolved to entities."""

    repository: str
    number: int  # 1-based, for progress reporting
    total: int
    project: ProjectModel
    matched: tuple[Resolved, ...]
    unreached: dict[str, int]

    @property
    def name(self) -> str:
        """``apache/syncope`` from the published clone URL."""
        return self.repository.partition(":")[2].removesuffix(".git")


def group_by_repository(samples: Iterable[Sample]) -> dict[str, list[Sample]]:
    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.repository].append(sample)
    return dict(grouped)


def _analyse_one(
    corpus: Corpus, repository: str, samples: list[Sample], number: int, total: int
) -> AnalysedRepository:
    unreached: dict[str, int] = defaultdict(int)
    present = [s for s in samples if corpus.has_source(s)]
    if not present:
        unreached["no_file"] += len(samples)
        return AnalysedRepository(
            repository=repository,
            number=number,
            total=total,
            project=ProjectModel(root=""),
            matched=(),
            unreached=dict(unreached),
        )

    project = analyze_path(corpus.analysable_root(present[0]))
    index = ProjectIndex(project)

    matched: list[Resolved] = []
    for sample in samples:
        if not corpus.has_source(sample):
            unreached["no_file"] += 1
            continue
        result = index.match(sample)
        if not result.ok or result.cls is None:
            unreached[result.outcome.value] += 1
            continue
        matched.append(Resolved(sample=sample, cls=result.cls, method=result.method))

    return AnalysedRepository(
        repository=repository,
        number=number,
        total=total,
        project=project,
        matched=tuple(matched),
        unreached=dict(unreached),
    )


def iter_repositories(
    corpus: Corpus,
    samples: Iterable[Sample],
    limit: int = 0,
    skip: Container[str] | None = None,
) -> Iterator[AnalysedRepository]:
    """Analyse each repository in turn, in a stable order.

    Repositories are visited alphabetically so that a run truncated by
    ``limit`` covers the same projects every time and two trial runs stay
    comparable. ``skip`` lets an interrupted run resume: the numbering still
    counts every repository, so progress reads against the whole job rather
    than against what is left of it.
    """
    grouped = group_by_repository(samples)
    repositories = sorted(grouped)
    if limit:
        repositories = repositories[:limit]
    for number, repository in enumerate(repositories, 1):
        if skip is not None and repository in skip:
            continue
        yield _analyse_one(corpus, repository, grouped[repository], number, len(repositories))
