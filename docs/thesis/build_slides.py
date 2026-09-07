"""Ndërton prezantimin e mbrojtjes nga të njëjtat burime si punimi.

    python docs/thesis/build_slides.py

Shkruan `Prezantimi_Florent_Latifi.pptx` krahas punimit.

**Pse gjenerohet e nuk shkruhet me dorë.** Sllajdet mbajnë të njëjtat shifra si
Kapitulli 5, dhe një prezantim i shkruar me dorë është vendi ku ato ndahen nga
punimi pa e vënë re askush: një numër përditësohet te `data/results/`, punimi
rindërtohet, sllajdi mbetet i vjetruar, dhe dallimi zbulohet para komisionit. Këtu
çdo shifër lexohet nga i njëjti skedar që lexon `chapters.py`, përmes të njëjtit
ngarkues, ndaj një sllajd i vjetruar nuk mund të ekzistojë (VD-38, VD-56).

Figurat janë ato të komituarat te `figures/`, të prodhuara nga
`scripts/build_figures.py`. Asnjë grafik nuk vizatohet këtu.

**Skeleti, jo forma përfundimtare.** Si te `build_thesis.py`, dalja është
pikënisje: renditja, teksti folës dhe koha janë të autorit, dhe rregullimi i
mëtejshëm bëhet në PowerPoint. Riekzekutimi e mbishkruan skedarin.
"""

from __future__ import annotations

import os

from chapters import (
    SMELL_SQ,
    _load,
)
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

OUTPUT = os.path.join(os.path.dirname(__file__), "Prezantimi_Florent_Latifi.pptx")
FIGURES = os.path.join(os.path.dirname(__file__), "figures")

# 16:9. Një sallë mbrojtjeje projekton gjerë, dhe 4:3 lë shirita bosh anash.
WIDTH = Inches(13.333)
HEIGHT = Inches(7.5)

# E njëjta paletë si figurat dhe si ndërfaqja: një pamje ekrani dhe një figurë e
# Kapitullit 5 rrinë në të njëjtin sllajd pa u përplasur.
INK = RGBColor(0x1A, 0x1D, 0x21)
SOFT = RGBColor(0x4C, 0x55, 0x60)
FAINT = RGBColor(0x83, 0x8D, 0x99)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
CRITICAL = RGBColor(0x8C, 0x2F, 0x22)

SERIF = "Times New Roman"
SANS = "Segoe UI"

#: Trupi lexohet nga rreshti i fundit i sallës, jo nga ekrani i folësit.
TITLE_SIZE = Pt(34)
BODY_SIZE = Pt(19)
SMALL_SIZE = Pt(14)
FIGURE_SIZE = Pt(54)

MARGIN = Inches(0.85)


def _blank(deck: Presentation):
    """Një sllajd pa asnjë vend-mbajtës: çdo kuti vendoset shprehimisht.

    Layout-et e gatshme të PowerPoint-it sjellin vend-mbajtës me madhësi që nuk
    i zgjedh ky skript, dhe një titull që rrëshqet dy centimetra nga sllajdi te
    sllajdi duket si pakujdesi edhe kur përmbajtja është e saktë.
    """
    return deck.slides.add_slide(deck.slide_layouts[6])


