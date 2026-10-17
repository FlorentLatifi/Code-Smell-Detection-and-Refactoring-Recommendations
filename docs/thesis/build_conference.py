"""Prezantimi në anglisht për Konferencën Ndërkombëtare të UBT-së 2026, dhe fleta e pyetjeve.

    PYTHONPATH=backend python docs/thesis/build_conference.py

Shkruan te `docs/konferenca/`:
- `UBT2026_Florent_Latifi.pptx`: nëntë sllajde, me tekstin folës anglisht te shënimet
  (rreth shtatë minuta), dhe sllajde rezervë për pyetjet;
- `UBT2026_Florent_Latifi_9min.pptx`: të njëjtat sllajde, me një tekst folës më të gjatë
  (rreth nëntë minuta e gjysmë) për rastin kur kryesuesi jep vërtet dhjetë minuta;
- `UBT2026_pergatitja.docx`: koha për sllajd për të dy versionet, pyetjet e mundshme me
  përgjigje, shqiptimi i termave dhe lista për ditën e konferencës.

Dy versionet ndërtohen nga i njëjti tekst: i gjati është i shkurtri plus disa fjali
shtesë, që pjesa e provuar të mbetet e njëjtë dhe shtesat të mund të lihen jashtë në
sallë pa humbur fillin.

Si `build_slides.py`, çdo shifër lexohet nga `data/results/` me të njëjtët ngarkues si
punimi, që prezantimi, abstrakti i konferencës dhe punimi të mos thonë tre numra të
ndryshëm për të njëjtën gjë. Shembulli i kodit prodhohet nga motori përmes
`build_code_example.py`, ndaj kërkon korpusin; pa të, sllajdi e thotë.

Grafikët janë grafikë të PowerPoint-it e jo figurat e punimit: ato kanë etiketa shqip,
dhe një grafik vendas mund të ndryshohet në PowerPoint pa e rivizatuar.
"""

from __future__ import annotations

import os
import re
import sys

from build_slides import (
    ACCENT,
    BODY_SIZE,
    CRITICAL,
    FAINT,
    FIGURES,
    HEIGHT,
    INK,
    MARGIN,
    SANS,
    SERIF,
    SMALL_SIZE,
    SOFT,
    WIDTH,
    _blank,
    _bullets,
    _figures,
    _mean,
    _note,
    _table,
    _text,
    _title,
)
from chapters import (
    MADEYSKI_2023_DS1,
    REPOSITORY,
    SMELL_SQ,
    _load,
    _repositories_in_dataset,
    _significance,
)
from docx import Document
from docx.shared import Pt as DocPt
from docx.shared import RGBColor as DocRGB
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(__file__)
OUT_DIR = os.path.join(HERE, "..", "konferenca")
DECK = os.path.join(OUT_DIR, "UBT2026_Florent_Latifi.pptx")
DECK_LONG = os.path.join(OUT_DIR, "UBT2026_Florent_Latifi_9min.pptx")
SHEET = os.path.join(OUT_DIR, "UBT2026_pergatitja.docx")

TITLE = (
    "Automated Code Smell Detection and Refactoring Recommendations "
    "Using Software Metrics and Machine Learning"
)
AUTHORS = "Florent Latifi  ·  Altina Salihu"
AFFILIATION = "UBT – Higher Education Institution, Kosovo"
# Emri siç e shkruan agjenda e konferencës: email-i dhe faqja e saj përdorin shkurtesa
# të ndryshme, dhe agjenda është dokumenti që ka salla.
EVENT = "15th UBT Annual International Conference on Computer Science and Engineering  ·  2026"

# Gri për rregullat, blu për modelin: e njëjta ndarje si te figurat e punimit, që
# lexohet edhe kur projektori i zbeh ngjyrat.
MUTED = RGBColor(0xA6, 0xA6, 0xA6)
ADDED = RGBColor(0x2F, 0x6F, 0x45)
CODE_FILL = RGBColor(0xF4, 0xF5, 0xF7)
MONO = "Consolas"
CODE_SIZE = Pt(12)
# Rreshti i kodit me hapësirë të saktë, që lartësia e kutisë të llogaritet e jo të hamendësohet.
CODE_LINE = Pt(13.6)

MODEL_EN = {
    "majority": "Majority",
    "logistic": "Logistic regression",
    "random_forest": "Random forest",
    "gradient_boosting": "Gradient boosting",
}

# Ritmi i një folësi jo-amtar që flet qetë. Koha e çdo sllajdi llogaritet nga fjalët e
# shënimit, që fleta e kohës të ndjekë tekstin e jo një vlerësim me sy.
WORDS_PER_MINUTE = 115
# Autori flet shpejt, dhe nervozizmi në sallë e shpejton më tej. Ky është një supozim,
# jo një matje: fleta i thotë ta zëvendësojë me ritmin e vet, të matur me kronometër.
FAST_WORDS_PER_MINUTE = 145

# Emrat e refaktorimeve siç thuhen me gojë, jo siç janë në kod.
SPOKEN_REFACTORING = {"ReplaceNestedConditionalWithGuardClauses": "Guard Clauses"}


class Extra(str):
    """Një fjali që thuhet vetëm në versionin nëntë-minutësh.

    Shtesat janë pjesë e të njëjtit tekst e jo një tekst i dytë, që versioni i gjatë të
    mos i ndryshojë fjalitë e provuara: në sallë, kur koha mbaron, ato thjesht lihen.
    """


def _spoken(parts: list[str], long: bool) -> list[str]:
    return [part for part in parts if long or not isinstance(part, Extra)]


def _word_count(parts: list[str]) -> int:
    return len(" ".join(parts).split())


def _clock(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def _words(name: str) -> str:
    """`LongParameterList` → `Long Parameter List`, siç e thotë folësi."""
    return SPOKEN_REFACTORING.get(name, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name))


# ----------------------------------------------------------------------
# Të dhënat
# ----------------------------------------------------------------------
def _facts() -> dict:
    """Çdo shifër që thotë prezantimi, e lexuar një herë."""
    rules = _load("rules_evaluation.json")
    ml = _load("ml_evaluation.json")
    refactoring = _load("refactoring_evaluation.json")
    quality = _load("rewrite_quality.json")
    agreement = _load("reviewer_agreement.json")
    dataset = _load("mlcq_dataset.json")
    reference = _load("system_reference.json")
    smells = sorted(ml["per_smell"])
    unsure, _ = _significance(smells)
    best = {s: ml["per_smell"][s]["models"][ml["per_smell"][s]["best_model"]] for s in smells}
    strategy = {s: _mean(rules, s) for s in smells}
    return {
        "rules": rules,
        "ml": ml,
        "refactoring": refactoring,
        "quality": quality,
        "agreement": agreement,
        "smells": smells,
        "names": [SMELL_SQ[s] for s in smells],
        "strategy": strategy,
        "best": best,
        "sure": [SMELL_SQ[s] for s in smells if SMELL_SQ[s] not in unsure],
        "unsure": unsure,
        "samples": dataset["rows"],
        "repositories": _repositories_in_dataset(),
        "metrics": len(reference["metrics"]["class"]) + len(reference["metrics"]["method"]),
        "strategies": len(reference["strategies"]),
        "reviewers": {s: agreement["per_smell"][s]["mcc"] for s in smells},
    }


