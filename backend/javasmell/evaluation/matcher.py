"""Linking an MLCQ sample to the entity this project's parser produced for it.

This is the joint on which the whole evaluation turns. MLCQ says "this class,
in this file, at this commit, is a Blob"; the detectors say "this ``ClassInfo``
is a God Class". Getting the two to refer to the same piece of code is what
makes precision and recall mean anything, and getting it subtly wrong, an
overload resolved to its sibling, an inner class taken for its outer, would
produce numbers that look entirely reasonable and are entirely false.

The design follows from a measurement rather than an assumption. Across the
samples materialised so far, MLCQ's ``start_line`` and ``end_line`` agree with
the parser exactly for 791 of 791 classes and 871 of 875 methods, while the
names agree far less often, because ``code_name`` mixes four formats (see
:attr:`~javasmell.evaluation.mlcq.Sample.simple_name`). So the **line range is
the anchor and the name is the check**, not the other way round.

That ordering settles the two ambiguities the plan flagged as risks, at no
cost: two overloads cannot begin on the same line, and neither can an inner
class and the class enclosing it. Neither needs a symbol resolver.

Anything that does not line up exactly is reported as a specific
:class:`MatchOutcome` rather than being forced into a match. An unmatched
sample subtracts from coverage, which is a stated limitation of the study; a
wrongly matched one corrupts every number that follows, silently.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum

from javasmell.evaluation.corpus import WINDOWS_LONG_PATH_PREFIX
from javasmell.evaluation.mlcq import Sample
from javasmell.model.entities import ClassInfo, MethodInfo, ProjectModel

CLASS_ENTITY = "class"


class MatchOutcome(StrEnum):
    """Why a sample did or did not reach an entity.

    The failures are kept apart because they mean different things in the
    Results chapter: ``NO_FILE`` is a gap in the corpus, ``SYNTAX_ERRORS`` is a
    limit of the grammar we parse with, and ``NO_ENTITY`` on a cleanly parsed
    file means the code moved between the commit MLCQ reviewed and the one we
    hold.
    """

    MATCHED = "matched"
    NO_FILE = "no_file"  # never fetched, or not part of this project
    NO_ENTITY = "no_entity"  # nothing begins on that line
    SYNTAX_ERRORS = "syntax_errors"  # nothing found, and the file did not parse cleanly
    NAME_MISMATCH = "name_mismatch"  # something begins there, under another name
    SPAN_MISMATCH = "span_mismatch"  # right name and start, different extent
    AMBIGUOUS = "ambiguous"  # several entities of that name begin on that line


@dataclass(frozen=True)
class MatchResult:
    """One sample's fate, carrying the entity when there is one."""

    sample: Sample
    outcome: MatchOutcome
    cls: ClassInfo | None = None
    method: MethodInfo | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome is MatchOutcome.MATCHED


def normalise_path(path: str) -> str:
    """One spelling of a path, so that two sources can be compared at all.

    The parser reports whatever ``os.walk`` handed it (backslashes, and on
    Windows the extended-length prefix without which the corpus cannot be read
    at all), while MLCQ publishes ``/a/b/C.java``. Neither side is wrong; they
    just have to be reduced to the same form before a lookup can work.
    """
    return path.removeprefix(WINDOWS_LONG_PATH_PREFIX).replace("\\", "/").strip("/")


def relative_key(file_path: str, root: str) -> str:
    """``file_path`` written the way MLCQ writes it: relative to the checkout."""
    normalised = normalise_path(file_path)
    normalised_root = normalise_path(root)
    if normalised_root and normalised.startswith(normalised_root):
        normalised = normalised[len(normalised_root) :]
    return normalised.strip("/")


