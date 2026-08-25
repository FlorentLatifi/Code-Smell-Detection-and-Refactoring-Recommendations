"""Detector tests.

Two properties matter more than raw coverage here:

* a strategy must fire when *all* of its conditions hold, and
* it must stay silent when only some of them do.

The second is what the conjunction is for, so nearly every positive test below
has a negative twin that changes exactly one condition.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from javasmell.analysis import analyze_path, analyze_source
from javasmell.detectors.base import Severity
from javasmell.detectors.rules import detect_all, detect_in_class
from javasmell.detectors.thresholds import Thresholds

FIXTURES = str(Path(__file__).parent / "fixtures")


@pytest.fixture(scope="module")
def project():
    return analyze_path(FIXTURES)


def smells_of(project, smell_type):
    return [s for s in detect_all(project) if s.smell_type == smell_type]


def build_god_class(*, cohesive: bool, envious: bool, methods: int = 16) -> str:
    """Generate a class that crosses the God Class thresholds on demand.

    Written as a generator rather than a checked-in fixture because the
    strategy needs WMC >= 47, which takes roughly fifty lines of filler that
    would say nothing a reader could not infer from the parameters.
    """
    lines = ["class Beast {"]
    for i in range(methods):
        lines.append(f"    private int field{i};")
    lines.append("    private Helper helper = new Helper();")
    # Each method has complexity 3 (base + if + &&), so WMC = 3 * methods.
    for i in range(methods):
        # A cohesive variant has every method touch the same field.
        target = "field0" if cohesive else f"field{i}"
        lines.append(f"    public int op{i}(int a) {{")
        lines.append(f"        if (a > 0 && {target} > 0) {{ {target} = a; }}")
        lines.append(f"        return {target};")
        lines.append("    }")
    if envious:
        reads = " + ".join(f"helper.value{i}" for i in range(6))
        lines.append(f"    public int drain() {{ return {reads}; }}")
    lines.append("}")
    lines.append("class Helper {")
    for i in range(6):
        lines.append(f"    public int value{i};")
    lines.append("}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# God Class
# ----------------------------------------------------------------------
def test_god_class_fires_when_all_conditions_hold():
    project = analyze_source(build_god_class(cohesive=False, envious=True))
    beast = next(c for c in project.classes if c.name == "Beast")
    assert beast.metrics["WMC"] >= 47
    assert beast.metrics["TCC"] < 1 / 3
    assert beast.metrics["ATFD"] > 5

    found = [s for s in detect_in_class(beast) if s.smell_type == "GodClass"]
    assert len(found) == 1
    assert found[0].severity is not Severity.MINOR
    assert {c.metric for c in found[0].conditions} == {"WMC", "TCC", "ATFD"}


def test_god_class_stays_silent_when_the_class_is_cohesive():
    project = analyze_source(build_god_class(cohesive=True, envious=True))
    beast = next(c for c in project.classes if c.name == "Beast")
    assert beast.metrics["WMC"] >= 47  # still big
    assert beast.metrics["TCC"] >= 1 / 3  # but its methods belong together
    assert not [s for s in detect_in_class(beast) if s.smell_type == "GodClass"]


def test_god_class_stays_silent_without_foreign_data():
    project = analyze_source(build_god_class(cohesive=False, envious=False))
    beast = next(c for c in project.classes if c.name == "Beast")
    assert beast.metrics["ATFD"] == 0
    assert not [s for s in detect_in_class(beast) if s.smell_type == "GodClass"]


def test_large_class_is_reported_independently_of_god_class():
    project = analyze_source(build_god_class(cohesive=True, envious=False, methods=25))
    beast = next(c for c in project.classes if c.name == "Beast")
    types = {s.smell_type for s in detect_in_class(beast)}
    # Long but cohesive: size is reported, the design verdict is not.
    assert "LargeClass" in types
    assert "GodClass" not in types


# ----------------------------------------------------------------------
# Data Class
# ----------------------------------------------------------------------
def test_data_class_detected(project):
    flagged = {s.class_name for s in smells_of(project, "DataClass")}
    assert "Item" in flagged
    assert "Customer" in flagged
    # Warehouse has real behaviour (add, size), so it must not be flagged.
    assert "Warehouse" not in flagged


def test_data_class_needs_a_wide_public_surface():
    source = """
    class Tiny {
        private int a;
        public int getA() { return a; }
    }
    """
    project = analyze_source(source)
    tiny = next(c for c in project.classes if c.name == "Tiny")
    # WOC is 0, but a single accessor is not a data class.
    assert tiny.metrics["WOC"] == 0.0
    assert not [s for s in detect_in_class(tiny) if s.smell_type == "DataClass"]


# ----------------------------------------------------------------------
# Feature Envy
# ----------------------------------------------------------------------
def test_feature_envy_detected(project):
    envy = smells_of(project, "FeatureEnvy")
    targets = {(s.class_name, s.method.split("(")[0]) for s in envy}
    assert ("InvoicePrinter", "describe") in targets


def test_feature_envy_ignores_methods_that_use_their_own_data(project):
    envy = smells_of(project, "FeatureEnvy")
    assert not any(s.class_name == "Warehouse" for s in envy)


def test_dispatcher_across_many_classes_is_not_envy():
    source = """
    class A { public int x; }
    class B { public int x; }
    class C { public int x; }
    class D { public int x; }
    class E { public int x; }
    class F { public int x; }
    class Dispatcher {
        public int sum(A a, B b, C c, D d, E e, F f) {
            return a.x + b.x + c.x + d.x + e.x + f.x;
        }
    }
    """
    project = analyze_source(source)
    dispatcher = next(c for c in project.classes if c.name == "Dispatcher")
    method = dispatcher.methods[0]
    assert method.metrics["ATFD"] == 6.0  # plenty of foreign data
    assert method.metrics["FDP"] == 6.0  # but spread over six providers
    assert not [s for s in detect_in_class(dispatcher) if s.smell_type == "FeatureEnvy"]


def test_accessors_are_never_envious():
    source = """
    class Wrapper {
        private Inner inner;
        public int getA() { return inner.a; }
    }
    class Inner { public int a; }
    """
    project = analyze_source(source)
    wrapper = next(c for c in project.classes if c.name == "Wrapper")
    assert not [s for s in detect_in_class(wrapper) if s.smell_type == "FeatureEnvy"]


# ----------------------------------------------------------------------
# Method-level size rules
# ----------------------------------------------------------------------
def test_long_parameter_list(project):
    flagged = smells_of(project, "LongParameterList")
    assert any(s.method.startswith("priceOrder") for s in flagged)


def test_five_parameters_are_allowed():
    source = "class S { void f(int a, int b, int c, int d, int e) { } }"
    project = analyze_source(source)
    cls = project.classes[0]
    assert not [s for s in detect_in_class(cls) if s.smell_type == "LongParameterList"]


def test_deep_nesting(project):
    flagged = smells_of(project, "DeepNesting")
    assert any(s.method.startswith("priceOrder") for s in flagged)


# ----------------------------------------------------------------------
# Interfaces and enums
# ----------------------------------------------------------------------
def test_interfaces_are_not_class_smells():
    source = """
    interface Repository {
        void a(); void b(); void c(); void d(); void e();
        void f(); void g(); void h(); void i(); void j();
        void k(); void l(); void m(); void n(); void o();
        void p(); void q(); void r(); void s(); void t();
        void u(); void v();
    }
    """
    project = analyze_source(source)
    repo = project.classes[0]
    assert repo.metrics["NOM"] == 22.0  # would trip Large Class if not skipped
    assert detect_in_class(repo) == []


# ----------------------------------------------------------------------
# Severity and configuration
# ----------------------------------------------------------------------
def test_severity_grows_with_the_excess():
    mild = """
    class Mild { void f(int a, int b, int c, int d, int e, int g) { } }
    """
    severe = """
    class Severe {
        void f(int a, int b, int c, int d, int e, int g,
               int h, int i, int j, int k, int l, int m,
               int n, int o, int p, int q, int r, int s) { }
    }
    """
    mild_smell = detect_in_class(analyze_source(mild).classes[0])[0]
    severe_smell = detect_in_class(analyze_source(severe).classes[0])[0]
    assert mild_smell.severity is Severity.MINOR
    assert severe_smell.severity is Severity.CRITICAL
    assert severe_smell.score > mild_smell.score


def test_thresholds_are_configurable(project):
    """The Results chapter sweeps thresholds, so they must not be baked in."""
    strict = Thresholds(long_parameter_list_np=3)
    lenient = Thresholds(long_parameter_list_np=20)
    strict_count = len(
        [s for s in detect_all(project, strict) if s.smell_type == "LongParameterList"]
    )
    lenient_count = len(
        [s for s in detect_all(project, lenient) if s.smell_type == "LongParameterList"]
    )
    assert strict_count > lenient_count
    assert lenient_count == 0


def test_results_are_sorted_worst_first(project):
    scores = [s.score for s in detect_all(project)]
    assert scores == sorted(scores, reverse=True)


def test_smell_serialises_for_the_api(project):
    smell = detect_all(project)[0]
    payload = smell.to_dict()
    assert payload["severity"] in {"minor", "major", "critical"}
    assert payload["smell_type"]
    assert payload["refactorings"]
    assert isinstance(payload["metrics"], dict)