def _and(items: list[str]) -> str:
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


# ----------------------------------------------------------------------
# Elementet e sllajdeve që `build_slides.py` nuk i ka
# ----------------------------------------------------------------------
def _speech(slide, parts: list[str]) -> None:
    """Shënimi i folësit, me fjalitë shtesë të pjerrëta.

    Pamja e folësit në PowerPoint e ruan stilin, ndaj në sallë dallohet me një shikim cila
    fjali mund të lihet kur koha nuk mjafton.
    """
    paragraph = slide.notes_slide.notes_text_frame.paragraphs[0]
    for index, part in enumerate(parts):
        run = paragraph.add_run()
        run.text = part if index == 0 else " " + part
        run.font.italic = isinstance(part, Extra)


def _number(slide, index: int) -> None:
    """Numri i sllajdit poshtë djathtas, që pyetjet të mund t'i referohen."""
    frame = _text(slide, WIDTH - Inches(1.4), HEIGHT - Inches(0.55), Inches(1.0), Inches(0.4),
                  Pt(12), FAINT)  # fmt: skip
    frame.paragraphs[0].text = str(index)


def _bar_chart(slide, categories, series, top, height, minimum=0.0, maximum=1.0) -> None:
    """Shtylla të grupuara me vlerën mbi secilën, pa rrjetë dhe pa bosht të tepërt."""
    data = CategoryChartData()
    data.categories = categories
    for name, values, _ in series:
        data.add_series(name, values, number_format="0.00")
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, MARGIN, top, WIDTH - 2 * MARGIN, height, data
    )
    chart = frame.chart
    # Me një seri të vetme PowerPoint-i i vë grafikut emrin e serisë si titull.
    chart.has_title = False
    chart.font.name = SANS
    chart.font.size = Pt(16)
    chart.has_legend = len(series) > 1
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(16)
    axis = chart.value_axis
    axis.minimum_scale = minimum
    axis.maximum_scale = maximum
    axis.has_major_gridlines = False
    axis.visible = False
    chart.category_axis.tick_labels.font.size = Pt(18)
    chart.category_axis.has_major_gridlines = False
    # Emrat e erërave poshtë grafikut, jo te boshti zero, ku një shtyllë negative i mbulon.
    chart.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    plot = chart.plots[0]
    plot.gap_width = 60
    plot.overlap = -10
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.number_format = "0.00"
    labels.number_format_is_linked = False
    labels.font.size = Pt(16)
    for index, (_, _, colour) in enumerate(series):
        plot.series[index].invert_if_negative = False
        fill = plot.series[index].format.fill
        fill.solid()
        fill.fore_color.rgb = colour
    return chart


def _panel(slide, left, top, width, height):
    """Një kuti e mbushur, pa vijë dhe pa hije: hija e parazgjedhur e bën të duket buton."""
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = CODE_FILL
    box.line.fill.background()
    box.shadow.inherit = False
    box.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    return box


def _bullets_at(slide, lines, left, top, width, size):
    """`_bullets` i build_slides.py, por në një kolonë të caktuar e jo te margjina."""
    frame = _bullets(slide, lines, top=top, width=width, size=size)
    list(slide.shapes)[-1].left = left
    return frame


def _code_block(slide, label, lines, marked, colour, left, top, width) -> Emu:
    """Kod me shkronja me gjerësi të njëtrajtshme; rreshtat e ndryshuar të theksuar."""
    caption = _text(slide, left, top, width, Inches(0.35), SMALL_SIZE, SOFT, SANS, bold=True)
    caption.paragraphs[0].text = label
    top = top + Inches(0.38)
    height = Emu(int(CODE_LINE * len(lines) + Inches(0.2)))
    box = _panel(slide, left, top, width, height)
    frame = box.text_frame
    frame.vertical_anchor = MSO_ANCHOR.TOP
    frame.word_wrap = False
    frame.margin_left = frame.margin_right = Inches(0.12)
    frame.margin_top = frame.margin_bottom = Inches(0.08)
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.line_spacing = CODE_LINE
        paragraph.space_after = Pt(0)
        paragraph.alignment = PP_ALIGN.LEFT
        run = paragraph.add_run()
        run.text = line
        run.font.name = MONO
        run.font.size = CODE_SIZE
        changed = index in marked
        run.font.bold = changed
        run.font.color.rgb = colour if changed else INK
    return Emu(int(top + height))


def _elided(lines: list[str], marked: set[int]) -> tuple[list[str], set[int]]:
    """Trupi i bllokut synchronized zëvendësohet me një koment që thotë sa rreshta ka.

    Ai pjesë nuk ndryshon nga rishkrimi, dhe e plotë nuk hyn në një sllajd me shkronja
    që lexohen nga salla. Shkurtimi shënohet në vetë kodin, që askush të mos e lexojë
    si kodin e plotë.
    """
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("synchronized"))
    depth, end = 0, start
    for end in range(start, len(lines)):
        depth += lines[end].count("{") - lines[end].count("}")
        if depth == 0:
            break
    inner = lines[start + 1 : end]
    indent = len(inner[0]) - len(inner[0].lstrip())
    shown = lines[: start + 1] + [" " * indent + f"// … {len(inner)} unchanged lines"] + lines[end:]
    kept = {i if i <= start else i - len(inner) + 1 for i in marked if i <= start or i >= end}
    return shown, kept


def _example() -> tuple[list[str], set[int], list[str], set[int]] | None:
    """Rishkrimi i vërtetë i figurës së Nënkapitullit 4.7, ose None pa korpus."""
    import build_code_example as example

    if not example.SOURCE.exists():
        return None
    before, after = example._rewritten()
    removed, added = example._changed(before, after)
    before, removed = _elided(before, removed)
    after, added = _elided(after, added)
    return before, removed, after, added


# ----------------------------------------------------------------------
# Sllajdet
# ----------------------------------------------------------------------
def _notes_words(deck: Presentation) -> list[int]:
    return [len(slide.notes_slide.notes_text_frame.text.split()) for slide in deck.slides]


