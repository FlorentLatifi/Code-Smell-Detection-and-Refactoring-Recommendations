"""Replace Nested Conditional with Guard Clauses (Fowler, *Refactoring* 2nd ed.).

Turns a method whose whole body is wrapped in one conditional::

    void post(int amount) {
        if (amount > 0) {
            total += amount;
            log(amount);
        }
    }

into one that leaves early and keeps its real work at the top level::

    void post(int amount) {
        if (!(amount > 0)) {
            return;
        }
        total += amount;
        log(amount);
    }

The transformation is deliberately narrow. It rewrites exactly the shape above
and declines everything else, because every widening of it introduces a case
where the rewrite is not obviously equivalent: an ``else`` branch has to go
somewhere, a non-void method needs a return value that cannot be invented, and a
body of several statements around the conditional means the conditional is not
what the method is *for*. A transformation that declines often but is never wrong
is defensible in a thesis; one that tries everything and corrupts a file is not.

**On negating the condition.** The guard uses ``!(...)`` around the original text
rather than inverting the operator. Rewriting ``a > b`` to ``a <= b`` is wrong for
floating point, where both are false if either side is NaN, and inverting a
compound condition by hand is how De Morgan bugs get written. Wrapping is
mechanical and correct for every boolean expression, including one with side
effects, which is evaluated exactly once either way.
"""

from __future__ import annotations

from tree_sitter import Node

from javasmell.refactor.base import Outcome, Refusal
from javasmell.refactor.edits import Edit, dedent, indent_at
from javasmell.refactor.locate import Site

NAME = "ReplaceNestedConditionalWithGuardClauses"


def _sole_statement(body: Node) -> Node | None:
    """The one statement in a block, or None when there is not exactly one."""
    statements = [child for child in body.named_children if child.type != "comment"]
    return statements[0] if len(statements) == 1 else None


def apply(site: Site) -> Outcome:
    """Rewrite the site, or decline with the reason it does not fit."""
    source = site.source
    method = site.node
    target = site.text(method.child_by_field_name("name")) or "<anonymous>"

    def decline(reason: Refusal, detail: str) -> Outcome:
        return Outcome.refuse(NAME, site.file_path, target, reason, detail)

    returns = method.child_by_field_name("type")
    if returns is None or site.text(returns) != "void":
        return decline(Refusal.SHAPE_NOT_MATCHED, "a non-void method needs a return value")

    body = method.child_by_field_name("body")
    if body is None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "no body to rewrite")

    conditional = _sole_statement(body)
    if conditional is None or conditional.type != "if_statement":
        return decline(Refusal.SHAPE_NOT_MATCHED, "the body is not a single conditional")

    if conditional.child_by_field_name("alternative") is not None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "the conditional has an else branch")

    consequence = conditional.child_by_field_name("consequence")
    if consequence is None or consequence.type != "block":
        return decline(Refusal.SHAPE_NOT_MATCHED, "the branch is not a block")

    kept = [child for child in consequence.named_children if child.type != "comment"]
    if not kept:
        return decline(Refusal.SHAPE_NOT_MATCHED, "the branch is empty")

    condition = conditional.child_by_field_name("condition")
    if condition is None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "the conditional has no condition")

    outer = indent_at(source, conditional.start_byte)
    inner = indent_at(source, kept[0].start_byte)
    if not inner.startswith(outer) or inner == outer:
        return decline(
            Refusal.SHAPE_NOT_MATCHED,
            "the branch is not indented one level past the conditional",
        )
    unit = inner[len(outer) :]

    # The condition node includes its own parentheses, so wrapping gives
    # `!(...)` rather than `!((...))`.
    negated = b"!" + source[condition.start_byte : condition.end_byte]

    # From the first kept statement to the last, so a trailing comment inside
    # the branch is carried out with the code rather than left behind.
    inner_span = source[kept[0].start_byte : kept[-1].end_byte]
    lifted = dedent(inner_span, unit)

    replacement = (
        b"if (" + negated + b") {\n" + inner + b"return;\n" + outer + b"}\n" + outer + lifted
    )
    edit = Edit(conditional.start_byte, conditional.end_byte, replacement)
    return Outcome.rewrite(NAME, site.file_path, target, (edit,))
