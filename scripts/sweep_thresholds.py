"""Sa e qëndrueshme është detektimi ndaj pragjeve që i janë dhënë.

    python scripts/sweep_thresholds.py

Shkruan ``data/results/threshold_sweep.json``.

Pragjet e Lanza & Marinescu-t janë nxjerrë statistikisht nga një korpus prej
dyzet e pesë sistemesh, jo nga ky korpus. Pyetja e natyrshme është sa varet
rezultati prej tyre: nëse një zhvendosje prej njëzet e pesë përqind e ndryshon
përfundimin, atëherë numri i raportuar flet më shumë për pragun sesa për kodin.

Fshirja bëhet **një prag në një kohë**, me të tjerët të mbajtur te vlera e
botuar. Kjo e mban interpretimin të lexueshëm — çdo lëvizje i atribuohet një
pragu të vetëm — dhe është e vetmja formë e fshirjes që një kapitull rezultatesh
mund ta paraqesë pa u kthyer në tabelë kombinatorike.

Kjo është e mundur vetëm sepse pragjet nuk hyjnë në matje: detektorët rirendisin
mbi tabelën e ruajtur (VD-23), ndaj çdo konfigurim kushton më pak se një sekondë
në vend të 95 minutave.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.detectors.thresholds import DEFAULT  # noqa: E402
from javasmell.evaluation.mlcq import Aggregation, load_samples  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.replay import replay  # noqa: E402
from javasmell.evaluation.scoring import (  # noqa: E402
    PRIMARY_VARIANT,
    VARIANTS,
    score,
    severity_agreement,
)

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_DATASET = Path("data/results/mlcq_dataset.csv")
DEFAULT_OUT = Path("data/results")

RESULT_NAME = "threshold_sweep.json"

# Cili prag prek cilën erë. Vetëm pragjet që hyjnë në strategjinë parësore të
# secilës erë; një prag që nuk e prek atë erë do të jepte një vijë të sheshtë
# dhe do ta zgjeronte tabelën pa shtuar informacion.
SWEPT: dict[str, tuple[str, ...]] = {
    "blob": ("god_class_wmc", "god_class_tcc", "god_class_atfd"),
    "data class": ("data_class_woc", "data_class_public_members", "data_class_wmc_low"),
    "long method": ("long_method_loc",),
    "feature envy": ("feature_envy_atfd", "feature_envy_laa", "feature_envy_fdp"),
}

# Zhvendosje relative rreth vlerës së botuar. Relative e jo absolute, sepse të
# njëjtat faktorë vlejnë njësoj për një numërim (ATFD = 5) dhe për një raport
# (TCC = 1/3), ndërsa një hap absolut do të kishte kuptim vetëm për njërin.
FACTORS = (0.50, 0.75, 1.00, 1.25, 1.50, 2.00)

# Pragjet e ashpërsisë maten veç, sepse ato nuk vendosin nëse një detektor ndez,
# vetëm sa e rëndë e quan atë që gjeti. Fshirja e tyre kundrejt MCC-së do të jepte
# një vijë të sheshtë; e vetmja pyetje që u përket është a e afron zhvendosja e
# tyre ashpërsinë tonë me atë të rishikuesve. VD-06 e premtoi këtë matje.
SEVERITY_SWEPT = ("severity_major", "severity_critical")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dataset.exists():
        print(f"tabela e veçorive mungon: {args.dataset}", file=sys.stderr)
        print("Ekzekuto së pari scripts/build_dataset.py", file=sys.stderr)
        return 1

    samples = [s for s in load_samples(args.mlcq) if s.smell in VARIANTS]

    results: dict[str, dict[str, list[dict[str, object]]]] = {}
    for smell, names in SWEPT.items():
        results[smell] = {}
        for name in names:
            published = float(getattr(DEFAULT, name))
            points: list[dict[str, object]] = []
            for factor in FACTORS:
                value = published * factor
                thresholds = replace(DEFAULT, **{name: value})
                matrix = score(
                    replay(args.dataset, samples, thresholds),
                    smell,
                    PRIMARY_VARIANT,
                    Aggregation.MEAN,
                )
                points.append(
                    {
                        "factor": factor,
                        "value": round(value, 4),
                        "precision": matrix.precision,
                        "recall": matrix.recall,
                        "f1": matrix.f1,
                        "mcc": matrix.mcc,
                        "fired": matrix.tp + matrix.fp,
                    }
                )
            results[smell][name] = points
            baseline = next(p for p in points if p["factor"] == 1.00)
            spread = [p["mcc"] for p in points if p["mcc"] is not None]
            print(
                f"{smell:<13}{name:<28} MCC te vlera e botuar "
                f"{baseline['mcc']:.3f}, brez {min(spread):.3f}-{max(spread):.3f}",
                flush=True,
            )

    severity: dict[str, dict[str, list[dict[str, object]]]] = {}
    for smell in SWEPT:
        severity[smell] = {}
        for name in SEVERITY_SWEPT:
            published = float(getattr(DEFAULT, name))
            points = []
            for factor in FACTORS:
                value = published * factor
                thresholds = replace(DEFAULT, **{name: value})
                agreement = severity_agreement(
                    replay(args.dataset, samples, thresholds),
                    smell,
                    PRIMARY_VARIANT,
                    Aggregation.MEAN,
                )
                points.append({"factor": factor, "value": round(value, 4), **agreement.to_dict()})
            severity[smell][name] = points
            spread = [p["kappa_quadratic"] for p in points if p["kappa_quadratic"] is not None]
            print(
                f"{smell:<13}{name:<28} kappa brez {min(spread):.3f}-{max(spread):.3f}",
                flush=True,
            )

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "per_smell": results,
        "severity": severity,
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