def build_deck(f: dict, long: bool) -> tuple[str, list[tuple[str, list[str]]]]:
    """Prezantimi; me `long` shënimet mbajnë edhe fjalitë `Extra`.

    Kthen tekstin e plotë të çdo sllajdi kryesor, me shtesat të shënuara, që fleta e
    përgatitjes të llogarisë kohën e të dy versioneve nga i njëjti burim.
    """
    deck = Presentation()
    deck.slide_width = WIDTH
    deck.slide_height = HEIGHT
    script: list[tuple[str, list[str]]] = []
    refactoring, quality, smells = f["refactoring"], f["quality"], f["smells"]
    recall = [f["strategy"][s]["recall"] for s in smells]
    model_mcc = [f["best"][s]["mcc"] for s in smells]
    rule_mcc = [f["strategy"][s]["mcc"] for s in smells]
    applied, detected = refactoring["applied"], refactoring["detected"]
    resolved = refactoring["resolution"]["resolved"] / applied
    broken = refactoring["verdicts"].get("new_errors", 0) / applied
    refused = sum(refactoring["refused_by_reason"].values()) / detected
    moderate = [s for s in smells if f["reviewers"][s] > 0.1]
    chance = [s for s in smells if f["reviewers"][s] <= 0.1]
    # Krahasimi me PMD-në: ndryshimi është yni minus i PMD-së, dhe vetëm një interval që
    # e përjashton zeron lejon të thuhet se njëri është përpara.
    pmd = _load("pmd_comparison.json")
    differences = {
        key: entry["difference"] for key, entry in pmd["by_smell"].items() if "difference" in entry
    }
    pmd_ahead = [SMELL_SQ[key.split("/")[0]] for key, d in differences.items()
                 if d["excludes_zero"] and d["median"] < 0]  # fmt: skip
    pmd_behind = [SMELL_SQ[key.split("/")[0]] for key, d in differences.items()
                  if key.endswith("/strategy") and d["excludes_zero"]
                  and d["median"] > 0]  # fmt: skip
    introduced = refactoring["introduced_smells"]
    by_refactoring = quality["by_refactoring"]
    always = [_words(name) for name, entry in by_refactoring.items() if entry["acceptable"] == 1.0]
    never = [_words(name) for name, entry in by_refactoring.items() if entry["acceptable"] == 0.0]

    def add(title: str, *parts: str):
        slide = _blank(deck)
        _speech(slide, _spoken(list(parts), long))
        _number(slide, len(deck.slides))
        script.append((title, list(parts)))
        return slide

    # --- 1. titulli ---
    slide = add(
        "Title",
        "Good morning, everyone. My name is Florent Latifi, and this work comes from my "
        "bachelor thesis at UBT, supervised by Altina Salihu. In the next ten minutes I "
        "will show how we can detect code smells in Java automatically, how accurate that "
        "detection really is, and how far we can go in fixing them.",
    )
    frame = _text(slide, MARGIN, Inches(2.0), WIDTH - 2 * MARGIN, Inches(2.0), Pt(36), INK, SERIF)
    frame.paragraphs[0].text = TITLE
    frame = _text(slide, MARGIN, Inches(4.4), WIDTH - 2 * MARGIN, Inches(1.6), BODY_SIZE, SOFT)
    frame.paragraphs[0].text = AUTHORS
    for line in (AFFILIATION, EVENT):
        paragraph = frame.add_paragraph()
        paragraph.text = line
        paragraph.font.size = SMALL_SIZE
        paragraph.font.color.rgb = FAINT
        paragraph.font.name = SANS

    # --- 2. problemi ---
    slide = add(
        "The problem",
        "Every developer knows the class that nobody wants to touch. The program works, "
        "but every change takes longer than it should. These design problems are called "
        "code smells. They are not bugs, but they make maintenance expensive. Most tools "
        "find them with fixed thresholds. For example, if a method is longer than a "
        "certain number of lines, it is a Long Method. But these numbers were calibrated "
        "on other code, and most tools only point at the problem. They do not fix it. So "
        "we asked three questions. First, how accurate are the published detection rules? "
        "Second, can machine learning do better with the same metrics? And third, can we "
        "fix smells automatically without breaking the code?",
    )
    _title(slide, "The class nobody wants to touch", "Code smells are design problems, not bugs")
    _bullets(
        slide,
        [
            "The program works, but every change costs more than it should.",
            "Existing tools use fixed thresholds, calibrated on other code.",
            "They point at the problem, but rarely fix it.",
        ],
        top=Inches(1.8),
    )
    frame = _text(slide, MARGIN, Inches(4.25), WIDTH - 2 * MARGIN, Inches(2.4), BODY_SIZE, ACCENT)
    questions = [
        "RQ1  How accurate are published detection rules?",
        "RQ2  Does machine learning on the same metrics do better?",
        "RQ3  Can fixes be applied automatically without breaking compilation?",
    ]
    for index, line in enumerate(questions):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.size = BODY_SIZE
        paragraph.font.color.rgb = ACCENT
        paragraph.font.name = SANS
        paragraph.space_after = Pt(8)

    # --- 3. sistemi ---
    slide = add(
        "What we built",
        f"To answer them, I built a tool called JavaSmell. It reads Java code and measures "
        f"{f['metrics']} metrics for every class and method. On top of these metrics there "
        f"are three approaches. A uses {f['strategies']} detection strategies from the "
        "literature, such as Lanza and Marinescu and Fowler. B trains machine learning "
        "classifiers on the same metrics. And C is a refactoring engine. It rewrites code "
        "only when it can prove its preconditions from the syntax tree, and then it checks "
        "the result with the Java compiler.",
        Extra(
            "Every detection also shows the conditions it checked, so a developer can see why "
            "a class was flagged, not only that it was."
        ),
        "On the right you can see the web interface. It also has a plain-language mode for "
        "people without a technical background.",
    )
    _title(slide, "What we built: JavaSmell", "One Java analyzer, three approaches")
    left_width = Inches(5.3)
    parts = [
        ("A  Rules", f"{f['strategies']} published detection strategies over {f['metrics']} metrics"),
        ("B  Machine learning", "classifiers trained on the same metrics"),
        ("C  Refactoring engine", "AST rewrites only when preconditions are proven, then javac"),
    ]
    top = Inches(1.9)
    for name, detail in parts:
        box = _panel(slide, MARGIN, top, left_width, Inches(1.35))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = Inches(0.2)
        paragraph = frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.LEFT
        paragraph.text = name
        paragraph.font.size = Pt(21)
        paragraph.font.bold = True
        paragraph.font.color.rgb = ACCENT
        paragraph.font.name = SANS
        line = frame.add_paragraph()
        line.alignment = PP_ALIGN.LEFT
        line.text = detail
        line.font.size = Pt(16)
        line.font.color.rgb = INK
        line.font.name = SANS
        top = Emu(int(top + Inches(1.55)))
    path = os.path.join(FIGURES, "nderfaqja_paneli.png")
    picture = slide.shapes.add_picture(path, MARGIN + left_width + Inches(0.35), Inches(2.1),
                                       width=Inches(6.0))  # fmt: skip
    caption = _text(slide, picture.left, Emu(int(picture.top + picture.height + Inches(0.08))),
                    Inches(6.0), Inches(0.4), Pt(13), FAINT)  # fmt: skip
    caption.paragraphs[0].text = "Web interface on the jsoup library (plain-language mode, Albanian)"

    # --- 4. të dhënat ---
    slide = add(
        "Data and evaluation",
        "For a fair test, we need labels from people. We used MLCQ, a public dataset where "
        "professional developers reviewed real open-source Java code. After matching the "
        f"samples to our tool, we have {f['samples']:,} labeled samples from "
        f"{f['repositories']} repositories, for four smells.",
        Extra(
            "Blob is a class that does too much. Data Class only holds data and has almost "
            "no behavior. Long Method is a method that has grown too long, and Feature Envy "
            "is a method that uses another class more than its own."
        ),
        "One important detail is how we split the data. Code from the same project looks "
        "very similar, so we grouped the data by repository: a model is never tested on a project it learned from. And "
        "we report the Matthews correlation coefficient, MCC. Most samples are clean, so "
        "simple accuracy would look very good even for a detector that never fires.",
    )
    _title(slide, "Data and a fair test", "MLCQ: real Java code labeled by professional developers")
    _figures(
        slide,
        [
            (f"{f['samples']:,}", "labeled samples"),
            (f"{f['repositories']}", "repositories"),
            (f"{len(smells)}", "code smells"),
            (f"{f['metrics']}", "metrics"),
        ],
        top=Inches(1.9),
    )
    _bullets(
        slide,
        [
            "Labels from MLCQ (Madeyski & Lewowski, 2020): open-source Java reviewed by "
            "26 professional developers.",
            "Grouped by repository: a model is never tested on a project it learned from.",
            "Main score: Matthews correlation coefficient (MCC), because most samples are clean.",
        ],
        top=Inches(4.0),
    )

    # --- 5. rregullat kundrejt modelit ---
    slide = add(
        "Rules vs. machine learning",
        "Here are the main results. The gray bars are the published rules, and the blue "
        "bars are the best machine learning model for each smell. The rules are often "
        f"correct when they fire, but they catch only {min(recall) * 100:.0f} to "
        f"{max(recall) * 100:.0f} percent of the smells that developers marked. The models "
        f"are better on all four smells, with MCC from {min(model_mcc):.2f} to "
        f"{max(model_mcc):.2f}. We also computed 95 percent confidence intervals by "
        "resampling repositories. The improvement is clearly above zero for "
        f"{_and(f['sure'])}. For {_and(f['unsure'])}, the difference could be chance.",
        Extra(
            "We also compared with PMD, a popular open-source analyzer, on the same samples. "
            "Once the confidence interval is considered, "
            + ("PMD is never ahead" if not pmd_ahead else f"PMD is ahead for {_and(pmd_ahead)}")
            + f", and for {_and(pmd_behind)} our rules are clearly better."
        ),
    )
    _title(slide, "Rules vs. machine learning", "MCC on the same samples, with the same scoring code")
    _bar_chart(
        slide,
        f["names"],
        [("Published rules (A)", rule_mcc, MUTED), ("Best ML model (B)", model_mcc, ACCENT)],
        top=Inches(1.7),
        height=Inches(4.2),
    )
    _bullets(
        slide,
        [
            f"Rules: precise when they fire, but catch only {min(recall) * 100:.0f}–"
            f"{max(recall) * 100:.0f}% of the cases.",
            f"Models: better on all four smells; significant on {_and(f['sure'])} "
            "(95% bootstrap CI by repository).",
        ],
        top=Inches(6.0),
        size=Pt(17),
    )

    # --- 6. pajtimi i njerëzve ---
    slide = add(
        "Human agreement",
        "Why is Feature Envy so hard? We measured how much the human reviewers agree with "
        f"each other. For {_and([SMELL_SQ[s] for s in moderate])}, two reviewers agree only "
        f"moderately. For {_and([SMELL_SQ[s] for s in chance])}, they agree no better than "
        "chance.",
        Extra(
            " ".join(
                f"For {SMELL_SQ[s]}, their MCC is {f['reviewers'][s]:.2f}, practically zero."
                for s in chance
            )
            + f" This matches the previous slide: {_and(f['unsure'])} is where the model "
            "could not clearly beat the rules."
        ),
        "So the problem is not only the algorithm. It is the definition of the "
        "smell itself. If experts do not agree on what a smell is, no detector can learn it "
        "well. For me, this is the main lesson of the detection part.",
    )
    _title(slide, "Why some smells stay hard", "Agreement between two human reviewers of the same code (MCC)")
    chart = _bar_chart(
        slide,
        f["names"],
        [("Two reviewers", [f["reviewers"][s] for s in smells], ACCENT)],
        top=Inches(1.8),
        height=Inches(3.9),
        minimum=-0.2,
        maximum=1.0,
    )
    # Erët ku pajtimi është në nivelin e rastësisë dalin me ngjyrë tjetër: për to flet sllajdi.
    for index, smell in enumerate(smells):
        if smell in chance:
            point = chart.plots[0].series[0].points[index]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = CRITICAL
            # Një pikë me format të vetin nuk e trashëgon `invertIfNegative` të serisë, dhe
            # PowerPoint-i e vizaton shtyllën negative bosh nëse pika nuk e thotë vetë.
            dpt = point.format._element
            flag = dpt.makeelement(qn("c:invertIfNegative"), {"val": "0"})
            dpt.find(qn("c:idx")).addnext(flag)
    _bullets(
        slide,
        ["The limit is not only the algorithm, but the definition of the smell itself."],
        top=Inches(6.0),
        size=Pt(19),
    )

    # --- 7. refaktorimi ---
    slide = add(
        "Automatic refactoring",
        "Now the refactoring engine. It supports three transformations: Extract Method, "
        "Replace Nested Conditional with Guard Clauses, and Introduce Parameter Object. On "
        f"the whole corpus it found {detected:,} sites and rewrote {applied:,} of them, "
        f"which is {applied / detected * 100:.0f} percent. The rest were refused, each with "
        "a reason.",
        Extra(
            f"In {refactoring['refused_by_reason']['shape_not_matched'] / detected * 100:.0f} "
            "percent of the sites, the reason is simply that the code does not have the shape "
            "the transformation needs."
        ),
        "For us, refusing is a correct result, not a failure. After rewriting, "
        f"the smell disappeared in {resolved * 100:.0f} percent of the cases. Only "
        f"{broken * 100:.1f} percent of the rewrites introduced a new type of compilation "
        "error, and those never reach the code, because the tool only writes verified "
        f"rewrites. I also read {quality['reviewed']} rewrites by hand: after reweighting, "
        f"about {quality['acceptable_reweighted'] * 100:.0f} percent would be acceptable "
        "to a developer.",
        Extra(
            f"Refactoring can also create new smells: {sum(introduced.values()):,} appeared "
            f"after rewriting, most often {_words(max(introduced, key=introduced.get))}, "
            "because Extract Method passes every input as a parameter."
        ),
        Extra(
            f"In that review, {_and(always)} were always acceptable, and {_and(never)} never, "
            "because it only moves the long list into a new class."
        ),
    )
    _title(slide, "Automatic refactoring", "Rewrite only when the preconditions are proven")
    _figures(
        slide,
        [
            (f"{detected:,}", "sites with a transformation"),
            (f"{applied:,}", f"rewritten ({_pct(applied / detected)})"),
            (_pct(resolved), "smell removed"),
            (_pct(broken), "new compile-error types"),
        ],
        top=Inches(1.9),
    )
    _bullets(
        slide,
        [
            "Three transformations: Extract Method, Guard Clauses, Introduce Parameter Object.",
            f"Refusing is a correct outcome: {_pct(refused)} of the sites were refused, "
            "each with a reason.",
            f"Manual review of {quality['reviewed']} rewrites: "
            f"{_pct(quality['acceptable_reweighted'])} acceptable to a developer (reweighted).",
        ],
        top=Inches(4.0),
    )

    # --- 8. shembulli ---
    slide = add(
        "Example",
        "Here is one real example from Apache Geode. Before, the whole method is wrapped in "
        "one if statement, so everything is nested deeply. After the rewrite, the condition "
        "becomes a guard clause with an early return, and the rest of the method moves one "
        "level up.",
        Extra(
            "The engine accepts only exactly this shape: a void method whose whole body is one "
            "if statement, without else. It also wraps the condition in a not, instead of "
            "inverting it by hand, so it stays correct for every condition."
        ),
        "The rewrite passed the compiler check, and in my review it was acceptable as it is.",
    )
    _title(slide, "Example from real code",
           "Apache Geode · DistributedRegion.checkForLimitedOrNoAccess · Guard Clauses")  # fmt: skip
    code = _example()
    if code is None:
        _text(slide, MARGIN, Inches(2.0), WIDTH - 2 * MARGIN, Inches(0.6), BODY_SIZE,
              CRITICAL).paragraphs[0].text = "[Corpus missing: run build_code_example.py]"  # fmt: skip
    else:
        before, removed, after, added = code
        code_width = Inches(7.6)
        bottom = _code_block(slide, "Before", before, removed, CRITICAL, MARGIN, Inches(1.55),
                             code_width)  # fmt: skip
        _code_block(slide, "After", after, added, ADDED, MARGIN, Emu(int(bottom + Inches(0.12))),
                    code_width)  # fmt: skip
        _bullets_at(
            slide,
            [
                "The outer condition becomes a guard clause with an early return.",
                "The rest of the method moves one level up.",
                "Passed the javac check; judged acceptable as-is in the manual review.",
            ],
            left=Emu(int(MARGIN + code_width + Inches(0.35))),
            top=Inches(2.0),
            width=Inches(3.6),
            size=Pt(17),
        )

    # --- 9. kufizimet dhe mesazhi ---
    slide = add(
        "Limitations and takeaways",
        "To be honest about the limits: compiling is not the same as behaving the same. We "
        "did not run the projects' test suites, so behavior preservation is future work. We "
        "also used one dataset, four smells, and only Java.",
        Extra(
            "And the best model was chosen on the same predictions it is scored on, so its "
            "numbers are slightly optimistic."
        ),
        Extra(
            "As next steps, I would add a small symbol resolver to support more refactorings, "
            "and ask independent reviewers to judge the rewrites."
        ),
        "To summarize: learned boundaries beat fixed thresholds. Safe automatic refactoring is possible, but "
        "narrow, and it should be reviewed by a developer. The tool is open source, and "
        "every number in this talk can be regenerated with a script. Thank you. I am happy "
        "to take your questions.",
    )
    _title(slide, "Limitations and takeaways")
    column = Emu(int((WIDTH - 2 * MARGIN - Inches(0.4)) / 2))
    for index, (heading, lines, colour) in enumerate(
        [
            ("Limitations", [
                "Compiles ≠ behaves the same: project tests were not run.",
                "One dataset, four smells, Java only.",
                "Best model chosen on the same predictions: slightly optimistic.",
            ], CRITICAL),
            ("Takeaways", [
                "Learned boundaries beat fixed thresholds.",
                "Safe automation is narrow, but measurable.",
                "Open source and reproducible: every number comes from a script.",
            ], ACCENT),
        ]
    ):  # fmt: skip
        left = Emu(int(MARGIN + index * (column + Inches(0.4))))
        frame = _text(slide, left, Inches(1.6), column, Inches(0.5), Pt(22), colour, SANS, bold=True)
        frame.paragraphs[0].text = heading
        _bullets_at(slide, lines, left=left, top=Inches(2.2), width=column, size=Pt(18))
    frame = _text(slide, MARGIN, Inches(5.45), WIDTH - 2 * MARGIN, Inches(1.2), Pt(30), INK, SERIF)
    frame.paragraphs[0].text = "Thank you!  Questions?"
    link = frame.add_paragraph()
    link.text = REPOSITORY.replace("https://", "")
    link.font.size = Pt(14)
    link.font.color.rgb = FAINT
    link.font.name = SANS

    main = len(deck.slides)

    # ------------------------------------------------------------------
    # Rezervë: vetëm për pyetjet, nuk thuhen në dhjetë minutat
    # ------------------------------------------------------------------
    def backup(title: str, subtitle: str, notes: str):
        slide = _blank(deck)
        _title(slide, f"Backup · {title}", subtitle)
        _note(slide, notes)
        _number(slide, len(deck.slides))
        return slide

    ml, rules = f["ml"], f["rules"]
    slide = backup("Full detection results", "Precision, recall and MCC for both approaches",
                   "Use when asked for precision or recall per smell.")  # fmt: skip
    _table(
        slide,
        ["Smell", "Rules P", "Rules R", "Rules MCC", "Model", "Model P", "Model R", "Model MCC"],
        [
            [
                SMELL_SQ[s],
                f"{f['strategy'][s]['precision']:.3f}",
                f"{f['strategy'][s]['recall']:.3f}",
                f"{f['strategy'][s]['mcc']:.3f}",
                MODEL_EN[ml["per_smell"][s]["best_model"]],
                f"{f['best'][s]['precision']:.3f}",
                f"{f['best'][s]['recall']:.3f}",
                f"{f['best'][s]['mcc']:.3f}",
            ]
            for s in smells
        ],
        top=Inches(2.0),
    )

    intervals = _load("bootstrap_intervals.json")["per_smell"]
    slide = backup("Confidence intervals", "95% bootstrap intervals, resampling whole repositories",
                   "Above zero means the model's advantage is not explained by which projects "
                   "happen to be in the sample.")  # fmt: skip
    _table(
        slide,
        ["Smell", "Rules (A)", "Model (B)", "B − A", "Above zero"],
        [
            [
                SMELL_SQ[s],
                "[{low:.3f}, {high:.3f}]".format(**intervals[s]["intervals"]["rules"]),
                "[{low:.3f}, {high:.3f}]".format(**intervals[s]["intervals"][intervals[s]["best_model"]]),
                "[{low:.3f}, {high:.3f}]".format(**intervals[s]["intervals"]["difference_model_minus_rules"]),
                "yes" if intervals[s]["intervals"]["difference_model_minus_rules"]["low"] > 0 else "no",
            ]
            for s in smells
        ],
        top=Inches(2.0),
    )  # fmt: skip

    slide = backup("Every algorithm", "MCC of each classifier, same folds",
                   "If asked whether choosing the best model inflates the result: yes, slightly. "
                   "Even the weakest learning algorithm beats the rules on three of four smells.")  # fmt: skip
    _table(
        slide,
        ["Smell", *[MODEL_EN[m] for m in ("logistic", "random_forest", "gradient_boosting")], "Rules (A)"],
        [
            [SMELL_SQ[s]]
            + [f"{ml['per_smell'][s]['models'][m]['mcc']:.3f}"
               for m in ("logistic", "random_forest", "gradient_boosting")]
            + [f"{f['strategy'][s]['mcc']:.3f}"]
            for s in smells
        ],
        top=Inches(2.0),
    )  # fmt: skip

    names = {"blob/strategy": "Blob (strategy)", "blob/with_size": "Blob (with size)",
             "data class/strategy": "Data Class", "long method/strategy": "Long Method",
             "feature envy/law_of_demeter": "Feature Envy (LawOfDemeter)"}  # fmt: skip
    slide = backup("Comparison with PMD", f"PMD {pmd['pmd_version']} with its default thresholds, same samples",
                   "PMD is never ahead once the confidence interval is considered. PMD has no "
                   "Feature Envy rule.")  # fmt: skip
    _table(
        slide,
        ["Smell", "PMD MCC", "Our MCC", "Difference, 95% CI"],
        [
            [
                names.get(key, key),
                f"{entry['pmd']['mcc']:.3f}",
                "—" if entry.get("ours") is None else f"{entry['ours']['mcc']:.3f}",
                "—" if entry.get("difference") is None
                else f"{entry['difference']['low']:+.3f} to {entry['difference']['high']:+.3f}",
            ]
            for key, entry in pmd["by_smell"].items()
        ],
        top=Inches(2.0),
    )  # fmt: skip

    verify = _load("verify_with_project.json")
    reasons = sorted(refactoring["refused_by_reason"].items(), key=lambda pair: -pair[1])[:3]
    reason_en = {"shape_not_matched": "Code shape does not match the transformation",
                 "control_flow_escapes": "A return, break or continue leaves the block",
                 "not_definitely_assigned": "An input value is not definitely assigned"}  # fmt: skip
    slide = backup("Verification in detail", "Why sites were refused, and what compiling inside the project shows",
                   "Isolated files often cannot compile because their neighbours are missing; "
                   "inside the project many more compile fully.")  # fmt: skip
    _bullets(
        slide,
        [f"{reason_en.get(name, name)}: {count:,} sites ({_pct(count / detected)})"
         for name, count in reasons]
        + [
            f"Same {verify['rewrites']} rewrites compiled inside their project: "
            f"{verify['compiled_alone'].get('compiles', 0)} → "
            f"{verify['compiled_in_project'].get('compiles', 0)} compile fully, "
            f"{verify['compiled_in_project'].get('new_errors', 0)} add a new error.",
            f"After rewriting, {sum(refactoring['introduced_smells'].values()):,} new smells "
            "appeared, mostly Long Parameter List from Extract Method.",
        ],
        top=Inches(1.9),
        size=Pt(18),
    )  # fmt: skip

    slide = backup("Extract Method in the interface", "jsoup · NodeTraversor.traverse, preview before any file is touched",
                   "The extracted method is named 'extracted'; choosing a meaningful name is "
                   "left to the developer.")  # fmt: skip
    path = os.path.join(FIGURES, "nderfaqja_rishkrimi.png")
    slide.shapes.add_picture(path, MARGIN, Inches(2.0), width=WIDTH - 2 * MARGIN)

    slide = backup("Comparison with the literature", "Madeyski & Lewowski (2023), same MLCQ dataset, DS1",
                   "They used random 5-fold cross-validation and tuned hyperparameters; we "
                   "grouped by repository and did not tune. Our results are in the same range.")  # fmt: skip
    _table(
        slide,
        ["Smell", "Rules (A)", "Model (B)", "Madeyski & Lewowski 2023"],
        [[SMELL_SQ[s], f"{f['strategy'][s]['mcc']:.3f}", f"{f['best'][s]['mcc']:.3f}",
          MADEYSKI_2023_DS1[s]] for s in smells],
        top=Inches(2.0),
    )  # fmt: skip

    os.makedirs(OUT_DIR, exist_ok=True)
    path = DECK_LONG if long else DECK
    deck.save(path)
    return path, script[:main]


