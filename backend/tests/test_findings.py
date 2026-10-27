"""Tests for suppression in source and for the baseline (VD-163).

Each case is a small piece of Java written out below, so the expected answer is
read off the text rather than off the function. The near misses matter as much
as the hits: a suppression that leaks onto the next declaration hides a finding
nobody looked at, which is worse than not suppressing at all.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from javasmell.detectors.base import Smell
from javasmell.findings import (
    BASELINE_VERSION,
    BaselineError,
    baseline_document,
    fingerprint,
    load_baseline,
    suppressed_in_source,
)


def smell(
    smell_type: str = "LongMethod",
    start_line: int = 2,
    method: str | None = "run()",
    class_name: str = "Job",
) -> Smell:
    return Smell(
        smell_type=smell_type,
        scope="method" if method else "class",
        class_name=class_name,
        package="com.example",
        file_path="Job.java",
        start_line=start_line,
        end_line=start_line + 10,
        conditions=[],
        refactorings=[],
        method=method,
    )


def lines(text: str) -> list[str]:
    return text.strip("\n").splitlines()


# --- fingerprint ----------------------------------------------------------------


def test_the_fingerprint_is_the_documented_identity_hashed():
    """Type, package, class and method, joined by "|", first 32 hex digits of SHA-256."""
    expected = hashlib.sha256(b"LongMethod|com.example|Job|run()").hexdigest()[:32]

    assert fingerprint(smell()) == expected


def test_a_finding_that_moves_keeps_its_fingerprint():
    """An edit above a finding shifts its line; it is still the same finding."""
    assert fingerprint(smell(start_line=2)) == fingerprint(smell(start_line=40))


def test_overloads_and_other_smells_get_their_own_fingerprint():
    assert fingerprint(smell(method="run()")) != fingerprint(smell(method="run(int)"))
    assert fingerprint(smell("LongMethod")) != fingerprint(smell("FeatureEnvy"))


# --- @SuppressWarnings ---------------------------------------------------------


def test_the_bare_annotation_suppresses_every_smell_on_the_declaration():
    source = lines("""
class Job {
    @SuppressWarnings("javasmell")
    void run() {
    }
}
""")
    # The declaration starts at its annotation, line 2.
    assert suppressed_in_source(smell("LongMethod"), source)
    assert suppressed_in_source(smell("FeatureEnvy"), source)


def test_a_named_annotation_suppresses_only_that_smell():
    source = lines("""
class Job {
    @SuppressWarnings("javasmell:LongMethod")
    void run() {
    }
}
""")
    assert suppressed_in_source(smell("LongMethod"), source)
    assert not suppressed_in_source(smell("FeatureEnvy"), source)


def test_the_array_form_of_the_annotation_is_read():
    source = lines("""
class Job {
    @SuppressWarnings({"unchecked", "javasmell:LongMethod"})
    void run() {
    }
}
""")
    assert suppressed_in_source(smell("LongMethod"), source)


def test_an_annotation_inside_the_body_does_not_suppress_the_method():
    """Near miss: a local variable's annotation sits past the opening brace."""
    source = lines("""
class Job {
    void run(int a,
             int b) {
        @SuppressWarnings("javasmell")
        int unused = a + b;
    }
}
""")
    assert not suppressed_in_source(smell("LongMethod"), source)


def test_an_annotation_on_a_later_member_does_not_reach_back():
    """Near miss: the annotation is past this declaration's opening brace."""
    source = lines("""
class Job {
    void run() {
    }
    @SuppressWarnings("javasmell")
    void other() {
    }
}
""")
    assert not suppressed_in_source(smell("LongMethod"), source)


def test_another_tools_suppression_is_not_ours():
    source = lines("""
class Job {
    @SuppressWarnings("PMD.ExcessiveMethodLength")
    void run() {
    }
}
""")
    assert not suppressed_in_source(smell("LongMethod"), source)


# --- // javasmell:ignore --------------------------------------------------------


def test_an_ignore_comment_above_the_declaration_suppresses_it():
    source = lines("""
class Job {
    // javasmell:ignore
    void run() {
    }
}
""")
    assert suppressed_in_source(smell(start_line=3), source)


def test_an_ignore_comment_can_name_the_smells_it_covers():
    source = lines("""
class Job {
    // javasmell:ignore LongMethod, DeepNesting
    void run() {
    }
}
""")
    assert suppressed_in_source(smell("LongMethod", start_line=3), source)
    assert suppressed_in_source(smell("DeepNesting", start_line=3), source)
    assert not suppressed_in_source(smell("FeatureEnvy", start_line=3), source)


def test_the_comment_may_sit_above_the_javadoc():
    source = lines("""
class Job {
    // javasmell:ignore
    /**
     * Runs the job.
     */
    void run() {
    }
}
""")
    assert suppressed_in_source(smell(start_line=6), source)


def test_a_comment_above_an_earlier_member_does_not_carry_over():
    """Near miss: a line of code sits between the comment and this declaration."""
    source = lines("""
class Job {
    // javasmell:ignore
    int counter;
    void run() {
    }
}
""")
    assert not suppressed_in_source(smell(start_line=4), source)


def test_a_line_outside_the_file_suppresses_nothing():
    assert not suppressed_in_source(smell(start_line=99), lines("class Job {}"))
    assert not suppressed_in_source(smell(start_line=0), lines("class Job {}"))


# --- baseline -------------------------------------------------------------------


def test_a_written_baseline_reads_back_as_the_same_fingerprints(tmp_path):
    findings = [smell("LongMethod"), smell("FeatureEnvy"), smell("LongMethod")]
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline_document(findings)), encoding="utf-8")

    # Two distinct findings: the repeated LongMethod is one identity.
    assert load_baseline(path) == {fingerprint(findings[0]), fingerprint(findings[1])}


def test_the_baseline_file_is_sorted_so_it_diffs_cleanly():
    document = baseline_document([smell("LongMethod"), smell("FeatureEnvy")])

    assert document["version"] == BASELINE_VERSION
    assert document["findings"] == sorted(document["findings"])  # type: ignore[type-var]


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps([]),
        json.dumps({"version": BASELINE_VERSION + 1, "findings": []}),
        json.dumps({"version": BASELINE_VERSION, "findings": "abc"}),
        json.dumps({"version": BASELINE_VERSION, "findings": [1, 2]}),
    ],
)
def test_a_file_that_is_not_a_baseline_is_refused(tmp_path, content):
    path = tmp_path / "baseline.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(BaselineError):
        load_baseline(path)


def test_a_missing_baseline_is_refused(tmp_path):
    with pytest.raises(BaselineError):
        load_baseline(tmp_path / "absent.json")
