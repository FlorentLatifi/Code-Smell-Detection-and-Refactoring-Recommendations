"""Tests for importing a public repository from a link.

Two kinds of thing are checked. The first is what a link is allowed to mean: a
host that is not GitHub, a link with credentials, a name with characters GitHub
does not allow, are each refused with their own code rather than being tried.

The second is what an archive is allowed to write. Archive members are
attacker-controlled input in the general case, so the cases below are the ways
such an extraction is normally got wrong: a member that climbs out with ``..``,
a member that is not Java, one larger than the ceiling, and an archive larger
than the ceiling.

No test here touches the network. The download is one injected function, and
everything else -- the path checks, the caps, the counting -- runs for real.
"""

from __future__ import annotations

import io
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from javasmell.projects.github import (
    DEFAULT_REF,
    MAX_ARCHIVE_MB,
    ImportRejected,
    Repository,
    extract_java,
    fetch,
    parse,
)

# ----------------------------------------------------------------------
# Çfarë do të thotë një lidhje
# ----------------------------------------------------------------------

ACCEPTED = [
    ("https://github.com/jhy/jsoup", Repository("jhy", "jsoup", DEFAULT_REF)),
    ("https://github.com/jhy/jsoup.git", Repository("jhy", "jsoup", DEFAULT_REF)),
    ("https://www.github.com/jhy/jsoup/", Repository("jhy", "jsoup", DEFAULT_REF)),
    ("http://github.com/jhy/jsoup", Repository("jhy", "jsoup", DEFAULT_REF)),
    ("git@github.com:apache/hive.git", Repository("apache", "hive", DEFAULT_REF)),
    ("jhy/jsoup", Repository("jhy", "jsoup", DEFAULT_REF)),
    ("https://github.com/jhy/jsoup/tree/master", Repository("jhy", "jsoup", "master")),
    (
        "https://github.com/apache/hive/commit/2fa22bf",
        Repository("apache", "hive", "2fa22bf"),
    ),
]


@pytest.mark.parametrize(("link", "expected"), ACCEPTED)
def test_a_link_someone_would_paste_is_understood(link, expected):
    assert parse(link) == expected


REFUSED = [
    ("", "link_empty"),
    ("   ", "link_empty"),
    ("https://gitlab.com/jhy/jsoup", "not_github"),
    ("https://github.com/jhy", "no_repository"),
    ("ftp://github.com/jhy/jsoup", "bad_scheme"),
    ("https://user:token@github.com/jhy/jsoup", "credentials_in_link"),
    ("https://github.com/-bad/jsoup", "bad_repository"),
    ("https://github.com/jhy/../secret", "bad_repository"),
    ("https://github.com/jhy/jsoup/tree/..%2f..%2fsecret", "bad_ref"),
]


@pytest.mark.parametrize(("link", "code"), REFUSED)
def test_a_link_that_is_not_a_public_repository_is_refused(link, code):
    with pytest.raises(ImportRejected) as raised:
        parse(link)

    assert raised.value.code == code


def test_the_directory_name_carries_the_owner_and_the_branch():
    """Dy depo me të njëjtin emër nga pronarë të ndryshëm nuk guxojnë të përplasen."""
    assert Repository("jhy", "jsoup").directory == "jhy__jsoup"
    assert Repository("jhy", "jsoup", "1.x").directory == "jhy__jsoup__1.x"
    assert Repository("jhy", "jsoup", "feature/x").directory == "jhy__jsoup__feature-x"


# ----------------------------------------------------------------------
# Çfarë lejohet të shkruajë një arkiv
# ----------------------------------------------------------------------


def make_archive(members: dict[str, bytes]) -> bytes:
    """Një tar.gz si i GitHub-ut: gjithçka nën një dosje ``{emri}-{sha}/``."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_only_java_members_are_written(tmp_path):
    archive = tmp_path / "repo.tar.gz"
    archive.write_bytes(
        make_archive(
            {
                "jsoup-abc/src/A.java": b"class A {}",
                "jsoup-abc/README.md": b"# jsoup",
                "jsoup-abc/pom.xml": b"<project/>",
            }
        )
    )

    count, total = extract_java(archive, tmp_path / "out")

    assert count == 1
    assert total == len(b"class A {}")
    assert (tmp_path / "out" / "src" / "A.java").read_text(encoding="utf-8") == "class A {}"
    assert not (tmp_path / "out" / "README.md").exists()


def test_a_member_that_climbs_out_of_the_directory_is_not_written(tmp_path):
    """Ekuivalenti me tar i «zip-slip»: shtegu zgjidhet para se të shkruhet."""
    archive = tmp_path / "repo.tar.gz"
    archive.write_bytes(
        make_archive(
            {
                "jsoup-abc/src/A.java": b"class A {}",
                "jsoup-abc/../../escape.java": b"class Escape {}",
            }
        )
    )

    count, _ = extract_java(archive, tmp_path / "out")

    assert count == 1
    assert not (tmp_path / "escape.java").exists()
    assert not (tmp_path.parent / "escape.java").exists()


def test_a_member_past_the_size_ceiling_is_skipped(tmp_path):
    archive = tmp_path / "repo.tar.gz"
    archive.write_bytes(
        make_archive(
            {
                "jsoup-abc/src/A.java": b"class A {}",
                # Pesë megabajt, mbi tavanin prej katër për një skedar.
                "jsoup-abc/src/Huge.java": b"x" * (5 * 1024 * 1024),
            }
        )
    )

    count, _ = extract_java(archive, tmp_path / "out")

    assert count == 1
    assert not (tmp_path / "out" / "src" / "Huge.java").exists()


def test_the_total_written_has_a_ceiling_of_its_own(tmp_path, monkeypatch):
    """Kufijtë për skedar dhe për numër lejonin bashkë 80 GB nga një arkiv."""
    monkeypatch.setattr("javasmell.projects.github.MAX_EXTRACTED_MB", 1)
    archive = tmp_path / "repo.tar.gz"
    # Tre skedarë nga 600 kB: i dyti e kalon tavanin prej 1 MB.
    archive.write_bytes(
        make_archive({f"jsoup-abc/src/F{index}.java": b"x" * 600_000 for index in range(3)})
    )

    with pytest.raises(ImportRejected) as raised:
        extract_java(archive, tmp_path / "out")

    assert raised.value.code == "archive_too_large"


def test_reading_through_a_huge_archive_is_bounded_too(tmp_path, monkeypatch):
    """Edhe kur asnjë anëtar nuk shkruhet, leximi i zerove ka kufi."""
    monkeypatch.setattr("javasmell.projects.github.MAX_UNPACKED_MB", 1)
    archive = tmp_path / "repo.tar.gz"
    archive.write_bytes(
        make_archive(
            {
                "jsoup-abc/blob.bin": b"\0" * 2_000_000,
                "jsoup-abc/src/A.java": b"class A {}",
            }
        )
    )

    with pytest.raises(ImportRejected) as raised:
        extract_java(archive, tmp_path / "out")

    assert raised.value.code == "archive_too_large"


def test_extraction_starts_from_a_clean_directory(tmp_path):
    """Një provë e mëparshme e ndalur në mes nuk guxon të numërohet si e tëra."""
    destination = tmp_path / "out"
    destination.mkdir()
    (destination / "Stale.java").write_text("class Stale {}", encoding="utf-8")
    archive = tmp_path / "repo.tar.gz"
    archive.write_bytes(make_archive({"jsoup-abc/src/A.java": b"class A {}"}))

    extract_java(archive, destination)

    assert not (destination / "Stale.java").exists()


# ----------------------------------------------------------------------
# Shkarkimi, me hapin e rrjetit të zëvendësuar
# ----------------------------------------------------------------------


def serving(payload: bytes):
    """Një hapës që kthen këtë trup, si `urlopen`."""

    def opener(_: urllib.request.Request) -> io.BytesIO:
        return io.BytesIO(payload)

    return opener


def failing(exception: Exception):
    def opener(_: urllib.request.Request):
        raise exception

    return opener


def test_a_fetched_repository_reports_what_it_wrote(tmp_path):
    payload = make_archive(
        {"jsoup-abc/src/A.java": b"class A {}", "jsoup-abc/src/B.java": b"class B {}"}
    )

    imported = fetch(Repository("jhy", "jsoup"), tmp_path, opener=serving(payload))

    assert imported.java_files == 2
    assert imported.path == tmp_path / "jhy__jsoup"
    assert sorted(path.name for path in Path(imported.path).rglob("*.java")) == [
        "A.java",
        "B.java",
    ]


def test_a_repository_without_java_is_refused_and_leaves_nothing_behind(tmp_path):
    payload = make_archive({"jsoup-abc/README.md": b"# nothing to analyse"})

    with pytest.raises(ImportRejected) as raised:
        fetch(Repository("jhy", "jsoup"), tmp_path, opener=serving(payload))

    assert raised.value.code == "no_java_files"
    assert not (tmp_path / "jhy__jsoup").exists()


def test_a_missing_repository_says_so(tmp_path):
    failure = urllib.error.HTTPError("https://codeload", 404, "Not Found", {}, None)  # type: ignore[arg-type]

    with pytest.raises(ImportRejected) as raised:
        fetch(Repository("jhy", "nope"), tmp_path, opener=failing(failure))

    assert raised.value.code == "repository_not_found"


def test_a_refusal_by_github_is_not_read_as_the_callers_fault(tmp_path):
    failure = urllib.error.HTTPError("https://codeload", 429, "Too Many", {}, None)  # type: ignore[arg-type]

    with pytest.raises(ImportRejected) as raised:
        fetch(Repository("jhy", "jsoup"), tmp_path, opener=failing(failure))

    assert raised.value.code == "rate_limited"


def test_a_download_that_never_ends_is_refused_at_the_ceiling(tmp_path):
    """Tavani matet ndërsa shkarkohet, e jo pasi arkivi është te disku."""
    payload = b"x" * ((MAX_ARCHIVE_MB + 1) * 1024 * 1024)

    with pytest.raises(ImportRejected) as raised:
        fetch(Repository("jhy", "jsoup"), tmp_path, opener=serving(payload))

    assert raised.value.code == "archive_too_large"


def test_a_broken_archive_is_reported_rather_than_half_extracted(tmp_path):
    with pytest.raises(ImportRejected) as raised:
        fetch(Repository("jhy", "jsoup"), tmp_path, opener=serving(b"not a tarball"))

    assert raised.value.code == "archive_broken"
    assert not (tmp_path / "jhy__jsoup").exists()


def test_a_failed_refresh_keeps_the_copy_that_was_there(tmp_path):
    """Më parë shpaketimi e fshinte kopjen e djeshme para se e reja të ishte gati."""
    fetch(
        Repository("jhy", "jsoup"),
        tmp_path,
        opener=serving(make_archive({"jsoup-abc/src/A.java": b"class A {}"})),
    )

    with pytest.raises(ImportRejected):
        fetch(Repository("jhy", "jsoup"), tmp_path, opener=serving(b"not a tarball"))

    kept = tmp_path / "jhy__jsoup" / "src" / "A.java"
    assert kept.read_text(encoding="utf-8") == "class A {}"


def test_a_refresh_replaces_the_old_copy_entirely(tmp_path):
    """Një skedar që u hoq nga depoja nuk guxon të mbetet te kopja e rifreskuar."""
    fetch(
        Repository("jhy", "jsoup"),
        tmp_path,
        opener=serving(
            make_archive({"jsoup-abc/src/A.java": b"class A {}", "jsoup-abc/src/Old.java": b"x"})
        ),
    )

    fetch(
        Repository("jhy", "jsoup"),
        tmp_path,
        opener=serving(make_archive({"jsoup-def/src/A.java": b"class A { int v; }"})),
    )

    files = sorted(path.name for path in (tmp_path / "jhy__jsoup").rglob("*.java"))
    assert files == ["A.java"]


def test_no_working_directory_is_left_behind(tmp_path):
    """Dosjet anash fillojnë me pikë, dhe asnjëra nuk mbetet pas importit."""
    fetch(
        Repository("jhy", "jsoup"),
        tmp_path,
        opener=serving(make_archive({"jsoup-abc/src/A.java": b"class A {}"})),
    )
    with pytest.raises(ImportRejected):
        fetch(Repository("jhy", "jsoup"), tmp_path, opener=serving(b"broken"))

    assert sorted(path.name for path in tmp_path.iterdir()) == ["jhy__jsoup"]


def test_a_lost_connection_is_reported_as_the_network(tmp_path):
    with pytest.raises(ImportRejected) as raised:
        fetch(
            Repository("jhy", "jsoup"),
            tmp_path,
            opener=failing(ConnectionResetError("reset")),
        )

    assert raised.value.code == "network"
