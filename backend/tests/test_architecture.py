"""The layering `ENGINEERING.md` §2 declares, read off the imports themselves.

That section calls its rules "invariants that hold today and must keep holding",
and until now nothing held them: a `from javasmell.ml import ...` added inside
the refactor engine would pass lint, types, every test and CI, and the only
record that it was forbidden would be a sentence in a document.

Only the rules that section states in words are encoded here. An earlier attempt
ranked the packages by reading the arrow diagram as a dependency order and
reported four violations, every one of them false -- `parsing` importing `model`
is the base of the design, not a breach of it. A test that invents its own model
of the architecture measures the invention.

Imports are read with `ast` rather than by importing the packages, so a cycle or
a heavy optional dependency cannot turn an architectural check into an import
error.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "javasmell"


#: Packages whose contents are one layer. A top-level module such as `cli.py` or
#: `analysis.py` is its own name; `ENGINEERING.md` places neither in the chain,
#: so neither is constrained here beyond what the rules below say.
def _layer_of(path: Path) -> str:
    parts = path.relative_to(PACKAGE).parts
    return parts[0] if len(parts) > 1 else path.stem


def imports() -> dict[str, set[str]]:
    """Every within-package import, as layer -> layers it reaches for."""
    edges: dict[str, set[str]] = defaultdict(set)
    for source in PACKAGE.rglob("*.py"):
        layer = _layer_of(source)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            for name in names:
                if not name.startswith("javasmell."):
                    continue
                target = name.split(".")[1]
                if target != layer:
                    edges[layer].add(target)
    return dict(edges)


def test_the_model_is_plain_data_and_depends_on_nothing():
    """«plain data. No parsing logic, no metric logic, no I/O.»

    Everything else is defined against these types, so an import here would put
    the base of the design downstream of something and make the chain a cycle.
    """
    assert imports().get("model", set()) == set()


def test_the_two_consumers_of_detection_do_not_import_each_other():
    """«`ml/` and `refactor/` ... They do not import each other.»

    They are siblings on purpose: the classifier and the rewriter both read
    detector output, and a dependency either way would make one of them a
    detail of the other rather than an approach the thesis compares.
    """
    edges = imports()

    assert "refactor" not in edges.get("ml", set())
    assert "ml" not in edges.get("refactor", set())


def test_the_measuring_layers_never_reach_forward():
    """Parsing, the model, metrics and detectors sit left of everything else.

    None of them may reach for the classifier, the rewriter, the evaluation
    harness or the web layer. A metric that imported the evaluation harness
    would make the measurement depend on the thing that scores it.
    """
    forward = {"ml", "refactor", "api", "evaluation"}
    edges = imports()

    for layer in ("parsing", "model", "metrics", "detectors"):
        assert not (edges.get(layer, set()) & forward), f"{layer} reaches forward"


def test_nothing_inside_the_package_imports_the_web_layer():
    """`api/` is the outermost layer, so it is imported by the entry point alone.

    Anything else importing a route handler would be reaching through transport
    to get at logic that ought to live below it.
    """
    reaching = {layer for layer, targets in imports().items() if "api" in targets}

    assert reaching <= {"__main__"}, f"{sorted(reaching)} import the web layer"
