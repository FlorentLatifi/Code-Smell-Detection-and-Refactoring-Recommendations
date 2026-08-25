"""Java front-end built on tree-sitter.

tree-sitter was chosen over ``javalang`` because it keeps up with modern Java
syntax (records, sealed types, switch expressions, lambdas) and over a
JavaParser sidecar because it needs no JVM at analysis time.

The parser is deliberately *not* a full symbol resolver. It records what each
method syntactically touches -- bare names, ``this.x``, ``receiver.member`` --
and leaves interpretation to :mod:`javasmell.metrics`, where the declaring
class is known. That is enough for every metric in Lanza & Marinescu's
detection strategies and avoids building a type system.
"""

from __future__ import annotations

import os
from typing import Iterator, Optional

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser

from javasmell.model.entities import (
    ClassInfo,
    CompilationUnit,
    FieldInfo,
    MethodInfo,
    ParameterInfo,
)

TYPE_DECLARATIONS = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "record_declaration": "record",
}

# Statements that open a new indentation level, for max-nesting-depth.
NESTING_NODES = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
    "switch_expression",
    "try_statement",
    "catch_clause",
    "synchronized_statement",
}

# Each occurrence adds one independent path (McCabe).
DECISION_NODES = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
    "catch_clause",
    "ternary_expression",
    "switch_rule",
}

_LANGUAGE = Language(tsjava.language())


class JavaParser:
    """Turns Java source into :class:`CompilationUnit` objects."""

    def __init__(self) -> None:
        self._parser = Parser(_LANGUAGE)

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    def parse_file(self, path: str) -> CompilationUnit:
        with open(path, "rb") as handle:
            source = handle.read()
        return self.parse_source(source, path)

    def parse_source(self, source, path: str = "<memory>") -> CompilationUnit:
        if isinstance(source, str):
            source = source.encode("utf-8")
        tree = self._parser.parse(source)
        ctx = _Context(source)
        root = tree.root_node

        package = ""
        imports: list[str] = []
        for child in root.named_children:
            if child.type == "package_declaration":
                package = ctx.text(child).removeprefix("package").strip(" ;\n\t")
            elif child.type == "import_declaration":
                imports.append(ctx.text(child).removeprefix("import").strip(" ;\n\t"))

        classes = [
            _build_class(node, ctx, package, path)
            for node in _iter_type_declarations(root)
        ]
        return CompilationUnit(
            file_path=path, package=package, imports=imports, classes=classes
        )


class _Context:
    """Shared source text plus the line-based helpers the builders need."""

    def __init__(self, source: bytes) -> None:
        self.source = source
        self.lines = source.decode("utf-8", errors="replace").splitlines()

    def text(self, node: Node) -> str:
        return self.source[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )

    def loc(self, node: Node) -> int:
        """Effective lines of code: blank, brace-only and comment lines excluded."""
        start, end = node.start_point[0], node.end_point[0]
        count = 0
        in_block_comment = False
        for raw in self.lines[start : end + 1]:
            line = raw.strip()
            if in_block_comment:
                if "*/" in line:
                    in_block_comment = False
                continue
            if not line or line in {"{", "}", "});", "}"}:
                continue
            if line.startswith("//"):
                continue
            if line.startswith("/*"):
                if "*/" not in line:
                    in_block_comment = True
                continue
            if line.startswith("*"):
                continue
            count += 1
        return count


def _iter_type_declarations(node: Node) -> Iterator[Node]:
    """Yield every type declaration, including nested ones.

    Nested and inner classes are reported as separate classes: a God Class
    hiding inside an outer class should still be found.
    """
    for child in node.named_children:
        if child.type in TYPE_DECLARATIONS:
            yield child
        yield from _iter_type_declarations(child)


def _modifiers(node: Node, ctx: _Context) -> frozenset[str]:
    for child in node.named_children:
        if child.type == "modifiers":
            return frozenset(
                token for token in ctx.text(child).split() if not token.startswith("@")
            )
    return frozenset()


