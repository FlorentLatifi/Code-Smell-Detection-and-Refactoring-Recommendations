"""Tests for Extract Method.

Three kinds, as the engine's rules require: it applies correctly, it declines
when the parse tree cannot settle the question, and what it emits compiles.

The expected Java is written out by hand. Extraction is the transformation with
the most ways to be subtly wrong -- a missed parameter, a value that should have
come back, a jump that no longer lands where it did -- so the assertions compare
whole files rather than fragments.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from javasmell.refactor.base import Refusal
from javasmell.refactor.edits import apply_edits
from javasmell.refactor.extract_method import apply
from javasmell.refactor.locate import find_site

JAVAC = shutil.which("javac")


def transform(source: bytes, line: int = 2, name: str = "m", type_name: str = "T"):
    site = find_site("T.java", source, type_name, line, name)
    assert site is not None, "the fixture's line numbers have drifted"
    return apply(site)


def compiles(source: bytes) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / "T.java"
        path.write_bytes(source)
        completed = subprocess.run(
            [str(JAVAC), "-d", work, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    return completed.returncode == 0, completed.stderr


# ----------------------------------------------------------------------
# It applies
# ----------------------------------------------------------------------

ACCUMULATES = b"""public class T {
    void m(int[] xs) {
        int total = 0;
        for (int i = 0; i < xs.length; i++) {
            int amount = xs[i];
            if (amount > 0) {
                total += amount;
            }
        }
        System.out.println(total);
    }
}
"""


def test_a_value_used_after_the_block_comes_back_as_the_return():
    """`total` is read inside (via +=) and after, so it is both argument and result.

    The parameters come out alphabetical rather than in the order they appear:
    the order has to be fixed by something, and sorting is the only rule that
    cannot depend on how the tree was walked.
    """
    outcome = transform(ACCUMULATES)
    assert outcome.applied

    assert (
        apply_edits(ACCUMULATES, outcome.edits).decode()
        == """public class T {
    void m(int[] xs) {
        int total = 0;
        total = extracted(total, xs);
        System.out.println(total);
    }

    private int extracted(int total, int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            int amount = xs[i];
            if (amount > 0) {
                total += amount;
            }
        }
        return total;
    }
}
"""
    )


def test_a_block_that_produces_nothing_becomes_a_void_method():
    source = b"""public class T {
    void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                System.out.println(xs[i]);
            }
        }
        System.out.println("done");
    }
}
"""
    outcome = transform(source)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    assert "        extracted(xs);\n" in rewritten
    assert "    private void extracted(int[] xs) {" in rewritten
    assert "return" not in rewritten.split("private void extracted")[1]


def test_a_field_needs_no_parameter():
    """The new method sits in the same class, so `this.total` resolves unchanged."""
    source = b"""public class T {
    private int total;

    void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                this.total += xs[i];
            }
        }
        System.out.println(total);
    }
}
"""
    outcome = transform(source, line=4)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    assert "private void extracted(int[] xs) {" in rewritten
    assert "total" not in rewritten.split("private void extracted(")[1].split(")")[0]


def test_a_static_method_yields_a_static_method():
    """An instance method cannot be called from a static one."""
    source = b"""public class T {
    static void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                System.out.println(xs[i]);
            }
        }
        System.out.println("done");
    }
}
"""
    outcome = transform(source)
    assert outcome.applied
    assert "private static void extracted" in apply_edits(source, outcome.edits).decode()


def test_the_name_avoids_one_that_is_taken():
    source = b"""public class T {
    void extracted() {
    }

    void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                System.out.println(xs[i]);
            }
        }
        System.out.println("done");
    }
}
"""
    outcome = transform(source, line=5)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    assert "private void extracted2(int[] xs)" in rewritten
    assert "        extracted2(xs);" in rewritten


def test_the_largest_block_is_the_one_chosen():
    """Two candidates; the choice is by line span, so it must be the second."""
    source = b"""public class T {
    void m(int[] xs) {
        while (xs.length > 0) {
            System.out.println(1);
            System.out.println(2);
            break;
        }
        for (int i = 0; i < xs.length; i++) {
            System.out.println(3);
            System.out.println(4);
            System.out.println(5);
            System.out.println(6);
        }
    }
}
"""
    outcome = transform(source)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    assert "while (xs.length > 0) {" in rewritten.split("void m(")[1].split("private")[0]
    assert "System.out.println(6);" in rewritten.split("private void extracted")[1]


# ----------------------------------------------------------------------
# It declines
# ----------------------------------------------------------------------


def test_a_return_in_the_block_is_refused():
    """It would return from the extracted method, which is a different program."""
    source = b"""public class T {
    void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] < 0) {
                return;
            }
        }
        System.out.println("ok");
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.CONTROL_FLOW_ESCAPES
    assert "return" in outcome.detail


