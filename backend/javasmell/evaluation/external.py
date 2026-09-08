"""Reading an external detector's verdict, so it can be scored like our own.

The comparison in Chapter 5 sets this project's detectors beside PMD on the same
samples, through the same ``scoring.score``. For that to mean anything, PMD's
report has to be reduced to the same unit of answer: did this tool fire on *this
entity*. That is what this module does, and it is here rather than in the script
because it is the part with a wrong answer to give.

**Entities, not lines.** PMD's XML report carries the simple class name and the
bare method name on every violation, which is exactly how MLCQ identifies the
entity its reviewers looked at. Matching on names is therefore exact, where
matching on line numbers would have to guess whether a tool counts an annotation
or a Javadoc block as part of the declaration.

**A broken report is not an empty one.** PMD's XML renderer emits an unbalanced
closing tag when a source file fails to process, and one corpus repository (the
JDK) triggers it. A strict parser rejects the whole 25 MB file, and the first
version of this code caught that exception and returned "no violations" -- which
silently turned the corpus's largest repository into a tool that found nothing.
The recovery path below exists for that, and it reports that it was needed.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import unescape

from javasmell.evaluation.matcher import relative_key

NAMESPACE = "{http://pmd.sourceforge.net/report/2.0.0}"

#: Read only when the strict parser refuses the report. PMD writes one opening
#: tag per line, so a line scan sees exactly what the parser would have seen.
VIOLATION = re.compile(r"<violation\s([^>]*)>")
ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')
FILE_TAG = re.compile(r'<file\s+name="([^"]*)"')
ERROR_TAG = re.compile(r"<error\s+filename=")


@dataclass(frozen=True)
class Violations:
    """What one PMD run said, and how much of it is trustworthy."""

    #: ``file<tab>class<tab>method`` -> the rules that fired exactly there.
    at: dict[str, set[str]]
    #: Files PMD could not process. Counted, never read as "nothing found".
    errors: int
    #: True when the strict parser refused the report and the scan was used.
    recovered: bool


def entity_of(code_name: str) -> tuple[str, str | None]:
    """The (class, method) an MLCQ ``code_name`` names, in PMD's own spelling.

    MLCQ writes ``pkg.Outer.Inner#method Type1 Type2`` for a method and
    ``pkg.Outer.Inner`` for a class. PMD's report carries the simple class name
    and the bare method name, so both sides are reduced to that.
    """
    qualified, _, signature = code_name.partition("#")
    simple = qualified.rpartition(".")[2].strip()
    if not signature:
        return simple, None
    return simple, signature.split(" ")[0].strip()


def entity_key(file: str, cls: str, method: str | None, root: str = "") -> str:
    """One spelling of "this entity", used by both sides of the lookup."""
    return f"{relative_key(file, root)}\t{cls}\t{method or ''}"


def parse_report(report: Path, root: Path) -> Violations:
    """Every violation as entity -> rules, plus the files PMD could not read.

    A file PMD failed on is counted rather than left to look like a file with no
    violations: those are opposite claims and only one of them is evidence.
    """
    if not report.exists():
        return Violations(at={}, errors=0, recovered=False)

    try:
        tree = ElementTree.parse(report)
    except ElementTree.ParseError:
        return scan_report(report, root)

    at: dict[str, set[str]] = defaultdict(set)
    errors = 0
    for element in tree.getroot():
        if element.tag == f"{NAMESPACE}error":
            errors += 1
            continue
        if element.tag != f"{NAMESPACE}file":
            continue
        name = element.get("name", "")
        for child in element:
            if child.tag == f"{NAMESPACE}error":
                errors += 1
                continue
            key = entity_key(name, child.get("class", ""), child.get("method"), str(root))
            at[key].add(child.get("rule", ""))
    return Violations(at=dict(at), errors=errors, recovered=False)


def scan_report(report: Path, root: Path) -> Violations:
    """The same report read tag by tag, for when the renderer emitted broken XML.

    A recovery path, and it says so through ``recovered`` so a run that needed it
    can be reported rather than quietly accepted. It is never the primary reader:
    a hand-rolled scan of XML is worse than a parser everywhere except here,
    where the alternative is discarding a repository.
    """
    at: dict[str, set[str]] = defaultdict(set)
    errors = 0
    name = ""
    with report.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            found = FILE_TAG.search(line)
            if found:
                name = unescape(found.group(1))
            if ERROR_TAG.search(line):
                errors += 1
            match = VIOLATION.search(line)
            if not match:
                continue
            attributes = dict(ATTRIBUTE.findall(match.group(1)))
            key = entity_key(name, attributes.get("class", ""), attributes.get("method"), str(root))
            at[key].add(attributes.get("rule", ""))
    return Violations(at=dict(at), errors=errors, recovered=True)


def rules_at(violations: Violations, key: str) -> set[str]:
    """Which rules fired on exactly this entity."""
    return violations.at.get(key, set())