# ----------------------------------------------------------------------
# Fleta e përgatitjes
# ----------------------------------------------------------------------
def _questions(f: dict) -> list[tuple[str, str]]:
    refactoring, quality = f["refactoring"], f["quality"]
    applied, detected = refactoring["applied"], refactoring["detected"]
    reasons = refactoring["refused_by_reason"]
    weakest = sum(
        min(e["mcc"] for e in f["ml"]["per_smell"][s]["models"].values() if e["mcc"] is not None)
        > f["strategy"][s]["mcc"]
        for s in f["smells"]
    )
    envy = f["reviewers"].get("feature envy")
    return [
        ("Why MCC and not accuracy or F1?",
         "Most samples are clean, so a detector that never fires already has high accuracy. "
         "MCC uses all four cells of the confusion matrix and is zero for a detector that "
         "learns nothing. We also report precision, recall and F1 for completeness."),
        ("How did you avoid data leakage?",
         "We split by repository with grouped cross-validation, five folds. Code from one "
         "project never appears in both training and testing, because similar code from the "
         "same project would inflate the results."),
        ("Why is Feature Envy so poor?",
         f"Even two human reviewers do not agree on it: their MCC is {envy:.2f}, which is "
         "chance level. A label that humans do not agree on cannot be learned well."),
        ("Which model was best, and why not deep learning?",
         "Logistic regression for Blob, gradient boosting for Data Class and Feature Envy, "
         "random forest for Long Method. The data is tabular and small, the models must be "
         "explainable, and everything had to run on a laptop at zero cost."),
        ("Isn't choosing the best model optimistic?",
         "Yes, slightly, because the choice is made on the same predictions. That is why we "
         f"report every algorithm: even the weakest one beats the rules on {weakest} of "
         f"{len(f['smells'])} smells, so the conclusion does not depend on the choice."),
        ("How do you know the refactoring does not change behavior?",
         "We do not claim that. We prove preconditions on the syntax tree and check with the "
         "compiler. Running the projects' tests was not possible, because the corpus has no "
         "build files. It is the main future work."),
        (f"Why only {applied / detected:.0%} of the sites?",
         "The engine refuses when it cannot prove a precondition. The main reasons are that "
         f"the code shape does not match ({reasons['shape_not_matched'] / detected:.0%}) or "
         f"that a return or break leaves the block ({reasons['control_flow_escapes'] / detected:.0%}). "
         "A refusal is a correct result, not a failure."),
        ("What happens to the rewrites with new errors?",
         "They are counted in the evaluation, but the tool never writes them: only rewrites "
         "that pass verification go into the patch."),
        ("Why not use a large language model to refactor?",
         "We wanted deterministic, verifiable and free rewrites. A language model can produce "
         "plausible code, but it cannot prove the preconditions, and the results would not be "
         "reproducible."),
        ("How does it compare to existing tools?",
         "We compared with PMD on the same samples. PMD was never ahead once the confidence "
         "interval is considered, and ours was clearly better for Long Method. We did not "
         "compare with commercial tools such as SonarQube."),
        ("Where do the thresholds come from?",
         "Mostly from Lanza and Marinescu. Four values have no published source, for example "
         "30 lines for Long Method, and we measured how sensitive the results are to them."),
        ("Does it work for other languages?",
         "Not yet. The parser, tree-sitter, supports many languages, but the metrics and the "
         "refactoring engine are written for Java."),
        ("Is the tool available?",
         "Yes, it is open source on GitHub under the MIT license, with a Docker image."),
        ("What is MLCQ?",
         "A public dataset by Madeyski and Lewowski, 2020: about fifteen thousand reviews of "
         "Java code by twenty-six professional developers, for four smells."),
        ("Did refactoring create new smells?",
         f"Yes: {sum(refactoring['introduced_smells'].values()):,} new smells appeared, mostly "
         "Long Parameter List, because Extract Method passes every input as a parameter. We "
         "report them together with the removed smells."),
        ("How good are the rewrites for a developer?",
         f"I reviewed {quality['reviewed']} by hand. After reweighting, "
         f"{quality['acceptable_reweighted']:.0%} are acceptable. Guard Clauses were always "
         "acceptable; Introduce Parameter Object never, because it only moves the long list."),
        ("What would you do next?",
         "Run the projects' own tests after each rewrite, add a small symbol resolver to "
         "support more refactorings, and let independent reviewers judge the rewrites."),
    ]


