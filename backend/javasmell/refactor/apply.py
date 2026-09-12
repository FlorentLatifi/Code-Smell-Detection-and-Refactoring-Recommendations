"""Writing a verified patch to disk, and the conditions that must hold first.

This is the only code in the system that changes the author's files, and it is
written to be refused easily. ENGINEERING.md §4 permits in-place modification
"with an explicit flag and a clean working tree", and both halves of that are
enforced here rather than assumed of the caller: a flag the caller must pass,
and a tree this module checks for itself.

**Why git and not a backup copy.** A copy beside the file is a second thing to
trust, to clean up and to get wrong, and it answers "how do I undo this" with a
procedure. A clean git tree answers it with one command the author already
knows. The requirement is therefore not bureaucracy: it *is* the undo.

**What "clean" means here.** No modified tracked file and no staged change
anywhere in the repository, not merely in the files about to be written.
Narrowing it to those files was considered and rejected: the point is that the
author can run one command afterwards and be certain of what it reverts, and
that certainty does not survive other edits sitting in the same tree.
Untracked files are allowed, because they are not something ``git restore`` would
touch and refusing on them would block the common case of a build directory.

**What is written.** Only files whose rewrite already passed verification, which
is to say only the contents of a :class:`~javasmell.refactor.patch.FilePatch`.
Anything the planner dropped, deferred or declined is not here to write.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from javasmell.refactor.patch import FilePatch

#: Long enough for git to answer on a large repository, short enough that a
#: hung command cannot hold the caller. `status` on a very large tree is the
#: slowest of the two calls and finishes well inside this.
GIT_TIMEOUT_S = 30

#: The command that undoes everything this module writes. Given back to the
#: caller rather than printed here, so the interface and the terminal can each
#: present it in their own words.
REVERT_COMMAND = "git restore ."


class Refused(StrEnum):
    """Why a write did not happen. Each value names a condition that failed."""

    #: The caller did not ask for it. The default is never to write.
    NOT_REQUESTED = "not_requested"

    #: `git` is not installed, or the path is not inside a working tree. Without
    #: it there is no undo, and this module will not write without one.
    NOT_A_REPOSITORY = "not_a_repository"

    #: The tree holds modified or staged changes. `git restore .` would then
    #: revert the author's own work along with the engine's.
    TREE_NOT_CLEAN = "tree_not_clean"

    #: The planner produced nothing to write.
    NOTHING_TO_WRITE = "nothing_to_write"

    #: A file changed on disk between being planned and being written. The
    #: rewrite was computed against bytes that are no longer there, so applying
    #: it would produce a file nobody verified.
    FILE_CHANGED = "file_changed"


@dataclass(frozen=True)
class Applied:
    """What reached the disk, and how to undo it."""

    #: Paths written, relative to the analysed root, in the order written.
    written: tuple[str, ...]
    #: The command that reverts them.
    revert: str = REVERT_COMMAND


@dataclass(frozen=True)
class Refusal:
    """Why nothing reached the disk."""

    reason: Refused
    detail: str = ""


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str] | None:
    """Run one git command, or None when git cannot be run at all.

    A fixed argument list and never a shell string, as ENGINEERING.md §6
    requires of every subprocess here: the path is user input, and a shell would
    give it a second meaning.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def working_tree_state(target: Path) -> Refusal | None:
    """Whether ``target`` sits in a clean git tree, or why it does not."""
    repository = target if target.is_dir() else target.parent
    inside = _git(repository, "rev-parse", "--is-inside-work-tree")
    if inside is None:
        return Refusal(Refused.NOT_A_REPOSITORY, "git is not available")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return Refusal(Refused.NOT_A_REPOSITORY, "the path is not inside a git working tree")

    # `--porcelain` is the stable, script-readable form; `--untracked-files=no`
    # because an untracked file is not something the revert command would touch.
    status = _git(repository, "status", "--porcelain", "--untracked-files=no")
    if status is None or status.returncode != 0:
        return Refusal(Refused.NOT_A_REPOSITORY, "git status could not be read")
    if status.stdout.strip():
        changed = len([line for line in status.stdout.splitlines() if line.strip()])
        return Refusal(
            Refused.TREE_NOT_CLEAN,
            f"{changed} file(s) already modified or staged",
        )
    return None


def apply_patches(
    patches: tuple[FilePatch, ...],
    target: Path,
    *,
    requested: bool = False,
) -> Applied | Refusal:
    """Write every verified rewrite, once every condition holds.

    ``requested`` defaults to False so that a caller who forgets the flag gets
    the safe answer. An engine that writes by accident is worse than one that
    never writes.

    The bytes each patch was computed from are compared against what is on disk
    now. A file that moved in between is not written and neither is any other:
    a half-applied patch is the one outcome with no clean undo, because
    ``git restore .`` would then revert some verified rewrites and leave others.
    """
    if not requested:
        return Refusal(Refused.NOT_REQUESTED, "writing was not asked for")
    if not patches:
        return Refusal(Refused.NOTHING_TO_WRITE, "the plan changed nothing")

    unclean = working_tree_state(target)
    if unclean is not None:
        return unclean

    # Kontrolluar i teri para se te shkruhet i pari: nje patch gjysmak eshte i
    # vetmi perfundim pa kthim te qarte.
    for patch in patches:
        try:
            current = patch.path.read_bytes()
        except OSError as failure:
            return Refusal(Refused.FILE_CHANGED, f"{patch.relative} could not be read: {failure}")
        if current != patch.before:
            return Refusal(
                Refused.FILE_CHANGED,
                f"{patch.relative} changed since it was measured",
            )

    written: list[str] = []
    for patch in patches:
        patch.path.write_bytes(patch.after)
        written.append(patch.relative)
    return Applied(tuple(written))
