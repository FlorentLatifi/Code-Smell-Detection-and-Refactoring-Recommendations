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
path itself is unusable, 4 when ``--apply`` was asked for and refused. Giving the
first two the same code is what let a mistyped path in an experiment read as a
project with nothing in it.

3 is different from all of them: it means the command worked and the project did
not. Only ``--fail-on`` produces it, and only then, so a build gate can tell "the
tool broke" from "the code is over the line" without parsing any output. Finding
smells is otherwise a success, because reporting is what this command is for
(VD-92).

``--apply`` is the one option that changes the author's files, and it is the only
one that can produce 4. A refusal there is an ordinary outcome -- the tree was
not clean, the path is not a repository -- but a script that asked for a write
and did not get one must not read as success (VD-100).
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
from javasmell.detectors.rules import REFACTORINGS, detect_all
from javasmell.detectors.thresholds import DEFAULT
from javasmell.metrics.calculator import metric_names
from javasmell.model.entities import ProjectModel, posix
from javasmell.refactor.apply import Refusal, apply_patches
from javasmell.refactor.patch import Plan, iter_plan, unified

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}

#: Gjeresia e rreshtit te progresit. Rreshti rishkruhet mbi vetveten, ndaj duhet
#: mbushur deri ketu qe nje rresht i meparshem me i gjate te mos lere bisht.
PROGRESS_WIDTH = 44

#: Kthimi i karroces, i emeruar qe te mos rrije nje shenje e padukshme te teksti.
CR = chr(13)


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
    parser.add_argument(
        "--smell",
        action="append",
        choices=sorted(REFACTORINGS),
        metavar="TYPE",
        help="Only report this smell type (repeatable). One of: " + ", ".join(sorted(REFACTORINGS)),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the verified rewrites to the files. Requires a clean git working "
        "tree, so that one 'git restore .' undoes everything this wrote",
    )
    parser.add_argument(
        "--fail-on",
        choices=("minor", "major", "critical"),
        help="Exit 3 when a finding at or above this severity survives the filters, "
        "so the command can gate a build",
    )
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

    # Planifikuar nje here dhe ndare: `--apply` shkruan pikerisht ate qe diff-i
    # pershkruan, e jo nje plan te dyte qe mund te ndryshoje.
    planned = _planned(Path(project.root), smells, shutil.which("javac")) if args.apply else None

    if args.out:
        with Path(args.out).open("w", encoding="utf-8", newline="") as stream:
            _emit(args.format, project, smells, stream, planned)
        # Reported only after the file closed cleanly; claiming a write that
        # raised half way through would be worse than saying nothing.
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        _emit(args.format, project, smells, sys.stdout, planned)

    if planned is not None and not _apply(planned, Path(project.root)):
        return 4

    if args.fail_on is not None:
        limit = SEVERITY_ORDER[args.fail_on]
        offending = [s for s in smells if SEVERITY_ORDER[s.severity.value] <= limit]
        if offending:
            print(
                f"{len(offending)} finding(s) at or above {args.fail_on}.",
                file=sys.stderr,
            )
            return 3
    return 0


def _emit(
    fmt: str,
    project: ProjectModel,
    smells: list[Smell],
    stream: TextIO,
    planned: Plan | None = None,
) -> None:
    if fmt == "json":
        json.dump([s.to_dict() for s in smells], stream, indent=2)
    elif fmt == "csv":
        _write_smell_csv(stream, smells)
    elif fmt == "metrics":
        _write_metric_csv(stream, project)
    elif fmt == "patch":
        _write_patch(stream, project, smells, planned)
    else:
        _write_report(stream, project, smells)


def _apply(planned: Plan, root: Path) -> bool:
    """Write the verified rewrites, or say why nothing was written.

    Returns whether the write happened, so the caller can exit non-zero: a
    script that asked for a write and got a refusal must not read as success
    (VD-100).
    """
    outcome = apply_patches(planned.patches, root, requested=True)
    if isinstance(outcome, Refusal):
        print(f"Nothing was written: {outcome.detail or outcome.reason}", file=sys.stderr)
        return False

    for relative in outcome.written:
        print(f"wrote {relative}", file=sys.stderr)
    print(
        f"{len(outcome.written)} file(s) written. To undo all of it: {outcome.revert}",
        file=sys.stderr,
    )
    return True


