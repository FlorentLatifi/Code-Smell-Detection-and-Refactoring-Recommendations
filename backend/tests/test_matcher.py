"""Tests for the MLCQ-to-model matcher.

Every fixture below carries its line numbers in trailing comments, so each
expected ``start_line``/``end_line`` can be read straight off the source
instead of being taken from whatever the parser happened to produce. That is
the whole point of these tests: the matcher decides which entity a
ground-truth label belongs to, and a mismatch it accepts silently would be
invisible in every number the thesis reports afterwards.

The cases the plan named as risks (overloads, inner classes) get a test
each, because the claim that the line anchor resolves them without symbol
resolution is exactly the kind of claim that has to be demonstrated.
"""

from __future__ import annotations

import pytest

from javasmell.evaluation.matcher import (
    MatchOutcome,
    ProjectIndex,
    match_samples,
    normalise_path,
    relative_key,
    summarise,
)
from javasmell.evaluation.mlcq import Review, Sample
from javasmell.metrics.calculator import compute_all
from javasmell.model.entities import ProjectModel
from javasmell.parsing.java_parser import JavaParser

ROOT = "/corpus/apache__demo__0123456789ab"
DEMO_PATH = "src/main/java/demo/Demo.java"


def project_of(source: str, path: str = DEMO_PATH) -> ProjectModel:
    """A one-file project laid out the way the corpus lays repositories out."""
    project = ProjectModel(root=ROOT)
    project.units.append(JavaParser().parse_source(source, f"{ROOT}/{path}"))
    return compute_all(project)


def sample(
    code_name: str,
    entity_type: str,
    start_line: int,
    end_line: int,
    path: str = DEMO_PATH,
) -> Sample:
    """One MLCQ sample; only the fields the matcher reads carry meaning."""
    return Sample(
        sample_id="s1",
        smell="blob",
        entity_type=entity_type,
        code_name=code_name,
        repository="git@github.com:apache/demo.git",
        commit_hash="0123456789abcdef",
        path=f"/{path}",
        start_line=start_line,
        end_line=end_line,
        reviews=(Review("s1", "r1", "blob", "major"),),
    )


# ----------------------------------------------------------------------
# Reading MLCQ's four spellings of code_name
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("code_name", "expected"),
    [
        ("com.acme.Ledger", "Ledger"),  # type
        ("com.acme.Ledger.Entry", "Entry"),  # inner type: last segment wins
        ("com.acme.Ledger#post", "post"),  # the common method form
        ("com.acme.Ledger#post String|int", "post"),  # parameters are dropped
        ("com.acme.Ledger.Ledger int", "Ledger"),  # constructors use a dot
        ("com.acme.ledger..post String", "post"),  # empty type segment (4 real rows)
        ("Ledger", "Ledger"),  # no package at all (6 real rows)
    ],
)
def test_simple_name_survives_every_code_name_shape(code_name: str, expected: str) -> None:
    assert sample(code_name, "class", 1, 2).simple_name == expected


# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
def test_paths_from_both_sides_reduce_to_the_same_key() -> None:
    windows = "\\\\?\\C:\\corpus\\repo\\src\\Demo.java"
    assert normalise_path(windows) == "C:/corpus/repo/src/Demo.java"
    assert relative_key(windows, "\\\\?\\C:\\corpus\\repo") == "src/Demo.java"
    assert relative_key("/corpus/repo/src/Demo.java", "/corpus/repo/") == "src/Demo.java"


# ----------------------------------------------------------------------
# The two ambiguities the line anchor is supposed to resolve
# ----------------------------------------------------------------------
OVERLOADS = """\
package demo;                                   // 1
                                                // 2
class Repo {                                    // 3
    void save(String a) {                       // 4
        log(a);                                 // 5
    }                                           // 6
                                                // 7
    void save(String a, int b) {                // 8
        log(a);                                 // 9
    }                                           // 10
}                                               // 11
"""


def test_overloads_are_separated_by_their_line_alone() -> None:
    index = ProjectIndex(project_of(OVERLOADS))

    one = index.match(sample("demo.Repo#save String", "function", 4, 6))
    two = index.match(sample("demo.Repo#save String|int", "function", 8, 10))

    assert one.outcome is MatchOutcome.MATCHED
    assert two.outcome is MatchOutcome.MATCHED
    # Both are named `save`; only the line range tells them apart.
    assert one.method is not None and one.method.parameter_count == 1
    assert two.method is not None and two.method.parameter_count == 2


NESTED = """\
package demo;                                   // 1
                                                // 2
class Outer {                                   // 3
    static class Inner {                        // 4
        void go() {                             // 5
        }                                       // 6
    }                                           // 7
}                                               // 8
"""


