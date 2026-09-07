"""Tests for scoring the detectors from the stored feature table.

`replay` produces every Approach A number the Results chapter reports: the
sensitivity sweep, the calibrated thresholds and the headline scores all reach
the detectors through this function rather than through the corpus. It had no
tests at all, which mattered most for the one thing it does silently.

A row whose `sample_id` is not among the supplied samples is skipped without a
word. That is correct for a table wider than the sample set, and it is also what
a broken join looks like: change the key on either side and every row is skipped,
`replay` returns an empty list, and the scoring downstream reports on nothing at
all rather than failing. Two tests below pin that behaviour so the difference
between "some rows do not apply" and "no rows apply any more" cannot pass unseen.

Expected verdicts are hand-derived from the threshold. Long Method fires on
``MLOC > 30`` (`thresholds.long_method_loc`), and the LOC counter scores a method
as one line for its signature plus one per statement, the lone closing brace not
counting -- so thirty statements measure 31 and trip it, and twenty-nine measure
30 and do not.
"""

from __future__ import annotations

import csv
from pathlib import Path

from javasmell.analysis import analyze_source
from javasmell.detectors.thresholds import DEFAULT
from javasmell.evaluation.dataset import columns, row
from javasmell.evaluation.mlcq import Review, Sample
from javasmell.evaluation.replay import replay

#: Statements that put the method one line past `long_method_loc`, and one line
#: short of it. See the module docstring for the derivation.
TRIPS = 30
STOPS_SHORT = 29


def make_sample(sample_id: str = "42", smell: str = "long method") -> Sample:
    return Sample(
        sample_id=sample_id,
        smell=smell,
        entity_type="function" if smell in ("long method", "feature envy") else "class",
        code_name="com.acme.Ledger",
        repository="git@github.com:apache/alpha.git",
        commit_hash="abcdef0123456789",
        path="/src/com/acme/Ledger.java",
        start_line=1,
        end_line=9,
        reviews=(Review(sample_id=sample_id, reviewer_id="1", smell=smell, severity="major"),),
    )


def method_of(statements: int):
    """A class with one method carrying exactly this many statement lines."""
    body = "\n".join(f"    int v{i} = {i};" for i in range(statements))
    source = f"class Ledger {{\n  void work() {{\n{body}\n  }}\n}}"
    cls = analyze_source(source).units[0].classes[0]
    return cls, cls.methods[0]


def write_table(path: Path, records: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns()))
        writer.writeheader()
        writer.writerows(records)
    return path


def test_the_loc_counter_matches_the_derivation(tmp_path):
    """The arithmetic the other expectations rest on, asserted rather than assumed."""
    _, method = method_of(TRIPS)
    assert method.metrics["MLOC"] == TRIPS + 1 == 31
    _, shorter = method_of(STOPS_SHORT)
    assert shorter.metrics["MLOC"] == STOPS_SHORT + 1 == 30
    assert DEFAULT.long_method_loc == 30


def test_a_row_past_the_threshold_is_reported_as_fired(tmp_path):
    sample = make_sample()
    cls, method = method_of(TRIPS)
    table = write_table(tmp_path / "dataset.csv", [row(sample, cls, method)])

    predictions = replay(table, [sample], DEFAULT)

    assert len(predictions) == 1
    assert predictions[0].fired["strategy"] is True
    assert predictions[0].severity["strategy"] is not None


def test_a_row_at_the_threshold_is_not_fired(tmp_path):
    """31 lines trip Long Method and 30 do not: the comparison is strict."""
    sample = make_sample()
    cls, method = method_of(STOPS_SHORT)
    table = write_table(tmp_path / "dataset.csv", [row(sample, cls, method)])

    predictions = replay(table, [sample], DEFAULT)

    assert len(predictions) == 1
    assert predictions[0].fired["strategy"] is False


def test_a_row_without_a_matching_sample_is_skipped(tmp_path):
    """A table wider than the sample set is ordinary, and must not raise."""
    listed = make_sample("42")
    absent = make_sample("999")
    cls, method = method_of(TRIPS)
    table = write_table(
        tmp_path / "dataset.csv",
        [row(listed, cls, method), row(absent, cls, method)],
    )

    predictions = replay(table, [listed], DEFAULT)

    assert [p.sample.sample_id for p in predictions] == ["42"]


def test_a_join_that_matches_nothing_yields_nothing(tmp_path):
    """The failure this function cannot report, pinned so a reader can see it.

    Nothing here is wrong: skipping unmatched rows is the documented behaviour.
    The point is that a *total* mismatch -- a renamed key, a table built against
    a different sample set -- is indistinguishable from it at this level, and
    produces an empty result rather than an error. Whatever consumes `replay`
    is the layer that has to notice, and this test is the record of why.
    """
    cls, method = method_of(TRIPS)
    table = write_table(tmp_path / "dataset.csv", [row(make_sample("42"), cls, method)])

    assert replay(table, [make_sample("other-id")], DEFAULT) == []


def test_blob_is_scored_under_both_of_its_variants(tmp_path):
    """`blob` is the one smell measured two ways, and both must come back."""
    sample = make_sample("7", smell="blob")
    cls, _ = method_of(TRIPS)
    table = write_table(tmp_path / "dataset.csv", [row(sample, cls, None)])

    predictions = replay(table, [sample], DEFAULT)

    assert len(predictions) == 1
    assert set(predictions[0].fired) == {"strategy", "with_size"}
    assert set(predictions[0].severity) == {"strategy", "with_size"}
