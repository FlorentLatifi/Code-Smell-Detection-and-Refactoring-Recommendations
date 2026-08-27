"""Extract Method (Fowler, *Refactoring* 2nd ed.).

Lifts one compound statement out of an over-long method into a method of its own
and leaves a call in its place. Before::

    void process(int[] orders) {
        int total = 0;
        for (int i = 0; i < orders.length; i++) {
            total += orders[i];
        }
        report(total);
    }

After::

    void process(int[] orders) {
        int total = 0;
        total = extracted(orders, total);
        report(total);
    }

    private int extracted(int[] orders, int total) {
        for (int i = 0; i < orders.length; i++) {
            total += orders[i];
        }
        return total;
    }

**Which statement is chosen.** The largest compound statement at the top level of
the method body, measured in lines. The choice is mechanical on purpose: its
boundaries come from the syntax rather than from a heuristic about where a human
would cut, so the same input always yields the same extraction and the result is
reproducible by anyone re-running the experiment.

**What is refused.** Everything the parse tree cannot settle. Control flow that
leaves the block, more than one value flowing out, a name whose declared type is
not visible, a constructor. The engine's claim is that what it applies is
correct, not that it applies often, and the distribution of these refusals is a
reported result rather than a list of defects (VD-28).

**On the name.** The new method is called ``extracted``. Fowler names by intent,
which requires understanding what the code is *for*, and nothing in a parse tree
carries that. Inventing a plausible-sounding name would be the one part of this
transformation that is a guess, so the tool supplies structure and leaves the
vocabulary to the author.
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from javasmell.refactor.base import Outcome, Refusal
from javasmell.refactor.dataflow import (
    declarations_in,
    escaping_control_flow,
    names_read,
    names_written,
    span_of,
    text_of,
    walk,
)
from javasmell.refactor.edits import Edit, indent_at
from javasmell.refactor.locate import Site

NAME = "ExtractMethod"

# Statements worth lifting whole. A bare expression statement is excluded: a
# method built to hold one call is noise, not structure.
EXTRACTABLE = frozenset(
    {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "try_statement",
        "switch_expression",
        "switch_statement",
        "synchronized_statement",
        "block",
    }
)

# Below this the extraction trades one problem for two: a method too small to
# name and a call site that hides nothing. Measured in lines rather than in
# statements, because what a Long Method needs is fewer lines, and a loop whose
# body is a single line is still five lines of the enclosing method.
MINIMUM_LINES = 5

BASE_NAME = "extracted"


@dataclass(frozen=True)
class Plan:
    """What crosses the boundary, once the block is known to be extractable."""

    statement: Node
    inputs: tuple[str, ...]
    output: str | None
    types: dict[str, str]

    @property
    def return_type(self) -> str:
        return "void" if self.output is None else self.types[self.output]


def _line_span(node: Node) -> int:
    return node.end_point[0] - node.start_point[0] + 1


def _largest_candidate(body: Node) -> Node | None:
    """The top-level compound statement spanning the most lines.

    Ties break on position so the choice does not depend on iteration order --
    two blocks of equal size must not produce different output on two runs.
    """
    candidates = [
        child
        for child in body.named_children
        if child.type in EXTRACTABLE and _line_span(child) >= MINIMUM_LINES
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda n: (_line_span(n), -n.start_byte))


def _existing_names(enclosing_type: Node, source: bytes) -> set[str]:
    names: set[str] = set()
    for node in walk(enclosing_type):
        if node.type in {"method_declaration", "field_declaration", "constructor_declaration"}:
            named = node.child_by_field_name("name")
            if named is not None:
                names.add(text_of(named, source))
    return names


def _free_name(taken: set[str]) -> str:
    if BASE_NAME not in taken:
        return BASE_NAME
    suffix = 2
    while f"{BASE_NAME}{suffix}" in taken:
        suffix += 1
    return f"{BASE_NAME}{suffix}"


def _plan(method: Node, statement: Node, source: bytes) -> Plan | str:
    """Work out the boundary, or return the reason it cannot be crossed."""
    body = method.child_by_field_name("body")
    if body is None:
        return "no body"

    chosen = span_of(statement)
    siblings = list(body.named_children)
    position = next(i for i, node in enumerate(siblings) if span_of(node) == chosen)
    before, after = siblings[:position], siblings[position + 1 :]

    # Declared before the block: the parameters, plus anything the earlier
    # statements introduced. Names born inside the block die with it, so they
    # never cross the boundary.
    outer = declarations_in(method.child_by_field_name("parameters") or method, source)
    for node in before:
        for name, type_text in declarations_in(node, source).types.items():
            outer.add(name, type_text)

    # Sorted, not in order of appearance: the parameter order has to be fixed by
    # something, and sorting is the only rule that cannot depend on how the tree
    # happened to be walked.
    inputs = sorted(names_read(statement, source, outer))
    written = names_written(statement, source, outer)

    read_after: set[str] = set()
    for node in after:
        read_after |= names_read(node, source, outer)
    outputs = sorted(written & read_after)

    if len(outputs) > 1:
        return f"{len(outputs)} values flow out: {', '.join(outputs)}"

    types = {name: outer.types[name] for name in [*inputs, *outputs]}
    return Plan(
        statement=statement,
        inputs=tuple(inputs),
        output=outputs[0] if outputs else None,
        types=types,
    )


def _render(
    plan: Plan, name: str, source: bytes, static: bool, indent: bytes
) -> tuple[bytes, bytes]:
    """The call that replaces the block, and the method that receives it."""
    inner = indent + b"    "
    parameters = ", ".join(f"{plan.types[n]} {n}" for n in plan.inputs)
    arguments = ", ".join(plan.inputs)

    lifted = source[plan.statement.start_byte : plan.statement.end_byte]
    tail = b"" if plan.output is None else inner + b"return " + plan.output.encode() + b";\n"

    modifiers = b"private static " if static else b"private "
    # A blank line before, none after. The insertion point sits immediately past
    # the original method's closing brace, and whatever follows it -- the next
    # member, or the end of the class -- already carries its own separation.
    definition = (
        b"\n\n"
        + indent
        + modifiers
        + plan.return_type.encode()
        + b" "
        + name.encode()
        + b"("
        + parameters.encode()
        + b") {\n"
        + inner
        + lifted
        + b"\n"
        + tail
        + indent
        + b"}"
    )

    call = name.encode() + b"(" + arguments.encode() + b");"
    if plan.output is not None:
        call = plan.output.encode() + b" = " + call
    return call, definition


def apply(site: Site) -> Outcome:
    """Rewrite the site, or decline with the reason it does not fit."""
    source = site.source
    method = site.node
    target = site.text(method.child_by_field_name("name")) or "<anonymous>"

    def decline(reason: Refusal, detail: str) -> Outcome:
        return Outcome.refuse(NAME, site.file_path, target, reason, detail)

    if method.type != "method_declaration":
        return decline(Refusal.SHAPE_NOT_MATCHED, "a constructor has no return type to give back")

    body = method.child_by_field_name("body")
    if body is None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "no body to extract from")

    statement = _largest_candidate(body)
    if statement is None:
        return decline(
            Refusal.SHAPE_NOT_MATCHED,
            f"no top-level block of at least {MINIMUM_LINES} lines",
        )

    escape = escaping_control_flow([statement])
    if escape is not None:
        return decline(Refusal.CONTROL_FLOW_ESCAPES, f"the block contains a {escape}")

    planned = _plan(method, statement, source)
    if isinstance(planned, str):
        return decline(Refusal.MULTIPLE_OUTPUTS, planned)

    missing = [n for n in (*planned.inputs, planned.output) if n and n not in planned.types]
    if missing:
        return decline(Refusal.UNRESOLVED_NAME, f"no declared type for {', '.join(missing)}")

    static = any(
        child.type == "modifiers" and "static" in text_of(child, source)
        for child in method.children
    )
    indent = indent_at(source, method.start_byte)
    name = _free_name(_existing_names(site.enclosing_type, source))
    call, definition = _render(planned, name, source, static, indent)

    return Outcome.rewrite(
        NAME,
        site.file_path,
        target,
        (
            Edit(statement.start_byte, statement.end_byte, call),
            Edit(method.end_byte, method.end_byte, definition),
        ),
    )
