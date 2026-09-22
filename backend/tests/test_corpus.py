"""Tests for the corpus layout and its manifest.

Two of these guard against silent data loss rather than a crash. A sample whose
path escapes the corpus root would read an arbitrary file, and a coverage
figure computed from paths the filesystem quietly refuses would understate the
usable ground truth; both produce numbers that look fine and are wrong.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from javasmell.evaluation.corpus import (
    REPOSITORY_MOVES,
    Corpus,
    Manifest,
    RepoStatus,
    corpus_relative,
    download_name,
    in_corpus,
    repo_dirname,
)
from javasmell.evaluation.mlcq import Review, Sample
from javasmell.filesystem import long_path


def make_sample(
    sample_id: str = "1",
    repository: str = "git@github.com:apache/hive.git",
    commit: str = "2fa22bf36089aabbccdd",
    path: str = "/src/main/java/org/acme/Ledger.java",
) -> Sample:
    return Sample(
        sample_id=sample_id,
        smell="blob",
        entity_type="class",
        code_name="org.acme.Ledger",
        repository=repository,
        commit_hash=commit,
        path=path,
        start_line=10,
        end_line=42,
        reviews=(Review(sample_id, "a", "blob", "minor"),),
    )


def test_directory_name_identifies_owner_repo_and_commit():
    # The commit is truncated to 12 characters; the full hash lives in the manifest.
    assert repo_dirname(make_sample()) == "apache__hive__2fa22bf36089"


def test_source_path_is_resolved_below_the_corpus_root(tmp_path):
    corpus = Corpus(tmp_path)
    resolved = corpus.source_path(make_sample())

    assert resolved.is_relative_to(tmp_path.resolve())
    assert resolved.name == "Ledger.java"


def test_sample_path_cannot_escape_the_corpus_root(tmp_path):
    """MLCQ paths are third-party data, so they are treated as untrusted input."""
    corpus = Corpus(tmp_path)
    escaping = replace(make_sample(), path="/../../../../etc/passwd")

    with pytest.raises(ValueError, match="escapes the corpus root"):
        corpus.source_path(escaping)


def test_has_source_reflects_what_is_on_disk(tmp_path):
    corpus = Corpus(tmp_path)
    sample = make_sample()

    assert corpus.has_source(sample) is False

    target = long_path(corpus.source_path(sample))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("class Ledger {}", encoding="utf-8")

    assert corpus.has_source(sample) is True


def test_has_source_survives_a_path_past_the_windows_limit(tmp_path):
    """A deep Java package is the normal case here, not an edge case."""
    corpus = Corpus(tmp_path)
    deep = "/" + "/".join(f"pkg{i:02d}levelname" for i in range(18)) + "/Deep.java"
    sample = replace(make_sample(), path=deep)

    assert len(str(corpus.source_path(sample))) > 260

    target = long_path(corpus.source_path(sample))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("class Deep {}", encoding="utf-8")

    assert corpus.has_source(sample) is True


def test_coverage_counts_samples_and_repositories(tmp_path):
    corpus = Corpus(tmp_path)
    present = make_sample("1")
    same_repo_missing = make_sample("2", path="/src/main/java/org/acme/Gone.java")
    other_repo = make_sample("3", repository="git@github.com:apache/ode.git")

    target = long_path(corpus.source_path(present))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("class Ledger {}", encoding="utf-8")

    coverage = corpus.coverage([present, same_repo_missing, other_repo])

    # One of three samples, from one of the two repositories referenced.
    assert coverage.samples_available == 1
    assert coverage.samples_total == 3
    assert coverage.repositories_available == 1
    assert coverage.repositories_total == 2
    assert coverage.sample_fraction == pytest.approx(1 / 3)


def test_manifest_round_trips(tmp_path):
    manifest = Manifest()
    manifest.record(
        RepoStatus(
            repository="git@github.com:apache/hive.git",
            commit_hash="2fa22bf36089",
            directory="apache__hive__2fa22bf36089",
            ok=True,
            java_files=6406,
            bytes_written=59_000_000,
        )
    )
    manifest.save(tmp_path)

    reloaded = Manifest.load(tmp_path)
    entry = reloaded.entries["git@github.com:apache/hive.git"]

    assert entry.ok is True
    assert entry.java_files == 6406


def test_failed_repositories_are_retried_not_skipped(tmp_path):
    """A network timeout must not permanently shrink the corpus."""
    manifest = Manifest()
    manifest.record(
        RepoStatus(
            repository="git@github.com:apache/ode.git",
            commit_hash="deadbeef",
            directory="apache__ode__deadbeef",
            ok=False,
            reason="network: URLError",
        )
    )

    assert manifest.is_done("git@github.com:apache/ode.git") is False
    assert manifest.is_done("git@github.com:never/seen.git") is False


def test_missing_manifest_loads_as_empty(tmp_path):
    assert Manifest.load(tmp_path).entries == {}


def test_download_name_passes_through_a_repository_that_never_moved() -> None:
    sample = make_sample(repository="git@github.com:apache/hive.git")
    assert download_name(sample) == ("apache", "hive")


def test_download_name_follows_a_recorded_move() -> None:
    """eclipse/jgit is unreachable; the same commit is served by eclipse-jgit."""
    sample = make_sample(repository="git@github.com:eclipse/jgit.git")
    assert download_name(sample) == ("eclipse-jgit", "jgit")


def test_a_move_may_change_the_repository_name_too() -> None:
    """epam/DLab was donated to Apache and renamed on the way."""
    sample = make_sample(repository="git@github.com:epam/DLab.git")
    assert download_name(sample) == ("apache", "incubator-datalab")


def test_a_move_does_not_change_where_the_checkout_lives() -> None:
    """The layout stays keyed to the identity MLCQ published.

    If a move reached ``repo_dirname``, every already-fetched repository would
    have to be re-downloaded and the matcher would look in the wrong place, so
    this is the property that keeps the map from touching any published figure.
    """
    sample = make_sample(repository="git@github.com:eclipse/jgit.git", commit="abcdef0123456789")
    assert repo_dirname(sample) == "eclipse__jgit__abcdef012345"


def test_every_recorded_move_is_well_formed() -> None:
    """Each entry is ``owner/name`` on both sides and actually changes something."""
    for original, moved in REPOSITORY_MOVES.items():
        assert original.count("/") == 1, original
        assert moved.count("/") == 1, moved
        assert original != moved, original


# ----------------------------------------------------------------------
# Paths in committed results (VD-134)
# ----------------------------------------------------------------------
def test_a_corpus_file_is_recorded_below_the_root_with_forward_slashes(tmp_path):
    corpus = tmp_path / "corpus"
    source = corpus / "apache__hive__2fa22bf36089" / "ql" / "Plan.java"
    source.parent.mkdir(parents=True)
    source.write_text("class Plan {}", encoding="utf-8")

    recorded = corpus_relative(source, corpus)

    # No home directory, no drive letter, and the same separator on every system.
    assert recorded == "apache__hive__2fa22bf36089/ql/Plan.java"
    assert in_corpus(recorded, corpus) == corpus / "apache__hive__2fa22bf36089" / "ql" / "Plan.java"


def test_an_older_absolute_path_still_names_its_file(tmp_path):
    """Results written before VD-134 carry absolute paths, and must still be readable."""
    corpus = tmp_path / "corpus"
    absolute = str(corpus / "repo" / "A.java")

    assert in_corpus(absolute, corpus) == Path(absolute)


def test_a_relative_path_is_taken_as_already_recorded(tmp_path):
    assert corpus_relative("repo/src/A.java", tmp_path) == "repo/src/A.java"


def test_a_file_outside_the_corpus_is_not_rewritten_into_a_wrong_relative_path(tmp_path):
    outside = tmp_path / "elsewhere" / "B.java"
    outside.parent.mkdir()
    outside.write_text("class B {}", encoding="utf-8")

    assert corpus_relative(outside, tmp_path / "corpus") == str(outside)


def test_the_separator_is_why_the_order_depended_on_the_system():
    """Why results record ``/``: the two separators rank differently against a capital.

    Take ``a/x.java`` and ``aB/x.java``, which differ at their second character:
    the separator in one, ``B`` (0x42) in the other. A forward slash (0x2F) ranks
    below ``B``, so ``a/x.java`` sorts first; a backslash (0x5C) ranks above it,
    so on Windows the same two files sort the other way round. A seeded sample
    drawn from the sorted list therefore picked different files on each system.
    """
    backslash = chr(0x5C)
    forward = ["aB/x.java", "a/x.java"]
    windows = [name.replace("/", backslash) for name in forward]

    assert sorted(forward) == ["a/x.java", "aB/x.java"]
    assert sorted(windows) == [f"aB{backslash}x.java", f"a{backslash}x.java"]
