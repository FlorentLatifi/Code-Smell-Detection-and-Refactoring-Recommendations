"""What the rewrite did to the smells: removed one, moved one, or shifted a number.

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

Three things are measured, because "did it help" has three honest answers:

1. **Is the smell gone** at the entity that was rewritten.
2. **Was a new one introduced** anywhere in the enclosing class. This is the
   question Extract Method makes unavoidable: it passes every value the block
   read as a parameter, so a block with six inputs becomes a method with six
   parameters -- which is Long Parameter List, whose bound is five. A tool that
   trades one smell for another should say so.
3. **How far the measurement moved**, even when the smell survives. A method that
   falls from ninety lines to forty is better code and a worse claim; without
   this number the difference cannot be stated at all.

The entity is found again by **name**, not by line, because the rewrite moves
lines: Introduce Parameter Object inserts a class above the method it changes.
Where a name is ambiguous -- two classes, or an overloaded method -- the answer
is ``UNKNOWN`` rather than a guess, on the same principle the transformations
themselves refuse under.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from javasmell.analysis import analyze_source
from javasmell.detectors.rules import detect_entity, detect_in_class
from javasmell.detectors.thresholds import DEFAULT, Thresholds
from javasmell.model.entities import ClassInfo, MethodInfo

# The measurement each smell is really about, so a before-and-after pair can be
# reported in the unit the reader already knows from the detection strategy.
PRIMARY_METRIC = {
    "LongMethod": "MLOC",
    "BrainMethod": "MLOC",
    "DeepNesting": "MAXNESTING",
    "LongParameterList": "NP",
    "FeatureEnvy": "ATFD",
    "GodClass": "WMC",
    "LargeClass": "CLOC",
    "DataClass": "WOC",
}


class Resolution(StrEnum):
    """What the rewrite did to the smell it targeted."""

    #: The detector no longer fires at that entity.
    RESOLVED = "resolved"

    #: The rewrite was applied and the smell is still there.
    PERSISTS = "persists"

    #: The entity could not be identified unambiguously after the rewrite.
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Change:
    """The rewrite's effect on one site, in the terms the thesis reports."""

    resolution: Resolution
    introduced: tuple[str, ...]
    metric: str
    before: float | None
    after: float | None


def _entity(
    text: str, class_name: str, method: str | None
) -> tuple[ClassInfo, MethodInfo | None] | None:
    """The class, and the method inside it, or None when the name is ambiguous."""
    project = analyze_source(text)
    classes = [cls for unit in project.units for cls in unit.classes if cls.name == class_name]
    if len(classes) != 1:
        return None
    target = classes[0]
    if method is None:
        return target, None
    overloads = [m for m in target.methods if m.name == method]
    if len(overloads) != 1:
        return None
    return target, overloads[0]


def _fires(cls: ClassInfo, method: MethodInfo | None, smell_type: str, t: Thresholds) -> bool:
    return any(s.smell_type == smell_type for s in detect_entity(cls, method, t))


def _by_type(cls: ClassInfo, t: Thresholds) -> Counter[str]:
    """Every smell in the class, counted by type.

    The whole class rather than the one entity, because a transformation can add
    an entity: the method Extract Method creates is new code that nothing has
    measured yet.
    """
    return Counter(smell.smell_type for smell in detect_in_class(cls, t))


def compare(
    original: bytes,
    rewritten: bytes,
    class_name: str,
    method: str | None,
    smell_type: str,
    thresholds: Thresholds = DEFAULT,
) -> Change:
    """Measure the entity and its class on both sides of the rewrite."""
    metric = PRIMARY_METRIC.get(smell_type, "")
    before = _entity(original.decode("utf-8", errors="replace"), class_name, method)
    after = _entity(rewritten.decode("utf-8", errors="replace"), class_name, method)

    if before is None or after is None:
        return Change(Resolution.UNKNOWN, (), metric, None, None)

    before_class, before_entity = before
    after_class, after_entity = after

    was = before_entity.metrics if before_entity is not None else before_class.metrics
    now = after_entity.metrics if after_entity is not None else after_class.metrics

    counted_before = _by_type(before_class, thresholds)
    counted_after = _by_type(after_class, thresholds)
    introduced = tuple(
        sorted(name for name, count in counted_after.items() if count > counted_before[name])
    )

    resolution = (
        Resolution.PERSISTS
        if _fires(after_class, after_entity, smell_type, thresholds)
        else Resolution.RESOLVED
    )
    return Change(resolution, introduced, metric, was.get(metric), now.get(metric))


def resolves(
    rewritten: bytes,
    class_name: str,
    method: str | None,
    smell_type: str,
    thresholds: Thresholds = DEFAULT,
) -> Resolution:
    """Whether the smell survived, for callers that need nothing else."""
    entity = _entity(rewritten.decode("utf-8", errors="replace"), class_name, method)
    if entity is None:
        return Resolution.UNKNOWN
    cls, target = entity
    return (
        Resolution.PERSISTS if _fires(cls, target, smell_type, thresholds) else Resolution.RESOLVED
    )
