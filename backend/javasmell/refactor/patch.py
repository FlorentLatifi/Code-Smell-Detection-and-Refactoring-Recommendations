"""Turning what the engine would rewrite into a patch the author can review.

Until now the engine could show a rewrite and never hand one over: the API
previews a single site and the CLI reports findings. ENGINEERING.md §4 says what
the missing step is allowed to be -- *output to a copy or a patch*, never a write
in place -- and a unified diff is the form that keeps the author in charge. It is
read before it is applied, it applies with ``git apply``, and it fails loudly if
the file moved underneath it.

**Several findings, one file.** A single method routinely carries Long Method,
Deep Nesting and Long Parameter List at once, and each transformation computes
its edits against the *original* bytes. Two of them will usually claim the same
lines. `edits.check` already refuses an overlapping pair rather than inventing an
order for them, so this module accepts transformations one at a time and keeps
only those whose edits do not collide with what it has already taken. The rest
are **deferred**, not lost: they are reported, and re-running against the patched
tree offers them again from a file that has moved on.

That greedy order is by position in the file, which is arbitrary but fixed --
what matters is that two runs over the same input produce the same patch, since
a patch that varies between runs is not something a reader can check.

**Nothing enters the patch unverified.** Each rewritten file goes through
``verify.check``: syntax always, and ``javac`` when it is on the path. A file
whose rewrite does not pass is dropped from the patch entirely rather than
offered with a warning, because a patch is a thing people apply.
"""

from __future__ import annotations

import difflib
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from javasmell.detectors.base import Smell
from javasmell.refactor.base import Refusal
from javasmell.refactor.edits import Edit, EditConflict, apply_edits
from javasmell.refactor.edits import check as check_edits
from javasmell.refactor.locate import FileIndex
from javasmell.refactor.registry import for_smell
from javasmell.refactor.verify import Verdict, check

#: Git's marker for a final line that carries no newline. Without it a patch
#: whose last line lacks one is rejected by ``git apply``.
NO_NEWLINE = "\\ No newline at end of file"


@dataclass(frozen=True)
class Change:
    """One transformation the engine ran, and where."""

    refactoring: str
    smell_type: str
    class_name: str
    method: str | None
    start_line: int

    def describe(self) -> str:
        where = self.class_name if self.method is None else f"{self.class_name}.{self.method}"
        return f"{self.refactoring} on {where} (line {self.start_line}, {self.smell_type})"


@dataclass(frozen=True)
class FilePatch:
    """One file's rewrite, with what went in and what was left out."""

    path: Path
    #: Path as it appears in the diff header, relative to the analysed root.
    relative: str
    before: bytes
    after: bytes
    applied: tuple[Change, ...]
    #: Transformations that would have collided with an accepted one.
    deferred: tuple[Change, ...]
    verdict: Verdict


@dataclass(frozen=True)
class Rejected:
    """A file the engine rewrote but would not offer, and why."""

    relative: str
    verdict: Verdict
    detail: str


def _decoded(source: bytes) -> str | None:
    """Java source as text, or None when it is not UTF-8 after all.

    The engine works in bytes throughout and only needs text here, to diff. A
    file that will not decode is one this tool has no business rewriting.
    """
    try:
        return source.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _relative(path: Path, root: Path) -> str:
    base = root if root.is_dir() else root.parent
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.name


def plan_file(
    path: Path,
    root: Path,
    smells: Sequence[Smell],
    javac: str | None,
) -> tuple[FilePatch | Rejected | None, list[Declined]]:
    """Everything the engine can safely change in one file, as a single rewrite.

    Returns the plan and one record per site the engine declined outright. A
    ``None`` plan means there was nothing to offer -- no automated smell, no
    locatable site, or every transformation refused. That is the ordinary outcome
    for most files and is not a failure, which is why the refusals come back
    named rather than being dropped on the floor.
    """
    try:
        source = path.read_bytes()
    except OSError:
        return None, []

    automated = [s for s in smells if for_smell(s.smell_type) is not None]
    if not automated:
        return None, []

    # Fixed order, so two runs over one input produce one patch.
    automated.sort(key=lambda s: (s.start_line, s.smell_type, s.class_name))

    index = FileIndex(str(path), source)
    taken: list[Edit] = []
    # Emrat qe rishkrimet e meparshme te ketij skedari i shtuan. Mbahen per
    # skedar e jo per klase: nje emer unik mbi tere skedarin eshte gjithnje i
    # vlefshem, dhe ndarja sipas klases do te kerkonte nje celes te qendrueshem
    # qe vendi nuk e mban.
    reserved: set[str] = set()
    applied: list[Change] = []
    deferred: list[Change] = []
    declined: list[Declined] = []

    for smell in automated:
        found = for_smell(smell.smell_type)
        assert found is not None  # filtered above
        refactoring, transform = found
        method = None if smell.method is None else smell.method.split("(")[0]

        def record(reason: str, detail: str, smell: Smell = smell, name: str = refactoring) -> None:
            declined.append(
                Declined(
                    file_path=_relative(path, root),
                    class_name=smell.class_name,
                    method=None if smell.method is None else smell.method.split("(")[0],
                    start_line=smell.start_line,
                    smell_type=smell.smell_type,
                    refactoring=name,
                    reason=reason,
                    detail=detail,
                )
            )

        site = index.find(smell.class_name, smell.start_line, method)
        if site is None:
            # Nuk eshte refuzim i transformimit: vendi nuk u gjet dot ne peme.
            record(Refusal.SHAPE_NOT_MATCHED.value, "the entity was not found at that line")
            continue
        outcome = transform(site, frozenset(reserved))
        if not outcome.applied:
            assert outcome.refusal is not None
            record(outcome.refusal.value, outcome.detail)
            continue

        change = Change(refactoring, smell.smell_type, smell.class_name, method, smell.start_line)
        try:
            check_edits([*taken, *outcome.edits])
        except EditConflict:
            deferred.append(change)
            continue
        taken.extend(outcome.edits)
        reserved.update(outcome.introduced)
        applied.append(change)

    if not applied:
        return None, declined

    after = apply_edits(source, taken)
    result = check(javac, source, after, path.name)
    relative = _relative(path, root)
    if not result.verdict.passed:
        return Rejected(relative, result.verdict, result.detail), declined

    return FilePatch(
        path=path,
        relative=relative,
        before=source,
        after=after,
        applied=tuple(applied),
        deferred=tuple(deferred),
        verdict=result.verdict,
    ), declined