PHRASES = [
    ("Thank you, that is a good question.", "Fillim i sigurt për çdo pyetje; të jep dy sekonda kohë."),
    ("If I understand correctly, you are asking about …", "Kur pyetja është e gjatë ose e paqartë."),
    ("Could you repeat the question, please?", "Kur nuk e dëgjove ose nuk e kuptove."),
    ("We did not measure that directly, but …", "Kur pyetja del jashtë asaj që mate."),
    ("That is a limitation of this study, and it is part of our future work.",
     "Kur të kapin te një kufizim: pranoje, mos u mbro."),
    ("Let me show you the backup slide.", "Kur ke sllajd rezervë për atë pyetje."),
]

PRONUNCIATION = [
    ("code smell", "kod smel"),
    ("refactoring", "ri-FÉK-tëring"),
    ("precondition", "pri-kën-DÍ-shën"),
    ("Matthews correlation coefficient", "MÉ-thjuz ko-rë-LÉJ-shën ko-i-FÍ-shënt"),
    ("repository", "ri-PÓ-zi-to-ri"),
    ("threshold", "THRÉSH-hold (th si te «thikë»)"),
    ("Feature Envy", "FÍ-çër ÉN-vi"),
    ("compiler / compilation", "kom-PÁJ-lër / kom-pi-LÉJ-shën"),
    ("behavior", "bi-HÉJ-vjër"),
    ("precision / recall", "pri-SÍ-zhën / ri-KÓLL"),
    ("confidence interval", "KÓN-fi-dëns ÍN-tër-vël"),
    ("bootstrap", "BÚT-strep"),
    ("syntax tree", "SÍN-teks tri"),
    ("Guard Clauses", "gard KLLÓ-zëz"),
    ("Apache Geode", "ë-PÉ-çi XHÍ-oud"),
]

