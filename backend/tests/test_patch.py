"""Tests for turning a rewrite into a patch.

The transformations themselves are tested elsewhere. What is new here is the
combining: several findings in one file become one rewrite, and the questions are
which ones may travel together, what happens to the rest, and whether the diff
that comes out is one `git apply` accepts.

`javac` is not required by any of these. `verify.check` degrades to a syntax
check when it is absent, so the patch is still verified, just less strongly --
and a test that only ran where a JDK is installed is a test that quietly stops
running.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from javasmell.analysis import analyze_path
from javasmell.detectors.base import Smell
from javasmell.detectors.rules import detect_all
from javasmell.refactor.patch import plan, plan_file, unified

# `process` is private with six parameters and 33 effective lines, so Extract
# Method and Introduce Parameter Object both apply to it; `report` is void with
# four levels of nesting, so Guard Clauses applies there. One file, three
# rewrites, two of them on the same method.
LEDGER = """package com.acme;

public class Ledger {
    private int taxRate = 2;

    private int process(int[] xs, int mode, boolean flag, String tag, int extra, int more) {
        int sum = 0;
        for (int i = 0; i < xs.length; i++) {
            sum += xs[i];
            System.out.println(sum);
            System.out.println(i);
            System.out.println(mode);
            System.out.println(tag);
            System.out.println(extra);
            System.out.println(more);
            System.out.println("step");
            System.out.println(xs.length);
            System.out.println(flag);
            System.out.println(sum + i);
            System.out.println(sum - i);
            System.out.println(sum * 2);
            System.out.println(sum / 2);
            System.out.println("more");
            System.out.println("again");
            System.out.println("and again");
            System.out.println("filler one");
            System.out.println("filler two");
            System.out.println("filler three");
            System.out.println("filler four");
            System.out.println("filler five");
        }
        int tax = sum * taxRate;
        while (tax > 100) {
            tax = tax / 2;
        }
        System.out.println(tax);
        System.out.println(sum);
        System.out.println("done");
        System.out.println("end");
        return sum + tax;
    }

    public void report(int mode, boolean flag, String tag) {
        if (mode > 2) {
            if (flag) {
                if (tag != null) {
                    if (tag.length() > 3) {
                        System.out.println(tag);
                    }
                }
            }
        }
    }
}
"""

# Short, shallow, two parameters: nothing any strategy fires on.
CLEAN = """package com.acme;

public class Clean {
    private int value;

