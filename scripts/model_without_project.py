"""What Approach B answers when it is shown one file instead of the project.

    python scripts/model_without_project.py

Writes ``data/results/model_without_project.json``.

The question is forced by putting the classifier behind the API. A caller may
point the analyser at a single file, and the model will answer: it takes a row of
numbers and returns a probability whatever those numbers came from. VD-16 already
settled what happens to the *rules* in a one-file "project" -- ATFD and CBO
collapse towards zero, so God Class and Feature Envy fall quiet -- but said
nothing about the model, which was never served at the time.

Two things are measured, and they are different questions.

**Does the verdict change.** Every entity is judged twice, once with the project
measured whole and once with its file measured alone, and the two verdicts are
compared. A lost detection and a false alarm are counted separately because they
are not equally bad: falling quiet is the failure mode VD-16 describes for the
rules, and matching it would mean B degrades no worse than A.

**Does the explanation stay honest.** This is the question the verdict comparison
cannot answer. A verdict that survives may still be explained by a measurement
that only looks the way it does because the rest of the project was not read, and
the interface shows that explanation as the reason. So the measurements are
compared column by column, and the decisive one is checked against the columns
that moved.

Projects are sampled with a fixed seed and named in the output, because the point
is a general property of measuring without context rather than a fact about one
repository.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.analysis import analyze_path  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.metrics.calculator import compute_all  # noqa: E402
from javasmell.ml.serving import (  # noqa: E402
    Prediction,
    SmellModel,
    load_models,
    predict,
    vector,
)
from javasmell.model.entities import ProjectModel  # noqa: E402
from javasmell.parsing.java_parser import JavaParser, iter_java_files  # noqa: E402

DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_MODELS = Path("data/models")
DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "model_without_project.json"

# Enough repositories that a single unusual one cannot carry the finding, few
# enough that the pass stays minutes rather than hours. Every project is measured
# twice, so this costs roughly double a normal analysis run.
DEFAULT_PROJECTS = 5
SEED = 20260901

#: (file, class name, method name or None). The file belongs in the key: a
#: corpus project may declare the same class name in several files, and keying
#: on the name alone would silently drop all but one of them.
Key = tuple[str, str, str | None]


def measured_alone(root: Path) -> ProjectModel:
    """Every file measured as if it were the only file in the project.

    Each unit is compiled into a project of its own and measured there, then the
    measured units are collected. Measuring them together afterwards would be the
    thing being compared against, not the thing being measured.
    """
    collected = ProjectModel(root=str(root))
    parser = JavaParser()
    for path in iter_java_files(str(root)):
        try:
            alone = ProjectModel(root=str(root))
            alone.units.append(parser.parse_file(path))
        except (OSError, UnicodeDecodeError):
            continue
        collected.units.extend(compute_all(alone).units)
    return collected


def verdicts(model: SmellModel, project: ProjectModel) -> dict[Key, Prediction]:
    return {(p.file_path, p.class_name, p.method): p for p in predict(model, project).predictions}


def rows(model: SmellModel, project: ProjectModel) -> dict[Key, list[float]]:
    """The feature row per entity, for the columns that comparison needs."""
    collected: dict[Key, list[float]] = {}
    for cls in project.classes:
        entities = [(cls, None)] if model.is_class_level else [(cls, m) for m in cls.methods]
        for owner, method in entities:
            row = vector(owner, method, model.features)
            if row is not None:
                key = (owner.file_path, owner.name, None if method is None else method.name)
                collected[key] = [float(value) for value in row]
    return collected


@dataclass
class Comparison:
    """One model's two passes, reduced to counts that add across projects."""

    entities: int = 0
    flagged_with_project: int = 0
    flagged_file_alone: int = 0
    agree: int = 0
    lost: int = 0
    false_alarm: int = 0
    measurements_compared: int = 0
    #: Per feature, how many entities it measured differently without context.
    measurement_moved: Counter[str] = field(default_factory=Counter)
    #: Per feature, how often it was the reason given for a file-alone flag.
    decisive_file_alone: Counter[str] = field(default_factory=Counter)
    decisive_on_a_moved_measurement: int = 0
    explained_file_alone: int = 0

    def add(self, other: Comparison) -> None:
        self.entities += other.entities
        self.flagged_with_project += other.flagged_with_project
        self.flagged_file_alone += other.flagged_file_alone
        self.agree += other.agree
        self.lost += other.lost
        self.false_alarm += other.false_alarm
        self.measurements_compared += other.measurements_compared
        self.measurement_moved.update(other.measurement_moved)
        self.decisive_file_alone.update(other.decisive_file_alone)
        self.decisive_on_a_moved_measurement += other.decisive_on_a_moved_measurement
        self.explained_file_alone += other.explained_file_alone

    def to_json(self) -> dict[str, int | dict[str, int]]:
        return {
            "entities": self.entities,
            "flagged_with_project": self.flagged_with_project,
            "flagged_file_alone": self.flagged_file_alone,
            "agree": self.agree,
            "lost": self.lost,
            "false_alarm": self.false_alarm,
            "measurements_compared": self.measurements_compared,
            "measurement_moved": dict(self.measurement_moved.most_common()),
            "decisive_file_alone": dict(self.decisive_file_alone.most_common()),
            "decisive_on_a_moved_measurement": self.decisive_on_a_moved_measurement,
            "explained_file_alone": self.explained_file_alone,
        }


