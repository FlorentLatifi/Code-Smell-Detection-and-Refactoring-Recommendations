"""Rule-based detection strategies.

Each detector is a direct transcription of a published strategy. Where a
strategy is composed of several conditions joined by AND, all of them must
hold; that conjunction is what keeps the false-positive rate down compared
with single-metric thresholding, and is the reason this approach is worth
measuring against the machine-learning one.

Detectors that need no cross-class information run on one class at a time;
this keeps the whole pass linear in the size of the project.
"""

from __future__ import annotations

from javasmell.detectors.base import Condition, Smell
from javasmell.detectors.thresholds import DEFAULT, Thresholds
from javasmell.model.entities import ClassInfo, MethodInfo, ProjectModel

# Fowler's catalogue entry (or entries) that address each smell. The refactor
# engine keys off these names, so they must stay stable.
REFACTORINGS = {
    "GodClass": ["ExtractClass", "MoveMethod", "ExtractSubclass"],
    "DataClass": ["EncapsulateField", "MoveMethod"],
    "LargeClass": ["ExtractClass", "ExtractSubclass"],
    "FeatureEnvy": ["MoveMethod", "ExtractMethod"],
    "LongMethod": ["ExtractMethod", "DecomposeConditional"],
    "BrainMethod": ["ExtractMethod", "ReplaceConditionalWithPolymorphism"],
    "LongParameterList": ["IntroduceParameterObject", "PreserveWholeObject"],
    "DeepNesting": ["ReplaceNestedConditionalWithGuardClauses", "ExtractMethod"],
}


def _skip(cls: ClassInfo) -> bool:
    """Interfaces and enums are excluded from class-level strategies.

    An interface has no state and no method bodies, so cohesion and complexity
    metrics are meaningless for it; flagging one would be a guaranteed false
    positive.
    """
    return cls.kind in {"interface", "enum"}


def _class_smell(cls: ClassInfo, smell_type: str, conditions: list[Condition]) -> Smell:
    return Smell(
        smell_type=smell_type,
        scope="class",
        class_name=cls.name,
        package=cls.package,
        file_path=cls.file_path,
        start_line=cls.start_line,
        end_line=cls.end_line,
        conditions=conditions,
        refactorings=REFACTORINGS[smell_type],
        metrics=dict(cls.metrics),
    )


def _method_smell(
    cls: ClassInfo, method: MethodInfo, smell_type: str, conditions: list[Condition]
) -> Smell:
    return Smell(
        smell_type=smell_type,
        scope="method",
        class_name=cls.name,
        package=cls.package,
        file_path=cls.file_path,
        start_line=method.start_line,
        end_line=method.end_line,
        conditions=conditions,
        refactorings=REFACTORINGS[smell_type],
        method=method.signature,
        metrics=dict(method.metrics),
    )


# ----------------------------------------------------------------------
# Class-level strategies
# ----------------------------------------------------------------------
def detect_god_class(cls: ClassInfo, t: Thresholds = DEFAULT) -> Smell | None:
    """God Class (Lanza & Marinescu, p. 80).

        WMC >= VERY_HIGH  AND  TCC < ONE_THIRD  AND  ATFD > FEW

    The three clauses capture the three symptoms together: the class does too
    much, its parts are unrelated, and it reaches into other objects' data.
    Any one alone would flag ordinary code.
    """
    if _skip(cls):
        return None
    clauses = god_class_clauses(cls, t)
    if not all(clause.satisfied for clause in clauses):
        return None
    return _class_smell(cls, "GodClass", clauses)


def god_class_clauses(cls: ClassInfo, t: Thresholds = DEFAULT) -> list[Condition]:
    """The three clauses, measured, whether or not they hold.

    Separate from the detector because a clause list that exists only when the
    strategy fires can explain a detection and never a miss. Recall for this
    strategy is under 0.10 on MLCQ, so *why* the other 90% did not fire is the
    more interesting half, and it is answerable only from the clauses that were
    evaluated and rejected.
    """
    return [
        Condition("WMC", ">=", t.god_class_wmc, cls.metrics.get("WMC", 0.0)),
        Condition("TCC", "<", t.god_class_tcc, cls.metrics.get("TCC", 1.0)),
        Condition("ATFD", ">", t.god_class_atfd, cls.metrics.get("ATFD", 0.0)),
    ]