class ProjectIndex:
    """Every entity of one analysed repository, keyed for sample lookup.

    Built once per repository and queried once per sample. A repository holds
    thousands of files of which a handful were ever reviewed, so the alternative
    (parsing per sample) would dominate the evaluation's runtime for no gain.
    """

    def __init__(self, project: ProjectModel) -> None:
        self._classes: dict[str, list[ClassInfo]] = defaultdict(list)
        self._methods: dict[str, list[tuple[ClassInfo, MethodInfo]]] = defaultdict(list)
        self._broken: set[str] = set()
        for unit in project.units:
            key = relative_key(unit.file_path, project.root)
            if unit.has_syntax_errors:
                self._broken.add(key)
            self._classes[key].extend(unit.classes)
            for cls in unit.classes:
                self._methods[key].extend((cls, method) for method in cls.methods)

    def match(self, sample: Sample) -> MatchResult:
        key = sample.relative_path
        if key not in self._classes:
            return MatchResult(sample, MatchOutcome.NO_FILE, detail=key)

        candidates: list[tuple[ClassInfo, MethodInfo | None]]
        if sample.entity_type == CLASS_ENTITY:
            candidates = [
                (cls, None) for cls in self._classes[key] if cls.start_line == sample.start_line
            ]
        else:
            candidates = [
                (cls, method)
                for cls, method in self._methods[key]
                if method.start_line == sample.start_line
            ]
        return self._resolve(sample, candidates, broken=key in self._broken)

    def _resolve(
        self,
        sample: Sample,
        candidates: list[tuple[ClassInfo, MethodInfo | None]],
        *,
        broken: bool,
    ) -> MatchResult:
        if not candidates:
            outcome = MatchOutcome.SYNTAX_ERRORS if broken else MatchOutcome.NO_ENTITY
            return MatchResult(sample, outcome, detail=f"line {sample.start_line}")

        named = [
            (cls, method)
            for cls, method in candidates
            if _entity_name(cls, method) == sample.simple_name
        ]
        if not named:
            found = ", ".join(sorted({_entity_name(c, m) for c, m in candidates}))
            return MatchResult(
                sample,
                MatchOutcome.NAME_MISMATCH,
                detail=f"{sample.simple_name} != {found}",
            )
        if len(named) > 1:
            return MatchResult(sample, MatchOutcome.AMBIGUOUS, detail=f"{len(named)} candidates")

        cls, method = named[0]
        end_line = cls.end_line if method is None else method.end_line
        if end_line != sample.end_line:
            return MatchResult(
                sample,
                MatchOutcome.SPAN_MISMATCH,
                cls=cls,
                method=method,
                detail=f"ends at {end_line}, MLCQ says {sample.end_line}",
            )
        return MatchResult(sample, MatchOutcome.MATCHED, cls=cls, method=method)


def _entity_name(cls: ClassInfo, method: MethodInfo | None) -> str:
    return cls.name if method is None else method.name


def match_samples(project: ProjectModel, samples: Iterable[Sample]) -> Iterator[MatchResult]:
    """Match every sample belonging to one analysed repository."""
    index = ProjectIndex(project)
    for sample in samples:
        yield index.match(sample)


@dataclass(frozen=True)
class MatchReport:
    """How many samples reached an entity, and why the rest did not.

    This goes into the thesis as it stands: ``matched`` is the denominator of
    every precision and recall figure that follows, so the shortfall has to be
    accounted for rather than left for a reader to notice on their own.
    """

    counts: dict[MatchOutcome, int]

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def matched(self) -> int:
        return self.counts.get(MatchOutcome.MATCHED, 0)

    @property
    def match_rate(self) -> float:
        return self.matched / self.total if self.total else 0.0

    def describe(self) -> str:
        lines = [f"{self.matched}/{self.total} samples matched ({self.match_rate:.1%})"]
        for outcome, count in sorted(self.counts.items(), key=lambda kv: -kv[1]):
            if outcome is not MatchOutcome.MATCHED:
                lines.append(f"  {outcome.value:<14} {count:5d}  {count / self.total:6.1%}")
        return "\n".join(lines)


def summarise(results: Iterable[MatchResult]) -> MatchReport:
    counts: dict[MatchOutcome, int] = defaultdict(int)
    for result in results:
        counts[result.outcome] += 1
    return MatchReport(counts=dict(counts))
