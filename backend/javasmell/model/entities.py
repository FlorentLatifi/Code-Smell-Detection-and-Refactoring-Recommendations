"""Language-independent model of the Java source code under analysis.

The parser fills these structures; the metric calculators only ever read them.
Keeping the two apart means a second front-end (another language, another
parser) can be plugged in without touching the metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ACCESSOR_PREFIXES = ("get", "set", "is", "has")


@dataclass(frozen=True)
class ParameterInfo:
    name: str
    type_name: str


@dataclass
class FieldInfo:
    name: str
    type_name: str
    modifiers: frozenset[str]
    line: int

    @property
    def is_static(self) -> bool:
        return "static" in self.modifiers

    @property
    def is_public(self) -> bool:
        return "public" in self.modifiers

    @property
    def is_constant(self) -> bool:
        return "static" in self.modifiers and "final" in self.modifiers


@dataclass
class MethodInfo:
    """A method or constructor, plus everything its body touches.

    The ``*_accesses`` sets are what the cohesion and coupling metrics are
    computed from, so they are collected once during parsing rather than by
    re-walking the tree per metric.
    """

    name: str
    return_type: str | None
    parameters: list[ParameterInfo]
    modifiers: frozenset[str]
    start_line: int
    end_line: int
    is_constructor: bool = False

    # --- collected during parsing -------------------------------------
    declared_locals: set[str] = field(default_factory=set)
    bare_names: set[str] = field(default_factory=set)
    this_accesses: set[str] = field(default_factory=set)
    # (receiver expression text, member name). Fields and calls are kept apart
    # because ATFD counts foreign *data*, while a behavioural call is coupling.
    qualified_field_accesses: set[tuple[str, str]] = field(default_factory=set)
    qualified_calls: set[tuple[str, str]] = field(default_factory=set)
    unqualified_calls: set[str] = field(default_factory=set)
    referenced_types: set[str] = field(default_factory=set)
    local_var_types: dict[str, str] = field(default_factory=dict)

    # --- filled by the metric calculators ------------------------------
    metrics: dict[str, float] = field(default_factory=dict)
    # Resolved once the declaring class is known.
    own_field_accesses: set[str] = field(default_factory=set)
    foreign_accesses: set[tuple[str, str]] = field(default_factory=set)

    @property
    def is_static(self) -> bool:
        return "static" in self.modifiers

    @property
    def is_public(self) -> bool:
        return "public" in self.modifiers

    @property
    def is_abstract(self) -> bool:
        return "abstract" in self.modifiers

    @property
    def qualified_accesses(self) -> set[tuple[str, str]]:
        """Fields and calls together, for metrics that do not distinguish them."""
        return self.qualified_field_accesses | self.qualified_calls

    @property
    def parameter_count(self) -> int:
        return len(self.parameters)

    @property
    def signature(self) -> str:
        params = ", ".join(p.type_name for p in self.parameters)
        return f"{self.name}({params})"

    @property
    def is_accessor(self) -> bool:
        """Getter/setter heuristic used by WOC and the Data Class detector.

        Name prefix alone is not enough: ``getConnectionOrFail`` may hold real
        logic, so the body must also be trivial (a handful of lines).
        """
        if self.is_constructor:
            return False
        if not self.name.startswith(ACCESSOR_PREFIXES):
            return False
        return (self.end_line - self.start_line) <= 3


@dataclass
class ClassInfo:
    name: str
    kind: str  # class | interface | enum | record
    package: str
    file_path: str
    modifiers: frozenset[str]
    superclass: str | None
    interfaces: list[str]
    fields: list[FieldInfo]
    methods: list[MethodInfo]
    start_line: int
    end_line: int
    source_lines: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        return f"{self.package}.{self.name}" if self.package else self.name

    @property
    def field_names(self) -> set[str]:
        return {f.name for f in self.fields}

    @property
    def field_types(self) -> dict[str, str]:
        return {f.name: f.type_name for f in self.fields}

    @property
    def instance_methods(self) -> list[MethodInfo]:
        return [m for m in self.methods if not m.is_static and not m.is_constructor]


@dataclass
class CompilationUnit:
    file_path: str
    package: str
    imports: list[str]
    classes: list[ClassInfo]
    # tree-sitter recovers from syntax it cannot parse instead of failing, so a
    # file may yield a plausible but incomplete class list. Real corpora contain
    # such files: Hadoop's Hamlet.java uses `_` as a method name, illegal since
    # Java 9, and a silently truncated parse would look like a missing entity.
    has_syntax_errors: bool = False


@dataclass
class ProjectModel:
    """Every compilation unit of one analysed project."""

    root: str
    units: list[CompilationUnit] = field(default_factory=list)

    @property
    def classes(self) -> list[ClassInfo]:
        return [c for u in self.units for c in u.classes]

    def class_by_name(self, name: str) -> ClassInfo | None:
        """Look up by simple or qualified name.

        Simple names are ambiguous across packages; the first match wins, which
        is accurate enough for the metrics that use it (DIT/NOC) and avoids a
        full symbol-resolution pass.
        """
        for c in self.classes:
            if c.name == name or c.qualified_name == name:
                return c
        return None
