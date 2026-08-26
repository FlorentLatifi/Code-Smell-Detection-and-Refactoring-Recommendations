"""Object-oriented metric suite.

Two families are implemented:

* the **CK suite** (Chidamber & Kemerer, 1994): WMC, DIT, NOC, CBO, RFC, LCOM;
* the **detection-strategy metrics** of Lanza & Marinescu (2006): ATFD, LAA,
  FDP, TCC, WOC and NOAV, which the rule-based detectors in
  :mod:`javasmell.detectors` are built from.

Every metric is computed from the syntactic facts the parser collected, never
by re-walking the tree, so a class is traversed once regardless of how many
metrics are requested.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations

from javasmell.model.entities import ClassInfo, MethodInfo, ProjectModel
from javasmell.parsing.java_parser import effective_loc

# Primitive and ubiquitous JDK types are noise in a coupling count: every class
# touches String and int, so including them would flatten the metric.
IGNORED_TYPES = {
    "void",
    "int",
    "long",
    "short",
    "byte",
    "char",
    "boolean",
    "float",
    "double",
    "Integer",
    "Long",
    "Short",
    "Byte",
    "Character",
    "Boolean",
    "Float",
    "Double",
    "String",
    "StringBuilder",
    "Object",
    "Number",
    "Math",
    "System",
    "Class",
    "List",
    "ArrayList",
    "Map",
    "HashMap",
    "Set",
    "HashSet",
    "Collection",
    "Optional",
    "Stream",
    "Exception",
    "RuntimeException",
    "Throwable",
    "Error",
    "Iterator",
    "Iterable",
    "Comparable",
    "Runnable",
    "Thread",
    # Conventional generic type-parameter names. Only consulted when the set of
    # project types is unknown; otherwise project membership decides.
    "T",
    "E",
    "K",
    "V",
    "R",
    "U",
}

ACCESSOR_PREFIXES = ("get", "set", "is", "has")


def _is_accessor_name(name: str) -> bool:
    return name.startswith(ACCESSOR_PREFIXES)


# ----------------------------------------------------------------------
# Step 1: resolve what each method touches, now that the class is known
# ----------------------------------------------------------------------
def resolve_accesses(cls: ClassInfo, project_types: set[str] | None = None) -> None:
    """Split every access a method makes into *own* and *foreign*.

    A bare name is an own-field access only when it matches a declared field
    and is not shadowed by a local or parameter, which is exactly Java's own
    scoping rule, and the reason ``declared_locals`` is collected up front.

    ``project_types`` restricts foreign data to classes belonging to the
    analysed project. Without it, calls into the JDK would inflate ATFD and
    make every class look envious.
    """
    field_names = cls.field_names
    field_types = cls.field_types

    for method in cls.methods:
        visible = (method.bare_names - method.declared_locals) & field_names
        method.own_field_accesses = visible | (method.this_accesses & field_names)

        # Foreign *data* is either a direct field read on another object, or a
        # value pulled out through an accessor. A behavioural call on another
        # object is coupling (counted by CBO/CINT), not envy.
        candidates = method.qualified_field_accesses | {
            (receiver, member)
            for receiver, member in method.qualified_calls
            if _is_accessor_name(member)
        }

        foreign: set[tuple[str, str]] = set()
        for receiver, member in candidates:
            receiver_type = _resolve_receiver_type(receiver, method, field_types)
            if receiver_type is None or receiver_type == cls.name:
                continue
            if project_types is not None:
                # Membership in the project is the precise filter, so the
                # name-based blocklist must not override it; a project class
                # really called `E` or `Set` is still foreign data.
                if receiver_type not in project_types:
                    continue
            elif receiver_type in IGNORED_TYPES:
                continue
            foreign.add((receiver_type, member))
        method.foreign_accesses = foreign


def _resolve_receiver_type(
    receiver: str, method: MethodInfo, field_types: dict[str, str]
) -> str | None:
    """Best-effort type of a receiver expression.

    Only single-identifier receivers are resolved. Chained expressions such as
    ``a.b().c()`` are skipped rather than guessed; a wrong type would corrupt
    FDP, and an omission only makes the metric conservative.
    """
    receiver = receiver.strip()
    if not receiver.isidentifier():
        return None
    if receiver in method.local_var_types:
        return method.local_var_types[receiver]
    if receiver in field_types:
        return field_types[receiver]
    if receiver[:1].isupper():
        # Capitalised bare identifier: a static access on a type.
        return receiver
    return None


# ----------------------------------------------------------------------
# Step 2: per-method metrics
# ----------------------------------------------------------------------
def compute_method_metrics(cls: ClassInfo, method: MethodInfo) -> dict[str, float]:
    """Fill and return ``method.metrics`` (CC/MLOC/NP came from the parser)."""
    atfd = len(method.foreign_accesses)
    own = len(method.own_field_accesses)
    total_attribute_accesses = own + atfd

    method.metrics["ATFD"] = float(atfd)
    method.metrics["FDP"] = float(len({t for t, _ in method.foreign_accesses}))
    # LAA: Locality of Attribute Accesses. A method that reads mostly other
    # objects' data (LAA well below 1) is the signature of Feature Envy.
    method.metrics["LAA"] = 1.0 if total_attribute_accesses == 0 else own / total_attribute_accesses
    method.metrics["NOAV"] = float(len(method.declared_locals) + total_attribute_accesses)
    method.metrics["CINT"] = float(
        len({t for t, _ in method.qualified_accesses}) + len(method.unqualified_calls)
    )
    return method.metrics


# ----------------------------------------------------------------------
# Step 3: per-class metrics
# ----------------------------------------------------------------------
def compute_class_metrics(cls: ClassInfo) -> dict[str, float]:
    methods = cls.methods
    non_ctor = [m for m in methods if not m.is_constructor]

    cls.metrics["NOM"] = float(len(non_ctor))
    cls.metrics["NOF"] = float(len(cls.fields))
    cls.metrics["CLOC"] = float(effective_loc(cls.source_lines))
    cls.metrics["WMC"] = float(sum(m.metrics.get("CC", 1.0) for m in methods))
    cls.metrics["AMW"] = cls.metrics["WMC"] / len(methods) if methods else 0.0
    cls.metrics["MAXCC"] = float(max((m.metrics.get("CC", 1.0) for m in methods), default=0.0))
    cls.metrics["TCC"] = _tight_class_cohesion(cls)
    cls.metrics["LCOM"] = _lcom_ck(cls)
    cls.metrics["LCOM3"] = _lcom_henderson_sellers(cls)
    cls.metrics["ATFD"] = float(len({access for m in methods for access in m.foreign_accesses}))
    cls.metrics["CBO"] = float(len(_coupled_types(cls)))
    cls.metrics["RFC"] = _response_for_class(cls)
    cls.metrics["WOC"] = _weight_of_class(cls)
    cls.metrics["NOPA"] = float(len([f for f in cls.fields if f.is_public and not f.is_constant]))
    cls.metrics["NOAM"] = float(len([m for m in methods if m.is_accessor]))
    return cls.metrics


def _tight_class_cohesion(cls: ClassInfo) -> float:
    """TCC (Bieman & Kang, 1995): share of visible method pairs that are connected.

    Two methods are *directly connected* when they access at least one instance
    field in common. Constructors are excluded: they touch every field by
    definition and would make any class look cohesive.
    """
    visible = [m for m in cls.instance_methods if m.is_public]
    if len(visible) < 2:
        return 1.0
    pairs = list(combinations(visible, 2))
    connected = sum(1 for a, b in pairs if a.own_field_accesses & b.own_field_accesses)
    return connected / len(pairs)


def _lcom_ck(cls: ClassInfo) -> float:
    """LCOM1 (Chidamber & Kemerer): disjoint pairs minus sharing pairs, floored at 0."""
    methods = [m for m in cls.methods if not m.is_constructor]
    if len(methods) < 2:
        return 0.0
    disjoint = sharing = 0
    for a, b in combinations(methods, 2):
        if a.own_field_accesses & b.own_field_accesses:
            sharing += 1
        else:
            disjoint += 1
    return float(max(0, disjoint - sharing))


def _lcom_henderson_sellers(cls: ClassInfo) -> float:
    """LCOM* (Henderson-Sellers, 1996), normalised to [0, 1].

    Preferred over LCOM1 for comparing classes of different sizes, because
    LCOM1 grows quadratically with the method count.
    """
    methods = [m for m in cls.methods if not m.is_constructor]
    fields = cls.fields
    m_count, f_count = len(methods), len(fields)
    if m_count <= 1 or f_count == 0:
        return 0.0
    accesses_per_field = [sum(1 for m in methods if f.name in m.own_field_accesses) for f in fields]
    mean_access = sum(accesses_per_field) / f_count
    return (mean_access - m_count) / (1 - m_count)


def _coupled_types(cls: ClassInfo) -> set[str]:
    types: set[str] = set()
    if cls.superclass:
        types.add(cls.superclass)
    types.update(cls.interfaces)
    types.update(f.type_name for f in cls.fields)
    for method in cls.methods:
        types.update(method.referenced_types)
        types.update(t for t, _ in method.foreign_accesses)
    return {t for t in types if t and t not in IGNORED_TYPES and t != cls.name}


def _response_for_class(cls: ClassInfo) -> float:
    """RFC: own methods plus every distinct method they can invoke."""
    called: set[str] = set()
    for method in cls.methods:
        called.update(method.unqualified_calls)
        called.update(f"{receiver}.{member}" for receiver, member in method.qualified_accesses)
    return float(len(cls.methods) + len(called))


def _weight_of_class(cls: ClassInfo) -> float:
    """WOC: share of public members that actually do something.

    A class whose public surface is nothing but getters and setters scores near
    zero, the defining property of a Data Class.
    """
    public_methods = [m for m in cls.methods if m.is_public and not m.is_constructor]
    public_fields = [f for f in cls.fields if f.is_public and not f.is_constant]
    total = len(public_methods) + len(public_fields)
    if total == 0:
        return 1.0
    functional = len([m for m in public_methods if not m.is_accessor])
    return functional / total


# ----------------------------------------------------------------------
# Step 4: metrics that need the whole project
# ----------------------------------------------------------------------
def compute_inheritance_metrics(project: ProjectModel) -> None:
    """DIT and NOC, resolved against the classes present in the project.

    A superclass outside the project (a framework base class) still counts as
    one level: the depth is real even when the ancestor is not analysed.
    """
    by_name = {c.name: c for c in project.classes}

    children: dict[str, int] = dict.fromkeys(by_name, 0)
    for cls in project.classes:
        if cls.superclass in children:
            children[cls.superclass] += 1

    for cls in project.classes:
        cls.metrics["DIT"] = float(_depth(cls, by_name, set()))
        cls.metrics["NOC"] = float(children.get(cls.name, 0))


def _depth(cls: ClassInfo, by_name: dict[str, ClassInfo], seen: set[str]) -> int:
    if cls.superclass is None:
        return 0
    if cls.name in seen:
        # Cyclic `extends` cannot compile, but a partial parse can produce one.
        return 0
    parent = by_name.get(cls.superclass)
    if parent is None:
        return 1
    return 1 + _depth(parent, by_name, seen | {cls.name})


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def compute_all(project: ProjectModel) -> ProjectModel:
    """Run every metric over an already-parsed project, in dependency order."""
    project_types = {c.name for c in project.classes}
    for cls in project.classes:
        resolve_accesses(cls, project_types)
        for method in cls.methods:
            compute_method_metrics(cls, method)
        compute_class_metrics(cls)
    compute_inheritance_metrics(project)
    return project


def metric_names() -> Iterable[str]:
    """Column order used by the CSV export and the ML feature matrix."""
    return (
        "CLOC",
        "NOM",
        "NOF",
        "WMC",
        "AMW",
        "MAXCC",
        "TCC",
        "LCOM",
        "LCOM3",
        "ATFD",
        "CBO",
        "RFC",
        "WOC",
        "NOPA",
        "NOAM",
        "DIT",
        "NOC",
    )
