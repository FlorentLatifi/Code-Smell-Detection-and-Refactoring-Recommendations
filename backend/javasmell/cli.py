"""Command-line front-end.

Exists ahead of the web interface so the analysis core can be run against real
repositories, and so the experiment scripts for the Results chapter have a
scriptable entry point that does not depend on the API being up.

    python -m javasmell path/to/java/project
    python -m javasmell path/to/project --format csv --out smells.csv
    python -m javasmell path/to/project --format patch --out fixes.patch

The patch format is the only one that proposes a change rather than describing
one. It still writes nothing: the diff goes to stdout or to ``--out``, and
applying it stays the author's decision (ENGINEERING.md §4).

Exit codes are part of that scriptable contract, so each failure gets its own:
0 on success, 1 when the path was analysable but held no Java class, 2 when the
path itself is unusable. Giving the last two the same code is what let a
mistyped path in an experiment read as a project with nothing in it.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import TextIO

from javasmell.analysis import analyze_path
from javasmell.detectors.base import Smell
from javasmell.detectors.rules import detect_all
from javasmell.detectors.thresholds import DEFAULT
from javasmell.metrics.calculator import metric_names
from javasmell.model.entities import ProjectModel
from javasmell.refactor.patch import plan, unified

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="javasmell", description="Detect code smells in a Java project."
    )
    parser.add_argument("path", help="Directory or .java file to analyse")
    parser.add_argument(
        "--format",
        choices=("text", "json", "csv", "metrics", "patch"),
        default="text",
        help="text: readable report; metrics: the per-class feature matrix; "
        "patch: a unified diff of what the engine would rewrite",
    )
    parser.add_argument("--out", help="Write to this file instead of stdout")
    parser.add_argument(
        "--min-severity",
        choices=("minor", "major", "critical"),
        default="minor",
        help="Hide findings below this severity",
    )
    parser.add_argument("--smell", action="append", help="Only report this smell type (repeatable)")
    return parser


def _path_problem(path: str) -> str | None:
    """Why ``path`` cannot be analysed, or ``None`` if it can.

    ``iter_java_files`` yields nothing for a path that does not exist, so
    ``analyze_path`` hands back the same empty model it hands back for a
    directory holding no Java. The API never sees the difference, since
    ``api/paths.py`` has already established that the path exists; the CLI had
    no equivalent check, so a typo was answered with "No Java classes found",
    which reads as a fact about the project rather than a mistake in the
    command.

    The two shapes accepted here are the two ``iter_java_files`` actually walks:
    a directory, or a single ``.java`` file.
    """
    target = Path(path)
    if not target.exists():
        return f"No such file or directory: {path}"
    if not target.is_dir() and not path.endswith(".java"):
        return f"Not a directory or a .java file: {path}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    problem = _path_problem(args.path)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 2

    project = analyze_path(args.path)
    if not project.classes:
        print(f"No Java classes found under {args.path}", file=sys.stderr)
        return 1

    smells = detect_all(project, DEFAULT)
    cutoff = SEVERITY_ORDER[args.min_severity]
    smells = [s for s in smells if SEVERITY_ORDER[s.severity.value] <= cutoff]
    if args.smell:
        wanted = set(args.smell)
        smells = [s for s in smells if s.smell_type in wanted]

    if args.out:
        with Path(args.out).open("w", encoding="utf-8", newline="") as stream:
            _emit(args.format, project, smells, stream)
        # Reported only after the file closed cleanly; claiming a write that
        # raised half way through would be worse than saying nothing.
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        _emit(args.format, project, smells, sys.stdout)
    return 0


def _emit(fmt: str, project: ProjectModel, smells: list[Smell], stream: TextIO) -> None:
    if fmt == "json":
        json.dump([s.to_dict() for s in smells], stream, indent=2)
    elif fmt == "csv":
        _write_smell_csv(stream, smells)
    elif fmt == "metrics":
        _write_metric_csv(stream, project)
    elif fmt == "patch":
        _write_patch(stream, project, smells)
    else:
        _write_report(stream, project, smells)


def _write_patch(stream: TextIO, project: ProjectModel, smells: list[Smell]) -> None:
    """The diff to stdout, the account of it to stderr.

    Kept apart on purpose: the patch has to be pipeable into ``git apply``, so
    anything that is not diff goes to the other stream. A reader still gets told
    what was deferred and what was dropped, because a patch that silently omits
    half of what was found is one nobody can trust.
    """
    # A diff has to reach git byte for byte. On Windows a text stream rewrites
    # every "\n" as "\r\n", and against an LF source file every context line then
    # fails to match -- `git apply` reports trailing whitespace and refuses the
    # patch. `--out` already opens with newline="", but stdout does not, and
    # redirecting stdout is the usage this format documents.
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(newline="")

    javac = shutil.which("javac")
    result = plan(Path(project.root), smells, javac)
    stream.write(unified(result.patches))

    print(
        f"{result.changes} change(s) in {len(result.patches)} file(s)"
        + ("" if javac else "; javac not found, so verification stopped at syntax"),
        file=sys.stderr,
    )
    if result.declined:
        print(
            f"{result.declined} site(s) had no safe rewrite and were declined.",
            file=sys.stderr,
        )
    if result.deferred:
        print(
            f"{result.deferred} deferred: their edits overlap a change already in the patch. "
            "Apply this patch and run again to be offered them.",
            file=sys.stderr,
        )
    for drop in result.dropped:
        print(f"dropped {drop.relative}: {drop.verdict.value} -- {drop.detail}", file=sys.stderr)


def _write_report(stream: TextIO, project: ProjectModel, smells: list[Smell]) -> None:
    files = len(project.units)
    classes = len(project.classes)
    methods = sum(len(c.methods) for c in project.classes)
    print(f"Analysed {files} file(s), {classes} class(es), {methods} method(s)\n", file=stream)

    if not smells:
        print("No smells detected.", file=stream)
        return

    by_type = Counter(s.smell_type for s in smells)
    by_severity = Counter(s.severity.value for s in smells)
    print("Summary", file=stream)
    for smell_type, count in by_type.most_common():
        print(f"  {smell_type:<20} {count}", file=stream)
    print(
        "  "
        + "  ".join(
            f"{name}={by_severity.get(name, 0)}" for name in ("critical", "major", "minor")
        ),
        file=stream,
    )
    print(file=stream)

    for smell in smells:
        print(f"[{smell.severity.value.upper():<8}] {smell.smell_type}", file=stream)
        print(f"    {smell.location}", file=stream)
        print(f"    why: {smell.rationale}", file=stream)
        print(f"    fix: {', '.join(smell.refactorings)}", file=stream)
        print(file=stream)


def _write_smell_csv(stream: TextIO, smells: list[Smell]) -> None:
    writer = csv.writer(stream)
    writer.writerow(
        [
            "smell_type",
            "severity",
            "score",
            "package",
            "class",
            "method",
            "file",
            "start_line",
            "end_line",
            "rationale",
            "refactorings",
        ]
    )
    for s in smells:
        writer.writerow(
            [
                s.smell_type,
                s.severity.value,
                round(s.score, 3),
                s.package,
                s.class_name,
                s.method or "",
                s.file_path,
                s.start_line,
                s.end_line,
                s.rationale,
                "|".join(s.refactorings),
            ]
        )


def _write_metric_csv(stream: TextIO, project: ProjectModel) -> None:
    """The per-class feature matrix that the ML stage will train on."""
    columns = list(metric_names())
    writer = csv.writer(stream)
    writer.writerow(["package", "class", "file", "start_line", *columns])
    for cls in project.classes:
        writer.writerow(
            [
                cls.package,
                cls.name,
                cls.file_path,
                cls.start_line,
                *[round(cls.metrics.get(name, 0.0), 4) for name in columns],
            ]
        )


if __name__ == "__main__":
    raise SystemExit(main())
