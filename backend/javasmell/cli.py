"""Command-line front-end.

Exists ahead of the web interface so the analysis core can be run against real
repositories -- and so the experiment scripts for the Results chapter have a
scriptable entry point that does not depend on the API being up.

    python -m javasmell path/to/java/project
    python -m javasmell path/to/project --format csv --out smells.csv
"""

from __future__ import annotations

import argparse
import csv
import json
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

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="javasmell", description="Detect code smells in a Java project."
    )
    parser.add_argument("path", help="Directory or .java file to analyse")
    parser.add_argument(
        "--format",
        choices=("text", "json", "csv", "metrics"),
        default="text",
        help="text: readable report; metrics: the per-class feature matrix",
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

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
        # Reported only after the file closed cleanly -- claiming a write that
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
    else:
        _write_report(stream, project, smells)


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
