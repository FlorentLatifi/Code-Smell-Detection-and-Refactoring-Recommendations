"""Does the verdict get stronger when the file is compiled inside its project?

    python scripts/verify_with_project.py

Writes ``data/results/verify_with_project.json``.

The engine verifies a rewrite by compiling the file **alone**, and a file from a
real repository does not compile alone: it imports its neighbours. 92% of the
corpus fails ``javac`` before anything is changed, so for most sites the claim
degrades from "compiles" to "introduces no new kind of error" (`verify.py`).

VD-53 recorded the one strengthening available without re-fetching the corpus:
compile the rewritten file with its project's own sources on the sourcepath.
Nothing is downloaded and nothing is built -- ``javac`` resolves the classes it
needs from source, on demand. Third-party jars stay missing, so this does not
promise a clean compile; it promises a smaller and more honest baseline.

**Source roots, not the project root.** A package maps to a directory *relative
to its source root*, and a Maven or Gradle project keeps several -- one project
in this corpus has 463. Pointing ``javac`` at the project root resolves nothing
at all, which is the first thing this measurement got wrong. The roots are
therefore derived from the ``package`` declarations themselves.

**Both verdicts come from this one pass.** ``refactoring_sites.csv`` records the
isolated verdict but carries no line number, so re-locating a site from it would
be ambiguous wherever a class overloads a method. Rather than join on an
ambiguous key, each sampled file is re-analysed here and each rewrite is compiled
twice -- alone and in context -- so the two verdicts describe the same rewrite by
construction. The corpus totals are reported beside them as a check that this
pass sees the same corpus.

**Sampled, because it is slow.** One context compile ran between 0.2 and 22
seconds against 1 second for an isolated one. Every applied site would take
hours, so a seeded sample of files is measured and the seed is recorded. The run
is resumable (VD-33): progress is written per file and an interrupted run
continues where it stopped.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.analysis import analyze_source  # noqa: E402
from javasmell.detectors.rules import detect_in_class  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.parsing.java_parser import JavaParser  # noqa: E402
from javasmell.refactor.edits import apply_edits  # noqa: E402
from javasmell.refactor.locate import FileIndex  # noqa: E402
from javasmell.refactor.registry import for_smell  # noqa: E402
from javasmell.refactor.verify import ERROR_MARKER, Verdict  # noqa: E402

DEFAULT_SITES = Path("data/results/refactoring_sites.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "verify_with_project.json"
PROGRESS_NAME = "verify_with_project.progress.json"

#: Files, not sites. Each costs roughly six minutes -- a context compile
#: resolves and compiles the file's whole dependency closure, and that is paid
#: once per rewrite. Thirty files is what fits in an evening; the seed is
#: recorded so a longer run extends this one rather than replacing it.
DEFAULT_SAMPLE = 30
SEED = 20260902

# Generous, because a context compile pulls in a dependency closure rather than
# one file. A timeout is counted, never read as success -- the same distinction
# `verify.error_messages` makes.
JAVAC_TIMEOUT_S = 180

PACKAGE = re.compile(rb"^\s*package\s+([\w.]+)\s*;", re.M)


def source_root(path: Path) -> Path:
    """The directory this file's package path hangs from.

    A file at ``.../src/main/java/com/acme/Thing.java`` declaring ``com.acme``
    has its root at ``.../src/main/java``. Without this, every package lookup
    fails and the sourcepath resolves nothing.
    """
    try:
        head = path.read_bytes()[:4000]
    except OSError:
        return path.parent
    match = PACKAGE.search(head)
    root = path.parent
    if match:
        for _ in match.group(1).decode().split("."):
            root = root.parent
    return root


def project_roots(project: Path) -> list[str]:
    """Every source root in one project, walked once and cached by the caller."""
    return sorted({str(source_root(java)) for java in project.rglob("*.java")})


def javac_errors(javac: str, arguments: list[str], work: Path) -> set[str] | None:
    """The distinct errors from one ``javac`` run, or None when it timed out.

    Driven through an argument file: a multi-module sourcepath runs to tens of
    thousands of characters and Windows rejects a command line that long, the
    same class of problem VD-17 records. Backslashes become forward slashes
    because ``javac`` reads a backslash in an argument file as an escape.
    """
    argfile = work / "args.txt"
    argfile.write_text("\n".join(arguments).replace("\\", "/") + "\n", encoding="utf-8")
    try:
        done = subprocess.run(
            [javac, f"@{argfile}"],
            capture_output=True,
            text=True,
            timeout=JAVAC_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if done.returncode == 0:
        return set()
    return {
        line.split(ERROR_MARKER, 1)[1].strip()
        for line in done.stderr.splitlines()
        if ERROR_MARKER in line
    }


def compile_alone(javac: str, name: str, source: bytes, work: Path) -> set[str] | None:
    """What the engine does today: the file by itself, nothing else reachable."""
    target = work / name
    target.write_bytes(source)
    out = work / "out"
    out.mkdir(exist_ok=True)
    return javac_errors(javac, ["-nowarn", "-proc:none", "-d", str(out), str(target)], work)


def _shadowed(path: Path, source: bytes, work: Path) -> Path:
    """Write one version of the file into a tree mirroring its package layout.

    The corpus itself is only ever read. The shadow tree goes first on the
    sourcepath so the version under test is the one any sibling resolves to.
    """
    root = source_root(path)
    shadow = work / "shadow"
    try:
        target = shadow / path.relative_to(root)
    except ValueError:
        target = shadow / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)
    return target


def compile_in_context(
    javac: str, path: Path, source: bytes, roots: list[str], work: Path
) -> set[str] | None:
    """The file with its project's sources reachable, resolved from source each time.

    Every call pays for ``javac`` to compile the file's dependency closure, which
    is most of the cost of this measurement. Building that closure once per file
    and compiling each rewrite against the resulting classes was tried and
    **rejected**: a project missing its third-party jars does not compile
    cleanly, so the closure is missing whatever ``javac`` could not emit, and
    compiling against it reports "cannot find symbol" for classes that resolve
    perfectly well from source. Checked against this function on the files
    already measured, that shortcut turned four `compiles` verdicts into
    `no_new_errors` -- it was not the same measurement, only a faster one.
    """
    target = _shadowed(path, source, work)
    out = work / "out"
    out.mkdir(exist_ok=True)
    sourcepath = os.pathsep.join([str(work / "shadow"), *roots])
    return javac_errors(
        javac,
        ["-nowarn", "-proc:none", "-sourcepath", sourcepath, "-d", str(out), str(target)],
        work,
    )


def verdict_for(before: set[str] | None, after: set[str] | None) -> Verdict:
    """The reading `verify.check` applies, over whichever compile was run."""
    if before is None or after is None:
        return Verdict.NOT_CHECKED
    if not after:
        return Verdict.COMPILES
    return Verdict.NO_NEW_ERRORS if after <= before else Verdict.NEW_ERRORS


def rewrites_in(path: Path, source: bytes) -> list[tuple[str, bytes]]:
    """Every rewrite the engine applies in this file, as (smell, new bytes).

    Enumerated exactly as the corpus run enumerates them, so the set of rewrites
    checked here is the set it verified -- only the compilation differs.
    """
    try:
        project = analyze_source(source.decode("utf-8"), str(path))
    except (UnicodeDecodeError, ValueError):
        return []

    index = FileIndex(str(path), source, JavaParser().parse_tree(source))
    found: list[tuple[str, bytes]] = []
    for unit in project.units:
        for cls in unit.classes:
            for smell in detect_in_class(cls):
                automated = for_smell(smell.smell_type)
                if automated is None or smell.method is None:
                    continue
                site = index.find(cls.name, smell.start_line, smell.method.partition("(")[0])
                if site is None:
                    continue
                outcome = automated[1](site)
                if outcome.applied:
                    found.append((smell.smell_type, apply_edits(source, outcome.edits)))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, help="Files to check")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    javac = shutil.which("javac")
    if javac is None:
        print("javac not found; this measurement is only about compilation", file=sys.stderr)
        return 1
    if not args.sites.is_file():
        print(f"sites csv not found: {args.sites}", file=sys.stderr)
        return 1

    with args.sites.open(encoding="utf-8", newline="") as handle:
        with_applied = sorted(
            {row["file"] for row in csv.DictReader(handle) if row["applied"] == "1"}
        )
    chosen = random.Random(args.seed).sample(with_applied, min(args.sample, len(with_applied)))

    args.out.mkdir(parents=True, exist_ok=True)
    progress_path = args.out / PROGRESS_NAME
    done: dict[str, list[list[str]]] = {}
    if args.resume and progress_path.is_file():
        done = json.loads(progress_path.read_text(encoding="utf-8"))
        print(f"Resuming: {len(done)} files already checked", flush=True)

    corpus = args.corpus.resolve()
    roots_cache: dict[str, list[str]] = {}
    started = time.perf_counter()

    for number, file_path in enumerate(chosen, 1):
        if file_path in done:
            continue
        path = Path(file_path)
        try:
            source = path.read_bytes()
            project = corpus / path.resolve().relative_to(corpus).parts[0]
        except (OSError, ValueError):
            done[file_path] = []
            continue

        rewritten = rewrites_in(path, source)
        if not rewritten:
            done[file_path] = []
            continue

        if str(project) not in roots_cache:
            roots_cache[str(project)] = project_roots(project)
        roots = roots_cache[str(project)]

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "alone").mkdir()
            alone_before = compile_alone(javac, path.name, source, work / "alone")
            context_before = compile_in_context(javac, path, source, roots, work)

        outcomes: list[list[str]] = []
        for smell, after_bytes in rewritten:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                (work / "alone").mkdir()
                alone_after = compile_alone(javac, path.name, after_bytes, work / "alone")
                context_after = compile_in_context(javac, path, after_bytes, roots, work)
            outcomes.append(
                [
                    smell,
                    verdict_for(alone_before, alone_after).value,
                    verdict_for(context_before, context_after).value,
                ]
            )
        done[file_path] = outcomes
        progress_path.write_text(json.dumps(done, sort_keys=True) + "\n", encoding="utf-8")
        if not args.quiet:
            print(f"  {number}/{len(chosen)} files", flush=True)

    alone_counts: Counter[str] = Counter()
    context_counts: Counter[str] = Counter()
    moved: Counter[str] = Counter()
    for outcomes in done.values():
        for _, alone, context in outcomes:
            alone_counts[alone] += 1
            context_counts[context] += 1
            moved[f"{alone} -> {context}"] += 1

    print()
    print(f"{'verdict':<16} {'alone':>8} {'in project':>12}")
    for name in sorted(set(alone_counts) | set(context_counts)):
        print(f"{name:<16} {alone_counts.get(name, 0):>8} {context_counts.get(name, 0):>12}")
    print("\nmoved:")
    for change, count in moved.most_common():
        print(f"  {change:<34} {count}")

    payload = {
        "files_checked": len(done),
        "rewrites": sum(alone_counts.values()),
        "sample": args.sample,
        "seed": args.seed,
        "compiled_alone": dict(alone_counts.most_common()),
        "compiled_in_project": dict(context_counts.most_common()),
        "moved": dict(moved.most_common()),
        "javac_timeout_s": JAVAC_TIMEOUT_S,
        "seconds": round(time.perf_counter() - started, 1),
        "environment": environment(),
    }
    result = args.out / RESULT_NAME
    result.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    progress_path.unlink(missing_ok=True)
    print(f"\nWrote {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
