"""Tests for the one module that writes to the author's files.

Every test here is about a refusal. That is deliberate: this is the only code in
the system that can destroy work, and the property worth pinning is not that it
writes but that it declines to. The single test that does write checks the bytes
that landed and that the revert command is the one handed back.

`git` is required, not stubbed. The conditions being enforced are conditions of a
real working tree, and a stub would test the stub.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from javasmell.refactor.apply import Applied, Refusal, Refused, apply_patches, working_tree_state
from javasmell.refactor.patch import FilePatch
from javasmell.refactor.verify import Verdict

GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(not GIT, reason="git not installed")

BEFORE = b"class T {\n    void m() {}\n}\n"
AFTER = b"class T {\n    void m() {\n        System.out.println(1);\n    }\n}\n"


def repository(tmp_path: Path) -> Path:
    """A git tree with one committed Java file, which is the clean starting point."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "T.java").write_bytes(BEFORE)
    for command in (
        ["init", "-q"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "T"],
        # Pinned, or the round trip asserts about the machine's git config rather
        # than about this module: with autocrlf on, Windows gets CRLF back from
        # `restore` and the bytes no longer match what was committed.
        ["config", "core.autocrlf", "false"],
        ["add", "."],
        ["commit", "-q", "-m", "first"],
    ):
        subprocess.run([str(GIT), "-C", str(root), *command], check=True, capture_output=True)
    return root


def patch_for(root: Path, before: bytes = BEFORE, after: bytes = AFTER) -> FilePatch:
    return FilePatch(
        path=root / "T.java",
        relative="T.java",
        before=before,
        after=after,
        applied=(),
        deferred=(),
        verdict=Verdict.COMPILES,
    )


# ----------------------------------------------------------------------
# The flag
# ----------------------------------------------------------------------
def test_nothing_is_written_without_being_asked(tmp_path: Path) -> None:
    """The default is never to write. A forgotten flag must give the safe answer."""
    root = repository(tmp_path)

    result = apply_patches((patch_for(root),), root)

    assert isinstance(result, Refusal)
    assert result.reason is Refused.NOT_REQUESTED
    assert (root / "T.java").read_bytes() == BEFORE


# ----------------------------------------------------------------------
# The tree
# ----------------------------------------------------------------------
def test_a_path_outside_a_repository_is_refused(tmp_path: Path) -> None:
    """Without git there is no undo, and this module will not write without one."""
    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / "T.java").write_bytes(BEFORE)

    result = apply_patches((patch_for(loose),), loose, requested=True)

    assert isinstance(result, Refusal)
    assert result.reason is Refused.NOT_A_REPOSITORY
    assert (loose / "T.java").read_bytes() == BEFORE


def test_a_modified_tree_is_refused(tmp_path: Path) -> None:
    """`git restore .` would revert the author's own work along with the engine's."""
    root = repository(tmp_path)
    (root / "Other.java").write_bytes(b"class Other {}\n")
    subprocess.run(
        [str(GIT), "-C", str(root), "add", "Other.java"], check=True, capture_output=True
    )

    result = apply_patches((patch_for(root),), root, requested=True)

    assert isinstance(result, Refusal)
    assert result.reason is Refused.TREE_NOT_CLEAN
    assert "1 file" in result.detail


def test_an_untracked_file_does_not_block_the_write(tmp_path: Path) -> None:
    """`git restore .` does not touch an untracked file, so it is not a reason to stop.

    Refusing on one would block the common case of a build directory sitting
    beside the source.
    """
    root = repository(tmp_path)
    (root / "build.log").write_text("noise", encoding="utf-8")

    assert working_tree_state(root) is None


# ----------------------------------------------------------------------
# The bytes
# ----------------------------------------------------------------------
def test_a_file_that_moved_since_it_was_measured_is_refused(tmp_path: Path) -> None:
    """The rewrite was computed against bytes that are no longer there."""
    root = repository(tmp_path)
    patch = patch_for(root, before=b"class T { /* something else */ }\n")

    result = apply_patches((patch,), root, requested=True)

    assert isinstance(result, Refusal)
    assert result.reason is Refused.FILE_CHANGED


def test_one_stale_file_stops_every_write(tmp_path: Path) -> None:
    """A half-applied patch is the one outcome with no clean undo.

    `git restore .` would then revert the verified rewrites that did land and
    leave the author to work out which those were.
    """
    root = repository(tmp_path)
    (root / "U.java").write_bytes(BEFORE)
    subprocess.run([str(GIT), "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [str(GIT), "-C", str(root), "commit", "-q", "-m", "second"], check=True, capture_output=True
    )

    good = patch_for(root)
    stale = FilePatch(
        path=root / "U.java",
        relative="U.java",
        before=b"class U { /* not what is on disk */ }\n",
        after=AFTER,
        applied=(),
        deferred=(),
        verdict=Verdict.COMPILES,
    )

    result = apply_patches((good, stale), root, requested=True)

    assert isinstance(result, Refusal)
    assert (root / "T.java").read_bytes() == BEFORE, "the first file must not have been written"


def test_an_empty_plan_is_refused_rather_than_reported_as_success(tmp_path: Path) -> None:
    root = repository(tmp_path)

    result = apply_patches((), root, requested=True)

    assert isinstance(result, Refusal)
    assert result.reason is Refused.NOTHING_TO_WRITE


# ----------------------------------------------------------------------
# The write
# ----------------------------------------------------------------------
def test_a_verified_patch_reaches_the_file(tmp_path: Path) -> None:
    """Every condition holds, so the bytes land and the undo is named."""
    root = repository(tmp_path)

    result = apply_patches((patch_for(root),), root, requested=True)

    assert isinstance(result, Applied)
    assert result.written == ("T.java",)
    assert result.revert == "git restore ."
    assert (root / "T.java").read_bytes() == AFTER


def test_the_named_revert_command_actually_reverts_it(tmp_path: Path) -> None:
    """The claim the whole design rests on, checked rather than asserted in prose."""
    root = repository(tmp_path)
    apply_patches((patch_for(root),), root, requested=True)

    subprocess.run([str(GIT), "-C", str(root), "restore", "."], check=True, capture_output=True)

    assert (root / "T.java").read_bytes() == BEFORE
