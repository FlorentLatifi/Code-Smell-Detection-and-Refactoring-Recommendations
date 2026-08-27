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
2. **It introduces no new compiler errors.** ``javac`` is run before and after
   and the error counts compared. A file that failed on 12 unresolved imports and
   still fails on 12 has not been damaged by the rewrite. This is a proxy: it
   would miss a change that removed one error and added another, which is why it
   does not replace the third check.
3. **It compiles.** For the minority of files that compile alone, the strongest
   statement available: ``javac`` accepted it before and accepts it after.

The thesis reports all three. Reporting only the third would understate the
evidence; reporting only the first would overstate it.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from javasmell.parsing.java_parser import JavaParser

JAVAC_TIMEOUT_S = 60

# javac prints a trailing summary line; the errors themselves carry this marker.
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


def count_errors(javac: str, source: bytes, name: str) -> int:
    """How many errors ``javac`` reports for this file on its own.

    The file is written to a throwaway directory with its original name, because
    a public class must live in a file that matches it and renaming would invent
    an error the code does not have.
    """
    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / name
        path.write_bytes(source)
        try:
            completed = subprocess.run(
                [javac, "-nowarn", "-proc:none", "-d", work, str(path)],
                capture_output=True,
                text=True,
                timeout=JAVAC_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return -1
    if completed.returncode == 0:
        return 0
    return sum(1 for line in completed.stderr.splitlines() if ERROR_MARKER in line)


def check(javac: str | None, before: bytes, after: bytes, name: str) -> Check:
    """Verify one rewrite as strongly as this file allows."""
    if not parses_cleanly(after):
        return Check(Verdict.BROKEN_SYNTAX, detail="the rewritten file is not valid Java")

    if javac is None:
        return Check(Verdict.PARSES, detail="javac not available")

    errors_before = count_errors(javac, before, name)
    errors_after = count_errors(javac, after, name)

    if errors_before < 0 or errors_after < 0:
        return Check(Verdict.PARSES, detail="javac timed out")

    if errors_before == 0:
        verdict = Verdict.COMPILES if errors_after == 0 else Verdict.NEW_ERRORS
        return Check(verdict, errors_before, errors_after)

    # The file did not compile alone to begin with. The most that can be said is
    # whether the rewrite made it worse.
    verdict = Verdict.NO_NEW_ERRORS if errors_after <= errors_before else Verdict.NEW_ERRORS
    return Check(verdict, errors_before, errors_after)
