"""Tests for the three-level check on a rewritten file."""

from __future__ import annotations

import shutil

import pytest

from javasmell.refactor.verify import Verdict, check, error_messages, parses_cleanly

JAVAC = shutil.which("javac")

GOOD = b"public class T {\n    void m() {\n        System.out.println(1);\n    }\n}\n"
BROKEN = b"public class T {\n    void m() {\n        System.out.println(1);\n"  # no braces
NEEDS_IMPORT = b"public class T {\n    Missing m;\n    Absent other;\n}\n"


def test_valid_java_parses():
    assert parses_cleanly(GOOD)


def test_a_lost_brace_is_caught():
    """The check that costs nothing and catches a mangled rewrite."""
    assert not parses_cleanly(BROKEN)


def test_a_broken_rewrite_is_rejected_before_javac_is_asked():
    result = check(None, GOOD, BROKEN, "T.java")
    assert result.verdict is Verdict.BROKEN_SYNTAX
    assert not result.verdict.passed


def test_without_javac_the_check_stops_at_parsing():
    result = check(None, GOOD, GOOD, "T.java")
    assert result.verdict is Verdict.PARSES
    assert result.verdict.passed


def test_only_the_passing_verdicts_report_as_passed():
    assert Verdict.COMPILES.passed
    assert Verdict.NO_NEW_ERRORS.passed
    assert Verdict.PARSES.passed
    assert not Verdict.BROKEN_SYNTAX.passed
    assert not Verdict.NEW_ERRORS.passed
    assert not Verdict.NOT_CHECKED.passed


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_a_file_that_compiles_before_and_after():
    result = check(JAVAC, GOOD, GOOD, "T.java")
    assert result.verdict is Verdict.COMPILES
    assert result.errors_before == 0 and result.errors_after == 0


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_breaking_a_file_that_used_to_compile_is_caught():
    broke = b"public class T {\n    void m() {\n        undefinedCall();\n    }\n}\n"
    result = check(JAVAC, GOOD, broke, "T.java")
    assert result.verdict is Verdict.NEW_ERRORS
    assert "cannot find symbol" in result.detail


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_a_file_that_never_compiled_is_judged_on_whether_it_got_worse():
    """92% of the corpus lands here: it fails on its neighbours, not on itself."""
    assert error_messages(JAVAC, NEEDS_IMPORT, "T.java")

    result = check(JAVAC, NEEDS_IMPORT, NEEDS_IMPORT, "T.java")
    assert result.verdict is Verdict.NO_NEW_ERRORS
    assert result.verdict.passed


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_a_new_kind_of_error_in_an_already_failing_file_is_caught():
    worse = NEEDS_IMPORT.replace(b"}\n", b'    int n = "text";\n}\n')
    result = check(JAVAC, NEEDS_IMPORT, worse, "T.java")

    assert result.verdict is Verdict.NEW_ERRORS
    assert "incompatible types" in result.detail


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_the_known_blind_spot_of_comparing_kinds():
    """Documented rather than fixed: an error reading like one already there passes.

    Counting errors would catch this, and counting was tried first -- but it
    flagged correct rewrites, because lifting a block whose parameter is an
    imported type adds one more `cannot find symbol` purely from compiling
    without a classpath. Between a check that misses some breakage and one that
    denies correct work, the first is the honest trade, and the compile tier
    exists to cover what it misses.
    """
    worse = NEEDS_IMPORT.replace(b"}\n", b"    AlsoAbsent another;\n}\n")
    result = check(JAVAC, NEEDS_IMPORT, worse, "T.java")

    assert result.verdict is Verdict.NO_NEW_ERRORS  # not caught, and known
    assert result.errors_after == result.errors_before