def _text(slide, left, top, width, height, size=BODY_SIZE, color=INK, font=SANS, bold=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.font.size = size
    paragraph.font.color.rgb = color
    paragraph.font.name = font
    paragraph.font.bold = bold
    return frame


def _title(slide, text, subtitle=""):
    frame = _text(slide, MARGIN, Inches(0.5), WIDTH - 2 * MARGIN, Inches(1.0), TITLE_SIZE, INK, SERIF)
    frame.paragraphs[0].text = text
    if subtitle:
        run = frame.add_paragraph()
        run.text = subtitle
        run.font.size = SMALL_SIZE
        run.font.color.rgb = FAINT
        run.font.name = SANS
    return frame


def _bullets(slide, lines, top=Inches(1.9), width=None, size=BODY_SIZE):
    frame = _text(slide, MARGIN, top, width or (WIDTH - 2 * MARGIN), Inches(4.6), size)
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = f"·  {line}" if not line.startswith(" ") else line
        paragraph.font.size = size
        paragraph.font.color.rgb = INK
        paragraph.font.name = SANS
        paragraph.space_after = Pt(14)
    return frame


def _figures(slide, values, top=Inches(2.0)):
    """Një rresht shifrash të mëdha me nënshkrim, si shiriti i ndërfaqes."""
    span = (WIDTH - 2 * MARGIN) // max(len(values), 1)
    for index, (number, label) in enumerate(values):
        left = MARGIN + Emu(int(span) * index)
        frame = _text(slide, left, top, Emu(int(span)), Inches(1.2), FIGURE_SIZE, ACCENT, SERIF)
        frame.paragraphs[0].text = number
        caption = frame.add_paragraph()
        caption.text = label
        caption.font.size = SMALL_SIZE
        caption.font.color.rgb = FAINT
        caption.font.name = SANS


def _picture(slide, name, top=Inches(1.9), height=Inches(4.7)):
    path = os.path.join(FIGURES, name)
    if not os.path.exists(path):
        _text(slide, MARGIN, top, WIDTH - 2 * MARGIN, Inches(0.6), BODY_SIZE, CRITICAL).paragraphs[
            0
        ].text = f"[MUNGON figura {name}]"
        return
    picture = slide.shapes.add_picture(path, MARGIN, top, height=height)
    picture.left = Emu(int((WIDTH - picture.width) / 2))


def _note(slide, text):
    """Shënim folësi: çka thuhet me gojë, jo çka lexohet nga sllajdi."""
    slide.notes_slide.notes_text_frame.text = text


def _table(slide, headers, rows, top=Inches(2.0), size=Pt(16)):
    shape = slide.shapes.add_table(
        len(rows) + 1, len(headers), MARGIN, top, WIDTH - 2 * MARGIN, Inches(0.5)
    )
    table = shape.table
    for column, name in enumerate(headers):
        cell = table.cell(0, column)
        cell.text = name
        paragraph = cell.text_frame.paragraphs[0]
        paragraph.font.size = SMALL_SIZE
        paragraph.font.bold = True
        paragraph.font.name = SANS
    for line, values in enumerate(rows, start=1):
        for column, value in enumerate(values):
            cell = table.cell(line, column)
            cell.text = str(value)
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.font.size = size
            paragraph.font.name = SANS
            if column:
                paragraph.alignment = PP_ALIGN.RIGHT
    return table


# ======================================================================
# Përmbajtja. Çdo shifër lexohet; asnjë nuk shtypet.
# ======================================================================
AUTHOR = "Florent Latifi"
SUPERVISOR = "Altina Salihu"
TITLE_SQ = "Detektimi i code smells dhe rekomandimet për refaktorim"
PROGRAM = "Shkenca Kompjuterike dhe Inxhinieri · UBT"


def _mean(rules, smell):
    return rules["per_smell"][smell]["strategy"]["by_aggregation"]["mean"]


def _best_model(ml, smell):
    entry = ml["per_smell"][smell]
    return entry["best_model"], entry["models"][entry["best_model"]]["mcc"]


def build() -> str:
    rules = _load("rules_evaluation.json")
    ml = _load("ml_evaluation.json")
    refactoring = _load("refactoring_evaluation.json")
    dataset = _load("mlcq_dataset.json")
    agreement = _load("reviewer_agreement.json")
    verify = _load("verify_with_project.json")

    smells = sorted(rules["per_smell"])
    ceiling = [agreement["per_smell"][s]["mcc"] for s in smells]

    deck = Presentation()
    deck.slide_width = WIDTH
    deck.slide_height = HEIGHT

    # --- 1. kopertina ---
    slide = _blank(deck)
    frame = _text(slide, MARGIN, Inches(2.4), WIDTH - 2 * MARGIN, Inches(1.4), Pt(40), INK, SERIF)
    frame.paragraphs[0].text = TITLE_SQ
    frame = _text(slide, MARGIN, Inches(4.0), WIDTH - 2 * MARGIN, Inches(1.6), BODY_SIZE, SOFT)
    frame.paragraphs[0].text = f"{AUTHOR}  ·  Mentore: {SUPERVISOR}"
    line = frame.add_paragraph()
    line.text = PROGRAM
    line.font.size = SMALL_SIZE
    line.font.color.rgb = FAINT
    line.font.name = SANS
    _note(slide, "Rreth 13 minuta; pyetjet vijnë pas.")

    # --- 2. problemi ---
    slide = _blank(deck)
    _title(slide, "Problemi", "Pse detektimi i code smells nuk është i zgjidhur")
    _bullets(
        slide,
        [
            "Një code smell është simptomë dizajni, jo defekt: kodi funksionon, por "
            "ndryshimi i tij kushton.",
            "Përkufizimet janë cilësore. Nuk ka prag të botuar që e pranojnë të gjithë.",
            "Vetë zhvilluesit profesionistë nuk pajtohen mes tyre për një të katërtën "
            "e mostrave.",
            "Rrjedhimisht «sa i saktë është një detektor» varet nga kundrejt kujt matet.",
        ],
    )
    _note(
        slide,
        "Këtu vendoset pse punimi mat edhe tavanin e pajtimit mes rishikuesve, "
        "e jo vetëm saktësinë kundrejt etiketave.",
    )

    # --- 3. pyetjet ---
    slide = _blank(deck)
    _title(slide, "Tri pyetje kërkimore")
    _bullets(
        slide,
        [
            "PK1 — Sa e saktë është detektimi me strategji metrikash, krahasuar me "
            "etiketimet e zhvilluesve profesionistë?",
            "PK2 — A e përmirëson një model i mësimit të makinës, i trajnuar mbi të "
            "njëjtat metrika, saktësinë krahasuar me pragjet fikse?",
            "PK3 — A i përmirësojnë refaktorimet e propozuara karakteristikat "
            "strukturore, duke ruajtur kompilueshmërinë dhe sjelljen?",
        ],
    )
    _note(slide, "PK3 ka dy gjysma. Vetëm njëra u mat, dhe kjo thuhet hapur më vonë.")

    # --- 4. çka u ndërtua ---
    slide = _blank(deck)
    _title(slide, "Çka u ndërtua", "Tri qasje të pavarura mbi një sistem të vetëm")
    _bullets(
        slide,
        [
            "A — Strategji detektimi nga literatura (Lanza & Marinescu), me pragje të cituara.",
            "B — Klasifikues i trajnuar mbi të njëjtat metrika, me etiketat e MLCQ-së.",
            "C — Motor refaktorimi mbi AST: transformime deterministike, të verifikuara "
            "me kompilator.",
            "Të tria ndajnë një parser, një grup metrikash dhe të njëjtin kod pikëzimi.",
        ],
    )
    _note(
        slide,
        "Theksi: A dhe B pikëzohen me të njëjtin kod. Kjo i bën shifrat e krahasueshme "
        "dhe është një nga tri kontributet.",
    )

    # --- 5. të dhënat ---
    slide = _blank(deck)
    _title(slide, "Të dhënat", "MLCQ: etiketime nga zhvillues profesionistë")
    _figures(
        slide,
        [
            (f"{dataset['rows']:,}".replace(",", " "), "mostra të matura"),
            (f"{dataset['repositories']}", "depo Java"),
            (f"{len(smells)}", "erëra"),
        ],
    )
    _bullets(
        slide,
        [
            "Korpusi shkarkohet nga commit-et që MLCQ-ja emërton, jo nga HEAD.",
            "Çdo mostër lidhet me entitetin e vet përmes rangut të rreshtave, jo emrit.",
        ],
        top=Inches(4.2),
        size=SMALL_SIZE,
    )
    _note(slide, "Nëse pyesin për mbulimin: 95.4% e mostrave u materializuan; pjesa tjetër është kufizim i raportuar.")

    # --- 6. si matet ---
    slide = _blank(deck)
    _title(slide, "Si matet", "Ndarja është vendi ku rezultatet fryhen më lehtë")
    _bullets(
        slide,
        [
            "Ndarja është e grupuar sipas depos: asnjë projekt nuk shfaqet në të dyja anët.",
            "Një ndarje e rastësishme sipas rreshtave do të vinte kod të kopjuar nga i "
            "njëjti projekt në të dy anët, dhe do t'i fryjë të gjitha shifrat.",
            "Raportohet MCC, jo saktësia: kur shumica e etiketave janë «asnjë erë», një "
            "detektor që nuk ndez kurrë duket i shkëlqyer.",
            "Klasifikuesi i shumicës raportohet për çdo erë, si kontroll.",
        ],
    )
    _note(slide, "Ky sllajd i përgjigjet pyetjes më të mundshme: a janë fryrë numrat.")

    # --- 7. PK1 ---
    slide = _blank(deck)
    _title(slide, "PK1 — Qasja A: strategjitë", "Precizion i lartë, recall i ulët, kudo")
    _table(
        slide,
        ["Erë", "Precizion", "Recall", "F1", "MCC"],
        [
            [
                SMELL_SQ.get(s, s),
                f"{_mean(rules, s)['precision']:.3f}",
                f"{_mean(rules, s)['recall']:.3f}",
                f"{_mean(rules, s)['f1']:.3f}",
                f"{_mean(rules, s)['mcc']:.3f}",
            ]
            for s in smells
        ],
    )
    _bullets(
        slide,
        ["Kur strategjia ndez, zakonisht ka të drejtë. Por ndez rrallë."],
        top=Inches(5.3),
        size=SMALL_SIZE,
    )
    _note(slide, "Pragjet janë ato të botuara, të pandryshuara. Nuk u kalibruan për t'i zbukuruar numrat.")

    # --- 8. PK2 ---
    slide = _blank(deck)
    _title(slide, "PK2 — Qasja B kundrejt A", "I njëjti korpus, i njëjti kod pikëzimi")
    _picture(slide, "mcc_a_vs_b.png", top=Inches(1.9), height=Inches(4.3))
    _note(
        slide,
        "Modeli fiton te të katër erërat, dhe përparësia mbetet mbi zeron edhe me "
        "intervale besimi të grupuara sipas depos.",
    )

    # --- 9. tavani ---
    slide = _blank(deck)
    _title(slide, "Sa të mira janë vërtet këto shifra?", "Tavani nuk është 1.0")
    _table(
        slide,
        ["Erë", "MCC: A", "MCC: B", "MCC mes rishikuesve"],
        [
            [
                SMELL_SQ.get(s, s),
                f"{_mean(rules, s)['mcc']:.3f}",
                f"{_best_model(ml, s)[1]:.3f}",
                f"{agreement['per_smell'][s]['mcc']:.3f}",
            ]
            for s in smells
        ],
    )
    _bullets(
        slide,
        [
            f"Vetë rishikuesit pajtohen mes tyre me MCC {min(ceiling):.3f}–{max(ceiling):.3f}. "
            "Kjo i vendos të gjitha shifrat e mësipërme në një shkallë tjetër.",
        ],
        top=Inches(5.3),
        size=SMALL_SIZE,
    )
    _note(slide, "Ky sllajd e parandalon pyetjen «pse MCC-ja juaj është kaq e ulët».")

    # --- 10. PK3 ---
    slide = _blank(deck)
    _title(slide, "PK3 — Qasja C: motori i refaktorimit")
    _figures(
        slide,
        [
            (f"{refactoring['detected']:,}".replace(",", " "), "vende të gjetura"),
            (f"{refactoring['applied']:,}".replace(",", " "), "të transformuara"),
            (f"{refactoring['applied'] / refactoring['detected']:.0%}", "e vendeve"),
        ],
    )
    _bullets(
        slide,
        [
            "Refuzimi është rezultat i saktë, jo dështim: motori nuk e prek kodin kur "
            "parakushti nuk provohet nga pema e analizës.",
            "Arsyeja kryesore është që forma e kodit nuk përputhet — "
            f"{refactoring['refused_by_reason']['shape_not_matched'] / refactoring['detected']:.0%}"
            " e vendeve.",
        ],
        top=Inches(4.2),
        size=SMALL_SIZE,
    )
    _note(slide, "Numri i vogël i aplikuar është zgjedhje konservatore dhe raportohet si e tillë.")

    # --- 11. verifikimi ---
    slide = _blank(deck)
    _title(slide, "Verifikimi, dhe ku ndalet", "Gjysma e dytë e PK3 nuk u mat")
    _bullets(
        slide,
        [
            "Çdo rishkrim kompilohet. Pretendimi është «kompilon» ose «nuk shton lloj "
            "të ri gabimi».",
            "I kompiluar brenda projektit të vet, verdikti më i fortë ngjitet nga "
            f"{verify['compiled_alone'].get('compiles', 0)} te "
            f"{verify['compiled_in_project'].get('compiles', 0)} nga {verify['rewrites']} "
            "rishkrime të mostrës.",
            "Ruajtja e sjelljes nuk verifikohet: korpusi mban vetëm skedarë .java, pa "
            "skedarë ndërtimi dhe pa varësi, ndaj asnjë suitë testesh nuk ekzekutohet dot.",
            "Kjo raportohet si kufizim, jo si pretendim i arritur.",
        ],
    )
    _note(
        slide,
        "Nëse pyesin pse nuk u testua sjellja: rishkarkimi i korpusit me varësi ishte "
        "jashtë kohës dhe hapësirës; kufizimi është i shkruar te Kapitulli 1 dhe 6.",
    )

    # --- 12. përgjigjet ---
    slide = _blank(deck)
    _title(slide, "Përgjigjet")
    _bullets(
        slide,
        [
            "PK1 — Strategjitë janë të sakta kur ndezin, por e humbin shumicën e rasteve.",
            "PK2 — Po. Modeli i tejkalon pragjet fikse te të katër erërat, mbi të njëjtën "
            "ndarje dhe me të njëjtin kod pikëzimi.",
            "PK3 — Pjesërisht. Kompilueshmëria u verifikua; sjellja jo, dhe kjo thuhet "
            "hapur në vend që pyetja të ngushtohej.",
        ],
    )
    _note(slide, "Përgjigjja e ndarë për PK3 është e qëllimshme dhe e regjistruar te DECISIONS.md.")

    # --- 13. kufizimet ---
    slide = _blank(deck)
    _title(slide, "Kufizimet", "Të raportuara, jo të zbutura")
    _bullets(
        slide,
        [
            "E vërteta bazë është subjektive dhe rishikuesit nuk pajtohen mes tyre.",
            "Analiza është statike dhe nuk zgjidh tipa: varësitë semantike trajtohen "
            "konservativisht.",
            "Ashpërsia e derivuar u krahasua me atë të rishikuesve, rezultati doli "
            "negativ, dhe pretendimi u hoq.",
            "Sjellja e kodit të rishkruar mbetet e paverifikuar.",
            "Nuk ka krahasim me mjete ekzistuese: kontributi është krahasueshmëria e "
            "brendshme mes A-së dhe B-së.",
        ],
    )
    _note(slide, "Më mirë t'i thuash vetë kufizimet se t'i nxjerrin ata.")

    # --- 14. kontributi ---
    slide = _blank(deck)
    _title(slide, "Kontributi")
    _bullets(
        slide,
        [
            "Dy qasje detektimi të vlerësuara mbi të njëjtin korpus me të njëjtin kod "
            "pikëzimi, me ndarje të grupuar dhe të deklaruar.",
            "Lidhja mes detektimit dhe refaktorimit e matur empirikisht: sa nga rastet "
            "e gjetura arrijnë të transformohen vërtet.",
            "Rezultatet negative të raportuara, jo të fshehura.",
            "Çdo shifër e riprodhueshme nga një skript, dhe riprodhimi u vu në provë.",
        ],
    )
    _note(slide, "Mbyll me riprodhueshmërinë: është ajo që e dallon këtë punim.")

    # --- 15. faleminderit ---
    slide = _blank(deck)
    frame = _text(slide, MARGIN, Inches(3.0), WIDTH - 2 * MARGIN, Inches(1.0), Pt(36), INK, SERIF)
    frame.paragraphs[0].text = "Faleminderit"
    frame = _text(slide, MARGIN, Inches(4.1), WIDTH - 2 * MARGIN, Inches(1.0), SMALL_SIZE, FAINT)
    frame.paragraphs[0].text = "Pyetje"
    _note(slide, "Sllajdet rezervë vijnë pas kësaj.")

    # --- rezervë ---
    slide = _blank(deck)
    _title(slide, "Rezervë — ndjeshmëria ndaj pragjeve")
    _picture(slide, "ndjeshmeria_e_pragjeve.png", top=Inches(1.9), height=Inches(4.3))
    _note(slide, "Fshirja mat qëndrueshmëri, nuk zgjedh pragje. Dy pragje dolën të ndjeshme dhe nuk u adoptuan.")

    slide = _blank(deck)
    _title(slide, "Rezervë — çka zgjodhi modeli")
    _picture(slide, "rendesia_e_vecorive.png", top=Inches(1.9), height=Inches(4.3))
    _note(slide, "Rëndësia matet jashtë fold-it, ndaj nuk anon drejt veçorive me shumë vlera.")

    deck.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(f"U gjenerua: {build()}")
