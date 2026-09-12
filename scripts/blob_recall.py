"""What a reviewer calls a blob when the strategy disagrees.

    python scripts/blob_recall.py

Writes ``data/results/blob_recall.json`` and a CSV naming the misses the
cohesion clause can never accept. Seconds: every field this reads is a column
of the committed feature table (VD-23), so nothing is re-parsed and nothing is
re-measured. The one exception is the optional corpus confirmation described
below, which reads a couple of dozen files.

**The question.** ``blocking_conditions.py`` reports which clause stopped each
miss and finds that 254 of 315 blob misses fail two clauses or three. That rules
out "the thresholds are slightly severe" and leaves the harder question
untouched: what do these classes look like? A reader who is told that recall is
0.10 and that most misses fail on several clauses at once will reasonably
suspect the strategy is measuring the wrong things.

**What the answer decides.** If the missed classes resemble the flagged ones on
a dimension the strategy never reads, the fix is a clause and the work is in
``detectors``. If they resemble the classes reviewers called clean on every
dimension measured, no clause reaches them, and the finding belongs in the
thesis as a property of the ground truth rather than as a defect to repair.

**The corpus confirmation.** Cohesion saturation is read off the feature table,
where TCC is 1.0 without saying why. Two different classes carry that value: one
genuinely cohesive, and one with fewer than two public instance methods, where
the metric is undefined and the calculator's guard supplies 1.0. Only the second
is a ceiling. With ``--corpus`` the named classes are re-parsed and their public
instance methods counted, which turns the distinction from an inference into a
measurement. Without the corpus the field is written as null rather than
guessed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.detectors.thresholds import DEFAULT  # noqa: E402
from javasmell.evaluation.corpus import Corpus, long_path  # noqa: E402
from javasmell.evaluation.missed import (  # noqa: E402
    SATURATED_COLUMNS,
    Saturated,
    partition,
    profile,
    recall_by_severity,
    saturated_cohesion,
)
from javasmell.evaluation.mlcq import Aggregation, Sample, load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.scoring import VARIANTS  # noqa: E402
from javasmell.parsing.java_parser import JavaParser  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "blob_recall.json"
SATURATED_NAME = "blob_recall_saturated.csv"

#: The smell this script is about. Blob alone, because the question comes from
#: its recall and because it is the only MLCQ smell with two rule variants: the
#: published strategy and the size disjunction VD-09 keeps separate. Reporting
#: both is what stops the answer being an artefact of the stricter one.
SMELL = "blob"

#: Two clauses' worth of "public instance methods" is what TCC needs to be
#: defined at all; see ``metrics.calculator._tight_class_cohesion``.
TCC_MINIMUM_METHODS = 2

#: How many saturated classes the results file names with their measurements.
#: The chapter prints a table of them and a page holds about this many; the CSV
#: beside it carries every one, so nothing is lost by the cut.
SATURATED_REPORTED = 8

SATURATED_COLUMNS_CSV = [
    "sample_id",
    "class_name",
    "failed",
    *SATURATED_COLUMNS,
    "public_instance_methods",
    "path",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def count_public_instance_methods(
    corpus: Corpus, sample: Sample, class_name: str, parser: JavaParser
) -> int | None:
    """How many public instance methods the named class really declares.

    None when the file is not in the corpus, which is the honest answer for a
    checkout that never ran step 1 and is not the same answer as zero.
    """
    if not corpus.has_source(sample):
        return None
    source = long_path(corpus.source_path(sample))
    unit = parser.parse_source(source.read_bytes(), str(sample.path))
    for cls in unit.classes:
        if cls.name == class_name:
            return len([m for m in cls.instance_methods if m.is_public])
    return None


def confirm(
    found: list[Saturated], samples: dict[str, Sample], corpus_root: Path
) -> dict[str, int | None]:
    """Re-parse the saturated classes and count what TCC needs to be defined."""
    if not corpus_root.exists():
        return dict.fromkeys((item.sample_id for item in found), None)
    corpus = Corpus(corpus_root)
    parser = JavaParser()
    counts: dict[str, int | None] = {}
    for item in found:
        sample = samples.get(item.sample_id)
        counts[item.sample_id] = (
            None
            if sample is None
            else count_public_instance_methods(corpus, sample, item.class_name, parser)
        )
    return counts


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.mlcq, args.dataset):
        if not path.exists():
            print(f"not found: {path}", file=sys.stderr)
            return 1

    samples = list(load_samples(args.mlcq))
    by_id = {sample.sample_id: sample for sample in samples}

    per_variant: dict[str, object] = {}
    groups = {}
    for variant in VARIANTS[SMELL]:
        groups[variant] = partition(args.dataset, samples, SMELL, variant, DEFAULT)
        per_variant[variant] = profile(groups[variant]) | {
            "recall_by_severity": {
                how.value: recall_by_severity(args.dataset, samples, SMELL, variant, DEFAULT, how)
                for how in (Aggregation.MEAN, Aggregation.MAX)
            }
        }

    # Vetem te strategjia e botuar: klauzola e kohezionit eshte e saj, dhe te
    # varianti me madhesi nje klase e kapur nga LargeClass-i nuk eshte fare
    # mospërputhje per te cilen te pyetet cila klauzole e ndaloi.
    found = saturated_cohesion(groups["strategy"].missed, DEFAULT)
    counts = confirm(found, by_id, args.corpus)
    undefined = [
        item.sample_id
        for item in found
        if (counts.get(item.sample_id) or 0) < TCC_MINIMUM_METHODS
        and counts.get(item.sample_id) is not None
    ]

    args.out.mkdir(parents=True, exist_ok=True)
    saturated_path = args.out / SATURATED_NAME
    with saturated_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SATURATED_COLUMNS_CSV)
        writer.writeheader()
        for item in found:
            writer.writerow(
                {
                    "sample_id": item.sample_id,
                    "class_name": item.class_name,
                    "failed": " ".join(item.failed),
                    **{name: f"{item.metrics[name]:g}" for name in SATURATED_COLUMNS},
                    "public_instance_methods": (
                        "" if counts.get(item.sample_id) is None else counts[item.sample_id]
                    ),
                    "path": item.path,
                }
            )

    summary = {
        "smell": SMELL,
        "aggregation": Aggregation.MEAN.value,
        "per_variant": per_variant,
        "saturated_cohesion": {
            "count": len(found),
            "confirmed_undefined": len(undefined),
            "checked": sum(1 for value in counts.values() if value is not None),
            "classes": [item.class_name for item in found],
            # Emrat me matjet e tyre, qe kapitulli te ndertoje tabele pa e lexuar
            # CSV-ne: i gjithe teksti i punimit ndertohet nga JSON-i.
            "largest": [
                {
                    "class_name": item.class_name,
                    "failed": " ".join(item.failed),
                    "public_instance_methods": counts.get(item.sample_id),
                    **{name: item.metrics[name] for name in SATURATED_COLUMNS},
                }
                for item in found[:SATURATED_REPORTED]
            ],
        },
        "environment": environment(),
    }
    result_path = args.out / RESULT_NAME
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for variant, entry in per_variant.items():
        assert isinstance(entry, dict)
        support = entry["support"]
        assert isinstance(support, dict)
        print(
            f"\n{SMELL} / {variant}: {support['missed']} të humbura, {support['caught']} të kapura"
        )
        quarts = entry["quartiles"]
        assert isinstance(quarts, dict)
        for metric in ("CLOC", "NOM", "WMC"):
            cells = "   ".join(
                f"{name} {quarts[metric][name][1]:g}" for name in ("caught", "missed", "negative")
            )
            print(f"  mediana {metric:<5} {cells}")
        below = entry["below_negative_median"]
        assert isinstance(below, dict)
        print(f"  nën medianën e negativëve (CLOC): {below['CLOC']}/{support['missed']}")
        sep = entry["separation"]
        assert isinstance(sep, dict)
        best = sorted(sep.items(), key=lambda pair: -pair[1])[:3]
        print("  ndarja më e mirë: " + ", ".join(f"{m} {v:.3f}" for m, v in best))

    print(f"\nkohezion i ngopur te mospërputhjet e mëdha: {len(found)}")
    print(
        f"  të konfirmuara me nën {TCC_MINIMUM_METHODS} metoda publike instance: {len(undefined)}"
    )
    print()
    print(f"Wrote {result_path} and {saturated_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
