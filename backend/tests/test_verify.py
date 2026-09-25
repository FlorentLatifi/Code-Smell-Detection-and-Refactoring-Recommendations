"""Tests for the three-level check on a rewritten file."""

from __future__ import annotations

import os
import shutil
import sys
import time

import pytest

from javasmell.refactor.verify import (
    Verdict,
    check,
    error_messages,
    errors_in,
    javac_command,
    parses_cleanly,
    run_javac,
)

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


# --- Reading javac's output (VD-136) --------------------------------------------
#
# All three samples are real `javac 21` output, shortened only in the number of
# repeated blocks. The expectations are derived by hand from the rule: count the
# lines carrying the `: error:` marker, and treat a failure with none of them as
# something javac could not attribute to the source.

SOURCE_ERRORS = """T.java:2: error: cannot find symbol
    Missing m;
    ^
  symbol:   class Missing
  location: class T
T.java:3: error: cannot find symbol
    Absent other;
    ^
  symbol:   class Absent
  location: class T
2 errors
"""

WRITE_FAILED = """error: error while writing T: T.class (Access is denied)
1 error
"""

NO_SUCH_FILE = """javac: file not found: T.java
Usage: javac <options> <source files>
use --help for a list of possible options
"""


def test_a_clean_run_reports_no_errors():
    assert errors_in(0, "") == set()


def test_both_marked_lines_collapse_to_the_one_kind_they_share():
    """Two marked lines, the same message, and the pointer lines do not count."""
    assert errors_in(1, SOURCE_ERRORS) == {"cannot find symbol"}


def test_a_failure_javac_could_not_attribute_to_the_source_is_unknown():
    """Not a property of the code, so not readable as a clean compile.

    This output, unrecognised, is what gave 19 rewrites the `compiles` verdict
    in the 23 September 2026 corpus run, on files that do not compile at all.
    """
    assert errors_in(1, WRITE_FAILED) is None
    assert errors_in(2, NO_SUCH_FILE) is None


def test_an_empty_failure_is_unknown_too():
    """A VM that will not start writes no line this can read."""
    assert errors_in(1, "") is None


def test_marked_errors_are_read_even_beside_a_failure_of_javacs_own():
    """javac named something about the source, and its own failure does not hide it."""
    assert errors_in(1, SOURCE_ERRORS + WRITE_FAILED) == {"cannot find symbol"}


# --- A bounded javac run really is bounded (VD-137) ------------------------------
#
# The stated limit was 180 seconds and one rewrite waited 50 minutes, because the
# compiler that kept running was a child of the process the timeout killed, and it
# still held the pipes the caller was reading. These use `sys.executable` as a
# stand-in for javac: what matters is the plumbing, not the program.


def test_a_command_that_outlives_its_limit_reports_no_result(tmp_path):
    """A process killed by the timeout gives None, and gives it promptly."""
    started = time.monotonic()
    outcome = run_javac(sys.executable, ["-c", "import time; time.sleep(30)"], tmp_path, 2)
    waited = time.monotonic() - started

    assert outcome is None
    assert waited < 10, f"the call waited {waited:.0f}s for a 2s limit"


INNER_SCRIPT = """import sys, time
for _ in range(30):
    print('busy')
    sys.stdout.flush()
    time.sleep(1)
"""

OUTER_SCRIPT = """import subprocess, sys
subprocess.Popen([sys.executable, sys.argv[1]])
import time; time.sleep(30)
"""


def test_a_grandchild_that_outlives_the_limit_cannot_hold_the_call_open(tmp_path):
    """The case that was actually hit: the killed child leaves a child of its own.

    The inner process writes to the inherited output for half a minute. With a
    pipe the caller blocks until that write end closes, however long that takes;
    with a file there is nothing to wait for.
    """
    inner = tmp_path / "inner.py"
    inner.write_text(INNER_SCRIPT, encoding="utf-8")
    outer = tmp_path / "outer.py"
    outer.write_text(OUTER_SCRIPT, encoding="utf-8")

    started = time.monotonic()
    outcome = run_javac(sys.executable, [str(outer), str(inner)], tmp_path, 3)
    waited = time.monotonic() - started

    assert outcome is None
    assert waited < 15, f"a surviving grandchild held the call for {waited:.0f}s"


def test_a_command_inside_its_limit_returns_its_code_and_output(tmp_path):
    outcome = run_javac(sys.executable, ["-c", "print('hello'); raise SystemExit(3)"], tmp_path, 30)

    assert outcome is not None
    returncode, output = outcome
    assert returncode == 3
    assert "hello" in output


def test_the_jdk_compiler_is_preferred_over_a_launcher_on_the_path(tmp_path, monkeypatch):
    """JAVA_HOME wins, because a PATH javac may be a shim that re-launches it."""
    binary = "javac.exe" if os.name == "nt" else "javac"
    home = tmp_path / "jdk"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / binary).write_text("", encoding="utf-8")

    monkeypatch.setenv("JAVA_HOME", str(home))
    assert javac_command() == str(home / "bin" / binary)


def test_a_java_home_without_a_compiler_falls_back_to_the_path(tmp_path, monkeypatch):
    """A JRE, or a stale variable, must not hide the compiler that is installed."""
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "missing"))

    assert javac_command() == shutil.which("javac")
