"""Metric tests.

Every expected value below is derived by hand from the fixture, not captured
from a previous run; a snapshot test would happily lock in a wrong formula.
The derivation is written next to each assertion so the numbers can be checked
against the definitions in Chidamber & Kemerer (1994) and Lanza & Marinescu
(2006) without re-reading the implementation.
"""

from __future__ import annotations

import pathlib
from pathlib import Path

import pytest

from javasmell.analysis import analyze_path, analyze_source
from javasmell.parsing.java_parser import effective_loc, iter_java_files

FIXTURES = str(Path(__file__).parent / "fixtures")


@pytest.fixture(scope="module")
def project():
    return analyze_path(FIXTURES)


def find_class(project, name):
    cls = next((c for c in project.classes if c.name == name), None)
    assert cls is not None, f"class {name} not found"
    return cls


def find_method(cls, name):
    method = next((m for m in cls.methods if m.name == name), None)
    assert method is not None, f"method {name} not found on {cls.name}"
    return method


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------
def test_package_and_classes_are_parsed(project):
    assert {c.name for c in project.classes} == {
        "Warehouse",
        "Item",
        "InvoicePrinter",
        "OrderManager",
        "Customer",
    }
    assert all(c.package == "com.example.shop" for c in project.classes)


def test_field_modifiers_and_types(project):
    item = find_class(project, "Item")
    price = next(f for f in item.fields if f.name == "price")
    assert price.type_name == "double"
    assert price.is_public

    warehouse = find_class(project, "Warehouse")
    stock = next(f for f in warehouse.fields if f.name == "stock")
    # Generics are erased: List<Item> is recorded as List.
    assert stock.type_name == "List"


def test_constructor_is_not_counted_as_a_method(project):
    warehouse = find_class(project, "Warehouse")
    # 5 declarations, one of which is the constructor.
    assert len(warehouse.methods) == 5
    assert warehouse.metrics["NOM"] == 4


# ----------------------------------------------------------------------
# Size and complexity
# ----------------------------------------------------------------------
def test_cyclomatic_complexity_counts_every_decision_point():
    source = """
    class Sample {
        int run(int a, int b) {
            if (a > 0 && b > 0) {          // if + && -> 2
                for (int i = 0; i < a; i++) {   // for -> 1
                    a += i;
                }
            }
            try {
                a = a / b;
            } catch (Exception e) {        // catch -> 1
                a = 0;
            }
            return a > b ? a : b;          // ternary -> 1
        }
    }
    """
    project = analyze_source(source)
    run = find_method(find_class(project, "Sample"), "run")
    assert run.metrics["CC"] == 6.0  # base 1 + 5 decision points
    assert run.metrics["NP"] == 2.0
    assert run.metrics["MAXNESTING"] == 2.0  # if -> for


def test_wmc_is_the_sum_of_method_complexity(project):
    item = find_class(project, "Item")
    # Six accessors, each with complexity 1.
    assert item.metrics["WMC"] == 6.0
    assert item.metrics["AMW"] == 1.0


def test_switch_default_is_not_a_decision():
    source = """
    class Sample {
        int pick(int a) {
            switch (a) {
                case 1: return 1;
                case 2: return 2;
                default: return 0;
            }
        }
    }
    """
    project = analyze_source(source)
    pick = find_method(find_class(project, "Sample"), "pick")
    assert pick.metrics["CC"] == 3.0  # base 1 + two cases, default excluded


# ----------------------------------------------------------------------
# Cohesion
# ----------------------------------------------------------------------
def test_tcc_of_a_data_class_is_low(project):
    item = find_class(project, "Item")
    # 6 public methods -> 15 pairs; only get/set of the same field are
    # connected -> 3 pairs. 3/15 = 0.2
    assert item.metrics["TCC"] == pytest.approx(0.2)


def test_tcc_excludes_constructors(project):
    warehouse = find_class(project, "Warehouse")
    # 4 public instance methods -> 6 pairs. add/size share `stock`,
    # getLocation/setLocation share `location` -> 2 connected pairs.
    assert warehouse.metrics["TCC"] == pytest.approx(2 / 6)


