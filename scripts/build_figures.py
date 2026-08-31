"""Figurat e punimit, të gjeneruara nga rezultatet e komituara.

    python scripts/build_figures.py

Shkruan PNG-të te ``docs/thesis/figures/``.

Asnjë figurë nuk vizatohet me dorë dhe asnjë numër nuk shkruhet këtu. Çdo vlerë
lexohet nga ``data/results/``, ndaj nëse një rezultat rigjenerohet, figurat
ndjekin pa u prekur. Kjo është arsyeja pse figurat prodhohen nga një skript dhe
jo nga një mjet grafik: një numër i kopjuar me dorë vjetërohet në heshtje, dhe
komisioni nuk ka si ta dallojë.

Stili mbahet i thjeshtë me qëllim: shkallë gri me një ngjyrë theksuese, pa
rrjetë të rëndë dhe pa efekte. Punimi shtypet, dhe një figurë që mbështetet te
ngjyrat për të dalluar seritë humbet kuptimin në letër bardh e zi.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

RESULTS = Path("data/results")
FIGURES = Path("docs/thesis/figures")

# Ngjyra theksuese dhe grija shoqëruese. Të dallueshme edhe kur shtypen gri.
ACCENT = "#1f4e79"
MUTED = "#a6a6a6"
LIGHT = "#d9d9d9"

SMELL_LABELS = {
    "blob": "Blob",
    "data class": "Data Class",
    "long method": "Long Method",
    "feature envy": "Feature Envy",
}

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
    }
)


# Një skedar rezultati i lexuar nga JSON-i. `Any` këtu është i qëllimshëm dhe i
# kufizuar: forma e tij vendoset nga skripti që e shkroi, dhe përshkrimi i saj me
# TypedDict për tetë skedarë do të ishte më shumë tip sesa figura që vizatojnë.
Results = dict[str, Any]


def load(name: str) -> Results:
    path = RESULTS / name
    if not path.exists():
        print(f"mungon: {path}", file=sys.stderr)
        raise SystemExit(1)
    loaded: Results = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def save(fig: Figure, slug: str) -> None:
    """Emri i skedarit e përshkruan përmbajtjen, nuk e numëron.

    Numri i figurës varet nga radha ku ajo shfaqet në punim, dhe ajo radhë
    ndryshon sa herë riorganizohet një nënkapitull. I ngjitur te skedari, ai numër
    do të duhej rregulluar në tri vende njëherësh; i llogaritur gjatë ndërtimit të
    dokumentit, nuk mund të dalë i gabuar fare.
    """
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{slug}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def figure_rules_vs_ml(rules: Results, ml: Results) -> None:
    """MCC për të dyja qasjet, erë për erë."""
    smells = sorted(ml["per_smell"])
    approach_a = [
        rules["per_smell"][s]["strategy"]["by_aggregation"]["mean"]["mcc"] for s in smells
    ]
    approach_b = [
        ml["per_smell"][s]["models"][ml["per_smell"][s]["best_model"]]["mcc"] for s in smells
    ]

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    positions = range(len(smells))
    width = 0.38
    ax.bar(
        [p - width / 2 for p in positions],
        approach_a,
        width,
        label="Qasja A (rregulla)",
        color=MUTED,
    )
    ax.bar(
        [p + width / 2 for p in positions], approach_b, width, label="Qasja B (ML)", color=ACCENT
    )

    ax.set_xticks(list(positions))
    ax.set_xticklabels([SMELL_LABELS[s] for s in smells])
    ax.set_ylabel("MCC")
    ax.set_ylim(0, 0.8)
    ax.legend(frameon=False)
    for position, value in zip(positions, approach_a, strict=True):
        ax.text(position - width / 2, value + 0.015, f"{value:.3f}", ha="center", fontsize=8)
    for position, value in zip(positions, approach_b, strict=True):
        ax.text(position + width / 2, value + 0.015, f"{value:.3f}", ha="center", fontsize=8)
    save(fig, "mcc_a_vs_b")


def figure_recall_by_severity(rules: Results) -> None:
    """Recall-i sipas ashpërsisë që caktuan rishikuesit."""
    rows = []
    for smell in sorted(rules["per_smell"]):
        for variant, data in rules["per_smell"][smell].items():
            by_severity = data.get("recall_by_severity") or {}
            if "major" not in by_severity or "minor" not in by_severity:
                continue
            label = SMELL_LABELS[smell] + ("" if variant == "strategy" else " + madhësi")
            rows.append(
                (
                    label,
                    by_severity["minor"]["caught"] / by_severity["minor"]["support"],
                    by_severity["major"]["caught"] / by_severity["major"]["support"],
                )
            )

    rows.sort(key=lambda r: r[2])
    labels = [r[0] for r in rows]
    minor = [r[1] for r in rows]
    major = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    positions = range(len(rows))
    height = 0.38
    ax.barh([p - height / 2 for p in positions], minor, height, label="minor", color=LIGHT)
    ax.barh([p + height / 2 for p in positions], major, height, label="major", color=ACCENT)
    ax.set_yticks(list(positions))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Recall")
    ax.set_xlim(0, 1.0)
    ax.legend(frameon=False, loc="lower right")
    save(fig, "recall_sipas_ashpersise")


def figure_agreement(ml: Results) -> None:
    """Çka kap secila qasje vetëm, dhe çka të dyja."""
    smells = sorted(ml["per_smell"])
    both = [ml["per_smell"][s]["vs_rules"]["both"] for s in smells]
    only_a = [ml["per_smell"][s]["vs_rules"]["only_rules"] for s in smells]
    only_b = [ml["per_smell"][s]["vs_rules"]["only_model"] for s in smells]

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    positions = range(len(smells))
    ax.bar(positions, only_a, 0.6, label="vetëm A", color=LIGHT)
    ax.bar(positions, both, 0.6, bottom=only_a, label="të dyja", color=MUTED)
    ax.bar(
        positions,
        only_b,
        0.6,
        bottom=[a + b for a, b in zip(only_a, both, strict=True)],
        label="vetëm B",
        color=ACCENT,
    )
    ax.set_xticks(list(positions))
    ax.set_xticklabels([SMELL_LABELS[s] for s in smells])
    ax.set_ylabel("Mostra të shënuara")
    ax.legend(frameon=False)
    save(fig, "pajtimi_a_b")


def figure_feature_importance(ml: Results) -> None:
    """Veçoritë që modelet zgjodhën, për dy erëra."""
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.2))
    for ax, smell in zip(axes, ("long method", "feature envy"), strict=True):
        ranked = sorted(ml["per_smell"][smell]["importances"].items(), key=lambda p: p[1])[-6:]
        names = [n for n, _ in ranked]
        values = [v for _, v in ranked]
        ax.barh(range(len(names)), values, color=ACCENT)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9)
        ax.set_title(SMELL_LABELS[smell], fontsize=10)
        ax.set_xlabel("Rëndësia (permutation)")
    fig.tight_layout()
    save(fig, "rendesia_e_vecorive")


def figure_dataset_balance(dataset: Results) -> None:
    """Sa mostra për erë, dhe sa prej tyre pozitive."""
    smells = sorted(dataset["by_smell"])
    totals = [dataset["by_smell"][s] for s in smells]

    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    ax.bar(range(len(smells)), totals, 0.6, color=MUTED)
    ax.set_xticks(range(len(smells)))
    ax.set_xticklabels([SMELL_LABELS[s] for s in smells])
    ax.set_ylabel("Mostra")
    for position, value in enumerate(totals):
        ax.text(position, value + 20, str(value), ha="center", fontsize=9)
    save(fig, "shperndarja_e_mostrave")


def figure_threshold_sweep(sweep: Results) -> None:
    """Sa lëviz MCC-ja kur një prag zhvendoset rreth vlerës së botuar."""
    interesting = [
        ("long method", "long_method_loc", "Long Method: LOC"),
        ("feature envy", "feature_envy_fdp", "Feature Envy: FDP"),
        ("blob", "god_class_wmc", "Blob: WMC"),
        ("data class", "data_class_woc", "Data Class: WOC"),
    ]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    styles = ["-o", "-s", "--^", "--v"]
    for (smell, name, label), style in zip(interesting, styles, strict=True):
        points = sweep["per_smell"][smell][name]
        ax.plot(
            [p["factor"] for p in points],
            [p["mcc"] for p in points],
            style,
            label=label,
            color=ACCENT if style.startswith("-") and "-" not in style[1:] else MUTED,
            markersize=4,
        )
    ax.axvline(1.0, color=LIGHT, linewidth=1, zorder=0)
    ax.set_xlabel("Faktori i zbatuar mbi vlerën e botuar")
    ax.set_ylabel("MCC")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "ndjeshmeria_e_pragjeve")


def main() -> int:
    rules = load("rules_evaluation.json")
    ml = load("ml_evaluation.json")
    dataset = load("mlcq_dataset.json")
    sweep = load("threshold_sweep.json")

    print("Figurat:")
    figure_rules_vs_ml(rules, ml)
    figure_recall_by_severity(rules)
    figure_agreement(ml)
    figure_feature_importance(ml)
    figure_dataset_balance(dataset)
    figure_threshold_sweep(sweep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
