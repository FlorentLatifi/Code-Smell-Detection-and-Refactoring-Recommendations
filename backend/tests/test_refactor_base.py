"""Tests for the outcome and refusal contract.

The engine's central claim is that declining is a correct result, so these check
that a decline carries a reason that can be counted, and that "applied" cannot be
claimed without an actual change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from javasmell.refactor import base
from javasmell.refactor.base import DETAILS, Note, Outcome, Refusal, Tally, explain
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


# ----------------------------------------------------------------------
# Refusal details as codes (VD-123)
# ----------------------------------------------------------------------
#: Kept by hand, and copied by `frontend/src/api.test.ts`: a new code breaks one
#: test on each side instead of reaching the screen in English.
DETAIL_CODES = {
    "needs_void",
    "no_body",
    "not_single_conditional",
    "has_else",
    "branch_not_block",
    "branch_empty",
    "no_condition",
    "irregular_indent",
    "not_method",
    "not_private",
    "generic_method",
    "nested_enclosing_type",
    "no_parameter_list",
    "varargs_or_annotated",
    "too_few_parameters",
    "overloaded",
    "unresolvable_reference",
    "constructor",
    "no_body_to_extract",
    "no_large_block",
    "escaping_statement",
    "not_assigned",
    "several_outputs",
    "untyped_names",
    "type_parameters",
    "entity_not_found",
}


def test_every_detail_code_is_one_the_interface_knows():
    assert set(DETAILS) == DETAIL_CODES


def test_a_coded_refusal_keeps_the_sentence_it_always_had():
    """The corpus tables read `detail`; a code must not change a word of it."""
    outcome = Outcome.refuse(
        "ExtractMethod",
        "Ledger.java",
        "Ledger.post",
        Refusal.MULTIPLE_OUTPUTS,
        explain("several_outputs", count=2, names="a, b"),
    )

    assert outcome.detail == "2 values flow out: a, b"
    assert outcome.explanation == Note("several_outputs", {"count": 2, "names": "a, b"})


def test_a_plain_sentence_still_refuses_without_a_code():
    assert decline().explanation is None
    assert decline().detail == "totals"


def test_an_unknown_code_or_a_missing_value_is_refused_at_once():
    """Caught where the refusal is built, not where a caller first reads it."""
    with pytest.raises(KeyError):
        explain("no_such_reason")
    with pytest.raises(KeyError):
        explain("overloaded")


def test_every_transformation_refuses_through_a_code():
    """A bare sentence in a transformation would reach the screen untranslated."""
    package = Path(base.__file__).parent
    for module in ("guard_clauses.py", "introduce_parameter_object.py", "extract_method.py"):
        source = (package / module).read_text(encoding="utf-8")
        bare = re.findall(r"decline\(\s*Refusal\.\w+,\s*f?[\"']", source)
        assert bare == [], module
