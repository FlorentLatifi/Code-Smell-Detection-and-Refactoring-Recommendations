"""Checking that a rewrite did not break the file, at three levels of strength.

The engine's claim is only worth what it can be checked against, and checking is
harder here than it looks. A file from a real repository does not compile on its
own: it imports its neighbours, and 92% of the corpus fails ``javac`` before
anything is changed. Insisting on a clean compile would therefore leave 8% of the
corpus verifiable and say nothing about the rest.

So three checks, weakest to strongest, and each is reported separately rather
than collapsed into one figure:

1. **It still parses.** tree-sitter reports an ERROR or MISSING node for text
   that is not Java. This catches a malformed rewrite -- a lost brace, a mangled
   multi-byte character -- and it applies to every file.
2. **It introduces no new kind of compiler error.** ``javac`` runs before and
   after and the *distinct* messages are compared. Counting them instead was
   tried first and proved too strict: extracting a block whose parameter is an
   imported type adds one more ``cannot find symbol`` for that type, purely
   because the file is being compiled without its classpath. The rewrite is
   correct and the extra error is an artefact of the isolation.

   The weakness of comparing kinds is the mirror image: an introduced error that
   happens to read like one already present would pass unnoticed. That is why it
   does not replace the third check, and why both are reported.
3. **It compiles.** For the minority of files that compile alone, the strongest
   statement available: ``javac`` accepted it before and accepts it after.

The thesis reports all three. Reporting only the third would understate the
evidence; reporting only the first would overstate it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from javasmell.parsing.java_parser import JavaParser

JAVAC_TIMEOUT_S = 60

# javac prints a trailing summary line; a complaint about the source carries this
# marker, and a failure of javac's own does not (see `errors_in`).
ERROR_MARKER = ": error:"


class Verdict(StrEnum):
    """How strongly a rewrite was checked, and whether it passed."""

    COMPILES = "compiles"
    NO_NEW_ERRORS = "no_new_errors"
    PARSES = "parses"
    BROKEN_SYNTAX = "broken_syntax"
    NEW_ERRORS = "new_errors"
    NOT_CHECKED = "not_checked"

    @property
    def passed(self) -> bool:
        return self in {Verdict.COMPILES, Verdict.NO_NEW_ERRORS, Verdict.PARSES}


@dataclass(frozen=True)
class Check:
    verdict: Verdict
    errors_before: int = 0
    errors_after: int = 0
    detail: str = ""


def parses_cleanly(source: bytes) -> bool:
    """Does tree-sitter read this as Java with no error or missing node?"""
    tree = JavaParser().parse_tree(source)
    root = tree.root_node
    if not root.has_error:
        return True
    # has_error is set on the root for any error anywhere, which is what we want;
    # the explicit walk is only for the case where the flag is unavailable.
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            return False
        stack.extend(node.children)
    return True


def errors_in(returncode: int, stderr: str) -> set[str] | None:
    """The distinct errors in one ``javac`` run, or None when it did not name any.

    ``javac`` marks a complaint about the source as ``file: error: message``. A
    failure of its own carries no such marker: a class file it could not write,
    a source file it could not find, a VM that would not start. Those lines read
    ``error: ...`` at the start, and the marker deliberately does not match them,
    because such a failure is not a property of the code under test.

    Returning an empty set for them, which this did until VD-136, awards the
    most favourable verdict available to a run that failed. It happened: five
    large files of the 23 September corpus run exited non-zero with no marked
    line, and 19 rewrites were recorded as fully compiling when the files they
    live in do not compile at all. An unexplained failure is therefore None --
    javac was asked and cannot be believed -- which the caller reports as the
    weakest verdict rather than the strongest.
    """
    marked = {
        line.split(ERROR_MARKER, 1)[1].strip()
        for line in stderr.splitlines()
        if ERROR_MARKER in line
    }
    if marked:
        return marked
    return set() if returncode == 0 else None


def javac_command() -> str | None:
    """The compiler binary, preferring the JDK's own over a launcher that wraps it.

    On Windows the ``javac`` on PATH is usually a shim under
    ``Common Files/Oracle/Java/javapath`` that starts the real compiler as a
    child of its own. A timeout then kills the shim and leaves the compiler
    running, so the limit bounds the wrong process: a stated 180 seconds took
    50 minutes on one JDK file, because the caller waited for a compile it had
    already given up on (VD-137). Calling the JDK's binary directly means the
    process that is killed is the process doing the work.
    """
    home = os.environ.get("JAVA_HOME")
    if home:
        candidate = Path(home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
        if candidate.is_file():
            return str(candidate)
    return shutil.which("javac")


def run_javac(javac: str, arguments: list[str], work: Path, timeout: int) -> tuple[int, str] | None:
    """One bounded ``javac`` run: its exit code and output, or None if it ran out of time.

    Output goes to a file rather than a pipe. With pipes, a descendant that
    outlives the timeout keeps the write end open, and ``subprocess.run`` waits
    for that handle to close even after killing the child it started -- which is
    how a bounded call became an unbounded one (VD-137). A file has no such
    reader, so the call returns as soon as the timeout fires.
    """
    log = work / "javac.log"
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        try:
            completed = subprocess.run(
                [javac, *arguments],
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
    return completed.returncode, log.read_text(encoding="utf-8", errors="replace")


def error_messages(javac: str, source: bytes, name: str) -> set[str] | None:
    """The distinct errors ``javac`` reports for this file on its own, or None.

    None means javac could not be believed: it timed out, or it failed without
    naming a single error in the source. Either is different from finding no
    errors and must not be read as success.

    The file is written to a throwaway directory under its original name,
    because a public class must live in a file that matches it and renaming
    would invent an error the code does not have. Line numbers are dropped: the
    rewrite moves code, so every message after the edit point would otherwise
    look new.
    """
    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / name
        path.write_bytes(source)
        outcome = run_javac(
            javac,
            ["-nowarn", "-proc:none", "-d", work, str(path)],
            Path(work),
            JAVAC_TIMEOUT_S,
        )
    if outcome is None:
        return None
    return errors_in(*outcome)


def check(
    javac: str | None,
    before: bytes,
    after: bytes,
    name: str,
    before_errors: set[str] | None = None,
) -> Check:
    """Verify one rewrite as strongly as this file allows.

    ``before_errors`` may be supplied when the caller has already compiled the
    original. A file usually holds several sites, and its baseline does not
    change between them; recompiling it per site doubles the cost of a corpus
    run for no new information.
    """
    if not parses_cleanly(after):
        return Check(Verdict.BROKEN_SYNTAX, detail="the rewritten file is not valid Java")

    if javac is None:
        return Check(Verdict.PARSES, detail="javac not available")

    if before_errors is None:
        before_errors = error_messages(javac, before, name)
    after_errors = error_messages(javac, after, name)
    if before_errors is None or after_errors is None:
        return Check(Verdict.PARSES, detail="javac could not be asked")

    counts = (len(before_errors), len(after_errors))
    introduced = after_errors - before_errors

    if not before_errors:
        verdict = Verdict.COMPILES if not after_errors else Verdict.NEW_ERRORS
        return Check(verdict, *counts, detail="; ".join(sorted(introduced))[:200])

    # The file did not compile alone to begin with, so the most that can be said
    # is whether the rewrite introduced a kind of error that was not there.
    verdict = Verdict.NEW_ERRORS if introduced else Verdict.NO_NEW_ERRORS
    return Check(verdict, *counts, detail="; ".join(sorted(introduced))[:200])
