"""Tests for Replace Nested Conditional with Guard Clauses.

Per the engine's rules every transformation needs three kinds of test: it applies
correctly, it declines when it cannot prove the rewrite safe, and its output
compiles. The expected text below is written out by hand, including its
whitespace, because the whitespace is part of what the transformation promises.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from javasmell.refactor.base import Refusal
from javasmell.refactor.edits import apply_edits
from javasmell.refactor.guard_clauses import apply
from javasmell.refactor.locate import find_site

JAVAC = shutil.which("javac")


def transform(source: bytes, line: int, name: str = "post", type_name: str = "Ledger"):
    site = find_site("Ledger.java", source, type_name, line, name)
    assert site is not None, "the fixture's line numbers have drifted"
    return apply(site)


# ----------------------------------------------------------------------
# It applies
# ----------------------------------------------------------------------

WRAPPED = b"""class Ledger {
    private int total;

    void post(int amount) {
        if (amount > 0) {
            total += amount;
        }
    }
}
"""


def test_a_wrapped_body_becomes_a_guard():
    outcome = transform(WRAPPED, 4)
    assert outcome.applied

    assert (
        apply_edits(WRAPPED, outcome.edits).decode()
        == """class Ledger {
    private int total;

    void post(int amount) {
        if (!(amount > 0)) {
            return;
        }
        total += amount;
    }
}
"""
    )


def test_several_statements_all_move_up_one_level():
    source = b"""class Ledger {
    private int total;

    void post(int amount) {
        if (amount > 0) {
            total += amount;
            notifyAll();
        }
    }
}
"""
    outcome = transform(source, 4)
    assert outcome.applied

    assert (
        apply_edits(source, outcome.edits).decode()
        == """class Ledger {
    private int total;

    void post(int amount) {
        if (!(amount > 0)) {
            return;
        }
        total += amount;
        notifyAll();
    }
}
"""
    )


def test_the_indent_unit_is_taken_from_the_file():
    """A project that indents with tabs must come back out indented with tabs."""
    source = (
        b"class Ledger {\n"
        b"\tvoid post(int amount) {\n"
        b"\t\tif (amount > 0) {\n"
        b"\t\t\tnotifyAll();\n"
        b"\t\t}\n"
        b"\t}\n"
        b"}\n"
    )
    outcome = transform(source, 2)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    assert "\t\tif (!(amount > 0)) {\n\t\t\treturn;\n\t\t}\n\t\tnotifyAll();" in rewritten
    assert "    " not in rewritten  # no spaces crept in


def test_a_compound_condition_is_wrapped_not_inverted():
    """De Morgan by hand is how an inverted condition becomes a bug."""
    source = b"""class Ledger {
    void post(int amount) {
        if (amount > 0 && amount < 100) {
            notifyAll();
        }
    }
}
"""
    outcome = transform(source, 2)
    assert outcome.applied
    assert "if (!(amount > 0 && amount < 100))" in apply_edits(source, outcome.edits).decode()


# ----------------------------------------------------------------------
# It declines
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "line", "why"),
    [
        (
            b"class Ledger {\n    int post(int a) {\n        if (a > 0) {\n"
            b"            return a;\n        }\n        return 0;\n    }\n}\n",
            2,
            "non-void",
        ),
        (
            b"class Ledger {\n    void post(int a) {\n        if (a > 0) {\n"
            b"            notifyAll();\n        } else {\n            wait();\n        }\n    }\n}\n",
            2,
            "else branch",
        ),
        (
            b"class Ledger {\n    void post(int a) {\n        notifyAll();\n"
            b"        if (a > 0) {\n            wait();\n        }\n    }\n}\n",
            2,
            "not a single conditional",
        ),
        (
            b"class Ledger {\n    void post(int a) {\n        if (a > 0) {\n        }\n    }\n}\n",
            2,
            "empty branch",
        ),
        (
            b"class Ledger {\n    void post(int a) {\n        if (a > 0) notifyAll();\n    }\n}\n",
            2,
            "branch is not a block",
        ),
        (
            b"abstract class Ledger {\n    abstract void post(int a);\n}\n",
            2,
            "no body",
        ),
    ],
    ids=["non-void", "else", "extra-statement", "empty", "no-block", "abstract"],
)
def test_declines_what_it_cannot_prove_safe(source, line, why):
    outcome = transform(source, line)
    assert not outcome.applied, f"should have declined: {why}"
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED
    assert outcome.detail


def test_a_decline_leaves_the_file_untouched():
    source = b"class Ledger {\n    void post(int a) {\n        if (a > 0) notifyAll();\n    }\n}\n"
    outcome = transform(source, 2)
    assert not outcome.applied
    assert outcome.edits == ()


# ----------------------------------------------------------------------
# Its output compiles
# ----------------------------------------------------------------------


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_the_rewritten_file_compiles():
    """The engine's claim is not "it looks right", it is "javac accepts it"."""
    source = b"""public class Ledger {
    private int total;

    void post(int amount) {
        if (amount > 0) {
            total += amount;
            System.out.println(total);
        }
    }
}
"""
    outcome = transform(source, 4)
    assert outcome.applied
    rewritten = apply_edits(source, outcome.edits)

    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / "Ledger.java"
        path.write_bytes(rewritten)
        completed = subprocess.run(
            [JAVAC, "-d", work, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr
