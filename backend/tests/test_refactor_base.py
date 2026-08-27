"""Tests for the outcome and refusal contract.

The engine's central claim is that declining is a correct result, so these check
that a decline carries a reason that can be counted, and that "applied" cannot be
claimed without an actual change.
"""

from __future__ import annotations

import pytest

from javasmell.refactor.base import Outcome, Refusal, Tally
from javasmell.refactor.edits import Edit


def rewrite(target: str = "Ledger.post") -> Outcome:
    return Outcome.rewrite("ExtractMethod", "Ledger.java", target, (Edit(0, 1, b"x"),))


def decline(reason: Refusal = Refusal.UNRESOLVED_NAME, target: str = "Ledger.post") -> Outcome:
    return Outcome.refuse("ExtractMethod", "Ledger.java", target, reason, "totals")


def test_applied_means_no_refusal():
    assert rewrite().applied
    assert not decline().applied


def test_claiming_to_apply_without_editing_is_rejected():
    """Otherwise the tally would count a change that never reached the file."""
    with pytest.raises(ValueError, match="with no edits"):
        Outcome.rewrite("ExtractMethod", "Ledger.java", "Ledger.post", ())


def test_a_refusal_carries_a_countable_reason():
    """Free text would not aggregate into the table the thesis reports."""
    outcome = decline(Refusal.CONTROL_FLOW_ESCAPES)
    assert outcome.refusal is Refusal.CONTROL_FLOW_ESCAPES
    assert outcome.refusal in Refusal
    assert "control_flow_escapes" in outcome.describe()


def test_tally_separates_applied_from_declined():
    """3 sites: one rewritten, two declined for different reasons."""
    tally = Tally()
    tally.record(rewrite())
    tally.record(decline(Refusal.UNRESOLVED_NAME))
    tally.record(decline(Refusal.MULTIPLE_OUTPUTS))

    assert tally.detected == 3
    assert tally.applied == 1
    assert tally.refused == 2
    assert tally.refused_by_reason == {
        Refusal.UNRESOLVED_NAME: 1,
        Refusal.MULTIPLE_OUTPUTS: 1,
    }


def test_tally_counts_repeats_of_one_reason():
    tally = Tally()
    for _ in range(4):
        tally.record(decline(Refusal.POSSIBLE_SIDE_EFFECT))
    assert tally.refused_by_reason == {Refusal.POSSIBLE_SIDE_EFFECT: 4}
    assert tally.applied == 0


def test_an_empty_tally_does_not_divide_by_zero():
    assert "0/0" in Tally().describe()


def test_describe_states_the_share_applied():
    """1 of 4 is 25.0%."""
    tally = Tally()
    tally.record(rewrite())
    for _ in range(3):
        tally.record(decline())
    assert "1/4 applied (25.0%)" in tally.describe()
