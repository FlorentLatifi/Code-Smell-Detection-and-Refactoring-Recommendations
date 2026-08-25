"""Tests for the MLCQ ground-truth reader.

Every expectation below is derived by hand from the miniature data set in
``_write_csv``; the arithmetic is shown in the comment beside each assertion.
This matters more here than elsewhere: these labels *are* the ground truth the
thesis measures against, so a reader that silently mis-aggregates them would
produce plausible, publishable and wrong numbers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from javasmell.evaluation.mlcq import (
    Aggregation,
    load_samples,
    repositories_by_sample_count,
)

HEADER = (
    "id;reviewer_id;sample_id;smell;severity;review_timestamp;type;code_name;"
    "repository;commit_hash;path;start_line;end_line;link;"
    "is_from_industry_relevant_project"
)

# sample -> (smell, type, code_name, repo, [(reviewer, severity), ...])
FIXTURE = {
    # Two reviewers disagreeing across the none/smell boundary.
    "1": ("blob", "class", "com.acme.Ledger", "apache/alpha", [("a", "none"), ("b", "minor")]),
    # Two reviewers disagreeing at the top of the scale.
    "2": (
        "data class",
        "class",
        "com.acme.Dto",
        "apache/alpha",
        [("a", "major"), ("b", "critical")],
    ),
    # Three reviewers, one outlier.
    "3": (
        "long method",
        "function",
        "com.acme.Job#run",
        "apache/beta",
        [("a", "none"), ("b", "none"), ("c", "critical")],
    ),
    # Unanimous.
    "4": (
        "feature envy",
        "function",
        "com.acme.Printer#describe",
        "apache/beta",
        [("a", "minor"), ("b", "minor")],
    ),
    # Unanimously clean.
    "5": ("blob", "class", "com.acme.Tidy", "apache/beta", [("a", "none"), ("b", "none")]),
}


def _write_csv(tmp_path: Path) -> Path:
    lines = [HEADER]
    row_id = 0
    for sample_id, (smell, kind, name, repo, reviews) in FIXTURE.items():
        for reviewer, severity in reviews:
            row_id += 1
            lines.append(
                f"{row_id};{reviewer};{sample_id};{smell};{severity};"
                f"2019-03-27 10:34:53.041496;{kind};{name};"
                f"git@github.com:{repo}.git;deadbeef;/src/main/java/Acme.java;10;42;"
                f"https://github.com/{repo}/blob/deadbeef/src/main/java/Acme.java;1"
            )
    path = tmp_path / "MLCQCodeSmellSamples.csv"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _by_id(tmp_path: Path):
    return {s.sample_id: s for s in load_samples(_write_csv(tmp_path))}


def test_reviews_are_grouped_into_samples(tmp_path):
    samples = _by_id(tmp_path)

    # 11 review rows collapse into the 5 entities that were reviewed.
    assert len(samples) == 5
    assert len(samples["3"].reviews) == 3
    assert len(samples["4"].reviews) == 2


def test_sample_carries_the_location_fields(tmp_path):
    sample = _by_id(tmp_path)["1"]

    assert sample.start_line == 10
    assert sample.end_line == 42
    # The published path has a leading slash; joining it to a checkout root
    # unmodified would produce an absolute path and silently escape the corpus.
    assert sample.path.startswith("/")
    assert sample.relative_path == "src/main/java/Acme.java"


def test_repository_url_is_split_into_owner_and_name(tmp_path):
    assert _by_id(tmp_path)["1"].owner_and_name == ("apache", "alpha")


def test_smell_names_map_onto_detector_names(tmp_path):
    samples = _by_id(tmp_path)

    assert samples["1"].detector_name == "GodClass"
    assert samples["2"].detector_name == "DataClass"
    assert samples["3"].detector_name == "LongMethod"
    assert samples["4"].detector_name == "FeatureEnvy"


def test_mean_aggregation_rounds_a_tie_towards_the_smell(tmp_path):
    samples = _by_id(tmp_path)

    # none(0) + minor(1) -> 1/2 = 0.5 -> half up -> 1 = minor.
    # Banker's rounding would give 0 here and lose the finding entirely.
    assert samples["1"].severity_label() == "minor"
    # major(2) + critical(3) -> 5/2 = 2.5 -> half up -> 3 = critical.
    assert samples["2"].severity_label() == "critical"
    # none(0) + none(0) + critical(3) -> 3/3 = 1.0 -> 1 = minor.
    assert samples["3"].severity_label() == "minor"
    # minor + minor -> 2/2 = 1.0 -> 1 = minor.
    assert samples["4"].severity_label() == "minor"
    # none + none -> 0 = none.
    assert samples["5"].severity_label() == "none"


def test_max_and_min_bracket_the_mean(tmp_path):
    sample = _by_id(tmp_path)["3"]  # ranks 0, 0, 3

    assert sample.severity_label(Aggregation.MAX) == "critical"
    assert sample.severity_label(Aggregation.MIN) == "none"
    assert sample.severity_label(Aggregation.MEAN) == "minor"


def test_unanimous_strategy_discards_disagreements(tmp_path):
    samples = _by_id(tmp_path)

    # Samples 1, 2 and 3 were not unanimous: the strategy refuses to label them.
    assert samples["1"].severity_rank(Aggregation.UNANIMOUS) is None
    assert samples["2"].severity_rank(Aggregation.UNANIMOUS) is None
    assert samples["3"].severity_rank(Aggregation.UNANIMOUS) is None
    # 4 and 5 were unanimous and keep their label.
    assert samples["4"].severity_label(Aggregation.UNANIMOUS) == "minor"
    assert samples["5"].severity_label(Aggregation.UNANIMOUS) == "none"


def test_is_smelly_is_the_binary_view_of_the_label(tmp_path):
    samples = _by_id(tmp_path)

    assert samples["1"].is_smelly() is True  # minor
    assert samples["5"].is_smelly() is False  # none
    assert samples["3"].is_smelly(Aggregation.MIN) is False  # min rank 0
    assert samples["1"].is_smelly(Aggregation.UNANIMOUS) is None  # refused


def test_unanimity_is_reported_per_sample(tmp_path):
    samples = _by_id(tmp_path)

    assert samples["1"].is_unanimous is False
    assert samples["4"].is_unanimous is True


def test_repositories_are_ranked_by_sample_count(tmp_path):
    samples = load_samples(_write_csv(tmp_path))

    # beta contributes samples 3, 4, 5; alpha contributes 1 and 2.
    assert repositories_by_sample_count(samples) == [
        ("git@github.com:apache/beta.git", 3),
        ("git@github.com:apache/alpha.git", 2),
    ]


# ----------------------------------------------------------------------
# Against the real file, when it has been downloaded.
# ----------------------------------------------------------------------
REAL = Path(__file__).parents[2] / "data" / "raw" / "MLCQCodeSmellSamples.csv"


@pytest.mark.skipif(not REAL.exists(), reason="MLCQ not downloaded; see scripts/README.md")
def test_published_data_set_has_its_documented_shape():
    """Guards against a re-published MLCQ version changing under us.

    The counts come from Zenodo record 3666840 v1.1 and are quoted in the
    thesis, so a change here must be noticed rather than absorbed.
    """
    samples = load_samples(REAL)

    assert len(samples) == 4770
    assert sum(len(s.reviews) for s in samples) == 14739
    assert len({s.repository for s in samples}) == 522
    assert {s.smell for s in samples} == {"blob", "data class", "long method", "feature envy"}
    # One commit per repository: the corpus fetch needs exactly 522 trees.
    assert len({(s.repository, s.commit_hash) for s in samples}) == 522
