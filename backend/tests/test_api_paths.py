"""Tests for path confinement.

An analysis path is user input, and this is the only thing between it and the
filesystem. The cases below are the ways such a check is normally got wrong:
comparing before resolving, forgetting symlinks, and forgetting that a prefix
match is not containment.
"""

from __future__ import annotations

import pytest

from javasmell.api.paths import (
    PathRejected,
    allowed_roots,
    confine,
    contains_java,
    java_files_under,
    subfolders,
)


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
    "path_not_directory",
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


# ----------------------------------------------------------------------
# Me dy rrënjë: dosja e zgjedhur dhe ajo e depove të importuara (VD-126)
# ----------------------------------------------------------------------


def test_a_path_inside_the_second_root_is_accepted(root, tmp_path):
    """Depot e importuara nuk rrinë brenda dosjes që zgjodhi përdoruesi."""
    projects = tmp_path / "projects"
    (projects / "acme__widgets").mkdir(parents=True)

    found = confine("acme__widgets", [root, projects])

    assert found == (projects / "acme__widgets").resolve()


def test_the_first_root_wins_a_name_that_exists_in_both(root, tmp_path):
    """Dy rrënjë mund të mbajnë të njëjtin emër; radha e vendos, jo rastësia."""
    projects = tmp_path / "projects"
    (projects / "project").mkdir(parents=True)

    assert confine("project", [root, projects]) == (root / "project").resolve()
    assert confine("project", [projects, root]) == (projects / "project").resolve()


def test_a_path_outside_every_root_is_still_refused(root, tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()

    with pytest.raises(PathRejected, match="outside") as raised:
        confine(str(tmp_path / "secret" / "keys.txt"), [root, projects])

    # Emrat e të dyja rrënjëve, sepse tani janë dy vende ku shtegu do të hynte.
    assert "allowed" in str(raised.value)
    assert "projects" in str(raised.value)
    assert "secret" not in str(raised.value)


def test_a_root_that_does_not_exist_is_simply_not_allowed(root, tmp_path):
    """Dosja e depove krijohet vetëm kur importohet e para; deri atëherë mungon."""
    assert allowed_roots([root, tmp_path / "nuk-ekziston"]) == (root.resolve(),)


def test_with_no_usable_root_the_rejection_says_so(tmp_path):
    with pytest.raises(PathRejected, match="root") as raised:
        confine("project", [tmp_path / "a", tmp_path / "b"])

    assert raised.value.code == "root_missing"


# ----------------------------------------------------------------------
# Shfletimi i dosjeve
# ----------------------------------------------------------------------


def test_subfolders_lists_directories_and_marks_the_ones_with_java(root):
    (root / "docs").mkdir()

    found = subfolders(root.resolve())

    # Dy nënndosje: `docs` bosh dhe `project`, që mban `src/A.java`.
    assert [(folder.name, folder.java) for folder in found] == [
        ("docs", False),
        ("project", True),
    ]


def test_subfolders_leaves_out_hidden_directories(root):
    (root / ".git").mkdir()
    (root / ".git" / "objects").mkdir()

    assert [folder.name for folder in subfolders(root.resolve())] == ["project"]


def test_subfolders_refuses_a_file(root):
    with pytest.raises(PathRejected, match="not a directory") as raised:
        subfolders(confine("project/notes.txt", root))

    assert raised.value.code == "path_not_directory"


def test_the_java_probe_gives_up_rather_than_walking_a_whole_tree(root):
    """Kufiri ekziston sepse shfletimi ndodh ndërsa përdoruesi pret.

    Pesë skedarë pa Java dhe një kufi prej tre: kërkimi ndalet dhe kthen
    «nuk e dita», e jo «nuk ka».
    """
    deep = root / "big"
    deep.mkdir()
    for index in range(5):
        (deep / f"f{index}.txt").write_text("x", encoding="utf-8")

    assert contains_java(deep, limit=3) is None
    assert contains_java(deep, limit=50) is False
    assert contains_java(root / "project", limit=50) is True


def test_the_whole_listing_shares_one_probe_budget(root):
    """Tri dosje me nga pesë skedarë pa Java dhe një buxhet prej tetë.

    E para i ha pesë nga tetë dhe del «pa Java»; e dyta merr tre të mbeturit,
    i kalon dhe del «nuk e dita»; e treta nuk shihet fare. Pa buxhet të
    përbashkët, secila do të ecte e plotë dhe lista do të rritej me dosjet.
    """
    for name in ("a", "b", "c"):
        (root / name).mkdir()
        for index in range(5):
            (root / name / f"f{index}.txt").write_text("x", encoding="utf-8")

    found = {folder.name: folder.java for folder in subfolders(root.resolve(), budget=8)}

    assert (found["a"], found["b"], found["c"]) == (False, None, None)


def test_the_folder_list_is_capped(root):
    for index in range(6):
        (root / f"d{index}").mkdir()

    assert len(subfolders(root.resolve(), limit=4)) == 4


def test_the_rejection_names_the_folder_that_is_allowed(tmp_path):
    """A path set by an environment variable is one the caller cannot guess.

    The name only, never the absolute path: echoing the latter tells a caller
    where the root sits and confirms what exists outside it (VD-95).
    """
    root = tmp_path / "workspace"
    root.mkdir()

    with pytest.raises(PathRejected) as raised:
        confine("../elsewhere", root)

    assert "workspace" in str(raised.value)
    assert str(root) not in str(raised.value)
