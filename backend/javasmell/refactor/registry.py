"""Which transformation the engine can actually run for a given smell.

``detectors.rules.REFACTORINGS`` lists what Fowler would *advise* for each smell.
This is the narrower list of what the engine will *do*, and the gap between the
two is deliberate: Encapsulate Field and Move Method both need to find every
reference in the project, which the parser cannot prove because it is not a
symbol resolver (VD-30). They stay as advice and are never applied.

The mapping is one smell to one transformation. A smell with several applicable
transformations would need a rule for choosing between them, and there is no
second case yet to derive that rule from.
"""

from __future__ import annotations

from collections.abc import Callable

from javasmell.refactor import extract_method, guard_clauses
from javasmell.refactor.base import Outcome
from javasmell.refactor.locate import Site

Transformation = Callable[[Site], Outcome]

# Keyed by the smell_type a detector emits, valued by the refactoring name from
# the REFACTORINGS contract and the function that performs it.
AUTOMATED: dict[str, tuple[str, Transformation]] = {
    "DeepNesting": (guard_clauses.NAME, guard_clauses.apply),
    "LongMethod": (extract_method.NAME, extract_method.apply),
    "BrainMethod": (extract_method.NAME, extract_method.apply),
}

# Advised by the detectors, never applied. Kept here so the reason travels with
# the decision rather than living only in the log.
ADVISORY_ONLY = {
    "DataClass": "every reference to the field would have to be found and rewritten",
    "GodClass": "moving members needs call sites this analysis cannot resolve",
    "LargeClass": "moving members needs call sites this analysis cannot resolve",
    "FeatureEnvy": "moving a method needs every call site",
    "LongParameterList": "changing a signature needs every call site",
}


def for_smell(smell_type: str) -> tuple[str, Transformation] | None:
    """The transformation to run, or None when the smell is advisory only."""
    return AUTOMATED.get(smell_type)
