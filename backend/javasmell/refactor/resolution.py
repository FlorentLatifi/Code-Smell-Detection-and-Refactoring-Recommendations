"""Did the rewrite remove the smell it was applied for?

``verify.py`` asks whether the rewrite broke the file. This asks the other half
of the question, and the two are independent: a transformation can be correct,
compile, and leave the smell exactly where it was.

That is not hypothetical, and it follows from the transformations themselves:

* **Guard Clauses** removes one level of nesting, while Deep Nesting fires above
  three. A method nested four deep is cured; one nested six is still over the
  bound after a perfectly correct rewrite.
* **Extract Method** lifts the largest block out of a long method. That shortens
  it, with no guarantee of crossing back under the threshold.
* **Introduce Parameter Object** resolves by construction, because the parameter
  list becomes one parameter.

So "the engine applied it and it compiles" says nothing about whether it helped.
Measuring the difference is the point of this module, and the answer belongs in
the results next to the refusal reasons: a transformation that never resolves is
as much a limitation as one that never applies.

The entity is found again by **name**, not by line, because the rewrite moves
lines: Introduce Parameter Object inserts a class above the method it changes.
Where a name is ambiguous -- two classes, or an overloaded method -- the answer
is ``UNKNOWN`` rather than a guess, on the same principle the transformations
themselves refuse under.
"""

from __future__ import annotations

from enum import StrEnum

from javasmell.analysis import analyze_source
from javasmell.detectors.rules import detect_entity
from javasmell.detectors.thresholds import DEFAULT, Thresholds


class Resolution(StrEnum):
    """What the rewrite did to the smell it targeted."""

    #: The detector no longer fires at that entity.
    RESOLVED = "resolved"

    #: The rewrite was applied and the smell is still there.
    PERSISTS = "persists"

    #: The entity could not be identified unambiguously after the rewrite.
    UNKNOWN = "unknown"


def resolves(
    rewritten: bytes,
    class_name: str,
    method: str | None,
    smell_type: str,
    thresholds: Thresholds = DEFAULT,
) -> Resolution:
    """Re-measure the rewritten text and ask whether the smell still fires."""
    text = rewritten.decode("utf-8", errors="replace")
    project = analyze_source(text)

    classes = [cls for unit in project.units for cls in unit.classes if cls.name == class_name]
    if len(classes) != 1:
        return Resolution.UNKNOWN
    target = classes[0]

    if method is None:
        found = detect_entity(target, None, thresholds)
    else:
        overloads = [m for m in target.methods if m.name == method]
        if len(overloads) != 1:
            return Resolution.UNKNOWN
        found = detect_entity(target, overloads[0], thresholds)

    return (
        Resolution.PERSISTS
        if any(smell.smell_type == smell_type for smell in found)
        else Resolution.RESOLVED
    )
