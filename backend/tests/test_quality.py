"""Tests for the by-hand review of rewrite quality.

The numbers this module produces go straight into the Results chapter and are
not recoverable from anywhere else: the sheet is filled once, by hand, and a
sampling or scoring bug would not announce itself. So the expectations here are
worked out from the inputs by hand rather than read off a run.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from javasmell.evaluation.quality import (
    SHEET_COLUMNS,
    Acceptance,
    Behaviour,
    Benefit,
    Judgement,
    Site,
    applied_sites,
    diff_text,
    label_sample,
    population,
    read_judgements,
    stratified_sample,
    summarise,
    wilson,
)
from javasmell.evaluation.sites import sites_in

FIXTURES = Path(__file__).parent / "fixtures"

SITE_COLUMNS = ["file", "class_name", "method", "smell", "refactoring", "applied", "verdict"]


def write_sites(path: Path, rows: list[dict[str, object]]) -> Path:
    """A stand-in for ``refactoring_sites.csv`` with only the columns read here."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SITE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in SITE_COLUMNS})
    return path


def site_row(file: str, method: str, applied: int, refactoring: str = "ExtractMethod") -> dict:
    return {
        "file": file,
        "class_name": "C",
        "method": method,
        "smell": "LongMethod",
        "refactoring": refactoring,
        "applied": applied,
        "verdict": "no_new_errors" if applied else "not_checked",
    }


def judgement(
    review_id: str,
    refactoring: str,
    acceptance: Acceptance,
    ordinal: int = 0,
    benefit: Benefit = Benefit.IMPROVES,
) -> Judgement:
    return Judgement(
        review_id=review_id,
        refactoring=refactoring,
        behaviour=Behaviour.PRESERVED,
        benefit=benefit,
        acceptance=acceptance,
        ordinal=ordinal,
    )


def test_the_ordinal_counts_refused_rows_as_well(tmp_path):
    """Position in the file's rows, not position among the applied ones.

    Four rows for one file, applied on the second and the fourth. The evaluation
    wrote all four, so the sites it applied sit at positions 1 and 3; numbering
    only the applied ones would call them 0 and 1 and reopen the wrong methods.
    """
    path = write_sites(
        tmp_path / "sites.csv",
        [
            site_row("A.java", "one", 0),
            site_row("A.java", "two", 1),
            site_row("A.java", "three", 0),
            site_row("A.java", "four", 1),
        ],
    )

    sites = applied_sites(path)

    assert [(site.method, site.ordinal) for site in sites] == [("two", 1), ("four", 3)]


def test_each_file_is_numbered_from_zero(tmp_path):
    """Ordinals are per file, because the walk restarts at every file."""
    path = write_sites(
        tmp_path / "sites.csv",
        [
            site_row("A.java", "one", 0),
            site_row("A.java", "two", 1),
            site_row("B.java", "three", 1),
        ],
    )

    sites = applied_sites(path)

    assert [(Path(s.file).name, s.ordinal) for s in sites] == [("A.java", 1), ("B.java", 0)]


def test_the_population_counts_applied_sites_only(tmp_path):
    """The reweighting divides by rewrites that happened, not by sites detected."""
    path = write_sites(
        tmp_path / "sites.csv",
        [
            site_row("A.java", "one", 1),
            site_row("A.java", "two", 0),
            site_row("A.java", "three", 1, "IntroduceParameterObject"),
        ],
    )

    assert population(applied_sites(path)) == {"ExtractMethod": 1, "IntroduceParameterObject": 1}


def many_sites(refactoring: str, count: int) -> list[Site]:
    return [
        Site(
            file=f"{refactoring}-{n}.java",
            ordinal=0,
            class_name="C",
            method=f"m{n}",
            smell="LongMethod",
            refactoring=refactoring,
        )
        for n in range(count)
    ]


def test_the_same_seed_draws_the_same_sites():
    """A sample that moved between runs would make the sheet unfillable."""
    sites = many_sites("ExtractMethod", 50)

    assert stratified_sample(sites, 5, seed=1) == stratified_sample(sites, 5, seed=1)


def test_a_different_seed_draws_a_different_sample():
    """Guards the seed actually reaching the draw; without it both are the first five."""
    sites = many_sites("ExtractMethod", 50)

    assert stratified_sample(sites, 5, seed=1) != stratified_sample(sites, 5, seed=2)


def test_the_input_order_does_not_change_the_sample():
    """The CSV is in walk order, and adding a corpus file must not reshuffle the draw."""
    sites = many_sites("ExtractMethod", 50)

    assert stratified_sample(sites, 5, seed=1) == stratified_sample(sites[::-1], 5, seed=1)