def test_inner_class_is_not_taken_for_its_outer() -> None:
    index = ProjectIndex(project_of(NESTED))

    outer = index.match(sample("demo.Outer", "class", 3, 8))
    inner = index.match(sample("demo.Outer.Inner", "class", 4, 7))

    assert outer.outcome is MatchOutcome.MATCHED
    assert outer.cls is not None and outer.cls.name == "Outer"
    assert inner.outcome is MatchOutcome.MATCHED
    assert inner.cls is not None and inner.cls.name == "Inner"
    # A method sample resolves to the inner class that declares it, not the file.
    go = index.match(sample("demo.Outer.Inner#go", "function", 5, 6))
    assert go.cls is not None and go.cls.name == "Inner"


# ----------------------------------------------------------------------
# Refusals: every one of these would otherwise be a silent mismatch
# ----------------------------------------------------------------------
def test_a_different_name_on_the_right_line_is_refused() -> None:
    index = ProjectIndex(project_of(NESTED))
    # Line 3 does declare a class, but MLCQ says the entity is called Ledger.
    result = index.match(sample("demo.Ledger", "class", 3, 8))
    assert result.outcome is MatchOutcome.NAME_MISMATCH
    assert result.cls is None


def test_a_different_extent_is_refused_but_reported() -> None:
    index = ProjectIndex(project_of(NESTED))
    # Right name, right start, wrong end: the file moved on since the review.
    result = index.match(sample("demo.Outer", "class", 3, 40))
    assert result.outcome is MatchOutcome.SPAN_MISMATCH
    assert not result.ok
    # The entity is still attached, so the failure can be inspected rather than
    # only counted.
    assert result.cls is not None and result.cls.end_line == 8


def test_nothing_on_that_line_is_no_entity() -> None:
    index = ProjectIndex(project_of(NESTED))
    result = index.match(sample("demo.Outer", "class", 2, 8))  # line 2 is blank
    assert result.outcome is MatchOutcome.NO_ENTITY


def test_a_file_outside_the_project_is_no_file() -> None:
    index = ProjectIndex(project_of(NESTED))
    result = index.match(sample("demo.Gone", "class", 3, 8, path="src/main/java/demo/Gone.java"))
    assert result.outcome is MatchOutcome.NO_FILE


ONE_LINE_OVERLOADS = """\
package demo;                                   // 1
class Repo { void a() { } void a(int x) { } }   // 2
"""


def test_two_entities_of_one_name_on_one_line_are_ambiguous() -> None:
    """The line anchor has a limit, and it is reported rather than guessed at."""
    index = ProjectIndex(project_of(ONE_LINE_OVERLOADS))
    result = index.match(sample("demo.Repo#a", "function", 2, 2))
    assert result.outcome is MatchOutcome.AMBIGUOUS
    assert result.method is None


# ----------------------------------------------------------------------
# Files the grammar cannot read
# ----------------------------------------------------------------------
BROKEN = """\
package demo;                                   // 1
class Repo {                                    // 2
    void _(  {{{ ]                              // 3
}                                               // 4
"""


def test_a_file_that_does_not_parse_is_named_as_such() -> None:
    """Hadoop's Hamlet.java is the real case: `_` is illegal since Java 9.

    Without this distinction the sample would be filed under NO_ENTITY, which
    would blame the ground truth for a limitation of our own front end.
    """
    project = project_of(BROKEN)
    assert project.units[0].has_syntax_errors
    result = ProjectIndex(project).match(sample("demo.Repo#save", "function", 3, 3))
    assert result.outcome is MatchOutcome.SYNTAX_ERRORS


def test_a_clean_file_is_not_flagged() -> None:
    assert not project_of(NESTED).units[0].has_syntax_errors


# ----------------------------------------------------------------------
# The report, whose numbers become the denominator of the evaluation
# ----------------------------------------------------------------------
def test_a_batch_is_reported_outcome_by_outcome() -> None:
    project = project_of(NESTED)
    samples = [
        sample("demo.Outer", "class", 3, 8),  # matches
        sample("demo.Outer.Inner", "class", 4, 7),  # matches
        sample("demo.Outer", "class", 2, 8),  # blank line -> no_entity
        sample("demo.Gone", "class", 3, 8, path="src/main/java/demo/Gone.java"),
    ]
    report = summarise(match_samples(project, samples))

    assert report.total == 4
    assert report.matched == 2
    assert report.match_rate == 0.5
    assert report.counts[MatchOutcome.NO_ENTITY] == 1
    assert report.counts[MatchOutcome.NO_FILE] == 1
    # The description is what gets read into the thesis, so it states the
    # shortfall rather than only the successes.
    described = report.describe()
    assert "2/4 samples matched (50.0%)" in described
    assert "no_entity" in described


def test_an_empty_batch_has_no_rate_to_divide_by() -> None:
    report = summarise([])
    assert report.total == 0
    assert report.match_rate == 0.0