CONFIDENCE = [
    "Mëso përmendësh vetëm dy fjalitë e para dhe dy të fundit. Fillimi i sigurt e qetëson "
    "zërin, dhe fundi i sigurt lë përshtypjen e fundit; mesin e mban sllajdi.",
    "Provoje me zë të lartë, me kronometër, të paktën pesë herë, dhe të dy versionet. Nëse "
    "i gjati, me pauzat, të del mbi 9½ minuta, hiqi disa fjali të gjelbra që në provë: në "
    "sallë flitet më shpejt nga nervozizmi, por kryesuesi mund të ta ndërpresë te minuta "
    "e dhjetë.",
    "Regjistrohu një herë me telefon dhe dëgjoje. Do të vëresh vetë ku nxiton dhe ku "
    "ngec; një provë para një shoku a familjari vlen sa tri vetëm.",
    "Mos e lexo sllajdin. Shiko titullin, thuaj mesazhin me fjalët e tua, pastaj trego "
    "shifrën. Shënimet folëse janë rrjetë sigurie, jo tekst për t'u lexuar.",
    "Ndalu pas çdo shifre të rëndësishme. Një pauzë prej një sekonde tingëllon si "
    "vetëbesim, jo si harresë.",
    "Para se të dalësh: frymë brenda katër sekonda, jashtë gjashtë, tri herë. Qëndro "
    "drejt, me këmbët të palëvizura, dhe shiko tri fytyra miqësore në pjesë të ndryshme "
    "të sallës.",
    "Nëse humbet fillin, shiko titullin e sllajdit dhe thuaje me zë: «So, the point here "
    "is …». Askush në sallë nuk e di çfarë kishe ndër mend të thoshe.",
    "Nëse të mungon një fjalë anglisht, thuaje më thjeshtë. «Let me say it in a simpler "
    "way» është plotësisht normale në një konferencë ndërkombëtare.",
    "Te pyetjet: dëgjoje deri në fund, ndalu dy sekonda, përgjigju me dy-tri fjali dhe "
    "ndalu. Përgjigja e shkurtër dhe e saktë duket më e sigurt se ajo e gjata.",
    "Kufizimet i ke vetë te sllajdi 9. Kur dikush të pyet për to, nuk të ka kapur: ti i "
    "ke thënë i pari. Pranoje, thuaj pse, dhe çka do të bëje më pas.",
    "Kujto: e ndërtove vetë, dhe askush në sallë nuk e njeh këtë sistem më mirë se ti. "
    "Shumica e prezantuesve janë studentë, dhe salla dëshiron që të dalësh mirë.",
]

