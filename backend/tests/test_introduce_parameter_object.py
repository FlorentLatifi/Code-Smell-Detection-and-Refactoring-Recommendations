"""Tests for Introduce Parameter Object.

Three kinds, as the engine's rules require: it applies correctly, it declines
when the file cannot settle the question, and what it emits compiles.

The expected Java is written out by hand. This transformation changes a
signature, so the assertions compare whole files: a call site left behind is the
failure that matters, and a fragment comparison would not show it.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from javasmell.refactor.base import Refusal
from javasmell.refactor.edits import apply_edits
from javasmell.refactor.introduce_parameter_object import apply
from javasmell.refactor.locate import find_site

JAVAC = shutil.which("javac")


def transform(source: bytes, line: int = 2, name: str = "total", type_name: str = "T"):
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


def test_a_private_method_gets_an_object_and_its_call_sites_follow() -> None:
    """The whole rewrite, worked out by hand.

    Four parameters become four final fields in declaration order, the body gets
    them back as locals of the same name and type, and the one call site wraps its
    arguments in the constructor with the order it already had.
    """
    source = b"""class T {
    private int total(Order order, int qty, double rate, boolean taxed) {
        return order.base(qty) + (taxed ? 1 : 0);
    }

    void run(Order o) {
        report(total(o, 3, 1.5, true));
    }
}
"""
    outcome = transform(source)
    assert outcome.applied, outcome.detail

    assert (
        apply_edits(source, outcome.edits)
        == b"""class T {
    private static final class TotalParams {
        final Order order;
        final int qty;
        final double rate;
        final boolean taxed;

        TotalParams(Order order, int qty, double rate, boolean taxed) {
            this.order = order;
            this.qty = qty;
            this.rate = rate;
            this.taxed = taxed;
        }
    }

    private int total(TotalParams params) {
        Order order = params.order;
        int qty = params.qty;
        double rate = params.rate;
        boolean taxed = params.taxed;
        return order.base(qty) + (taxed ? 1 : 0);
    }

    void run(Order o) {
        report(total(new TotalParams(o, 3, 1.5, true)));
    }
}
"""
    )


def test_a_call_qualified_with_this_is_rewritten_too() -> None:
    """``this.name(...)`` is provably the same method, so it is not a refusal."""
    source = b"""class T {
    private int total(int a, int b) {
        return a + b;
    }

    void run() {
        report(this.total(1, 2));
    }
}
"""
    outcome = transform(source)
    assert outcome.applied, outcome.detail
    assert b"this.total(new TotalParams(1, 2))" in apply_edits(source, outcome.edits)


def test_a_recursive_call_is_rewritten_like_any_other() -> None:
    source = b"""class T {
    private int total(int a, int b) {
        return a == 0 ? b : total(a - 1, b);
    }
}
"""
    outcome = transform(source)
    assert outcome.applied, outcome.detail
    assert b"total(new TotalParams(a - 1, b))" in apply_edits(source, outcome.edits)


def test_the_class_name_avoids_one_that_is_taken() -> None:
    source = b"""class T {
    private int total(int a, int b) {
        return a + b;
    }

    static class TotalParams {}
}
"""
    outcome = transform(source)
    assert outcome.applied, outcome.detail
    rewritten = apply_edits(source, outcome.edits)
    assert b"class TotalParams2 {" in rewritten
    assert b"private int total(TotalParams2 params)" in rewritten


def test_a_parameter_named_params_pushes_the_holder_aside() -> None:
    """The holder must not collide with a value it carries."""
    source = b"""class T {
    private int total(int params, int b) {
        return params + b;
    }
}
"""
    outcome = transform(source)
    assert outcome.applied, outcome.detail
    rewritten = apply_edits(source, outcome.edits)
    assert b"private int total(TotalParams params2)" in rewritten
    assert b"int params = params2.params;" in rewritten


def test_a_method_that_is_not_private_is_refused() -> None:
    """The whole basis of the transformation: only private scopes the calls here."""
    source = b"""class T {
    int total(int a, int b) {
        return a + b;
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_an_overloaded_name_is_refused() -> None:
    """Two methods share the name, so a bare call cannot be attributed."""
    source = b"""class T {
    private int total(int a, int b) {
        return a + b;
    }

    private int total(int a) {
        return a;
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.AMBIGUOUS_OVERLOAD


def test_a_call_through_another_instance_is_refused() -> None:
    """Java lets one instance call another's private method; we cannot prove it is ours."""
    source = b"""class T {
    private int total(int a, int b) {
        return a + b;
    }

    void run(T other) {
        report(other.total(1, 2));
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.UNRESOLVED_NAME


def test_a_method_reference_is_refused() -> None:
    """A reference carries the signature elsewhere, where this rewrite cannot follow."""
    source = b"""class T {
    private int total(int a, int b) {
        return a + b;
    }

    void run() {
        java.util.function.IntBinaryOperator f = this::total;
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.UNRESOLVED_NAME


def test_varargs_are_refused() -> None:
    source = b"""class T {
    private int total(int a, int... rest) {
        return a + rest.length;
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_an_annotated_parameter_is_refused() -> None:
    """An annotation may mean something on a parameter that it does not on a field."""
    source = b"""class T {
    private int total(@Deprecated int a, int b) {
        return a + b;
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_a_final_parameter_is_accepted_and_becomes_a_plain_local() -> None:
    """`final` on a parameter is invisible to the caller, so it is not a refusal."""
    source = b"""class T {
    private int total(final int a, final int b) {
        return a + b;
    }
}
"""
    outcome = transform(source)
    assert outcome.applied, outcome.detail
    assert b"int a = params.a;" in apply_edits(source, outcome.edits)


def test_a_generic_method_is_refused() -> None:
    source = b"""class T {
    private <V> int total(V a, int b) {
        return b;
    }
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_a_method_in_a_nested_class_is_refused() -> None:
    """A static nested class inside an inner class is not legal on older Java."""
    source = b"""class T {
    class Inner {
        private int total(int a, int b) {
            return a + b;
        }
    }
}
"""
    outcome = transform(source, line=3, type_name="Inner")
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_a_method_without_a_body_is_refused() -> None:
    source = b"""abstract class T {
    private abstract int total(int a, int b);
}
"""
    outcome = transform(source)
    assert outcome.refusal is Refusal.SHAPE_NOT_MATCHED


def test_a_decline_leaves_the_file_untouched() -> None:
    source = b"""class T {
    int total(int a, int b) {
        return a + b;
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
def test_what_it_emits_compiles() -> None:
    """The engine's claim is not that the output looks right, but that javac takes it."""
    source = b"""class T {
    private int total(Order order, int qty, double rate, boolean taxed) {
        return order.base(qty) + (int) rate + (taxed ? 1 : 0);
    }

    void run(Order o) {
        report(total(o, 3, 1.5, true));
        report(this.total(o, 4, 2.5, false));
    }

    void report(int value) {}
}

class Order {
    int base(int q) {
        return q;
    }
}
"""
    before, message = compiles(source)
    assert before, f"the fixture itself must compile: {message}"

    outcome = transform(source)
    assert outcome.applied, outcome.detail
    after, message = compiles(apply_edits(source, outcome.edits))
    assert after, message
