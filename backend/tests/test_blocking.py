"""Tests for the account of *why* the conjunction strategies miss.

The numbers this produces go into the Results chapter as an explanation, which
is a stronger claim than a score: a reader who is told that thirty misses were
blocked by WMC alone will conclude something about calibration. So the
expectations here are worked out from the thresholds by hand.

God Class fires on ``WMC >= 47 AND TCC < 1/3 AND ATFD > 5``. Every record below
is built to fail an exactly named subset of those three.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from javasmell.analysis import analyze_source
from javasmell.detectors.thresholds import DEFAULT
from javasmell.evaluation.blocking import Miss, clauses_for, misses, summarise
from javasmell.evaluation.dataset import columns, row
from javasmell.evaluation.mlcq import Review, Sample

WMC_LIMIT = 47
ATFD_LIMIT = 5
TCC_LIMIT = 1 / 3


def blob_sample(sample_id: str, severity: str = "major") -> Sample:
    return Sample(
        sample_id=sample_id,
        smell="blob",
        entity_type="class",
        code_name="com.acme.Ledger",
        repository="git@github.com:apache/alpha.git",
        commit_hash="abcdef0123456789",
        path="/src/com/acme/Ledger.java",
        start_line=1,
        end_line=3,
        reviews=(Review(sample_id=sample_id, reviewer_id="1", smell="blob", severity=severity),),
    )


def blob_record(sample: Sample, *, wmc: float, tcc: float, atfd: float) -> dict[str, str]:
    """One stored row whose class carries exactly these three measurements."""
    cls = analyze_source("class Ledger {\n  void work() {}\n}").units[0].classes[0]
    cls.metrics.update({"WMC": wmc, "TCC": tcc, "ATFD": atfd})
    return row(sample, cls, None)


def table(path: Path, records: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns()))
        writer.writeheader()
        writer.writerows(records)
    return path


def test_a_class_that_satisfies_every_clause_is_not_a_miss(tmp_path):
    """WMC 50 >= 47, TCC 0.1 < 1/3, ATFD 6 > 5: the strategy fires, so nothing to explain."""
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=50, tcc=0.1, atfd=6)])

    assert misses(path, [sample], DEFAULT) == []


def test_the_single_failing_clause_is_named(tmp_path):
    """WMC 50 and TCC 0.1 hold; ATFD 5 does not, because the clause is strict."""
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=50, tcc=0.1, atfd=5)])

    found = misses(path, [sample], DEFAULT)

    assert len(found) == 1
    assert found[0].failed == ("ATFD",)
    assert found[0].only_blocker == "ATFD"


def test_two_failing_clauses_leave_no_sole_blocker(tmp_path):
    """WMC 20 and ATFD 1 both fail; naming one of them would be a choice, not a fact."""
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=20, tcc=0.1, atfd=1)])

    found = misses(path, [sample], DEFAULT)

    assert found[0].failed == ("WMC", "ATFD")
    assert found[0].only_blocker is None


def test_the_clauses_are_reported_in_strategy_order(tmp_path):
    """WMC, TCC, ATFD: the order Lanza & Marinescu state them, so a reader can follow."""
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=1, tcc=0.9, atfd=1)])

    assert misses(path, [sample], DEFAULT)[0].failed == ("WMC", "TCC", "ATFD")


def test_an_instance_the_reviewers_called_clean_is_not_a_miss(tmp_path):
    """A miss is a *reviewed positive* the strategy did not flag.

    A negative the strategy also did not flag is agreement, and counting it here
    would turn the true negatives into an explanation of poor recall.
    """
    sample = blob_sample("1", severity="none")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=1, tcc=0.9, atfd=1)])

    assert misses(path, [sample], DEFAULT) == []


def test_the_shortfall_of_an_upward_clause_is_measured_over_threshold(tmp_path):
    """WMC 23.5 against 47 is exactly half way: 23.5 / 47 = 0.5."""
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=23.5, tcc=0.1, atfd=6)])

    assert misses(path, [sample], DEFAULT)[0].shortfall["WMC"] == 0.5


def test_the_shortfall_of_a_downward_clause_is_threshold_over_measured(tmp_path):
    """TCC wants below 1/3 and measured 2/3, which is half way: (1/3) / (2/3) = 0.5.

    Both directions have to read the same way, or the medians reported per clause
    would not be comparable with each other.
    """
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=50, tcc=2 / 3, atfd=6)])

    assert misses(path, [sample], DEFAULT)[0].shortfall["TCC"] == 0.5


def test_a_row_for_a_sample_nobody_supplied_is_skipped(tmp_path):
    """The table is wider than any one evaluation's sample set."""
    sample = blob_sample("1")
    path = table(tmp_path / "d.csv", [blob_record(blob_sample("999"), wmc=1, tcc=0.9, atfd=1)])

    assert misses(path, [sample], DEFAULT) == []


