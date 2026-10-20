"""Prezantimi në anglisht për Konferencën Ndërkombëtare të UBT-së 2026, dhe fleta e pyetjeve.

    PYTHONPATH=backend python docs/thesis/build_conference.py

Shkruan te `docs/konferenca/`:
- `UBT2026_Florent_Latifi.pptx`: nëntë sllajde, me tekstin folës anglisht te shënimet
  (rreth shtatë minuta), dhe sllajde rezervë për pyetjet;
- `UBT2026_Florent_Latifi_9min.pptx`: të njëjtat sllajde, me një tekst folës më të gjatë
  (rreth nëntë minuta e gjysmë) për rastin kur kryesuesi jep vërtet dhjetë minuta;
- `UBT2026_pergatitja.docx`: koha për sllajd për të dy versionet, pyetjet e mundshme me
  përgjigje, shqiptimi i termave dhe lista për ditën e konferencës;
- `UBT2026_cka_te_flas.docx`: udhëzuesi i fjalimit, sllajd për sllajd: çka shihet në
  sllajd, ku të tregohet, dhe çdo fjali angleze me kuptimin e saj shqip;
- `UBT2026_njohurite.docx`: punimi i shpjeguar nga e para, për një lexues që nuk e njeh
  temën, me të njëjtat shifra si sllajdet.

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
from dataclasses import dataclass, field

from build_slides import (
    ACCENT,
    CRITICAL,
    FIGURES,
    HEIGHT,
    INK,
    MARGIN,
    SOFT,
    WIDTH,
    _blank,
    _mean,
    _note,
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
from docx.shared import Cm as DocCm
from docx.shared import Pt as DocPt
from docx.shared import RGBColor as DocRGB
from javasmell import glossary
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
SPEECH = os.path.join(OUT_DIR, "UBT2026_cka_te_flas.docx")
KNOWLEDGE = os.path.join(OUT_DIR, "UBT2026_njohurite.docx")

TITLE = (
    "Automated Code Smell Detection and Refactoring Recommendations "
    "Using Software Metrics and Machine Learning"
)
AUTHORS = "Florent Latifi  ·  Altina Salihu"
AFFILIATION = "UBT – Higher Education Institution, Kosovo"
# Emri siç e shkruan agjenda e konferencës: email-i dhe faqja e saj përdorin shkurtesa
# të ndryshme, dhe agjenda është dokumenti që ka salla.
EVENT = "15th UBT Annual International Conference on Computer Science and Engineering  ·  2026"
# Nga agjenda paraprake; salla nuk shkruhet, sepse agjenda përfundimtare mund ta ndryshojë.
SESSION = "Session 1  ·  Software Engineering  ·  24 October 2026"

# Gri për rregullat, blu për modelin: e njëjta ndarje si te figurat e punimit, që
# lexohet edhe kur projektori i zbeh ngjyrat. Gria është e errët sa të kalojë kontrastin
# 3:1 që i duhet një grafiku kundrejt të bardhës.
MUTED = RGBColor(0x87, 0x91, 0x9C)
ADDED = RGBColor(0x2F, 0x6F, 0x45)
MONO = "Consolas"

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

# Rreshtat e krahasimit me PMD-në, siç i emërton sllajdi rezervë dhe dokumenti i njohurive.
PMD_NAMES = {
    "blob/strategy": "Blob (strategy)",
    "blob/with_size": "Blob (with size)",
    "data class/strategy": "Data Class",
    "long method/strategy": "Long Method",
    "feature envy/law_of_demeter": "Feature Envy (LawOfDemeter)",
}

# Emrat e refaktorimeve siç thuhen me gojë, jo siç janë në kod.
SPOKEN_REFACTORING = {"ReplaceNestedConditionalWithGuardClauses": "Guard Clauses"}


class Line(str):
    """Një fjali e tekstit folës, me kuptimin e saj shqip.

    Përkthimi nuk thuhet në sallë. Udhëzuesi i fjalimit e vë poshtë fjalisë angleze, që
    folësi ta dijë çka po thotë dhe të mos mësojë përmendësh tinguj pa kuptim. Fjalia dhe
    përkthimi shkruhen bashkë, që një shifër e ndryshuar të mos lërë njërën pas.
    """

    sq: str

    def __new__(cls, text: str, sq: str) -> Line:
        line = super().__new__(cls, text)
        line.sq = sq
        return line


class Extra(Line):
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
    pmd = _load("pmd_comparison.json")
    smells = sorted(ml["per_smell"])
    unsure, _ = _significance(smells)
    best = {s: ml["per_smell"][s]["models"][ml["per_smell"][s]["best_model"]] for s in smells}
    strategy = {s: _mean(rules, s) for s in smells}
    reviewers = {s: agreement["per_smell"][s]["mcc"] for s in smells}
    applied, detected = refactoring["applied"], refactoring["detected"]
    # Krahasimi me PMD-në: ndryshimi është yni minus i PMD-së, dhe vetëm një interval që
    # e përjashton zeron lejon të thuhet se njëri është përpara.
    differences = {
        key: entry["difference"] for key, entry in pmd["by_smell"].items() if "difference" in entry
    }
    by_refactoring = quality["by_refactoring"]
    return {
        "rules": rules,
        "ml": ml,
        "refactoring": refactoring,
        "quality": quality,
        "agreement": agreement,
        "dataset": dataset,
        "reference": reference,
        "pmd": pmd,
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
        "reviewers": reviewers,
        "recall": [strategy[s]["recall"] for s in smells],
        "model_mcc": [best[s]["mcc"] for s in smells],
        "rule_mcc": [strategy[s]["mcc"] for s in smells],
        "applied": applied,
        "detected": detected,
        "resolved": refactoring["resolution"]["resolved"] / applied,
        "broken": refactoring["verdicts"].get("new_errors", 0) / applied,
        "refused": sum(refactoring["refused_by_reason"].values()) / detected,
        "moderate": [s for s in smells if reviewers[s] > 0.1],
        "chance": [s for s in smells if reviewers[s] <= 0.1],
        "pmd_ahead": [SMELL_SQ[key.split("/")[0]] for key, d in differences.items()
                      if d["excludes_zero"] and d["median"] < 0],
        "pmd_behind": [SMELL_SQ[key.split("/")[0]] for key, d in differences.items()
                       if key.endswith("/strategy") and d["excludes_zero"] and d["median"] > 0],
        "introduced": refactoring["introduced_smells"],
        # Sa erëra fiton edhe algoritmi më i dobët kundër rregullave: përgjigjja kur dikush
        # pyet nëse zgjedhja e më të mirit e fryn rezultatin.
        "weakest": sum(
            min(e["mcc"] for e in ml["per_smell"][s]["models"].values() if e["mcc"] is not None)
            > strategy[s]["mcc"]
            for s in smells
        ),
        "always": [_words(name) for name, entry in by_refactoring.items() if entry["acceptable"] == 1.0],
        "never": [_words(name) for name, entry in by_refactoring.items() if entry["acceptable"] == 0.0],
    }  # fmt: skip


def _and(items: list[str], word: str = "and") -> str:
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {word} " + items[-1]


def _dhe(items: list[str]) -> str:
    return _and(items, "dhe")


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


def _bar_chart(slide, categories, series, top, height, minimum=0.0, maximum=1.0, left=MARGIN,
               width=None):  # fmt: skip
    """Shtylla të grupuara me vlerën mbi secilën, pa rrjetë dhe pa bosht të tepërt."""
    data = CategoryChartData()
    data.categories = categories
    for name, values, _ in series:
        data.add_series(name, values, number_format="0.00")
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width or WIDTH - 2 * MARGIN, height, data
    )
    chart = frame.chart
    # Me një seri të vetme PowerPoint-i i vë grafikut emrin e serisë si titull.
    chart.has_title = False
    chart.font.name = FONT
    chart.font.size = Pt(16)
    chart.font.color.rgb = INK
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
    chart.category_axis.tick_labels.font.size = Pt(16)
    chart.category_axis.has_major_gridlines = False
    chart.category_axis.format.line.color.rgb = FRAME
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
    labels.font.name = FONT_STRONG
    for index, (_, _, colour) in enumerate(series):
        plot.series[index].invert_if_negative = False
        fill = plot.series[index].format.fill
        fill.solid()
        fill.fore_color.rgb = colour
    return chart


def _elided(lines: list[str], marked: set[int]) -> tuple[list[str], set[int]]:
    """Blloku synchronized mblidhet në një rresht me një koment që thotë sa rreshta fsheh.

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
    folded = f"{lines[start].rstrip()} /* … {len(inner)} unchanged lines */ {lines[end].strip()}"
    shown = lines[:start] + [folded] + lines[end + 1 :]
    kept = {i if i < start else start if i <= end else i - (end - start) for i in marked}
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