def test_two_values_flowing_out_are_refused():
    """A single return cannot carry both."""
    source = b"""public class T {
    void m(int[] xs) {
        int a = 0;
        int b = 0;
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                a += xs[i];
                b += 1;
            }
        }
        System.out.println(a + b);
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.MULTIPLE_OUTPUTS
    assert "a, b" in outcome.detail


def test_a_method_with_no_block_worth_lifting_is_refused():
    source = b"""public class T {
    void m(int[] xs) {
        System.out.println(1);
        System.out.println(2);
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_a_short_block_is_left_alone():
    """Three lines is not a step; extracting it would hide nothing."""
    source = b"""public class T {
    void m(int[] xs) {
        if (xs.length > 0) {
            System.out.println(1);
        }
        System.out.println(2);
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert "5 lines" in outcome.detail


def test_an_abstract_method_is_refused():
    source = b"""public abstract class T {
    abstract void m(int[] xs);
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_a_decline_leaves_the_file_untouched():
    source = b"""public class T {
    void m(int[] xs) {
        System.out.println(1);
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.edits == ()


# ----------------------------------------------------------------------
# Its output compiles
# ----------------------------------------------------------------------


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
@pytest.mark.parametrize(
    ("source", "line"),
    [
        (ACCUMULATES, 2),
        (
            b"public class T {\n    private int total;\n\n    void m(int[] xs) {\n"
            b"        for (int i = 0; i < xs.length; i++) {\n"
            b"            if (xs[i] > 0) {\n                this.total += xs[i];\n            }\n"
            b"        }\n        System.out.println(total);\n    }\n}\n",
            4,
        ),
        (
            b"public class T {\n    static void m(int[] xs) {\n"
            b"        for (int i = 0; i < xs.length; i++) {\n"
            b"            if (xs[i] > 0) {\n                System.out.println(xs[i]);\n            }\n"
            b'        }\n        System.out.println("done");\n    }\n}\n',
            2,
        ),
    ],
    ids=["returns-a-value", "touches-a-field", "static"],
)
def test_what_it_emits_compiles(source, line):
    """The engine's claim is not that the output looks right, but that javac takes it."""
    before, _ = compiles(source)
    assert before, "the fixture itself must compile"

    outcome = transform(source, line=line)
    assert outcome.applied

    ok, errors = compiles(apply_edits(source, outcome.edits))
    assert ok, errors


def test_a_name_from_an_earlier_loop_is_out_of_scope():
    """Two sibling loops may each declare `i`; the first one's has left scope.

    Treating it as visible is not a harmless over-approximation. The block
    declares its own `i`, so passing one in produced `variable i is already
    defined in method extracted(...)` and the file stopped compiling. Found by
    running the engine over the corpus, not by reading the code.
    """
    source = b"""public class T {
    void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            System.out.println(xs[i]);
        }
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                System.out.println(xs[i] * 2);
            }
        }
    }
}
"""
    outcome = transform(source)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    signature = rewritten.split("private void extracted(")[1].split(")")[0]
    assert "int i" not in signature, f"`i` must not be a parameter: {signature}"
    assert signature == "int[] xs"


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_the_shadowed_loop_variable_case_compiles():
    source = b"""public class T {
    void m(int[] xs) {
        for (int i = 0; i < xs.length; i++) {
            System.out.println(xs[i]);
        }
        for (int i = 0; i < xs.length; i++) {
            if (xs[i] > 0) {
                System.out.println(xs[i] * 2);
            }
        }
    }
}
"""
    outcome = transform(source)
    assert outcome.applied

    ok, errors = compiles(apply_edits(source, outcome.edits))
    assert ok, errors


def test_a_value_not_yet_assigned_cannot_be_passed_in():
    """Java forbids reading a local before it is certainly assigned.

    `ch` is declared without a value and read inside the block, so passing it as
    a parameter gives `variable ch might not have been initialized`. The engine
    emitted exactly that over the corpus before this check existed.
    """
    source = b"""public class T {
    void m(int n) {
        char ch;
        for (int i = 0; i < n; i++) {
            if (ch == 'x') {
                System.out.println(i);
            }
        }
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.NOT_DEFINITELY_ASSIGNED
    assert "ch" in outcome.detail


def test_a_declaration_with_a_value_is_assigned():
    source = b"""public class T {
    void m(int n) {
        char ch = 'a';
        for (int i = 0; i < n; i++) {
            if (ch == 'x') {
                System.out.println(i);
            }
        }
    }
}
"""
    outcome = transform(source)
    assert outcome.applied
    assert "char ch" in apply_edits(source, outcome.edits).decode()


def test_a_plain_assignment_before_the_block_counts():
    source = b"""public class T {
    void m(int n) {
        char ch;
        ch = 'a';
        for (int i = 0; i < n; i++) {
            if (ch == 'x') {
                System.out.println(i);
            }
        }
    }
}
"""
    assert transform(source).applied


def test_an_assignment_inside_a_conditional_does_not_count():
    """It runs on some paths and not others, which is what Java refuses to assume."""
    source = b"""public class T {
    void m(int n) {
        char ch;
        if (n > 0) {
            ch = 'a';
        }
        for (int i = 0; i < n; i++) {
            if (ch == 'x') {
                System.out.println(i);
            }
        }
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.NOT_DEFINITELY_ASSIGNED


def test_a_checked_exception_keeps_its_throws_clause():
    """The block still throws after the move, so the new method must say so.

    Without this the engine emitted `unreported exception IOException`, found by
    running over the corpus.
    """
    source = b"""import java.io.IOException;

public class T {
    void m(int n) throws IOException {
        for (int i = 0; i < n; i++) {
            if (i > 0) {
                read(i);
            }
        }
        System.out.println(n);
    }

    void read(int i) throws IOException {
    }
}
"""
    outcome = transform(source, line=4)
    assert outcome.applied

    rewritten = apply_edits(source, outcome.edits).decode()
    assert "private void extracted(int n) throws IOException {" in rewritten


@pytest.mark.skipif(JAVAC is None, reason="javac not on PATH")
def test_the_checked_exception_case_compiles():
    source = b"""import java.io.IOException;

public class T {
    void m(int n) throws IOException {
        for (int i = 0; i < n; i++) {
            if (i > 0) {
                read(i);
            }
        }
        System.out.println(n);
    }

    void read(int i) throws IOException {
    }
}
"""
    outcome = transform(source, line=4)
    assert outcome.applied

    ok, errors = compiles(apply_edits(source, outcome.edits))
    assert ok, errors


def test_a_generic_method_is_refused():
    """Carrying type variables over means reasoning about bounds and inference."""
    source = b"""public class T {
    <E extends Number> void m(java.util.List<E> xs) {
        for (E item : xs) {
            if (item != null) {
                System.out.println(item);
            }
        }
        System.out.println(xs);
    }
}
"""
    outcome = transform(source)
    assert not outcome.applied
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED
    assert "type parameters" in outcome.detail