def test_lcom_variants(project):
    item = find_class(project, "Item")
    # LCOM1 = |disjoint pairs| - |sharing pairs| = 12 - 3 = 9
    assert item.metrics["LCOM"] == 9.0
    # LCOM* = (mean accesses per field - m) / (1 - m) = (2 - 6) / (1 - 6) = 0.8
    assert item.metrics["LCOM3"] == pytest.approx(0.8)


def test_cohesive_class_has_no_lcom_penalty():
    source = """
    class Counter {
        private int value;
        public void inc() { value++; }
        public int get() { return value; }
    }
    """
    project = analyze_source(source)
    counter = find_class(project, "Counter")
    assert counter.metrics["TCC"] == 1.0
    assert counter.metrics["LCOM"] == 0.0


# ----------------------------------------------------------------------
# Foreign data: the basis of Feature Envy detection
# ----------------------------------------------------------------------
def test_feature_envy_signature(project):
    printer = find_class(project, "InvoicePrinter")
    describe = find_method(printer, "describe")
    # Three accessor calls plus three direct field reads, all on Item.
    assert describe.metrics["ATFD"] == 6.0
    assert describe.metrics["FDP"] == 1.0
    # No own attribute is touched, so locality is zero.
    assert describe.metrics["LAA"] == 0.0


def test_own_fields_are_not_foreign_data(project):
    warehouse = find_class(project, "Warehouse")
    add = find_method(warehouse, "add")
    assert add.own_field_accesses == {"stock"}
    assert add.metrics["ATFD"] == 0.0
    assert add.metrics["LAA"] == 1.0


def test_local_variable_shadows_a_field():
    source = """
    class Shadow {
        private int value;
        public void run() {
            int value = 3;
            System.out.println(value);
        }
    }
    """
    project = analyze_source(source)
    run = find_method(find_class(project, "Shadow"), "run")
    # `value` is a local here, so it must not register as a field access.
    assert run.own_field_accesses == set()


def test_jdk_calls_do_not_inflate_foreign_data():
    source = """
    class Sample {
        public int len(String text) {
            return text.length() + Math.abs(-1);
        }
    }
    """
    project = analyze_source(source)
    sample = find_method(find_class(project, "Sample"), "len")
    assert sample.metrics["ATFD"] == 0.0


# ----------------------------------------------------------------------
# Data Class indicators
# ----------------------------------------------------------------------
def test_woc_is_zero_for_a_pure_data_holder(project):
    item = find_class(project, "Item")
    assert item.metrics["WOC"] == 0.0
    assert item.metrics["NOPA"] == 3.0
    assert item.metrics["NOAM"] == 6.0


def test_woc_counts_functional_methods(project):
    warehouse = find_class(project, "Warehouse")
    # Public members: add, size, getLocation, setLocation. Two are functional.
    assert warehouse.metrics["WOC"] == pytest.approx(0.5)


def test_long_accessor_is_not_treated_as_an_accessor():
    source = """
    class Sample {
        private int value;
        public int getValue() {
            int result = value;
            result = result * 2;
            result = result + 1;
            log(result);
            return result;
        }
        private void log(int v) { }
    }
    """
    project = analyze_source(source)
    getter = find_method(find_class(project, "Sample"), "getValue")
    assert not getter.is_accessor


# ----------------------------------------------------------------------
# Inheritance
# ----------------------------------------------------------------------
def test_dit_and_noc_across_the_project():
    source = """
    class Base { }
    class Middle extends Base { }
    class Leaf extends Middle { }
    class Other extends Middle { }
    """
    project = analyze_source(source)
    assert find_class(project, "Base").metrics["DIT"] == 0.0
    assert find_class(project, "Middle").metrics["DIT"] == 1.0
    assert find_class(project, "Leaf").metrics["DIT"] == 2.0
    assert find_class(project, "Base").metrics["NOC"] == 1.0
    assert find_class(project, "Middle").metrics["NOC"] == 2.0


def test_superclass_outside_the_project_still_counts_one_level():
    source = "class Handler extends javax.servlet.http.HttpServlet { }"
    project = analyze_source(source)
    assert find_class(project, "Handler").metrics["DIT"] == 1.0