def _script(f: dict) -> list[tuple]:
    """Teksti folës i nëntë sllajdeve kryesore, me radhë: emri i brendshëm dhe fjalitë.

    I ndarë nga paraqitja e sllajdeve, që një sllajd të rindërtohet pa e prekur tekstin
    që folësi e ka provuar.
    """
    refactoring, quality = f["refactoring"], f["quality"]
    recall, model_mcc = f["recall"], f["model_mcc"]
    applied, detected = f["applied"], f["detected"]
    resolved, broken = f["resolved"], f["broken"]
    moderate, chance = f["moderate"], f["chance"]
    pmd_ahead, pmd_behind = f["pmd_ahead"], f["pmd_behind"]
    introduced, always, never = f["introduced"], f["always"], f["never"]
    lowest, highest = min(recall) * 100, max(recall) * 100
    shape = refactoring["refused_by_reason"]["shape_not_matched"] / detected * 100
    newest = _words(max(introduced, key=introduced.get))
    return [
        (
            "Title",
            Line("Good morning, everyone.", "Mirëmëngjes të gjithëve."),
            Line(
                "My name is Florent Latifi, and this work comes from my bachelor thesis at UBT, "
                "supervised by Altina Salihu.",
                "Unë quhem Florent Latifi, dhe kjo punë vjen nga teza ime e bachelorit në UBT, me "
                "mentore Altina Salihu.",
            ),
            Line(
                "In the next ten minutes I will show how we can detect code smells in Java "
                "automatically, how accurate that detection really is, and how far we can go in "
                "fixing them.",
                "Në dhjetë minutat në vijim do të tregoj si mund t'i gjejmë automatikisht erërat e "
                "kodit në Java, sa e saktë është vërtet kjo gjetje, dhe deri ku mund të shkojmë me "
                "ndreqjen e tyre.",
            ),
        ),
        (
            "The problem",
            Line(
                "Every developer knows the class that nobody wants to touch.",
                "Çdo programues e njeh klasën që askush nuk do ta prekë.",
            ),
            Line(
                "The program works, but every change takes longer than it should.",
                "Programi punon, por çdo ndryshim zgjat më shumë se ç'duhet.",
            ),
            Line("These design problems are called code smells.",
                 "Këto probleme të ndërtimit të kodit quhen erëra të kodit."),
            Line("They are not bugs, but they make maintenance expensive.",
                 "Nuk janë gabime, por e bëjnë mirëmbajtjen të shtrenjtë."),
            Line("Most tools find them with fixed thresholds.",
                 "Shumica e mjeteve i gjejnë me pragje fikse, pra me numra të caktuar njëherë e "
                 "përgjithmonë."),
            Line(
                "For example, if a method is longer than a certain number of lines, it is a Long "
                "Method.",
                "Për shembull, nëse një metodë është më e gjatë se një numër i caktuar rreshtash, "
                "ajo quhet Long Method.",
            ),
            Line(
                "But these numbers were calibrated on other code, and most tools only point at the "
                "problem.",
                "Por këta numra janë përcaktuar duke parë kod tjetër, dhe shumica e mjeteve vetëm e "
                "tregojnë problemin.",
            ),
            Line("They do not fix it.", "Nuk e ndreqin."),
            Line("So we asked three questions.", "Prandaj bëmë tri pyetje."),
            Line("First, how accurate are the published detection rules?",
                 "E para: sa të sakta janë rregullat e botuara për gjetjen e erërave?"),
            Line("Second, can machine learning do better with the same metrics?",
                 "E dyta: a mund të bëjë më mirë mësimi makinerik, me të njëjtat metrika?"),
            Line("And third, can we fix smells automatically without breaking the code?",
                 "Dhe e treta: a mund t'i ndreqim erërat automatikisht, pa e prishur kodin?"),
        ),
        (
            "What we built",
            Line("To answer them, I built a tool called JavaSmell.",
                 "Për t'iu përgjigjur këtyre pyetjeve, ndërtova një mjet që quhet JavaSmell."),
            Line(f"It reads Java code and measures {f['metrics']} metrics for every class and method.",
                 f"E lexon kodin Java dhe mat {f['metrics']} metrika, pra numra, për çdo klasë dhe "
                 "metodë."),
            Line("On top of these metrics there are three approaches.",
                 "Mbi këto metrika ndërtohen tri qasje."),
            Line(
                f"A uses {f['strategies']} detection strategies from the literature, such as "
                "Lanza and Marinescu and Fowler.",
                f"A përdor {f['strategies']} rregulla gjetjeje nga literatura, si ato të Lanza-s e "
                "Marinescu-t dhe të Fowler-it.",
            ),
            Line("B trains machine learning classifiers on the same metrics.",
                 "B trajnon modele të mësimit makinerik mbi të njëjtat metrika."),
            Line("And C is a refactoring engine.", "Dhe C është një motor që e ndreq kodin."),
            Line(
                "It rewrites code only when it can prove its preconditions from the syntax tree, "
                "and then it checks the result with the Java compiler.",
                "E rishkruan kodin vetëm kur mund ta vërtetojë nga pema e sintaksës që ndryshimi "
                "është i sigurt, dhe pastaj e kontrollon rezultatin me kompajlerin e Java-s.",
            ),
            Extra(
                "Every detection also shows the conditions it checked, so a developer can see why a "
                "class was flagged, not only that it was.",
                "Çdo gjetje tregon edhe kushtet që kontrolloi, që programuesi të shohë pse u shënua "
                "një klasë, jo vetëm që u shënua.",
            ),
            Line("On the right you can see the web interface.", "Djathtas shihni ndërfaqen web."),
            Line("It also has a plain-language mode for people without a technical background.",
                 "Ka edhe një mënyrë me gjuhë të thjeshtë, për njerëzit pa përgatitje teknike."),
        ),
        (
            "Data and evaluation",
            Line("For a fair test, we need labels from people.",
                 "Për një provë të drejtë, na duhen etiketa nga njerëzit, pra dikush që thotë "
                 "«ky kod ka erë» ose «nuk ka»."),
            Line(
                "We used MLCQ, a public dataset where professional developers reviewed real "
                "open-source Java code.",
                "Përdorëm MLCQ, një bazë publike të dhënash ku programues profesionistë shqyrtuan "
                "kod të vërtetë Java me burim të hapur.",
            ),
            Line(
                f"After matching the samples to our tool, we have {f['samples']:,} labeled samples "
                f"from {f['repositories']} repositories, for four smells.",
                f"Pasi i gjetëm mostrat në kod me mjetin tonë, kemi {f['samples']:,} mostra me "
                f"etiketë nga {f['repositories']} projekte, për katër erëra.",
            ),
            Extra("Blob is a class that does too much.", "Blob është një klasë që bën shumë gjëra."),
            Extra("Data Class only holds data and has almost no behavior.",
                  "Data Class vetëm mban të dhëna dhe nuk bën pothuajse asgjë me to."),
            Extra(
                "Long Method is a method that has grown too long, and Feature Envy is a method that "
                "uses another class more than its own.",
                "Long Method është një metodë që është zgjatur shumë, dhe Feature Envy është një "
                "metodë që përdor një klasë tjetër më shumë se klasën e vet.",
            ),
            Line("One important detail is how we split the data.",
                 "Një detaj i rëndësishëm është si i ndamë të dhënat për mësim dhe për provë."),
            Line(
                "Code from the same project looks very similar, so we grouped the data by "
                "repository: a model is never tested on a project it learned from.",
                "Kodi i të njëjtit projekt ngjan shumë, ndaj i grupuam të dhënat sipas projektit: "
                "një model nuk provohet kurrë mbi një projekt nga i cili ka mësuar.",
            ),
            Line("And we report the Matthews correlation coefficient, MCC.",
                 "Dhe si notë kryesore raportojmë koeficientin e korrelacionit Matthews, MCC."),
            Line(
                "Most samples are clean, so simple accuracy would look very good even for a "
                "detector that never fires.",
                "Shumica e mostrave janë të pastra, ndaj saktësia e thjeshtë do të dukej shumë e "
                "mirë edhe për një detektor që nuk alarmon kurrë.",
            ),
        ),
        (
            "Rules vs. machine learning",
            Line("Here are the main results.", "Ja rezultatet kryesore."),
            Line(
                "The gray bars are the published rules, and the blue bars are the best machine "
                "learning model for each smell.",
                "Shtyllat gri janë rregullat e botuara, dhe shtyllat blu janë modeli më i mirë i "
                "mësimit makinerik për secilën erë.",
            ),
            Line(
                f"The rules are often correct when they fire, but they catch only {lowest:.0f} to "
                f"{highest:.0f} percent of the smells that developers marked.",
                f"Rregullat zakonisht kanë të drejtë kur alarmojnë, por kapin vetëm {lowest:.0f} deri "
                f"{highest:.0f} për qind të erërave që shënuan programuesit.",
            ),
            Line(
                f"The models are better on all four smells, with MCC from {min(model_mcc):.2f} to "
                f"{max(model_mcc):.2f}.",
                f"Modelet janë më të mira te të katër erërat, me MCC nga {min(model_mcc):.2f} deri "
                f"{max(model_mcc):.2f}.",
            ),
            Line("We also computed 95 percent confidence intervals by resampling repositories.",
                 "Llogaritëm edhe intervale besimi 95 për qind, duke i rizgjedhur projektet rastësisht "
                 "shumë herë."),
            Line(f"The improvement is clearly above zero for {_and(f['sure'])}.",
                 f"Përmirësimi është qartë mbi zero për {_dhe(f['sure'])}: nuk është fat."),
            Line(f"For {_and(f['unsure'])}, the difference could be chance.",
                 f"Për {_dhe(f['unsure'])}, ndryshimi mund të jetë edhe rastësi."),
            Extra("We also compared with PMD, a popular open-source analyzer, on the same samples.",
                  "E krahasuam edhe me PMD-në, një mjet i njohur falas për analizën e kodit, mbi të "
                  "njëjtat mostra."),
            Extra(
                "Once the confidence interval is considered, "
                + ("PMD is never ahead" if not pmd_ahead else f"PMD is ahead for {_and(pmd_ahead)}")
                + f", and for {_and(pmd_behind)} our rules are clearly better.",
                "Kur merret parasysh intervali i besimit, "
                + ("PMD nuk del kurrë përpara" if not pmd_ahead
                   else f"PMD del përpara për {_dhe(pmd_ahead)}")
                + f", dhe për {_dhe(pmd_behind)} rregullat tona janë qartë më të mira.",
            ),
        ),
        (
            "Human agreement",
            Line("Why is Feature Envy so hard?", "Pse është Feature Envy kaq e vështirë?"),
            Line("We measured how much the human reviewers agree with each other.",
                 "Matëm sa pajtohen rishikuesit njerëzorë me njëri-tjetrin."),
            Line(f"For {_and([SMELL_SQ[s] for s in moderate])}, two reviewers agree only moderately.",
                 f"Për {_dhe([SMELL_SQ[s] for s in moderate])}, dy rishikues pajtohen vetëm "
                 "mesatarisht."),
            Line(f"For {_and([SMELL_SQ[s] for s in chance])}, they agree no better than chance.",
                 f"Për {_dhe([SMELL_SQ[s] for s in chance])}, pajtohen jo më shumë se sa po të "
                 "hamendësonin."),
            *[
                Extra(f"For {SMELL_SQ[s]}, their MCC is {f['reviewers'][s]:.2f}, practically zero.",
                      f"Për {SMELL_SQ[s]}, MCC-ja e tyre është {f['reviewers'][s]:.2f}, praktikisht "
                      "zero.")
                for s in chance
            ],
            Extra(
                f"This matches the previous slide: {_and(f['unsure'])} is where the model could not "
                "clearly beat the rules.",
                f"Kjo përputhet me sllajdin e mëparshëm: te {_dhe(f['unsure'])} modeli nuk arriti "
                "t'i mundë qartë rregullat.",
            ),
            Line("So the problem is not only the algorithm.", "Pra problemi nuk është vetëm algoritmi."),
            Line("It is the definition of the smell itself.", "Është vetë përkufizimi i erës."),
            Line("If experts do not agree on what a smell is, no detector can learn it well.",
                 "Nëse ekspertët nuk pajtohen se çka është një erë, asnjë detektor nuk mund ta mësojë "
                 "mirë."),
            Line("For me, this is the main lesson of the detection part.",
                 "Për mua, ky është mësimi kryesor i pjesës së gjetjes së erërave."),
        ),
        (
            "Automatic refactoring",
            Line("Now the refactoring engine.", "Tani motori që e ndreq kodin."),
            Line(
                "It supports three transformations: Extract Method, Replace Nested Conditional with "
                "Guard Clauses, and Introduce Parameter Object.",
                "Ai di tri ndreqje: nxjerrjen e një metode, zëvendësimin e if-ave të futur thellë me "
                "dalje të hershme, dhe mbledhjen e shumë parametrave në një objekt.",
            ),
            Line(
                f"On the whole corpus it found {detected:,} sites and rewrote {applied:,} of them, "
                f"which is {applied / detected * 100:.0f} percent.",
                f"Në gjithë korpusin gjeti {detected:,} vende ku mund të ndreqte dhe rishkroi "
                f"{applied:,} prej tyre, pra {applied / detected * 100:.0f} për qind.",
            ),
            Line("The rest were refused, each with a reason.",
                 "Të tjerat i refuzoi, secilën me një arsye."),
            Extra(
                f"In {shape:.0f} percent of the sites, the reason is simply that the code does not "
                "have the shape the transformation needs.",
                f"Në {shape:.0f} për qind të vendeve, arsyeja është thjesht se kodi nuk ka formën që "
                "i duhet ndreqjes.",
            ),
            Line("For us, refusing is a correct result, not a failure.",
                 "Për ne, refuzimi është rezultat i saktë, jo dështim."),
            Line(f"After rewriting, the smell disappeared in {resolved * 100:.0f} percent of the cases.",
                 f"Pas rishkrimit, era u zhduk në {resolved * 100:.0f} për qind të rasteve."),
            Line(
                f"Only {broken * 100:.1f} percent of the rewrites introduced a new type of "
                "compilation error, and those never reach the code, because the tool only writes "
                "verified rewrites.",
                f"Vetëm {broken * 100:.1f} për qind e rishkrimeve shtuan një lloj të ri gabimi "
                "kompilimi, dhe ato nuk arrijnë kurrë te kodi, sepse mjeti shkruan vetëm rishkrime "
                "të kontrolluara.",
            ),
            Line(
                f"I also read {quality['reviewed']} rewrites by hand: after reweighting, about "
                f"{quality['acceptable_reweighted'] * 100:.0f} percent would be acceptable to a "
                "developer.",
                f"Lexova edhe {quality['reviewed']} rishkrime me dorë: pasi i peshova sipas sa të "
                f"shpeshtë janë, rreth {quality['acceptable_reweighted'] * 100:.0f} për qind do të "
                "ishin të pranueshme për një programues.",
            ),
            Extra(
                f"Refactoring can also create new smells: {sum(introduced.values()):,} appeared "
                f"after rewriting, most often {newest}, because Extract Method passes every input "
                "as a parameter.",
                f"Ndreqja mund të krijojë edhe erëra të reja: {sum(introduced.values()):,} u shfaqën "
                f"pas rishkrimit, më shpesh {newest}, sepse metoda e nxjerrë i merr të gjitha "
                "hyrjet si parametra.",
            ),
            Extra(
                f"In that review, {_and(always)} were always acceptable, and {_and(never)} never, "
                "because it only moves the long list into a new class.",
                f"Në atë rishikim, {_dhe(always)} ishin gjithmonë të pranueshme, dhe {_dhe(never)} "
                "kurrë, sepse vetëm e zhvendos listën e gjatë në një klasë të re.",
            ),
        ),
        (
            "Example",
            Line("Here is one real example from Apache Geode.",
                 "Ja një shembull i vërtetë nga Apache Geode, një projekt i madh me burim të hapur."),
            Line("Before, the whole method is wrapped in one if statement, so everything is nested "
                 "deeply.",
                 "Më parë, e gjithë metoda është brenda një if-i, ndaj gjithçka është e futur thellë."),
            Line(
                "After the rewrite, the condition becomes a guard clause with an early return, and "
                "the rest of the method moves one level up.",
                "Pas rishkrimit, kushti bëhet një «roje» që del herët nga metoda me return, dhe pjesa "
                "tjetër e metodës ngjitet një nivel lart.",
            ),
            Extra(
                "The engine accepts only exactly this shape: a void method whose whole body is one "
                "if statement, without else.",
                "Motori pranon vetëm saktësisht këtë formë: një metodë void, e cila nuk kthen vlerë, "
                "dhe trupi i saj është i gjithi një if, pa else.",
            ),
            Extra(
                "It also wraps the condition in a not, instead of inverting it by hand, so it stays "
                "correct for every condition.",
                "Gjithashtu e mbështjell kushtin me një «jo» (!), në vend që ta kthejë së prapthi me "
                "dorë, ndaj mbetet i saktë për çdo kusht.",
            ),
            Line("The rewrite passed the compiler check, and in my review it was acceptable as it is.",
                 "Rishkrimi e kaloi kontrollin e kompajlerit, dhe në rishikimin tim ishte i "
                 "pranueshëm ashtu siç është."),
        ),
        (
            "Limitations and takeaways",
            Line("To be honest about the limits: compiling is not the same as behaving the same.",
                 "Për të qenë i sinqertë për kufijtë: që kodi kompilohet nuk do të thotë që sillet "
                 "njësoj si më parë."),
            Line("We did not run the projects' test suites, so behavior preservation is future work.",
                 "Nuk i ekzekutuam testet e projekteve, ndaj vërtetimi që sjellja mbetet e njëjtë "
                 "është punë për më vonë."),
            Line("We also used one dataset, four smells, and only Java.",
                 "Përdorëm gjithashtu vetëm një bazë të dhënash, katër erëra dhe vetëm Java."),
            Extra(
                "And the best model was chosen on the same predictions it is scored on, so its "
                "numbers are slightly optimistic.",
                "Dhe modeli më i mirë u zgjodh mbi të njëjtat parashikime me të cilat vlerësohet, "
                "ndaj numrat e tij janë pak më të mirë se në realitet.",
            ),
            Extra(
                "As next steps, I would add a small symbol resolver to support more refactorings, "
                "and ask independent reviewers to judge the rewrites.",
                "Si hapa të ardhshëm, do të shtoja një pjesë të vogël që i kupton emrat në kod, për "
                "të mbështetur më shumë ndreqje, dhe do t'u kërkoja rishikuesve të pavarur t'i "
                "gjykojnë rishkrimet.",
            ),
            Line("To summarize: learned boundaries beat fixed thresholds.",
                 "Për ta përmbledhur: kufijtë që i mëson modeli i mundin pragjet fikse."),
            Line("Safe automatic refactoring is possible, but narrow, and it should be reviewed by a "
                 "developer.",
                 "Ndreqja automatike e sigurt është e mundshme, por vetëm për pak raste, dhe duhet ta "
                 "shohë një programues."),
            Line("The tool is open source, and every number in this talk can be regenerated with a "
                 "script.",
                 "Mjeti është me burim të hapur, dhe çdo numër në këtë prezantim mund të rimerret me "
                 "një skript."),
            Line("Thank you.", "Faleminderit."),
            Line("I am happy to take your questions.", "Me kënaqësi i pres pyetjet tuaja."),
        ),
    ]  # fmt: skip


# ----------------------------------------------------------------------
# Sistemi vizual i prezantimit
# ----------------------------------------------------------------------
# Segoe UI ndodhet në çdo Windows, ndaj kompjuteri i sallës e vizaton sllajdin ashtu siç
# u ndërtua; një font i shkarkuar mund të zëvendësohet atje dhe ta prishë faqosjen.
FONT = "Segoe UI"
FONT_STRONG = "Segoe UI Semibold"

# Ngjyrat janë të projektit: blu e figurave të punimit dhe e ndërfaqes, e kuqja vetëm për
# atë që nuk funksionon. Sfondi i errët vetëm për hapjen dhe mbylljen, që salla ta ndiejë
# fillimin dhe fundin pa e lexuar.
NAVY = RGBColor(0x0E, 0x27, 0x40)
ON_DARK = RGBColor(0xF4, 0xF6, 0xF9)
ON_DARK_SOFT = RGBColor(0xA9, 0xB8, 0xC9)
ACCENT_ON_DARK = RGBColor(0x8D, 0xBB, 0xE6)
DANGER_ON_DARK = RGBColor(0xF0, 0x8A, 0x7E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PANEL = RGBColor(0xF2, 0xF4, 0xF7)
TINT = RGBColor(0xE4, 0xED, 0xF6)
REFUSED = RGBColor(0xDD, 0xE2, 0xE8)
FRAME = RGBColor(0xC9, 0xD0, 0xD8)
# Gri e rregullave si tekst: më e errët se shtylla, që të lexohet nga fundi i sallës.
RULE_TEXT = RGBColor(0x5E, 0x68, 0x74)
REMOVED_TINT = RGBColor(0xF7, 0xE1, 0xDC)
ADDED_TINT = RGBColor(0xDF, 0xEF, 0xE3)

# Shkalla e shkronjave: titulli lexohet nga rreshti i fundit, teksti nga mesi i sallës.
SIZE_TITLE = Pt(28)
SIZE_LEAD = Pt(20)
SIZE_CAPTION = Pt(16)
SIZE_SMALL = Pt(14)
SIZE_FOOT = Pt(12)
SIZE_STAT = Pt(40)
SIZE_NUMBER = Pt(56)
RADIUS = Inches(0.08)
STAT_HEIGHT = Inches(1.7)
# Kodi: rreshti më i gjatë i shembullit duhet të hyjë në dy të tretat e sllajdit.
CODE_SIZE = Pt(13)
GAP = Inches(0.3)
CONTENT = WIDTH - 2 * MARGIN
# Titulli lë vend djathtas për hartën e pyetjeve, në çdo sllajd në të njëjtin vend.
TITLE_WIDTH = WIDTH - 2 * MARGIN - Inches(2.75)
TOP = Inches(2.0)
# Maja e boshtit MCC, e njëjtë te dy grafikët që salla t'i krahasojë me sy.
MCC_TOP = 0.9

# Pjesa e fotos së ndërfaqes që tregon dy gjetje me kushtet e tyre, në pikselat e origjinalit:
# e plotë, teksti i saj del sa një gjilpërë në projektor.
INTERFACE_CROP = (195, 1090, 1300, 1640)


def _frame(slide, left, top, width, height, anchor=MSO_ANCHOR.TOP):
    """Një kuti teksti pa kufi të brendshëm, që teksti të rreshtohet me format përreth."""
    frame = slide.shapes.add_textbox(left, top, width, height).text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = anchor
    return frame


def _run(paragraph, text: str, size, colour, strong: bool = False):
    run = paragraph.add_run()
    run.text = text
    run.font.size = size
    run.font.color.rgb = colour
    run.font.name = FONT_STRONG if strong else FONT
    return run


def _put(frame, text: str, size, colour, *, strong=False, new=False, align=PP_ALIGN.LEFT,
         before=0, after=0):  # fmt: skip
    paragraph = frame.add_paragraph() if new else frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.space_before = Pt(before)
    paragraph.space_after = Pt(after)
    _run(paragraph, text, size, colour, strong)
    return paragraph


def _shape(slide, left, top, width, height, fill, kind=MSO_SHAPE.ROUNDED_RECTANGLE, line=None):
    """Një formë e mbushur, pa hije: rrumbullakimi është i njëjtë në gjithë prezantimin."""
    shape = slide.shapes.add_shape(kind, left, top, width, height)
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        shape.adjustments[0] = min(RADIUS / min(width, height), 0.5)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(0.75)
    shape.shadow.inherit = False
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.18)
    frame.margin_top = frame.margin_bottom = Inches(0.1)
    return shape


def _background(slide, colour) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = colour


def _heading(slide, title: str, subtitle: str = "", dark: bool = False, kicker: str = ""):
    """Titulli në të njëjtin vend në çdo sllajd; titulli thotë gjetjen, nëntitulli burimin."""
    frame = _frame(slide, MARGIN, Inches(0.45), TITLE_WIDTH, Inches(1.4))
    paragraph = frame.paragraphs[0]
    if kicker:
        _run(paragraph, kicker, SIZE_TITLE, ON_DARK_SOFT if dark else SOFT, strong=True)
    _run(paragraph, title, SIZE_TITLE, ON_DARK if dark else INK, strong=True)
    if subtitle:
        _put(frame, subtitle, SIZE_CAPTION, ON_DARK_SOFT if dark else SOFT, new=True, before=6)
    return frame


def _map(slide, active: set[int]) -> None:
    """Tri pyetjet e kërkimit lart djathtas; ndizet ajo për të cilën flet sllajdi.

    Salla nuk e mban mend skeletin e një prezantimi dhjetë-minutësh; harta ia kujton në
    çdo sllajd pa asnjë fjalë më shumë.
    """
    width, height, gap = Inches(0.78), Inches(0.36), Inches(0.1)
    left = WIDTH - MARGIN - 3 * width - 2 * gap
    for index in (1, 2, 3):
        on = index in active
        pill = _shape(slide, Emu(int(left + (index - 1) * (width + gap))), Inches(0.5), width,
                      height, ACCENT if on else PANEL)  # fmt: skip
        pill.adjustments[0] = 0.5
        frame = pill.text_frame
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        _put(frame, f"RQ{index}", SIZE_SMALL, WHITE if on else SOFT, strong=True,
             align=PP_ALIGN.CENTER)  # fmt: skip


def _footer(slide, index: int, dark: bool = False) -> None:
    """Emri dhe numri i sllajdit, që një pyetje të mund të thotë «te sllajdi 5»."""
    colour = ON_DARK_SOFT if dark else SOFT
    top, height = HEIGHT - Inches(0.55), Inches(0.3)
    _put(_frame(slide, MARGIN, top, Inches(4), height), "Florent Latifi  ·  UBT 2026", SIZE_FOOT,
         colour)  # fmt: skip
    _put(_frame(slide, WIDTH - MARGIN - Inches(1), top, Inches(1), height), str(index), SIZE_FOOT,
         colour, align=PP_ALIGN.RIGHT)  # fmt: skip


def _bullet(paragraph, colour) -> None:
    """Një pikë e vërtetë e PowerPoint-it, me dhëmbëzim të varur, jo një «·» në tekst."""
    properties = paragraph._p.get_or_add_pPr()
    indent = int(Inches(0.3))
    properties.set("marL", str(indent))
    properties.set("indent", str(-indent))
    tint = properties.makeelement(qn("a:buClr"), {})
    tint.append(tint.makeelement(qn("a:srgbClr"), {"val": str(colour)}))
    properties.append(tint)
    properties.append(properties.makeelement(qn("a:buFont"), {"typeface": "Arial"}))
    properties.append(properties.makeelement(qn("a:buChar"), {"char": "•"}))


def _bullet_list(slide, left, top, width, height, lines, size=SIZE_LEAD, colour=INK, mark=ACCENT,
                 after=12):  # fmt: skip
    frame = _frame(slide, left, top, width, height)
    for index, line in enumerate(lines):
        _bullet(_put(frame, line, size, colour, new=index > 0, after=after), mark)
    return frame


