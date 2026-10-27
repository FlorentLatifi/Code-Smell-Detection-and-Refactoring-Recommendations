"""Findings as SARIF 2.1.0, the format GitHub code scanning and most CI tools read.

The other formats are for a person or a spreadsheet. This one is for the place a
developer already looks: a finding shows up as an annotation on the pull request
that introduced it, instead of in a report nobody opens (VD-163).

Three choices follow from how code scanning treats results:

* **Severity maps to SARIF level**: critical to ``error``, major to ``warning``,
  minor to ``note``. The MLCQ scale has three steps and SARIF has three levels,
  so nothing is merged or invented.
* **Every result carries the fingerprint from** ``javasmell.findings``. Code
  scanning uses it to recognise the same alert across commits; without it, an
  edit above a finding would close the alert and open a new one.
* **The message is the rationale the detector already produced**, the clauses
  with their measured values, plus the suggested refactorings. A reader sees why,
  not only what.
"""

from __future__ import annotations

import re
from pathlib import Path

from javasmell.detectors.base import Smell
from javasmell.findings import fingerprint
from javasmell.model.entities import posix

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
INFORMATION_URI = (
    "https://github.com/FlorentLatifi/Code-Smell-Detection-and-Refactoring-Recommendations"
)
FINGERPRINT_KEY = "javasmell/v1"

LEVEL = {"critical": "error", "major": "warning", "minor": "note"}


def document(smells: list[Smell], tool_version: str) -> dict[str, object]:
    """One SARIF log with one run: the rules that fired, and every finding."""
    types = sorted({s.smell_type for s in smells})
    index = {smell_type: i for i, smell_type in enumerate(types)}
    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "JavaSmell",
                        "version": tool_version,
                        "informationUri": INFORMATION_URI,
                        "rules": [_rule(smell_type) for smell_type in types],
                    }
                },
                "results": [_result(s, index[s.smell_type]) for s in smells],
            }
        ],
    }


def readable(smell_type: str) -> str:
    """``LongParameterList`` as "Long Parameter List", for a rule's title."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", smell_type)


def _rule(smell_type: str) -> dict[str, object]:
    name = readable(smell_type)
    return {
        "id": smell_type,
        "name": smell_type,
        "shortDescription": {"text": f"Code smell: {name}"},
        "fullDescription": {
            "text": f"{name}, found by a metric-based detection strategy. Each result "
            "lists the measured clauses that triggered it and the refactorings that "
            "address it."
        },
        "helpUri": INFORMATION_URI,
        "properties": {"tags": ["maintainability", "code-smell"]},
    }


def _result(smell: Smell, rule_index: int) -> dict[str, object]:
    where = f"{smell.class_name}.{smell.method}" if smell.method else smell.class_name
    message = f"{readable(smell.smell_type)} in {where}: {smell.rationale}."
    if smell.refactorings:
        message += " Suggested: " + ", ".join(readable(r) for r in smell.refactorings) + "."
    return {
        "ruleId": smell.smell_type,
        "ruleIndex": rule_index,
        "level": LEVEL[smell.severity.value],
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": artifact_uri(smell.file_path)},
                    "region": {"startLine": smell.start_line, "endLine": smell.end_line},
                }
            }
        ],
        "partialFingerprints": {FINGERPRINT_KEY: fingerprint(smell)},
        "properties": {
            "severity": smell.severity.value,
            "score": round(smell.score, 3),
            "refactorings": list(smell.refactorings),
        },
    }


def artifact_uri(file_path: str) -> str:
    """The file as a forward-slash path relative to where the command ran.

    Code scanning resolves URIs against the repository root, and the Action runs
    from there. An absolute path inside the root is made relative; one outside it
    is kept, since there is no root to be relative to.
    """
    path = Path(file_path)
    if path.is_absolute():
        try:
            path = path.relative_to(Path.cwd())
        except ValueError:
            return posix(str(path))
    return posix(str(path))
