"""Tests for the MLCQ feature table.

The expectations here are hand-derived from the snippet in each test, and the
first test exists purely to fail when someone adds a metric to the calculator
without adding a column for it.
"""

from __future__ import annotations

from javasmell.analysis import analyze_path, analyze_source
from javasmell.evaluation.dataset import (
    CLASS_METRICS,
    METHOD_METRICS,
    columns,
    feature_columns,
    row,
)
from javasmell.evaluation.mlcq import Review, Sample


def make_sample(
    smell: str = "blob",
    entity_type: str = "class",
    severities: tuple[str, ...] = ("major", "minor"),
) -> Sample:
    return Sample(
        sample_id="42",
        smell=smell,
        entity_type=entity_type,
        code_name="com.acme.Ledger",
        repository="git@github.com:apache/alpha.git",
        commit_hash="abcdef0123456789",
        path="/src/com/acme/Ledger.java",
        start_line=1,
        end_line=9,
        reviews=tuple(
            Review(sample_id="42", reviewer_id=str(i), smell=smell, severity=severity)
            for i, severity in enumerate(severities)
        ),
    )


def test_declared_columns_still_match_what_the_calculator_produces():
    """A metric added to the calculator must be added to the dataset as well.

    Otherwise it is measured on every run and silently dropped before any model
    or sweep can see it -- the same failure mode as the two LOC counters that
    drifted apart in VD-21, and just as invisible.
    """
    project = analyze_path("tests/fixtures")
    measured_class: set[str] = set()
    measured_method: set[str] = set()
    for unit in project.units:
        for cls in unit.classes:
            measured_class |= set(cls.metrics)
            for method in cls.methods:
                measured_method |= set(method.metrics)

    assert measured_class == set(CLASS_METRICS)
    assert measured_method == set(METHOD_METRICS)


def test_every_declared_column_is_filled_exactly_once():
    project = analyze_source("class Ledger { int total() { return 1; } }")
    cls = project.units[0].classes[0]

    produced = row(make_sample(), cls, None)

    assert set(produced) == set(columns())
    assert len(columns()) == len(set(columns()))


def test_class_sample_leaves_the_method_columns_empty():
    """A class has no cyclomatic complexity; 0.0 would be a measurement never taken."""
    project = analyze_source("class Ledger { int total() { return 1; } }")
    cls = project.units[0].classes[0]

    produced = row(make_sample(), cls, None)

    assert all(produced[f"m_{name}"] == "" for name in METHOD_METRICS)
    assert produced["c_NOM"] == "1.0"  # one non-constructor method
    assert produced["is_constructor"] == ""
    assert produced["is_accessor"] == ""
    assert produced["class_kind"] == "class"


def test_method_sample_carries_both_its_own_and_its_class_metrics():
    """Feature Envy is a claim about a method relative to its class, not in isolation."""
    source = """
    class Ledger {
        private int total;
        int total() { return total; }
        void post(int a, int b) { total = a + b; }
    }
    """
    project = analyze_source(source)
    cls = project.units[0].classes[0]
    post = next(m for m in cls.methods if m.name == "post")

    produced = row(make_sample(smell="long method", entity_type="function"), cls, post)

    assert produced["m_NP"] == "2.0"  # a and b
    assert produced["m_CC"] == "1.0"  # no branches
    assert produced["c_NOM"] == "2.0"  # total() and post()
    assert produced["is_constructor"] == "0"
    assert produced["is_accessor"] == "0"


def test_labels_cover_every_aggregation():
    """Ranks are none=0, minor=1, major=2, critical=3.

    major + minor = (2 + 1) / 2 = 1.5, rounded half up to 2 = major.
    """
    produced = row(
        make_sample(severities=("major", "minor")),
        analyze_source("class Ledger {}").units[0].classes[0],
        None,
    )

    assert produced["severity_mean"] == "2"
    assert produced["severity_max"] == "2"
    assert produced["severity_min"] == "1"
    assert produced["severity_unanimous"] == ""  # reviewers disagreed
    assert produced["smelly_mean"] == "1"
    assert produced["smelly_unanimous"] == ""
    assert produced["is_unanimous"] == "0"
    assert produced["review_count"] == "2"


def test_a_split_vote_counts_as_smelly():
    """minor + none = 0.5, and which way that rounds decides the label.

    Half up gives 1 (minor, smelly); Python's built-in round() is banker's and
    would give 0 (none, clean), turning a sample one reviewer called a smell
    into ground-truth evidence that it is not one. This is the single tie that
    separates the two rules, so it is the one worth pinning.
    """
    produced = row(
        make_sample(severities=("minor", "none")),
        analyze_source("class Ledger {}").units[0].classes[0],
        None,
    )

    assert produced["severity_mean"] == "1"
    assert produced["smelly_mean"] == "1"
    assert produced["smelly_min"] == "0"  # the lenient reading disagrees


def test_feature_columns_are_class_first_then_method():
    features = feature_columns()
    assert features[0] == "c_AMW"
    assert features[len(CLASS_METRICS)] == "m_ATFD"
    assert len(features) == len(CLASS_METRICS) + len(METHOD_METRICS) == 26