def _type_name(node: Optional[Node], ctx: _Context) -> str:
    """Erase generics and array brackets: ``List<Item>[]`` becomes ``List``."""
    if node is None:
        return "void"
    if node.type == "generic_type":
        base = node.named_children[0] if node.named_children else None
        return _type_name(base, ctx)
    if node.type == "array_type":
        return _type_name(node.child_by_field_name("element"), ctx)
    if node.type == "scoped_type_identifier":
        return ctx.text(node).split(".")[-1]
    return ctx.text(node).strip()


def _build_class(node: Node, ctx: _Context, package: str, path: str) -> ClassInfo:
    name_node = node.child_by_field_name("name")
    name = ctx.text(name_node) if name_node else "<anonymous>"

    superclass = None
    super_node = node.child_by_field_name("superclass")
    if super_node is not None and super_node.named_children:
        superclass = _type_name(super_node.named_children[0], ctx)

    interfaces: list[str] = []
    iface_node = node.child_by_field_name("interfaces")
    if iface_node is not None:
        for descendant in iface_node.named_children:
            if descendant.type == "type_list":
                interfaces = [_type_name(t, ctx) for t in descendant.named_children]

    body = node.child_by_field_name("body")
    fields: list[FieldInfo] = []
    methods: list[MethodInfo] = []
    if body is not None:
        for member in body.named_children:
            if member.type == "field_declaration":
                fields.extend(_build_fields(member, ctx))
            elif member.type in {"method_declaration", "constructor_declaration"}:
                methods.append(_build_method(member, ctx, name))

    return ClassInfo(
        name=name,
        kind=TYPE_DECLARATIONS[node.type],
        package=package,
        file_path=path,
        modifiers=_modifiers(node, ctx),
        superclass=superclass,
        interfaces=interfaces,
        fields=fields,
        methods=methods,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        source_lines=ctx.lines[node.start_point[0] : node.end_point[0] + 1],
    )


def _build_fields(node: Node, ctx: _Context) -> list[FieldInfo]:
    """One declaration can introduce several fields: ``int a, b;``."""
    type_name = _type_name(node.child_by_field_name("type"), ctx)
    modifiers = _modifiers(node, ctx)
    result = []
    for child in node.named_children:
        if child.type != "variable_declarator":
            continue
        declared = child.child_by_field_name("name")
        if declared is None:
            continue
        result.append(
            FieldInfo(
                name=ctx.text(declared),
                type_name=type_name,
                modifiers=modifiers,
                line=child.start_point[0] + 1,
            )
        )
    return result


def _build_method(node: Node, ctx: _Context, class_name: str) -> MethodInfo:
    is_constructor = node.type == "constructor_declaration"
    name_node = node.child_by_field_name("name")
    name = ctx.text(name_node) if name_node else class_name

    parameters = _build_parameters(node, ctx)
    method = MethodInfo(
        name=name,
        return_type=(
            None if is_constructor else _type_name(node.child_by_field_name("type"), ctx)
        ),
        parameters=parameters,
        modifiers=_modifiers(node, ctx),
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        is_constructor=is_constructor,
    )
    for param in parameters:
        method.declared_locals.add(param.name)
        method.local_var_types[param.name] = param.type_name
        method.referenced_types.add(param.type_name)
    if method.return_type:
        method.referenced_types.add(method.return_type)

    body = node.child_by_field_name("body")
    if body is not None:
        _collect_body(body, ctx, method)
        method.metrics["CC"] = float(_cyclomatic_complexity(body))
        method.metrics["MAXNESTING"] = float(_max_nesting(body))
    else:
        # Abstract or interface method: no body, so no decision points.
        method.metrics["CC"] = 1.0
        method.metrics["MAXNESTING"] = 0.0
    method.metrics["MLOC"] = float(ctx.loc(node))
    method.metrics["NP"] = float(len(parameters))
    return method