def _planned(root: Path, smells: list[Smell], javac: str | None) -> Plan:
    """Plan the patch, saying where it has got to while it works.

    The same operation the interface shows a bar for, and the same reason: a
    patch over 322 files was measured at two and a half minutes, and a terminal
    that prints nothing for that long is one a reader assumes has hung.

    The line is rewritten over itself and goes to stderr, where everything that
    is not diff already goes: redirecting stdout into ``git apply`` is the usage
    this format documents, and a progress line in the middle of a patch would
    corrupt it. When stderr is not a terminal nothing is printed at all, or the
    rewrites would pile up in a log file (VD-98).
    """
    live = sys.stderr.isatty()
    result: Plan | None = None
    for step in iter_plan(root, smells, javac):
        if isinstance(step, Plan):
            result = step
        elif live:
            line = f"{step.files_done}/{step.files_total} files, {step.changes} change(s)"
            print(CR + line.ljust(PROGRESS_WIDTH), end="", file=sys.stderr, flush=True)
    if live:
        # Fshihet me hapesira e jo me nje sekuence ANSI: kthimin e karroces dhe
        # hapesirat i kupton cdo terminal, ndersa nje sekuence e paperkrahur do
        # te dilte si tekst i papunuar pikerisht atje ku nuk kuptohet.
        print(CR + " " * PROGRESS_WIDTH + CR, end="", file=sys.stderr, flush=True)
    assert result is not None
    return result


def _write_patch(
    stream: TextIO,
    project: ProjectModel,
    smells: list[Smell],
    planned: Plan | None = None,
) -> None:
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
    # Kur `--apply` e ka llogaritur tashme planin, ai perdoret: planifikimi mat
    # me minuta mbi nje projekt real, dhe dy here do te thoshte dy here aq.
    result = planned if planned is not None else _planned(Path(project.root), smells, javac)
    stream.write(unified(result.patches))

    print(
        f"{result.changes} change(s) in {len(result.patches)} file(s)"
        + ("" if javac else "; javac not found, so verification stopped at syntax"),
        file=sys.stderr,
    )
    if result.declines:
        print(
            f"{result.declined} site(s) had no safe rewrite and were declined:",
            file=sys.stderr,
        )
        # Grouped by reason rather than listed one per line: a real project
        # declines hundreds of sites, and a reader wants the shape of the
        # refusals first. The per-site detail is in the JSON the API returns.
        for reason, count in sorted(
            Counter(d.reason for d in result.declines).items(),
            key=lambda pair: (-pair[1], pair[0]),
        ):
            example = next(d for d in result.declines if d.reason == reason)
            suffix = f" e.g. {example.file_path}:{example.start_line}"
            print(f"  {count:>5}  {reason}{suffix}", file=sys.stderr)
    if result.deferred:
        print(
            f"{result.deferred} deferred: their edits overlap a change already in the patch. "
            "Apply this patch and run again to be offered them.",
            file=sys.stderr,
        )
    for drop in result.dropped:
        print(f"dropped {drop.relative}: {drop.verdict.value} -- {drop.detail}", file=sys.stderr)


#: How many unparseable files the report names before it stops listing them.
#: Enough to recognise a pattern -- one package, one generator -- and few enough
#: that the warning does not bury the findings.
MAX_UNPARSED_NAMED = 5


def _write_unparsed(stream: TextIO, project: ProjectModel) -> None:
    """Say which files did not parse, because silence here reads as cleanliness.

    Tree-sitter recovers from an error and returns a tree regardless, so such a
    file still contributes a plausible but incomplete class list. A project
    where half the files fail then shows fewer smells and looks like better
    code, which is the one failure mode a detector must never have (VD-91).
    """
    unparsed = project.unparsed
    if not unparsed:
        return
    named = ", ".join(posix(u.file_path) for u in unparsed[:MAX_UNPARSED_NAMED])
    rest = len(unparsed) - MAX_UNPARSED_NAMED
    more = "" if rest <= 0 else f", and {rest} more"
    print(
        f"WARNING: {len(unparsed)} file(s) did not parse cleanly, so what was found "
        f"in them is incomplete: {named}{more}",
        file=stream,
    )


def _write_report(stream: TextIO, project: ProjectModel, smells: list[Smell]) -> None:
    files = len(project.units)
    classes = len(project.classes)
    methods = sum(len(c.methods) for c in project.classes)
    print(f"Analysed {files} file(s), {classes} class(es), {methods} method(s)", file=stream)
    _write_unparsed(stream, project)
    print(file=stream)

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
                posix(s.file_path),
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
                posix(cls.file_path),
                cls.start_line,
                *[round(cls.metrics.get(name, 0.0), 4) for name in columns],
            ]
        )


if __name__ == "__main__":
    raise SystemExit(main())
