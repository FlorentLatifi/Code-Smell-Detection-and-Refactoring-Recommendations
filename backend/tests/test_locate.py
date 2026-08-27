"""Tests for finding a flagged entity in a re-parsed file.

The cases that matter are the ones where name alone or line alone would pick the
wrong node: overloads share a name, and a file edited since it was measured has
something else on the line the detector recorded.
"""

from __future__ import annotations

from javasmell.parsing.java_parser import JavaParser
from javasmell.refactor.locate import find_site, iter_types

SOURCE = b"""package com.acme;

class Ledger {
    private int total;

    int total() {
        return total;
    }

    void post(int amount) {
        total += amount;
    }

    void post(int amount, String note) {
        total += amount;
    }

    static class Entry {
        int value;
    }
}
"""


def test_a_class_is_found_by_line_and_name():
    #  "class Ledger {" is line 3 of SOURCE.
    site = find_site("Ledger.java", SOURCE, "Ledger", 3)
    assert site is not None
    assert site.node.type == "class_declaration"
    assert site.text().startswith("class Ledger")


def test_a_method_is_found_within_its_class():
    #  "int total() {" is line 6.
    site = find_site("Ledger.java", SOURCE, "Ledger", 6, "total")
    assert site is not None
    assert site.node.type == "method_declaration"
    assert site.text().startswith("int total()")
    assert site.enclosing_type.type == "class_declaration"


def test_overloads_are_separated_by_line_not_by_name():
    """Both are called `post`; only the position distinguishes them."""
    #  The one-argument post starts on line 10, the two-argument one on line 14.
    one = find_site("Ledger.java", SOURCE, "Ledger", 10, "post")
    two = find_site("Ledger.java", SOURCE, "Ledger", 14, "post")

    assert one is not None and two is not None
    assert "String note" not in one.text()
    assert "String note" in two.text()


def test_a_wrong_name_on_a_real_line_is_rejected():
    """Guards against a file edited since it was measured.

    Line 6 holds a method, so anchoring on the line alone would return it. The
    detector recorded a different name, which means the file has moved on and
    rewriting here would hit the wrong code.
    """
    assert find_site("Ledger.java", SOURCE, "Ledger", 6, "post") is None


def test_a_line_with_no_declaration_finds_nothing():
    #  Line 7 is `return total;`, inside a method rather than a declaration.
    assert find_site("Ledger.java", SOURCE, "Ledger", 7, "total") is None


def test_nested_types_are_reachable():
    #  "static class Entry {" is line 18.
    site = find_site("Ledger.java", SOURCE, "Entry", 18)
    assert site is not None
    assert site.text().startswith("static class Entry")


def test_iter_types_finds_the_nested_one_too():
    root = JavaParser().parse_tree(SOURCE).root_node
    names = {
        SOURCE[n.child_by_field_name("name").start_byte : n.child_by_field_name("name").end_byte]
        for n in iter_types(root)
    }
    assert names == {b"Ledger", b"Entry"}


def test_span_covers_exactly_the_declaration():
    site = find_site("Ledger.java", SOURCE, "Ledger", 6, "total")
    assert site is not None
    start, end = site.span
    assert SOURCE[start:end].decode() == "int total() {\n        return total;\n    }"
