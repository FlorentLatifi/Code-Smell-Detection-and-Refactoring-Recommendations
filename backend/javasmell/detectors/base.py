"""The finding produced by every detector, and the conditions that justify it.

A detector never returns a bare boolean. It returns the conditions it evaluated
together with the measured values, so that three things become possible:

* the user interface can explain *why* something was flagged;
* the Results chapter can report which condition carried a detection;
* severity can be derived from how far past the threshold the code actually is,
  rather than being assigned arbitrarily.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """Ordinal severity.

    The scale deliberately matches the MLCQ data set (Madeyski & Lewowski,
    2020), whose reviewers labelled instances as none/minor/major/critical.
    Sharing the scale means the rule-based output can be compared against the
    manual labels without a mapping step.
    """

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Condition:
    """One clause of a detection strategy, with the value that satisfied it."""

    metric: str
    operator: str  # ">", ">=", "<", "<="
    threshold: float
    value: float

    @property
    def excess(self) -> float:
        """How far past the threshold the measurement is, as a ratio >= 1.

        Normalising both directions to a ratio lets conditions of opposite
        polarity (WMC too high, TCC too low) be averaged into one score.
        """
        if self.operator in (">", ">="):
            if self.threshold <= 0:
                return 1.0 + self.value
            return self.value / self.threshold
        if self.value <= 0:
            return float("inf") if self.threshold > 0 else 1.0
        return self.threshold / self.value

    def describe(self) -> str:
        return f"{self.metric} = {self.value:g} ({self.operator} {self.threshold:g})"


@dataclass
class Smell:
    smell_type: str
    scope: str  # "class" or "method"
    class_name: str
    package: str
    file_path: str
    start_line: int
    end_line: int
    conditions: list[Condition]
    refactorings: list[str]
    method: Optional[str] = None
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Mean excess across the conditions, capped so one extreme metric
        cannot by itself push a mild case to critical."""
        if not self.conditions:
            return 1.0
        capped = [min(c.excess, 5.0) for c in self.conditions]
        return sum(capped) / len(capped)

    @property
    def severity(self) -> Severity:
        score = self.score
        if score < 1.5:
            return Severity.MINOR
        if score < 2.5:
            return Severity.MAJOR
        return Severity.CRITICAL

    @property
    def location(self) -> str:
        target = f"{self.class_name}.{self.method}" if self.method else self.class_name
        return f"{target} ({self.file_path}:{self.start_line})"

    @property
    def rationale(self) -> str:
        return " and ".join(c.describe() for c in self.conditions)

    def to_dict(self) -> dict:
        """Serialisation used by the HTTP API and the CSV export."""
        return {
            "smell_type": self.smell_type,
            "scope": self.scope,
            "package": self.package,
            "class_name": self.class_name,
            "method": self.method,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "severity": self.severity.value,
            "score": round(self.score, 3),
            "rationale": self.rationale,
            "refactorings": list(self.refactorings),
            "metrics": {k: round(v, 3) for k, v in self.metrics.items()},
        }