def test_every_transformation_is_sampled_to_the_same_depth():
    """Stratified, not proportional: 40 of one kind and 6 of another give 5 and 5."""
    sites = many_sites("ExtractMethod", 40) + many_sites("IntroduceParameterObject", 6)

    drawn = stratified_sample(sites, 5, seed=1)

    assert [s.refactoring for s in drawn].count("ExtractMethod") == 5
    assert [s.refactoring for s in drawn].count("IntroduceParameterObject") == 5


def test_a_stratum_smaller_than_the_quota_is_taken_whole():
    """Three sites and a quota of five is a smaller sample, not an error."""
    sites = many_sites("ExtractMethod", 10) + many_sites("IntroduceParameterObject", 3)

    drawn = stratified_sample(sites, 5, seed=1)

    assert len(drawn) == 8


def test_labels_stay_unique_when_two_projects_share_a_file_name():
    """Two corpus projects both hold a MainActivity.java at position 0.

    The obvious label -- transformation, ordinal, file stem -- collides on
    exactly this input, and a collision would silently merge two judgements.
    """
    sites = [
        Site("one/MainActivity.java", 0, "MainActivity", "onCreate", "LongMethod", "ExtractMethod"),
        Site("two/MainActivity.java", 0, "MainActivity", "onCreate", "LongMethod", "ExtractMethod"),
    ]

    labels = [review_id for review_id, _ in label_sample(sites)]

    assert labels == ["EM01", "EM02"]


def test_labels_restart_the_numbering_for_each_transformation():
    sites = many_sites("ExtractMethod", 2) + many_sites("IntroduceParameterObject", 2)

    assert [review_id for review_id, _ in label_sample(sites)] == [
        "EM01",
        "EM02",
        "IPO01",
        "IPO02",
    ]


def test_wilson_matches_the_interval_computed_by_hand():
    """18 of 20, z = 1.96.

    z^2 = 3.8416; denominator = 1 + 3.8416/20 = 1.19208.
    centre = (0.9 + 3.8416/40) / 1.19208 = 0.99604 / 1.19208 = 0.835548.
    spread = 1.96 * sqrt(0.9*0.1/20 + 3.8416/1600) / 1.19208
           = 1.96 * sqrt(0.0069010) / 1.19208 = 0.162822 / 1.19208 = 0.136587.
    So the interval is [0.698961, 0.972135], rounded to four places.
    """
    assert wilson(18, 20) == (0.699, 0.9721)


def test_wilson_stays_inside_the_unit_interval_at_the_boundary():
    """20 of 20. The normal approximation gives [1.0, 1.0]; this is why it is not used."""
    low, high = wilson(20, 20)

    assert 0.0 < low < 1.0
    assert high == 1.0


def test_wilson_of_nothing_is_the_whole_range():
    assert wilson(0, 0) == (0.0, 1.0)


def sheet(path: Path, rows: list[dict[str, object]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in SHEET_COLUMNS})
    return path


def sheet_row(review_id: str, **answers: object) -> dict[str, object]:
    return {
        "review_id": review_id,
        "refactoring": "ExtractMethod",
        "smell": "LongMethod",
        "class_name": "C",
        "method": "m",
        "file": "p/C.java",
        "ordinal": 0,
        **answers,
    }


def test_an_unfilled_row_is_skipped_rather_than_scored(tmp_path):
    """A half-filled sheet reports on the half that is filled."""
    path = sheet(
        tmp_path / "sheet.csv",
        [
            sheet_row("EM01", behaviour="preserved", benefit="improves", acceptance="as_is"),
            sheet_row("EM02"),
        ],
    )

    assert [j.review_id for j in read_judgements(path)] == ["EM01"]


def test_a_value_outside_the_rubric_raises(tmp_path):
    """A typo in a spreadsheet must not become a category in the thesis."""
    path = sheet(
        tmp_path / "sheet.csv",
        [sheet_row("EM01", behaviour="preserved", benefit="improved", acceptance="as_is")],
    )

    with pytest.raises(ValueError, match="benefit='improved'"):
        read_judgements(path)


def test_the_row_number_in_the_error_is_the_spreadsheet_row(tmp_path):
    """The reviewer fixes this in a spreadsheet, where the header is row 1."""
    path = sheet(
        tmp_path / "sheet.csv",
        [
            sheet_row("EM01", behaviour="preserved", benefit="improves", acceptance="as_is"),
            sheet_row("EM02", behaviour="preserved", benefit="improves", acceptance="merge"),
        ],
    )

    with pytest.raises(ValueError, match="row 3"):
        read_judgements(path)


def test_the_ordinal_travels_with_the_judgement(tmp_path):
    """Scoring checks the sheet still describes the sample; it needs the key to do it."""
    path = sheet(
        tmp_path / "sheet.csv",
        [
            {
                **sheet_row("EM01", behaviour="preserved", benefit="improves", acceptance="as_is"),
                "ordinal": 7,
            }
        ],
    )

    assert read_judgements(path)[0].ordinal == 7


