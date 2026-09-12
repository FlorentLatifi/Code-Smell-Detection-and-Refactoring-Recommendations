"""Tests for path confinement.

An analysis path is user input, and this is the only thing between it and the
filesystem. The cases below are the ways such a check is normally got wrong:
comparing before resolving, forgetting symlinks, and forgetting that a prefix
match is not containment.
"""

from __future__ import annotations

import pytest

from javasmell.api.paths import PathRejected, confine, java_files_under


@pytest.fixture
def root(tmp_path):
    allowed = tmp_path / "allowed"
    (allowed / "project" / "src").mkdir(parents=True)
    (allowed / "project" / "src" / "A.java").write_text("class A {}", encoding="utf-8")
    (allowed / "project" / "notes.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "keys.txt").write_text("s3cret", encoding="utf-8")
    return allowed


def test_a_path_inside_the_root_is_accepted(root):
    assert confine("project/src/A.java", root).name == "A.java"


def test_the_root_itself_is_accepted(root):
    assert confine(".", root) == root.resolve()


def test_traversal_out_of_the_root_is_refused(root):
    """`allowed/../secret` has the root as a prefix but is not inside it."""
    with pytest.raises(PathRejected, match="outside"):
        confine("../secret/keys.txt", root)


def test_an_absolute_path_outside_the_root_is_refused(root, tmp_path):
    with pytest.raises(PathRejected, match="outside"):
        confine(str(tmp_path / "secret" / "keys.txt"), root)


def test_a_sibling_directory_sharing_the_prefix_is_refused(root, tmp_path):
    """`/tmp/allowed-other` starts with `/tmp/allowed` and is a different place.

    This is why containment is checked against the parent chain rather than with
    a string prefix.
    """
    sneaky = tmp_path / "allowed-other"
    sneaky.mkdir()
    (sneaky / "B.java").write_text("class B {}", encoding="utf-8")

    with pytest.raises(PathRejected, match="outside"):
        confine(str(sneaky / "B.java"), root)


def test_a_symlink_escaping_the_root_is_refused(root, tmp_path):
    """A link inside the root may point anywhere, so resolution comes first."""
    link = root / "escape"
    try:
        link.symlink_to(tmp_path / "secret", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow creating symlinks here")

    with pytest.raises(PathRejected, match="outside"):
        confine("escape/keys.txt", root)


def test_a_missing_path_is_refused(root):
    with pytest.raises(PathRejected, match="does not exist"):
        confine("project/src/Nope.java", root)


def test_an_empty_path_is_refused(root):
    with pytest.raises(PathRejected, match="empty"):
        confine("   ", root)


def test_the_error_never_leaks_the_resolved_location(root, tmp_path):
    """Echoing the absolute path back would confirm what exists outside the root."""
    with pytest.raises(PathRejected) as raised:
        confine("../secret/keys.txt", root)

    assert "secret" not in str(raised.value)
    assert str(tmp_path) not in str(raised.value)


# ----------------------------------------------------------------------
# Collecting the files
# ----------------------------------------------------------------------


def test_only_java_files_are_collected(root):
    found = java_files_under(confine("project", root), max_files=10, max_bytes=10_000)
    assert [p.name for p in found] == ["A.java"]


def test_a_single_java_file_is_allowed(root):
    found = java_files_under(confine("project/src/A.java", root), max_files=10, max_bytes=10_000)
    assert len(found) == 1


def test_a_path_with_no_java_is_refused(root):
    with pytest.raises(PathRejected, match="no Java files"):
        java_files_under(confine("project/notes.txt", root), max_files=10, max_bytes=10_000)


def test_too_many_files_is_refused(root):
    for index in range(6):
        (root / "project" / "src" / f"F{index}.java").write_text("class F {}", encoding="utf-8")

    with pytest.raises(PathRejected, match="more than 3 Java files"):
        java_files_under(confine("project", root), max_files=3, max_bytes=10_000)


def test_too_much_source_is_refused(root):
    (root / "project" / "src" / "Big.java").write_text("x" * 5000, encoding="utf-8")

    with pytest.raises(PathRejected, match="MB of source"):
        java_files_under(confine("project", root), max_files=100, max_bytes=1000)


# Kodet e refuzimit jane kontrate: nderfaqja i perkthen ne shqip nje nga nje, dhe
# nje kod i ri qe hyn pa u perkthyer do te dilte anglisht mes tekstit shqip.
# Testi nuk e ndalon shtimin; e ndalon shtimin e heshtur.
REJECTION_CODES = {
    "path_empty",
    "root_missing",
    "path_outside_root",
    "path_not_found",
    "too_many_files",
    "too_much_source",
    "no_java_files",
}


def test_every_rejection_names_which_rejection_it_is(tmp_path):
    """Shtate arsye te ndryshme arrinin te thirresi nen nje kod te vetem.

    Nje thirres qe duhet te analizoje mesazhin per te ditur cfare ndodhi nuk ka
    kontrate, ka hamendje. Ky test i mbledh kodet qe prodhohen vertet dhe kerkon
    qe secili te jete i njohur dhe i vecante.
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "empty").mkdir()

    seen = set()
    for candidate in ("", "   ", "../jashte", "nuk_ekziston"):
        try:
            confine(candidate, root)
        except PathRejected as rejected:
            seen.add(rejected.code)

    try:
        java_files_under(root / "empty", max_files=10, max_bytes=1000)
    except PathRejected as rejected:
        seen.add(rejected.code)

    assert seen, "asnje refuzim nuk u prodhua; testi nuk po mat gje"
    assert seen <= REJECTION_CODES, f"kod i panjohur: {sorted(seen - REJECTION_CODES)}"
    assert "path_empty" in seen
    assert "path_outside_root" in seen
    assert "path_not_found" in seen
    assert "no_java_files" in seen


def test_a_rejection_without_a_code_still_names_one():
    """Parazgjedhja mbetet, qe nje `raise` i ri te mos dale pa kod fare."""
    assert PathRejected("dicka").code == "path_rejected"
