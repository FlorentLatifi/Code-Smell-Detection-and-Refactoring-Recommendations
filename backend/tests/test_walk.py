"""Tests for the single traversal of the corpus that both experiments share.

Its own docstring names the stake: two scripts walk the corpus, one scoring the
rule detectors and one building the feature table, and a difference in which
samples reach an entity would change the denominator of one result and not the
other. The module exists so that cannot happen, and until now nothing checked
that it does its half.

Three properties carry that guarantee and are pinned below. Repositories are
visited alphabetically, so a run cut short by `limit` covers the same projects
every time and two trial runs stay comparable. A skipped repository still
consumes its number, so a resumed run reports progress against the whole job
rather than against what is left of it. And every sample that does not reach an
entity is counted under a reason -- never dropped, because those counts are the
difference between a denominator and a guess.
"""

from __future__ import annotations

from pathlib import Path

from javasmell.evaluation.corpus import Corpus, repo_dirname
from javasmell.evaluation.mlcq import Review, Sample
from javasmell.evaluation.walk import (
    AnalysedRepository,
    group_by_repository,
    iter_repositories,
)

LEDGER = """package org.acme;

public class Ledger {
  private int total;

  public int total() {
    return total;
  }
}
"""


def make_sample(
    sample_id: str = "1",
    repository: str = "git@github.com:apache/hive.git",
    path: str = "/src/main/java/org/acme/Ledger.java",
    code_name: str = "org.acme.Ledger",
    start_line: int = 3,
    end_line: int = 9,
) -> Sample:
    return Sample(
        sample_id=sample_id,
        smell="blob",
        entity_type="class",
        code_name=code_name,
        repository=repository,
        commit_hash="2fa22bf36089aabbccdd",
        path=path,
        start_line=start_line,
        end_line=end_line,
        reviews=(Review(sample_id, "a", "blob", "minor"),),
    )


def place(root: Path, sample: Sample, source: str = LEDGER) -> None:
    """Write the file this sample points at, where the corpus expects it."""
    target = root / repo_dirname(sample) / sample.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")


def test_samples_are_grouped_under_their_own_repository():
    one = make_sample("1", repository="git@github.com:apache/hive.git")
    two = make_sample("2", repository="git@github.com:apache/hive.git")
    other = make_sample("3", repository="git@github.com:apache/storm.git")

    grouped = group_by_repository([one, two, other])

    assert set(grouped) == {
        "git@github.com:apache/hive.git",
        "git@github.com:apache/storm.git",
    }
    assert [s.sample_id for s in grouped["git@github.com:apache/hive.git"]] == ["1", "2"]


def test_repositories_are_visited_alphabetically_so_a_limit_is_repeatable(tmp_path):
    """A trial run must cover the same projects every time it is cut short."""
    samples = [
        make_sample("1", repository="git@github.com:apache/storm.git"),
        make_sample("2", repository="git@github.com:apache/hive.git"),
        make_sample("3", repository="git@github.com:apache/beam.git"),
    ]

    walked = list(iter_repositories(Corpus(tmp_path), samples, limit=2))

    assert [r.name for r in walked] == ["apache/beam", "apache/hive"]


def test_a_skipped_repository_still_counts_towards_the_total(tmp_path):
    """Resuming must not renumber the job, or progress reads against the remainder.

    Three repositories, the first already done: what comes back is numbered 2
    and 3 out of 3, not 1 and 2 out of 2.
    """
    samples = [
        make_sample("1", repository="git@github.com:apache/beam.git"),
        make_sample("2", repository="git@github.com:apache/hive.git"),
        make_sample("3", repository="git@github.com:apache/storm.git"),
    ]

    walked = list(
        iter_repositories(Corpus(tmp_path), samples, skip={"git@github.com:apache/beam.git"})
    )

    assert [(r.number, r.total) for r in walked] == [(2, 3), (3, 3)]
    assert [r.name for r in walked] == ["apache/hive", "apache/storm"]


def test_a_repository_with_no_fetched_source_counts_every_sample_as_missing(tmp_path):
    """Nothing on disk, so nothing is analysed and nothing is silently dropped."""
    samples = [make_sample("1"), make_sample("2")]

    walked = list(iter_repositories(Corpus(tmp_path), samples))

    assert len(walked) == 1
    assert walked[0].matched == ()
    assert walked[0].unreached == {"no_file": 2}


def test_a_sample_whose_file_is_missing_is_counted_beside_one_that_resolves(tmp_path):
    """The denominator is the point: a partial checkout must not look complete."""
    here = make_sample("1")
    absent = make_sample("2", path="/src/main/java/org/acme/Missing.java")
    place(tmp_path, here)

    walked = list(iter_repositories(Corpus(tmp_path), [here, absent]))

    assert [r.sample.sample_id for r in walked[0].matched] == ["1"]
    assert walked[0].unreached == {"no_file": 1}


def test_a_sample_that_reaches_no_entity_is_counted_under_its_reason(tmp_path):
    """A file that was fetched but holds nothing at those lines is not a match."""
    resolves = make_sample("1")
    elsewhere = make_sample("2", code_name="org.acme.Absent", start_line=400, end_line=420)
    place(tmp_path, resolves)

    walked = list(iter_repositories(Corpus(tmp_path), [resolves, elsewhere]))

    assert [r.sample.sample_id for r in walked[0].matched] == ["1"]
    assert sum(walked[0].unreached.values()) == 1
    assert "no_file" not in walked[0].unreached, "the file is present; the entity is not"


def test_every_sample_is_either_matched_or_counted(tmp_path):
    """The invariant the shared walk exists to guarantee, stated as one sum."""
    samples = [
        make_sample("1"),
        make_sample("2", path="/src/main/java/org/acme/Missing.java"),
        make_sample("3", code_name="org.acme.Absent", start_line=400, end_line=420),
    ]
    place(tmp_path, samples[0])

    walked = list(iter_repositories(Corpus(tmp_path), samples))

    accounted = len(walked[0].matched) + sum(walked[0].unreached.values())
    assert accounted == len(samples)


def test_the_repository_name_is_read_off_the_clone_url():
    analysed = AnalysedRepository(
        repository="git@github.com:apache/syncope.git",
        number=1,
        total=1,
        project=None,  # type: ignore[arg-type]
        matched=(),
        unreached={},
    )

    assert analysed.name == "apache/syncope"