    public int get() {
        return value;
    }
}
"""


def written(tmp_path: Path, name: str, body: str) -> Path:
    root = tmp_path / "src"
    root.mkdir(exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")
    return root


def smells_in(root: Path) -> list[Smell]:
    return detect_all(analyze_path(str(root)))


def test_a_clean_project_yields_no_patch(tmp_path: Path) -> None:
    root = written(tmp_path, "Clean.java", CLEAN)
    result = plan(root, smells_in(root), javac=None)

    assert result.patches == ()
    assert unified(result.patches) == ""


def test_every_rewrite_in_one_file_travels_as_one_diff(tmp_path: Path) -> None:
    """Three transformations, one file, one rewrite.

    Extract Method and Introduce Parameter Object both act on `process` and
    Guard Clauses on `report`. None of their edits overlap -- the first two touch
    the body and the signature respectively -- so all three are taken.
    """
    root = written(tmp_path, "Ledger.java", LEDGER)
    result = plan(root, smells_in(root), javac=None)

    assert len(result.patches) == 1
    patch = result.patches[0]
    assert patch.relative == "Ledger.java"
    assert {c.refactoring for c in patch.applied} == {
        "ExtractMethod",
        "IntroduceParameterObject",
        "ReplaceNestedConditionalWithGuardClauses",
    }
    assert (result.changes, result.deferred, result.declined) == (3, 0, 0)


def test_the_diff_names_the_file_the_way_git_expects(tmp_path: Path) -> None:
    root = written(tmp_path, "Ledger.java", LEDGER)
    text = unified(plan(root, smells_in(root), javac=None).patches)

    # `git apply` reads the a/ and b/ prefixes; a diff without them needs -p0,
    # which is not the command this feature documents.
    assert "--- a/Ledger.java" in text
    assert "+++ b/Ledger.java" in text
    assert "@@" in text


def test_a_second_claim_on_the_same_bytes_is_deferred(tmp_path: Path) -> None:
    """Two transformations cannot both be computed against the original bytes.

    The registry maps Long Method and Brain Method to the *same* transformation,
    so a method flagged as both yields Extract Method twice over one region. The
    pair is built here rather than grown from Java, because a method complex
    enough for Brain Method is one Extract Method refuses for another reason --
    which would test the refusal instead of the collision.
    """
    root = written(tmp_path, "Ledger.java", LEDGER)
    found = smells_in(root)
    long_method = next(s for s in found if s.smell_type == "LongMethod")
    also_brain = replace(long_method, smell_type="BrainMethod")

    result = plan_file(root / "Ledger.java", root, [long_method, also_brain], javac=None)
    patch, declined = result

    assert patch is not None and not isinstance(patch, type(None))
    # Identical edits, so exactly one of the two can travel and the other waits.
    assert [c.smell_type for c in patch.applied] == ["BrainMethod"]  # sorts before LongMethod
    assert [c.smell_type for c in patch.deferred] == ["LongMethod"]
    assert declined == 0


def test_a_site_with_no_safe_rewrite_is_declined_not_dropped(tmp_path: Path) -> None:
    """Guard Clauses refuses a non-void method; that is counted, not hidden."""
    root = written(tmp_path, "Ledger.java", LEDGER)
    found = smells_in(root)
    deep = next(s for s in found if s.smell_type == "DeepNesting")
    # Point Deep Nesting at `process`, which returns a value and so cannot be
    # rewritten into guard clauses.
    on_process = replace(
        deep,
        method=next(s for s in found if s.smell_type == "LongMethod").method,
        start_line=next(s for s in found if s.smell_type == "LongMethod").start_line,
    )

    patch, declined = plan_file(root / "Ledger.java", root, [on_process], javac=None)

    assert patch is None
    assert declined == 1


def test_a_rewrite_that_fails_verification_never_reaches_the_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A patch is a thing people apply, so an unverified rewrite is dropped."""
    from javasmell.refactor import patch as patch_module
    from javasmell.refactor.verify import Check, Verdict

    monkeypatch.setattr(
        patch_module,
        "check",
        lambda *a, **k: Check(Verdict.NEW_ERRORS, detail="invented failure"),
    )
    root = written(tmp_path, "Ledger.java", LEDGER)
    result = plan(root, smells_in(root), javac=None)

    assert result.patches == ()
    assert [d.verdict for d in result.dropped] == [Verdict.NEW_ERRORS]


def test_a_file_that_is_not_there_is_skipped_rather_than_raising(tmp_path: Path) -> None:
    root = written(tmp_path, "Ledger.java", LEDGER)
    assert plan_file(root / "Gone.java", root, smells_in(root), javac=None) == (None, 0)


def test_the_patch_is_the_same_on_a_second_run(tmp_path: Path) -> None:
    """A patch that varies between runs is one nobody can review."""
    root = written(tmp_path, "Ledger.java", LEDGER)
    first = unified(plan(root, smells_in(root), javac=None).patches)
    second = unified(plan(root, smells_in(root), javac=None).patches)

    assert first == second and first != ""


@pytest.mark.parametrize("trailing", ["\n", ""])
def test_git_applies_the_diff_and_reproduces_the_planned_bytes(
    tmp_path: Path, trailing: str
) -> None:
    """The end of it, checked against git rather than against our own reader.

    Run with and without a final newline: that is the case `difflib` does not
    mark and `git apply` rejects unless the marker is written for it.
    """
    root = written(tmp_path, "Ledger.java", LEDGER.rstrip("\n") + trailing)
    result = plan(root, smells_in(root), javac=None)
    patch = result.patches[0]
    # newline="" on purpose: a plain text write on Windows would translate the
    # line endings, and git rejects such a patch against an LF source file.
    # Same reason cli._write_patch reconfigures the stream it is handed.
    with (tmp_path / "fixes.patch").open("w", encoding="utf-8", newline="") as handle:
        handle.write(unified(result.patches))

    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    applied = subprocess.run(
        ["git", "apply", str(tmp_path / "fixes.patch")],
        cwd=root,
        capture_output=True,
        text=True,
    )

    assert applied.returncode == 0, applied.stderr
    assert (root / "Ledger.java").read_bytes() == patch.after
