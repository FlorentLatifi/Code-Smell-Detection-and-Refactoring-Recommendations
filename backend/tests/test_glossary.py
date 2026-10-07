"""The plain-language glossary covers every term the system can show (VD-144).

The point of the glossary is that a reader in plain mode never meets a bare
`WOC` or `ExtractSubclass`. That promise breaks silently the day a detector,
metric or refactoring is added without an entry, so completeness is checked
against what the system itself produces rather than against a list kept here.
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import pytest

from javasmell import glossary
from javasmell.analysis import analyze_path
from javasmell.cli import main
from javasmell.detectors.base import Severity
from javasmell.detectors.rules import REFACTORINGS, detect_all
from javasmell.detectors.thresholds import Thresholds
from javasmell.evaluation.dataset import CLASS_METRICS, METHOD_METRICS
from javasmell.metrics.calculator import metric_names

FIXTURES = str(Path(__file__).parent / "fixtures")
RULES = Path(__file__).resolve().parents[1] / "javasmell" / "detectors" / "rules.py"


def _filled(entry: dict[str, str] | None, *keys: str) -> bool:
    return entry is not None and all(entry.get(key, "").strip() for key in keys)


@pytest.mark.parametrize("smell_type", sorted(REFACTORINGS))
def test_every_detected_smell_is_explained(smell_type):
    assert _filled(glossary.smell(smell_type), "name", "what", "why", "fix")  # type: ignore[arg-type]


@pytest.mark.parametrize("name", sorted({r for names in REFACTORINGS.values() for r in names}))
def test_every_proposed_refactoring_is_explained(name):
    assert _filled(glossary.refactoring(name), "name", "what")  # type: ignore[arg-type]


def _condition_metrics() -> set[str]:
    """Every metric a detector clause names, read off the detector source."""
    return set(re.findall(r'Condition\(\s*"([^"]+)"', RULES.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "name",
    sorted(set(metric_names()) | set(CLASS_METRICS) | set(METHOD_METRICS) | _condition_metrics()),
)
def test_every_metric_the_system_reports_is_explained(name):
    assert _filled(glossary.metric(name), "name", "what")  # type: ignore[arg-type]


#: Pragje që nuk kufizojnë një metrikë, por shkallën e ashpërsisë.
SEVERITY_SCALE = {"excess_cap", "severity_major", "severity_critical"}


@pytest.mark.parametrize(
    "name", sorted(f.name for f in fields(Thresholds) if f.name not in SEVERITY_SCALE)
)
def test_every_detection_threshold_names_its_metric(name):
    assert glossary.threshold_metric(name) is not None


def test_the_scan_of_detector_clauses_found_them():
    """Guard the regex: an empty scan would make the test above pass vacuously."""
    assert {"WMC", "TCC", "ATFD", "NOPA+NOAM", "MLOC", "MAXNESTING"} <= _condition_metrics()


def test_every_operator_and_severity_has_words():
    operators = {c.operator for s in detect_all(analyze_path(FIXTURES)) for c in s.conditions}
    assert operators <= set(glossary.vocabulary()["operators"])
    assert {">", ">=", "<", "<="} <= set(glossary.vocabulary()["operators"])
    for level in Severity:
        assert _filled(glossary.severity(level.value), "name", "what")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "name", ["blob", "data class", "feature envy", "long method", "data_class", "Blob"]
)
def test_mlcq_and_model_names_reach_the_same_entries(name):
    assert glossary.smell(name) is not None


def test_aliases_point_at_real_entries():
    words = glossary.vocabulary()
    assert set(words["smell_aliases"].values()) <= set(words["smells"])


def test_model_feature_prefixes_are_stripped():
    assert glossary.metric("c_WMC") == glossary.metric("WMC")
    assert glossary.metric("m_ATFD") == glossary.metric("ATFD")


def test_a_clause_reads_as_a_sentence():
    assert glossary.condition_sentence("MLOC", ">", 35, 77) == (
        "Rreshtat e kodit të metodës: 77 (problem kur është mbi 35)"
    )
    # Three decimals at most, as the interface shows them.
    assert glossary.condition_sentence("TCC", "<", 0.333333, 0.0183661) == (
        "Sa lidhen metodat mes tyre: 0.018 (problem kur është nën 0.333)"
    )


def test_an_unknown_term_shows_rather_than_disappears():
    assert glossary.condition_sentence("XYZ", "!=", 1, 2) == "XYZ: 2 (problem kur është != 1)"
    assert glossary.smell("NoSuchSmell") is None


def test_the_plain_report_explains_each_finding(capsys):
    assert main([FIXTURES, "--thjeshte"]) == 0
    out = capsys.readouterr().out
    assert "U analizuan 2 skedarë, 5 klasa" in out
    assert "Çfarë është një «erë kodi»" in out
    assert "Klasë vetëm me të dhëna (DataClass)" in out
    assert "Pse u shënua:" in out
    assert "(problem kur është" in out
    # The technical clause syntax stays out of the plain report.
    assert " and " not in out
    assert "WOC =" not in out


def test_the_plain_report_says_what_the_engine_can_fix(capsys):
    assert main([FIXTURES, "--thjeshte"]) == 0
    out = capsys.readouterr().out
    assert "Mjeti mund ta ndreqë vetë" in out
    assert "Këtë duhet ta ndreqësh me dorë" in out


def test_plain_only_applies_to_the_text_report(capsys):
    assert main([FIXTURES, "--thjeshte", "--format", "json"]) == 2
    assert "--thjeshte" in capsys.readouterr().err