CHECKLIST = [
    "Të mërkurën, 21 tetor: shiko agjendën përfundimtare dhe kontrollo radhën, orën dhe "
    "sallën.",
    "Merr të dy versionet në USB, si .pptx dhe si PDF, dhe dërgoji edhe me email vetes.",
    "Arrij te salla I-302 rreth 08:30, para se të fillojë seanca. Hape prezantimin në "
    "kompjuterin e sallës dhe kontrollo që kodi në sllajdin 8 duket njësoj (shkronja "
    "Consolas).",
    "Prezantohu te kryesuesi i seancës (Blerim Zylifu). Pyete sa minuta ka çdo prezantim "
    "dhe si ta sinjalizon kohën. Me 9 minuta ose më shumë merr versionin e gjatë; me më "
    "pak, të shkurtrin.",
    "Ujë pranë, telefoni pa zë, fleta e pyetjeve në xhep.",
    "Me versionin e shkurtër, kur vendi është 7 minuta: nëse në minutën e pestë je ende te "
    "sllajdi 6, kalo sllajdin 8 me një fjali dhe mbyll me sllajdin 9.",
    "Me versionin e gjatë: nëse në minutën e shtatë je ende te sllajdi 6, lëri të gjitha "
    "fjalitë e gjelbra që mbeten dhe vazhdo me tekstin e shkurtër.",
]

