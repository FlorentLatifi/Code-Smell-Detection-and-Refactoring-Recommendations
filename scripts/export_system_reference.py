"""Nxjerr konfigurimin e sistemit në formën që e lexon Shtojca e punimit.

    python scripts/export_system_reference.py

Shkruan ``data/results/system_reference.json``.

Shtojca liston pragjet, strategjitë, metrikat dhe arsyet e refuzimit. Të gjitha
këto jetojnë në kod dhe ndryshojnë me të, ndaj shtypja e tyre me dorë në tekst do
të prodhonte pikërisht atë ndarje të heshtur që VD-21 e gjeti mes dy numëruesve të
LOC-ut: dokumenti do të vazhdonte të thoshte një vlerë të vjetër dhe askush nuk do
ta vinte re. Prandaj shtojca ndërtohet si Kapitulli 5 — nga një skedar i gjeneruar.

Formulat e strategjive lexohen nga docstring-u i vetë detektorit, ku qëndrojnë
bashkë me faqen e burimit. Kjo do të thotë se shtojca s'ka asnjë transkriptim: ajo
që del në punim është ajo që kodi thotë për vetveten.

Ky nuk është eksperiment dhe nuk mat asgjë; është një fotografi e konfigurimit që
prodhoi rezultatet e tjera në të njëjtën dosje, prandaj shkruan edhe mjedisin.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from dataclasses import fields
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.detectors import thresholds as th  # noqa: E402
from javasmell.detectors.rules import (  # noqa: E402
    CLASS_DETECTORS,
    METHOD_DETECTORS,
    REFACTORINGS,
)
from javasmell.evaluation.dataset import CLASS_METRICS, METHOD_METRICS  # noqa: E402
from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.refactor.base import Refusal  # noqa: E402
from javasmell.refactor.registry import ADVISORY_ONLY, AUTOMATED  # noqa: E402

DEFAULT_OUT = Path("data/results")
RESULT_NAME = "system_reference.json"

# Fjalori i Lanza & Marinescu-t në të cilin janë shkruar strategjitë. Emrat janë
# ata të modulit; vlerat vijnë prej tij, ndaj tabela nuk mund të dalë e vjetruar.
QUANTIFIERS = (
    "FEW",
    "MANY",
    "SHORT_MEMORY_CAP",
    "ONE_THIRD",
    "HIGH_WMC",
    "VERY_HIGH_WMC",
    "HIGH_NOM",
    "HIGH_CLASS_LOC",
    "HIGH_METHOD_LOC",
)


def _smell_type(function_name: str) -> str:
    """``detect_god_class`` -> ``GodClass``, çelësi që përdor pjesa tjetër e sistemit.

    Emri nxirret e nuk mbahet në një hartë të dytë, sepse një hartë do të duhej të
    përditësohej me dorë. Përputhja me `REFACTORINGS` verifikohet më poshtë, ndaj
    një riemërtim e ndal eksportin në vend që ta lërë shtojcën të mbetet pas.
    """
    return "".join(part.title() for part in function_name.removeprefix("detect_").split("_"))


def _strategy(detector: object, scope: str) -> dict[str, object]:
    """Titulli, burimi dhe formula e një detektori, ashtu si i mban docstring-u."""
    doc = inspect.getdoc(detector) or ""
    lines = doc.splitlines()
    formula = [line.strip() for line in lines[1:] if line.startswith("    ") and line.strip()]
    smell = _smell_type(detector.__name__)  # type: ignore[attr-defined]
    engine = AUTOMATED.get(smell)
    return {
        "smell": smell,
        "scope": scope,
        "title": lines[0].rstrip("."),
        "formula": " ".join(formula),
        "refactorings": REFACTORINGS[smell],
        "automated": engine[0] if engine else None,
        "advisory_reason": ADVISORY_ONLY.get(smell),
    }


def collect() -> dict[str, object]:
    strategies = [_strategy(d, "class") for d in CLASS_DETECTORS]
    strategies += [_strategy(d, "method") for d in METHOD_DETECTORS]

    # Formula lexohet nga docstring-u me anë të indentimit, dhe indentimi është i
    # brishtë: formatuesi e hoqi një herë bllokun e një detektori dhe shtojca doli
    # me një qeli bosh, pa asnjë zë. Një formulë që humbet e ndal eksportin.
    empty = [str(entry["smell"]) for entry in strategies if not entry["formula"]]
    if empty:
        raise SystemExit(
            f"Detektorëve u mungon formula te docstring-u: {sorted(empty)}. "
            "Blloku duhet të jetë i indentuar më thellë se proza rreth tij."
        )

    covered = {str(entry["smell"]) for entry in strategies}
    missing = set(REFACTORINGS) - covered
    unexpected = covered - set(REFACTORINGS)
    if missing or unexpected:
        raise SystemExit(
            f"Detektorët dhe REFACTORINGS nuk përputhen: mungon {sorted(missing)}, "
            f"e panjohur {sorted(unexpected)}"
        )

    return {
        "quantifiers": {name: getattr(th, name) for name in QUANTIFIERS},
        "strategies": strategies,
        "thresholds": {f.name: getattr(th.DEFAULT, f.name) for f in fields(th.DEFAULT)},
        "metrics": {"class": list(CLASS_METRICS), "method": list(METHOD_METRICS)},
        "refusal_reasons": [reason.value for reason in Refusal],
        "environment": environment(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    payload = collect()
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / RESULT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    strategies = payload["strategies"]
    assert isinstance(strategies, list)
    print(f"{len(strategies)} strategji, {len(payload['thresholds'])} pragje.")  # type: ignore[arg-type]
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
