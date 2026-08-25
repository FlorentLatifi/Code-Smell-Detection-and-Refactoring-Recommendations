"""Tests for the command-line front end.

The CLI is not a convenience wrapper: it is the entry point the experiment
scripts for the Results chapter run against, so a silent change to its output
format would corrupt the data behind the thesis rather than merely annoy a
user. The contract worth pinning down is therefore the *shape* of each output
(exit codes, CSV header, JSON keys), not the prose of the readable report.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from javasmell.cli import main
from javasmell.metrics.calculator import metric_names

FIXTURES = str(Path(__file__).parent / "fixtures")


def test_text_report_summarises_the_analysed_project(capsys):
    assert main([FIXTURES]) == 0

    out = capsys.readouterr().out
    # The two fixture files hold five classes between them.
    assert "Analysed 2 file(s), 5 class(es)" in out
    assert "Summary" in out
    # Every finding explains itself: location, reason, suggested refactorings.
    assert "why:" in out
    assert "fix:" in out


def test_missing_sources_exit_non_zero(tmp_path, capsys):
    empty = tmp_path / "no_java_here"
    empty.mkdir()

    assert main([str(empty)]) == 1
    assert "No Java classes found" in capsys.readouterr().err


def test_json_output_carries_the_documented_keys(capsys):
    assert main([FIXTURES, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload, "the fixtures are built to trigger detections"
    assert payload == sorted(payload, key=lambda s: -s["score"]), "worst first"

    required = {
        "smell_type",
        "scope",
        "package",
        "class_name",
        "method",
        "file_path",
        "start_line",
        "end_line",
        "severity",
        "score",
        "rationale",
        "refactorings",
        "metrics",
    }
    assert required <= set(payload[0])


def test_csv_export_writes_a_file_with_a_stable_header(tmp_path, capsys):
    target = tmp_path / "smells.csv"

    assert main([FIXTURES, "--format", "csv", "--out", str(target)]) == 0
    assert f"Wrote {target}" in capsys.readouterr().err

    rows = list(csv.reader(target.read_text(encoding="utf-8").splitlines()))
    assert rows[0] == [
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
    assert len(rows) > 1


def test_metric_matrix_has_one_column_per_metric(capsys):
    """This matrix is the ML stage's feature vector; its columns are a contract."""
    assert main([FIXTURES, "--format", "metrics"]) == 0

    rows = list(csv.reader(capsys.readouterr().out.splitlines()))
    assert rows[0] == ["package", "class", "file", "start_line", *metric_names()]
    # One row per class in the fixtures.
    assert len(rows) == 6


def test_min_severity_hides_weaker_findings(capsys):
    main([FIXTURES, "--format", "json"])
    everything = json.loads(capsys.readouterr().out)

    main([FIXTURES, "--format", "json", "--min-severity", "critical"])
    critical_only = json.loads(capsys.readouterr().out)

    assert {s["severity"] for s in critical_only} == {"critical"}
    assert len(critical_only) < len(everything)


def test_smell_filter_is_repeatable(capsys):
    main([FIXTURES, "--format", "json", "--smell", "DataClass", "--smell", "FeatureEnvy"])
    selected = json.loads(capsys.readouterr().out)

    assert {s["smell_type"] for s in selected} == {"DataClass", "FeatureEnvy"}