def _stat(slide, left, top, width, number: str, caption: str, colour=ACCENT, size=SIZE_NUMBER,
          caption_colour=SOFT, height=STAT_HEIGHT):  # fmt: skip
    """Një shifër e madhe me nënshkrimin e saj: syri e gjen shifrën para se ta dëgjojë."""
    frame = _frame(slide, left, top, width, height)
    _put(frame, number, size, colour, strong=True)
    _put(frame, caption, SIZE_CAPTION, caption_colour, new=True, before=2)
    return frame


def _badge(slide, left, top, letter: str, fill) -> None:
    """Shkronja e qasjes (A, B, C) në një rreth: e njëjta shenjë në çdo sllajd ku shfaqet."""
    size = Inches(0.36)
    circle = _shape(slide, left, top, size, size, fill, kind=MSO_SHAPE.OVAL)
    frame = circle.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    _put(frame, letter, SIZE_SMALL, WHITE, strong=True, align=PP_ALIGN.CENTER)


def _node(slide, left, top, width, height, text: str, fill=PANEL, letter="", letter_fill=ACCENT):
    """Një hap i rrjedhës, me shkronjën e qasjes kur hapi i përket njërës prej tyre."""
    _shape(slide, left, top, width, height, fill)
    inset = Inches(0.16)
    if letter:
        _badge(slide, Emu(int(left + inset)), Emu(int(top + (height - Inches(0.36)) / 2)), letter,
               letter_fill)  # fmt: skip
        inset = Inches(0.66)
    frame = _frame(slide, Emu(int(left + inset)), top, Emu(int(width - inset - Inches(0.14))),
                   height, MSO_ANCHOR.MIDDLE)  # fmt: skip
    _put(frame, text, SIZE_CAPTION, INK)


def _arrow(slide, centre, top, height) -> None:
    arrow = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Emu(int(centre - Inches(0.1))), top,
                                   Inches(0.2), height)  # fmt: skip
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = FRAME
    arrow.line.fill.background()
    arrow.shadow.inherit = False


def _diff(slide, label, lines, marked, tint, colour, left, top, width, size=CODE_SIZE) -> Emu:
    """Kod me rreshtat e ndryshuar në një brez ngjyre, si në një pamje ndryshimesh.

    Lartësia e rreshtit është e saktë, ndaj brezi bie mbi rreshtin e vet pa u matur me sy.
    """
    line = Pt(round(size.pt * 1.15, 1))
    _put(_frame(slide, left, top, width, Inches(0.3)), label, SIZE_SMALL, SOFT, strong=True)
    top = Emu(int(top + Inches(0.34)))
    pad_x, pad_y = Inches(0.16), Inches(0.1)
    height = Emu(int(line * len(lines) + 2 * pad_y))
    _shape(slide, left, top, width, height, PANEL)
    for index in sorted(marked):
        _shape(slide, left, Emu(int(top + pad_y + line * index)), width, line, tint,
               kind=MSO_SHAPE.RECTANGLE)  # fmt: skip
    frame = _frame(slide, Emu(int(left + pad_x)), Emu(int(top + pad_y)),
                   Emu(int(width - 2 * pad_x)), Emu(int(height - 2 * pad_y)))  # fmt: skip
    frame.word_wrap = False
    for index, text in enumerate(lines):
        paragraph = frame.add_paragraph() if index else frame.paragraphs[0]
        paragraph.line_spacing = line
        paragraph.space_before = paragraph.space_after = Pt(0)
        run = paragraph.add_run()
        run.text = text or " "
        run.font.name = MONO
        run.font.size = size
        run.font.bold = index in marked
        run.font.color.rgb = colour if index in marked else INK
    return Emu(int(top + height))


def _data_table(slide, headers, rows, top=TOP, size=SIZE_CAPTION):
    """Tabelat rezervë: koka me blu, rreshtat me një nuancë të lehtë në çdo të dytin."""
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), MARGIN, top, CONTENT,
                                   Inches(0.5 * (len(rows) + 1)))  # fmt: skip
    table = shape.table
    # Kolonat sipas tekstit më të gjatë të secilës: me gjerësi të barabarta, «Feature Envy»
    # dhe emrat e modeleve thyhen në dy rreshta ndërsa kolonat e numrave mbeten gjysmë bosh.
    longest = [max(max(len(str(row[column])) for row in rows), len(headers[column]), 6)
               for column in range(len(headers))]  # fmt: skip
    for column, length in zip(table.columns, longest, strict=True):
        column.width = Emu(int(CONTENT * length / sum(longest)))
    for line, values in enumerate([headers, *rows]):
        for column, value in enumerate(values):
            cell = table.cell(line, column)
            cell.fill.solid()
            cell.fill.fore_color.rgb = ACCENT if line == 0 else (PANEL if line % 2 == 0 else WHITE)
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            frame = cell.text_frame
            frame.paragraphs[0].text = ""
            _put(frame, str(value), size if line else SIZE_SMALL, WHITE if line == 0 else INK,
                 strong=line == 0 or column == 0,
                 align=PP_ALIGN.LEFT if column == 0 else PP_ALIGN.RIGHT)  # fmt: skip
    return table


# ----------------------------------------------------------------------
# Sllajdet
# ----------------------------------------------------------------------
def _headings(f: dict) -> list[str]:
    """Titulli i çdo sllajdi kryesor: gjetja në një fjali, që salla ta lexojë para se ta dëgjojë.

    Prezantimi dhe udhëzuesi i fjalimit i marrin nga këtu, që të mos thonë dy tituj.
    """
    better = sum(f["best"][s]["mcc"] > f["strategy"][s]["mcc"] for s in f["smells"])
    count = "all four" if better == len(f["smells"]) == 4 else f"{better} of {len(f['smells'])}"
    chance = _and([SMELL_SQ[s] for s in f["chance"]])
    return [
        TITLE,
        "Code smells make every change expensive, and today's tools only point at them",
        f"JavaSmell measures {f['metrics']} metrics once and answers with three approaches",
        "Professional developers label the code; no model is tested on a project it saw",
        f"Learned models beat the rules on {count} smells",
        f"For {chance}, even two experts agree no better than chance",
        "The engine rewrites only what it can prove, and refuses the rest with a reason",
        "Real code: the outer if becomes an early return",
        "Limitations and takeaways",
    ]


def _slide_title(slide, f, heading) -> None:
    _background(slide, NAVY)
    _put(_frame(slide, MARGIN, Inches(0.6), CONTENT, Inches(0.4)), EVENT, SIZE_SMALL, ON_DARK_SOFT)
    _put(_frame(slide, MARGIN, Inches(1.75), Inches(11.0), Inches(2.4)), heading, Pt(40), ON_DARK,
         strong=True)  # fmt: skip
    frame = _frame(slide, MARGIN, Inches(4.45), CONTENT, Inches(1.0))
    _put(frame, AUTHORS, SIZE_LEAD, ON_DARK)
    _put(frame, AFFILIATION, SIZE_CAPTION, ON_DARK_SOFT, new=True, before=4)
    _put(_frame(slide, MARGIN, Inches(6.55), CONTENT, Inches(0.4)), SESSION, SIZE_SMALL,
         ON_DARK_SOFT)  # fmt: skip


def _slide_problem(slide, f, heading) -> None:
    _heading(slide, heading, "Code smells are design problems, not bugs")
    _bullet_list(slide, MARGIN, TOP, CONTENT, Inches(1.5), [
        "The program works, but every change costs more than it should.",
        "Existing tools use fixed thresholds, calibrated on other code.",
        "They point at the problem, but rarely fix it.",
    ], after=8)  # fmt: skip
    questions = [
        ("RQ1", "How accurate are published detection rules?", "A", "Rules", MUTED),
        ("RQ2", "Does machine learning on the same metrics do better?", "B", "Machine learning",
         ACCENT),
        ("RQ3", "Can fixes be applied automatically without breaking compilation?", "C",
         "Refactoring engine", ACCENT),
    ]  # fmt: skip
    width = Emu(int((CONTENT - 2 * GAP) / 3))
    top, height = Inches(3.85), Inches(2.6)
    for index, (label, question, letter, approach, fill) in enumerate(questions):
        left = Emu(int(MARGIN + index * (width + GAP)))
        _shape(slide, left, top, width, height, PANEL)
        frame = _frame(slide, Emu(int(left + Inches(0.25))), Emu(int(top + Inches(0.25))),
                       Emu(int(width - Inches(0.5))), Inches(1.6))  # fmt: skip
        _put(frame, label, SIZE_CAPTION, ACCENT, strong=True)
        _put(frame, question, SIZE_LEAD, INK, strong=True, new=True, before=6)
        badge_top = Emu(int(top + height - Inches(0.6)))
        _badge(slide, Emu(int(left + Inches(0.25))), badge_top, letter, fill)
        _put(_frame(slide, Emu(int(left + Inches(0.72))), badge_top, Inches(2.6), Inches(0.36),
                    MSO_ANCHOR.MIDDLE), approach, SIZE_SMALL, SOFT)  # fmt: skip


def _slide_system(slide, f, heading) -> None:
    _heading(slide, heading, "One analyzer: A rules · B machine learning · C refactoring engine")
    left, width, height, gap = MARGIN, Inches(6.2), Inches(0.52), Inches(0.2)
    half = Emu(int((width - Inches(0.2)) / 2))
    centre = Emu(int(left + width / 2))
    rows = [
        ("Java source code", None),
        (f"{f['metrics']} metrics for every class and method", None),
        ("split", None),
        ("Smells, each with the conditions that fired", None),
        ("Refactoring engine: rewrites only what it can prove", "C"),
        ("javac check, then a patch — never written in place", None),
    ]
    # Rreshti i ndarë (A dhe B) merr dy shigjeta, një për secilën kuti, që rrjedha të mos
    # duket sikur kalon mes tyre.
    halves = [Emu(int(left + half / 2)), Emu(int(left + half + Inches(0.2) + half / 2))]
    top = TOP
    for index, (text, letter) in enumerate(rows):
        if index:
            split = "split" in (text, rows[index - 1][0])
            for centre_x in halves if split else [centre]:
                _arrow(slide, centre_x, Emu(int(top - gap + Inches(0.03))),
                       Emu(int(gap - Inches(0.06))))  # fmt: skip
        if text == "split":
            _node(slide, left, top, half, height, f"{f['strategies']} published rules", PANEL, "A",
                  MUTED)  # fmt: skip
            _node(slide, Emu(int(left + half + Inches(0.2))), top, half, height,
                  "Machine learning", TINT, "B")  # fmt: skip
        else:
            _node(slide, left, top, width, height, text, TINT if letter else PANEL, letter or "")
        top = Emu(int(top + height + gap))
    picture_left = Emu(int(MARGIN + width + Inches(0.45)))
    picture_width = Emu(int(WIDTH - MARGIN - picture_left))
    path = os.path.join(FIGURES, "nderfaqja_paneli.png")
    x0, y0, x1, y1 = INTERFACE_CROP
    picture = slide.shapes.add_picture(path, picture_left, Inches(2.55), width=picture_width,
                                       height=Emu(int(picture_width * (y1 - y0) / (x1 - x0))))  # fmt: skip
    pixels_w, pixels_h = picture.image.size
    picture.crop_left, picture.crop_right = x0 / pixels_w, 1 - x1 / pixels_w
    picture.crop_top, picture.crop_bottom = y0 / pixels_h, 1 - y1 / pixels_h
    picture.line.color.rgb = FRAME
    picture.line.width = Pt(0.75)
    _put(_frame(slide, picture_left, Emu(int(picture.top + picture.height + Inches(0.15))),
                picture_width, Inches(0.9)),
         "Web interface, plain-language mode (Albanian): every finding shows the conditions "
         "that fired", SIZE_SMALL, SOFT)  # fmt: skip


def _slide_data(slide, f, heading) -> None:
    _heading(slide, heading, "MLCQ (Madeyski & Lewowski, 2020): reviewed by 26 professional "
                             "developers")  # fmt: skip
    _map(slide, {1, 2})
    width = Emu(int((CONTENT - 2 * GAP) / 3))
    for index, (number, caption) in enumerate([
        (f"{f['samples']:,}", "labeled samples: a class or a method judged by a person"),
        (f"{f['repositories']}", "repositories, each one an open-source project"),
        (f"{len(f['smells'])}", "code smells: " + ", ".join(SMELL_SQ[s] for s in f["smells"])),
    ]):  # fmt: skip
        _stat(slide, Emu(int(MARGIN + index * (width + GAP))), TOP, width, number, caption)
    # Pesë grupet e projekteve: modeli mëson nga katër dhe provohet te i pesti.
    folds, top, fold_w, fold_h = 5, Inches(4.0), Inches(1.22), Inches(1.6)
    gap, tile, tile_gap = Inches(0.17), Inches(0.24), Inches(0.1)
    for index in range(folds):
        left = Emu(int(MARGIN + index * (fold_w + gap)))
        test = index == folds - 1
        _shape(slide, left, top, fold_w, fold_h, TINT if test else PANEL)
        grid = 3 * tile + 2 * tile_gap
        x0 = Emu(int(left + (fold_w - grid) / 2))
        for cell in range(9):
            row, column = divmod(cell, 3)
            _shape(slide, Emu(int(x0 + column * (tile + tile_gap))),
                   Emu(int(top + Inches(0.22) + row * (tile + tile_gap))), tile, tile,
                   ACCENT if test else MUTED)  # fmt: skip
        _put(_frame(slide, left, Emu(int(top + fold_h - Inches(0.42))), fold_w, Inches(0.3)),
             "test" if test else "train", SIZE_SMALL, ACCENT if test else SOFT, strong=test,
             align=PP_ALIGN.CENTER)  # fmt: skip
    diagram_w = Emu(int(folds * fold_w + (folds - 1) * gap))
    _put(_frame(slide, MARGIN, Emu(int(top + fold_h + Inches(0.15))), diagram_w, Inches(0.7)),
         f"{f['ml']['folds']} folds grouped by repository: each project sits in exactly one. "
         "Train on four, test on the fifth, five times.", SIZE_SMALL, SOFT)  # fmt: skip
    majority = f["ml"]["per_smell"]["feature envy"]["models"]["majority"]["accuracy"]
    panel_left = Emu(int(MARGIN + diagram_w + Inches(0.45)))
    panel_w = Emu(int(WIDTH - MARGIN - panel_left))
    _shape(slide, panel_left, top, panel_w, Inches(2.3), PANEL)
    frame = _frame(slide, Emu(int(panel_left + Inches(0.25))), Emu(int(top + Inches(0.2))),
                   Emu(int(panel_w - Inches(0.5))), Inches(2.0))  # fmt: skip
    _put(frame, "Why MCC, not accuracy", SIZE_CAPTION, INK, strong=True)
    _put(frame, f"{majority:.1%}", SIZE_STAT, CRITICAL, strong=True, new=True, before=4)
    _put(frame, "accuracy of a detector that always says “clean” on Feature Envy. Its MCC is 0.",
         SIZE_CAPTION, INK, new=True, before=2)  # fmt: skip


def _slide_results(slide, f, heading) -> None:
    _heading(slide, heading, "MCC on the same samples, same scoring code · 95% bootstrap interval "
                             "by repository")  # fmt: skip
    _map(slide, {1, 2})
    # Vendimi statistikor nën emrin e erës: grafiku e thotë vetë cila fitore është e sigurt.
    names = [f"{SMELL_SQ[s]}\n({'significant' if SMELL_SQ[s] in f['sure'] else 'could be chance'})"
             for s in f["smells"]]  # fmt: skip
    _bar_chart(slide, names, [("Published rules (A)", f["rule_mcc"], MUTED),
                              ("Best ML model (B)", f["model_mcc"], ACCENT)],
               top=TOP, height=Inches(4.7), width=Inches(8.2), maximum=MCC_TOP)  # fmt: skip
    left = Emu(int(MARGIN + Inches(8.6)))
    width = Emu(int(WIDTH - MARGIN - left))
    lowest, highest = min(f["recall"]) * 100, max(f["recall"]) * 100
    _stat(slide, left, Inches(2.3), width, f"{lowest:.0f}–{highest:.0f}%",
          "of the smells developers marked, caught by the rules", RULE_TEXT, SIZE_STAT)  # fmt: skip
    _stat(slide, left, Inches(4.3), width, f"{min(f['model_mcc']):.2f}–{max(f['model_mcc']):.2f}",
          "MCC of the best model, per smell", ACCENT, SIZE_STAT)  # fmt: skip


def _slide_agreement(slide, f, heading) -> None:
    _heading(slide, heading, "Agreement between two human reviewers of the same code, as MCC · "
                             "0 = chance")  # fmt: skip
    _map(slide, {2})
    smells, chance = f["smells"], f["chance"]
    chart = _bar_chart(slide, f["names"], [("Two reviewers", [f["reviewers"][s] for s in smells],
                                            ACCENT)],
                       top=TOP, height=Inches(4.7), width=Inches(8.2), minimum=-0.2,
                       maximum=MCC_TOP)  # fmt: skip
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
    left = Emu(int(MARGIN + Inches(8.6)))
    width = Emu(int(WIDTH - MARGIN - left))
    for s in chance[:1]:
        _stat(slide, left, Inches(2.3), width, f"{f['reviewers'][s]:.2f}".replace("-", "−"),
              f"{SMELL_SQ[s]}: two reviewers agree at chance level", CRITICAL)  # fmt: skip
    _put(_frame(slide, left, Inches(4.5), width, Inches(1.6)),
         "If experts do not agree on what a smell is, no detector can learn it well.",
         SIZE_LEAD, INK, strong=True)  # fmt: skip


