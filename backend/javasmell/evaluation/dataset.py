"""One row per MLCQ sample: the reviewers' labels beside the measured features.

Producing these rows is the expensive step of the whole evaluation -- every
repository parsed and measured whole, 690 000 Java files, roughly 95 minutes --
and nothing downstream depends on *how* they were produced. Approach B trains on
them, the sensitivity sweep of the Results chapter re-runs the detectors over
them, and re-scoring Approach A after a detector change reads them back. So they
are built once, committed under ``data/results/``, and loaded in seconds instead
of recomputed per experiment. Without that, a sweep over k threshold
configurations would cost k * 95 minutes and simply would not be run.

Two consequences shape the columns.

*Method rows carry the enclosing class's metrics as well as their own.* Feature
Envy is a statement about a method *relative to* its class, and a long method
inside a God Class is not the same observation as one inside a small helper. A
model handed only the nine method metrics cannot express either.

*The three structural fields the detectors read are stored too.* Beyond
``metrics`` the rules consult only ``kind`` (interfaces and enums are excluded
from class strategies) and ``is_constructor``/``is_accessor`` (Feature Envy
skips both). Carrying them means a threshold sweep can rebuild exactly what the
detectors saw without going back to the source.
"""

from __future__ import annotations

from javasmell.evaluation.mlcq import Aggregation, Sample
from javasmell.model.entities import ClassInfo, MethodInfo

# The metric names the calculator actually produces. They are listed rather
# than discovered because a dataset column that appears or vanishes with the
# input would make two runs incomparable. `test_dataset` asserts the lists still
# match the calculator, so adding a metric without adding it here fails the
# suite instead of silently dropping a feature (the VD-21 lesson).
CLASS_METRICS = (
    "AMW", "ATFD", "CBO", "CLOC", "DIT", "LCOM", "LCOM3", "MAXCC", "NOAM",
    "NOC", "NOF", "NOM", "NOPA", "RFC", "TCC", "WMC", "WOC",
)  # fmt: skip

METHOD_METRICS = (
    "ATFD", "CC", "CINT", "FDP", "LAA", "MAXNESTING", "MLOC", "NOAV", "NP",
)  # fmt: skip

IDENTITY = (
    "sample_id",
    "repository",
    "smell",
    "entity_type",
    "path",
    "start_line",
    "end_line",
)

# Everything the rule detectors read that is not a metric; see module docstring.
STRUCTURE = ("class_kind", "is_constructor", "is_accessor")

AGGREGATIONS = (
    Aggregation.MEAN,
    Aggregation.MAX,
    Aggregation.MIN,
    Aggregation.UNANIMOUS,
)

LABELS = (
    "review_count",
    "is_unanimous",
    *[f"{prefix}_{how.value}" for prefix in ("severity", "smelly") for how in AGGREGATIONS],
)


def feature_columns() -> tuple[str, ...]:
    """The model's input columns, class metrics first."""
    return tuple(f"c_{name}" for name in CLASS_METRICS) + tuple(
        f"m_{name}" for name in METHOD_METRICS
    )


def columns() -> tuple[str, ...]:
    return IDENTITY + STRUCTURE + LABELS + feature_columns()


def _flag(value: bool | None) -> str:
    """CSV needs three states here, and "" is the honest one for "not applicable"."""
    return "" if value is None else str(int(value))


def row(sample: Sample, cls: ClassInfo, method: MethodInfo | None) -> dict[str, str]:
    """Flatten one matched sample into its dataset row.

    Class-level samples leave the ``m_*`` columns empty rather than zero. A
    class has no cyclomatic complexity, and writing 0.0 would hand the model a
    measurement that was never taken.
    """
    values: dict[str, str] = {
        "sample_id": sample.sample_id,
        "repository": sample.group,
        "smell": sample.smell,
        "entity_type": sample.entity_type,
        "path": sample.relative_path,
        "start_line": str(sample.start_line),
        "end_line": str(sample.end_line),
        "class_kind": cls.kind,
        "is_constructor": _flag(None if method is None else method.is_constructor),
        "is_accessor": _flag(None if method is None else method.is_accessor),
        "review_count": str(len(sample.reviews)),
        "is_unanimous": _flag(sample.is_unanimous),
    }

    for how in AGGREGATIONS:
        rank = sample.severity_rank(how)
        smelly = sample.is_smelly(how)
        values[f"severity_{how.value}"] = "" if rank is None else str(rank)
        values[f"smelly_{how.value}"] = _flag(smelly)

    for name in CLASS_METRICS:
        measured = cls.metrics.get(name)
        values[f"c_{name}"] = "" if measured is None else repr(measured)
    for name in METHOD_METRICS:
        measured = None if method is None else method.metrics.get(name)
        values[f"m_{name}"] = "" if measured is None else repr(measured)

    return values
