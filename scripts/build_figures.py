"""Figurat e punimit, të gjeneruara nga rezultatet e komituara.

    python scripts/build_figures.py

Shkruan PNG-të te ``docs/thesis/figures/``: arkitekturën e Kapitullit 4 dhe
figurat e rezultateve.

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
from matplotlib.patches import Rectangle

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


def figure_confidence_intervals(intervals: Results) -> None:
    """Brezi i besimit rreth çdo MCC-je, për të dyja qasjet.

    Shiritat e gabimit janë e vetmja mënyrë e ndershme për ta parë renditjen mes
    erërave: pikat e veçanta sugjerojnë një radhë që intervalet e mbivendosura e
    hedhin poshtë.
    """
    smells = sorted(intervals["per_smell"])
    positions = range(len(smells))
    offset = 0.16

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for label, key, colour, shift in (
        ("Qasja A (rregulla)", "rules", MUTED, -offset),
        ("Qasja B (ML)", None, ACCENT, offset),
    ):
        lows, highs, middles = [], [], []
        for smell in smells:
            entry = intervals["per_smell"][smell]
            band = entry["intervals"][key or entry["best_model"]]
            lows.append(band["median"] - band["low"])
            highs.append(band["high"] - band["median"])
            middles.append(band["median"])
        ax.errorbar(
            middles,
            [p + shift for p in positions],
            xerr=[lows, highs],
            fmt="o",
            color=colour,
            markersize=5,
            capsize=3,
            linewidth=1.4,
            label=label,
        )

    ax.set_yticks(list(positions))
    ax.set_yticklabels([SMELL_LABELS[s] for s in smells])
    ax.set_xlabel("MCC, me interval besimi 95% (bootstrap sipas depos)")
    ax.set_xlim(0, 0.85)
    ax.invert_yaxis()
    # Poshtë-majtas është e vetmja zonë bosh: djathtas shiritat e Long Method-it
    # e kalojnë legjendën.
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "intervalet_e_besimit")


def figure_severity_bias(rules: Results) -> None:
    """Ku bie ashpërsia jonë kundrejt asaj që caktuan rishikuesit.

    Tri kategori, jo një matricë e plotë: e njëjta, më e rëndë, më e lehtë. Gjetja
    nuk është se pajtimi mungon, por se gabimi ka drejtim.
    """
    scale = ("minor", "major", "critical")
    rank = {name: index for index, name in enumerate(scale)}
    smells = sorted(rules["per_smell"])

    exact, stricter, lenient = [], [], []
    for smell in smells:
        matrix = rules["per_smell"][smell]["strategy"]["severity_agreement"]["matrix"]
        counts = {"same": 0, "over": 0, "under": 0}
        for actual, predictions in matrix.items():
            for predicted, count in predictions.items():
                if rank[predicted] > rank[actual]:
                    counts["over"] += count
                elif rank[predicted] < rank[actual]:
                    counts["under"] += count
                else:
                    counts["same"] += count
        total = sum(counts.values()) or 1
        exact.append(100 * counts["same"] / total)
        stricter.append(100 * counts["over"] / total)
        lenient.append(100 * counts["under"] / total)

    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    positions = range(len(smells))
    bottom = [0.0] * len(smells)
    for values, label, colour in (
        (exact, "e njëjta ashpërsi", ACCENT),
        (stricter, "më e rëndë se rishikuesit", MUTED),
        (lenient, "më e lehtë se rishikuesit", LIGHT),
    ):
        ax.barh(list(positions), values, left=bottom, label=label, color=colour, height=0.6)
        bottom = [b + v for b, v in zip(bottom, values, strict=True)]

    ax.set_yticks(list(positions))
    ax.set_yticklabels([SMELL_LABELS[s] for s in smells])
    ax.set_xlabel("Përqindje e mostrave ku të dyja anët shohin një erë")
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    save(fig, "ashpersia_kundrejt_rishikuesve")


# Shtresat e sistemit, në radhën e varësisë (ENGINEERING.md §2), me qendrën e
# kutisë në figurë. Emri i një shtrese është emri i paketës së saj, dhe paketa
# verifikohet se ekziston, që figura të mos mbetet pas kodit po të riemërtohet.
# `None` shënon dy skajet që nuk janë paketa të backend-it: hyrjen dhe ndërfaqen.
ARCHITECTURE: tuple[tuple[str, str, float, float, str | None], ...] = (
    ("projekti Java", "skedarët .java\nnë diskun lokal", 0.85, 1.75, None),
    ("parsing", "analiza sintaksore\n(tree-sitter)", 0.85, 3.0, "parsing"),
    ("model", "klasat, metodat,\nfushat", 3.1, 3.0, "model"),
    ("metrics", "metrikat e klasës\ndhe të metodës", 5.2, 3.0, "metrics"),
    ("detectors", "rregullat mbi metrika\n(Qasja A)", 7.3, 3.0, "detectors"),
    ("ml", "klasifikuesit\n(Qasja B)", 5.2, 1.75, "ml"),
    ("refactor", "rishkrimet mbi pemën\n(Qasja C)", 7.3, 1.75, "refactor"),
    ("api", "shërbimi HTTP\n(FastAPI)", 3.1, 0.5, "api"),
    ("frontend", "ndërfaqja web\n(React, TypeScript)", 0.85, 0.5, None),
    ("evaluation", "vlerësimi mbi MLCQ\n(scripts/)", 7.3, 0.5, "evaluation"),
)
# Shigjeta shkon nga ai që jep te ai që përdor. Ndërfaqja dhe shërbimi flasin në
# të dy drejtimet, kërkesë e përgjigje.
ARCHITECTURE_EDGES = (
    ("projekti Java", "parsing", "-|>"),
    ("parsing", "model", "-|>"),
    ("model", "metrics", "-|>"),
    ("metrics", "detectors", "-|>"),
    ("detectors", "ml", "-|>"),
    ("detectors", "refactor", "-|>"),
    ("ml", "api", "-|>"),
    ("refactor", "api", "-|>"),
    ("api", "frontend", "<|-|>"),
)
BOX_WIDTH, BOX_HEIGHT = 1.75, 0.78
PACKAGE = Path("backend/javasmell")


def _edge(start: tuple[float, float], end: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    """Pikat ku shigjeta del nga një kuti dhe hyn te tjetra."""
    (x0, y0), (x1, y1) = start, end
    if y0 == y1:
        sign = 1 if x1 > x0 else -1
        return (x0 + sign * BOX_WIDTH / 2, y0), (x1 - sign * BOX_WIDTH / 2, y1)
    if x0 == x1:
        sign = 1 if y1 > y0 else -1
        return (x0, y0 + sign * BOX_HEIGHT / 2), (x1, y1 - sign * BOX_HEIGHT / 2)
    side = -1 if x1 < x0 else 1
    return (x0 + side * BOX_WIDTH / 2, y0 - BOX_HEIGHT / 2), (
        x1 - side * BOX_WIDTH / 2,
        y1 + BOX_HEIGHT / 2,
    )


def figure_architecture() -> None:
    """Shtresat e sistemit dhe rrjedha e të dhënave mes tyre.

    E vetmja figurë që nuk lexon `data/results/`: ajo përshkruan kodin, jo një
    matje, dhe nuk mban asnjë numër.
    """
    for _, _, _, _, package in ARCHITECTURE:
        if package is not None and not (PACKAGE / package).is_dir():
            print(f"mungon paketa: {PACKAGE / package}", file=sys.stderr)
            raise SystemExit(1)

    centres = {name: (x, y) for name, _, x, y, _ in ARCHITECTURE}
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.set_xlim(-0.15, 8.75)
    ax.set_ylim(-0.1, 3.6)
    ax.axis("off")

    for name, text, x, y, package in ARCHITECTURE:
        # Skajet vizatohen me gri; tri qasjet me sfond, sepse janë objekti i punimit.
        colour = ACCENT if package else MUTED
        face = "#eef3f8" if package in {"detectors", "ml", "refactor"} else "white"
        ax.add_patch(
            Rectangle(
                (x - BOX_WIDTH / 2, y - BOX_HEIGHT / 2), BOX_WIDTH, BOX_HEIGHT,
                facecolor=face, edgecolor=colour, linewidth=1.0,
            )
        )  # fmt: skip
        ax.text(
            x, y + 0.17, name, ha="center", va="center", fontsize=9, weight="bold", color=colour
        )
        ax.text(x, y - 0.12, text, ha="center", va="center", fontsize=7, linespacing=1.1)

    def arrow(start: tuple[float, float], end: tuple[float, float], style: str) -> None:
        ax.annotate(
            "", xy=end, xytext=start,
            arrowprops={"arrowstyle": style, "color": "#404040", "linewidth": 0.8,
                        "shrinkA": 0, "shrinkB": 0},
        )  # fmt: skip

    for source, target, style in ARCHITECTURE_EDGES:
        start, end = _edge(centres[source], centres[target])
        arrow(start, end, style)

    # Vlerësimi i lexon të tria qasjet. Vija e tij kalon anash, që të mos e
    # presë kutinë e refaktorimit, dhe është e ndërprerë sepse nuk është pjesë
    # e rrjedhës që sheh përdoruesi.
    x, top = centres["detectors"]
    _, bottom = centres["evaluation"]
    right = x + BOX_WIDTH / 2
    ax.plot(
        [right, right + 0.3, right + 0.3],
        [top, top, bottom],
        color="#404040",
        linewidth=0.8,
        linestyle="--",
    )
    arrow((right + 0.3, bottom), (right, bottom), "-|>")
    save(fig, "arkitektura_e_sistemit")


def main() -> int:
    rules = load("rules_evaluation.json")
    ml = load("ml_evaluation.json")
    dataset = load("mlcq_dataset.json")
    sweep = load("threshold_sweep.json")
    intervals = load("bootstrap_intervals.json")

    print("Figurat:")
    figure_architecture()
    figure_rules_vs_ml(rules, ml)
    figure_recall_by_severity(rules)
    figure_agreement(ml)
    figure_feature_importance(ml)
    figure_dataset_balance(dataset)
    figure_threshold_sweep(sweep)
    figure_confidence_intervals(intervals)
    figure_severity_bias(rules)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
