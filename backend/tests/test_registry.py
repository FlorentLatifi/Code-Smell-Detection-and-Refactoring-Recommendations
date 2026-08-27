"""Tests for the map from smell to transformation.

The point of these is that the two lists stay honest: everything the engine
claims to automate must exist, and everything it refuses to automate must be a
smell the detectors actually emit.
"""

from __future__ import annotations

from javasmell.detectors.rules import REFACTORINGS
from javasmell.refactor.registry import ADVISORY_ONLY, AUTOMATED, for_smell


def test_every_automated_smell_is_one_the_detectors_emit():
    """A key that no detector produces would be dead code pretending to be coverage."""
    assert set(AUTOMATED) <= set(REFACTORINGS)


def test_every_advisory_smell_is_one_the_detectors_emit():
    assert set(ADVISORY_ONLY) <= set(REFACTORINGS)


def test_the_two_lists_do_not_overlap():
    """A smell is either applied or advised, never described as both."""
    assert not set(AUTOMATED) & set(ADVISORY_ONLY)


def test_together_they_account_for_every_smell():
    """No smell may fall through unexplained; silence would read as an oversight."""
    assert set(AUTOMATED) | set(ADVISORY_ONLY) == set(REFACTORINGS)


def test_the_named_refactoring_is_one_the_detector_advises():
    """The engine must not run a transformation the detector never suggested."""
    for smell, (refactoring, _) in AUTOMATED.items():
        assert refactoring in REFACTORINGS[smell], f"{refactoring} not advised for {smell}"


def test_an_advisory_smell_has_no_transformation():
    assert for_smell("DataClass") is None
    assert for_smell("FeatureEnvy") is None


def test_an_automated_smell_returns_something_callable():
    found = for_smell("LongMethod")
    assert found is not None
    name, transform = found
    assert name == "ExtractMethod"
    assert callable(transform)


def test_every_advisory_entry_says_why():
    for smell, reason in ADVISORY_ONLY.items():
        assert reason.strip(), f"{smell} is refused without a reason"