def _build_parameters(node: Node, ctx: _Context) -> list[ParameterInfo]:
    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return []
    parameters: list[ParameterInfo] = []
    for param in params_node.named_children:
        if param.type not in {"formal_parameter", "spread_parameter"}:
            continue
        pname = param.child_by_field_name("name")
        ptype = param.child_by_field_name("type")
        if pname is None and param.type == "spread_parameter":
            # `T... args` keeps the name inside a variable_declarator.
            declarator = next(
                (c for c in param.named_children if c.type == "variable_declarator"),
                None,
            )
            pname = declarator.child_by_field_name("name") if declarator else None
            if ptype is None and param.named_children:
                ptype = param.named_children[0]
        if pname is None:
            continue
        parameters.append(
            ParameterInfo(name=ctx.text(pname), type_name=_type_name(ptype, ctx))
        )
    return parameters


def _collect_body(body: Node, ctx: _Context, method: MethodInfo) -> None:
    """Single walk of the body, recording everything the metrics need."""
    stack = [body]
    while stack:
        node = stack.pop()
        kind = node.type

        if kind == "local_variable_declaration":
            type_name = _type_name(node.child_by_field_name("type"), ctx)
            method.referenced_types.add(type_name)
            for child in node.named_children:
                if child.type == "variable_declarator":
                    declared = child.child_by_field_name("name")
                    if declared is not None:
                        var = ctx.text(declared)
                        method.declared_locals.add(var)
                        method.local_var_types[var] = type_name

        elif kind == "enhanced_for_statement":
            declared = node.child_by_field_name("name")
            if declared is not None:
                var = ctx.text(declared)
                method.declared_locals.add(var)
                method.local_var_types[var] = _type_name(
                    node.child_by_field_name("type"), ctx
                )

        elif kind == "catch_formal_parameter":
            declared = node.child_by_field_name("name")
            if declared is not None:
                method.declared_locals.add(ctx.text(declared))

        elif kind == "field_access":
            receiver = node.child_by_field_name("object")
            member = node.child_by_field_name("field")
            if member is not None and receiver is not None:
                member_name = ctx.text(member)
                if receiver.type == "this":
                    method.this_accesses.add(member_name)
                else:
                    method.qualified_field_accesses.add(
                        (ctx.text(receiver), member_name)
                    )

        elif kind == "method_invocation":
            receiver = node.child_by_field_name("object")
            called = node.child_by_field_name("name")
            if called is not None:
                called_name = ctx.text(called)
                if receiver is None or receiver.type == "this":
                    method.unqualified_calls.add(called_name)
                else:
                    method.qualified_calls.add((ctx.text(receiver), called_name))

        elif kind in {"type_identifier", "scoped_type_identifier"}:
            method.referenced_types.add(_type_name(node, ctx))

        elif kind == "identifier":
            method.bare_names.add(ctx.text(node))

        stack.extend(node.named_children)


def _cyclomatic_complexity(body: Node) -> int:
    """McCabe complexity: 1 plus every decision point in the body."""
    complexity = 1
    stack = [body]
    while stack:
        node = stack.pop()
        kind = node.type
        if kind in DECISION_NODES:
            complexity += 1
        elif kind == "switch_label":
            # `default` is the fall-through path, not a decision.
            label = node.text.decode("utf-8", errors="replace").strip()
            if not label.startswith("default"):
                complexity += 1
        elif kind == "binary_expression":
            operator = node.child_by_field_name("operator")
            if operator is not None and operator.type in {"&&", "||"}:
                complexity += 1
        stack.extend(node.named_children)
    return complexity


def _max_nesting(body: Node) -> int:
    deepest = 0
    stack: list[tuple[Node, int]] = [(body, 0)]
    while stack:
        node, depth = stack.pop()
        if node.type in NESTING_NODES:
            depth += 1
            deepest = max(deepest, depth)
        for child in node.named_children:
            stack.append((child, depth))
    return deepest


def iter_java_files(root: str) -> Iterator[str]:
    """Every ``.java`` file under ``root``, skipping build and VCS output."""
    skip = {".git", "target", "build", "out", "bin", "node_modules", ".idea", ".venv"}
    if os.path.isfile(root):
        if root.endswith(".java"):
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for filename in filenames:
            if filename.endswith(".java"):
                yield os.path.join(dirpath, filename)
