"""Introduce Parameter Object (Fowler, *Refactoring* 2nd ed.).

Replaces a long parameter list with a single object carrying the same values.
Before::

    private int total(Order order, int qty, double rate, boolean taxed) {
        return order.base(qty) * rate * (taxed ? 1.2 : 1.0);
    }

    void run() { report(total(o, 3, 1.5, true)); }

After::

    private static final class TotalParams {
        final Order order;
        final int qty;
        final double rate;
        final boolean taxed;

        TotalParams(Order order, int qty, double rate, boolean taxed) {
            this.order = order;
            this.qty = qty;
            this.rate = rate;
            this.taxed = taxed;
        }
    }

    private int total(TotalParams params) {
        Order order = params.order;
        int qty = params.qty;
        double rate = params.rate;
        boolean taxed = params.taxed;
        return order.base(qty) * rate * (taxed ? 1.2 : 1.0);
    }

    void run() { report(total(new TotalParams(o, 3, 1.5, true))); }

**Why only ``private`` methods.** This is the transformation VD-30 said was
blocked on locality rather than on difficulty. Changing a signature means finding
every call, and the parser is deliberately not a symbol resolver. But Java scopes
``private`` to the body of the enclosing top-level class, so for a private method
every call site is in the file being rewritten -- provable from the one parse tree
the engine already has. Nothing else about the method makes it easier; the access
modifier is the whole reason it can be done at all.

**Why the body is not rewritten.** Fowler threads the object through the body and
deletes the loose names. This engine re-declares them as locals on the first lines
instead, so the body it did not write is the body it does not touch. That removes
the two ways this transformation is usually got wrong -- a name shadowed in an
inner scope, and a parameter the body assigns to -- because the locals keep the
same names, the same types and the same assignability that Java gives parameters.
Java passes by value, so assigning to a parameter never reached the caller either;
the local behaves identically. What the smell is about, the signature, changes;
what the author wrote stays as they wrote it.

**What is refused.** Anything the file cannot settle: an overloaded name, a call
this analysis cannot tie to this method (a method reference, a call through
another instance), varargs, generics, an annotated parameter, a nested enclosing
class. The last one is not a parse limit but a portability one: the object is
emitted as a ``static`` nested class, which older Java forbids inside an inner
class, and the engine will not emit code whose legality depends on the compiler.
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from javasmell.refactor.base import Outcome, Refusal
from javasmell.refactor.dataflow import text_of, walk
from javasmell.refactor.edits import Edit, indent_at
from javasmell.refactor.locate import Site

NAME = "IntroduceParameterObject"

# Below this an object hides nothing: the call site trades two arguments for one
# constructor call of two arguments. The detector fires far above this, so the
# bound only guards direct use of the transformation.
MINIMUM_PARAMETERS = 2

FIELD_NAME = "params"
CLASS_SUFFIX = "Params"


@dataclass(frozen=True)
class Parameter:
    """One declared parameter, as the signature spells it."""

    name: str
    type_text: str


def _parameters(node: Node, source: bytes) -> list[Parameter] | None:
    """The declared parameters, or None when one of them is not plain.

    Varargs and annotated parameters return None: a spread parameter has no
    single field type, and an annotation may carry meaning that moving it to a
    field would change. ``final`` is allowed and dropped, since a final parameter
    and a plain local differ in nothing the caller can observe.
    """
    parameters: list[Parameter] = []
    for child in node.named_children:
        if child.type != "formal_parameter":
            return None
        declared = child.child_by_field_name("type")
        named = child.child_by_field_name("name")
        if declared is None or named is None:
            return None
        for extra in child.named_children:
            if extra.type == "modifiers" and text_of(extra, source).strip() != "final":
                return None
        parameters.append(Parameter(text_of(named, source), text_of(declared, source)))
    return parameters


def _same_name_declarations(root: Node, source: bytes, name: str) -> int:
    return sum(
        1
        for node in walk(root)
        if node.type == "method_declaration"
        and (named := node.child_by_field_name("name")) is not None
        and text_of(named, source) == name
    )


def _call_sites(root: Node, source: bytes, name: str, arity: int) -> list[Node] | None:
    """Every ``argument_list`` to rewrite, or None if a reference is unresolvable.

    Accepted: ``name(...)`` and ``this.name(...)``. Everything else that mentions
    the identifier -- ``other.name(...)``, ``Outer.this.name(...)``, ``this::name``
    -- is refused rather than guessed at. A private method is reachable from
    another instance of the same class, so a qualified call is not necessarily
    someone else's method; it is simply one this analysis cannot prove is ours.
    """
    invocations: dict[int, Node] = {}
    accepted_names: set[int] = set()

    for node in walk(root):
        if node.type != "method_invocation":
            continue
        named = node.child_by_field_name("name")
        if named is None or text_of(named, source) != name:
            continue
        receiver = node.child_by_field_name("object")
        if receiver is not None and receiver.type != "this":
            return None
        arguments = node.child_by_field_name("arguments")
        if arguments is None or len(arguments.named_children) != arity:
            return None
        invocations[arguments.start_byte] = arguments
        accepted_names.add(named.start_byte)

    for node in walk(root):
        if node.type != "identifier" or text_of(node, source) != name:
            continue
        parent = node.parent
        if parent is not None and parent.type == "method_declaration":
            continue  # the declaration's own name
        if node.start_byte not in accepted_names:
            return None

    return [invocations[key] for key in sorted(invocations)]


def _class_name(method_name: str, taken: set[str]) -> str:
    base = method_name[:1].upper() + method_name[1:] + CLASS_SUFFIX
    if base not in taken:
        return base
    index = 2
    while f"{base}{index}" in taken:
        index += 1
    return f"{base}{index}"


def _holder_name(parameters: list[Parameter]) -> str:
    """The name of the new parameter, kept clear of the values it carries."""
    taken = {parameter.name for parameter in parameters}
    if FIELD_NAME not in taken:
        return FIELD_NAME
    index = 2
    while f"{FIELD_NAME}{index}" in taken:
        index += 1
    return f"{FIELD_NAME}{index}"


def _object_class(
    class_name: str, parameters: list[Parameter], indent: bytes, unit: bytes
) -> bytes:
    """The nested class, rendered at the indentation of the method it serves."""
    outer = indent.decode()
    member = (indent + unit).decode()
    inside = (indent + unit + unit).decode()

    fields = "".join(f"{member}final {p.type_text} {p.name};\n" for p in parameters)
    signature = ", ".join(f"{p.type_text} {p.name}" for p in parameters)
    assignments = "".join(f"{inside}this.{p.name} = {p.name};\n" for p in parameters)

    return (
        f"{outer}private static final class {class_name} {{\n"
        f"{fields}\n"
        f"{member}{class_name}({signature}) {{\n"
        f"{assignments}"
        f"{member}}}\n"
        f"{outer}}}\n\n"
    ).encode()


def _unpacking(parameters: list[Parameter], holder: str, indent: bytes, unit: bytes) -> bytes:
    """The lines that give the body back the names it was written against."""
    inner = (indent + unit).decode()
    return b"".join(
        f"\n{inner}{p.type_text} {p.name} = {holder}.{p.name};".encode() for p in parameters
    )


def apply(site: Site) -> Outcome:
    """Rewrite the site, or decline with the reason it does not fit."""
    source = site.source
    method = site.node
    target = site.text(method.child_by_field_name("name")) or "<anonymous>"

    def decline(reason: Refusal, detail: str) -> Outcome:
        return Outcome.refuse(NAME, site.file_path, target, reason, detail)

    if method.type != "method_declaration":
        return decline(Refusal.SHAPE_NOT_MATCHED, "not a method declaration")

    body = method.child_by_field_name("body")
    if body is None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "no body to rewrite")

    modifiers = next((c for c in method.named_children if c.type == "modifiers"), None)
    if modifiers is None or "private" not in text_of(modifiers, source).split():
        return decline(Refusal.SHAPE_NOT_MATCHED, "not private, so the call sites are not local")

    if method.child_by_field_name("type_parameters") is not None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "generic method")

    # The object is emitted as a static nested class, which older Java forbids
    # inside an inner class. Restricting to a top-level enclosing class keeps the
    # output legal on every version rather than on the one that happens to run.
    parent = site.enclosing_type.parent
    if site.enclosing_type.type != "class_declaration" or (
        parent is not None and parent.type != "program"
    ):
        return decline(Refusal.SHAPE_NOT_MATCHED, "enclosing type is not a top-level class")

    declared = method.child_by_field_name("parameters")
    if declared is None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "no parameter list")
    parameters = _parameters(declared, source)
    if parameters is None:
        return decline(Refusal.SHAPE_NOT_MATCHED, "varargs or annotated parameter")
    if len(parameters) < MINIMUM_PARAMETERS:
        return decline(Refusal.SHAPE_NOT_MATCHED, f"only {len(parameters)} parameter(s)")

    root = site.enclosing_type
    while root.parent is not None:
        root = root.parent

    if _same_name_declarations(root, source, target) != 1:
        return decline(Refusal.AMBIGUOUS_OVERLOAD, f"more than one method named {target}")

    call_sites = _call_sites(root, source, target, len(parameters))
    if call_sites is None:
        return decline(Refusal.UNRESOLVED_NAME, "a reference that cannot be tied to the method")

    taken = {
        text_of(named, source)
        for node in walk(root)
        if node.type.endswith("_declaration")
        and (named := node.child_by_field_name("name")) is not None
    }
    class_name = _class_name(target, taken)
    holder = _holder_name(parameters)

    indent = indent_at(source, method.start_byte)
    unit = b"    " if b"\t" not in indent else b"\t"

    edits = [
        Edit(
            method.start_byte - len(indent),
            method.start_byte - len(indent),
            _object_class(class_name, parameters, indent, unit),
        ),
        Edit(declared.start_byte, declared.end_byte, f"({class_name} {holder})".encode()),
        Edit(
            body.start_byte + 1,
            body.start_byte + 1,
            _unpacking(parameters, holder, indent, unit),
        ),
    ]
    for arguments in call_sites:
        inside = source[arguments.start_byte + 1 : arguments.end_byte - 1].decode("utf-8")
        edits.append(
            Edit(
                arguments.start_byte,
                arguments.end_byte,
                f"(new {class_name}({inside}))".encode(),
            )
        )

    return Outcome.rewrite(NAME, site.file_path, target, tuple(sorted(edits)))
