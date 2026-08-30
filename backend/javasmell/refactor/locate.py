"""Finding, in a freshly parsed file, the entity a detector flagged.

A ``Smell`` says which class and method it found and on which line. Turning that
back into a syntax node needs care, because the two sides are not guaranteed to
be looking at the same text: the model may have been measured minutes or days
before, and the file on disk is what will be rewritten. So the file is re-parsed
and the node is looked up in the new tree.

The lookup anchors on the **start line** and verifies with the **name**, the same
way MLCQ samples are matched to entities (VD-19). Anchoring the other way round
fails on the ordinary case of an overloaded method, where several nodes share a
name and only the position separates them; verifying by name then catches the
case that matters, which is a file edited since it was measured, where the line
now holds something else entirely.
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node, Tree

from javasmell.parsing.java_parser import JavaParser

TYPE_NODES = frozenset(
    {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}
)
CALLABLE_NODES = frozenset({"method_declaration", "constructor_declaration"})


@dataclass(frozen=True)
class Site:
    """One place a transformation may rewrite, with the bytes it will rewrite."""

    file_path: str
    source: bytes
    node: Node
    enclosing_type: Node

    @property
    def span(self) -> tuple[int, int]:
        return self.node.start_byte, self.node.end_byte

    def text(self, node: Node | None = None) -> str:
        target = self.node if node is None else node
        return self.source[target.start_byte : target.end_byte].decode("utf-8", errors="replace")


def named_child_text(node: Node, source: bytes) -> str:
    """The declared name of a type or callable, or "" when it has none."""
    identifier = node.child_by_field_name("name")
    if identifier is None:
        return ""
    return source[identifier.start_byte : identifier.end_byte].decode("utf-8", errors="replace")


def iter_types(root: Node) -> list[Node]:
    """Every type declaration, including nested ones.

    Iterative rather than recursive for the same reason the parser's own walk is:
    a deeply nested expression is a single line of Java and a thousand levels of
    tree, and the recursion limit is not a property of the code being analysed.
    """
    found: list[Node] = []
    stack = list(root.named_children)
    while stack:
        node = stack.pop()
        if node.type in TYPE_NODES:
            found.append(node)
        stack.extend(node.named_children)
    return found


def find_site(
    file_path: str,
    source: bytes,
    type_name: str,
    start_line: int,
    member_name: str | None = None,
    tree: Tree | None = None,
) -> Site | None:
    """Locate one class, or one method within it. ``None`` when it is not there.

    ``start_line`` is 1-based, as every line number in this project is, while
    tree-sitter counts points from zero.

    ``tree`` may be supplied when the caller has already parsed this exact
    source. One generated file in the corpus is 3.3 MB and holds 885 sites the
    engine wants to look at; parsing it once per site cost eight minutes on that
    file alone, for a tree that never changes between them.
    """
    tree = tree if tree is not None else JavaParser().parse_tree(source)
    wanted_row = start_line - 1

    types = iter_types(tree.root_node)
    if member_name is None:
        for node in types:
            if node.start_point[0] == wanted_row and named_child_text(node, source) == type_name:
                return Site(file_path, source, node, node)
        return None

    for enclosing in types:
        if named_child_text(enclosing, source) != type_name:
            continue
        body = enclosing.child_by_field_name("body")
        if body is None:
            continue
        for member in body.named_children:
            if (
                member.type in CALLABLE_NODES
                and member.start_point[0] == wanted_row
                and named_child_text(member, source) == member_name
            ):
                return Site(file_path, source, member, enclosing)
    return None