# Nga agjenda paraprake që dërguan organizatorët; agjenda përfundimtare vjen më 21 tetor.
CONFERENCE = [
    "15th UBT Annual International Conference on Computer Science and Engineering, 23–25 "
    "tetor 2026. Ceremonia e hapjes është të premten, 23 tetor, në UBT Innovation Campus "
    "– Lipjan. Prezantimi mund të mbahet fizikisht ose online.",
    "Seanca jote: «Session 1 – Software Engineering», e shtunë 24 tetor, 09:00–11:00, "
    "salla I-302 në UBT Campus. Kryesues Blerim Zylifu, bashkëkryesues Lavdim Menxhiqi.",
    "Je i 14-ti nga 17 prezantime në seancë. Email-i thotë 10 minuta për prezantim, por "
    "17 prezantime në 120 minuta lënë rreth 7 për secilin. Prandaj ke dy versione, dhe "
    "zgjedh njërin sipas kohës që jep kryesuesi.",
    "Në të njëjtën seancë ka tri punime për kodin dhe modelet gjuhësore: optimizimi i kodit "
    "Java me LLM, besueshmëria e kodit të gjeneruar nga AI, dhe punimi i mentores «Trust "
    "but Verify». Pyetja «pse jo një LLM?» ka gjasa të dalë; përgjigjen e ke më poshtë.",
    "Agjenda përfundimtare vjen të mërkurën, 21 tetor: kontrollo radhën, orën dhe sallën.",
    "Abstraktet botohen në «Abstract Book» me ISBN dhe DOI në UBT Knowledge Center. "
    "Pyete mentoren nëse kërkohet më vonë edhe punim i plotë (6 faqe, formati Springer).",
]


def build_sheet(f: dict, script: list[tuple[str, list[str]]]) -> str:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = DocPt(11)

    doc.add_heading("Konferenca e UBT-së 2026: përgatitja", level=0)
    doc.add_paragraph(f"{TITLE}\n{AUTHORS}")

    doc.add_heading("Çka dimë për konferencën", level=1)
    for line in CONFERENCE:
        doc.add_paragraph(line, style="List Bullet")

    words = {
        long: sum(_word_count(_spoken(parts, long)) for _, parts in script) for long in (False, True)
    }

    def minutes(long: bool, rate: int) -> str:
        return _clock(round(words[long] / rate * 60))

    doc.add_heading("Dy versione", level=1)
    for line in [
        f"{os.path.basename(DECK)}: versioni i shkurtër, {words[False]} fjalë, rreth "
        f"{minutes(False, WORDS_PER_MINUTE)} me ritëm të qetë. Për rastin kur kryesuesi jep "
        "7 minuta ose më pak.",
        f"{os.path.basename(DECK_LONG)}: versioni i gjatë, {words[True]} fjalë, rreth "
        f"{minutes(True, WORDS_PER_MINUTE)} me ritëm të qetë. Për rastin kur jep vërtet 10 "
        "minuta, siç thotë email-i.",
        "Sllajdet janë të njëjta; ndryshon vetëm teksti folës. I gjati është i shkurtri plus "
        "disa fjali shtesë, që te shënimet e PowerPoint-it janë me shkronja të pjerrëta e "
        "këtu më poshtë me të gjelbër: kur koha nuk mjafton, i lë dhe je te versioni i "
        "shkurtër pa humbur fillin.",
        f"Me ritëm të shpejtë ({FAST_WORDS_PER_MINUTE} fjalë në minutë) i shkurtri zgjat "
        f"{minutes(False, FAST_WORDS_PER_MINUTE)} dhe i gjati "
        f"{minutes(True, FAST_WORDS_PER_MINUTE)}, pa pauzat. Ky ritëm është supozim. Për ta matur tëndin, lexo me zë tekstin e "
        "sllajdit 2 me kronometër: fjalët e tij (te tabela) pjesëtuar me minutat janë "
        "ritmi yt.",
    ]:  # fmt: skip
        doc.add_paragraph(line, style="List Bullet")

    doc.add_heading("Koha për sllajd", level=1)
    doc.add_paragraph(
        f"E llogaritur nga fjalët e shënimeve folëse, me {WORDS_PER_MINUTE} fjalë në minutë, "
        "pa pauzat dhe kalimet mes sllajdeve (zakonisht edhe rreth një minutë gjithsej)."
    )
    headers = ["#", "Sllajdi", "Fjalë",
               "Shkurt: sek.", "Shkurt: gjithsej", "9 min: sek.", "9 min: gjithsej"]  # fmt: skip
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    for cell, text in zip(table.rows[0].cells, headers, strict=True):
        cell.text = text
    # Gjithsej nga fjalët e grumbulluara, jo nga sekondat e rrumbullakuara të çdo sllajdi,
    # që rreshti i fundit të thotë të njëjtën kohë si përmbledhja më lart.
    spoken_so_far = {False: 0, True: 0}
    for index, (title, parts) in enumerate(script, 1):
        row = table.add_row().cells
        row[0].text, row[1].text = str(index), title
        counts = [_word_count(_spoken(parts, long)) for long in (False, True)]
        row[2].text = str(counts[0]) if counts[0] == counts[1] else f"{counts[0]} / {counts[1]}"
        for column, long in ((3, False), (5, True)):
            spoken_so_far[long] += counts[long]
            row[column].text = str(round(counts[long] / WORDS_PER_MINUTE * 60))
            row[column + 1].text = _clock(round(spoken_so_far[long] / WORDS_PER_MINUTE * 60))

    doc.add_heading("Si të marrësh vetëbesim", level=1)
    for line in CONFIDENCE:
        doc.add_paragraph(line, style="List Bullet")

    doc.add_heading("Pyetjet e mundshme (përgjigju në anglisht, shkurt)", level=1)
    for question, answer in _questions(f):
        paragraph = doc.add_paragraph()
        paragraph.add_run(question).bold = True
        doc.add_paragraph(answer)

    doc.add_heading("Fraza të gatshme për pyetjet", level=1)
    for phrase, when in PHRASES:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(phrase).bold = True
        paragraph.add_run(f"  ({when})")

    doc.add_heading("Shqiptimi i termave", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Termi", "Si thuhet (përafërsisht)"
    for term, sound in PRONUNCIATION:
        row = table.add_row().cells
        row[0].text, row[1].text = term, sound

    doc.add_heading("Dita e konferencës", level=1)
    for line in CHECKLIST:
        doc.add_paragraph(line, style="List Bullet")

    doc.add_heading("Teksti i plotë që thua (shënimet e sllajdeve)", level=1)
    doc.add_paragraph(
        "Fjalitë me të gjelbër dhe të pjerrëta thuhen vetëm në versionin 9-minutësh. Pa to, "
        "mbetet saktësisht teksti i versionit të shkurtër."
    )
    for index, (title, parts) in enumerate(script, 1):
        paragraph = doc.add_paragraph()
        paragraph.add_run(f"{index}. {title}").bold = True
        paragraph = doc.add_paragraph()
        for position, part in enumerate(parts):
            run = paragraph.add_run(part if position == 0 else " " + part)
            if isinstance(part, Extra):
                run.italic = True
                run.font.color.rgb = DocRGB(*ADDED)

    doc.save(SHEET)
    return SHEET


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    facts = _facts()
    for long in (False, True):
        deck, script = build_deck(facts, long)
        words = sum(_word_count(_spoken(parts, long)) for _, parts in script)
        print(f"U gjenerua: {deck}")
        print(f"  Fjalë në tekstin folës: {words}, rreth {words / WORDS_PER_MINUTE:.1f} minuta "
              f"me ritëm të qetë, {words / FAST_WORDS_PER_MINUTE:.1f} me të shpejtë")  # fmt: skip
    sheet = build_sheet(facts, script)
    print(f"U gjenerua: {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
