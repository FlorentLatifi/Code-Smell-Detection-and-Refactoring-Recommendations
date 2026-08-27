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

*The entity's own identity is stored, not just the sample's range.* Beyond
``metrics`` the rules consult ``kind``, ``is_constructor`` and ``is_accessor``.
The last of those is not a field but a property derived from the method's name
and how many lines it spans, so the row keeps the name and the span and lets it
derive itself. Storing the answer instead and forcing it back with a synthetic
name would make the replay agree with a definition of "accessor" that had since
changed, and agree silently. ``entities`` is the exact inverse of ``row`` for
every field a detector reads, and ``test_dataset`` holds it to that.
"""

from __future__ import annotations

from collections.abc import Mapping

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
    "start_line",  # the reviewers' range, kept for tracing back to MLCQ
    "end_line",
)

# What the detectors read that is not a metric, plus what `is_accessor` derives
# itself from. `entity_*` is the entity the matcher resolved, which is not
# always the range MLCQ recorded.
STRUCTURE = (
    "class_name",
    "class_kind",
    "entity_name",
    "entity_start_line",
    "entity_end_line",
    "is_constructor",
)

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
        "class_name": cls.name,
        "class_kind": cls.kind,
        "entity_name": cls.name if method is None else method.name,
        "entity_start_line": str(cls.start_line if method is None else method.start_line),
        "entity_end_line": str(cls.end_line if method is None else method.end_line),
        "is_constructor": _flag(None if method is None else method.is_constructor),
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


def entities(record: Mapping[str, str]) -> tuple[ClassInfo, MethodInfo | None]:
    """Rebuild what the detectors saw from one row: the inverse of :func:`row`.

    Only the fields a detector reads are restored, and they are restored as
    themselves rather than as their consequences -- the method keeps its real
    name and span so ``is_accessor`` derives the same answer it derived during
    the measured run. Everything else (fields, bodies, accesses) is left empty
    on purpose: a detector that started reading one of them would be measuring
    something this row never captured, and an empty list makes that show up as
    a wrong number in the equivalence test rather than as a plausible one.
    """
    method: MethodInfo | None = None
    if record["entity_type"] == "function":
        method = MethodInfo(
            name=record["entity_name"],
            return_type=None,
            parameters=[],
            modifiers=frozenset(),
            start_line=int(record["entity_start_line"]),
            end_line=int(record["entity_end_line"]),
            is_constructor=record["is_constructor"] == "1",
            metrics={
                name: float(record[f"m_{name}"])
                for name in METHOD_METRICS
                if record[f"m_{name}"] != ""
            },
        )

    cls = ClassInfo(
        name=record["class_name"],
        kind=record["class_kind"],
        package="",
        file_path=record["path"],
        modifiers=frozenset(),
        superclass=None,
        interfaces=[],
        fields=[],
        methods=[] if method is None else [method],
        start_line=int(record["entity_start_line"]) if method is None else 0,
        end_line=int(record["entity_end_line"]) if method is None else 0,
        metrics={
            name: float(record[f"c_{name}"]) for name in CLASS_METRICS if record[f"c_{name}"] != ""
        },
    )
    return cls, method
