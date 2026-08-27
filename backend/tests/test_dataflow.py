"""Tests for the data-flow analysis Extract Method depends on.

Every expected set is written out by hand from the snippet above it. The cases
are chosen for the distinctions that decide whether an extraction is safe: a
compound assignment reads before it writes, a field is not a local, and a jump
only escapes when the thing it jumps out of is left behind.
"""

from __future__ import annotations

import pytest

from javasmell.parsing.java_parser import JavaParser
from javasmell.refactor.dataflow import (
    declarations_in,
    escaping_control_flow,
    names_read,
    names_written,
    walk,
)


def method_of(source: bytes):
    tree = JavaParser().parse_tree(source)
    methods = [n for n in walk(tree.root_node) if n.type == "method_declaration"]
    assert methods, "the snippet has no method"
    return methods[0]


def body_statements(source: bytes):
    body = method_of(source).child_by_field_name("body")
    assert body is not None
    return list(body.named_children)


def wrap(inner: str) -> bytes:
    return ("class T {\n    void m(int p, String q) {\n" + inner + "\n    }\n}").encode()


# ----------------------------------------------------------------------
# Declarations
# ----------------------------------------------------------------------


def test_parameters_and_locals_are_collected_with_their_types():
    source = wrap("        int a = 1;\n        String s = q;\n        long[] xs = null;")
    found = declarations_in(method_of(source), source)

    assert found.types == {
        "p": "int",
        "q": "String",
        "a": "int",
        "s": "String",
        "xs": "long[]",
    }


def test_a_for_loop_variable_is_a_local():
    source = wrap("        for (int i = 0; i < 3; i++) { }")
    assert declarations_in(method_of(source), source).types["i"] == "int"


def test_a_catch_parameter_is_a_local():
    source = wrap("        try { } catch (IllegalStateException e) { }")
    assert declarations_in(method_of(source), source).types["e"] == "IllegalStateException"


# ----------------------------------------------------------------------
# Reads
# ----------------------------------------------------------------------


def test_a_plain_assignment_does_not_read_its_target():
    source = wrap("        int a = 1;\n        a = p;")
    known = declarations_in(method_of(source), source)
    body = method_of(source).child_by_field_name("body")

    #  `a = p` writes a and reads p. `int a = 1` reads nothing.
    assert names_read(body, source, known) == {"p"}


def test_a_compound_assignment_reads_its_target():
    """`a += p` is `a = a + p`, so a crosses the boundary as an input."""
    source = wrap("        int a = 1;\n        a += p;")
    known = declarations_in(method_of(source), source)
    body = method_of(source).child_by_field_name("body")

    assert names_read(body, source, known) == {"a", "p"}


def test_a_field_is_not_a_local_read():
    """`this.total` needs no parameter: the extracted method sits in the class."""
    source = wrap("        this.total = p;")
    known = declarations_in(method_of(source), source)
    body = method_of(source).child_by_field_name("body")

    assert names_read(body, source, known) == {"p"}


def test_the_member_half_of_a_qualified_access_is_not_a_read():
    source = wrap("        String s = q;\n        int n = s.length();")
    known = declarations_in(method_of(source), source)
    body = method_of(source).child_by_field_name("body")

    #  `s.length()` reads s; `length` is a method name, not a variable.
    assert names_read(body, source, known) == {"q", "s"}


# ----------------------------------------------------------------------
# Writes
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("statement", "written"),
    [
        ("        int a = 1;\n        a = p;", {"a"}),
        ("        int a = 1;\n        a += p;", {"a"}),
        ("        int a = 1;\n        a++;", {"a"}),
        ("        int a = 1;\n        ++a;", {"a"}),
        ("        int a = p;", {"a"}),
        ("        int a;", set()),  # declared, never assigned
    ],
    ids=["assign", "compound", "post-inc", "pre-inc", "init", "no-init"],
)
def test_every_form_of_assignment_counts_as_a_write(statement, written):
    source = wrap(statement)
    known = declarations_in(method_of(source), source)
    body = method_of(source).child_by_field_name("body")

    assert names_written(body, source, known) == written


def test_writing_a_field_is_not_writing_a_local():
    source = wrap("        this.total = p;")
    known = declarations_in(method_of(source), source)
    body = method_of(source).child_by_field_name("body")

    assert names_written(body, source, known) == set()


# ----------------------------------------------------------------------
# Escaping control flow
# ----------------------------------------------------------------------


def test_a_return_always_escapes():
    """After extraction it would return from the new method, not the old one."""
    source = wrap("        if (p > 0) {\n            return;\n        }")
    assert escaping_control_flow(body_statements(source)) == "return"


def test_a_break_inside_an_extracted_loop_travels_with_it():
    """The ordinary case: refusing it would refuse most real loops."""
    source = wrap("        for (int i = 0; i < 3; i++) {\n            break;\n        }")
    assert escaping_control_flow(body_statements(source)) is None


def test_a_break_whose_loop_stays_behind_escapes():
    """Only the if is extracted; the break belongs to a loop left outside it."""
    source = wrap(
        "        for (int i = 0; i < 3; i++) {\n"
        "            if (i == p) {\n                break;\n            }\n"
        "        }"
    )
    loop = body_statements(source)[0]
    inner_if = next(n for n in walk(loop) if n.type == "if_statement")

    assert escaping_control_flow([inner_if]) == "break"
    assert escaping_control_flow([loop]) is None


def test_a_break_belonging_to_a_switch_is_captured_by_it():
    source = wrap(
        "        switch (p) {\n            case 1: break;\n            default: break;\n        }"
    )
    assert escaping_control_flow(body_statements(source)) is None


def test_a_continue_whose_loop_stays_behind_escapes():
    source = wrap(
        "        while (p > 0) {\n"
        "            if (p == 2) {\n                continue;\n            }\n"
        "        }"
    )
    loop = body_statements(source)[0]
    inner_if = next(n for n in walk(loop) if n.type == "if_statement")

    assert escaping_control_flow([inner_if]) == "continue"


def test_a_labelled_jump_is_refused_rather_than_resolved():
    """Following a label means tracking labelled statements through the method."""
    source = wrap(
        "        outer:\n        for (int i = 0; i < 3; i++) {\n"
        "            for (int j = 0; j < 3; j++) {\n                break outer;\n            }\n"
        "        }"
    )
    assert escaping_control_flow(body_statements(source)) == "labelled break"


def test_straight_line_code_escapes_nowhere():
    source = wrap("        int a = 1;\n        a += p;\n        this.total = a;")
    assert escaping_control_flow(body_statements(source)) is None


def test_brackets_after_the_name_are_part_of_the_type():
    """Java lets `double a[]` mean `double[] a`, and the type field omits them.

    Reading only the type field gave `double`, so an extracted method took a
    `double` where a `double[]` was passed and the file stopped compiling. Found
    by running the engine over the corpus, not by reading the grammar.
    """
    source = wrap("        double a[] = null;\n        int b[][] = null;\n        String c = null;")
    found = declarations_in(method_of(source), source).types

    assert found["a"] == "double[]"
    assert found["b"] == "int[][]"
    assert found["c"] == "String"


def test_one_declaration_may_mix_a_value_and_an_array():
    """`int a, b[];` declares an int and an int array from a single type."""
    source = wrap("        int a = 0, b[] = null;")
    found = declarations_in(method_of(source), source).types

    assert found["a"] == "int"
    assert found["b"] == "int[]"
