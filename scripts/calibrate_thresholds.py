"""Çfarë do të arrinin rregullat po t'u kalibroheshin pragjet mbi këtë korpus.

    python scripts/calibrate_thresholds.py

Shkruan ``data/results/threshold_calibration.json``.

VD-34 e regjistroi tundimin dhe e refuzoi: fshirja tregoi se ulja e pragut të Long
Method-it e ngre MCC-në nga 0.580 në 0.690, por adoptimi i asaj vlere do të ishte
matje e sa mirë u zgjodh pragu mbi bashkësinë e vlerësimit, jo e sa mirë punon
detektimi. Kushti që u shkrua atje ishte i qartë: **kalibrim mbi një bashkësi dhe
vlerësim mbi një tjetër, të paprekur.** Ky skript e plotëson atë kusht.

**Si ndahet korpusi.** Me `GroupKFold` sipas depos, e njëjta ndarje që përdor
Qasja B (VD-12). Për secilin fold, pragu zgjidhet duke parë **vetëm** foldet e
trajnimit dhe pikëzohet mbi foldin e mbajtur jashtë, të cilin zgjedhja nuk e ka
parë kurrë. Parashikimet e të gjitha foldeve bashkohen dhe pikëzohen një herë, që
shifra e raportuar të jetë jashtë-fold-it në të njëjtin kuptim me atë të Qasjes B.

**Pse është e lirë.** Pragjet nuk hyjnë në matje (VD-23): çdo konfigurim
rirendit detektorët mbi tabelën e ruajtur në sekonda. Prandaj çdo konfigurim
rendohet **një herë**, dhe ndarja në folde bëhet mbi rezultatin e ruajtur.

**Çfarë raportohet.** Tri shifra për çdo erë: pragu i botuar mbi tërë korpusin,
pragu i kalibruar i pikëzuar jashtë-fold-it, dhe vlerat që foldet zgjodhën. E
fundit ka rëndësi më vete: nëse foldet nuk pajtohen për një vlerë, atëherë
«pragu optimal» është artefakt i bashkësisë dhe jo veti e gjuhës.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.detectors.thresholds import DEFAULT  # noqa: E402
from javasmell.evaluation.mlcq import Aggregation, Sample, load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.replay import replay  # noqa: E402
from javasmell.evaluation.scoring import (  # noqa: E402
    PRIMARY_VARIANT,
    VARIANTS,
    Confusion,
    Prediction,
    confusion,
)

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_OUT = Path("data/results")
RESULT_NAME = "threshold_calibration.json"

# Të njëjtat pragje që fshin `sweep_thresholds.py`, dhe për të njëjtën arsye:
# vetëm ato që hyjnë në strategjinë parësore të secilës erë.
SWEPT: dict[str, tuple[str, ...]] = {
    "blob": ("god_class_wmc", "god_class_tcc", "god_class_atfd"),
    "data class": ("data_class_woc", "data_class_public_members", "data_class_wmc_low"),
    "long method": ("long_method_loc",),
    "feature envy": ("feature_envy_atfd", "feature_envy_laa", "feature_envy_fdp"),
}

FACTORS = (0.50, 0.75, 1.00, 1.25, 1.50, 2.00)

# Aq folde sa përdor edhe Qasja B, që dy anët e krahasimit të ndahen njësoj.
FOLDS = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--folds", type=int, default=FOLDS)
    return parser


def fold_of(samples: list[Sample], folds: int) -> dict[str, int]:
    """Cilit fold i takon çdo mostër, e ndarë sipas depos.

    Depot renditen sipas emrit dhe u jepen foldeve me radhë, jo rastësisht: një
    ndarje e riprodhueshme nga kushdo që e riekzekuton skriptin vlen më shumë se
    një e balancuar në mënyrë të përsosur, dhe ndarja e ruan vetinë që i vetmi
    kusht e kërkon — asnjë depo nuk bie në dy folde.
    """
    repositories = sorted({sample.repository for sample in samples})
    assigned = {name: index % folds for index, name in enumerate(repositories)}
    return {sample.sample_id: assigned[sample.repository] for sample in samples}


def verdicts(predictions: list[Prediction], smell: str) -> dict[str, bool]:
    """Verdikti parësor për çdo mostër të kësaj ere."""
    return {
        p.sample.sample_id: p.fired[PRIMARY_VARIANT] for p in predictions if p.sample.smell == smell
    }


def labels(samples: list[Sample], smell: str, how: Aggregation) -> dict[str, bool]:
    """Etiketa e agreguar, aty ku strategjia e agregimit jep një të tillë."""
    answers = {}
    for sample in samples:
        if sample.smell != smell:
            continue
        truth = sample.is_smelly(how)
        if truth is not None:
            answers[sample.sample_id] = truth
    return answers


def score(chosen: dict[str, bool], truth: dict[str, bool], ids: list[str]) -> Confusion:
    """The matrix for one set of samples, over the verdicts of one configuration."""
    return confusion((truth[i], chosen[i]) for i in ids if i in truth and i in chosen)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dataset.exists():
        print(f"tabela e veçorive mungon: {args.dataset}", file=sys.stderr)
        return 1

    samples = [s for s in load_samples(args.mlcq) if s.smell in VARIANTS]
    folds = fold_of(samples, args.folds)

    # Çdo konfigurim rendohet një herë; ndarja në folde bëhet mbi rezultatin.
    print("Duke rirenditur konfigurimet…", flush=True)
    replayed: dict[tuple[str, float], list[Prediction]] = {}
    for names in SWEPT.values():
        for name in names:
            published = float(getattr(DEFAULT, name))
            for factor in FACTORS:
                key = (name, factor)
                if key in replayed:
                    continue
                thresholds = replace(DEFAULT, **{name: published * factor})
                replayed[key] = replay(args.dataset, samples, thresholds)

    results: dict[str, dict[str, object]] = {}
    for smell, names in SWEPT.items():
        truth = labels(samples, smell, Aggregation.MEAN)
        by_fold: dict[int, list[str]] = {}
        for sample_id in truth:
            by_fold.setdefault(folds[sample_id], []).append(sample_id)

        pooled = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        picked: dict[str, Counter[float]] = {name: Counter() for name in names}

        for held_out, ids in sorted(by_fold.items()):
            training = [i for fold, rest in by_fold.items() if fold != held_out for i in rest]

            # The choice sees only the training folds. Ties break on the first
            # configuration in a fixed order, so the run is reproducible.
            best_key: tuple[str, float] | None = None
            best_mcc = float("-inf")
            for name in names:
                for factor in FACTORS:
                    mcc = score(verdicts(replayed[(name, factor)], smell), truth, training).mcc
                    if mcc is not None and mcc > best_mcc:
                        best_mcc, best_key = mcc, (name, factor)

            if best_key is None:
                continue
            name, factor = best_key
            picked[name][round(float(getattr(DEFAULT, name)) * factor, 4)] += 1

            held = score(verdicts(replayed[best_key], smell), truth, ids)
            pooled["tp"] += held.tp
            pooled["fp"] += held.fp
            pooled["fn"] += held.fn
            pooled["tn"] += held.tn

        calibrated = Confusion(**pooled)
        # At factor 1.00 every configuration is the published one, so any of them
        # serves as the baseline.
        baseline = score(verdicts(replayed[(names[0], 1.00)], smell), truth, sorted(truth))

        results[smell] = {
            "published": baseline.to_dict(),
            "calibrated": calibrated.to_dict(),
            "chosen": {
                name: {str(value): count for value, count in sorted(counts.items())}
                for name, counts in picked.items()
                if counts
            },
        }
        print(
            f"{smell:<14} e botuar {baseline.mcc:.3f}  e kalibruar {calibrated.mcc:.3f}",
            flush=True,
        )

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "per_smell": results,
        "folds": args.folds,
        "factors": list(FACTORS),
        "aggregation": Aggregation.MEAN.value,
        "variant": PRIMARY_VARIANT,
        "environment": environment(),
    }
    path = args.out / RESULT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
