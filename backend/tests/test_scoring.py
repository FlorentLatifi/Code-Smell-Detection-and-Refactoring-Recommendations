"""Tests for the evaluation scoring.

Every matrix below is worked out on paper first and the arithmetic is written
next to the assertion. These are the figures the Results chapter reports, so a
value captured from a previous run would prove only that the formula has not
changed, not that it was ever right.
"""

from __future__ import annotations

import math

import pytest

from javasmell.detectors.base import Condition, Smell
from javasmell.evaluation.mlcq import Aggregation, Review, Sample
from javasmell.evaluation.scoring import (
    PRIMARY_VARIANT,
    VARIANTS,
    Confusion,
    Prediction,
    SmellIndex,
    confusion,
    recall_by_severity,
    score,
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