def detect_data_class(cls: ClassInfo, t: Thresholds = DEFAULT) -> Smell | None:
    """Data Class (Lanza & Marinescu, p. 88).

        WOC < ONE_THIRD  AND  (
            (NOPA + NOAM > FEW  AND WMC < HIGH)
            OR
            (NOPA + NOAM > MANY AND WMC < VERY_HIGH)
        )

    The disjunction lets a larger data holder qualify only if its exposed
    surface is correspondingly larger; otherwise every small value object
    would be flagged.
    """
    if _skip(cls):
        return None
    interface, branch = data_class_clauses(cls, t)
    if not interface.satisfied:
        return None
    satisfied = [pair for pair in branch if all(clause.satisfied for clause in pair)]
    if not satisfied:
        return None
    # Dega e vogel ka perparesi kur te dyja qendrojne, sepse kufijte e saj jane
    # me te ngushte dhe gjetja duhet te citoje pragun qe e mban vertet.
    return _class_smell(cls, "DataClass", [interface, *satisfied[0]])


def data_class_clauses(
    cls: ClassInfo, t: Thresholds = DEFAULT
) -> tuple[Condition, tuple[tuple[Condition, Condition], ...]]:
    """The WOC clause, and the two branches of the disjunction behind it.

    Returned apart rather than as one flat list because the strategy is not a
    conjunction: the first clause must hold and then *either* pair must, so a
    caller that flattened them would have to rediscover which is which.
    """
    woc = cls.metrics.get("WOC", 1.0)
    wmc = cls.metrics.get("WMC", 0.0)
    exposed = cls.metrics.get("NOPA", 0.0) + cls.metrics.get("NOAM", 0.0)
    return (
        Condition("WOC", "<", t.data_class_woc, woc),
        (
            (
                Condition("NOPA+NOAM", ">", t.data_class_public_members, exposed),
                Condition("WMC", "<", t.data_class_wmc_low, wmc),
            ),
            (
                Condition("NOPA+NOAM", ">", t.data_class_public_members_many, exposed),
                Condition("WMC", "<", t.data_class_wmc_high, wmc),
            ),
        ),
    )


def detect_large_class(cls: ClassInfo, t: Thresholds = DEFAULT) -> Smell | None:
    """Large Class (Fowler): size alone, without the cohesion evidence.

        CLOC > HIGH_CLASS_LOC  OR  NOM > HIGH_NOM

    Reported separately from God Class on purpose. A class can be long and
    still cohesive, and conflating the two would hide which symptom the tool
    actually found.
    """
    if _skip(cls):
        return None
    clauses = large_class_clauses(cls, t)
    satisfied = [clause for clause in clauses if clause.satisfied]
    if not satisfied:
        return None
    # Vetem ato qe u plotesuan hyjne te gjetja: kjo eshte disjunksion, ndaj nje
    # klauzole e paplotesuar nuk e mban gjetjen dhe do te lexohej si e tille.
    return _class_smell(cls, "LargeClass", satisfied)


def large_class_clauses(cls: ClassInfo, t: Thresholds = DEFAULT) -> list[Condition]:
    """Both clauses of the disjunction, measured, whether or not they hold."""
    return [
        Condition("CLOC", ">", t.large_class_loc, cls.metrics.get("CLOC", 0.0)),
        Condition("NOM", ">", t.large_class_nom, cls.metrics.get("NOM", 0.0)),
    ]


# ----------------------------------------------------------------------
# Method-level strategies
# ----------------------------------------------------------------------
def detect_feature_envy(
    cls: ClassInfo, method: MethodInfo, t: Thresholds = DEFAULT
) -> Smell | None:
    """Feature Envy (Lanza & Marinescu, p. 84).

        ATFD > FEW  AND  LAA < ONE_THIRD  AND  FDP <= FEW

    The FDP clause is what separates envy from a dispatcher: a method that
    pulls data from many different classes is a coordinator, whereas one that
    pulls it from a single class belongs in that class.
    """
    if method.is_constructor or method.is_accessor:
        return None
    clauses = feature_envy_clauses(method, t)
    if not all(clause.satisfied for clause in clauses):
        return None
    return _method_smell(cls, method, "FeatureEnvy", clauses)


def feature_envy_clauses(method: MethodInfo, t: Thresholds = DEFAULT) -> list[Condition]:
    """The three clauses, measured, whether or not they hold."""
    return [
        Condition("ATFD", ">", t.feature_envy_atfd, method.metrics.get("ATFD", 0.0)),
        Condition("LAA", "<", t.feature_envy_laa, method.metrics.get("LAA", 1.0)),
        Condition("FDP", "<=", t.feature_envy_fdp, method.metrics.get("FDP", 0.0)),
    ]