def test_the_pooled_rate_is_reweighted_by_the_true_stratum_sizes():
    """Two strata of two, one accepted throughout and one accepted half the time.

    Populations are 300 and 100. Read off the sample the pooled rate would be
    (0.5 + 1.0)/2 = 0.75, which describes a world where the two transformations
    are equally common. Reweighted it is (0.5*300 + 1.0*100)/400 = 0.625.
    """
    judgements = [
        judgement("EM01", "ExtractMethod", Acceptance.AS_IS),
        judgement("EM02", "ExtractMethod", Acceptance.REJECT),
        judgement("IPO01", "IntroduceParameterObject", Acceptance.AS_IS),
        judgement("IPO02", "IntroduceParameterObject", Acceptance.AFTER_EDIT),
    ]

    summary = summarise(judgements, {"ExtractMethod": 300, "IntroduceParameterObject": 100})

    assert summary["acceptable_reweighted"] == 0.625


def test_a_rewrite_needing_an_edit_still_counts_as_acceptable():
    """Only a rejection is a failure; a bad name is a minute of a reviewer's time."""
    judgements = [judgement("EM01", "ExtractMethod", Acceptance.AFTER_EDIT)]

    summary = summarise(judgements, {"ExtractMethod": 10})

    assert summary["by_refactoring"]["ExtractMethod"]["acceptable"] == 1.0


def test_a_category_nobody_chose_is_reported_as_zero():
    """A count of zero is a result: no reviewed rewrite changed behaviour."""
    judgements = [judgement("EM01", "ExtractMethod", Acceptance.AS_IS)]

    summary = summarise(judgements, {"ExtractMethod": 10})

    assert summary["by_refactoring"]["ExtractMethod"]["behaviour"] == {
        "preserved": 1,
        "unclear": 0,
        "changed": 0,
    }


def test_acceptance_is_crossed_with_what_the_compiler_said():
    """The reason the sheet is blind: the two verdicts have to be comparable."""
    judgements = [
        judgement("EM01", "ExtractMethod", Acceptance.AS_IS),
        judgement("EM02", "ExtractMethod", Acceptance.REJECT),
    ]
    verdicts = {"EM01": "no_new_errors", "EM02": "no_new_errors"}

    summary = summarise(judgements, {"ExtractMethod": 10}, verdicts)

    assert summary["acceptance_by_verdict"]["no_new_errors"] == {
        "as_is": 1,
        "after_edit": 0,
        "reject": 1,
    }


def test_a_sampled_site_with_no_recorded_verdict_is_named_unknown():
    """Absence is reported rather than folded into one of the compiler's answers."""
    summary = summarise(
        [judgement("EM01", "ExtractMethod", Acceptance.AS_IS)], {"ExtractMethod": 10}, {}
    )

    assert list(summary["acceptance_by_verdict"]) == ["unknown"]


def test_the_diff_marks_what_left_and_what_arrived():
    before = b"class C {\n    void m() {\n        a();\n    }\n}\n"
    after = b"class C {\n    void m() {\n        b();\n    }\n}\n"

    diff = diff_text(before, after, "C.m")

    assert "-        a();" in diff
    assert "+        b();" in diff
    assert "C.m (before)" in diff


def test_the_diff_survives_bytes_that_are_not_utf8():
    """Corpus files are other people's, and one of them is not UTF-8."""
    diff = diff_text(b"class C {\xff}\n", b"class D {\xff}\n", "C")

    assert "-class C" in diff


def test_a_method_carrying_three_smells_gives_three_addressable_sites():
    """``OrderManager.priceOrder`` is 43 lines, takes six parameters and nests five deep.

    That is one method and three separate automatable findings, which is exactly
    the case a name-based key cannot tell apart: all three rows say
    ``OrderManager.priceOrder``, and only their position separates them.
    """
    found = sites_in((FIXTURES / "OrderManager.java").read_bytes(), "OrderManager.java")

    assert [(cls, method) for cls, method, _, _, _ in found] == [("OrderManager", "priceOrder")] * 3
    assert {smell for _, _, smell, _, _ in found} == {
        "LongMethod",
        "LongParameterList",
        "DeepNesting",
    }


def test_the_walk_finds_the_sites_in_the_same_order_twice():
    """The ordinal is only a key while this holds."""
    source = (FIXTURES / "OrderManager.java").read_bytes()

    assert sites_in(source, "OrderManager.java") == sites_in(source, "OrderManager.java")


def test_a_file_that_does_not_parse_yields_no_sites():
    """Refuse rather than guess: an unparseable file has no established sites."""
    assert sites_in(b"\xff\xfe not java at all", "broken.java") == []
