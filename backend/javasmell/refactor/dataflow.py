"""What a run of statements reads, writes, declares, and where control leaves it.

Extract Method stands or falls on this. Lifting statements into their own method
is safe exactly when the values crossing the boundary can be carried by a
parameter list and a single return, and when control cannot leave the block by
any route other than falling off its end. Everything here answers one of those
two questions.

**Only provably local names are tracked.** A bare name that is not declared in the
method is a field, an inherited field, or a static import, and the parser is
deliberately not a symbol resolver (VD-02) so it cannot tell which. That is
harmless here, and the reason is worth stating: the extracted method is placed in
the same class with the same static-ness, so such a name resolves there exactly
as it did before. It must simply never be turned into a parameter, because
passing a copy of a field would change what the code means.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

# Nodes that introduce a local binding, each carrying a `type` field.
DECLARATION_NODES = frozenset(
    {"local_variable_declaration", "formal_parameter", "catch_formal_parameter", "resource"}
)

# Loops capture a break or continue appearing inside them; a switch captures
# only break.
LOOP_NODES = frozenset(
    {"for_statement", "enhanced_for_statement", "while_statement", "do_statement"}
)
SWITCH_NODES = frozenset({"switch_expression", "switch_statement", "switch_block"})

# A name in one of these roles spells something other than a variable read.
MEMBER_PARENTS = frozenset({"field_access", "method_invocation", "scoped_identifier"})


def same_node(left: Node | None, right: Node | None) -> bool:
    """Are these the same node in the tree?

    Not ``is``. The tree-sitter bindings build a fresh Python wrapper on every
    accessor call, so two references to one node are never the same object and
    ``id()`` of them differs too. ``Node.__eq__`` compares position and tree, so
    it is the only comparison that means what it looks like -- and using ``is``
    here fails silently: the check simply never matches, and the analysis quietly
    treats an assignment target as a value it reads.
    """
    if left is None or right is None:
        return False
    return bool(left == right)


def span_of(node: Node) -> tuple[int, int, str]:
    """A key that survives re-wrapping, for membership tests."""
    return node.start_byte, node.end_byte, node.type


def text_of(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def walk(root: Node) -> list[Node]:
    """Every node beneath ``root``, iteratively.

    Iterative for the reason the parser's own walk is: a long chain of string
    concatenations is one line of Java and a thousand levels of tree, and the
    recursion limit is not a property of the code being analysed.
    """
    seen: list[Node] = []
    stack = [root]
    while stack:
        node = stack.pop()
        seen.append(node)
        stack.extend(node.children)
    return seen


@dataclass
class Declarations:
    """Local names in scope, with the source text of their declared type."""

    types: dict[str, str] = field(default_factory=dict)

    def add(self, name: str, type_text: str) -> None:
        # First declaration wins: an inner shadowing declaration would give the
        # wrong type for the outer name, and shadowing is refused anyway.
        self.types.setdefault(name, type_text)

    def __contains__(self, name: object) -> bool:
        return name in self.types


def declarations_in(node: Node, source: bytes) -> Declarations:
    """Every local variable and parameter declared anywhere beneath ``node``."""
    found = Declarations()
    for current in walk(node):
        if current.type not in DECLARATION_NODES:
            continue
        declared_type = current.child_by_field_name("type")
        if declared_type is None:
            # A catch parameter spells its type as a `catch_type` child so that
            # multi-catch (`catch (A | B e)`) has somewhere to put both.
            declared_type = next(
                (c for c in current.named_children if c.type == "catch_type"), None
            )
        if declared_type is None:
            continue
        type_text = text_of(declared_type, source)

        named = current.child_by_field_name("name")
        if named is not None:
            found.add(text_of(named, source), type_text)
            continue
        # A local_variable_declaration holds one or more variable_declarators.
        for child in current.named_children:
            if child.type == "variable_declarator":
                declarator_name = child.child_by_field_name("name")
                if declarator_name is not None:
                    found.add(text_of(declarator_name, source), type_text)
    return found


def is_value_read(identifier: Node) -> bool:
    """Is this identifier a use of a variable's value?

    Excluded are the places where the syntax merely spells a name: the method in
    a call, the member half of a qualified access, the name being declared, and
    the target of a plain assignment.
    """
    parent = identifier.parent
    if parent is None:
        return False
    if parent.type in MEMBER_PARENTS:
        # In `a.b`, `a` is read and `b` is not; same for a call's receiver.
        return same_node(parent.child_by_field_name("object"), identifier)
    if parent.type == "variable_declarator":
        return not same_node(parent.child_by_field_name("name"), identifier)
    if parent.type == "assignment_expression":
        if not same_node(parent.child_by_field_name("left"), identifier):
            return True
        # `x += 1` reads x before writing it; `x = 1` does not read it at all.
        return _compound(parent)
    return parent.type not in DECLARATION_NODES


def _compound(assignment: Node) -> bool:
    """True for `+=` and friends, false for a plain `=`."""
    operator = assignment.child_by_field_name("operator")
    return operator is not None and operator.type != "="


def names_read(node: Node, source: bytes, known: Declarations) -> set[str]:
    """Local variables whose value is used beneath ``node``."""
    return {
        text_of(current, source)
        for current in walk(node)
        if current.type == "identifier"
        and text_of(current, source) in known
        and is_value_read(current)
    }


def names_written(node: Node, source: bytes, known: Declarations) -> set[str]:
    """Local variables assigned beneath ``node``, by any form of assignment."""
    written: set[str] = set()
    for current in walk(node):
        if current.type == "assignment_expression":
            left = current.child_by_field_name("left")
            if left is not None and left.type == "identifier":
                written.add(text_of(left, source))
        elif current.type == "update_expression":
            for child in current.children:
                if child.type == "identifier":
                    written.add(text_of(child, source))
        elif current.type == "variable_declarator":
            named = current.child_by_field_name("name")
            if named is not None and current.child_by_field_name("value") is not None:
                written.add(text_of(named, source))
    return {name for name in written if name in known}


def escaping_control_flow(nodes: list[Node]) -> str | None:
    """The first jump that would leave the extracted block, or None.

    A ``return`` always escapes: after extraction it would return from the new
    method rather than from the original one, which is a different program.

    A ``break`` or ``continue`` escapes only when the loop or switch it belongs
    to begins outside the block. One inside a loop that is itself part of the
    extraction travels with it and stays correct, which is the ordinary case and
    would be wasteful to refuse.

    A labelled jump is refused outright rather than resolved: proving where a
    label lands means tracking labelled statements through the whole method, and
    the construct is rare enough that the analysis would not earn its risk.
    """
    boundary = {span_of(node) for node in nodes}
    for top in nodes:
        for current in walk(top):
            kind = current.type
            if kind == "return_statement":
                return "return"
            if kind not in {"break_statement", "continue_statement"}:
                continue

            plain = kind.removesuffix("_statement")
            if any(child.type == "identifier" for child in current.named_children):
                return f"labelled {plain}"

            capturing = LOOP_NODES | SWITCH_NODES if plain == "break" else LOOP_NODES
            walker: Node | None = current.parent
            captured = False
            while walker is not None:
                if walker.type in capturing:
                    captured = True
                    break
                if span_of(walker) in boundary:
                    break
                walker = walker.parent
            if not captured:
                return plain
    return None