# ----------------------------------------------------------------------
# Robustness
# ----------------------------------------------------------------------
def test_modern_java_syntax_parses():
    source = """
    public record Point(int x, int y) {
        public int sum() { return x + y; }
    }
    interface Shape {
        double area();
        default String label() { return "shape"; }
    }
    """
    project = analyze_source(source)
    assert find_class(project, "Point").kind == "record"
    shape = find_class(project, "Shape")
    assert shape.kind == "interface"
    # An abstract method has no body and therefore no decision points.
    assert find_method(shape, "area").metrics["CC"] == 1.0


def test_nested_class_is_reported_separately():
    source = """
    class Outer {
        private int a;
        static class Inner {
            private int b;
            public int get() { return b; }
        }
    }
    """
    project = analyze_source(source)
    assert {c.name for c in project.classes} == {"Outer", "Inner"}
    assert find_class(project, "Inner").metrics["NOF"] == 1.0


def test_varargs_parameter_is_counted():
    source = """
    class Sample {
        public int total(int base, int... rest) { return base; }
    }
    """
    project = analyze_source(source)
    total = find_method(find_class(project, "Sample"), "total")
    assert total.metrics["NP"] == 2.0


# ----------------------------------------------------------------------
# Fields the language declares on your behalf
#
# None of these three appear as a `field_declaration` in the parse tree, so
# each needs the modifiers Java grants it implicitly. Getting that wrong is not
# cosmetic: `is_constant` decides whether a field counts towards NOPA and WOC,
# which is what the Data Class detector reads.
# ----------------------------------------------------------------------
def test_enum_members_are_measured():
    source = """
    public enum Planet {
        MERCURY(3.3e23), VENUS(4.87e24);
        private final double mass;
        Planet(double mass) { this.mass = mass; }
        public double mass() { return mass; }
    }
    """
    planet = find_class(analyze_source(source), "Planet")
    # MERCURY and VENUS are fields of type Planet (JLS 8.9.3), plus `mass`.
    assert planet.metrics["NOF"] == 3.0
    # NOM excludes constructors, so only mass().
    assert planet.metrics["NOM"] == 1.0
    # WMC counts the constructor too: CC 1 each, neither branches.
    assert planet.metrics["WMC"] == 2.0
    # A constant is public but not "public attribute"; NOPA stays 0.
    assert planet.metrics["NOPA"] == 0.0
    assert all(f.is_constant for f in planet.fields if f.name in {"MERCURY", "VENUS"})


def test_interface_constants_are_fields():
    source = """
    interface Repository {
        int MAX_RESULTS = 100;
        void save(String key);
        default boolean isEmpty() { return true; }
    }
    """
    repo = find_class(analyze_source(source), "Repository")
    assert repo.metrics["NOF"] == 1.0
    assert repo.metrics["NOM"] == 2.0
    # JLS 9.3: implicitly public static final, so a constant and not an attribute.
    assert repo.metrics["NOPA"] == 0.0
    assert repo.fields[0].is_constant


def test_record_components_are_fields():
    source = """
    public record Money(long amount, String currency) {
        public Money plus(Money other) { return new Money(amount + other.amount, currency); }
    }
    """
    money = find_class(analyze_source(source), "Money")
    # JLS 8.10.3: the header declares one private final field per component.
    assert money.metrics["NOF"] == 2.0
    assert [f.name for f in money.fields] == ["amount", "currency"]
    assert money.metrics["NOM"] == 1.0
    # Private, so no public attribute; final but not static, so not a constant.
    assert money.metrics["NOPA"] == 0.0
    assert not any(f.is_constant for f in money.fields)


# ----------------------------------------------------------------------
# Effective LOC: one rule, shared by MLOC and CLOC
# ----------------------------------------------------------------------

LAMBDA_SOURCE = """class Runner {
    void go() {
        run(() -> {
            step();
        });
    }
}
"""


