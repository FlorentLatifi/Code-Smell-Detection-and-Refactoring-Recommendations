"""Tests for the bootstrap intervals.

Every expected value below is worked out on paper. A resampling routine is easy
to write in a way that looks right and is wrong -- resampling rows instead of
groups, or reading an undefined score as zero -- and both mistakes produce
plausible numbers rather than errors, so the cases here pin the properties that
would catch them.
"""

from __future__ import annotations

import numpy as np
import pytest

from javasmell.evaluation.intervals import (
    Interval,
    draw,
    group_positions,
    mcc,
    percentile_interval,
    resample,
)


def test_group_positions_keeps_every_row_with_its_repository():
    groups = ["a", "b", "a", "c", "b", "a"]

    found = group_positions(groups)

    # Rows 0, 2 and 5 are the "a" rows, in the order they appear.
    assert found["a"].tolist() == [0, 2, 5]
    assert found["b"].tolist() == [1, 4]
    assert found["c"].tolist() == [3]


def test_a_draw_takes_whole_repositories_or_none_of_one():
    """The property that separates this from resampling rows.

    Repository "a" owns rows {0, 1, 2}. However many times it is drawn, its rows
    must appear together in complete copies; a draw containing row 0 without
    rows 1 and 2 would mean the grouping had been broken.
    """
    groups = ["a", "a", "a", "b", "b"]
    positions = group_positions(groups)
    names = ("a", "b")
    rng = np.random.default_rng(0)

    for _ in range(50):
        rows = draw(names, positions, rng).tolist()
        assert rows.count(0) == rows.count(1) == rows.count(2)
        assert rows.count(3) == rows.count(4)
        # Two repositories are drawn each time, so the draw holds two blocks.
        assert rows.count(0) + rows.count(3) == 2


def test_a_draw_is_as_large_as_the_set_when_repositories_are_equal_sized():
    groups = ["a", "a", "b", "b", "c", "c"]
    positions = group_positions(groups)
    rng = np.random.default_rng(1)

    rows = draw(("a", "b", "c"), positions, rng)

    # Three repositories drawn, two rows each: six rows, as in the original.
    assert len(rows) == 6


def test_percentile_interval_on_a_hand_worked_list():
    # 0.0 through 1.0 in steps of 0.01: 101 values. numpy interpolates linearly
    # between order statistics, and for this evenly spaced list the 2.5th
    # percentile lands on 0.025 and the 97.5th on 0.975.
    values = [index / 100 for index in range(101)]

    band = percentile_interval(values)

    assert band.low == pytest.approx(0.025)
    assert band.high == pytest.approx(0.975)
    assert band.median == pytest.approx(0.5)
    assert band.resamples_used == 101


def test_excludes_zero_reads_both_directions_and_the_straddle():
    assert Interval(0.1, 0.4, 0.25, 10).excludes_zero
    assert Interval(-0.4, -0.1, -0.25, 10).excludes_zero
    # The case the chapter has to report as indistinguishable.
    assert not Interval(-0.02, 0.06, 0.02, 10).excludes_zero


def test_mcc_matches_the_hand_computed_value():
    truth = np.array([True, True, False, False], dtype=np.bool_)
    predicted = np.array([True, False, False, False], dtype=np.bool_)

    # tp=1, fn=1, tn=2, fp=0.
    # (1*2 - 0*1) / sqrt(1 * 2 * 2 * 3) = 2 / sqrt(12) = 0.5773502692
    assert mcc(truth, predicted) == pytest.approx(0.5773502692, abs=1e-9)


def test_identical_predictors_differ_by_exactly_zero_in_every_draw():
    """The sharpest available check that the pairing is real.

    Both predictors see the same draw, so their difference is zero whatever the
    draw is. An implementation that resampled each predictor separately would
    produce a spread here instead of a point.
    """
    truth = np.array([True, False, True, False], dtype=np.bool_)
    same = np.array([True, False, False, False], dtype=np.bool_)
    groups = ["a", "a", "b", "b"]

    result = resample(
        truth,
        {"model": same, "rules": same.copy()},
        groups,
        against=("rules",),
        resamples=64,
        seed=7,
    )

    difference = result["difference_model_minus_rules"]
    assert difference.low == 0.0
    assert difference.high == 0.0
    assert difference.share_positive == 0.0


def test_a_perfect_predictor_scores_one_in_every_usable_draw():
    truth = np.array([True, False, True, False], dtype=np.bool_)
    groups = ["a", "a", "b", "b"]

    result = resample(truth, {"model": truth.copy()}, groups, resamples=64, seed=3)

    # Each repository holds one positive and one negative, so no draw can lose a
    # class and every draw scores a perfect 1.0.
    assert result["model"].low == pytest.approx(1.0)
    assert result["model"].high == pytest.approx(1.0)
    assert result["model"].resamples_used == 64


def test_draws_with_an_undefined_score_are_dropped_not_counted_as_zero():
    """Repository "b" is all negative, so a draw of two "b" blocks has no positive.

    MCC is undefined there. Reading it as zero would pull the interval down and
    understate a predictor that never actually failed.
    """
    truth = np.array([True, False, False, False], dtype=np.bool_)
    groups = ["a", "a", "b", "b"]

    result = resample(truth, {"model": truth.copy()}, groups, resamples=200, seed=11)

    # Drawing "b" twice happens about a quarter of the time, so some draws are
    # dropped -- but every draw that counted was perfect.
    assert result["model"].resamples_used < 200
    assert result["model"].low == pytest.approx(1.0)


def test_a_comparison_against_a_missing_predictor_is_simply_absent():
    truth = np.array([True, False, True, False], dtype=np.bool_)
    groups = ["a", "a", "b", "b"]

    result = resample(
        truth,
        {"model": truth.copy()},
        groups,
        against=("rules_swept",),
        resamples=16,
        seed=1,
    )

    assert "difference_model_minus_rules_swept" not in result