def compare(model: SmellModel, whole: ProjectModel, alone: ProjectModel) -> Comparison:
    """One model's two passes over one project, reduced to counts."""
    with_context = verdicts(model, whole)
    without = verdicts(model, alone)
    shared = sorted(set(with_context) & set(without))

    lost = false_alarm = agree = flagged_whole = flagged_alone = 0
    for key in shared:
        here = with_context[key].flagged
        there = without[key].flagged
        flagged_whole += here
        flagged_alone += there
        agree += here == there
        lost += here and not there
        false_alarm += there and not here

    row_whole = rows(model, whole)
    row_alone = rows(model, alone)
    comparable = sorted(set(row_whole) & set(row_alone))
    moved: Counter[str] = Counter()
    for key in comparable:
        for index, name in enumerate(model.features):
            if row_whole[key][index] != row_alone[key][index]:
                moved[name] += 1

    unstable = set(moved)
    decisive_alone: Counter[str] = Counter()
    on_moved = 0
    for key in shared:
        prediction = without[key]
        if not prediction.flagged:
            continue
        contribution = prediction.decisive
        if contribution is None:
            continue
        decisive_alone[contribution.feature] += 1
        on_moved += contribution.feature in unstable

    return Comparison(
        entities=len(shared),
        flagged_with_project=flagged_whole,
        flagged_file_alone=flagged_alone,
        agree=agree,
        lost=lost,
        false_alarm=false_alarm,
        measurements_compared=len(comparable),
        measurement_moved=moved,
        decisive_file_alone=decisive_alone,
        decisive_on_a_moved_measurement=on_moved,
        explained_file_alone=sum(decisive_alone.values()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--projects", type=int, default=DEFAULT_PROJECTS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    available = sorted(path.name for path in args.corpus.iterdir() if path.is_dir())
    if not available:
        print(f"no projects under {args.corpus}", file=sys.stderr)
        return 1
    chosen = random.Random(args.seed).sample(available, min(args.projects, len(available)))

    models = load_models(args.models, args.dataset)
    totals = {model.smell: Comparison() for model in models}
    per_project: dict[str, dict[str, int]] = {}

    for name in chosen:
        root = args.corpus / name
        whole = analyze_path(str(root))
        alone = measured_alone(root)
        per_project[name] = {"files": len(whole.units), "classes": len(list(whole.classes))}
        for model in models:
            totals[model.smell].add(compare(model, whole, alone))
        print(f"{name}: {per_project[name]['files']} files", flush=True)

    for smell, counts in totals.items():
        share = counts.agree / counts.entities if counts.entities else 0.0
        print(
            f"{smell:<14} agree {share:.1%}  lost {counts.lost}  false alarm {counts.false_alarm}",
            flush=True,
        )

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "per_smell": {smell: counts.to_json() for smell, counts in totals.items()},
        "projects": per_project,
        "seed": args.seed,
        "environment": environment(),
    }
    path = args.out / RESULT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
