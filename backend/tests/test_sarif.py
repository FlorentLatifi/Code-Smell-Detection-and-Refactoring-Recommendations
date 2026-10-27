"""Tests for the SARIF output and for hiding findings from the command line (VD-163).

SARIF is a contract with a tool we do not control: code scanning reads the rule
id, the level, the location and the fingerprint, and ignores the rest. Those are
pinned here. The run over the fixtures is compared with the JSON format of the
same run, so the test checks that SARIF carries every finding faithfully, without
fixing the detector's output as a golden file.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from javasmell import __version__
from javasmell.cli import main
from javasmell.findings import fingerprint
from javasmell.sarif import FINGERPRINT_KEY, LEVEL, artifact_uri, readable

FIXTURES = Path(__file__).parent / "fixtures"


def run_json(capsys, *args: str) -> list[dict[str, object]]:
    assert main([*args, "--format", "json"]) == 0
    return json.loads(capsys.readouterr().out)


def run_sarif(capsys, *args: str) -> dict[str, object]:
    assert main([*args, "--format", "sarif"]) == 0
    return json.loads(capsys.readouterr().out)


def test_the_log_declares_sarif_2_1_0_and_the_release_version(capsys):
    log = run_sarif(capsys, str(FIXTURES))

    assert log["version"] == "2.1.0"
    driver = log["runs"][0]["tool"]["driver"]
    assert driver["name"] == "JavaSmell"
    assert driver["version"] == __version__


def test_every_finding_appears_once_with_its_rule_level_and_place(capsys):
    findings = run_json(capsys, str(FIXTURES))
    log = run_sarif(capsys, str(FIXTURES))
    run = log["runs"][0]
    rules = run["tool"]["driver"]["rules"]

    assert len(run["results"]) == len(findings)
    for finding, result in zip(findings, run["results"], strict=True):
        assert result["ruleId"] == finding["smell_type"]
        assert rules[result["ruleIndex"]]["id"] == finding["smell_type"]
        assert result["level"] == LEVEL[finding["severity"]]
        place = result["locations"][0]["physicalLocation"]
        # FIXTURES is absolute; code scanning wants it relative to where the run started.
        relative = Path(str(finding["file_path"])).resolve().relative_to(Path.cwd())
        assert place["artifactLocation"]["uri"] == relative.as_posix()
        assert place["region"] == {
            "startLine": finding["start_line"],
            "endLine": finding["end_line"],
        }
        assert finding["rationale"] in result["message"]["text"]


def test_each_rule_is_listed_once(capsys):
    run = run_sarif(capsys, str(FIXTURES))["runs"][0]
    ids = [rule["id"] for rule in run["tool"]["driver"]["rules"]]

    assert ids == sorted(set(ids))
    assert set(ids) == {result["ruleId"] for result in run["results"]}


def test_the_three_severities_map_to_the_three_sarif_levels():
    assert LEVEL == {"critical": "error", "major": "warning", "minor": "note"}


def test_results_carry_the_fingerprint_the_baseline_uses(capsys):
    """Code scanning and the baseline must agree on what "the same finding" is."""
    from javasmell.analysis import analyze_path
    from javasmell.detectors.rules import detect_all

    expected = [fingerprint(s) for s in detect_all(analyze_path(str(FIXTURES)))]
    run = run_sarif(capsys, str(FIXTURES))["runs"][0]

    assert [r["partialFingerprints"][FINGERPRINT_KEY] for r in run["results"]] == expected


def test_rule_titles_split_the_type_name_into_words():
    assert readable("LongParameterList") == "Long Parameter List"
    assert readable("GodClass") == "God Class"


def test_paths_are_forward_slashes_relative_to_where_the_command_ran(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert artifact_uri(str(tmp_path / "src" / "A.java")) == "src/A.java"
    assert artifact_uri("src\\main\\B.java") == "src/main/B.java"


# --- hiding findings from the command line --------------------------------------


def copy_fixtures(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(FIXTURES, project)
    return project


def mark_above(path: Path, line: int, text: str) -> None:
    """Insert ``text`` as a new line above 1-based ``line``."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    indent = lines[line - 1][: len(lines[line - 1]) - len(lines[line - 1].lstrip())]
    lines.insert(line - 1, f"{indent}{text}\n")
    path.write_text("".join(lines), encoding="utf-8")


def priceorder(findings: list[dict[str, object]]) -> set[object]:
    return {f["smell_type"] for f in findings if f["method"] and "priceOrder" in str(f["method"])}


def test_an_ignore_comment_hides_only_the_smell_it_names(tmp_path, capsys):
    """`priceOrder` in OrderManager.java (line 23) takes six parameters and runs
    long and deep, so it carries four findings. Naming one hides one."""
    project = copy_fixtures(tmp_path)
    assert priceorder(run_json(capsys, str(project))) == {
        "LongParameterList",
        "LongMethod",
        "DeepNesting",
        "FeatureEnvy",
    }

    mark_above(project / "OrderManager.java", 23, "// javasmell:ignore LongParameterList")
    assert main([str(project), "--format", "json"]) == 0
    captured = capsys.readouterr()

    assert priceorder(json.loads(captured.out)) == {"LongMethod", "DeepNesting", "FeatureEnvy"}
    assert "1 finding(s) suppressed in source." in captured.err


def test_the_annotation_hides_every_smell_on_the_method_and_nothing_else(tmp_path, capsys):
    project = copy_fixtures(tmp_path)
    everything = run_json(capsys, str(project))

    mark_above(project / "OrderManager.java", 23, '@SuppressWarnings("javasmell")')
    remaining = run_json(capsys, str(project))

    assert priceorder(remaining) == set()
    assert len(remaining) == len(everything) - 4


def test_a_baseline_hides_what_it_recorded_and_lets_the_gate_pass(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    assert main([str(FIXTURES), "--fail-on", "minor"]) == 3
    capsys.readouterr()

    assert main([str(FIXTURES), "--write-baseline", str(baseline)]) == 0
    assert "Wrote baseline" in capsys.readouterr().err

    assert main([str(FIXTURES), "--baseline", str(baseline), "--fail-on", "minor"]) == 0
    assert "hidden by the baseline" in capsys.readouterr().err


def test_a_new_finding_is_reported_past_the_baseline(tmp_path, capsys):
    """Record a baseline without OrderManager, then add it back: its findings are new."""
    project = copy_fixtures(tmp_path)
    (project / "OrderManager.java").rename(tmp_path / "OrderManager.java")
    baseline = tmp_path / "baseline.json"
    assert main([str(project), "--write-baseline", str(baseline)]) == 0
    capsys.readouterr()

    (tmp_path / "OrderManager.java").rename(project / "OrderManager.java")
    reported = run_json(capsys, str(project), "--baseline", str(baseline))

    assert {Path(str(f["file_path"])).name for f in reported} == {"OrderManager.java"}


def test_an_unreadable_baseline_is_a_usage_error(tmp_path, capsys):
    """Exit 2, like a bad --thresholds file: the command, not the code, is wrong."""
    assert main([str(FIXTURES), "--baseline", str(tmp_path / "absent.json")]) == 2
    assert "Cannot read baseline" in capsys.readouterr().err
