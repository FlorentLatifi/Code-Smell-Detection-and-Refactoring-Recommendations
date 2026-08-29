"""Scoring the detectors from the stored feature table instead of the corpus.

Every field the detectors read is a column of that table (VD-23), so a replay
reaches the same verdicts as a full run -- ``test_dataset`` pins that equivalence
against every fixture entity -- in under a second instead of 95 minutes.

That is what makes the sensitivity sweep possible at all. A sweep varies only
thresholds, and thresholds play no part in the measuring; re-measuring 690 000
files per configuration would put a twenty-configuration sweep past thirty hours,
which in practice means it never runs.

This lives in the package rather than in whichever script needed it first,
because the second script that needed it would otherwise have copied it, and a
copy is how the two LOC counters drifted apart (VD-21).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from javasmell.detectors.rules import detect_entity
from javasmell.detectors.thresholds import Thresholds
from javasmell.evaluation.dataset import entities
from javasmell.evaluation.mlcq import Sample
from javasmell.evaluation.scoring import VARIANTS, Prediction


def replay(
    dataset_path: str | Path, samples: Iterable[Sample], thresholds: Thresholds
) -> list[Prediction]:
    """One prediction per row of the table, at the given thresholds.

    The rows carry measurements, not labels, so the samples are supplied by the
    caller: MLCQ is small and re-reading it costs nothing worth caching.
    """
    by_id = {sample.sample_id: sample for sample in samples}
    predictions: list[Prediction] = []
    with Path(dataset_path).open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            sample = by_id.get(record["sample_id"])
            if sample is None:
                continue
            cls, method = entities(record)
            found = {s.smell_type for s in detect_entity(cls, method, thresholds)}
            predictions.append(
                Prediction(
                    sample=sample,
                    fired={
                        name: not found.isdisjoint(detectors)
                        for name, detectors in VARIANTS[sample.smell].items()
                    },
                )
            )
    return predictions