def test_delimiter_only_lines_are_not_statements():
    """Counted by hand, line by line.

    `void go() {`, `run(() -> {` and `step();` carry logic: three lines.
    `});` and the two bare `}` close constructs that earlier lines already
    opened, so under Park's logical-statement view they are not statements.
    """
    cls = find_class(analyze_source(LAMBDA_SOURCE), "Runner")
    assert find_method(cls, "go").metrics["MLOC"] == 3
    # The class adds only its own `class Runner {` header to those three.
    assert cls.metrics["CLOC"] == 4


def test_mloc_and_cloc_apply_the_same_rule():
    """Regression: the two counts once disagreed on `});`.

    MLOC excluded it and CLOC did not, so a method and its enclosing class
    measured the same source differently while both fed size detectors.
    """
    cls = find_class(analyze_source(LAMBDA_SOURCE), "Runner")
    method = find_method(cls, "go")
    # The class is the method plus exactly one more line of logic: its header.
    assert cls.metrics["CLOC"] - method.metrics["MLOC"] == 1


@pytest.mark.parametrize("line", ["}", "{", "};", "});", ");", "},", ")", ";", "}));"])
def test_a_line_of_pure_delimiters_counts_as_nothing(line):
    assert effective_loc([line]) == 0


@pytest.mark.parametrize("line", ["} else {", "return x;", "}; // note", "int[] a = {1};"])
def test_a_line_with_any_content_counts(line):
    """`} else {` is the case that must not be swallowed: it carries control flow."""
    assert effective_loc([line]) == 1


def test_comments_and_blanks_are_still_excluded():
    lines = ["// a", "", "  ", "/* block", "   still block", "*/", "int x = 1;"]
    assert effective_loc(lines) == 1


# ----------------------------------------------------------------------
# Walking the syntax tree without recursing
# ----------------------------------------------------------------------


def test_a_deeply_nested_expression_does_not_overflow_the_stack():
    """Syntax-tree depth is not bounded by how the source looks.

    1200 concatenations are one line of Java and 1200 levels of left-nested
    `binary_expression`. Walking that by recursion exhausted Python's stack,
    and since analyze_path only skips a file on OSError, the RecursionError
    aborted every repository after the one that contained such a file.
    """
    source = "class Deep { String s = " + " + ".join(['"a"'] * 1200) + "; }"
    project = analyze_source(source)
    assert [c.name for c in project.classes] == ["Deep"]


def test_nested_types_are_reported_in_source_order():
    """Pre-order: a type, then its own nested types, then its later siblings.

    Worth pinning because the iterative walk has to reverse each batch of
    children to reproduce the order recursion gave for free.
    """
    source = """
    class Outer {
      class A { class A1 {} class A2 {} }
      class B { class B1 {} }
      class C {}
    }
    """
    project = analyze_source(source)
    assert [c.name for c in project.classes] == ["Outer", "A", "A1", "A2", "B", "B1", "C"]


# ----------------------------------------------------------------------
# Which files the walk picks up
# ----------------------------------------------------------------------


def test_build_output_is_skipped_but_a_package_of_the_same_name_is_not(tmp_path):
    """`target`, `build`, `out` and `bin` are both output dirs and package names.

    Maven writes to `<module>/target/`; Eclipse writes to `<project>/bin/`.
    Neither sits under `src/`. A package always does, and MLCQ reviewed real
    classes in packages named exactly these -- org.eclipse.tycho.p2.target and
    com.google.caliper.runner.target among them -- so pruning by name alone
    dropped source that had been reviewed.
    """
    written = {
        "src/main/java/com/acme/target/Kept.java",  # a package called target
        "src/main/java/com/acme/build/Kept.java",  # a package called build
        "src/out/Kept.java",
        "target/classes/Generated.java",  # genuine Maven output
        "bin/Compiled.java",  # genuine Eclipse output
        "node_modules/dep/Bundled.java",
        "src/main/java/com/acme/Plain.java",
    }
    for relative in written:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("class C {}", encoding="utf-8")

    found = {
        str(pathlib.Path(f).relative_to(tmp_path)).replace("\\", "/")
        for f in iter_java_files(str(tmp_path))
    }
    assert found == {
        "src/main/java/com/acme/target/Kept.java",
        "src/main/java/com/acme/build/Kept.java",
        "src/out/Kept.java",
        "src/main/java/com/acme/Plain.java",
    }