def _slide_engine(slide, f, heading) -> None:
    _heading(slide, heading, "Three transformations: Extract Method · Guard Clauses · Introduce "
                             "Parameter Object")  # fmt: skip
    _map(slide, {3})
    applied, detected, quality = f["applied"], f["detected"], f["quality"]
    refused = sum(f["refactoring"]["refused_by_reason"].values())
    frame = _frame(slide, MARGIN, TOP, CONTENT, Inches(0.7), MSO_ANCHOR.BOTTOM)
    paragraph = frame.paragraphs[0]
    _run(paragraph, f"{detected:,}", SIZE_STAT, INK, strong=True)
    _run(paragraph, "   sites where a transformation could apply", SIZE_CAPTION, SOFT)
    top, height = Inches(2.85), Inches(0.75)
    rewritten_w = Emu(int(CONTENT * applied / detected))
    refused_w = Emu(int(CONTENT * refused / detected) - Inches(0.05))
    # Gjerësia e çdo pjese është pjesa e vendeve: shiriti e tregon raportin pa e lexuar.
    for segment_left, segment_w, fill, colour, label, share in (
        (MARGIN, rewritten_w, ACCENT, WHITE, f"{applied:,} rewritten", applied / detected),
        (Emu(int(MARGIN + rewritten_w + Inches(0.05))), refused_w, REFUSED, INK,
         f"{refused:,} refused, each with a reason", refused / detected),
    ):  # fmt: skip
        frame = _shape(slide, segment_left, top, segment_w, height, fill).text_frame
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        frame.margin_top = frame.margin_bottom = Inches(0.04)
        _put(frame, label, SIZE_CAPTION, colour, strong=True)
        _put(frame, _pct(share), SIZE_SMALL, colour, new=True)
    _put(_frame(slide, MARGIN, Inches(3.95), CONTENT, Inches(0.3)), f"Of the {applied:,} rewrites",
         SIZE_SMALL, SOFT, strong=True)  # fmt: skip
    width = Emu(int((CONTENT - 2 * GAP) / 3))
    tiles = [
        (_pct(f["resolved"]), "removed the smell they were made for"),
        (_pct(f["broken"]), "added a new kind of compile error, and are never written"),
        (_pct(quality["acceptable_reweighted"]),
         f"acceptable to a developer in a manual review of {quality['reviewed']} (reweighted)"),
    ]  # fmt: skip
    for index, (number, caption) in enumerate(tiles):
        left = Emu(int(MARGIN + index * (width + GAP)))
        _shape(slide, left, Inches(4.35), width, Inches(1.8), PANEL)
        _stat(slide, Emu(int(left + Inches(0.25))), Inches(4.55), Emu(int(width - Inches(0.5))),
              number, caption, ACCENT, SIZE_STAT, INK)  # fmt: skip


def _slide_example(slide, f, heading) -> None:
    _heading(slide, heading, "Apache Geode · DistributedRegion.checkForLimitedOrNoAccess · Guard "
                             "Clauses")  # fmt: skip
    _map(slide, {3})
    code = _example()
    if code is None:
        _put(_frame(slide, MARGIN, TOP, CONTENT, Inches(0.6)),
             "[Corpus missing: run build_code_example.py]", SIZE_LEAD, CRITICAL)  # fmt: skip
        return
    before, removed, after, added = code
    width = Inches(8.3)
    bottom = _diff(slide, "Before", before, removed, REMOVED_TINT, CRITICAL, MARGIN,
                   Inches(1.65), width)  # fmt: skip
    _diff(slide, "After", after, added, ADDED_TINT, ADDED, MARGIN, Emu(int(bottom + Inches(0.12))),
          width)  # fmt: skip
    left = Emu(int(MARGIN + width + Inches(0.4)))
    column = Emu(int(WIDTH - MARGIN - left))
    steps = [
        "The outer condition becomes a guard clause with an early return.",
        "The rest of the method moves one level up.",
        "Passed the javac check; judged acceptable as-is in the review.",
    ]
    top = Inches(2.05)
    for index, text in enumerate(steps, 1):
        _badge(slide, left, top, str(index), ADDED if index < 3 else ACCENT)
        _put(_frame(slide, Emu(int(left + Inches(0.5))), top, Emu(int(column - Inches(0.5))),
                    Inches(1.2)), text, SIZE_CAPTION, INK)  # fmt: skip
        top = Emu(int(top + Inches(1.35)))


def _slide_closing(slide, f, heading) -> None:
    _background(slide, NAVY)
    _heading(slide, heading, dark=True)
    width = Emu(int((CONTENT - Inches(0.6)) / 2))
    for index, (title, lines, colour) in enumerate([
        ("Limitations", [
            "Compiles ≠ behaves the same: project tests were not run.",
            "One dataset, four smells, Java only.",
            "Best model chosen on the same predictions: slightly optimistic.",
        ], DANGER_ON_DARK),
        ("Takeaways", [
            "Learned boundaries beat fixed thresholds.",
            "Safe automation is narrow, but measurable.",
            "Open source and reproducible: every number comes from a script.",
        ], ACCENT_ON_DARK),
    ]):  # fmt: skip
        left = Emu(int(MARGIN + index * (width + Inches(0.6))))
        _put(_frame(slide, left, Inches(1.6), width, Inches(0.45)), title, SIZE_LEAD, colour,
             strong=True)  # fmt: skip
        _bullet_list(slide, left, Inches(2.2), width, Inches(2.8), lines, SIZE_LEAD, ON_DARK,
                     colour)  # fmt: skip
    frame = _frame(slide, MARGIN, Inches(5.35), CONTENT, Inches(1.2))
    _put(frame, "Thank you  ·  Questions?", Pt(40), ON_DARK, strong=True)
    _put(frame, REPOSITORY.replace("https://", ""), SIZE_CAPTION, ON_DARK_SOFT, new=True, before=4)


LAYOUTS = [_slide_title, _slide_problem, _slide_system, _slide_data, _slide_results,
           _slide_agreement, _slide_engine, _slide_example, _slide_closing]  # fmt: skip
DARK = {0, len(LAYOUTS) - 1}


def build_deck(f: dict, long: bool) -> tuple[str, list[tuple[str, list[Line]]], list[str]]:
    """Prezantimi; me `long` shënimet mbajnë edhe fjalitë `Extra`.

    Kthen tekstin e plotë të çdo sllajdi kryesor, me shtesat të shënuara, që fleta e
    përgatitjes të llogarisë kohën e të dy versioneve nga i njëjti burim, dhe titujt e
    sllajdeve rezervë me radhë, që udhëzuesi t'i numërojë siç janë në prezantim.
    """
    deck = Presentation()
    deck.slide_width = WIDTH
    deck.slide_height = HEIGHT
    script = [(title, list(parts)) for title, *parts in _script(f)]
    for index, ((_, parts), layout, heading) in enumerate(
        zip(script, LAYOUTS, _headings(f), strict=True)
    ):
        slide = _blank(deck)
        _speech(slide, _spoken(parts, long))
        layout(slide, f, heading)
        if index:
            _footer(slide, index + 1, dark=index in DARK)
    main = len(deck.slides)
    refactoring, smells, detected, pmd = f["refactoring"], f["smells"], f["detected"], f["pmd"]

    # ------------------------------------------------------------------
    # Rezervë: vetëm për pyetjet, nuk thuhen në dhjetë minutat
    # ------------------------------------------------------------------
    backups: list[str] = []

    def backup(title: str, subtitle: str, notes: str):
        slide = _blank(deck)
        backups.append(title)
        _heading(slide, title, subtitle, kicker="Backup · ")
        _note(slide, notes)
        _footer(slide, len(deck.slides))
        return slide

    ml = f["ml"]
    slide = backup("Full detection results", "Precision, recall and MCC for both approaches",
                   "Use when asked for precision or recall per smell.")  # fmt: skip
    _data_table(
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
    )

    intervals = _load("bootstrap_intervals.json")["per_smell"]
    slide = backup("Confidence intervals", "95% bootstrap intervals, resampling whole repositories",
                   "Above zero means the model's advantage is not explained by which projects "
                   "happen to be in the sample.")  # fmt: skip
    _data_table(
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
    )  # fmt: skip

    slide = backup("Every algorithm", "MCC of each classifier, same folds",
                   "If asked whether choosing the best model inflates the result: yes, slightly. "
                   "Even the weakest learning algorithm beats the rules on three of four smells.")  # fmt: skip
    _data_table(
        slide,
        ["Smell", *[MODEL_EN[m] for m in ("logistic", "random_forest", "gradient_boosting")], "Rules (A)"],
        [
            [SMELL_SQ[s]]
            + [f"{ml['per_smell'][s]['models'][m]['mcc']:.3f}"
               for m in ("logistic", "random_forest", "gradient_boosting")]
            + [f"{f['strategy'][s]['mcc']:.3f}"]
            for s in smells
        ],
    )  # fmt: skip

    names = PMD_NAMES
    slide = backup("Comparison with PMD", f"PMD {pmd['pmd_version']} with its default thresholds, same samples",
                   "PMD is never ahead once the confidence interval is considered. PMD has no "
                   "Feature Envy rule.")  # fmt: skip
    _data_table(
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
    )  # fmt: skip

    verify = _load("verify_with_project.json")
    reasons = sorted(refactoring["refused_by_reason"].items(), key=lambda pair: -pair[1])[:3]
    reason_en = {"shape_not_matched": "Code shape does not match the transformation",
                 "control_flow_escapes": "A return, break or continue leaves the block",
                 "not_definitely_assigned": "An input value is not definitely assigned"}  # fmt: skip
    slide = backup("Verification in detail", "Why sites were refused, and what compiling inside the project shows",
                   "Isolated files often cannot compile because their neighbours are missing; "
                   "inside the project many more compile fully.")  # fmt: skip
    _bullet_list(
        slide,
        MARGIN,
        TOP,
        CONTENT,
        Inches(4.6),
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
    )  # fmt: skip

    slide = backup("Extract Method in the interface", "jsoup · NodeTraversor.traverse, preview before any file is touched",
                   "The extracted method is named 'extracted'; choosing a meaningful name is "
                   "left to the developer.")  # fmt: skip
    path = os.path.join(FIGURES, "nderfaqja_rishkrimi.png")
    picture = slide.shapes.add_picture(path, MARGIN, TOP, width=CONTENT)
    picture.line.color.rgb = FRAME
    picture.line.width = Pt(0.75)

    slide = backup("Comparison with the literature", "Madeyski & Lewowski (2023), same MLCQ dataset, DS1",
                   "They used random 5-fold cross-validation and tuned hyperparameters; we "
                   "grouped by repository and did not tune. Our results are in the same range.")  # fmt: skip
    _data_table(
        slide,
        ["Smell", "Rules (A)", "Model (B)", "Madeyski & Lewowski 2023"],
        [[SMELL_SQ[s], f"{f['strategy'][s]['mcc']:.3f}", f"{f['best'][s]['mcc']:.3f}",
          MADEYSKI_2023_DS1[s]] for s in smells],
    )  # fmt: skip

    os.makedirs(OUT_DIR, exist_ok=True)
    path = DECK_LONG if long else DECK
    deck.save(path)
    return path, script[:main], backups


# ----------------------------------------------------------------------
# Fleta e përgatitjes
# ----------------------------------------------------------------------
def _questions(f: dict) -> list[tuple[str, str]]:
    refactoring, quality = f["refactoring"], f["quality"]
    applied, detected = refactoring["applied"], refactoring["detected"]
    reasons = refactoring["refused_by_reason"]
    weakest = f["weakest"]
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


# ----------------------------------------------------------------------
# Ndihmës për dokumentet Word
# ----------------------------------------------------------------------
def _document() -> Document:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = DocPt(11)
    return doc


def _list(doc, lines: list[str]) -> None:
    for line in lines:
        doc.add_paragraph(line, style="List Bullet")


# Gjerësia e shkrimit në një faqe Letter me kufijtë e parazgjedhur të Word-it, dhe sa zë
# përafërsisht një shkronjë Calibri 11 dhe kufiri i brendshëm i një qelize.
TEXT_WIDTH_CM = 16.4
CHAR_CM = 0.21
CELL_PADDING_CM = 0.5


