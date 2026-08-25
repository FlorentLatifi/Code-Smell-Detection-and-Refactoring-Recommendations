"""Top-level entry point: source tree in, fully measured project model out."""

from __future__ import annotations

from javasmell.metrics.calculator import compute_all
from javasmell.model.entities import ProjectModel
from javasmell.parsing.java_parser import JavaParser, iter_java_files


def analyze_path(root: str) -> ProjectModel:
    """Parse and measure every ``.java`` file under ``root``.

    Files that fail to parse are skipped rather than aborting the run: a real
    repository usually contains at least one file that does not compile, and
    one bad file should not cost the whole analysis.
    """
    parser = JavaParser()
    project = ProjectModel(root=root)
    for path in iter_java_files(root):
        try:
            project.units.append(parser.parse_file(path))
        except (OSError, UnicodeDecodeError):
            continue
    return compute_all(project)


def analyze_source(source: str, path: str = "<memory>") -> ProjectModel:
    """Measure a single in-memory source file. Used by the tests and the API."""
    parser = JavaParser()
    project = ProjectModel(root=path)
    project.units.append(parser.parse_source(source, path))
    return compute_all(project)
