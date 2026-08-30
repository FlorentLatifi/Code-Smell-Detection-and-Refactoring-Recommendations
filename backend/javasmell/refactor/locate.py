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


class FileIndex:
    """Every type in one file, walked once.

    The walk is the expensive part: a generated parser in the corpus is 3.3 MB
    and holds 885 sites the engine looks at, and walking the whole tree per site
    cost six minutes on that file alone. The tree does not change between sites,
    so neither does this.
    """

    def __init__(self, file_path: str, source: bytes, tree: Tree | None = None) -> None:
        self.file_path = file_path
        self.source = source
        self._types = iter_types((tree or JavaParser().parse_tree(source)).root_node)
        self._by_name: dict[str, list[Node]] = {}
        for node in self._types:
            self._by_name.setdefault(named_child_text(node, source), []).append(node)

    def find(self, type_name: str, start_line: int, member_name: str | None = None) -> Site | None:
        """Locate one class, or one method within it. ``None`` when it is not there.

        ``start_line`` is 1-based, as every line number in this project is, while
        tree-sitter counts points from zero.
        """
        wanted_row = start_line - 1
        candidates = self._by_name.get(type_name, [])

        if member_name is None:
            for node in candidates:
                if node.start_point[0] == wanted_row:
                    return Site(self.file_path, self.source, node, node)
            return None

        for enclosing in candidates:
            body = enclosing.child_by_field_name("body")
            if body is None:
                continue
            for member in body.named_children:
                if (
                    member.type in CALLABLE_NODES
                    and member.start_point[0] == wanted_row
                    and named_child_text(member, self.source) == member_name
                ):
                    return Site(self.file_path, self.source, member, enclosing)
        return None


def find_site(
    file_path: str,
    source: bytes,
    type_name: str,
    start_line: int,
    member_name: str | None = None,
    tree: Tree | None = None,
) -> Site | None:
    """Locate one entity. Convenience wrapper for a caller with a single lookup.

    A caller with several lookups in one file should build a :class:`FileIndex`
    instead: this rebuilds it every call, which is the whole cost.
    """
    return FileIndex(file_path, source, tree).find(type_name, start_line, member_name)