def test_a_smell_without_a_conjunction_is_not_explained(tmp_path):
    """Long Method has one clause, so "which clause blocked it" has one answer."""
    sample = blob_sample("1")
    long_method = Sample(
        sample_id="1",
        smell="long method",
        entity_type="function",
        code_name="com.acme.Ledger#work",
        repository="git@github.com:apache/alpha.git",
        commit_hash="abcdef0123456789",
        path="/src/com/acme/Ledger.java",
        start_line=1,
        end_line=3,
        reviews=(Review(sample_id="1", reviewer_id="1", smell="long method", severity="major"),),
    )
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=1, tcc=0.9, atfd=1)])

    assert misses(path, [long_method], DEFAULT) == []


def test_clauses_for_refuses_a_strategy_it_does_not_know():
    """Silence would produce an empty clause list and a miss with no blockers."""
    with pytest.raises(ValueError, match="no clause list"):
        clauses_for("DataClass", {}, DEFAULT)


def miss(sample_id: str, failed: tuple[str, ...], **shortfall: float) -> Miss:
    return Miss(
        sample_id=sample_id,
        smell="blob",
        severity="major",
        failed=failed,
        shortfall=shortfall,
    )


def test_the_summary_counts_how_many_clauses_blocked_each_miss():
    """One miss blocked by one clause, two blocked by two: 1 -> 1 and 2 -> 2."""
    found = [
        miss("1", ("WMC",), WMC=0.5),
        miss("2", ("WMC", "TCC"), WMC=0.5, TCC=0.5),
        miss("3", ("WMC", "ATFD"), WMC=0.5, ATFD=0.5),
    ]

    summary = summarise(found)["blob"]

    assert summary["missed"] == 3
    assert summary["blocked_by_one_clause"] == 1
    assert summary["clauses_failing"] == {"1": 1, "2": 2}


def test_the_median_shortfall_covers_only_the_single_blocker_misses():
    """Three sole-WMC misses at 0.2, 0.4, 0.9 have median 0.4.

    The miss blocked by two clauses is excluded: it has no single distance, and
    folding one of its two numbers in would invent one.
    """
    found = [
        miss("1", ("WMC",), WMC=0.2),
        miss("2", ("WMC",), WMC=0.4),
        miss("3", ("WMC",), WMC=0.9),
        miss("4", ("WMC", "TCC"), WMC=0.01, TCC=0.01),
    ]

    summary = summarise(found)["blob"]

    assert summary["sole_blocker"] == {"WMC": 3}
    assert summary["median_shortfall"]["WMC"] == 0.4


def test_an_even_number_of_shortfalls_takes_the_midpoint():
    """0.2 and 0.6 give 0.4, not either endpoint."""
    found = [miss("1", ("TCC",), TCC=0.2), miss("2", ("TCC",), TCC=0.6)]

    assert summarise(found)["blob"]["median_shortfall"]["TCC"] == 0.4
