"""Tests for the evaluation scoring.

Every matrix below is worked out on paper first and the arithmetic is written
next to the assertion. These are the figures the Results chapter reports, so a
value captured from a previous run would prove only that the formula has not
changed, not that it was ever right.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from javasmell.detectors.base import Condition, Smell
from javasmell.detectors.thresholds import DEFAULT
from javasmell.evaluation.mlcq import Aggregation, Review, Sample
from javasmell.evaluation.scoring import (
    PRIMARY_VARIANT,
    VARIANTS,
    Confusion,
    Prediction,
    SmellIndex,
    confusion,
    decode_verdict,
    encode_verdict,
    recall_by_severity,
    score,
    severity_agreement,
    weighted_kappa,
)


def make_sample(
    sample_id: str = "1",
    smell: str = "blob",
    severities: tuple[str, ...] = ("major",),
    start_line: int = 10,
) -> Sample:
    return Sample(
        sample_id=sample_id,
        smell=smell,
        entity_type="class",
        code_name="com.acme.Ledger",
        repository="git@github.com:apache/alpha.git",
        commit_hash="abcdef0123456789",
        path="/src/com/acme/Ledger.java",
        start_line=start_line,
        end_line=start_line + 20,
        reviews=tuple(
            Review(sample_id=sample_id, reviewer_id=str(i), smell=smell, severity=severity)
            for i, severity in enumerate(severities)
        ),
    )


def make_smell(smell_type: str = "GodClass", start_line: int = 10) -> Smell:
    return Smell(
        smell_type=smell_type,
        scope="class",
        class_name="Ledger",
        package="com.acme",
        file_path="/src/com/acme/Ledger.java",
        start_line=start_line,
        end_line=start_line + 20,
        conditions=[Condition("WMC", ">", 47, 60)],
        refactorings=["ExtractClass"],
    )


# ----------------------------------------------------------------------
# The confusion matrix and its derived scores
# ----------------------------------------------------------------------


def test_confusion_counts_each_quadrant() -> None:
    """Four smelly samples, six clean; the detector fires on five of them.

    It catches three of the four smelly ones and two of the six clean ones,
    which is TP=3, FN=1, FP=2, TN=4.
    """
    pairs = [
        (True, True),
        (True, True),
        (True, True),
        (True, False),
        (False, True),
        (False, True),
        (False, False),
        (False, False),
        (False, False),
        (False, False),
    ]
    matrix = confusion(pairs)
    assert (matrix.tp, matrix.fn, matrix.fp, matrix.tn) == (3, 1, 2, 4)
    assert matrix.total == 10


def test_scores_of_that_matrix() -> None:
    """Derived from TP=3, FP=2, FN=1, TN=4.

    precision = 3/5   = 0.6
    recall    = 3/4   = 0.75
    F1        = 2 * 0.6 * 0.75 / 1.35 = 0.9 / 1.35 = 0.6667
    accuracy  = 7/10  = 0.7
    MCC       = (3*4 - 2*1) / sqrt(5 * 4 * 6 * 5)
              = 10 / sqrt(600) = 10 / 24.4949 = 0.40825
    """
    matrix = Confusion(tp=3, fp=2, fn=1, tn=4)
    assert matrix.precision == pytest.approx(0.6)
    assert matrix.recall == pytest.approx(0.75)
    assert matrix.f1 == pytest.approx(0.9 / 1.35)
    assert matrix.accuracy == pytest.approx(0.7)
    assert matrix.mcc == pytest.approx(10 / math.sqrt(600))


def test_precision_is_undefined_when_the_detector_never_fires() -> None:
    """Not 0.0: nothing was predicted, so nothing was predicted wrongly."""
    matrix = Confusion(tp=0, fp=0, fn=5, tn=5)
    assert matrix.precision is None
    assert matrix.recall == pytest.approx(0.0)
    assert matrix.f1 is None


def test_mcc_is_undefined_when_a_margin_is_empty() -> None:
    """A detector that fires on everything, with every label positive.

    Accuracy calls this perfect; MCC refuses to score it at all, which is the
    reason both are reported.
    """
    matrix = Confusion(tp=8, fp=0, fn=0, tn=0)
    assert matrix.accuracy == pytest.approx(1.0)
    assert matrix.mcc is None


def test_a_detector_that_never_fires_scores_zero_mcc_not_high_accuracy() -> None:
    """78% of MLCQ labels are "none", so this is the failure mode to catch.

    TP=0, FP=0, FN=22, TN=78: accuracy 0.78 looks respectable and MCC is 0.
    """
    matrix = Confusion(tp=0, fp=0, fn=22, tn=78)
    assert matrix.accuracy == pytest.approx(0.78)
    assert matrix.mcc is None  # no positive prediction at all: undefined, not good


# ----------------------------------------------------------------------
# Locating a detection
# ----------------------------------------------------------------------


def test_smell_index_finds_a_detector_that_fired_on_the_entity() -> None:
    index = SmellIndex([make_smell("GodClass", start_line=10)])
    assert index.fired("/src/com/acme/Ledger.java", 10, ("GodClass",))


def test_smell_index_does_not_confuse_neighbouring_entities() -> None:
    """Two entities in one file are told apart by their start line."""
    index = SmellIndex([make_smell("GodClass", start_line=10)])
    assert not index.fired("/src/com/acme/Ledger.java", 40, ("GodClass",))


def test_smell_index_matches_any_detector_of_the_variant() -> None:
    """The `with_size` variant fires when either detector did."""
    index = SmellIndex([make_smell("LargeClass", start_line=10)])
    assert not index.fired("/src/com/acme/Ledger.java", 10, ("GodClass",))
    assert index.fired("/src/com/acme/Ledger.java", 10, ("GodClass", "LargeClass"))


# ----------------------------------------------------------------------
# Scoring against the ground truth
# ----------------------------------------------------------------------


def test_score_pairs_labels_with_detections() -> None:
    """Two smelly samples, one caught; one clean sample, not flagged.

    TP=1, FN=1, FP=0, TN=1.
    """
    predictions = [
        Prediction(make_sample("1", severities=("major",)), {PRIMARY_VARIANT: True}),
        Prediction(make_sample("2", severities=("minor",)), {PRIMARY_VARIANT: False}),
        Prediction(make_sample("3", severities=("none",)), {PRIMARY_VARIANT: False}),
    ]
    matrix = score(predictions, "blob", PRIMARY_VARIANT)
    assert (matrix.tp, matrix.fn, matrix.fp, matrix.tn) == (1, 1, 0, 1)


def test_score_ignores_samples_of_another_smell() -> None:
    predictions = [
        Prediction(make_sample("1", smell="blob", severities=("major",)), {PRIMARY_VARIANT: True}),
        Prediction(
            make_sample("2", smell="data class", severities=("major",)), {PRIMARY_VARIANT: True}
        ),
    ]
    assert score(predictions, "blob", PRIMARY_VARIANT).total == 1


def test_an_unresolved_disagreement_is_dropped_not_counted_as_clean() -> None:
    """Under UNANIMOUS a split review has no label, and inventing one would
    move a real disagreement into the negative class."""
    split = Prediction(make_sample("1", severities=("none", "major")), {PRIMARY_VARIANT: True})
    agreed = Prediction(make_sample("2", severities=("major", "major")), {PRIMARY_VARIANT: True})
    assert score([split, agreed], "blob", PRIMARY_VARIANT, Aggregation.UNANIMOUS).total == 1
    # Under the mean, the split sample rounds up to "minor" and is scored.
    assert score([split, agreed], "blob", PRIMARY_VARIANT, Aggregation.MEAN).total == 2


def test_recall_by_severity_splits_the_catches() -> None:
    """Two critical samples, both caught; two minor, one caught.

    critical: 2/2 = 1.0, minor: 1/2 = 0.5. "none" is not a severity to recall.
    """
    predictions = [
        Prediction(make_sample("1", severities=("critical",)), {PRIMARY_VARIANT: True}),
        Prediction(make_sample("2", severities=("critical",)), {PRIMARY_VARIANT: True}),
        Prediction(make_sample("3", severities=("minor",)), {PRIMARY_VARIANT: True}),
        Prediction(make_sample("4", severities=("minor",)), {PRIMARY_VARIANT: False}),
        Prediction(make_sample("5", severities=("none",)), {PRIMARY_VARIANT: False}),
    ]
    table = recall_by_severity(predictions, "blob", PRIMARY_VARIANT)
    assert table["critical"] == {"support": 2, "caught": 2, "recall": 1.0}
    assert table["minor"] == {"support": 2, "caught": 1, "recall": 0.5}
    assert "none" not in table


# ----------------------------------------------------------------------
# The mapping decided in VD-22
# ----------------------------------------------------------------------


def test_every_mlcq_smell_has_a_primary_variant() -> None:
    for smell, variants in VARIANTS.items():
        assert PRIMARY_VARIANT in variants, smell


def test_only_blob_carries_a_size_variant() -> None:
    """VD-22: Large Class is reported alongside God Class for blob only.

    The other three map one-to-one, Brain Method included: its LOC > 35 makes
    it a strict subset of Long Method's LOC > 30, so a union would change
    nothing.
    """
    assert VARIANTS["blob"]["with_size"] == ("GodClass", "LargeClass")
    assert [s for s, v in VARIANTS.items() if len(v) > 1] == ["blob"]


# ----------------------------------------------------------------------
# The CSV verdict contract
# ----------------------------------------------------------------------


def test_a_verdict_survives_a_round_trip_through_the_csv():
    assert decode_verdict(encode_verdict(True)) is True
    assert decode_verdict(encode_verdict(False)) is False


def test_both_spellings_of_a_verdict_are_understood():
    """The file holds "1"/"0"; a reader that assumed str(bool) must still work."""
    assert decode_verdict("1") is True
    assert decode_verdict("True") is True
    assert decode_verdict("0") is False
    assert decode_verdict("False") is False


def test_an_unrecognised_verdict_stops_the_run():
    """Silently reading it as False would report that no detector ever fired.

    That is the failure mode this pair exists to prevent: a comparison table of
    zeros looks like a result, not like a bug.
    """
    with pytest.raises(ValueError, match="not a detector verdict"):
        decode_verdict("yes")


def test_weighted_kappa_matches_a_matrix_worked_out_by_hand() -> None:
    """Four ratings on the three-level scale, kappa derived on paper.

    Pairs (reviewers, ours): (minor, minor), (minor, major), (major, major),
    (critical, critical).

    Counts, rows = reviewers, columns = ours:

        minor    [1, 1, 0]
        major    [0, 1, 0]
        critical [0, 0, 1]

    Row marginals 0.50 / 0.25 / 0.25, column marginals 0.25 / 0.50 / 0.25.
    Quadratic weights w(i,j) = (i-j)^2 / 4, so w = 0, 0.25 or 1.

    Observed disagreement = (0.25 * 1) / 4 = 0.0625.
    Expected disagreement, summing w(i,j) * row_i * col_j over the six cells
    with non-zero weight:
        0.25*0.50*0.50 + 1*0.50*0.25 + 0.25*0.25*0.25
      + 0.25*0.25*0.25 + 1*0.25*0.25 + 0.25*0.25*0.50
      = 0.0625 + 0.125 + 0.015625 + 0.015625 + 0.0625 + 0.03125 = 0.3125.

    kappa = 1 - 0.0625 / 0.3125 = 0.8.
    """
    pairs = [
        ("minor", "minor"),
        ("minor", "major"),
        ("major", "major"),
        ("critical", "critical"),
    ]
    assert weighted_kappa(pairs) == pytest.approx(0.8)


def test_a_two_step_miss_costs_more_than_two_one_step_misses() -> None:
    """The reason for quadratic weights, stated as a test.

    Plain kappa cannot tell these apart; here calling one minor case critical
    must score worse than calling two minor cases major.
    """
    far = weighted_kappa([("minor", "critical"), ("major", "major"), ("critical", "critical")])
    near = weighted_kappa([("minor", "major"), ("major", "major"), ("critical", "critical")])
    assert far is not None and near is not None
    assert far < near


def test_kappa_is_undefined_when_every_rating_lands_in_one_cell() -> None:
    """No variation means no expected disagreement, and 1 - 0/0 is not zero."""
    assert weighted_kappa([("major", "major"), ("major", "major")]) is None


def test_severity_is_compared_only_where_both_sides_see_a_smell() -> None:
    """Three of five pairs are comparable.

    Counted: the two where the detector fired and the reviewers called it a
    smell. Dropped: the sample the detector missed (no severity of ours to
    compare), the one the reviewers labelled `none` (a false positive, which is
    a recall question and not a severity one), and the one of another smell.
    """
    predictions = [
        Prediction(
            make_sample("1", severities=("major",)),
            {PRIMARY_VARIANT: True},
            {PRIMARY_VARIANT: "major"},
        ),
        Prediction(
            make_sample("2", severities=("minor",)),
            {PRIMARY_VARIANT: True},
            {PRIMARY_VARIANT: "critical"},
        ),
        Prediction(
            make_sample("3", severities=("major",)),
            {PRIMARY_VARIANT: False},
            {PRIMARY_VARIANT: None},
        ),
        Prediction(
            make_sample("4", severities=("none",)),
            {PRIMARY_VARIANT: True},
            {PRIMARY_VARIANT: "minor"},
        ),
        Prediction(
            make_sample("5", smell="data class", severities=("major",)),
            {PRIMARY_VARIANT: True},
            {PRIMARY_VARIANT: "minor"},
        ),
    ]
    agreement = severity_agreement(predictions, "blob", PRIMARY_VARIANT)

    assert agreement.n == 2
    assert agreement.exact == pytest.approx(0.5)  # one of the two matches exactly
    assert agreement.within_one == pytest.approx(0.5)  # minor vs critical is two steps
    assert agreement.matrix["major"]["major"] == 1
    assert agreement.matrix["minor"]["critical"] == 1


def test_severity_agreement_reports_a_gap_when_nothing_is_comparable() -> None:
    missed = Prediction(
        make_sample("1", severities=("major",)),
        {PRIMARY_VARIANT: False},
        {PRIMARY_VARIANT: None},
    )
    agreement = severity_agreement([missed], "blob", PRIMARY_VARIANT)
    assert agreement.n == 0
    assert (agreement.exact, agreement.within_one, agreement.kappa) == (None, None, None)


def test_the_severity_cutoffs_can_be_moved() -> None:
    """VD-06 promised these would be swept, which needs them to be parameters.

    A condition measured at 3x the threshold scores 3.0, which is critical at the
    published cutoffs (>= 2.5) and merely major once the cutoff moves past it.
    """
    smell = Smell(
        smell_type="GodClass",
        scope="class",
        class_name="Ledger",
        package="com.acme",
        file_path="Ledger.java",
        start_line=1,
        end_line=9,
        conditions=[Condition("WMC", ">=", 10.0, 30.0)],
        refactorings=[],
    )
    assert smell.score == pytest.approx(3.0)
    assert smell.severity.value == "critical"
    assert smell.severity_at(replace(DEFAULT, severity_critical=4.0)).value == "major"
