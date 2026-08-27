"""Tests for the byte-range rewriter.

This is the only code in the project that modifies the author's source, so the
cases below are chosen for the ways a rewriter corrupts a file while appearing
to work: offsets shifted by an earlier edit, two edits silently fighting over
the same bytes, and a multi-byte character cut in half.

Every expected value is written out by hand from the literal in the test.
"""

from __future__ import annotations

import pytest

from javasmell.refactor.edits import (
    Edit,
    EditConflict,
    apply_edits,
    check,
    dedent,
    indent_at,
    line_start,
)


def test_one_replacement():
    #  b"class A {}" ->  replace bytes [6:7], which is "A"
    assert apply_edits(b"class A {}", [Edit(6, 7, b"Ledger")]) == b"class Ledger {}"


def test_edits_apply_to_the_text_they_were_measured_against():
    """The property that back-to-front application exists to guarantee.

    Both offsets are measured against the original. Applying front to back
    would leave the second edit pointing four bytes short once the first has
    grown the text, and it would take the wrong slice without erroring.
    """
    source = b"int a = 1; int b = 2;"
    #          0123456789...          "a" is at 4, "b" is at 15
    result = apply_edits(source, [Edit(4, 5, b"alpha"), Edit(15, 16, b"beta")])
    assert result == b"int alpha = 1; int beta = 2;"


def test_input_order_does_not_matter():
    source = b"int a = 1; int b = 2;"
    forwards = apply_edits(source, [Edit(4, 5, b"alpha"), Edit(15, 16, b"beta")])
    backwards = apply_edits(source, [Edit(15, 16, b"beta"), Edit(4, 5, b"alpha")])
    assert forwards == backwards


def test_overlapping_edits_are_refused():
    """No rule here would be better than refusing: one change would vanish."""
    with pytest.raises(EditConflict, match=r"\[2:6\] overlaps \[4:8\]"):
        apply_edits(b"abcdefghij", [Edit(2, 6, b"X"), Edit(4, 8, b"Y")])


def test_touching_edits_are_allowed():
    """Rewriting two adjacent statements is ordinary, not a conflict."""
    #  b"abcdef": [0:3] is "abc", [3:6] is "def"
    result = apply_edits(b"abcdef", [Edit(0, 3, b"X"), Edit(3, 6, b"Y")])
    assert result == b"XY"


def test_an_insertion_removes_nothing():
    #  insert at offset 5, between "class" and " A"
    assert apply_edits(b"class A {}", [Edit(5, 5, b" final")]) == b"class final A {}"


def test_two_insertions_at_one_offset_conflict():
    """Their order would decide the output, and nothing here defines it."""
    with pytest.raises(EditConflict):
        apply_edits(b"abc", [Edit(1, 1, b"X"), Edit(1, 1, b"Y")])


def test_an_empty_replacement_deletes():
    #  b"int a = 1;": drop " = 1", bytes [5:9]
    assert apply_edits(b"int a = 1;", [Edit(5, 9, b"")]) == b"int a;"


def test_an_edit_past_the_end_is_refused():
    with pytest.raises(ValueError, match="past the file"):
        apply_edits(b"abc", [Edit(2, 9, b"X")])


def test_a_backwards_range_cannot_be_built():
    with pytest.raises(ValueError, match="precedes start"):
        Edit(9, 2, b"X")


def test_a_negative_start_cannot_be_built():
    with pytest.raises(ValueError, match="negative start"):
        Edit(-1, 2, b"X")


def test_no_edits_leaves_the_file_untouched():
    assert apply_edits(b"class A {}", []) == b"class A {}"


def test_multibyte_source_survives():
    """The reason the whole pipeline is in bytes rather than characters.

    "Përllogarit" is 11 characters but 12 bytes: "ë" is two (0xC3 0xAB). A
    rewriter working in character offsets would take its ranges two bytes short
    from here on and cut through that sequence, producing a file that either
    fails to decode or decodes to the wrong text.
    """
    source = "int x; // Përllogarit\nint y;".encode()
    assert len(source) == len("int x; // Përllogarit\nint y;") + 1

    #  "int y" starts after the comment and the newline.
    y_at = source.index(b"int y") + 4
    result = apply_edits(source, [Edit(y_at, y_at + 1, b"total")])

    assert result.decode("utf-8") == "int x; // Përllogarit\nint total;"


def test_check_returns_document_order():
    ordered = check([Edit(15, 16, b"b"), Edit(4, 5, b"a"), Edit(9, 9, b"c")])
    assert [e.start for e in ordered] == [4, 9, 15]


# ----------------------------------------------------------------------
# Indentation
# ----------------------------------------------------------------------


def test_indent_is_read_from_the_line_the_offset_is_on():
    source = b"class A {\n    int x;\n\t\tint y;\n"
    assert indent_at(source, source.index(b"class")) == b""
    assert indent_at(source, source.index(b"int x")) == b"    "
    assert indent_at(source, source.index(b"int y")) == b"\t\t"


def test_indent_of_an_offset_inside_a_line():
    """Anywhere on the line gives the same answer."""
    source = b"    total += amount;"
    assert indent_at(source, 10) == b"    "


def test_line_start_handles_the_first_line():
    assert line_start(b"abc\ndef", 1) == 0
    assert line_start(b"abc\ndef", 5) == 4


def test_dedent_removes_exactly_one_level():
    block = b"a();\n        b();\n        c();"
    #  The first line carries no indent: it begins where the statement begins.
    assert dedent(block, b"    ") == b"a();\n    b();\n    c();"


def test_dedent_leaves_alone_a_line_that_is_not_indented_that_way():
    """The reason it matches a prefix rather than cutting a fixed length.

    A line inside a Java text block sits at whatever depth the author chose, and
    trimming four bytes off it would change the value of the string.
    """
    block = b"x();\n  odd();\n        normal();"
    assert dedent(block, b"    ") == b"x();\n  odd();\n    normal();"


def test_dedent_with_no_unit_changes_nothing():
    assert dedent(b"    a();", b"") == b"    a();"
