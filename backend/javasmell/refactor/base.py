"""What a transformation reports back: a rewrite, or a refusal with a reason.

The engine's contract is that it refuses rather than corrupts. A transformation
declares what must be true of the code, and if any of it cannot be *proven* from
the parse tree -- a name it cannot resolve, a call that might have side effects,
an overload it cannot disambiguate -- it declines and says which. Declining is a
correct outcome, not an error: the thesis reports *N detected, M transformed, K
behaviour-preserving*, and the distribution of refusal reasons is a result in its
own right rather than a list of bugs.

That is why :class:`Refusal` is an enumeration and not a string. The reasons have
to aggregate into a table, and free text does not aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from javasmell.refactor.edits import Edit


class Refusal(StrEnum):
    """Why a transformation declined to touch a site.

    Each value names something the parse tree could not establish. The set grows
    only when a transformation needs a reason that is genuinely new; reusing a
    near-miss would blur the very table this exists to produce.
    """

    #: A name whose declaration this analysis cannot find. The parser records
    #: syntactic facts and is deliberately not a symbol resolver (see the
    #: architecture note in parsing/), so this is expected and common.
    UNRESOLVED_NAME = "unresolved_name"

    #: Moving or reordering the code could change behaviour, because something
    #: in it may write state or perform I/O.
    POSSIBLE_SIDE_EFFECT = "possible_side_effect"

    #: Several methods share the name and the call cannot be tied to one.
    AMBIGUOUS_OVERLOAD = "ambiguous_overload"

    #: The block assigns more than one variable that is read afterwards, so a
    #: single return value cannot carry the result out.
    MULTIPLE_OUTPUTS = "multiple_outputs"

    #: A return, break or continue inside the block leaves it, so the block is
    #: not an expression and cannot be lifted whole.
    CONTROL_FLOW_ESCAPES = "control_flow_escapes"

    #: The code does not have the shape this transformation rewrites. Not a
    #: failure of analysis: simply the wrong tool for this site.
    SHAPE_NOT_MATCHED = "shape_not_matched"

    #: Two edits claimed the same bytes. Always a defect in the transformation
    #: that produced them, and reported so it cannot pass unnoticed.
    EDIT_CONFLICT = "edit_conflict"

    #: The file did not parse cleanly, so nothing about it is established.
    UNPARSEABLE = "unparseable"


@dataclass(frozen=True)
class Outcome:
    """One transformation's verdict at one site.

    Construct through :meth:`rewrite` or :meth:`refuse` rather than directly, so
    that "applied with no edits" -- which would report a change that did not
    happen -- cannot be expressed.
    """

    refactoring: str
    file_path: str
    target: str
    edits: tuple[Edit, ...] = ()
    refusal: Refusal | None = None
    detail: str = ""

    @property
    def applied(self) -> bool:
        return self.refusal is None

    @classmethod
    def rewrite(
        cls, refactoring: str, file_path: str, target: str, edits: tuple[Edit, ...]
    ) -> Outcome:
        if not edits:
            raise ValueError(f"{refactoring} claimed to apply at {target} with no edits")
        return cls(refactoring=refactoring, file_path=file_path, target=target, edits=edits)

    @classmethod
    def refuse(
        cls, refactoring: str, file_path: str, target: str, refusal: Refusal, detail: str = ""
    ) -> Outcome:
        return cls(
            refactoring=refactoring,
            file_path=file_path,
            target=target,
            refusal=refusal,
            detail=detail,
        )

    def describe(self) -> str:
        if self.applied:
            return f"{self.refactoring} at {self.target}: {len(self.edits)} edit(s)"
        suffix = f" ({self.detail})" if self.detail else ""
        return f"{self.refactoring} at {self.target}: declined, {self.refusal}{suffix}"


@dataclass
class Tally:
    """How a run of the engine came out, in the shape the thesis reports it.

    Counted rather than derived at the end because a run over the corpus streams
    its sites and never holds them all at once.
    """

    detected: int = 0
    applied: int = 0
    missing: int = 0
    refused_by_reason: dict[Refusal, int] = field(default_factory=dict)

    def record(self, outcome: Outcome) -> None:
        self.detected += 1
        reason = outcome.refusal
        if reason is None:
            self.applied += 1
            return
        self.refused_by_reason[reason] = self.refused_by_reason.get(reason, 0) + 1

    def record_missing(self) -> None:
        """A site the detector found but a fresh parse could not locate.

        Kept apart from the refusals because it is not one: the transformation
        was never consulted. It happens when the file changed between being
        measured and being rewritten, and counting it as a decline would credit
        the engine with caution it never exercised.
        """
        self.detected += 1
        self.missing += 1

    @property
    def refused(self) -> int:
        return sum(self.refused_by_reason.values())

    def describe(self) -> str:
        share = self.applied / self.detected if self.detected else 0.0
        tail = f", {self.missing} unlocatable" if self.missing else ""
        return (
            f"{self.applied}/{self.detected} applied ({share:.1%}), {self.refused} declined{tail}"
        )
