"""Tests for reading an external detector's report.

The comparison against PMD lives or dies on this file: if a violation fails to
land on the entity it describes, PMD is scored as having found nothing, and the
resulting table flatters this project. That failure is silent by construction,
which is why the recovery case below is tested rather than trusted.
"""

from __future__ import annotations

from pathlib import Path

from javasmell.evaluation.external import (
    entity_key,
    entity_of,
    parse_report,
    rules_at,
    scan_report,
)

REPORT_HEAD = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<pmd xmlns="http://pmd.sourceforge.net/report/2.0.0" version="7.27.0">\n'
)


def violation(rule: str, cls: str, method: str | None = None) -> str:
    attributes = f'beginline="10" endline="20" rule="{rule}" class="{cls}"'
    if method is not None:
        attributes += f' method="{method}"'
    return f'<violation {attributes} priority="3">\ntext\n</violation>\n'


def report(path: Path, body: str, closed: bool = True) -> Path:
    path.write_text(REPORT_HEAD + body + ("</pmd>\n" if closed else ""), encoding="utf-8")
    return path


def test_a_method_sample_names_its_class_and_method():
    """MLCQ writes the parameter types after the method name; PMD carries neither."""
    assert entity_of("com.example.shop.OrderManager#priceOrder Customer int") == (
        "OrderManager",
        "priceOrder",
    )


def test_a_class_sample_has_no_method():
    assert entity_of("com.example.shop.OrderManager") == ("OrderManager", None)


def test_a_nested_class_is_named_by_its_innermost_part():
    """PMD reports the simple name of the type the violation is in, not the outer one."""
    assert entity_of("com.example.Outer.Inner#run") == ("Inner", "run")


def test_the_key_separator_cannot_occur_in_a_java_name():
    """A tab: no Java identifier or path contains one, so the three parts cannot blur."""
    key = entity_key("a/B.java", "B", "m")

    assert chr(9) in key
    assert key.count(chr(9)) == 2


def test_the_key_is_relative_to_the_repository_root():
    """PMD reports absolute paths and MLCQ publishes relative ones; only one can win."""
    absolute = entity_key("/repo/src/B.java", "B", None, "/repo")
    relative = entity_key("/src/B.java", "B", None)

    assert absolute == relative


def test_a_violation_is_found_on_the_entity_it_names(tmp_path):
    """The whole comparison reduces to this lookup succeeding."""
    path = report(
        tmp_path / "pmd.xml",
        '<file name="/repo/src/A.java">\n' + violation("GodClass", "A") + "</file>\n",
    )

    found = parse_report(path, Path("/repo"))

    assert rules_at(found, entity_key("/src/A.java", "A", None)) == {"GodClass"}
    assert found.recovered is False


def test_a_class_rule_does_not_land_on_a_method_of_that_class():
    """NcssCount fires on both, and the two answers are different questions.

    A class-level violation carries no method attribute, so its key ends with an
    empty method and cannot be confused with any method's key.
    """
    assert entity_key("/src/A.java", "A", None) != entity_key("/src/A.java", "A", "m")


def test_a_file_pmd_could_not_read_is_counted_not_ignored(tmp_path):
    """Counted, because "failed" and "found nothing" are opposite claims."""
    path = report(
        tmp_path / "pmd.xml",
        '<file name="/repo/src/A.java">\n'
        + violation("DataClass", "A")
        + "</file>\n"
        + '<error filename="/repo/src/B.java" msg="boom"/>\n',
    )

    found = parse_report(path, Path("/repo"))

    assert found.errors == 1
    assert rules_at(found, entity_key("/src/A.java", "A", None)) == {"DataClass"}


def test_a_report_the_parser_rejects_is_recovered_rather_than_read_as_empty(tmp_path):
    """PMD emits an unbalanced closing tag when a file fails, and the JDK does that.

    The first version of this code caught the parse error and returned no
    violations, which turned the corpus's largest repository into a tool that
    found nothing. The recovery must produce the same keys and say it was used.
    """
    body = (
        '<file name="/repo/src/A.java">\n'
        + violation("GodClass", "A")
        + violation("NcssCount", "A", "priceOrder")
        + "</file>\n"
        + "</error>\n"  # the stray tag PMD writes
    )
    path = report(tmp_path / "pmd.xml", body)

    found = parse_report(path, Path("/repo"))

    assert found.recovered is True
    assert rules_at(found, entity_key("/src/A.java", "A", None)) == {"GodClass"}
    assert rules_at(found, entity_key("/src/A.java", "A", "priceOrder")) == {"NcssCount"}


def test_both_readers_agree_on_a_report_they_can_both_read(tmp_path):
    """The recovery path is only defensible if it is not a second, different reader."""
    body = (
        '<file name="/repo/src/A.java">\n'
        + violation("GodClass", "A")
        + violation("NcssCount", "A", "m")
        + "</file>\n"
    )
    path = report(tmp_path / "pmd.xml", body)

    strict = parse_report(path, Path("/repo"))
    scanned = scan_report(path, Path("/repo"))

    assert strict.at == scanned.at


def test_a_missing_report_is_empty_rather_than_an_exception(tmp_path):
    """A repository PMD never wrote a report for is a repository with no verdict."""
    found = parse_report(tmp_path / "absent.xml", Path("/repo"))

    assert found.at == {}
    assert found.errors == 0


def test_an_entity_nothing_fired_on_has_no_rules(tmp_path):
    path = report(
        tmp_path / "pmd.xml",
        '<file name="/repo/src/A.java">\n' + violation("GodClass", "A") + "</file>\n",
    )

    found = parse_report(path, Path("/repo"))

    assert rules_at(found, entity_key("/src/B.java", "B", None)) == set()
