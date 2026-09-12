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
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_unusable_path_is_refused_before_any_analysis(tmp_path, capsys):
    """A mistyped path must not be reportable as a project with nothing in it.

    ``analyze_path`` returns an empty model for a path that does not exist, so
    before this check a typo produced the very sentence a real but Java-free
    directory produces. The empty directory above still exits 1; an unusable
    path exits 2, which is what lets an experiment script tell the two apart.
    """
    missing = tmp_path / "typo"

    assert main([str(missing)]) == 2

    captured = capsys.readouterr()
    assert f"No such file or directory: {missing}" in captured.err
    assert captured.out == "", "nothing was analysed, so there is nothing to report"


def test_non_java_file_is_refused(tmp_path, capsys):
    """The path exists, but ``iter_java_files`` would walk straight past it."""
    notes = tmp_path / "notes.txt"
    notes.write_text("not Java", encoding="utf-8")

    assert main([str(notes)]) == 2

    captured = capsys.readouterr()
    assert f"Not a directory or a .java file: {notes}" in captured.err
    assert captured.out == ""


def test_a_single_java_file_is_accepted(capsys):
    """The other shape the walker handles, so the new check must let it through."""
    one_file = str(Path(FIXTURES) / "Warehouse.java")

    assert main([one_file, "--format", "metrics"]) == 0

    rows = list(csv.reader(capsys.readouterr().out.splitlines()))
    # Warehouse, Item and InvoicePrinter are three of the five fixture classes;
    # three rows plus the header, against six rows for the whole directory.
    assert len(rows) == 4


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


def test_patch_format_emits_a_diff_and_keeps_the_account_off_it(capsys):
    """stdout has to be nothing but the patch, or the pipe into git breaks."""
    assert main([FIXTURES, "--format", "patch"]) == 0

    captured = capsys.readouterr()
    assert captured.out.startswith("--- a/")
    assert "+++ b/" in captured.out
    # How many changes, what was declined: useful, and not part of a diff.
    assert "change(s)" in captured.err
    assert "change(s)" not in captured.out


def test_the_patch_written_to_a_file_keeps_its_line_endings(tmp_path):
    """A translated newline is enough to make git refuse the whole patch.

    The fixtures use LF. On Windows a text stream would write CRLF, every
    context line would then fail to match, and `git apply` would report trailing
    whitespace on each one -- so the bytes are what this asserts, not the text.
    """
    out = tmp_path / "fixes.patch"
    assert main([FIXTURES, "--format", "patch", "--out", str(out)]) == 0

    raw = out.read_bytes()
    assert raw.count(b"\r\n") == 0
    assert raw.count(b"\n") > 0


def test_a_redirected_patch_keeps_its_line_endings(tmp_path):
    """Run for real, because the defect only exists in a stream pytest replaces.

    `capsys` hands the CLI an object that is not a text stream, so the newline
    translation this guards against cannot happen under it -- and a test using
    capsys would pass against the bug. Only an actual process writing to an
    actual redirected file exercises it.
    """
    out = tmp_path / "redirected.patch"
    with out.open("wb") as handle:
        finished = subprocess.run(
            [sys.executable, "-m", "javasmell", FIXTURES, "--format", "patch"],
            cwd=Path(__file__).parent.parent,
            stdout=handle,
            stderr=subprocess.PIPE,
        )

    assert finished.returncode == 0, finished.stderr.decode()
    raw = out.read_bytes()
    assert raw.count(b"\n") > 0
    assert raw.count(b"\r\n") == 0


# ----------------------------------------------------------------------
# Filters, gate and the things a typo should not be answered with
# ----------------------------------------------------------------------
def test_an_unknown_smell_name_is_refused_rather_than_reported_as_nothing():
    """`--smell Blob` used to print "No smells detected" and exit 0.

    That is the worst answer available: it is what a clean project looks like,
    so a typo reads as a result. argparse refuses the value instead and names
    every valid one (VD-92).
    """
    with pytest.raises(SystemExit) as raised:
        main([FIXTURES, "--smell", "Blob"])

    assert raised.value.code == 2


def test_a_known_smell_name_still_filters(capsys):
    """The guard must not have narrowed what the option accepts."""
    assert main([FIXTURES, "--smell", "DataClass"]) == 0

    out = capsys.readouterr().out
    assert "DataClass" in out
    assert "FeatureEnvy" not in out


def test_without_the_gate_finding_smells_is_still_success(capsys):
    """Reporting is what the command is for, so findings alone are not a failure."""
    assert main([FIXTURES]) == 0


def test_the_gate_fails_on_a_finding_at_the_named_severity(capsys):
    """The fixture holds four critical findings, so a critical gate must trip."""
    code = main([FIXTURES, "--fail-on", "critical"])

    assert code == 3
    assert "at or above critical" in capsys.readouterr().err


def test_the_gate_respects_the_filters_above_it(capsys):
    """`--smell DeepNesting` leaves one major finding and no critical one.

    The gate reads what survived the filters, not what was found, or else
    `--smell` and `--min-severity` would silently not apply to it.
    """
    assert main([FIXTURES, "--smell", "DeepNesting", "--fail-on", "critical"]) == 0
    assert main([FIXTURES, "--smell", "DeepNesting", "--fail-on", "major"]) == 3


def test_the_report_warns_about_a_file_that_did_not_parse(tmp_path, capsys):
    """A broken file still yields a tree, so silence would read as cleanliness."""
    (tmp_path / "Broken.java").write_text("public class B {\n  void f( {\n", encoding="utf-8")
    (tmp_path / "Fine.java").write_text("public class F { int a; }\n", encoding="utf-8")

    main([str(tmp_path)])

    out = capsys.readouterr().out
    assert "1 file(s) did not parse cleanly" in out
    assert "Broken.java" in out


def test_a_project_that_parses_cleanly_says_nothing_about_parsing(capsys):
    """The warning has to stay rare enough to mean something."""
    main([FIXTURES])

    assert "did not parse" not in capsys.readouterr().out


def test_reported_paths_use_one_separator(capsys):
    """A single run mixed both on Windows: forward from the argument, back from the walk."""
    main([FIXTURES, "--format", "csv"])

    assert "\\" not in capsys.readouterr().out