def _grid(doc, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    """Një tabelë, me gjerësi kolonash në centimetra.

    Word-i u jep kolonave gjerësi të barabarta, dhe një kolonë me fjali të gjata ngushtohet
    sa një kolonë me një numër. Pa `widths`, secila kolonë merr së paku vendin e fjalës së
    saj më të gjatë, që asnjë fjalë të mos thyhet në mes, dhe pjesa që mbetet ndahet sipas
    gjatësisë mesatare të tekstit.
    """
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    for cell, text in zip(table.rows[0].cells, headers, strict=True):
        cell.text = text
    for values in rows:
        for cell, text in zip(table.add_row().cells, values, strict=True):
            cell.text = text
    if widths is None:
        columns = list(zip(headers, *rows, strict=True))
        floor = [max(len(word) for text in column for word in text.split() or [""]) * CHAR_CM
                 + CELL_PADDING_CM for column in columns]  # fmt: skip
        weights = [sum(map(len, column)) / len(column) for column in columns]
        spare = max(TEXT_WIDTH_CM - sum(floor), 0.0)
        widths = [low + spare * weight / sum(weights) for low, weight in zip(floor, weights, strict=True)]
    table.autofit = False
    for row in table.rows:
        for cell, width in zip(row.cells, widths, strict=True):
            cell.width = DocCm(width)
    doc.add_paragraph()


def _code(doc, lines: list[str]) -> None:
    """Kod me shkronja me gjerësi të njëtrajtshme, që dhëmbëzimi të mbetet i lexueshëm."""
    for line in lines:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = DocPt(0)
        run = paragraph.add_run(line or " ")
        run.font.name = MONO
        run.font.size = DocPt(9.5)
    doc.add_paragraph()


def _qa(doc, pairs: list[tuple[str, str]]) -> None:
    for question, answer in pairs:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = DocPt(0)
        paragraph.add_run(question).bold = True
        doc.add_paragraph(answer)


# ----------------------------------------------------------------------
# Udhëzuesi i fjalimit
# ----------------------------------------------------------------------
@dataclass
class SlideGuide:
    """Çka i duhet folësit për një sllajd, përtej fjalive që thotë."""

    heading: str
    message: str
    shows: list[str]
    point: list[str]
    keywords: str
    asked: list[tuple[str, str]] = field(default_factory=list)


def _slide_guides(f: dict) -> list[SlideGuide]:
    """Një udhëzim për secilin nga nëntë sllajdet kryesore, me radhën e prezantimit.

    Titujt vijnë nga `_headings`, të njëjtët që vë prezantimi, dhe «Çka shihet» përshkruan
    pamjen që vizatojnë funksionet `_slide_*`: kur ndryshon një sllajd, ndryshon edhe këtu.
    """
    smells, ml = f["smells"], f["ml"]
    titles = _headings(f)
    lowest, highest = min(f["recall"]) * 100, max(f["recall"]) * 100
    pairs = "; ".join(
        f"{SMELL_SQ[s]} {f['strategy'][s]['mcc']:.2f} → {f['best'][s]['mcc']:.2f}" for s in smells
    )
    agree = "; ".join(f"{SMELL_SQ[s]} {f['reviewers'][s]:.2f}" for s in smells)
    winners = "; ".join(
        f"{SMELL_SQ[s]}: {MODEL_EN[ml['per_smell'][s]['best_model']]}" for s in smells
    )
    majority = ml["per_smell"]["feature envy"]["models"]["majority"]["accuracy"]
    applied, detected = f["applied"], f["detected"]
    refused = sum(f["refactoring"]["refused_by_reason"].values())
    extract = f["refactoring"]["applied_by_refactoring"]["ExtractMethod"] / applied
    chance = _dhe([SMELL_SQ[s] for s in f["chance"]])
    moderate = _dhe([SMELL_SQ[s] for s in f["moderate"]])
    quality = f["quality"]
    return [
        SlideGuide(
            heading=titles[0],
            message="Kush je, nga vjen puna, dhe tri gjërat që do të dëgjojnë: si gjenden "
            "erërat, sa saktë, dhe sa mund të ndreqen.",
            shows=[
                "Sfond blu i errët: kështu duken vetëm sllajdi i parë dhe i fundit, që salla ta "
                "ndiejë fillimin dhe mbylljen.",
                "Lart, me shkronja të vogla: emri i konferencës. Në mes: titulli i punimit.",
                f"Poshtë titullit: emrat ({AUTHORS}) dhe UBT. Në fund: seanca dhe data.",
            ],
            point=[
                "Mos e lexo titullin: salla e lexon vetë. Shiko sallën dhe thuaj hyrjen "
                "përmendësh.",
                "Kalo te sllajdi 2 pas fjalisë «…how far we can go in fixing them».",
            ],
            keywords="emri · teza në UBT · gjej / sa saktë / ndreq",
        ),
        SlideGuide(
            heading=titles[1],
            message="Erërat e kodit nuk janë gabime, por e bëjnë çdo ndryshim të shtrenjtë. "
            "Mjetet e sotme përdorin numra fiksë dhe nuk ndreqin, prandaj tri pyetje.",
            shows=[
                "Titulli e thotë problemin në një fjali: erërat e bëjnë çdo ndryshim të "
                "shtrenjtë, dhe mjetet e sotme vetëm i tregojnë. Nëntitulli: janë probleme "
                "ndërtimi, jo gabime.",
                "Tri pika: programi punon, por çdo ndryshim kushton më shumë se ç'duhet; mjetet "
                "përdorin pragje fikse, të përcaktuara mbi kod tjetër; e tregojnë problemin, "
                "por rrallë e ndreqin.",
                "Poshtë, tri karta: tri pyetjet e kërkimit (RQ = research question). RQ1: sa të "
                "sakta janë rregullat e botuara? RQ2: a bën më mirë mësimi makinerik me të "
                "njëjtat metrika? RQ3: a mund të ndreqen automatikisht pa e prishur kompilimin?",
                "Në fund të çdo karte, një rreth me shkronjë: A (gri) rregullat, B (blu) mësimi "
                "makinerik, C (blu) motori. Janë të njëjtat shkronja që shfaqen te sllajdi 3.",
                "Nga sllajdi 4 deri te 8, lart djathtas ka tri etiketa RQ1 · RQ2 · RQ3. Ajo me "
                "blu është pyetja për të cilën flet sllajdi: kjo është harta e prezantimit.",
            ],
            point=[
                "Kur thua fjalitë e para, trego tri pikat me radhë.",
                "Te «So we asked three questions», trego tri kartat nga e majta në të djathtë "
                "dhe ndalu një sekondë te secila.",
            ],
            keywords="punon, por kushton · pragje fikse · nuk ndreqin · tri pyetje",
            asked=[
                ("Çka është saktësisht një erë e kodit?",
                 "Shenjë e një problemi në ndërtimin e kodit që e bën ndryshimin më të shtrenjtë. "
                 "Nuk është gabim. Termin e bënë të njohur Fowler dhe Beck te libri "
                 "«Refactoring» (1999)."),
            ],
        ),
        SlideGuide(
            heading=titles[2],
            message=f"Një mjet, {f['metrics']} metrika, tri qasje: A rregulla, B modele, C një "
            "motor që ndreq dhe çdo ndreqje e kontrollon me javac.",
            shows=[
                "Majtas, rrjedha e mjetit nga lart poshtë: kodi Java → "
                f"{f['metrics']} metrika për çdo klasë e metodë → dy kuti krah për krah, "
                f"A ({f['strategies']} rregulla të botuara) dhe B (mësimi makinerik) → erërat, "
                "secila me kushtet që e shkaktuan → C, motori që rishkruan vetëm atë që "
                "vërteton → kontrolli me javac dhe një patch, pa e prekur origjinalin.",
                "AST është pema e sintaksës: kodi i kthyer në pemë, si analiza gramatikore e një "
                "fjalie. javac është kompajleri i Java-s: programi që e kthen kodin në program "
                "të ekzekutueshëm dhe tregon gabimet.",
                "Djathtas, një copë e zmadhuar e ndërfaqes web gjatë analizës së jsoup-it (një "
                "librari e njohur Java për faqet HTML), shqip: dy gjetje, secila me kushtet e "
                "veta, p.sh. «Rreshtat e kodit të metodës: 53 (problem kur është mbi 30)».",
            ],
            point=[
                "Ndiqe rrjedhën me dorë nga lart poshtë: te «A uses…» kutia A, te «B trains…» "
                "kutia B, te «And C is a refactoring engine» kutia C.",
                "Te «On the right you can see the web interface», trego foton djathtas.",
            ],
            keywords=f"{f['metrics']} metrika · A rregulla · B modele · C ndreqje + javac · "
            "ndërfaqja",
            asked=[
                ("Me çka është ndërtuar?",
                 "Pjesa që analizon është në Python, kodin e lexon parseri tree-sitter, ndërfaqja "
                 "është në React. Punon në kompjuterin tënd, falas, me burim të hapur (licenca "
                 "MIT) dhe me një imazh Docker."),
                ("Pse jo një LLM për ndreqjen?",
                 "Doja rishkrime deterministe, të vërtetueshme dhe falas. Një LLM shkruan kod që "
                 "duket i besueshëm, por nuk i vërteton dot kushtet, dhe rezultati ndryshon nga "
                 "njëri ekzekutim te tjetri."),
            ],
        ),
        SlideGuide(
            heading=titles[3],
            message="Etiketat vijnë nga programues profesionistë (MLCQ), dhe prova bëhet e "
            "drejtë duke i ndarë të dhënat sipas projektit dhe duke përdorur MCC.",
            shows=[
                "Lart djathtas ndizen RQ1 dhe RQ2: ky sllajd tregon si u provuan rregullat dhe "
                "modelet.",
                f"Tre numra të mëdhenj: {f['samples']:,} mostra me etiketë (një mostër është "
                f"një klasë ose një metodë që e ka vlerësuar një njeri), {f['repositories']} "
                "projekte (repository) dhe 4 erëra.",
                f"Poshtë majtas, {ml['folds']} kuti me katrorë: çdo kuti është një grup "
                "projektesh. Katër gri janë «train», ku modeli mëson; e pesta, blu, është "
                "«test», ku provohet. Një projekt ndodhet vetëm në një kuti.",
                f"Poshtë djathtas, kutia «Why MCC, not accuracy»: {majority:.1%} me të kuqe "
                "është saktësia e një detektori që thotë gjithmonë «i pastër» te Feature Envy. "
                "MCC-ja e tij është 0.",
            ],
            point=[
                "Kur thua numrat, trego numrat e mëdhenj, njërin pas tjetrit.",
                "Te «we grouped the data by repository», trego kutitë: «mëson nga këto katër, "
                "provohet te kjo».",
                "Te «simple accuracy would look very good», trego numrin e kuq.",
            ],
            keywords=f"MLCQ · 26 programues · {f['samples']:,} mostra · ndarje sipas projektit "
            "· MCC",
            asked=[
                ("Pse MCC dhe jo saktësia?",
                 f"Te Feature Envy, një detektor që thotë gjithmonë «i pastër» del {majority:.1%} "
                 "i saktë, edhe pse nuk ka mësuar asgjë. MCC i jep 0."),
                ("Si e shmangët rrjedhjen e të dhënave?",
                 f"Me ndarje në {ml['folds']} grupe sipas projektit: asnjë projekt nuk është "
                 "njëkohësisht në mësim dhe në provë."),
            ],
        ),
        SlideGuide(
            heading=titles[4],
            message="Rregullat kanë të drejtë kur alarmojnë, por humbasin shumicën e rasteve; "
            f"modelet janë më të mira te të katër erërat, dhe qartë te {_dhe(f['sure'])}.",
            shows=[
                "Grafik me shtylla. Për çdo erë ka dy shtylla krah për krah: gri janë rregullat "
                "e botuara (A), blu është modeli më i mirë (B).",
                "Numri mbi çdo shtyllë është MCC: 0 do të thotë jo më mirë se hamendja, 1 do të "
                "thotë i përsosur. Sa më e lartë shtylla, aq më mirë.",
                f"Numrat, rregullat → modeli: {pairs}.",
                "Nën emrin e çdo ere: «(significant)» do të thotë që fitorja e modelit është e "
                "sigurt statistikisht; «(could be chance)» do të thotë që mund të jetë rastësi.",
                f"Djathtas, dy numra: {lowest:.0f}–{highest:.0f}% me gri, sa nga erërat e "
                f"vërteta kapin rregullat; {min(f['model_mcc']):.2f}–"
                f"{max(f['model_mcc']):.2f} me blu, MCC-ja e modelit më të mirë.",
            ],
            point=[
                "Te «The gray bars… and the blue bars…», trego një shtyllë gri dhe një blu, që "
                "salla ta lidhë ngjyrën me kuptimin.",
                f"Te «they catch only {lowest:.0f} to {highest:.0f} percent», trego numrin gri "
                "djathtas.",
                f"Te «For {_and(f['unsure'])}, the difference could be chance», trego dy "
                "shtyllat e saj: janë më të ulëtat dhe më afër njëra-tjetrës.",
            ],
            keywords=f"gri = rregullat · blu = modeli · kapin {lowest:.0f}–{highest:.0f}% · "
            f"më mirë te të katërta · {_dhe(f['unsure'])} ndoshta rastësi",
            asked=[
                ("Cili model fitoi për secilën erë?",
                 f"{winners}. Sllajdi rezervë «Every algorithm» i tregon të gjithë."),
                ("Si dihet që nuk është fat?",
                 "I rizgjodhëm projektet rastësisht 2,000 herë dhe e llogaritëm ndryshimin çdo "
                 "herë. Sllajdi rezervë «Confidence intervals»."),
                ("Precision dhe recall për secilën erë?",
                 "Sllajdi rezervë «Full detection results»."),
            ],
        ),
        SlideGuide(
            heading=titles[5],
            message=f"Për {chance} edhe ekspertët nuk pajtohen me njëri-tjetrin; kufiri nuk është "
            "vetëm algoritmi, por vetë përkufizimi i erës.",
            shows=[
                "Grafik me një shtyllë për çdo erë: sa pajtohen dy rishikues njerëzorë që panë "
                "të njëjtin kod, i matur me MCC. Vija e hollë horizontale është zero, pra "
                "hamendja.",
                f"Numrat: {agree}.",
                f"Shtylla e {chance} është e kuqe dhe nën zero: pajtimi është sa me hamendje. "
                f"Për {moderate} pajtimi është mesatar.",
                "Djathtas: i njëjti numër i madh me të kuqe, dhe fjalia kryesore e sllajdit me "
                "shkronja të trasha.",
            ],
            point=[
                f"Te «For {_and([SMELL_SQ[s] for s in f['chance']])}, they agree no better than "
                "chance», trego shtyllën e kuqe.",
                "Fjalinë «If experts do not agree…» thuaje ngadalë, duke parë sallën: është "
                "mesazhi kryesor i pjesës së parë, dhe e ke të shkruar djathtas.",
            ],
            keywords="sa pajtohen njerëzit · Feature Envy sa hamendja · problemi është "
            "përkufizimi",
            asked=[
                ("Si e matët pajtimin?",
                 "Te mostrat që kanë më shumë se një rishikim, krahasuam çdo çift rishikimesh të "
                 "së njëjtës mostër: a thonë të dy «ka erë» apo jo. MCC u llogarit mbi këto "
                 "çifte."),
            ],
        ),
        SlideGuide(
            heading=titles[6],
            message=f"Motori ndreq vetëm kur është i sigurt: rishkruan {applied / detected:.0%} të "
            f"vendeve, refuzon të tjerat me arsye, era zhduket në {f['resolved']:.0%}, dhe asnjë "
            "rishkrim me gabim nuk shkruhet.",
            shows=[
                f"Lart: {detected:,} vende ku mund të zbatohej një ndreqje (një «site» është një "
                "vend konkret në kod).",
                f"Shiriti poshtë tij: pjesa blu janë {applied:,} të rishkruarat "
                f"({_pct(applied / detected)}), pjesa gri janë {refused:,} të refuzuarat "
                f"({_pct(refused / detected)}). Gjatësia e secilës pjese është sa pjesa e saj.",
                f"Tri kartat «Of the {applied:,} rewrites»: {_pct(f['resolved'])} e hoqën erën; "
                f"{_pct(f['broken'])} shtuan një lloj të ri gabimi kompilimi dhe nuk shkruhen "
                f"kurrë; {_pct(quality['acceptable_reweighted'])} ishin të pranueshme në "
                f"rishikimin me dorë të {quality['reviewed']} rishkrimeve.",
                "Tri ndreqjet, në nëntitull. Extract Method: një pjesë e metodës së gjatë kalon "
                "në një metodë të re. Guard Clauses: if-i i madh që mbështjell gjithë metodën "
                "bëhet dalje e hershme. Introduce Parameter Object: shumë parametra mblidhen në "
                "një objekt.",
            ],
            point=[
                "Te «it found … sites and rewrote …», trego numrin e madh, pastaj pjesën blu të "
                "shiritit.",
                "Te «The rest were refused», trego pjesën gri. Te «For us, refusing is a correct "
                "result», mos lëviz: thuaje duke parë sallën.",
                "Te tri numrat e fundit, trego tri kartat me radhë.",
            ],
            keywords=f"tri ndreqje · {detected:,} → {applied:,} · refuzimi është i saktë · "
            f"era zhduket {f['resolved']:.0%} · gabimet nuk shkruhen · "
            f"{quality['acceptable_reweighted']:.0%} të pranueshme",
            asked=[
                ("Si e dini që sjellja nuk ndryshon?",
                 "Nuk e pretendojmë. Vërtetojmë kushtet në pemën e sintaksës dhe kontrollojmë me "
                 "kompajlerin. Testet e projekteve nuk u ekzekutuan, sepse korpusi nuk ka "
                 "skedarë ndërtimi."),
                (f"Pse vetëm {applied / detected:.0%}?",
                 "Motori refuzon kur nuk vërteton dot një kusht. Sllajdi rezervë «Verification "
                 "in detail» i tregon arsyet."),
                ("Çka do të thotë «të peshuara»?",
                 f"Extract Method përbën {extract:.0%} të rishkrimeve, ndaj përqindja e "
                 "përgjithshme peshohet sipas sa i shpeshtë është secili lloj."),
                ("Si duket kjo në ndërfaqe?", "Sllajdi rezervë «Extract Method in the interface»."),
            ],
        ),
        SlideGuide(
            heading=titles[7],
            message="Një shembull i vërtetë: if-i i madh bëhet dalje e hershme, kodi ngjitet një "
            "nivel lart, kompilohet dhe është i pranueshëm.",
            shows=[
                "Lart, «Before»: kodi origjinal nga Apache Geode, metoda "
                "checkForLimitedOrNoAccess. Rreshtat në brez të kuq janë ata që ndryshojnë: if-i "
                "i jashtëm dhe kllapa e tij e fundit.",
                "Poshtë, «After»: kodi pas rishkrimit. Rreshtat në brez të gjelbër janë të rinj: "
                "kushti me «!( … )» dhe «return;».",
                "Komenti «/* … unchanged lines */» do të thotë që një pjesë e gjatë që nuk "
                "ndryshon është mbledhur në një rresht, që kodi të lexohet nga salla.",
                "Djathtas, tri hapa me numër: kushti bëhet dalje e hershme; pjesa tjetër ngjitet "
                "një nivel; e kaloi javac dhe u gjykua e pranueshme.",
            ],
            point=[
                "Te «Before…», trego brezin e kuq lart.",
                "Te «After…», trego brezin e gjelbër poshtë, pastaj hapat djathtas.",
            ],
            keywords="Apache Geode · if i madh → dalje e hershme · një nivel lart · kompilohet",
            asked=[
                ("Pse !( … ) dhe jo kushti i kthyer së prapthi?",
                 "Mbështjellja është mekanike dhe e saktë për çdo kusht, edhe për numrat me presje "
                 "(NaN), ku a > b dhe a <= b mund të jenë të dy të rremë. Kthimi me dorë i një "
                 "kushti të përbërë sjell lehtë gabime."),
            ],
        ),
        SlideGuide(
            heading=titles[8],
            message="Kufizimet i thua vetë, para se të pyesin. Pastaj mbyll me dy mesazhe: "
            "kufijtë e mësuar i mundin pragjet fikse, dhe ndreqja e sigurt është e mundshme, por "
            "e ngushtë.",
            shows=[
                "Sfond blu i errët, si sllajdi i parë: salla e kupton që po mbyll.",
                "Majtas, me të kuqe, «Limitations»: kompilohet ≠ sillet njësoj (testet e "
                "projekteve nuk u ekzekutuan); një bazë të dhënash, katër erëra, vetëm Java; "
                "modeli më i mirë u zgjodh mbi të njëjtat parashikime, ndaj është pak optimist.",
                "Djathtas, me blu të çelët, «Takeaways», mesazhet që merr salla me vete: kufijtë "
                "e mësuar i mundin pragjet fikse; automatizimi i sigurt është i ngushtë, por i "
                "matshëm; burim i hapur dhe i riprodhueshëm.",
                "Poshtë: «Thank you · Questions?» dhe adresa e projektit në GitHub.",
            ],
            point=[
                "Trego kolonën e kuqe kur flet për kufizimet, pastaj kolonën blu te «To "
                "summarize».",
                "Pas «I am happy to take your questions», ndalu, buzëqesh dhe prit. Mos e mbyll "
                "sllajdin: adresa e GitHub-it duhet të mbetet në ekran.",
            ],
            keywords="kompilohet ≠ sillet njësoj · një bazë, katër erëra, Java · kufijtë e "
            "mësuar · e sigurt, por e ngushtë · faleminderit",
            asked=[
                ("Çka do të bëje më pas?",
                 "Do t'i ekzekutoja testet e projekteve pas çdo rishkrimi, do të shtoja një "
                 "zgjidhës të vogël emrash për më shumë ndreqje, dhe do t'u kërkoja rishikuesve "
                 "të pavarur t'i gjykojnë rishkrimet."),
            ],
        ),
    ]  # fmt: skip


def _backup_guides(f: dict) -> dict[str, tuple[str, str]]:
    """Për çdo sllajd rezervë: çka tregon dhe kur hapet."""
    return {
        "Full detection results": (
            "Tabelë: për çdo erë precision (P), recall (R) dhe MCC, për rregullat dhe për "
            "modelin më të mirë.",
            "Kur pyesin për precision ose recall.",
        ),
        "Confidence intervals": (
            "Intervalet 95% për rregullat, për modelin dhe për ndryshimin B − A. Kolona «Above "
            "zero» thotë nëse ndryshimi është i sigurt.",
            "Kur pyesin «si e dini që nuk është fat?».",
        ),
        "Every algorithm": (
            "MCC i çdo algoritmi (logistic regression, random forest, gradient boosting) "
            "krahas rregullave.",
            "Kur pyesin nëse zgjedhja e modelit më të mirë e fryn rezultatin: edhe algoritmi më "
            f"i dobët i mund rregullat te {f['weakest']} nga {len(f['smells'])} erërat.",
        ),
        "Comparison with PMD": (
            f"PMD {f['pmd']['pmd_version']}, me pragjet e veta, mbi të njëjtat mostra: MCC i "
            "PMD-së, MCC ynë dhe intervali i ndryshimit.",
            "Kur pyesin si krahasohet me mjetet ekzistuese.",
        ),
        "Verification in detail": (
            "Arsyet kryesore të refuzimit me numra, kompilimi brenda projektit, dhe erërat e "
            "reja pas rishkrimit.",
            "Kur pyesin pse u rishkrua kaq pak, ose çka do të thotë «kompilohet».",
        ),
        "Extract Method in the interface": (
            "Foto e ndërfaqes që tregon një Extract Method te jsoup, para se të preket ndonjë "
            "skedar.",
            "Kur pyesin si duket mjeti ose si e përdor një programues.",
        ),
        "Comparison with the literature": (
            "Rezultatet tuaja krahas Madeyski & Lewowski (2023), mbi të njëjtën bazë MLCQ.",
            "Kur pyesin si krahasohet me punë të tjera.",
        ),
    }


def _say(doc, line: Line) -> None:
    """Fjalia angleze që thuhet, dhe poshtë saj kuptimi shqip që nuk thuhet."""
    extra = isinstance(line, Extra)
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = DocPt(0)
    if extra:
        mark = paragraph.add_run("+ ")
        mark.bold = True
        mark.font.color.rgb = DocRGB(*ADDED)
    run = paragraph.add_run(str(line))
    run.font.size = DocPt(12)
    if extra:
        run.italic = True
        run.font.color.rgb = DocRGB(*ADDED)
    meaning = doc.add_paragraph()
    meaning.paragraph_format.left_indent = DocPt(18)
    meaning.paragraph_format.space_after = DocPt(8)
    run = meaning.add_run(line.sq)
    run.italic = True
    run.font.size = DocPt(10)
    run.font.color.rgb = DocRGB(*SOFT)


def build_speech_guide(f: dict, script: list[tuple[str, list[Line]]], backups: list[str]) -> str:
    """Çka të thuhet dhe ku të tregohet, sllajd për sllajd.

    Sllajdet janë të rralla me tekst me qëllim, që salla të dëgjojë e jo të lexojë; ky
    dokument është gjysma tjetër: ai i shpjegon folësit çdo element dhe i jep kuptimin e
    çdo fjalie që thotë.
    """
    guides = _slide_guides(f)
    doc = _document()
    doc.add_heading("Çka të flas: prezantimi sllajd për sllajd", level=0)
    doc.add_paragraph(f"{TITLE}\n{AUTHORS}")
    doc.add_paragraph(
        "E shtunë, 24 tetor 2026 · Session 1 – Software Engineering · salla I-302 · "
        "prezantimi i 14-të nga 17."
    )

    doc.add_heading("Si ta përdorësh këtë dokument", level=1)
    _list(doc, [
        "Për çdo sllajd ke: mesazhin në një fjali, çka shihet në sllajd, ku të tregosh, "
        "çka thua, fjalët kyçe dhe pyetjet e mundshme.",
        "Te «Çka thua», fjalia me të zeza është ajo që e thua në anglisht. Poshtë saj, me gri, "
        "është kuptimi në shqip: atë nuk e thua, është që ta dish çka po thua.",
        "Fjalitë me të gjelbër dhe me «+» para thuhen vetëm në versionin 9-minutësh. Pa to "
        "mbetet saktësisht versioni i shkurtër.",
        "Mos e mëso përmendësh çdo fjali. Mëso mesazhin e çdo sllajdi dhe fjalët kyçe, dhe "
        "vetëm hyrjen e mbylljen fjalë për fjalë (në fund të dokumentit).",
        "Lexoje një herë të gjithin me zë, me sllajdet hapur pranë, dhe trego me gisht atë që "
        "thotë «Ku të tregosh».",
        "Lart djathtas, nga sllajdi 4 te 8, etiketat RQ1 · RQ2 · RQ3 tregojnë për cilën pyetje "
        "flet sllajdi; ajo me blu është pyetja e tanishme. Nuk ke nevojë ta thuash: salla e "
        "sheh vetë.",
    ])  # fmt: skip

    doc.add_heading("Historia e prezantimit në një faqe", level=1)
    doc.add_paragraph(
        "Prezantimi është një histori me tri pjesë: problemi (1–2), çka ndërtove dhe si e "
        "provove (3–4), çka gjete (5–8), dhe kufijtë (9). Nëse e kupton këtë tabelë, e di "
        "prezantimin."
    )
    rows, totals = [], {False: 0, True: 0}
    for index, ((_, parts), guide) in enumerate(zip(script, guides, strict=True), 1):
        cells = [str(index), guide.heading if index > 1 else "Titulli", guide.message]
        for long in (False, True):
            totals[long] += _word_count(_spoken(parts, long))
            cells.append(_clock(round(totals[long] / WORDS_PER_MINUTE * 60)))
        rows.append(cells)
    _grid(doc, ["#", "Sllajdi", "Mesazhi", "Shkurt: deri këtu", "9 min: deri këtu"], rows,
          widths=[0.8, 5.0, 7.0, 1.8, 1.8])  # fmt: skip

    doc.add_heading("Para se të fillosh", level=1)
    verification = len(script) + 1 + backups.index("Verification in detail")
    _list(doc, [
        "Nise prezantimin me pamjen e folësit: Alt+F5, ose Slide Show → Presenter View. Salla "
        "sheh sllajdin; ti sheh edhe shënimet dhe sllajdin e radhës.",
        "Përpara: shigjeta djathtas, hapësira ose klikuesi. Prapa: shigjeta majtas.",
        f"Për të hapur një sllajd rezervë, shtyp numrin e tij dhe Enter (p.sh. "
        f"{', '.join(str(verification))}, Enter për sllajdin {verification}). Për t'u kthyer "
        f"te mbyllja: {len(script)}, Enter.",
        "Qëndro anash ekranit, jo para tij, me trup nga salla. Trego me dorë ose me laser, "
        "pastaj kthehu nga salla para se të flasësh.",
        "Shënimet në PowerPoint janë rrjetë sigurie: shiko fjalët kyçe, jo gjithë tekstin.",
    ])  # fmt: skip

    for index, ((_, parts), guide) in enumerate(zip(script, guides, strict=True), 1):
        doc.add_page_break()
        doc.add_heading(f"Sllajdi {index} · {guide.heading}", level=1)
        paragraph = doc.add_paragraph()
        paragraph.add_run("Mesazhi: ").bold = True
        paragraph.add_run(guide.message)
        short, full = (round(_word_count(_spoken(parts, long)) / WORDS_PER_MINUTE * 60)
                       for long in (False, True))  # fmt: skip
        doc.add_paragraph(f"Koha: rreth {short} sekonda në versionin e shkurtër, {full} në atë "
                          "9-minutësh.")  # fmt: skip
        doc.add_heading("Çka shihet në sllajd", level=2)
        _list(doc, guide.shows)
        doc.add_heading("Ku të tregosh", level=2)
        _list(doc, guide.point)
        doc.add_heading("Çka thua", level=2)
        for line in parts:
            _say(doc, line)
        doc.add_heading("Nëse të ngec mendja", level=2)
        doc.add_paragraph(guide.keywords)
        if guide.asked:
            doc.add_heading("Nëse të pyesin për këtë sllajd", level=2)
            _qa(doc, guide.asked)

    doc.add_page_break()
    doc.add_heading("Sllajdet rezervë: vetëm për pyetjet", level=1)
    doc.add_paragraph(
        "Këto nuk i tregon gjatë prezantimit. I hap vetëm kur një pyetje i kërkon: shtyp "
        "numrin dhe Enter, përgjigju, pastaj kthehu te sllajdi i fundit."
    )
    explained = _backup_guides(f)
    for offset, title in enumerate(backups, len(script) + 1):
        shows, when = explained[title]
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = DocPt(0)
        paragraph.add_run(f"Sllajdi {offset} · {title}").bold = True
        doc.add_paragraph(shows)
        paragraph = doc.add_paragraph()
        paragraph.add_run("Kur e hap: ").italic = True
        paragraph.add_run(when)

    doc.add_heading("Hyrja dhe mbyllja, përmendësh", level=1)
    doc.add_paragraph(
        "Këto janë fjalitë e vetme që ia vlen t'i mësosh fjalë për fjalë: fillimi i sigurt e "
        "qetëson zërin, dhe mbyllja e sigurt lë përshtypjen e fundit."
    )
    for line in script[0][1][:2] + script[-1][1][-3:]:
        _say(doc, line)

    doc.save(SPEECH)
    return SPEECH


# ----------------------------------------------------------------------
# Dokumenti i njohurive
# ----------------------------------------------------------------------
REASON_SQ = {
    "shape_not_matched": "Kodi nuk ka formën që i duhet ndreqjes, p.sh. metoda nuk është e "
    "gjitha një if.",
    "control_flow_escapes": "Një return, break ose continue del jashtë pjesës që do të "
    "nxirrej: në metodën e re do të kishte kuptim tjetër.",
    "not_definitely_assigned": "Pjesa e nxjerrë lexon një variabël që mund të mos ketë marrë "
    "vlerë në çdo rrugë.",
    "multiple_outputs": "Pjesa ndryshon më shumë se një variabël që përdoret më pas, ndërsa "
    "një metodë Java kthen vetëm një vlerë.",
    "ambiguous_overload": "Ka disa metoda me të njëjtin emër, dhe nga pema nuk dihet cila "
    "thirret.",
    "unresolved_name": "Një emër në kod nuk zgjidhet dot pa e njohur gjithë projektin.",
    "possible_side_effect": "Një shprehje mund të ndryshojë diçka jashtë saj, dhe zhvendosja "
    "do ta ndryshonte radhën.",
}

VERDICT_SQ = {
    "compiles": "kompilohet plotësisht",
    "no_new_errors": "nuk shton asnjë lloj të ri gabimi; skedari nuk kompilohej as më parë, "
    "sepse i mungojnë fqinjët",
    "new_errors": "shton një lloj të ri gabimi, ndaj nuk shkruhet kurrë",
    "parses": "javac nuk u arrit dot, ndaj u kontrollua vetëm sintaksa",
}

TERMS = [
    ("code smell", "erë e kodit", "Shenjë se kodi është ndërtuar në një mënyrë që e bën të "
     "vështirë për t'u ndryshuar. Nuk është gabim."),
    ("refactoring", "refaktorim, ndreqje", "Ndryshim i strukturës së kodit pa ia ndryshuar "
     "sjelljen."),
    ("metric", "metrikë", "Një numër që përshkruan kodin: rreshta, kompleksitet, lidhje."),
    ("threshold", "prag", "Vlera mbi ose nën të cilën një metrikë konsiderohet problem."),
    ("detection strategy", "rregull gjetjeje", "Disa kushte mbi metrika, të lidhura me DHE/OSE."),
    ("label", "etiketë", "Përgjigjja e njeriut: kjo mostër ka erë apo jo."),
    ("sample", "mostër", "Një klasë ose metodë e vlerësuar nga një njeri."),
    ("repository", "projekt, depo", "Dosja e një projekti, zakonisht në GitHub."),
    ("corpus", "korpus", "Të gjitha projektet e shkarkuara mbi të cilat punon mjeti."),
    ("parser", "parser", "Programi që e lexon tekstin e kodit dhe e kthen në pemë."),
    ("AST, syntax tree", "pema e sintaksës", "Kodi i paraqitur si pemë, si analiza "
     "gramatikore e një fjalie."),
    ("compiler, javac", "kompajler", "Programi që e kthen kodin Java në program dhe tregon "
     "gabimet."),
    ("precondition", "kusht paraprak", "Kushti që duhet vërtetuar para se një ndreqje të jetë "
     "e sigurt."),
    ("refusal", "refuzim", "Motori nuk ndreq, dhe thotë pse. Rezultat i saktë, jo dështim."),
    ("patch", "skedari i ndryshimeve", "Skedar që tregon çdo rresht që hiqet dhe shtohet, pa e "
     "prekur kodin."),
    ("classifier, model", "model", "Program që mëson nga shembuj dhe jep përgjigje për raste "
     "të reja."),
    ("baseline", "pikë krahasimi", "Zgjidhja më e thjeshtë që çdo model duhet ta kalojë."),
    ("confusion matrix", "matrica e konfuzionit", "Tabela 2 × 2 e përgjigjeve të sakta dhe të "
     "gabuara."),
    ("precision", "sa shpesh ka të drejtë", "Kur thotë «ka erë», sa herë ka vërtet."),
    ("recall", "sa nga problemet gjen", "Nga erërat e vërteta, sa i gjen."),
    ("F1", "nota e përbashkët", "Një notë që bashkon precision dhe recall."),
    ("MCC", "nota e saktësisë", "Nga −1 deri në 1; 0 = sa hamendja. Nuk mashtrohet kur "
     "shumica e kodit është e pastër."),
    ("data leakage", "rrjedhje e të dhënave", "Kur modeli provohet mbi diçka që e ka parë gjatë "
     "mësimit."),
    ("fold, cross-validation", "grup, provë e kryqëzuar", "Të dhënat ndahen në grupe; mëson nga "
     "të tjerat, provohet te njëri, me radhë."),
    ("bootstrap", "rizgjedhje", "Rizgjedhja e rastësishme me kthim, shumë herë, për të parë sa "
     "lëviz rezultati."),
    ("confidence interval", "interval besimi", "Kufijtë brenda të cilëve ndodhet vlera e vërtetë "
     "me 95% siguri."),
    ("inter-rater agreement", "pajtimi i rishikuesve", "Sa pajtohen dy njerëz që vlerësojnë të "
     "njëjtën gjë."),
    ("seed", "farë", "Numri nga i cili nisin numrat e rastit; i njëjti numër jep të njëjtin "
     "rezultat."),
    ("severity", "rëndësia", "Sa e rëndë është era: minor, major, critical."),
    ("open source", "burim i hapur", "Kodi është publik dhe mund ta përdorë kushdo."),
]  # fmt: skip

SOURCES = [
    "Fowler, M. (1999; 2nd ed. 2018). Refactoring: Improving the Design of Existing Code. "
    "Addison-Wesley. Erërat e kodit dhe refaktorimet.",
    "Lanza, M. & Marinescu, R. (2006). Object-Oriented Metrics in Practice. Springer. "
    "Rregullat e gjetjes dhe pragjet.",
    "Chidamber, S. R. & Kemerer, C. F. (1994). A Metrics Suite for Object Oriented Design. "
    "IEEE TSE. WMC, CBO, DIT, NOC, RFC, LCOM.",
    "McCabe, T. J. (1976). A Complexity Measure. IEEE TSE. Kompleksiteti ciklomatik (CC).",
    "Bieman, J. M. & Kang, B.-K. (1995). Cohesion and Reuse in an Object-Oriented System. "
    "TCC.",
    "Madeyski, L. & Lewowski, T. (2020). MLCQ: Industry-Relevant Code Smell Data Set. Baza e "
    "të dhënave.",
    "Madeyski, L. & Lewowski, T. (2023), mbi të njëjtën bazë MLCQ. Krahasimi me literaturën.",
]


def _metric_name(feature: str) -> str:
    """`c_CLOC` → `CLOC (Rreshtat e kodit të klasës)`: prefiksi thotë vetëm nivelin."""
    name = feature.split("_", 1)[1] if feature[:2] in ("c_", "m_") else feature
    entry = glossary.metric(name)
    return f"{name} ({entry['name'].lower()})" if entry else name


def build_knowledge(f: dict) -> str:
    """Punimi i shpjeguar nga e para, për dikë që nuk e njeh temën.

    Çdo shifër lexohet nga `data/results/` si te sllajdet, dhe çdo term i mjetit merr
    emrin dhe shpjegimin nga fjalori i thjeshtë i sistemit, që dokumenti, ndërfaqja dhe
    CLI-ja të mos e shpjegojnë të njëjtën gjë në tri mënyra.
    """
    smells, ml = f["smells"], f["ml"]
    reference, dataset, pmd = f["reference"], f["dataset"], f["pmd"]
    refactoring, quality = f["refactoring"], f["quality"]
    applied, detected = f["applied"], f["detected"]
    vocab = glossary.vocabulary()
    intervals = _load("bootstrap_intervals.json")["per_smell"]
    verify = _load("verify_with_project.json")
    blob, envy = f["strategy"]["blob"], f["strategy"]["feature envy"]
    envy_total = envy["tp"] + envy["fp"] + envy["tn"] + envy["fn"]
    majority = ml["per_smell"]["feature envy"]["models"]["majority"]["accuracy"]
    precision = [f["strategy"][s]["precision"] for s in smells]
    lowest, highest = min(f["recall"]) * 100, max(f["recall"]) * 100
    resamples = intervals[smells[0]]["intervals"]["difference_model_minus_rules"]["resamples_used"]
    q = reference["quantifiers"]
    by_type = refactoring["applied_by_refactoring"]
    refused = sum(refactoring["refused_by_reason"].values())

    doc = _document()
    doc.add_heading("Gjithçka për punimin: udhëzues nga e para", level=0)
    doc.add_paragraph(f"{TITLE}\n{AUTHORS}")
    doc.add_paragraph(
        "Ky dokument e shpjegon punimin për dikë që nuk e njeh temën. Lexoje me radhë: çdo "
        "pjesë mbështetet te ajo para saj. Çdo shifër vjen nga `data/results/`, njësoj si te "
        "sllajdet, ndaj nuk ka mospërputhje mes tyre."
    )

    # --- 1 ---
    doc.add_heading("1. Punimi në një paragraf", level=1)
    doc.add_paragraph(
        f"Punimi ndërton JavaSmell, një mjet që lexon kod Java, mat {f['metrics']} metrika për "
        "çdo klasë dhe metodë, dhe i gjen erërat e kodit në tri mënyra. A: "
        f"{f['strategies']} rregulla të botuara, kryesisht nga Lanza & Marinescu. B: modele të "
        "mësimit makinerik, të trajnuara mbi të njëjtat metrika. C: një motor që disa erëra i "
        "ndreq vetë duke e rishkruar kodin, por vetëm kur mund ta vërtetojë që rishkrimi është "
        "i sigurt, dhe çdo rishkrim e kontrollon me kompajlerin e Java-s. A dhe B krahasohen me "
        f"vlerësimet e programuesve profesionistë nga baza MLCQ, mbi {f['samples']:,} mostra."
    )
    doc.add_heading("Nëse të pyesin në korridor (në anglisht)", level=2)
    doc.add_paragraph(
        "I built a tool that finds design problems, called code smells, in Java code. I "
        "compared published rules with machine learning, using labels from professional "
        "developers: the models are better, but some smells are hard even for humans to agree "
        "on. The tool also fixes some smells automatically, but only when it can prove the "
        "change is safe, and it checks every change with the Java compiler."
    )

    # --- 2 ---
    doc.add_heading("2. Tri pyetjet e kërkimit dhe përgjigjet", level=1)
    _grid(doc, ["Pyetja", "Përgjigjja e shkurtër"], [
        ["RQ1. Sa të sakta janë rregullat e botuara?",
         f"Kanë të drejtë kur alarmojnë (precision {min(precision):.0%}–{max(precision):.0%}), "
         f"por kapin vetëm {lowest:.0f}–{highest:.0f}% të erërave. MCC "
         f"{min(f['rule_mcc']):.2f}–{max(f['rule_mcc']):.2f}."],
        ["RQ2. A bën më mirë mësimi makinerik me të njëjtat metrika?",
         f"Po, te të katër erërat (MCC {min(f['model_mcc']):.2f}–{max(f['model_mcc']):.2f}). "
         f"Dallimi është i sigurt te {_dhe(f['sure'])}; te {_dhe(f['unsure'])} mund të jetë "
         "rastësi."],
        ["RQ3. A mund të ndreqen erërat automatikisht pa e prishur kompilimin?",
         f"Po, por për pak raste: {applied:,} nga {detected:,} vende ({_pct(applied / detected)}). "
         f"Era zhduket në {_pct(f['resolved'])}; {_pct(f['broken'])} shtojnë një gabim të ri "
         "kompilimi dhe nuk shkruhen; "
         f"{_pct(quality['acceptable_reweighted'])} janë të pranueshme në rishikimin me dorë."],
    ])  # fmt: skip

    # --- 3 ---
    doc.add_heading("3. Bazat: pesë fjalë Java", level=1)
    _code(doc, [
        "class BankAccount {                   // KLASË: një «dosje» me të dhëna dhe veprime",
        "    private double balance;           // FUSHË: një e dhënë brenda klasës",
        "",
        "    void deposit(double amount) {     // METODË: një veprim; amount është PARAMETËR",
        "        balance += amount;",
        "    }",
        "}",
    ])  # fmt: skip
    _list(doc, [
        "Klasa është si një formular me rubrikat e veta (fushat) dhe butonat e vet (metodat).",
        "Metoda merr hyrje (parametrat), bën diçka dhe ndonjëherë kthen një vlerë (return). "
        "Një metodë «void» nuk kthen vlerë.",
        "Një projekt (repository) është një dosje me qindra klasa, zakonisht në GitHub.",
    ])  # fmt: skip

    # --- 4 ---
    doc.add_heading("4. Erërat e kodit", level=1)
    doc.add_paragraph(
        "Mendo për një frigorifer që mban erë: era nuk vërteton që diçka është prishur, por të "
        "thotë «shiko këtu». Njësoj, një erë e kodit nuk është gabim, sepse programi punon. "
        "Është shenjë që kodi është ndërtuar në një mënyrë që e bën çdo ndryshim të ardhshëm më "
        "të shtrenjtë. Termin e bënë të njohur Kent Beck dhe Martin Fowler te «Refactoring» "
        "(1999)."
    )
    mlcq = {"GodClass", "DataClass", "FeatureEnvy", "LongMethod"}
    _grid(doc, ["Era", "Emri i thjeshtë", "Çka është", "Pse ka rëndësi", "Në MLCQ?"], [
        [_words(name), entry["name"], entry["what"], entry["why"], "po" if name in mlcq else "jo"]
        for name, entry in vocab["smells"].items()
    ])  # fmt: skip
    doc.add_paragraph(
        f"Mjeti gjen {f['strategies']} erëra. Me njerëz mund të vlerësohen vetëm katër, sepse "
        "vetëm ato kanë etiketa në MLCQ. «Blob» në MLCQ është e njëjta erë që Lanza & "
        "Marinescu e quajnë «God Class»."
    )
    _list(doc, [
        "Blob: një punonjës që bën punën e gjithë zyrës.",
        "Data Class: një formular i plotësuar, me të cilin punojnë vetëm të tjerët.",
        "Long Method: një recetë tri faqe pa asnjë nëntitull.",
        "Feature Envy: një kuzhinier që gatuan gjithmonë në kuzhinën e fqinjit; ndoshta i "
        "takon atje.",
    ])  # fmt: skip

    # --- 5 ---
    doc.add_heading("5. Refaktorimi", level=1)
    doc.add_paragraph(
        "Refaktorimi e ndryshon strukturën e kodit pa ia ndryshuar sjelljen, si kur rregullon "
        "dollapin: rrobat janë po ato, vetëm i gjen më shpejt. Rregulli i artë: për çdo hyrje, "
        "programi duhet të japë saktësisht të njëjtin rezultat si më parë."
    )
    automated = [s for s in reference["strategies"] if s["automated"]]
    advisory = [s for s in reference["strategies"] if not s["automated"]]
    _grid(doc, ["Ndreqja", "Emri i thjeshtë", "Çka bën", "E zbaton mjeti vetë?"], [
        [_words(name), entry["name"], entry["what"],
         "po" if name in {s["automated"] for s in automated} else "vetëm e propozon"]
        for name, entry in vocab["refactorings"].items()
    ])  # fmt: skip
    doc.add_paragraph(
        "Pse disa ndreqje vetëm propozohen: për "
        + _dhe([_words(s["smell"]) for s in advisory])
        + ", ndreqja do të duhej të zhvendoste metoda ose të ndryshonte fusha, pra të gjente "
        "çdo vend ku ato përdoren. Analiza jonë i njeh faktet e sintaksës, jo kuptimin e çdo "
        "emri në gjithë projektin, ndaj nuk mund t'i gjejë me siguri të gjitha këto vende."
    )

    # --- 6 ---
    doc.add_heading("6. Metrikat", level=1)
    doc.add_paragraph(
        "Një metrikë është një numër që përshkruan kodin, si presioni dhe pesha te mjeku: një "
        "numër i vetëm nuk jep diagnozë, por disa bashkë po. Mjeti mat "
        f"{len(reference['metrics']['class'])} metrika për klasat dhe "
        f"{len(reference['metrics']['method'])} për metodat. Parseri e lexon çdo klasë një herë "
        "dhe mbledh faktet; të gjitha metrikat llogariten nga këto fakte."
    )
    for level, title in (("class", "Metrikat e klasës"), ("method", "Metrikat e metodës")):
        doc.add_heading(title, level=2)
        _grid(doc, ["Shkurtesa", "Emri", "Çka mat"], [
            [name, vocab["metrics"][name]["name"], vocab["metrics"][name]["what"]]
            for name in reference["metrics"][level]
        ])  # fmt: skip
    doc.add_paragraph(
        "Burimet: Chidamber & Kemerer (1994) për WMC, CBO, DIT, NOC, RFC dhe LCOM; McCabe "
        "(1976) për kompleksitetin ciklomatik; Bieman & Kang (1995) për TCC; Lanza & Marinescu "
        "(2006) për metrikat e rregullave të tyre."
    )

    # --- 7 ---
    doc.add_heading("7. Qasja A: rregullat", level=1)
    doc.add_paragraph(
        "Një rregull gjetjeje është një kombinim kushtesh mbi metrika, me pragje. Shumica vijnë "
        "nga Lanza & Marinescu (2006). Kur të gjitha kushtet plotësohen, kodi shënohet."
    )
    _grid(doc, ["Era", "Rregulli", "Burimi"], [
        [_words(s["smell"]), s["formula"], s["title"]] for s in reference["strategies"]
    ])  # fmt: skip
    doc.add_paragraph(
        "Fjalët e mëdha në rregulla janë emra për vlerat më poshtë; te rregullat e klasës, HIGH "
        "dhe VERY_HIGH janë HIGH_WMC dhe VERY_HIGH_WMC. Burimi i secilës vlerë është shënuar "
        "pranë saj te backend/javasmell/detectors/thresholds.py."
    )
    _grid(doc, ["Emri", "Vlera"], [
        [name, f"{value:.2f}" if isinstance(value, float) and value != int(value) else f"{value:g}"]
        for name, value in q.items()
    ])  # fmt: skip
    doc.add_paragraph(
        f"Shembull me fjalë: God Class do të thotë WMC ≥ {q['VERY_HIGH_WMC']}, TCC < 1/3 dhe "
        f"ATFD > {q['FEW']}. Pra klasa bën shumë punë, pjesët e saj nuk lidhen me njëra-tjetrën, "
        "dhe merr shumë të dhëna nga klasat e tjera."
    )
    doc.add_heading("Mjeti thotë edhe pse", level=2)
    doc.add_paragraph(
        "Një detektor nuk kthen vetëm «po» ose «jo», por kushtet që kontrolloi, p.sh. «WMC = 63 "
        "(≥ 47)». Kështu ndërfaqja shpjegon pse, punimi tregon cili kusht e shkaktoi gjetjen, "
        "dhe rëndësia matet nga sa larg pragut është vlera."
    )
    t = reference["thresholds"]
    doc.add_heading("Rëndësia: minor, major, critical", level=2)
    doc.add_paragraph(
        "Për çdo kusht llogaritet sa herë e kalon vlera pragun, si raport. Merret mesatarja e "
        f"këtyre raporteve (secili me tavan {t['excess_cap']:g}, që një vlerë e vetme ekstreme "
        f"të mos e bëjë gjithçka critical). Nën {t['severity_major']:g} është minor, nën "
        f"{t['severity_critical']:g} major, dhe ndryshe critical. Shembull: një metodë me 60 "
        f"rreshta, me prag {t['long_method_loc']:g}, ka raport 2.0, pra major. Shkalla është e "
        "njëjtë me atë të MLCQ-së, që rezultatet të krahasohen pa përkthim."
    )
    doc.add_heading("Vlerat pa burim të botuar", level=2)
    doc.add_paragraph(
        f"Katër pragje nuk kanë burim të botuar: {t['long_method_loc']:g} rreshta për Long "
        f"Method, CC {t['brain_method_cc']:g} dhe thellësia {t['brain_method_nesting']:g} për "
        f"Brain Method, dhe thellësia {t['deep_nesting']:g} për Deep Nesting. Edhe tri vlerat e "
        "rëndësisë janë të tuat. Punimi e thotë hapur. Pragu i Long Method u provua me vlera të "
        "ndryshme dhe u kalibrua kundrejt MLCQ-së; të tjerët nuk mund të provohen, sepse MLCQ "
        "nuk ka etiketa për Brain Method dhe Deep Nesting."
    )
    doc.add_paragraph(
        "Problemi i rregullave: numrat janë fiksë dhe të përcaktuar mbi kod tjetër. Rezultati: "
        "kur alarmojnë zakonisht kanë të drejtë, por humbasin shumicën e rasteve."
    )

    # --- 8 ---
    doc.add_heading("8. Qasja B: mësimi makinerik", level=1)
    doc.add_paragraph(
        "Si e dallon një shalqi të pjekur? Rregulli thotë «nëse tingëllon bosh». Mësimi "
        "makinerik thotë: «më trego një mijë shalqinj që dikush i provoi, dhe unë e gjej vetë "
        f"kufirin». Modeli merr të njëjtat {f['metrics']} metrika si hyrje dhe etiketën e "
        "njeriut si përgjigje, dhe e mëson vetë kufirin."
    )
    winners = {s: ml["per_smell"][s]["best_model"] for s in smells}
    explain = {
        "logistic": "I jep çdo metrike një peshë, i mbledh dhe e kthen shumën në probabilitet. "
        "I thjeshtë dhe i shpjegueshëm.",
        "random_forest": "Qindra pemë vendimi, si loja «20 pyetje», secila pak ndryshe; ato "
        "votojnë.",
        "gradient_boosting": "Pemë njëra pas tjetrës; secila ndreq gabimet e së mëparshmes.",
        "majority": "Thotë gjithmonë përgjigjen më të shpeshtë («i pastër»). Pikë krahasimi që "
        "çdo model duhet ta kalojë.",
    }
    _grid(doc, ["Modeli", "Si punon", "Fitoi te"], [
        [MODEL_EN[m], text, _dhe([SMELL_SQ[s] for s in smells if winners[s] == m]) or "–"]
        for m, text in explain.items()
    ])  # fmt: skip
    doc.add_paragraph(
        "Pse jo deep learning: të dhënat janë të vogla dhe në tabelë, modelet duhet të "
        "shpjegohen, dhe gjithçka duhej të punonte në një laptop pa kosto."
    )
    doc.add_paragraph("Metrikat që ndikojnë më shumë te secili model:")
    _list(doc, [
        f"{SMELL_SQ[s]}: " + ", ".join(_metric_name(x) for x in ml["per_smell"][s]["top_features"][:4])
        for s in smells
    ])  # fmt: skip

    # --- 9 ---
    doc.add_heading("9. Të dhënat: MLCQ", level=1)
    _list(doc, [
        "MLCQ (Madeyski & Lewowski, 2020) është një bazë publike: 26 programues profesionistë "
        "shqyrtuan kod të vërtetë Java me burim të hapur dhe dhanë rreth 15 mijë vlerësime, në "
        "shkallën none, minor, major, critical.",
        "Kur një mostër ka disa vlerësues, etiketa merret nga mesatarja e vlerësimeve të tyre.",
        f"Nga {dataset['samples_considered']:,} mostra të shqyrtuara, {f['samples']:,} u gjetën "
        "në kod. Të tjerat humbën sepse skedari mungonte, kishte gabime sintakse, ose rreshtat "
        "nuk përputheshin.",
        f"MLCQ përmend {dataset['repositories']} projekte; disa nuk ishin më të arritshme, ndaj "
        f"mostrat vijnë nga {f['repositories']}.",
        "Korpusi mban vetëm skedarët .java, pa skedarë ndërtimi dhe pa librari. Kjo ka rëndësi "
        "te kontrolli me javac (pjesa 13).",
    ])  # fmt: skip

    # --- 10 ---
    doc.add_heading("10. Si matet nëse një detektor është i mirë", level=1)
    doc.add_paragraph(
        f"Matrica e konfuzionit, me rregullat për Blob mbi "
        f"{blob['tp'] + blob['fp'] + blob['tn'] + blob['fn']:,} mostra:"
    )
    _grid(doc, ["", "Njerëzit: erë", "Njerëzit: e pastër"], [
        ["Mjeti: erë", f"{blob['tp']} (saktë)", f"{blob['fp']} (alarm i rremë)"],
        ["Mjeti: e pastër", f"{blob['fn']} (e humbur)", f"{blob['tn']:,} (saktë)"],
    ])  # fmt: skip
    _list(doc, [
        f"Precision = {blob['tp']} / ({blob['tp']} + {blob['fp']}) = {blob['precision']:.0%}: "
        "kur thotë «erë», ka të drejtë kaq shpesh.",
        f"Recall = {blob['tp']} / ({blob['tp']} + {blob['fn']}) = {blob['recall']:.0%}: nga "
        "erërat e vërteta, kap vetëm kaq.",
        f"Kurthi i saktësisë: te Feature Envy vetëm {envy['support_positive']} nga "
        f"{envy_total:,} mostra kanë erë. Një «detektor» që thotë gjithmonë «i pastër» del "
        f"{majority:.1%} i saktë, edhe pse nuk ka mësuar asgjë.",
        "Prandaj MCC: nga −1 në +1, ku 0 do të thotë sa hamendja dhe +1 i përsosur. I përdor "
        "të katër qelizat e matricës, ndaj detektori që thotë gjithmonë «i pastër» merr 0.",
        f"Ndarja sipas projektit: të dhënat ndahen në {ml['folds']} grupe projektesh; modeli "
        "mëson nga katër dhe provohet te i pesti, me radhë. Asnjë model nuk provohet mbi një "
        "projekt nga i cili ka mësuar, sepse kodi i një projekti ka të njëjtin stil e të "
        "njëjtët emra, dhe modeli do ta njihte projektin në vend të erës.",
        f"Bootstrap: projektet rizgjidhen rastësisht me kthim {resamples:,} herë, dhe ndryshimi "
        "model − rregulla llogaritet çdo herë. 95% e mesme e këtyre vlerave është intervali i "
        "besimit. Nëse i gjithë intervali është mbi zero, modeli është vërtet më i mirë.",
        f"Fara e fiksuar ({ml['seed']}): numrat e rastit janë të njëjtët në çdo ekzekutim, ndaj "
        "kushdo i rimerr të njëjtat rezultate.",
    ])  # fmt: skip

    # --- 11 ---
    doc.add_heading("11. Rezultatet e gjetjes së erërave", level=1)
    rows = []
    for s in smells:
        rule, model = f["strategy"][s], f["best"][s]
        diff = intervals[s]["intervals"]["difference_model_minus_rules"]
        rows.append([
            SMELL_SQ[s],
            f"{rule['precision']:.2f} / {rule['recall']:.2f} / {rule['mcc']:.2f}",
            MODEL_EN[winners[s]],
            f"{model['precision']:.2f} / {model['recall']:.2f} / {model['mcc']:.2f}",
            f"{diff['low']:+.2f} … {diff['high']:+.2f}",
            "po" if diff["low"] > 0 else "jo, përfshin zeron",
        ])
    _grid(doc, ["Era", "Rregullat P / R / MCC", "Modeli", "Modeli P / R / MCC",
                "B − A, 95%", "I sigurt?"], rows)  # fmt: skip
    b = f["best"]["blob"]
    _list(doc, [
        "Rregullat kanë të drejtë kur alarmojnë, por kapin pak. Modelet kapin shumë më tepër, "
        f"me më shumë alarme të rreme. Te Blob: rregullat P {blob['precision']:.0%} dhe R "
        f"{blob['recall']:.0%}, modeli P {b['precision']:.0%} dhe R {b['recall']:.0%}.",
        f"Edhe algoritmi më i dobët i mund rregullat te {f['weakest']} nga {len(smells)} "
        "erërat, ndaj përfundimi nuk varet nga zgjedhja e modelit më të mirë.",
    ])  # fmt: skip

    # --- 12 ---
    doc.add_heading("12. Pse disa erëra mbeten të vështira", level=1)
    doc.add_paragraph(
        "Te mostrat me më shumë se një rishikim, u krahasua çdo çift rishikimesh të së njëjtës "
        "mostër: a thonë të dy «ka erë» apo jo. MCC mes rishikuesve:"
    )
    _grid(doc, ["Era", "MCC mes dy rishikuesve", "Kuptimi"], [
        [SMELL_SQ[s], f"{f['reviewers'][s]:.2f}",
         "sa hamendja" if s in f["chance"] else "pajtim mesatar"]
        for s in smells
    ])  # fmt: skip
    doc.add_paragraph(
        "Nëse mësuesit nuk pajtohen për çelësin e përgjigjeve, nxënësi nuk mund ta mësojë. "
        "Kufiri nuk është vetëm algoritmi, por vetë përkufizimi i erës. Prandaj te "
        f"{_dhe(f['unsure'])} modeli nuk i mund qartë rregullat."
    )

    # --- 13 ---
    doc.add_heading("13. Motori i refaktorimit", level=1)
    doc.add_heading("Kodi si pemë", level=2)
    doc.add_paragraph(
        "Parseri tree-sitter e kthen tekstin e kodit në një pemë sintakse (AST), si analiza "
        "gramatikore e një fjalie. «if (x > 0) { total += x; }» bëhet një nyje if me një "
        "kusht dhe një bllok brenda. Motori punon mbi pemën, jo me «gjej dhe zëvendëso» mbi "
        "tekst."
    )
    doc.add_heading("Pse jo një LLM", level=2)
    doc.add_paragraph(
        "Rishkrimet duhet të jenë deterministe (gjithmonë i njëjti rezultat), të vërtetueshme "
        "dhe falas. Një LLM shkruan kod që duket i besueshëm, por nuk i vërteton dot kushtet, "
        "dhe rezultati ndryshon nga njëri ekzekutim te tjetri. Ky vendim është i shënuar te "
        "docs/DECISIONS.md."
    )
    doc.add_heading("Tri ndreqjet", level=2)
    doc.add_paragraph("Guard Clauses, nga shembulli i vetë motorit:")
    _code(doc, [
        "void post(int amount) {              void post(int amount) {",
        "    if (amount > 0) {                    if (!(amount > 0)) {",
        "        total += amount;      →              return;",
        "        log(amount);                     }",
        "    }                                    total += amount;",
        "}                                        log(amount);",
        "                                     }",
    ])  # fmt: skip
    doc.add_paragraph(
        "Pranohet vetëm kjo formë: metodë void, i gjithë trupi një if, pa else. Kushti "
        "mbështillet me !( … ) dhe nuk kthehet së prapthi me dorë, ndaj mbetet i saktë për "
        "çdo kusht, edhe për numrat me presje (NaN)."
    )
    doc.add_paragraph(
        "Extract Method (shembull ilustrues, jo dalja e saktë e motorit): një pjesë e metodës "
        "kalon në një metodë të re, dhe hyrjet e saj bëhen parametra. Motori e quan metodën e "
        "re «extracted»; emrin e mirë e zgjedh programuesi."
    )
    _code(doc, [
        "void report(List<Order> orders) {        void report(List<Order> orders) {",
        "    double total = 0;                        double total = extracted(orders);",
        "    for (Order o : orders) {        →        System.out.println(total);",
        "        total += o.price();                }",
        "    }                                      // + metoda e re extracted(orders)",
        "    System.out.println(total);",
        "}",
    ])  # fmt: skip
    doc.add_paragraph(
        "Introduce Parameter Object (ilustrues): metoda(a, b, c, d, e, f) bëhet metoda(params), "
        "me një klasë të re që i mban të gjashtë."
    )
    doc.add_heading("Kushtet paraprake dhe refuzimi", level=2)
    doc.add_paragraph(
        "Mendo për një kirurg: nëse nuk je i sigurt, mos opero. Çdo ndreqje ka kushte "
        "paraprake. Nëse një kusht nuk vërtetohet dot nga pema, motori refuzon dhe thotë pse. "
        f"Gjithsej u refuzuan {refused:,} vende ({_pct(f['refused'])}):"
    )
    _grid(doc, ["Arsyeja", "Vende", "Pjesa", "Çka do të thotë"], [
        [reason, f"{count:,}", _pct(count / detected), REASON_SQ.get(reason, "")]
        for reason, count in sorted(refactoring["refused_by_reason"].items(), key=lambda p: -p[1])
    ])  # fmt: skip
    doc.add_heading("Kontrolli me javac", level=2)
    doc.add_paragraph(
        "Meqë korpusi nuk ka skedarë ndërtimi, shumica e skedarëve nuk kompilohen të vetëm as "
        "para ndryshimit: u mungojnë fqinjët. Prandaj kontrolli është: kompilo para dhe pas, "
        f"dhe shiko nëse rishkrimi shtoi një lloj të ri gabimi. Nga {applied:,} rishkrimet:"
    )
    _grid(doc, ["Rezultati", "Rishkrime", "Kuptimi"], [
        [verdict, f"{count:,}", VERDICT_SQ.get(verdict, "")]
        for verdict, count in sorted(refactoring["verdicts"].items(), key=lambda p: -p[1])
    ])  # fmt: skip
    inside = verify["compiled_in_project"]
    doc.add_paragraph(
        f"Kur {verify['rewrites']} rishkrime u kompiluan brenda projektit të tyre, ato që "
        f"kompilohen plotësisht u rritën nga {verify['compiled_alone'].get('compiles', 0)} në "
        f"{inside.get('compiles', 0)}, dhe {inside.get('new_errors', 0)} shtuan gabim të ri "
        f"({inside.get('not_checked', 0)} nuk u kontrolluan dot). Pra shumica e rasteve «nuk "
        "kompilohet» vjen nga skedarët e vetmuar, jo nga rishkrimi."
    )
    doc.add_heading("Rezultatet e motorit", level=2)
    resolution = refactoring["resolution"]
    _list(doc, [
        f"{detected:,} vende ku mund të zbatohej një ndreqje; {applied:,} u rishkruan "
        f"({_pct(applied / detected)}): " + ", ".join(f"{_words(k)} {v:,}" for k, v in by_type.items()) + ".",
        f"Era u zhduk në {resolution['resolved']:,} raste ({_pct(f['resolved'])}), mbeti në "
        f"{resolution['persists']:,}, dhe në {resolution.get('unknown', 0):,} nuk u mat dot.",
        f"{sum(f['introduced'].values()):,} erëra të reja u shfaqën pas rishkrimit: "
        + ", ".join(f"{_words(k)} {v}" for k, v in sorted(f["introduced"].items(), key=lambda p: -p[1]))
        + ". Më shpesh Long Parameter List, sepse metoda e nxjerrë i merr të gjitha hyrjet si "
        "parametra.",
    ])  # fmt: skip
    doc.add_heading("Rishikimi me dorë", level=2)
    doc.add_paragraph(
        f"Lexove {quality['reviewed']} rishkrime, {quality['per_refactoring']} për çdo ndreqje, "
        "dhe për secilin vendose: i pranueshëm siç është, i pranueshëm pas një ndreqjeje të "
        "vogël, ose i refuzuar."
    )
    rows, weighted = [], []
    for name, entry in quality["by_refactoring"].items():
        accept = entry["acceptance"]
        rows.append([_words(name), f"{entry['population']:,}", str(accept["as_is"]),
                     str(accept["after_edit"]), str(accept["reject"]), _pct(entry["acceptable"], 0),
                     str(entry["behaviour"]["changed"])])  # fmt: skip
        weighted.append(f"{entry['population']:,} × {entry['acceptable']:.2f}")
    _grid(doc, ["Ndreqja", "Rishkrime gjithsej", "Siç është", "Pas ndreqjes", "Refuzuar",
                "E pranueshme", "Sjellja ndryshoi"], rows)  # fmt: skip
    doc.add_paragraph(
        "Pse «e peshuar»: llojet nuk janë njësoj të shpeshta, ndaj përqindja e përgjithshme "
        f"peshohet me sa rishkrime ka secili: ({' + '.join(weighted)}) / {applied:,} = "
        f"{_pct(quality['acceptable_reweighted'])}."
    )
    changed = {_words(name): e["behaviour"]["changed"]
               for name, e in quality["by_refactoring"].items() if e["behaviour"]["changed"]}  # fmt: skip
    doc.add_paragraph(
        "Dije këtë: në rishikim, sjellja dukej se ndryshonte te "
        + _dhe([f"{count} {'rishkrim' if count == 1 else 'rishkrime'} {name}"
                for name, count in changed.items()])  # fmt: skip
        + ". Kjo është pikërisht arsyeja pse punimi thotë «kompilohet» dhe jo «sillet njësoj»."
    )

    # --- 14 ---
    doc.add_heading("14. Krahasimet", level=1)
    doc.add_heading(f"Me PMD {pmd['pmd_version']}", level=2)
    doc.add_paragraph(
        "PMD është një analizues statik falas dhe shumë i përdorur. U ekzekutua me pragjet e "
        "veta, mbi të njëjtat mostra. Ndryshimi është yni minus i PMD-së."
    )
    _grid(doc, ["Era", "PMD MCC", "MCC ynë", "Ndryshimi, 95%"], [
        [PMD_NAMES.get(key, key), f"{e['pmd']['mcc']:.2f}",
         "–" if e.get("ours") is None else f"{e['ours']['mcc']:.2f}",
         "–" if e.get("difference") is None
         else f"{e['difference']['low']:+.2f} … {e['difference']['high']:+.2f}"]
        for key, e in pmd["by_smell"].items()
    ])  # fmt: skip
    closer = [PMD_NAMES.get(key, key) for key, e in pmd["by_smell"].items()
              if e.get("ours") and e["pmd"]["mcc"] > e["ours"]["mcc"]]  # fmt: skip
    doc.add_paragraph(
        ("Me intervalin e besimit, PMD nuk del kurrë përpara."
         if not f["pmd_ahead"] else f"PMD del përpara te {_dhe(f['pmd_ahead'])}.")
        + (f" Te {_dhe(closer)} PMD ka numër pak më të lartë, por intervali e përfshin zeron, "
           "ndaj nuk mund të thuhet që është përpara." if closer else "")
        + " PMD nuk ka rregull për Feature Envy; LawOfDemeter është më i afërti. Me SonarQube, "
        "që është komercial, nuk u krahasua."
    )  # fmt: skip
    doc.add_heading("Me literaturën", level=2)
    _grid(doc, ["Era", "Rregullat (A)", "Modeli (B)", "Madeyski & Lewowski 2023"], [
        [SMELL_SQ[s], f"{f['strategy'][s]['mcc']:.2f}", f"{f['best'][s]['mcc']:.2f}",
         MADEYSKI_2023_DS1[s]] for s in smells
    ])  # fmt: skip
    doc.add_paragraph(
        "Ata përdorën ndarje rastësore në pesë pjesë dhe i akorduan modelet; ti i ndave sipas "
        "projektit dhe nuk i akordove. Rezultatet janë në të njëjtin rang."
    )

    # --- 15 ---
    doc.add_heading("15. Ndërfaqja, CLI-ja dhe siguria", level=1)
    _list(doc, [
        "Ndërfaqja web (React) tregon erërat, kushtet që i shkaktuan dhe rishkrimin e "
        "propozuar, para se të preket ndonjë skedar.",
        "Mënyra me gjuhë të thjeshtë, shqip, vjen nga një fjalor i vetëm që e përdorin edhe "
        "CLI-ja (--thjeshte) edhe ndërfaqja, që të dyja të shpjegojnë njësoj.",
        "Si parazgjedhje mjeti nuk shkruan mbi kodin origjinal: prodhon një skedar ndryshimesh "
        "(patch). Shkrimi në vend kërkon një flamur të qartë.",
        "Punon vetëm në kompjuterin tënd (localhost). Nuk pranon kërkesa nga faqe të huaja, dhe "
        "çdo shteg analize mbyllet brenda një dosjeje të lejuar.",
        "Niset me Nis-JavaSmell.bat ose me Docker. Licenca është MIT.",
    ])  # fmt: skip

    # --- 16 ---
    doc.add_heading("16. Parimet e punimit", level=1)
    _list(doc, [
        "Zero kosto: asnjë shërbim me pagesë; gjithçka punon në një laptop pa kartë grafike.",
        "I riprodhueshëm: çdo numër prodhohet nga një skript te scripts/ dhe ruhet te "
        "data/results/, me fara të fiksuara dhe versione të fiksuara.",
        "Pa LLM në produkt: ndreqjet janë transformime të pemës, jo tekst i gjeneruar.",
        "Çdo prag ka një burim, ose thuhet hapur që nuk ka.",
        "Rezultatet negative raportohen: Feature Envy, refuzimet, erërat e reja, Introduce "
        "Parameter Object.",
        "Vendimet shënohen kur merren, te docs/DECISIONS.md, secili me numrin e vet VD.",
    ])  # fmt: skip

    # --- 17 ---
    doc.add_heading("17. Kufizimet dhe si t'i thuash", level=1)
    doc.add_paragraph("Formula për çdo kufizim: pranoje → thuaj pse → thuaj çka do të bëje më pas.")
    _grid(doc, ["Kufizimi", "Pse", "Çka do të bëje"], [
        ["Kompilohet ≠ sillet njësoj", "Korpusi nuk ka skedarë ndërtimi, ndaj testet e "
         "projekteve nuk u ekzekutuan", "Testet e projekteve pas çdo rishkrimi"],
        ["Një bazë, katër erëra, vetëm Java", "Etiketat vijnë vetëm nga MLCQ, që ka katër erëra "
         "dhe kod Java", "Baza të tjera dhe gjuhë të tjera; parseri tree-sitter i mbështet"],
        ["Modeli më i mirë u zgjodh mbi të njëjtat parashikime", "Krahasimi bëhet mbi të njëjtat "
         "grupe", f"Raportohen të gjithë; edhe më i dobëti fiton te {f['weakest']} nga "
         f"{len(smells)}"],
        ["Disa pragje pa burim", "Literatura nuk jep vlerë", "U provuan me vlera të ndryshme"],
        ["Rishikimin me dorë e bëri vetëm autori", "Punim individual", "Rishikues të pavarur"],
        ["Etiketat e Feature Envy nuk janë të besueshme", "Njerëzit nuk pajtohen",
         "Përkufizim më i qartë ose më shumë rishikues për mostër"],
    ])  # fmt: skip

    # --- 18 ---
    doc.add_heading("18. Fjalorth", level=1)
    _grid(doc, ["Termi", "Shqip", "Shpjegimi"], [list(row) for row in TERMS])

    # --- 19 ---
    doc.add_heading("19. Pyetje për vetëkontroll", level=1)
    doc.add_paragraph(
        "Mbuloje përgjigjen dhe thuaje me zë. Përgjigjet në anglisht për sallën janë te fleta "
        "e përgatitjes."
    )
    _qa(doc, [
        ("Çka është një erë e kodit, dhe pse nuk është gabim?",
         "Shenjë që kodi është ndërtuar keq dhe ndryshohet me vështirësi. Programi punon, ndaj "
         "nuk është gabim."),
        ("Cilat janë katër erërat e vlerësuara, dhe pse vetëm këto?",
         "Blob, Data Class, Feature Envy dhe Long Method: vetëm ato kanë etiketa në MLCQ."),
        ("Çka bën qasja A, B dhe C?",
         "A: rregulla të botuara mbi metrika. B: modele që mësojnë nga etiketat. C: ndreqje e "
         "kodit vetëm kur kushtet vërtetohen, me kontroll nga javac."),
        ("Pse MCC dhe jo saktësia?",
         f"Te Feature Envy, «gjithmonë i pastër» del {majority:.1%} i saktë. MCC i jep 0."),
        ("Çka është rrjedhja e të dhënave, dhe si u shmang?",
         "Provimi mbi atë që modeli e ka parë. U shmang me ndarje sipas projektit."),
        ("Çka tregon bootstrap-i?",
         "Nëse ndryshimi model − rregulla është i vërtetë apo fat: nëse intervali 95% është i "
         "gjithi mbi zero, është i vërtetë."),
        ("Pse rregullat kanë precision të lartë, por recall të ulët?",
         "Pragjet fikse janë të rrepta: alarmojnë rrallë, por kur alarmojnë kanë të drejtë."),
        ("Pse Feature Envy është e vështirë?",
         f"Dy ekspertë pajtohen sa me hamendje: MCC {f['reviewers']['feature envy']:.2f}."),
        ("Çka është AST-ja?", "Kodi i kthyer në pemë, si analiza gramatikore e një fjalie."),
        ("Pse motori refuzon kaq shpesh?",
         "Sepse refuzon kur nuk vërteton dot një kusht. Refuzimi është rezultat i saktë."),
        ("Pse një return brenda pjesës së nxjerrë e ndalon Extract Method?",
         "Në metodën e re, return-i do të dilte vetëm nga ajo, jo nga metoda origjinale: "
         "sjellja ndryshon."),
        ("Çka do të thotë «nuk shton lloj të ri gabimi»?",
         "Skedari nuk kompilohej as më parë, sepse i mungojnë fqinjët; rishkrimi nuk shtoi "
         "gabim tjetër."),
        ("Pse Introduce Parameter Object merr 0%?",
         "Sepse vetëm e zhvendos listën e gjatë të parametrave në një klasë të re."),
        ("Pse jo një LLM?",
         "Nuk vërteton kushtet, nuk riprodhohet dhe nuk është deterministik; dhe kërkesa ishte "
         "zero kosto."),
        ("Çka do të bëje më pas?",
         "Testet e projekteve pas çdo rishkrimi, një zgjidhës i vogël emrash për më shumë "
         "ndreqje, dhe rishikues të pavarur."),
    ])  # fmt: skip

    # --- 20 ---
    doc.add_heading("20. Burimet kryesore", level=1)
    _list(doc, SOURCES)

    doc.save(KNOWLEDGE)
    return KNOWLEDGE


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    facts = _facts()
    for long in (False, True):
        deck, script, backups = build_deck(facts, long)
        words = sum(_word_count(_spoken(parts, long)) for _, parts in script)
        print(f"U gjenerua: {deck}")
        print(f"  Fjalë në tekstin folës: {words}, rreth {words / WORDS_PER_MINUTE:.1f} minuta "
              f"me ritëm të qetë, {words / FAST_WORDS_PER_MINUTE:.1f} me të shpejtë")  # fmt: skip
    for path in (
        build_sheet(facts, script),
        build_speech_guide(facts, script, backups),
        build_knowledge(facts),
    ):
        print(f"U gjenerua: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
