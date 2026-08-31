"""Tests for the question the engine never asked: is the smell gone?

The expectations are derived from the metric definitions, not from a run.
``_max_nesting`` counts one for each nesting construct starting from the method
body, and Deep Nesting fires above three. Guard Clauses removes exactly the
outermost condition, so a method that measures four is cured and one that
measures five is not -- and both rewrites are equally correct.
"""

from __future__ import annotations

from javasmell.refactor import guard_clauses, introduce_parameter_object
from javasmell.refactor.edits import apply_edits
from javasmell.refactor.locate import find_site
from javasmell.refactor.resolution import Resolution, compare, resolves

# Body is one `if`, with three more inside it: MAXNESTING = 4, over the bound of
# three. Removing the outer condition leaves three, which does not fire.
NESTED_FOUR = b"""class T {
    void m(int a) {
        if (a > 0) {
            if (a > 1) {
                if (a > 2) {
                    if (a > 3) {
                        System.out.println(a);
                    }
                }
            }
        }
    }
}
"""

# The same shape one level deeper: MAXNESTING = 5, and four is still over three.
NESTED_FIVE = b"""class T {
    void m(int a) {
        if (a > 0) {
            if (a > 1) {
                if (a > 2) {
                    if (a > 3) {
                        if (a > 4) {
                            System.out.println(a);
                        }
                    }
                }
            }
        }
    }
}
"""

SIX_PARAMETERS = b"""class T {
    private int total(int a, int b, int c, int d, int e, int f) {
        return a + b + c + d + e + f;
    }

    void run() {
        report(total(1, 2, 3, 4, 5, 6));
    }

    void report(int value) {}
}
"""


def rewrite(source: bytes, module, line: int = 2, name: str = "m") -> bytes:
    site = find_site("T.java", source, "T", line, name)
    assert site is not None, "the fixture's line numbers have drifted"
    outcome = module.apply(site)
    assert outcome.applied, outcome.detail
    return apply_edits(source, outcome.edits)


def test_a_cured_method_is_reported_as_resolved() -> None:
    """Four levels become three, and the detector fires above three."""
    rewritten = rewrite(NESTED_FOUR, guard_clauses)
    assert resolves(rewritten, "T", "m", "DeepNesting") is Resolution.RESOLVED


def test_a_correct_rewrite_can_leave_the_smell_in_place() -> None:
    """The finding this module exists for.

    Guard Clauses removes one level, not all of them. Five becomes four, which is
    still over the bound: the rewrite is correct, it compiles, and the method is
    still Deep Nesting.
    """
    rewritten = rewrite(NESTED_FIVE, guard_clauses)
    assert resolves(rewritten, "T", "m", "DeepNesting") is Resolution.PERSISTS


def test_a_parameter_object_always_resolves_its_smell() -> None:
    """Six parameters become one, so the bound of five cannot be exceeded."""
    rewritten = rewrite(SIX_PARAMETERS, introduce_parameter_object, name="total")
    assert resolves(rewritten, "T", "total", "LongParameterList") is Resolution.RESOLVED


def test_an_overloaded_name_is_not_guessed_at() -> None:
    """Two methods share the name, so no single entity answers the question."""
    overloaded = b"""class T {
    void m(int a) {
        if (a > 0) {
            System.out.println(a);
        }
    }

    void m(String s) {
        System.out.println(s);
    }
}
"""
    assert resolves(overloaded, "T", "m", "DeepNesting") is Resolution.UNKNOWN


def test_a_class_that_is_no_longer_there_is_not_guessed_at() -> None:
    assert resolves(NESTED_FOUR, "Missing", "m", "DeepNesting") is Resolution.UNKNOWN


def test_a_class_level_smell_is_asked_without_a_method() -> None:
    """A Data Class keeps its smell through any rewrite of one of its methods."""
    data_class = b"""class T {
    public int a;
    public int b;
    public int c;
    public int d;
    public int e;
    public int f;

    public int getA() { return a; }
}
"""
    assert resolves(data_class, "T", None, "DataClass") is Resolution.PERSISTS


# Extract Method passes every value the block read as a parameter. This block
# reads six locals, so the method it produces takes six parameters -- one over
# the bound of five, and therefore a Long Parameter List that did not exist
# before the rewrite.
SIX_INPUTS = b"""class T {
    int run(int a, int b, int c, int d, int e, int f) {
        int total = 0;
        for (int i = 0; i < 10; i++) {
            total += a;
            total += b;
            total += c;
            total += d;
            total += e;
            total += f;
        }
        return total;
    }
}
"""


def test_a_rewrite_can_introduce_a_smell_that_was_not_there() -> None:
    """The mirror of resolving one, and the reason the class is measured whole.

    Nothing in the original file is a Long Parameter List; `run` takes six
    parameters but is not private and is not what was rewritten. The extracted
    method is new code, and it is measured for the first time here.
    """
    from javasmell.refactor import extract_method

    site = find_site("T.java", SIX_INPUTS, "T", 2, "run")
    assert site is not None
    outcome = extract_method.apply(site)
    assert outcome.applied, outcome.detail
    rewritten = apply_edits(SIX_INPUTS, outcome.edits)

    change = compare(SIX_INPUTS, rewritten, "T", "run", "LongMethod")
    assert "LongParameterList" in change.introduced


def test_the_measurement_that_moved_is_reported_with_the_smell() -> None:
    """Four levels of nesting become three, and the number says so."""
    rewritten = rewrite(NESTED_FOUR, guard_clauses)
    change = compare(NESTED_FOUR, rewritten, "T", "m", "DeepNesting")

    assert change.metric == "MAXNESTING"
    assert (change.before, change.after) == (4.0, 3.0)
    assert change.resolution is Resolution.RESOLVED


def test_a_surviving_smell_still_reports_how_far_it_moved() -> None:
    """Five levels become four: still over the bound, and measurably better."""
    rewritten = rewrite(NESTED_FIVE, guard_clauses)
    change = compare(NESTED_FIVE, rewritten, "T", "m", "DeepNesting")

    assert change.resolution is Resolution.PERSISTS
    assert (change.before, change.after) == (5.0, 4.0)
