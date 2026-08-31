"""Tests for the reviewer-agreement ceiling.

Each matrix is worked out on paper. The figure this produces is the one the
discussion reads every detector score against, so a value captured from a run
would prove only that the code still does what it did.
"""

from __future__ import annotations

import pytest

from javasmell.evaluation.agreement import ceiling, pairwise
from javasmell.evaluation.mlcq import Review, Sample


def make_sample(sample_id: str, severities: tuple[str, ...], smell: str = "blob") -> Sample:
    return Sample(
        sample_id=sample_id,
        smell=smell,
        entity_type="class",
        code_name="a.b.C",
        repository="git@github.com:owner/name.git",
        commit_hash="abc123",
        path="/src/C.java",
        start_line=1,
        end_line=20,
        reviews=tuple(
            Review(sample_id=sample_id, reviewer_id=str(index), smell=smell, severity=severity)
            for index, severity in enumerate(severities)
        ),
    )


def test_reviewers_who_always_agree_reach_a_perfect_ceiling():
    samples = [
        make_sample("1", ("major", "critical")),  # both smelly
        make_sample("2", ("none", "none")),  # both clean
    ]

    result = pairwise(samples, "blob")

    # Sample 1 gives (True, True) twice; sample 2 gives (False, False) twice.
    # tp=2, tn=2, fp=fn=0 -> MCC = 1.
    assert result.matrix.tp == 2
    assert result.matrix.tn == 2
    assert result.matrix.fp == 0
    assert result.matrix.fn == 0
    assert result.matrix.mcc == pytest.approx(1.0)


def test_severity_disagreement_is_not_disagreement_on_presence():
    """The binary question is the one the detectors answer.

    Two reviewers calling the same class "minor" and "critical" disagree about
    how bad it is, not about whether the smell is there, and a detector is never
    asked the first question.
    """
    result = pairwise([make_sample("1", ("minor", "critical"))], "blob")

    # Both reviewers saw the smell, so the pair agrees: two true positives and
    # no disagreement cell. MCC stays undefined here because the matrix has no
    # negatives at all -- that is the subject of its own test below.
    assert result.matrix.tp == 2
    assert (result.matrix.fp, result.matrix.fn) == (0, 0)


def test_one_disagreeing_pair_lands_where_the_arithmetic_says():
    samples = [
        make_sample("1", ("major", "none")),  # one says smelly, one does not
        make_sample("2", ("major", "major")),
        make_sample("3", ("none", "none")),
    ]

    result = pairwise(samples, "blob")

    # Sample 1 counted both ways gives one fn and one fp.
    # Sample 2 gives tp=2; sample 3 gives tn=2.
    # tp=2, tn=2, fp=1, fn=1.
    # (2*2 - 1*1) / sqrt(3 * 3 * 3 * 3) = 3 / 9 = 0.3333333333
    assert (result.matrix.tp, result.matrix.tn) == (2, 2)
    assert (result.matrix.fp, result.matrix.fn) == (1, 1)
    assert result.matrix.mcc == pytest.approx(1 / 3, abs=1e-9)


def test_the_matrix_is_symmetric_so_no_reviewer_is_the_authority():
    """Counting one direction only would make the answer depend on review order."""
    forward = pairwise([make_sample("1", ("major", "none"))], "blob")
    backward = pairwise([make_sample("1", ("none", "major"))], "blob")

    assert forward.matrix.fp == forward.matrix.fn
    assert forward.matrix.to_dict() == backward.matrix.to_dict()


def test_three_reviewers_contribute_every_pair():
    result = pairwise([make_sample("1", ("major", "major", "none"))], "blob")

    # Three reviewers make three unordered pairs, each counted twice: six cells.
    assert result.pairs == 3
    assert result.matrix.total == 6


def test_singly_reviewed_samples_are_counted_not_hidden():
    samples = [make_sample("1", ("major",)), make_sample("2", ("major", "major"))]

    result = pairwise(samples, "blob")

    assert result.samples == 2
    assert result.samples_with_one_review == 1
    assert result.pairs == 1


def test_an_undefined_ceiling_is_none_rather_than_zero():
    """Every reviewer calling every sample clean leaves MCC undefined.

    Reporting zero there would read as "the reviewers agree no better than
    chance", which is the opposite of what unanimity means.
    """
    result = pairwise([make_sample("1", ("none", "none"))], "blob")

    assert result.matrix.mcc is None


def test_ceiling_keeps_the_smells_apart():
    samples = [
        make_sample("1", ("major", "major"), smell="blob"),
        make_sample("2", ("major", "none"), smell="data class"),
    ]

    result = ceiling(samples, ["blob", "data class"])

    # Blob: one agreeing pair, counted both ways -> tp=2, nothing else.
    assert result["blob"].pairs == 1
    assert (result["blob"].matrix.tp, result["blob"].matrix.fp) == (2, 0)
    # Data class: one pair that disagrees -> fp=1, fn=1, tp=tn=0.
    # (0*0 - 1*1) / sqrt(1 * 1 * 1 * 1) = -1, total disagreement.
    assert result["data class"].pairs == 1
    assert result["data class"].matrix.mcc == pytest.approx(-1.0)
