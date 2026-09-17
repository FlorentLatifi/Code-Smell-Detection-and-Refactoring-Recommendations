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

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

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

    #: A value the block reads is declared but not yet certainly assigned where
    #: the block sits. Java forbids passing such a variable, so the rewrite would
    #: not compile even though it is otherwise correct.
    NOT_DEFINITELY_ASSIGNED = "not_definitely_assigned"

    #: The file did not parse cleanly, so nothing about it is established.
    UNPARSEABLE = "unparseable"


@dataclass(frozen=True)
class Note:
    """Something true about an applied rewrite, in a form a caller can translate.

    A code and its numbers, never a sentence. The interface writes Albanian and
    the package writes English, and this project has already paid once for
    sending prose across that line: "the path does not exist" appeared in the
    middle of an Albanian screen until the error codes were given a translation
    table. A note is the same kind of text and takes the same shape (VD-97).
    """

    code: str
    values: Mapping[str, float | str] = field(default_factory=dict)


#: Every refusal detail as a code, with the English sentence it has always been.
#:
#: The sentence was all there was, and the interface showed it in English in the
#: middle of an Albanian screen. The code is what now crosses to the interface;
#: the sentence is what the corpus tables and the terminal print, kept word for
#: word so that no committed result changes (VD-123). A placeholder names a value
#: the sentence carries, and the note supplies it.
DETAILS: Mapping[str, str] = MappingProxyType(
    {
        # Guard Clauses
        "needs_void": "a non-void method needs a return value",
        "no_body": "no body to rewrite",
        "not_single_conditional": "the body is not a single conditional",
        "has_else": "the conditional has an else branch",
        "branch_not_block": "the branch is not a block",
        "branch_empty": "the branch is empty",
        "no_condition": "the conditional has no condition",
        "irregular_indent": "the branch is not indented one level past the conditional",
        # Introduce Parameter Object
        "not_method": "not a method declaration",
        "not_private": "not private, so the call sites are not local",
        "generic_method": "generic method",
        "nested_enclosing_type": "enclosing type is not a top-level class",
        "no_parameter_list": "no parameter list",
        "varargs_or_annotated": "varargs or annotated parameter",
        "too_few_parameters": "only {count} parameter(s)",
        "overloaded": "more than one method named {name}",
        "unresolvable_reference": "a reference that cannot be tied to the method",
        # Extract Method
        "constructor": "a constructor has no return type to give back",
        "no_body_to_extract": "no body to extract from",
        "no_large_block": "no top-level block of at least {lines} lines",
        "escaping_statement": "the block contains a {statement}",
        "not_assigned": "{names} may not be assigned yet",
        "several_outputs": "{count} values flow out: {names}",
        "untyped_names": "no declared type for {names}",
        "type_parameters": "the method declares type parameters",
        # The planner, before any transformation is asked
        "entity_not_found": "the entity was not found at that line",
    }
)


def explain(code: str, **values: float | str) -> Note:
    """A refusal detail as a code and its values.

    Raises for a code :data:`DETAILS` does not know, and for a missing value, so a
    new refusal cannot reach a caller without a sentence to fall back on.
    """
    DETAILS[code].format(**values)
    return Note(code, values)


def sentence(note: Note) -> str:
    """The English sentence a refusal detail has always been."""
    return DETAILS[note.code].format(**note.values)


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
    #: Declarations this rewrite adds to the file, by name. A transformation
    #: that invents a name picks one that is free *in the source it was handed*,
    #: and two rewrites of the same file are both handed the same source: each
    #: would pick the same free name and the file would then declare it twice.
    #: Reporting the name lets the caller reserve it for the next site.
    introduced: tuple[str, ...] = ()
    #: True things about an applied rewrite that are not reasons to refuse it.
    #: A note never blocks the change; it tells the author something they would
    #: want to know before taking it, which is the whole posture of an engine
    #: that proposes rather than applies (VD-97).
    notes: tuple[Note, ...] = ()
    #: The refusal detail as a code and its values, when the transformation gave
    #: one. ``detail`` is the same thing as an English sentence.
    explanation: Note | None = None

    @property
    def applied(self) -> bool:
        return self.refusal is None

    @classmethod
    def rewrite(
        cls,
        refactoring: str,
        file_path: str,
        target: str,
        edits: tuple[Edit, ...],
        introduced: tuple[str, ...] = (),
        notes: tuple[Note, ...] = (),
    ) -> Outcome:
        if not edits:
            raise ValueError(f"{refactoring} claimed to apply at {target} with no edits")
        return cls(
            refactoring=refactoring,
            file_path=file_path,
            target=target,
            edits=edits,
            introduced=introduced,
            notes=notes,
        )

    @classmethod
    def refuse(
        cls,
        refactoring: str,
        file_path: str,
        target: str,
        refusal: Refusal,
        detail: str | Note = "",
    ) -> Outcome:
        explanation = detail if isinstance(detail, Note) else None
        return cls(
            refactoring=refactoring,
            file_path=file_path,
            target=target,
            refusal=refusal,
            detail=detail if isinstance(detail, str) else sentence(detail),
            explanation=explanation,
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