def detect_long_method(cls: ClassInfo, method: MethodInfo, t: Thresholds = DEFAULT) -> Smell | None:
    """Long Method (Fowler): effective lines of code past the threshold.

        MLOC > 30

    Comment and blank lines are already excluded by the parser's LOC counter,
    so a well-documented method is not punished for its documentation.
    """
    clause = Condition("MLOC", ">", t.long_method_loc, method.metrics.get("MLOC", 0.0))
    if not clause.satisfied:
        return None
    return _method_smell(cls, method, "LongMethod", [clause])


def detect_brain_method(
    cls: ClassInfo, method: MethodInfo, t: Thresholds = DEFAULT
) -> Smell | None:
    """Brain Method (Lanza & Marinescu, p. 92).

        LOC > HIGH/2  AND  CC >= threshold  AND  MAXNESTING >= 3
        AND  NOAV > MANY

    A stricter, higher-confidence relative of Long Method: the method is not
    merely long, it concentrates the logic of its class.
    """
    clauses = brain_method_clauses(method, t)
    if not all(clause.satisfied for clause in clauses):
        return None
    return _method_smell(cls, method, "BrainMethod", clauses)


def brain_method_clauses(method: MethodInfo, t: Thresholds = DEFAULT) -> list[Condition]:
    """The four clauses, measured, whether or not they hold."""
    return [
        Condition("MLOC", ">", t.brain_method_loc, method.metrics.get("MLOC", 0.0)),
        Condition("CC", ">=", t.brain_method_cc, method.metrics.get("CC", 0.0)),
        Condition(
            "MAXNESTING", ">=", t.brain_method_nesting, method.metrics.get("MAXNESTING", 0.0)
        ),
        Condition("NOAV", ">", t.brain_method_noav, method.metrics.get("NOAV", 0.0)),
    ]


def detect_long_parameter_list(
    cls: ClassInfo, method: MethodInfo, t: Thresholds = DEFAULT
) -> Smell | None:
    """Long Parameter List (Fowler).

        NP > FEW

    The bound is the "few" quantifier rather than a number of its own: a
    parameter list is long when it exceeds what a reader holds at once, which is
    the same quantity the other strategies are written in.
    """
    clause = Condition("NP", ">", t.long_parameter_list_np, method.metrics.get("NP", 0.0))
    if not clause.satisfied:
        return None
    return _method_smell(cls, method, "LongParameterList", [clause])


def detect_deep_nesting(
    cls: ClassInfo, method: MethodInfo, t: Thresholds = DEFAULT
) -> Smell | None:
    """Deeply nested control flow.

        MAXNESTING > 3

    Not in Fowler's catalogue under this name, but it is the condition that
    ``Replace Nested Conditional with Guard Clauses`` exists to remove, and it
    is one of the transformations the refactor engine can apply mechanically.
    """
    clause = Condition("MAXNESTING", ">", t.deep_nesting, method.metrics.get("MAXNESTING", 0.0))
    if not clause.satisfied:
        return None
    return _method_smell(cls, method, "DeepNesting", [clause])


CLASS_DETECTORS = (detect_god_class, detect_data_class, detect_large_class)
METHOD_DETECTORS = (
    detect_feature_envy,
    detect_brain_method,
    detect_long_method,
    detect_long_parameter_list,
    detect_deep_nesting,
)


def detect_entity(
    cls: ClassInfo, method: MethodInfo | None, t: Thresholds = DEFAULT
) -> list[Smell]:
    """Every smell found at one entity: this class, or this one method.

    ``detect_in_class`` walks a whole class; the evaluation asks the narrower
    question, and asking it directly means a replay from stored metrics does not
    have to assemble a project around the single entity it wants to interrogate.
    """
    if method is None:
        return [s for detector in CLASS_DETECTORS if (s := detector(cls, t))]
    return [s for detector in METHOD_DETECTORS if (s := detector(cls, method, t))]


def detect_in_class(cls: ClassInfo, t: Thresholds = DEFAULT) -> list[Smell]:
    smells = detect_entity(cls, None, t)
    for method in cls.methods:
        smells.extend(detect_entity(cls, method, t))
    return smells


def detect_all(project: ProjectModel, t: Thresholds = DEFAULT) -> list[Smell]:
    """Every smell in the project, worst first.

    Ordering by severity rather than by file is deliberate: the tool's first
    screen should show what matters most, not whatever sorted first
    alphabetically.
    """
    smells = [s for cls in project.classes for s in detect_in_class(cls, t)]
    smells.sort(key=lambda s: (-s.score, s.file_path, s.start_line))
    return smells
