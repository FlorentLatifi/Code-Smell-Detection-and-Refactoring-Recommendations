"""Tests for the description of *what* the God Class strategy misses.

These numbers reach the Results chapter as a claim about the ground truth --
that reviewers labelled small classes blob and no threshold reaches them -- and
a claim of that kind has to be arithmetically unimpeachable, because its
conclusion is convenient. Every expectation below is worked out by hand from
the rows the test builds.

God Class fires on ``WMC >= 47 AND TCC < 1/3 AND ATFD > 5``; Large Class, the
second variant, on ``CLOC > 200 OR NOM > 20``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from javasmell.analysis import analyze_source
from javasmell.detectors.thresholds import DEFAULT
from javasmell.evaluation.dataset import columns, row
from javasmell.evaluation.missed import (
    Groups,
    below_median,
    partition,
    profile,
    quartiles,
    recall_by_severity,
    saturated_cohesion,
    separation,
)
from javasmell.evaluation.mlcq import Aggregation, Review, Sample


def blob_sample(sample_id: str, *severities: str) -> Sample:
    """One MLCQ sample carrying one review per severity given."""
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
        reviews=tuple(
            Review(sample_id=sample_id, reviewer_id=str(index), smell="blob", severity=severity)
            for index, severity in enumerate(severities)
        ),
    )


def blob_record(
    sample: Sample,
    *,
    wmc: float = 1,
    tcc: float = 1.0,
    atfd: float = 0,
    cloc: float = 1,
    nom: float = 1,
    nof: float = 0,
) -> dict[str, str]:
    """One stored row whose class carries exactly these measurements."""
    cls = analyze_source("class Ledger {\n  void work() {}\n}").units[0].classes[0]
    cls.metrics.update({"WMC": wmc, "TCC": tcc, "ATFD": atfd, "CLOC": cloc, "NOM": nom, "NOF": nof})
    return row(sample, cls, None)


def table(path: Path, records: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns()))
        writer.writeheader()
        writer.writerows(records)
    return path


def rows(metric: str, *values: float) -> list[dict[str, str]]:
    """The smallest thing the statistics accept: rows with one column that counts."""
    return [{f"c_{metric}": str(value)} for value in values]


# ----------------------------------------------------------------------
# The statistics
# ----------------------------------------------------------------------
def test_quartiles_pick_by_nearest_rank():
    """Eight values 1..8: index int(0.25*8)=2, int(0.5*8)=4, int(0.75*8)=6.

    Zero-based, so the answers are the third, fifth and seventh values. Nearest
    rank rather than interpolation because an interpolated 4.5 methods is a
    count no class has.
    """
    assert quartiles(rows("NOM", 8, 7, 6, 5, 4, 3, 2, 1), "NOM") == (3.0, 5.0, 7.0)


def test_quartiles_of_a_single_value_are_that_value():
    assert quartiles(rows("NOM", 9), "NOM") == (9.0, 9.0, 9.0)


def test_separation_of_disjoint_groups_is_one():
    """Every miss outranks every negative: 3 x 2 = 6 wins out of 6 pairs."""
    assert separation(rows("NOM", 10, 20, 30), rows("NOM", 1, 2), "NOM") == 1.0


def test_separation_of_identical_groups_is_a_half():
    """Two groups of the same two values: every pair is a tie, and a tie counts 0.5."""
    assert separation(rows("NOM", 4, 9), rows("NOM", 4, 9), "NOM") == 0.5


def test_separation_splits_ties_and_counts_wins():
    """Missed 3 and 5 against negatives 1, 3, 9.

    3 beats 1, ties 3, loses to 9: 1 + 0.5 = 1.5.
    5 beats 1 and 3, loses to 9: 2.
    Total 3.5 over 2 x 3 = 6 pairs, which is 0.58333...
    """
    assert separation(rows("NOM", 3, 5), rows("NOM", 1, 3, 9), "NOM") == 3.5 / 6


def test_separation_without_a_group_is_not_a_number():
    """No pairs means no statistic; zero would read as perfect inversion."""
    assert separation([], rows("NOM", 1), "NOM") != separation([], rows("NOM", 1), "NOM")


def test_below_median_counts_misses_no_larger_than_the_median_negative():
    """Negatives 1, 4, 10 have median 4; misses 2, 4 and 30 put two at or below it.

    At or below, not below: a miss the same size as the median class the
    reviewers cleared is the case the count exists to describe.
    """
    assert below_median(rows("CLOC", 2, 4, 30), rows("CLOC", 1, 4, 10), "CLOC") == 2


# ----------------------------------------------------------------------
# Partitioning
# ----------------------------------------------------------------------
def test_a_reviewed_positive_the_strategy_flags_is_caught(tmp_path):
    """WMC 50 >= 47, TCC 0.1 < 1/3, ATFD 6 > 5, and one major review."""
    sample = blob_sample("1", "major")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=50, tcc=0.1, atfd=6)])

    groups = partition(path, [sample], "blob", "strategy", DEFAULT)

    assert len(groups.caught) == 1
    assert groups.missed == []


def test_a_reviewed_positive_the_strategy_ignores_is_missed(tmp_path):
    """ATFD 5 does not clear "> 5", so the conjunction fails on one clause."""
    sample = blob_sample("1", "major")
    path = table(tmp_path / "d.csv", [blob_record(sample, wmc=50, tcc=0.1, atfd=5)])

    groups = partition(path, [sample], "blob", "strategy", DEFAULT)

    assert len(groups.missed) == 1
    assert groups.caught == []


def test_a_class_the_reviewers_cleared_is_a_negative(tmp_path):
    """Two "none" reviews average to none, and nothing fired: agreement."""
    sample = blob_sample("1", "none", "none")
    path = table(tmp_path / "d.csv", [blob_record(sample)])

    groups = partition(path, [sample], "blob", "strategy", DEFAULT)

    assert len(groups.negative) == 1
    assert groups.spurious == []


def test_a_class_only_the_size_variant_flags_moves_between_the_cells(tmp_path):
    """CLOC 300 > 200 fires Large Class; WMC 1 leaves God Class silent.

    The same row is therefore a miss for the published strategy and a catch for
    the size disjunction, which is the whole reason both variants are reported.
    """
    sample = blob_sample("1", "major")
    path = table(tmp_path / "d.csv", [blob_record(sample, cloc=300)])

    assert len(partition(path, [sample], "blob", "strategy", DEFAULT).missed) == 1
    assert len(partition(path, [sample], "blob", "with_size", DEFAULT).caught) == 1


def test_another_smells_rows_are_not_partitioned(tmp_path):
    """The table holds every smell; a blob profile built from all of it is not one."""
    blob = blob_sample("1", "major")
    envy = Sample(
        sample_id="2",
        smell="feature envy",
        entity_type="class",
        code_name="com.acme.Ledger",
        repository="git@github.com:apache/alpha.git",
        commit_hash="abcdef0123456789",
        path="/src/com/acme/Ledger.java",
        start_line=1,
        end_line=3,
        reviews=(Review(sample_id="2", reviewer_id="0", smell="feature envy", severity="major"),),
    )
    path = table(tmp_path / "d.csv", [blob_record(blob), blob_record(envy)])

    groups = partition(path, [blob, envy], "blob", "strategy", DEFAULT)

    assert len(groups.missed) == 1


# ----------------------------------------------------------------------
# Saturated cohesion
# ----------------------------------------------------------------------
def test_a_large_miss_at_maximum_cohesion_is_reported():
    """WMC 50 clears the complexity clause, and TCC 1.0 no threshold below 1 accepts."""
    sample = blob_sample("1", "major")
    found = saturated_cohesion([blob_record(sample, wmc=50, tcc=1.0, atfd=6)], DEFAULT)

    assert len(found) == 1
    assert found[0].failed == ("TCC",)
    assert found[0].metrics["WMC"] == 50


def test_a_small_miss_at_maximum_cohesion_is_not_reported():
    """WMC 10 fails the complexity clause anyway, so cohesion is not what stopped it."""
    sample = blob_sample("1", "major")

    assert saturated_cohesion([blob_record(sample, wmc=10, tcc=1.0, atfd=6)], DEFAULT) == []


def test_a_miss_with_cohesion_merely_high_is_not_reported():
    """TCC 0.9 is far from the threshold but reachable; 1.0 is the value that is not.

    The distinction matters: a class at 0.9 would be flagged by a looser
    threshold, so it belongs to the calibration question, not to this one.
    """
    sample = blob_sample("1", "major")

    assert saturated_cohesion([blob_record(sample, wmc=50, tcc=0.9, atfd=6)], DEFAULT) == []


def test_saturated_misses_are_ordered_by_complexity():
    """Largest first, because the case rests on these being big classes."""
    small = blob_record(blob_sample("1", "major"), wmc=50, tcc=1.0, atfd=6)
    large = blob_record(blob_sample("2", "major"), wmc=500, tcc=1.0, atfd=6)

    assert [item.sample_id for item in saturated_cohesion([small, large], DEFAULT)] == ["2", "1"]


# ----------------------------------------------------------------------
# The assembled profile
# ----------------------------------------------------------------------
def test_the_profile_counts_every_cell():
    groups = Groups(
        caught=rows("NOM", 1),
        missed=rows("NOM", 2, 3),
        spurious=rows("NOM", 4, 5, 6),
        negative=rows("NOM", 7),
    )

    assert profile(groups, ["NOM"])["support"] == {
        "caught": 1,
        "missed": 2,
        "spurious": 3,
        "negative": 1,
    }


def test_the_profile_reports_separation_per_metric():
    """Misses 10 and 20 both outrank the single negative 1: 2 wins of 2 pairs."""
    groups = Groups(caught=[], missed=rows("NOM", 10, 20), negative=rows("NOM", 1))

    assert profile(groups, ["NOM"])["separation"] == {"NOM": 1.0}


# ----------------------------------------------------------------------
# Severity gradient
# ----------------------------------------------------------------------
def test_recall_by_severity_uses_the_aggregation_it_is_given(tmp_path):
    """One sample reviewed "none" and "critical": MAX calls it critical, MEAN minor.

    Ranks are none 0 and critical 3, so the mean is 1.5 and rounds half up to 2,
    which is major -- except that this sample has two reviews, and the point of
    the test is that the same row lands in a different severity bucket under the
    two aggregations. The row itself is never flagged (WMC 1), so recall is 0 in
    both, and only the bucket differs.
    """
    sample = blob_sample("1", "none", "critical")
    path = table(tmp_path / "d.csv", [blob_record(sample)])

    by_max = recall_by_severity(path, [sample], "blob", "strategy", DEFAULT, Aggregation.MAX)
    by_mean = recall_by_severity(path, [sample], "blob", "strategy", DEFAULT, Aggregation.MEAN)

    assert list(by_max) == ["critical"]
    assert list(by_mean) == ["major"]
    assert by_max["critical"]["support"] == 1


def test_recall_by_severity_separates_caught_from_missed(tmp_path):
    """Two critical samples, one flagged and one not: recall 0.5 in that bucket."""
    caught = blob_sample("1", "critical")
    missed = blob_sample("2", "critical")
    path = table(
        tmp_path / "d.csv",
        [blob_record(caught, wmc=50, tcc=0.1, atfd=6), blob_record(missed)],
    )

    split = recall_by_severity(path, [caught, missed], "blob", "strategy", DEFAULT, Aggregation.MAX)

    assert split["critical"] == {"support": 2, "caught": 1, "recall": 0.5}
