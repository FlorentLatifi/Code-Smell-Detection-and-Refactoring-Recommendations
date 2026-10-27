"""Which findings a team has already decided about, so a report shows only new ones.

A detector with the precision this one has (MCC 0.49 to 0.72 for Approach B,
lower for the rules) produces findings a reader disagrees with. Without a way to
say "seen, and accepted", the same finding returns on every run, and a build gate
built on ``--fail-on`` either fails forever or gets switched off. Both outcomes
end with the tool unused (VD-163). Two mechanisms, for two situations:

* **In the source**, for one declaration the author has looked at. Either the
  annotation Java already uses for exactly this, ``@SuppressWarnings("javasmell")``
  or ``@SuppressWarnings("javasmell:LongMethod")``, or a comment
  ``// javasmell:ignore`` (optionally followed by smell types) in the comment
  block directly above the declaration.
* **A baseline file**, for adopting the tool on a codebase that already has
  hundreds of findings: record them once, and from then on report only what is
  new.

Both are applied after detection, never inside it. A suppressed finding was still
detected and still counts in every evaluation; it is only hidden from one report.

Matching is textual, like the parser's facts: no symbol resolution, and a
suppression applies to the declaration that carries it, not to what it encloses.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from javasmell.detectors.base import Smell
from javasmell.model.entities import posix

#: Bumped if the identity below ever changes, so an old baseline is refused
#: instead of silently matching nothing.
BASELINE_VERSION = 1

#: How far a declaration header may run before its opening brace. A signature
#: with many parameters wraps over a few lines; past this, the brace belongs to
#: something else.
HEADER_MAX_LINES = 20

_ANNOTATION = re.compile(r"@SuppressWarnings\s*\((?P<body>[^)]*)\)", re.DOTALL)
_STRING = re.compile(r'"([^"]*)"')
_IGNORE = re.compile(r"javasmell:ignore\b(?P<types>[\w ,]*)")


class BaselineError(ValueError):
    """The baseline file exists but cannot be read as one."""


def fingerprint(smell: Smell) -> str:
    """A finding's identity across commits: what it is and where, but not on which line.

    Line numbers are left out on purpose. A finding that moves because code above
    it changed is the same finding, and a baseline keyed on lines would report it
    as new after every edit. The method is its full signature, so overloads stay
    apart; the file is left out, so moving a class does not resurrect its findings.
    """
    identity = "|".join((smell.smell_type, smell.package, smell.class_name, smell.method or ""))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


def suppressed_in_source(smell: Smell, lines: Sequence[str]) -> bool:
    """Whether the declaration ``smell`` points at carries a suppression for it.

    ``lines`` is the file's text split into lines; ``smell.start_line`` is 1-based
    and is where the declaration begins, annotations included.
    """
    start = smell.start_line - 1
    if not 0 <= start < len(lines):
        return False
    return _in_annotation(smell.smell_type, _header(lines, start)) or _in_comment(
        smell.smell_type, _comment_block_above(lines, start)
    )


def _header(lines: Sequence[str], start: int) -> str:
    """The declaration from its first line up to and including its opening brace."""
    end = min(len(lines), start + HEADER_MAX_LINES)
    header: list[str] = []
    for line in lines[start:end]:
        header.append(line)
        if "{" in line:
            break
    return "\n".join(header)


def _comment_block_above(lines: Sequence[str], start: int) -> list[str]:
    """The comment lines directly above the declaration, nearest first.

    Stops at the first line that is neither a comment nor blank, so a comment
    above an earlier member is never mistaken for one on this declaration.
    """
    block: list[str] = []
    for line in reversed(lines[:start]):
        text = line.strip()
        if not text:
            continue
        if not text.startswith(("//", "/*", "*")):
            break
        block.append(text)
    return block


def _names(types: str) -> set[str]:
    return {name for name in re.split(r"[\s,]+", types) if name}


def _in_annotation(smell_type: str, header: str) -> bool:
    for match in _ANNOTATION.finditer(header):
        for value in _STRING.findall(match.group("body")):
            if value == "javasmell" or value == f"javasmell:{smell_type}":
                return True
    return False


def _in_comment(smell_type: str, block: Iterable[str]) -> bool:
    for text in block:
        match = _IGNORE.search(text)
        if match is None:
            continue
        named = _names(match.group("types"))
        if not named or smell_type in named:
            return True
    return False


def load_baseline(path: Path) -> set[str]:
    """The fingerprints a baseline file records."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BaselineError(f"Cannot read baseline {posix(str(path))}: {error}") from error
    if not isinstance(data, dict) or data.get("version") != BASELINE_VERSION:
        raise BaselineError(
            f"{posix(str(path))} is not a version {BASELINE_VERSION} JavaSmell baseline"
        )
    findings = data.get("findings")
    if not isinstance(findings, list) or not all(isinstance(f, str) for f in findings):
        raise BaselineError(f"{posix(str(path))} has no list of findings")
    return set(findings)


def baseline_document(smells: Iterable[Smell]) -> dict[str, object]:
    """What ``--write-baseline`` writes: sorted, so the file diffs cleanly in review."""
    return {
        "version": BASELINE_VERSION,
        "findings": sorted({fingerprint(s) for s in smells}),
    }
