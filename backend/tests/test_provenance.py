"""Tests for the environment block every result file carries.

The reproduction appendix rests entirely on this: it tells a reader which commit,
which interpreter and which machine produced each number, and the audit that
raised the claim to thirteen of fifteen steps read nothing else to decide whether
a regenerated file had changed or merely been produced again.

The case worth pinning is the quiet one. `git_commit` swallows every failure and
returns the empty string, so a run outside a checkout, or on a machine without
git, still writes a result -- with no revision in it. That is the right choice
for a long experiment, which should not die on its last write because git is
missing, but it means an empty commit is a real state a reader can meet. These
tests fix it as deliberate rather than accidental.
"""

from __future__ import annotations

import re
import subprocess

from javasmell.evaluation import provenance

COMMIT = re.compile(r"^[0-9a-f]{40}$")


def test_the_block_carries_the_three_fields_a_reader_needs():
    recorded = provenance.environment()

    assert set(recorded) == {"python", "platform", "commit"}
    assert recorded["python"], "an interpreter version is always knowable"
    assert recorded["platform"], "a platform is always knowable"


def test_the_commit_is_a_full_revision_inside_a_checkout():
    """Abbreviated hashes collide across large histories; the block stores all 40."""
    assert COMMIT.match(provenance.git_commit())


def test_a_missing_git_records_an_empty_commit_rather_than_failing(monkeypatch):
    """An experiment that has run for hours must not lose its result to this."""

    def absent(*_args, **_kwargs):
        raise OSError("git not found")

    monkeypatch.setattr(subprocess, "run", absent)

    assert provenance.git_commit() == ""
    assert provenance.environment()["commit"] == ""


def test_a_git_that_fails_records_an_empty_commit(monkeypatch):
    """Outside a checkout git exits non-zero and prints nothing to stdout."""

    def outside_a_checkout(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="fatal")

    monkeypatch.setattr(subprocess, "run", outside_a_checkout)

    assert provenance.git_commit() == ""


def test_a_hanging_git_is_given_up_on(monkeypatch):
    """The call is bounded, because a stalled git would stall the whole run."""

    def hangs(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=provenance.GIT_TIMEOUT_S)

    monkeypatch.setattr(subprocess, "run", hangs)

    assert provenance.git_commit() == ""