@dataclass(frozen=True)
class Declined:
    """One site the engine would not rewrite, and the reason it gave.

    The reason was always computed -- every transformation returns a typed
    :class:`~javasmell.refactor.base.Refusal` -- and until now the planner threw
    it away and kept only a count. A count answers "how many" and leaves the
    question a user actually asks, which is "why not this one" (VD-89). The
    corpus-wide table of refusal reasons in the Results chapter is built from
    the same vocabulary, so a reader of the tool and a reader of the thesis now
    see the same words.
    """

    file_path: str
    class_name: str
    method: str | None
    start_line: int
    smell_type: str
    refactoring: str
    reason: str
    detail: str


@dataclass(frozen=True)
class Plan:
    """What a whole run would change, and everything it would not.

    The three ways of not changing something are kept apart because they mean
    different things to a reader: the engine *declined* (no safe rewrite exists
    for that site), it *deferred* (a safe rewrite exists but collides with one
    already in the patch), or it *dropped* (the rewrite did not verify).
    """

    patches: tuple[FilePatch, ...]
    dropped: tuple[Rejected, ...]
    #: Sites where the transformation itself reported "not applicable", each
    #: with the reason it reported.
    declines: tuple[Declined, ...]
    #: Files the run never got to, because the time budget ran out first.
    unreached: int = 0

    @property
    def declined(self) -> int:
        return len(self.declines)

    @property
    def changes(self) -> int:
        return sum(len(p.applied) for p in self.patches)

    @property
    def deferred(self) -> int:
        return sum(len(p.deferred) for p in self.patches)


def plan(
    root: Path,
    smells: Iterable[Smell],
    javac: str | None,
    deadline: float | None = None,
) -> Plan:
    """Group the findings by file and plan each file's rewrite.

    ``deadline`` is a ``time.monotonic`` reading to stop at. Verification runs
    ``javac`` once per rewritten file and a compile of a large generated file was
    measured at over twelve seconds, so a whole-project patch is exactly the
    "cap total analysis time" case ENGINEERING.md §6 describes. Running out of
    budget is not an error: what was planned so far is verified and applicable
    just the same, and the files never reached are counted so the caller can say
    the patch is partial rather than implying it is complete.

    The check happens between files, never inside one. A half-planned file would
    be a rewrite nobody verified.
    """
    by_file: dict[str, list[Smell]] = {}
    for smell in smells:
        by_file.setdefault(smell.file_path, []).append(smell)

    patches: list[FilePatch] = []
    dropped: list[Rejected] = []
    declined: list[Declined] = []
    unreached = 0
    for file_path in sorted(by_file):
        if deadline is not None and time.monotonic() >= deadline:
            unreached += 1
            continue
        planned, refused = plan_file(Path(file_path), root, by_file[file_path], javac)
        declined.extend(refused)
        if isinstance(planned, FilePatch):
            patches.append(planned)
        elif isinstance(planned, Rejected):
            dropped.append(planned)
    return Plan(tuple(patches), tuple(dropped), tuple(declined), unreached)


def _mark_missing_newline(lines: list[str]) -> list[str]:
    """Append git's marker after any content line that lacks its newline.

    ``difflib`` emits the line exactly as it found it, so a file with no final
    newline yields a hunk whose last line runs into whatever follows. ``git
    apply`` rejects that. The marker is what git itself writes in the same place.
    """
    out: list[str] = []
    for line in lines:
        if line.startswith(("+", "-", " ")) and not line.endswith("\n"):
            out.append(line + "\n")
            out.append(NO_NEWLINE + "\n")
        else:
            out.append(line)
    return out


def unified(patches: Sequence[FilePatch]) -> str:
    """The whole plan as one unified diff.

    Headers are ``a/`` and ``b/`` prefixed and paths are relative to the analysed
    root, which is what lets the result be piped straight into ``git apply`` from
    that directory.
    """
    chunks: list[str] = []
    for patch in patches:
        before = _decoded(patch.before)
        after = _decoded(patch.after)
        if before is None or after is None:
            continue
        diff = difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{patch.relative}",
            tofile=f"b/{patch.relative}",
        )
        chunks.extend(_mark_missing_newline(list(diff)))
    return "".join(chunks)
