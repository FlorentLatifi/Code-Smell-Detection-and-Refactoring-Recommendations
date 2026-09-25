"""Abstrakti dhe përmbajtja e kapitujve 2 deri 8.

E ndarë nga `build_thesis.py` sepse ai është ndërtues formati dhe ky është tekst;
bashkimi i të dyjave do ta bënte të vështirë të ndryshohej njëri pa prekur
tjetrin.

Një seksion është `(numri | None, titulli, [paragrafët])`. Një paragraf është
varg teksti, ose një çift `("bullet", teksti)`, ose `("figure", shtegu, titulli)`,
ose `("table", titulli, kokat, rreshtat)`.

**Numrat e Kapitullit 5 nuk shkruhen këtu.** Ata lexohen nga `data/results/` në
kohën e ndërtimit, njësoj si figurat. Një numër i shkruar me dorë në tekst dhe i
rigjeneruar në JSON ndahen heshtazi nga njëri-tjetri, dhe komisioni nuk ka si ta
dallojë cili është i vjetruar.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "data" / "results"
FIGURES = Path(__file__).resolve().parent / "figures"

SMELL_SQ = {
    "blob": "Blob",
    "data class": "Data Class",
    "long method": "Long Method",
    "feature envy": "Feature Envy",
}

# Verdiktet e verifikimit, ashtu si i emërton teksti. Tabelat i shtypnin
# identifikuesit e kodit («no new errors») ndërsa proza fliste për «pa gabim të
# ri», dhe lexuesi duhej ta bënte vetë lidhjen mes dy emrave të së njëjtës gjë.
VERDICT_SQ = {
    "compiles": "kompilon",
    "no_new_errors": "pa gabim të ri",
    "new_errors": "gabim i ri",
    "parses": "u parsua, pa kompilim",
    "broken_syntax": "sintaksë e prishur",
    "not_checked": "i pakontrolluar",
}

# Numërorët në gjininë femërore, për «erëra», «rishkrime», «krahasime»: emrat
# mashkullorë që marrin -e në shumës (rishkrim, rishkrime) sillen në shumës si
# femërorë, ndaj «tri» e jo «tre».
_FEMININE = ("asnjë", "një", "dy", "tri", "katër", "pesë", "gjashtë", "shtatë", "tetë",
             "nëntë", "dhjetë")  # fmt: skip
_ALL_OF = {2: "të dyja", 3: "të tria"}

# Nga sa shifra ndahen mijëshet. Katër shifra shkruhen bashkë, sipas konventës së
# SI-së, që «4534» të mos dalë njëherë si «4 534» e njëherë si «4.534».
_GROUPED_FROM = 10_000


def _count(value: int) -> str:
    """Një numër i plotë në prozë ose në tabelë, në një trajtë të vetme.

    Punimi e shkruante të njëjtin numër në tri mënyra: «4 534» te abstrakti,
    «4534» te Kapitulli 5 dhe «4.534» te Shtojca 8.5. E treta është edhe e
    rrezikshme, sepse këtu pika është presje dhjetore dhe «4.534» lexohet katër e
    gjysmë. Nga pesë shifra e lart mijëshet ndahen me hapësirë të pandashme, që
    numri të mos çahet në dy rreshta (VD-129).
    """
    if value < _GROUPED_FROM:
        return str(value)
    return f"{value:,}".replace(",", " ")


def _word(count: int) -> str:
    """Një numër i vogël me fjalë («tri»), një i madh me shifra."""
    return _FEMININE[count] if 0 <= count < len(_FEMININE) else str(count)


def _among(count: int, total: int, noun: str = "erërat") -> str:
    """«te tri nga katër erërat», ose «te të katër erërat» kur janë të gjitha.

    Proza e ndërtuar nga të dhënat shkruante «te 4 nga 4 erërat», e saktë por e
    pazakontë në një tekst shqip, ku numrat e vegjël shkruhen me fjalë.
    """
    if count == total:
        return f"te {_ALL_OF.get(total, 'të ' + _word(total))} {noun}"
    if count == 0:
        return f"te asnjëra nga {_word(total)} {noun}"
    return f"te {_word(count)} nga {_word(total)} {noun}"


def _named(identifier: str) -> str:
    """Emri i një ere ose i një refaktorimi ashtu si e shkruan Fowler-i.

    Kodi i mban si identifikues («BrainMethod», «ReplaceNestedConditionalWith
    GuardClauses»), dhe ashtu dilnin në tabela, ndërsa teksti i shkruan «Brain
    Method». Lexuesi s'duhet të mendojë nëse janë e njëjta gjë.
    """
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", identifier).replace(" With ", " with ")


def _load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def _load_if_present(name: str) -> dict | None:
    """A result that may not exist yet.

    The refactoring evaluation takes hours, so the chapter has to build while it
    is still running. When the file is missing the section says so plainly rather
    than quoting the partial run as if it were finished.
    """
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _rows_if_present(name: str) -> list[dict[str, str]] | None:
    """Një rezultat CSV që mund të mos ekzistojë ende, si `_load_if_present`."""
    path = RESULTS / name
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _provenance() -> tuple[dict[str, str], set[str], set[str]]:
    """Which run produced each result file.

    Every script records its own environment, and those environments are not one
    environment: the experiments were run in the order they were written, over
    several days, so the commit differs from file to file. Quoting a single commit
    for the whole thesis would read more tidily and would be untrue of every file
    but one, which is the sort of claim a reader can check in a minute.
    """
    commits: dict[str, str] = {}
    pythons: set[str] = set()
    platforms: set[str] = set()
    for path in sorted(RESULTS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        environment = data.get("environment") if isinstance(data, dict) else None
        if not environment:
            continue
        commits[path.name] = environment["commit"]
        pythons.add(environment["python"])
        platforms.add(environment["platform"])
    return commits, pythons, platforms


# ======================================================================
# Abstrakti
# ======================================================================
def abstract() -> list[str]:
    """Abstrakti, me çdo shifër të lexuar nga `data/results/`.

    Shifrat këtu janë të njëjtat që raporton Kapitulli 5, dhe lexohen nga i njëjti
    burim. Të shtypura me dorë, ato do të ishin i vetmi vend në punim ku një numër
    i rigjeneruar dhe një numër i shkruar mund të ndaheshin heshtazi — dhe do të
    ishte pikërisht faqja e parë që lexon komisioni.
    """
    rules = _load("rules_evaluation.json")
    ml = _load("ml_evaluation.json")
    dataset = _load("mlcq_dataset.json")
    reference = _load("system_reference.json")
    refactoring = _load_if_present("refactoring_evaluation.json")
    ceiling = _load_if_present("reviewer_agreement.json")

    primary = [
        rules["per_smell"][smell]["strategy"]["by_aggregation"]["mean"]
        for smell in sorted(rules["per_smell"])
    ]
    best = [
        ml["per_smell"][smell]["models"][ml["per_smell"][smell]["best_model"]]
        for smell in sorted(ml["per_smell"])
    ]
    severity = [
        rules["per_smell"][smell]["strategy"]["severity_agreement"]["kappa_quadratic"]
        for smell in sorted(rules["per_smell"])
    ]
    severity = [value for value in severity if value is not None]

    metrics = len(reference["metrics"]["class"]) + len(reference["metrics"]["method"])
    automated = len({s["automated"] for s in reference["strategies"] if s["automated"]})

    def band(values: list[float]) -> str:
        return f"{min(values):.3f} deri {max(values):.3f}"

    # Numri formatohet vetë e jo paragrafi: një herë zëvendësimi u lëshua mbi tërë
    # tekstin dhe i hoqi të gjitha presjet e fjalisë.
    samples = _count(dataset["rows"])

    paragraphs = [
        "Code smells janë simptoma të dizajnit të dobët që nuk shkaktojnë gabime, por e "
        "rrisin koston e çdo ndryshimi të ardhshëm. Identifikimi manual i tyre nuk "
        "shkallëzohet në sisteme të mëdha, ndërsa mjetet ekzistuese të analizës statike "
        "mbështeten kryesisht në pragje fikse të kalibruara gjetiu dhe rrallë "
        "propozojnë zgjidhje.",
        f"Ky punim ndërton një sistem që i zbulon code smells në dy mënyra të pavarura "
        f"dhe i krahason mbi të njëjtën të vërtetë bazë. Qasja e parë zbaton strategjitë "
        f"e publikuara të detektimit mbi {metrics} metrika; e dyta trajnon klasifikues "
        f"mbi po ato metrika. Të dyja vlerësohen mbi {samples} mostra nga "
        f"{_repositories_in_dataset()} depo Java, të etiketuara nga zhvillues "
        f"profesionistë, me ndarje të grupuar sipas depos dhe me të njëjtin kod "
        f"pikëzimi. Sistemi përfshin edhe një motor refaktorimi që rishkruan kod vetëm "
        f"kur i provon parakushtet e veta nga pema sintaksore, dhe një ndërfaqe web mbi "
        f"të tria.",
        f"Strategjitë e publikuara dolën të sakta por të kursyera: precizion "
        f"{band([m['precision'] for m in primary])} me recall "
        f"{band([m['recall'] for m in primary])}. Klasifikuesit i tejkaluan qartë, me "
        f"MCC {band([m['mcc'] for m in best])} kundrejt "
        f"{band([m['mcc'] for m in primary])}. Intervalet e besimit me bootstrap sipas depos "
        f"tregojnë se ajo përparësi e kalon zeron te të katër erërat.",
    ]

    third = (
        f"Dy rezultate janë negative dhe raportohen si të tilla. Ashpërsia që sistemi "
        f"e derivon nga teprica mbi pragje nuk e riprodhon gjykimin e rishikuesve: "
        f"pajtimi i matur me kappa me peshë qëndron te {band(severity)}, dhe gabimi "
        f"anon nga mbivlerësimi. "
    )
    if ceiling is not None:
        ceilings = [entry["mcc"] for entry in ceiling["per_smell"].values()]
        third += (
            f"Po ashtu, vetë rishikuesit pajtohen mes tyre me MCC {band(ceilings)}, "
            f"çka tregon se një pjesë e pareduktueshme e gabimit të çdo detektori i "
            f"takon përkufizimit të erës dhe jo detektorit. "
        )
    if refactoring is not None:
        share = refactoring["applied"] / refactoring["detected"]
        third += (
            f"Motori i refaktorimit automatizon {_word(automated)} transformime dhe transformoi "
            f"{share:.1%} të vendeve të detektuara; refuzimi trajtohet si rezultat i "
            f"saktë dhe numërohet. "
        )
    third += (
        "Kontributi kryesor nuk është një shifër e vetme, por një zinxhir i plotë dhe "
        "i riprodhueshëm, nga korpusi deri te rezultati."
    )

    paragraphs.append(third)
    return paragraphs


# ======================================================================
# Kapitulli 2
# ======================================================================
CHAPTER_2 = [
    (
        None,
        "",
        [
            "Detektimi automatik i code smells dhe refaktorimi studiohen prej më "
            "shumë se dy dekadash. Shqyrtimi mbështetet te artikuj në revista dhe "
            "konferenca me rishikim nga kolegët, te librat që e themeluan fushën dhe "
            "te dy shqyrtime sistematike, ai i Sharma & Spinellis (2018) dhe ai i "
            "Azeem et al. (2019), të cilat shërbyen edhe si pikënisje për burime të "
            "tjera. Burimet u kërkuan kryesisht në IEEE Xplore, ACM Digital Library "
            "dhe Springer, dhe grupohen sipas idesë që trajtojnë, jo sipas autorit. "
            "Kapitulli nis me atë që është një erë dhe pse ka rëndësi, kalon te "
            "mënyrat si matet dhe si detektohet, dhe mbyllet me hendekun që adreson "
            "ky punim.",
        ],
    ),
    (
        "2.1",
        "Code smells dhe ndikimi i tyre",
        [
            "Katalogun kanonik e jep Fowler (2018): njëzet e katër erëra, secila me "
            "refaktorimet që e adresojnë. Përkufizimi është qëllimisht cilësor. Një "
            "erë është simptomë, jo gabim, dhe nëse diçka është problem apo jo varet "
            "nga konteksti. Edhe erërat që duken sasiore, si metoda e gjatë apo klasa "
            "e madhe, nuk thonë sa rreshta janë shumë; pikërisht ky boshllëk e detyron "
            "çdo mjet të vendosë kufijtë e vet.",
            "A kanë erërat pasoja të matshme? Khomh et al. (2012) detektuan "
            "trembëdhjetë antimodele në 54 versione të katër sistemeve Java, ArgoUML, "
            "Eclipse, Mylyn dhe Rhino, dhe gjetën se klasat që marrin pjesë në to "
            "ndryshojnë dhe përmbajnë defekte më shpesh se klasat e tjera. Palomba et "
            "al. (2018) e përsëritën pyetjen në shkallë shumë më të madhe, mbi 395 "
            "versione të 30 projekteve me burim të hapur dhe 17 350 raste të "
            "validuara me dorë të trembëdhjetë erërave. Erërat që lidhen me kod të "
            "gjatë ose të ndërlikuar dolën më të përhapurat, dhe klasat e prekura "
            "dolën më të prirura ndaj ndryshimeve dhe defekteve se klasat pa erë.",
            "Efekti nuk është i njëjtë në çdo kontekst. Sjøberg et al. (2013) matën "
            "me saktësi kohën që gjashtë zhvillues shpenzuan për të mirëmbajtur katër "
            "sisteme Java me funksionalitet të njëjtë, dhe gjetën se efekti i "
            "dymbëdhjetë erërave mbi përpjekjen ishte i kufizuar; sipas tyre, "
            "zvogëlimi i madhësisë së kodit dhe i numrit të ndryshimeve premtonte më "
            "shumë se refaktorimi i erërave. Kjo nuk i bën erërat të "
            "parëndësishme, por tregon se madhësia duhet ndarë prej tyre në çdo "
            "analizë: një klasë e madhe ndryshon më shpesh edhe kur nuk ka asnjë erë "
            "tjetër.",
            "Tufano et al. (2015) ndoqën historikun e 200 projekteve me burim të "
            "hapur për të parë kur lindin erërat. Shumica e tyre futen që kur krijohet "
            "klasa ose metoda, jo gradualisht gjatë evolucionit, dhe rreth katër të "
            "pestat mbijetojnë në sistem. Nëse një erë lind bashkë me kodin, mjeti "
            "që e gjen ka më shumë vlerë kur vepron herët, para se kodi të rritet mbi "
            "të.",
            "Mbetet pyetja nëse zhvilluesit i shohin erërat si probleme reale. "
            "Yamashita & Moonen (2013) anketuan 85 zhvillues profesionistë për "
            "njohjen, interesin dhe rëndësinë që u japin erërave, duke nisur nga "
            "vërejtja se vlera e tyre si koncept i cilësisë mbetej e diskutueshme nga "
            "pikëpamja e zhvilluesit. Pyetja ka rëndësi për çdo detektor: ai vlen aq "
            "sa zhvilluesi e njeh gjetjen e tij si problem.",
        ],
    ),
    (
        "2.2",
        "Matja e cilësisë së dizajnit",
        [
            "Matja sasiore e sistemeve me objekte u bë e mundur me suitën e "
            "Chidamber & Kemerer (1994), gjashtë metrika për klasën: WMC, DIT, NOC, "
            "CBO, RFC dhe LCOM. WMC e peshon klasën me kompleksitetin e metodave të "
            "saj, DIT dhe NOC e vendosin në hierarkinë e trashëgimisë, CBO dhe RFC "
            "matin sa varet nga klasat e tjera, dhe LCOM mat sa pak i ndajnë metodat "
            "fushat e saj. Kompleksiteti i një metode matet zakonisht me numrin "
            "ciklomatik të McCabe (1976), pra me numrin e shtigjeve të pavarura në "
            "grafin e saj të kontrollit.",
            "LCOM-i origjinal rritet me katrorin e numrit të metodave dhe nuk "
            "krahason dot klasa me madhësi të ndryshme. Henderson-Sellers (1996) "
            "propozoi një variant të normalizuar mes 0 dhe 1, ndërsa Bieman & Kang "
            "(1995) prezantuan TCC-në, që e mat kohezionin me pjesën e çifteve të "
            "metodave që ndajnë të paktën një fushë. Mbi këto metrika ndërtohet "
            "pothuajse çdo detektim sasior i mëvonshëm.",
            "Lanza & Marinescu (2006) i organizojnë metrikat në tri përmasa: madhësinë "
            "dhe kompleksitetin, lidhjen me klasat e tjera, dhe trashëgiminë. Ata u "
            "shtuan edhe metrika të reja, si ATFD, LAA dhe FDP, që nuk matin madhësinë "
            "e një entiteti por marrëdhënien e tij me të dhënat e klasave të tjera. "
            "Këto janë metrikat që u duhen erërave të bashkëpunimit, si Feature Envy, "
            "të cilat nuk i kap dot asnjë metrikë madhësie.",
            "Sharma & Spinellis (2018), në një shqyrtim sistematik të fushës, vërejnë "
            "se përkufizimet e erërave në literaturë nuk janë konsistente, dhe as "
            "rezultatet e metodave të detektimit, ndaj mjetet krahasohen me "
            "vështirësi. Ata i ndajnë metodat e detektimit në disa familje, ndër të "
            "cilat ato që mbështeten te metrikat, te rregullat, te historiku i "
            "ndryshimeve dhe te mësimi i makinës; nënkapitujt që vijnë ndjekin këtë "
            "ndarje.",
        ],
    ),
    (
        "2.3",
        "Detektimi me rregulla mbi metrika",
        [
            "Marinescu (2004) prezantoi strategjitë e detektimit: rregulla që "
            "kombinojnë disa metrika me pragje, në vend që të mbështeten te një "
            "metrikë e vetme. Një strategji filtron fillimisht entitetet që e kalojnë "
            "secilin prag dhe pastaj i kombinon filtrat me «dhe» dhe «ose», ndaj "
            "arsyeja e çdo detektimi mbetet e lexueshme si kusht. Lanza & Marinescu "
            "(2006) e zgjeruan idenë në një katalog të plotë, ku çdo erë shprehet si "
            "kombinim kushtesh mbi metrika, me pragje të nxjerra statistikisht nga "
            "dyzet e pesë sisteme Java.",
            "Pragjet e tyre janë dy llojesh. Ato statistikore, si «i lartë» dhe "
            "«shumë i lartë», nxirren nga mesatarja dhe devijimi standard i metrikës "
            "në korpusin e tyre. Ato me kuptim të zakonshëm, si «pak» ose «një e "
            "treta», vijnë nga mënyra si njerëzit i përdorin këto fjalë. Të parat "
            "varen pra nga korpusi ku u matën, dhe kjo i bën pyetje të hapur për çdo "
            "korpus tjetër.",
            "Moha et al. (2010) propozuan DECOR-in, një metodë ku erërat përshkruhen "
            "në një gjuhë specifikimi dhe detektorët gjenerohen nga përshkrimet; "
            "zbatimi i saj u vlerësua me precizion dhe recall mbi sisteme me burim të "
            "hapur. Avantazhi i qasjeve me rregulla është se arsyeja e çdo detektimi "
            "lexohet qartë. Dobësia është ndjeshmëria ndaj pragjeve, që kalibrohen me "
            "vështirësi jashtë korpusit ku u nxorën.",
            "Palomba et al. (2015) i detektojnë erërat me HIST nga historiku i "
            "ndryshimeve, jo nga një pamje e vetme e kodit. Për pesë erëra, ndër to "
            "Blob dhe Feature Envy, ata treguan se historiku kap raste që analiza e "
            "kodit nuk i sheh, por qasja kërkon historikun e plotë të depos, që jo "
            "çdo projekt e ka dhe jo çdo dataset e ruan.",
            "Mjetet që përdoren në praktikë, si PMD (PMD Team, 2026), zbatojnë "
            "kryesisht këtë familje: rregulla me pragje të fiksuara, që zhvilluesi mund "
            "t'i ndryshojë por rrallë i ndryshon. Rezultati i tyre mbetet pra aq i "
            "mirë sa janë pragjet e parazgjedhura për kodin ku zbatohen.",
        ],
    ),
    (
        "2.4",
        "Detektimi me mësim të makinës",
        [
            "Ideja e mësimit të makinës është që pragjet t'i mësojë modeli nga "
            "shembuj të etiketuar, në vend që t'i vendosë njeriu. Arcelli Fontana et "
            "al. (2016) kryen një nga eksperimentet më të mëdha të këtij lloji: "
            "gjashtëmbëdhjetë algoritme mbi katër erëra (Data Class, Large Class, "
            "Feature Envy dhe Long Method), me 1 986 raste të validuara me dorë nga 74 "
            "sisteme. Ata raportuan performancë të lartë për shumicën e algoritmeve në "
            "validimin e kryqëzuar, me J48 dhe Random Forest si më të mirat dhe "
            "makinat me vektorë mbështetës si më të dobëtat. Studimi u bë pikë "
            "referimi për shumë punime pasuese.",
            "Di Nucci et al. (2018) vunë re megjithatë se aty çdo dataset kishte "
            "raste të një lloji të vetëm ere. Kur e përsëritën eksperimentin me "
            "dataset-e ku bashkëjetojnë disa erëra, performanca ra ndjeshëm. Pra "
            "shifra e raportuar varet nga mënyra si ndërtohet bashkësia e vlerësimit, "
            "jo vetëm nga algoritmi.",
            "E njëjta arsye qëndron pas njërës nga zgjedhjet kryesore të këtij "
            "punimi: trajnimi dhe testimi ndahen sipas depos, jo rastësisht sipas "
            "rreshtave. Mostrat e një depoje kanë të njëjtët autorë, të njëjtat "
            "konvencione e shpesh kod të kopjuar, dhe një ndarje e rastësishme i "
            "vendos në të dyja anët, duke i fryrë shifrat.",
            "Azeem et al. (2019), në një shqyrtim sistematik me meta-analizë, gjetën "
            "vetëm pesëmbëdhjetë studime që përdorin mësimin e makinës për këtë "
            "qëllim, nga mbi dy mijë punime fillestare, dhe përfundojnë se fusha ka "
            "ende vend për përmirësim. Ata e vendosin mësimin e makinës si përgjigje "
            "ndaj tri kufizimeve të detektorëve me rregulla: subjektivitetit të "
            "zhvilluesve, pajtimit të ulët mes detektorëve të ndryshëm dhe "
            "vështirësisë për të gjetur pragje të mira.",
            "Madeyski & Lewowski (2023) trajnuan klasifikues mbi MLCQ-në, me metrikat "
            "e mjeteve të përgjithshme të analizës statike si veçori, dhe raportuan "
            "koeficientin e Matthews-it në vend të saktësisë. Punimi i tyre është "
            "krahasimi më i afërt me këtë punim, sepse përdor të njëjtën të vërtetë "
            "bazë, dhe Kapitulli 6 i vë rezultatet përballë.",
            "Një kundërshtim i përsëritur ndaj modeleve është se nuk e shpjegojnë "
            "vendimin e tyre. Rëndësia e veçorive jep një përgjigje për tërë "
            "bashkësinë, por mënyra si llogaritet ka rëndësi: Strobl et al. (2007) "
            "treguan se rëndësia e bazuar te papastërtia në pyjet e rastësishme "
            "anon nga veçoritë me shumë vlera të mundshme, dhe propozuan matje që e "
            "shmangin këtë anim.",
        ],
    ),
    (
        "2.5",
        "E vërteta bazë dhe subjektiviteti",
        [
            "Çdo vlerësim i detektimit ka nevojë për një të vërtetë bazë, dhe këtu "
            "del një problem themelor. Mäntylä & Lassenius (2006), në një studim "
            "rasti në një kompani finlandeze produktesh softuerike, treguan se "
            "vlerësimi i zhvilluesve për praninë e një ere është subjektiv dhe se "
            "vlerësues të ndryshëm shpesh nuk pajtohen për të njëjtin modul.",
            "Madeyski & Lewowski (2020) ndërtuan MLCQ-në, një bashkësi mostrash Java "
            "të etiketuara nga zhvillues profesionistë për katër erëra, me ashpërsi "
            "në shkallën none/minor/major/critical. Mostrat vijnë nga projekte me "
            "burim të hapur të zgjedhura për rëndësi industriale, dhe për çdo "
            "rishikues publikohet edhe profili i përvojës së tij, ndaj çdo gjykim "
            "mund të lidhet me atë që e dha. Ky punim e përdor MLCQ-në si të vërtetë "
            "bazë, dhe mospajtimin mes rishikuesve e raporton si të dhënë, në vend që "
            "ta pastrojë si zhurmë.",
        ],
    ),
    (
        "2.6",
        "Refaktorimi i automatizuar",
        [
            "Opdyke (1992), në tezën e doktoratës, e formalizoi refaktorimin me "
            "nocionin e parakushteve: një transformim është i sigurt vetëm nëse disa "
            "kushte vërtetohen para se të aplikohet. Mbi këtë nocion mbështetet çdo "
            "motor refaktorimi që pretendon se e ruan sjelljen.",
            "Mens & Tourwé (2004), në shqyrtimin e tyre të fushës, e ndajnë procesin "
            "e refaktorimit në disa veprimtari: gjetja e vendit që duhet refaktoruar, "
            "zgjedhja e transformimit, garantimi që sjellja ruhet, aplikimi, "
            "vlerësimi i efektit mbi cilësinë, dhe ruajtja e përputhjes me artefaktet "
            "e tjera. Mjetet zakonisht mbulojnë vetëm aplikimin; ky punim synon të "
            "lidhë gjetjen, aplikimin dhe matjen e efektit në një zinxhir të vetëm.",
            "Tsantalis & Chatzigeorgiou (2009) propozuan një metodë për gjetjen e "
            "rasteve të Move Method si zgjidhje për Feature Envy. Algoritmi mat "
            "distancën mes entiteteve dhe klasave, propozon vetëm lëvizje që kalojnë "
            "një bashkësi parakushtesh, dhe vendimin e fundit ia lë projektuesit.",
            "Murphy-Hill et al. (2012), me të dhëna nga mbi trembëdhjetë mijë "
            "zhvillues, gjetën se refaktorimi shpesh përzihet me ndryshime të tjera "
            "dhe rrallë përmendet në mesazhet e commit-eve, ndaj matet me vështirësi "
            "nga historiku. Silva et al. (2016) i pyetën zhvilluesit pse refaktorojnë "
            "dhe gjetën se arsyet janë kryesisht praktike, të lidhura me një ndryshim "
            "konkret që duhet bërë.",
            "Lidhja mes refaktorimit dhe erërave është më e dobët nga sa pritet. "
            "Bavota et al. (2015), duke ndjekur refaktorimet në historikun e sistemeve "
            "me burim të hapur, gjetën se vetëm 42% "
            "e refaktorimeve prekin entitete me erë, dhe vetëm 7% e tyre e heqin "
            "erën nga klasa. Refaktorimi që bëjnë zhvilluesit, pra, nuk është në "
            "shumicën e rasteve ndreqje e një ere, dhe as ndreqja e një ere nuk është "
            "domosdoshmërisht e suksesshme; kjo e bën të nevojshme që çdo rishkrim "
            "automatik të matet pas aplikimit.",
        ],
    ),
    (
        "2.7",
        "Hendeku",
        [
            "Nga ky shqyrtim dalin tri vërejtje. Qasja me rregulla dhe ajo me mësim "
            "makine rrallë vlerësohen mbi të njëjtën të vërtetë bazë dhe me të "
            "njëjtat metrika, ndaj krahasimi i drejtpërdrejtë mungon. Jo çdo punim e "
            "thotë qartë si e ndan bashkësinë e vlerësimit, edhe pse shifra e "
            "raportuar varet pikërisht prej saj. Detektimi dhe refaktorimi, nga ana "
            "tjetër, trajtohen zakonisht veç e veç, ndaj mbetet pa përgjigje empirike "
            "nëse një erë e gjetur mund të ndreqet edhe automatikisht, dhe nëse ndreqja "
            "e heq vërtet. Kapitulli 3 i kthen këto vërejtje në problemin dhe pyetjet "
            "e punimit.",
        ],
    ),
]

# ======================================================================
# Kapitulli 3
# ======================================================================
CHAPTER_3 = [
    (
        None,
        "",
        [
            "**Situata ideale.** Për çdo pjesë të kodit, ekipi do të duhej të dinte "
            "nëse ka një problem dizajni, sa i rëndë është, dhe cili transformim e "
            "heq pa ndryshuar sjelljen. Ky gjykim do të duhej të ishte i përsëritshëm "
            "dhe i krahasuar me vlerësimin e zhvilluesve me përvojë.",
            "**Realiteti.** Identifikimi me dorë nuk shkallëzohet, dhe mjetet "
            "ekzistuese zakonisht vetëm njoftojnë, me pragje të kalibruara në "
            "projekte të tjera (Kapitulli 1). Studimet rrallë i vënë dy qasjet "
            "përballë njëra-tjetrës, dhe nuk matin sa nga erërat e gjetura ndreqen "
            "dot automatikisht (Nënkapitulli 2.7).",
            "**Fokusi i punës.** Ky punim i krahason dy qasjet e detektimit mbi të "
            "njëjtin korpus të etiketuar nga profesionistë, me ndarje sipas depos dhe "
            "me të njëjtën mënyrë pikëzimi, dhe mat sa nga vendet e detektuara mund "
            "të rishkruhen automatikisht pa sjellë gabime të reja kompilimi.",
        ],
    ),
    (
        "3.1",
        "Pyetjet kërkimore",
        [
            "Secila pyetje lidhet me një nga tri pjesët e sistemit:",
            (
                "bullet",
                "PK1: Sa e saktë është detektimi i bazuar në strategji metrikash, "
                "krahasuar me etiketimet manuale të zhvilluesve profesionistë?",
            ),
            (
                "bullet",
                "PK2: A e përmirëson një model i mësimit të makinës, i trajnuar mbi "
                "të njëjtat metrika, saktësinë e detektimit krahasuar me pragjet "
                "fikse?",
            ),
            (
                "bullet",
                "PK3: A i përmirësojnë objektivisht refaktorimet e propozuara "
                "karakteristikat strukturore të kodit, duke ruajtur kompilueshmërinë "
                "dhe sjelljen e tij?",
            ),
            "PK1 e vë gjykimin e pragjeve fikse përballë atij njerëzor. PK2 pyet nëse "
            "të njëjtat metrika, të përdorura ndryshe, japin më shumë. PK3 pyet nëse "
            "sistemi mund të shkojë përtej njoftimit pa e prishur kodin.",
        ],
    ),
    (
        "3.2",
        "Qëllimi dhe objektivat",
        [
            "Qëllimi i punimit është të projektohet, të implementohet dhe të "
            "vlerësohet empirikisht një sistem që gjen code smells në kod Java dhe "
            "propozon refaktorime konkrete e të verifikueshme për to. Objektivat "
            "janë:",
            (
                "bullet",
                "Të shqyrtohet literatura për metrikat e cilësisë së kodit, "
                "strategjitë e detektimit dhe refaktorimin.",
            ),
            (
                "bullet",
                "Të ndërtohet një motor analize që mat kodin Java në nivel klase dhe "
                "metode.",
            ),
            (
                "bullet",
                "Të implementohet detektimi me rregulla, me strategji të publikuara "
                "dhe me burimin e çdo pragu të deklaruar.",
            ),
            (
                "bullet",
                "Të trajnohet një klasifikues mbi të dhënat e MLCQ-së dhe të "
                "krahasohet me rregullat.",
            ),
            (
                "bullet",
                "Të ndërtohet një motor refaktorimi që i aplikon transformimet vetëm "
                "kur janë të sigurta dhe e verifikon rezultatin.",
            ),
            (
                "bullet",
                "Të ndërtohet një ndërfaqe web që ia bën rezultatet të përdorshme "
                "zhvilluesit.",
            ),
        ],
    ),
    (
        "3.3",
        "Formulimi i matshëm dhe kriteret e suksesit",
        [
            "Detektimi trajtohet si klasifikim binar: një klasë ose metodë është ose "
            "nuk është shembull i një ere të caktuar. E vërteta bazë vjen nga "
            "rishikuesit e MLCQ-së, dhe krahasimi bëhet me matricën konfuze dhe "
            "shifrat që dalin prej saj.",
            "Refaktorimi nuk është klasifikim, por transformim me parakushte, dhe "
            "pyetja e matshme është sa shpesh aplikohet pa e prishur kodin. "
            "Raportohen vendet e detektuara, ato të transformuara dhe arsyet pse të "
            "tjerat u refuzuan. Kriteret e suksesit janë:",
            (
                "bullet",
                "Për PK1: shifra për çdo erë mbi një korpus të deklaruar, të "
                "riprodhueshme me një komandë. Edhe një recall i ulët është përgjigje "
                "e vlefshme, për sa kohë nuk fshihet.",
            ),
            (
                "bullet",
                "Për PK2: krahasim mostër për mostër me detektimin me rregulla, plus "
                "një model bazë që nuk mëson asgjë, që fitimi të mos ngatërrohet me "
                "çekuilibrin e klasave.",
            ),
            (
                "bullet",
                "Për PK3: çdo rishkrim i aplikuar verifikohet se nuk e prish "
                "skedarin, dhe matet nëse era u hoq. Për ruajtjen e sjelljes nuk ka "
                "kriter, për arsyen që jepet te Nënkapitulli 3.4.",
            ),
        ],
    ),
    (
        "3.4",
        "Fushëveprimi dhe kufizimet",
        [
            "Punimi kufizohet te Java, sepse shumica e literaturës për metrikat e "
            "objekteve dhe dataset-et e etiketuara të code smells janë ndërtuar mbi "
            "kod Java. Vlerësohen vetëm erërat për të cilat ka strategji të "
            "publikuara dhe të dhëna të etiketuara. Analiza është statike: programi "
            "nuk ekzekutohet, ndaj sjellja gjatë ekzekutimit nuk mbulohet.",
            "Dy zgjedhje janë bërë me qëllim. E para, analizuesi regjistron fakte "
            "sintaksore dhe nuk zgjidh simbole. Prandaj një transformim që duhet të "
            "gjejë çdo referencë ndaj një emri nuk mund t'i provojë parakushtet e "
            "veta, dhe dy nga pesë transformimet e planifikuara mbeten vetëm "
            "propozim. Për të njëjtën arsye Introduce Parameter Object aplikohet "
            "vetëm te metodat «private», thirrjet e të cilave mbeten brenda skedarit. "
            "E dyta, refaktorimi bëhet me transformime mbi pemën sintaksore dhe jo me "
            "gjenerim teksti, sepse ajo që aplikohet duhet të jetë e saktë. Kur "
            "siguria nuk provohet, refuzimi konsiderohet rezultat i saktë.",
            "Korpusi mban nga depot e MLCQ-së vetëm skedarët «.java», pa skedarë "
            "ndërtimi dhe pa varësi, dhe disa depo nuk gjenden më. Prandaj çdo "
            "rishkrim kontrollohet vetëm me kompilator: nëse kompilon, ose të paktën "
            "nëse nuk shton lloj të ri gabimi. Ruajtja e sjelljes, që përmend PK3, "
            "**nuk verifikohet empirikisht në këtë punim**, sepse do të kërkonte "
            "ekzekutimin e testeve të projekteve, gjë që korpusi nuk e lejon.",
        ],
    ),
]

# ======================================================================
# Kapitulli 4
# ======================================================================
def _repositories_in_dataset() -> int:
    """Depot nga të cilat vijnë mostrat e vlerësuara.

    `mlcq_dataset.json` ruan 522, numrin e depove që përmend MLCQ-ja. Dhjetë prej
    tyre nuk ishin më të arritshme, ndaj mostrat vijnë nga më pak depo; abstrakti
    dhe Kapitulli 5 e shkruanin 522 si burim të mostrave (VD-118).
    """
    with (RESULTS / "mlcq_dataset.csv").open(encoding="utf-8") as handle:
        return len({row["repository"] for row in csv.DictReader(handle)})


def _negative_share() -> str:
    """Pjesa e mostrave negative nën agregimin parësor, e lexuar nga tabela e veçorive.

    Ishte shtypur «78%», shifër e një versioni më të hershëm të tabelës (VD-118).
    """
    path = RESULTS / "mlcq_dataset.csv"
    if not path.exists():
        return "shumica"
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    positives = sum(1 for row in rows if row["smelly_mean"] == "1")
    return f"{1 - positives / len(rows):.0%}"


def _coverage_sentence() -> str:
    """Sa nga MLCQ-ja hyri në vlerësim. Nënkapitujt 3.4 dhe 6.6 i referohen këtij numri."""
    dataset = _load("mlcq_dataset.json")
    coverage = _load("mlcq_matching.json")["corpus_coverage"]
    missing = dataset["samples_considered"] - dataset["rows"]
    no_file = dataset["unreached"].get("no_file", 0)
    unreachable = coverage["repositories_total"] - coverage["repositories_available"]
    return (
        f"MLCQ-ja përmend {dataset['samples_considered']} mostra në "
        f"{coverage['repositories_total']} depo, nga të cilat {unreachable} nuk ishin më të "
        f"arritshme. Jashtë vlerësimit mbetën {missing} mostra: {no_file} sepse skedari nuk "
        f"ishte në korpus, dhe {missing - no_file} sepse entiteti nuk u përputh ose "
        "skedari kishte gabim sintakse."
    )


# Gjendja e validimit në verifikimin e fundit, e njëjta me `docs/ROADMAP.md`.
# Nuk lexohet nga një skedar rezultati, sepse testet nuk shkruajnë të tillë; kur
# suita rritet, këto ndryshohen bashkë me ROADMAP-in.
VALIDATION_DATE = "25 shtator 2026"
BACKEND_TESTS = 717
COVERAGE = "96%"
FRONTEND_TESTS = 165

# Versionet e varësive që kanë rol në rezultate ose në sistem, ashtu si janë
# fiksuar te `backend/requirements*.txt`, `frontend/package.json` dhe
# `docs/thesis/requirements.txt`. Një version i ndryshuar atje duhet ndryshuar
# edhe këtu.
TECHNOLOGIES = [
    ["Python", "3.13", "gjuha e backend-it dhe e eksperimenteve"],
    ["tree-sitter, tree-sitter-java", "0.26.0, 0.23.5", "analiza sintaksore e Java-s"],
    ["scikit-learn", "1.9.0", "modelet, ndarja e grupuar, rëndësia e veçorive"],
    ["NumPy, SciPy", "2.5.2, 1.18.1", "llogaritjet numerike"],
    ["FastAPI, Uvicorn, Pydantic", "0.141.1, 0.52.4, 2.13.5",
     "shërbimi HTTP dhe validimi i kërkesave"],
    ["JDK (javac)", "21", "verifikimi i rishkrimeve me kompilator"],
    ["Git", "—", "shkrimi i kthyeshëm i rishkrimeve në disk"],
    ["PMD", "7.27.0", "mjeti i jashtëm i krahasimit"],
    ["React, TypeScript, Vite", "18.3.1, 5.7.2, 6.4.3", "ndërfaqja web dhe ndërtimi i saj"],
    ["Tailwind CSS, Recharts, lucide-react", "4.1.14, 2.15.4, 0.548.0",
     "stili, grafikët dhe ikonat e ndërfaqes"],
    ["pytest, Vitest, Playwright, axe-core", "9.1.1, 4.1.11, 1.56.1, 4.13.0",
     "testet e backend-it, të ndërfaqes, end-to-end dhe të aksesueshmërisë"],
    ["Ruff, mypy", "0.16.4, 2.3.1", "stili i kodit dhe kontrolli strikt i tipave"],
    ["Matplotlib, python-docx", "3.11.1, 1.2.0", "figurat dhe ky dokument"],
]  # fmt: skip

def _unsourced_thresholds() -> str:
    """Cilat pragje nuk vijnë nga një burim, të lexuara nga vlerat e eksportuara.

    Teksti thoshte «çdo numër aty ka citim; një vlerë që nuk i atribuohet dot një
    burimi nuk përdoret». Katër pragje nuk kanë burim të botuar, dhe auditi i 19
    shtatorit e gjeti pohimin të pavërtetë (VD-133).
    """
    values = _load("system_reference.json")["thresholds"]

    def at(name: str) -> str:
        return f"{values[name]:g}"

    return (
        "Katër pragje nuk kanë burim të botuar dhe i ka zgjedhur autori: kufiri i "
        f"Long Method ({at('long_method_loc')} rreshta), dy kushte të Brain Method (CC ≥ "
        f"{at('brain_method_cc')}, ndërfutja ≥ {at('brain_method_nesting')}) dhe kufiri i Deep "
        f"Nesting (> {at('deep_nesting')}). Ndjeshmëria ndaj të parit matet te Nënkapitulli 5.5, "
        "ndërsa tre të tjerët nuk maten dot kundrejt MLCQ-së. Të autorit janë edhe tre pragjet "
        "e ashpërsisë (Shtojca 8.7); të tjerat vijnë nga Lanza & Marinescu (Shtojca 8.2)."
    )


def _reference_value(name: str) -> str:
    """Një prag i sistemit, i lexuar nga vlerat e eksportuara e jo i shtypur."""
    value = _load("system_reference.json")["thresholds"][name]
    if abs(value - 1 / 3) < 1e-9:
        return "1/3"
    return f"{value:g}"


def _experiment_setup() -> dict[str, str]:
    """Konfigurimi i eksperimentit, siç e regjistrojnë vetë skedarët e rezultateve.

    Fara, numri i foldeve dhe i rimostrimeve dhe mjedisi i ekzekutimit ruhen nga
    skriptet në çdo skedar rezultati. Të shtypura këtu, do të ndaheshin nga ata
    skedarë në rigjenerimin e parë me një konfigurim tjetër.
    """
    ml = _load("ml_evaluation.json")
    boot = _load("bootstrap_intervals.json")
    sweep = _load("threshold_sweep.json")
    platform = ml["environment"]["platform"].split("-")
    return {
        "seed": str(ml["seed"]),
        "folds": _word(int(ml["folds"])),
        "resamples": _count(int(boot["resamples"])),
        "factors": ", ".join(f"{factor:g}" for factor in sweep["factors"]),
        "system": " ".join(platform[:2]),
        "python": ml["environment"]["python"],
    }


_SETUP = _experiment_setup()


CHAPTER_4 = [
    (
        None,
        "",
        [
            "Ky kapitull përshkruan si u ndërtua sistemi dhe si u krye eksperimenti, me "
            "aq hollësi sa një lexues tjetër ta përsërisë. Radha ndjek rrugën e të "
            "dhënave: arkitektura dhe teknologjitë (4.1–4.2), korpusi dhe matja "
            "(4.3–4.4), tri qasjet (4.5–4.7), ndërfaqja (4.8), mënyra e vlerësimit "
            "(4.9), validimi i sistemit (4.10), riprodhueshmëria dhe mjedisi (4.11), "
            "etika (4.12) dhe kërcënimet ndaj vlefshmërisë (4.13). Rezultatet nuk "
            "jepen këtu; ato janë te Kapitulli 5.",
            "**Qasja e kërkimit.** Kërkimi është sasior dhe eksperimental. Pyetjet "
            "kërkimore pyesin «sa» dhe «a e përmirëson», dhe përgjigjen e marrin nga "
            "matje të përsëritshme mbi të njëjtin korpus: metrikat e kodit, etiketat "
            "e rishikuesve të MLCQ-së dhe verdiktet e kompilatorit. E vetmja pjesë "
            "cilësore është vlerësimi me rubrikë i një mostre rishkrimesh "
            "(Nënkapitulli 4.7), sepse vlera e një rishkrimi për zhvilluesin nuk "
            "matet vetëm me kompilim.",
            "**Dizajni.** Çdo mostër e MLCQ-së gjykohet nga të dyja qasjet e "
            "detektimit, ndaj dallimi mes tyre nuk ngatërrohet me dallimin mes "
            "mostrave. Variabla e pavarur është qasja e detektimit, dhe te refaktorimi "
            "lloji i transformimit; variablat e varura janë treguesit e Nënkapitullit "
            "4.9. Për PK2 hipoteza zero është se MCC-ja e Qasjes B nuk ndryshon nga ajo "
            "e Qasjes A. Ajo hidhet poshtë për një erë kur intervali 95% i dallimit "
            "B − A, i llogaritur me bootstrap sipas depos, nuk e përmban zeron.",
            "**Hapat e studimit.** Eksperimenti kryhet në tetë hapa, secili me skriptin "
            "e vet, sipas radhës së Shtojcës 8.5:",
            ("bullet", "materializimi i korpusit: çdo depo e MLCQ-së shkarkohet në "
                       "commit-in që panë rishikuesit;"),
            ("bullet", "përputhja e çdo mostre me entitetin që prodhon analizuesi;"),
            ("bullet", "matja e çdo entiteti dhe ruajtja e tabelës së veçorive;"),
            ("bullet", "pikëzimi i strategjive të Qasjes A kundrejt etiketave;"),
            ("bullet", "trajnimi i modeleve të Qasjes B dhe pikëzimi i tyre jashtë "
                       "fold-it, bashkë me ablacionin mbi metrikat e strategjive;"),
            ("bullet", "krahasimi i dy qasjeve mostër për mostër, me intervale besimi;"),
            ("bullet", "ekzekutimi i motorit të refaktorimit mbi korpus, me verifikim "
                       "dhe rimatje;"),
            ("bullet", "analizat dytësore: ndjeshmëria dhe kalibrimi i pragjeve, "
                       "krahasimi me PMD-në dhe pajtimi mes rishikuesve."),
        ],
    ),
    (
        "4.1",
        "Arkitektura e sistemit",
        [
            "Sistemi, i quajtur JavaSmell, është ndërtuar si një zinxhir shtresash ku "
            "varësia shkon në një drejtim: një modul importon vetëm nga shtresat para "
            "tij. Kështu çdo shtresë testohet veç, dhe logjika e detektimit nuk "
            "përzihet me transportin. Shtresat dhe rrjedha e të dhënave janë:",
            ("figure", str(FIGURES / "arkitektura_e_sistemit.png"),
             "Arkitektura e sistemit dhe rrjedha e të dhënave"),
            (
                "bullet",
                "parsing: lexon skedarët «.java» me tree-sitter dhe regjistron vetëm "
                "fakte sintaksore: deklarime, thirrje dhe qasje në fusha (emër i "
                "thjeshtë, «this.x» ose «marrësi.anëtari»). Nuk zgjidh simbole.",
            ),
            (
                "bullet",
                "model dhe metrics: strukturat e të dhënave për klasat, metodat dhe "
                "fushat, dhe metrikat e tyre, të llogaritura me një kalim të vetëm "
                "mbi çdo klasë.",
            ),
            (
                "bullet",
                "detectors: funksione të pastra që marrin një entitet dhe pragjet, "
                "dhe kthejnë erën bashkë me kushtet e vlerësuara. Të gjitha pragjet "
                "numerike janë në një skedar.",
            ),
            (
                "bullet",
                "ml dhe refactor: Qasja B dhe Qasja C, që përdorin daljen e "
                "detektorëve por nuk importojnë njëra-tjetrën.",
            ),
            (
                "bullet",
                "projects: shkarkon në disk një depo publike të GitHub-ut, që të "
                "analizohet.",
            ),
            (
                "bullet",
                "api: vetëm transport (validim, serializim, gabime), pa logjikë "
                "detektimi apo refaktorimi.",
            ),
            (
                "bullet",
                "frontend: ndërfaqja web, që komunikon me shërbimin vetëm përmes "
                "HTTP.",
            ),
            "Gjatë një analize parsohet i gjithë projekti, sepse disa metrika kërkojnë "
            "klasat e tjera të tij. Pastaj çdo entitet matet, detektorët vlerësojnë "
            "strategjitë, modeli jep verdiktin e vet kur kërkohet, dhe motori prodhon "
            "një diff të verifikuar për çdo erë që ka transformim të automatizuar. E "
            "njëjta rrjedhë thirret nga rreshti i komandës dhe nga shërbimi HTTP. "
            "Skriptet e eksperimenteve, te evaluation dhe scripts/, përdorin po këto "
            "shtresa mbi korpusin, ndaj çdo numër i punimit vjen nga i njëjti kod që "
            "përdor zhvilluesi.",
            "**Modeli i të dhënave.** Për çdo skedar, parser-i ndërton një njësi me "
            "paketën, importet dhe klasat e saj. Një klasë mban llojin (class, "
            "interface, enum ose record), emrin, modifikuesit, superklasën, "
            "ndërfaqet, fushat, metodat dhe rangun e rreshtave. Një metodë mban "
            "tipin që kthen, parametrat me tipet e tyre, variablat lokale që "
            "deklaron, emrat e thjeshtë që lexon, qasjet e formës «this.x» dhe "
            "«marrësi.anëtari», thirrjet me marrës dhe pa marrës, dhe tipet që "
            "përmend. Këto janë të gjitha fakte që lexohen drejtpërdrejt nga pema; "
            "asnjëra nuk kërkon të dihet se çfarë tipi ka një shprehje e ndërlikuar.",
            "**Rreshti i komandës.** Analiza nis me «python -m javasmell» dhe dosjen e "
            "projektit. Gjetjet dalin si tekst, JSON ose CSV, metrikat e çdo entiteti "
            "si tabelë, dhe rishkrimet e sigurta si patch i unifikuar që autori e "
            "lexon para se ta aplikojë. Si portë ndërtimi, opsioni «--fail-on» e mbyll "
            "komandën me kod 3 kur mbetet një gjetje në ashpërsinë e kërkuar ose mbi "
            "të, ndërsa kodet 1 dhe 2 i mbeten dështimit të vetë mjetit. Opsioni "
            "«--thresholds» lexon nga një skedar TOML vetëm pragjet që ndryshojnë, dhe "
            "i shkruan ato në dalje, që një raport me pragje të lëvizura të mos "
            "ngatërrohet me një të matur me vlerat e botuara.",
        ],
    ),
    (
        "4.2",
        "Teknologjitë e përdorura",
        [
            "Backend-i dhe eksperimentet janë në Python, ndërfaqja në TypeScript. Të "
            "gjitha varësitë janë falas, me licencë të hapur dhe me version të "
            "fiksuar, që një rezultat të mund të riprodhohet me të njëjtat versione.",
            ("table", "Teknologjitë e përdorura dhe roli i tyre",
             ["Teknologjia", "Versioni", "Roli"], TECHNOLOGIES),
            "Zgjedhjet kryesore kanë arsye konkrete. tree-sitter u preferua ndaj një "
            "analizuesi që kërkon ndërtimin e projektit, sepse korpusi nuk mban "
            "skedarë ndërtimi dhe shumica e skedarëve të tij nuk kompilojnë të vetëm; "
            "një analizues që toleron gabimet jep pemë të plotë edhe për ta. "
            "scikit-learn ofron në një vend ndarjen e grupuar, dy ansamblet e pemëve "
            "dhe rëndësinë me permutim, ndaj asnjëra prej tyre nuk u shkrua nga e "
            "para. FastAPI dhe Pydantic e validojnë çdo kërkesë nga tipet e "
            "deklaruara, dhe TypeScript e bën kontratën me ndërfaqen të kontrollueshme "
            "që gjatë ndërtimit. JDK 21 është versioni me mbështetje afatgjatë, ndaj "
            "javac-u i tij është kompilatori i verifikimit. PMD zgjidhet si mjet i "
            "jashtëm krahasimi, sepse zbaton dy nga strategjitë e Lanza & Marinescu "
            "(2006) dhe është i lirë. Sistemi nuk përdor asnjë model gjuhësor apo "
            "shërbim me pagesë.",
        ],
    ),
    (
        "4.3",
        "Korpusi dhe e vërteta bazë",
        [
            "MLCQ (Madeyski & Lewowski, 2020) përmban 14 739 rishikime të 4 770 "
            "mostrave kodi, të bëra nga 26 zhvillues profesionistë për katër erëra: "
            "Blob dhe Data Class në nivel klase, Feature Envy dhe Long Method në nivel "
            "metode. Çdo rishikim i jep mostrës një ashpërsi në shkallën none, minor, "
            "major dhe critical, ku «none» do të thotë se rishikuesi nuk e sheh erën. "
            "Mostrat vijnë nga projekte me burim të hapur, por vetë kodi nuk është "
            "pjesë e dataset-it: çdo rresht tregon depon, commit-in, skedarin dhe "
            "rangun e rreshtave të entitetit.",
            "**Materializimi.** Për çdo depo u shkarkua arkivi i commit-it të "
            "rishikuar, dhe prej tij u mbajtën vetëm skedarët «.java». Merret depoja e "
            "plotë e jo vetëm skedari i mostrës, sepse ATFD, CBO, DIT dhe NOC "
            "përkufizohen kundrejt tipave të tjerë të projektit, dhe një skedar i "
            "vetëm do të dukej pothuajse pa qasje në të dhëna të huaja. Shkarkimi është "
            "inkremental dhe mund të ndërpritet: depot e përfunduara kapërcehen, "
            "dështimet riprovohen, dhe një manifest e ruan gjendjen e secilës depo pas "
            "çdo hapi.",
            "Nëse një depo ishte zhvendosur, ajo u ndoq vetëm kur commit-i gjendej "
            "edhe te vendi i ri. Meqë SHA-ja e git-it është hash i përmbajtjes, një "
            "commit i gjetur garanton se kodi është i njëjti që panë rishikuesit. Kur "
            "nuk gjendet, depoja nuk zëvendësohet me hamendje.",
            "**Përputhja.** Një mostër e MLCQ-së lidhet me entitetin përkatës sipas "
            "rangut të rreshtave, dhe lidhja verifikohet me emrin. Renditja e kundërt "
            "nuk do të punonte, sepse emri i entitetit në dataset shfaqet në katër "
            "formate të ndryshme, ndërsa rangu i rreshtave përputhet pothuajse "
            "gjithmonë me atë të parser-it. Ky ankorim zgjidh pa asnjë zgjidhës "
            "simbolesh dy rastet që dukeshin të vështira: dy mbingarkesa të një "
            "metode nuk nisin në të njëjtin rresht, dhe as një klasë e brendshme me "
            "klasën që e përmban. Një mostër që nuk lidhet nuk detyrohet të lidhet: "
            "shkaku regjistrohet (skedari mungon, ka gabim sintakse, ose te rreshtat e "
            "dhënë nuk ka entitet me atë emër) dhe mostra del nga vlerësimi.",
            "**Etiketa.** Ashpërsitë e rishikuesve kthehen në numra nga 0 (none) te 3 "
            "(critical), dhe për çdo mostër merret mesatarja e tyre, e rrumbullakosur "
            "te numri i plotë më i afërt me gjysmën drejt lart. Mostra quhet pozitive "
            "kur rezultati është mbi zero; te dy rishikues, pra, mjafton që njëri ta "
            "shohë erën. Si analizë ndjeshmërie përdoren edhe maksimumi, minimumi dhe "
            "unanimiteti, ku mostrat me mospajtim hidhen. Çdo mostër pikëzohet vetëm "
            "për erën për të cilën u rishikua, ndaj një mostër e Blob-it nuk hyn si "
            "negative në vlerësimin e Data Class-it.",
        ],
    ),
    (
        "4.4",
        "Matja e metrikave",
        [
            "Analizuesi mbështetet te tree-sitter (Brunsfeld et al.), dhe mbi pemën "
            "që ai prodhon maten shtatëmbëdhjetë metrika klase dhe nëntë metrika "
            "metode, me një kalim për klasë. Ndër to janë metrikat e Chidamber & "
            "Kemerer (1994), varianti i normalizuar i LCOM-it nga Henderson-Sellers "
            "(1996), TCC-ja e Bieman & Kang (1995) dhe kompleksiteti ciklomatik "
            "(McCabe, 1976), i matur si numri i pikave të vendimit në trupin e "
            "metodës plus një. Përkufizimet e të gjitha metrikave jepen te Shtojca 8.3.",
            "Rreshtat e kodit numërohen si rreshta logjikë, sipas dallimit të Park "
            "(1992) mes rreshtave fizikë dhe logjikë: rreshtat bosh, komentet dhe "
            "rreshtat që kanë vetëm shenja si «}» ose «});» nuk numërohen.",
            "**Metrikat e metodës.** ATFD numëron atributet e klasave të tjera të "
            "projektit që metoda i lexon, drejtpërdrejt ose përmes një akses-metode, "
            "që njihet nga parashtesa «get», «set», «is» ose «has». FDP numëron "
            "klasat nga vijnë këto atribute. LAA është pjesa e qasjeve në atribute që "
            "bien mbi klasën e vet, dhe merr vlerën 1 kur metoda nuk prek asnjë "
            "atribut. NOAV numëron variablat lokale dhe atributet që metoda prek, "
            "ndërsa CINT mat sa operacione të ndryshme thërret ajo. Një thirrje me "
            "sjellje mbi një objekt tjetër është lidhje, jo qasje në të dhëna, ndaj "
            "hyn te CINT dhe CBO por jo te ATFD.",
            "**Metrikat e klasës.** WMC është shuma e kompleksitetit ciklomatik të "
            "metodave, ndërsa AMW mesatarja e tij. TCC është pjesa e çifteve të "
            "metodave publike që ndajnë të paktën një fushë; konstruktorët "
            "përjashtohen, sepse prekin çdo fushë, dhe kur klasa ka më pak se dy metoda "
            "publike, TCC merr vlerën 1. WOC është pjesa e anëtarëve publikë që nuk "
            "janë akses-metoda, NOPA numri i fushave publike që nuk janë konstante, "
            "dhe NOAM numri i akses-metodave.",
            "Metrikat ATFD, CBO, DIT dhe TCC varen nga tipat e tjerë të projektit, "
            "ndaj çdo depo analizohet e plotë. Si «e huaj» numërohet vetëm një klasë "
            "që i përket projektit, që thirrjet në bibliotekën standarde të mos e "
            "fryjnë ATFD-në. Tipi i marrësit gjendet vetëm kur marrësi është një "
            "identifikues i vetëm; një shprehje si «a.getB().getC()» lihet jashtë në "
            "vend që të hamendësohet, ndaj matja anon nga vlera më e ulët.",
        ],
    ),
    (
        "4.5",
        "Qasja A: detektimi me rregulla",
        [
            "Sistemi zbaton tetë strategji. God Class, Data Class, Feature Envy dhe "
            "Brain Method janë marrë ashtu siç i publikuan Lanza & Marinescu (2006). "
            "Large Class, Long Method dhe Long Parameter List ndjekin përshkrimet e "
            "Fowler-it (2018), ndërsa Deep Nesting mat sa thellë janë futur blloqet "
            "brenda njëri-tjetrit. Kushtet dhe burimi i secilës janë te Shtojca 8.1.",
            "**Si shprehen strategjitë.** Secila strategji është kombinim kushtesh mbi "
            "metrika, jo një metrikë e vetme. God Class kërkon njëkohësisht "
            f"kompleksitet të lartë (WMC ≥ {_reference_value('god_class_wmc')}), "
            f"kohezion të ulët (TCC < {_reference_value('god_class_tcc')}) dhe qasje "
            f"në të dhëna të huaja (ATFD > {_reference_value('god_class_atfd')}). "
            "Feature Envy kërkon që metoda të lexojë shumë atribute të huaja (ATFD > "
            f"{_reference_value('feature_envy_atfd')}), më shumë të huaja se të vetat "
            f"(LAA < {_reference_value('feature_envy_laa')}), por nga pak klasa (FDP ≤ "
            f"{_reference_value('feature_envy_fdp')}). Data Class kërkon një "
            "sipërfaqe publike pothuajse pa sjellje (WOC < "
            f"{_reference_value('data_class_woc')}), me shumë fusha publike ose "
            "akses-metoda dhe me kompleksitet të ulët. Long Method kërkon vetëm që "
            f"rreshtat efektivë të kalojnë {_reference_value('long_method_loc')}.",
            _unsourced_thresholds(),
            "Kundrejt MLCQ-së vlerësohen katër strategji: God Class kundrejt etiketës "
            "«blob», dhe Data Class, Feature Envy e Long Method kundrejt etiketave me "
            "të njëjtin emër. Për Blob-in pikëzohet edhe një variant që bashkon God "
            "Class me Large Class, detektorin që shikon vetëm madhësinë.",
            "Një detektor nuk kthen thjesht po ose jo, por kushtet që vlerësoi me "
            "vlerat e matura. Kjo i lejon ndërfaqes të shpjegojë pse u shënua diçka "
            "dhe punimit të raportojë cili kusht e mbajti detektimin.",
            "**Ashpërsia.** Për çdo kusht të plotësuar llogaritet teprica e, raporti "
            "mes matjes v dhe pragut t. Kur kushti kërkon që matja të jetë mbi prag, "
            "teprica është:",
            ("equation", "e = v / t"),
            "Kur kushti kërkon që matja të jetë nën prag, si te TCC-ja, raporti "
            "përmbyset, që teprica të jetë përsëri së paku 1 dhe kushtet me drejtim të "
            "kundërt të mesatarizohen bashkë:",
            ("equation", "e = t / v"),
            "Rezultati i gjetjes është mesatarja e tepricave të saj, ku secila "
            f"kufizohet te {_reference_value('excess_cap')}, që një metrikë e vetme "
            "ekstreme të mos e shtyjë një rast të butë te niveli më i lartë; shuma "
            "merret mbi të n kushtet e strategjisë:",
            ("equation", f"s = (1 / n) · Σ min(e, {_reference_value('excess_cap')})"),
            f"Gjetja quhet minor kur s < {_reference_value('severity_major')}, major "
            f"kur {_reference_value('severity_major')} ≤ s < "
            f"{_reference_value('severity_critical')}, dhe critical përndryshe. "
            "Shkalla është ajo e MLCQ-së, ndaj ashpërsia e derivuar krahasohet "
            "drejtpërdrejt me atë të rishikuesve.",
        ],
    ),
    (
        "4.6",
        "Qasja B: detektimi me mësim makine",
        [
            "Vlerësohen katër modele: klasifikuesi i shumicës, regresioni logjistik, "
            "Random Forest (Breiman, 2001) dhe Gradient Boosting (Friedman, 2001), të "
            "gjitha me scikit-learn (Pedregosa et al., 2011). Si veçori përdoren të "
            "gjitha metrikat e Nënkapitullit 4.4, jo vetëm ato të strategjive. Për "
            "erërat e klasës vektori ka shtatëmbëdhjetë metrika klase; për erërat e "
            "metodës ka nëntë metrika metode bashkë me metrikat e klasës që e "
            "përmban, gjithsej 26. Parashtesa «c_» shënon një metrikë klase dhe «m_» "
            "një metrikë metode, sepse disa metrika, si ATFD, maten në të dy nivelet.",
            "**Konfigurimi.** Klasifikuesi i shumicës parashikon gjithmonë «pa erë» "
            "dhe shërben si model bazë. Regresioni logjistik përdoret pas "
            "standardizimit të veçorive, sepse vetëm ai është i ndjeshëm ndaj "
            "shkallës: pa të, LCOM-i, që arrin mijëra, do ta mbulonte TCC-në, që "
            "qëndron mes 0 dhe 1. Random Forest ndërtohet me 300 pemë, ndërsa "
            "Gradient Boosting përdor variantin me histograma të scikit-learn me "
            "parametrat e parazgjedhur. Hiperparametrat nuk akordohen: akordimi do të "
            "kërkonte një ndarje të dytë brenda çdo fold-i, dhe pa të do të rridhte "
            f"informacion nga bashkësia e testimit. Të gjitha modelet përdorin farën "
            f"{_SETUP['seed']}.",
            "**Ndarja.** Ndarja bëhet me GroupKFold në "
            f"{_SETUP['folds']} folde sipas depos, që mostrat e një projekti të mos "
            "jenë njëkohësisht në trajnim dhe në testim (Nënkapitulli 2.4). Një ndarje "
            "e rastësishme sipas rreshtave do të ishte rast i asaj që Kaufman et al. "
            "(2012) e quajnë rrjedhje: modeli do të mësonte nga të dhëna që në "
            "përdorim real nuk i ka. Çdo mostër parashikohet një herë, nga një model "
            "që nuk e ka parë projektin e saj. Kështu modeli jep dalje të së njëjtës "
            "formë si detektorët, dhe të dy krahasohen mostër për mostër.",
            "Çekuilibri i klasave trajtohet me pesha, jo me mbi-mostrim, sepse "
            "mbi-mostrimi do t'i kopjonte rreshtat përtej kufirit të fold-it dhe do "
            "ta prishte grupimin. Bashkësia e testimit nuk ribalancohet.",
            "**Ablacioni.** Modelet trajnohen edhe vetëm me metrikat që lexon "
            "strategjia përkatëse: te Blob WMC, TCC dhe ATFD e klasës, te Feature Envy "
            "ATFD, LAA dhe FDP e metodës, te Data Class WOC, NOPA, NOAM dhe WMC, dhe te "
            "Long Method vetëm MLOC. Foldet, fara dhe pikëzimi mbeten të njëjta, ndaj "
            "dallimi me modelin e plotë tregon sa nga fitimi vjen nga kufiri i mësuar "
            "dhe sa nga metrikat shtesë.",
            "**Rëndësia dhe shpjegimi.** Rëndësia e veçorive matet me permutation "
            "importance mbi fold-in e testimit, me dhjetë përsëritje, sepse rëndësia e "
            "bazuar te papastërtia favorizon veçoritë me shumë vlera të ndryshme "
            "(Strobl et al., 2007). Kjo tregon cila metrikë ka peshë në tërë "
            "korpusin, por jo pse u shënua një entitet i caktuar. Prandaj çdo verdikt "
            "pozitiv shpjegohet veç: çdo metrikë, një nga një, zëvendësohet me "
            "mesoren e bashkësisë së trajnimit dhe modeli pyetet sërish. Nëse ky "
            "ndryshim i vetëm e ul probabilitetin nën 0.5, ajo metrikë e mban "
            "verdiktin, dhe ndërfaqja e shkruan si fjali: «po të ishte CLOC-u tipik, "
            "kjo klasë nuk do të shënohej». Metoda vlen për çdo lloj modeli, por "
            "shikon një metrikë në një kohë: kur dy metrika mbajnë të njëjtin "
            "informacion, ndryshimi i njërës mund të mos lëvizë asgjë, dhe rasti "
            "mbetet pa shpjegim. Edhe shpjegimet llogariten jashtë fold-it.",
            "Për ndërfaqen, modeli më i mirë i secilës erë trajnohet sërish mbi të "
            "gjitha mostrat dhe ruhet në disk me një manifest që mban veçoritë, "
            "versionet dhe farën. Ai pyetet vetëm kur përdoruesi e kërkon; nëse "
            "mungon, analiza me rregulla vazhdon dhe shërbimi e njofton me një kod "
            "gabimi të veçantë. Shifrat e punimit vijnë vetëm nga parashikimet jashtë "
            "fold-it, kurrë nga ky model.",
        ],
    ),
    (
        "4.7",
        "Qasja C: motori i refaktorimit",
        [
            "Motori automatizon tri transformime të Fowler-it (2018): Extract Method "
            "për Long Method dhe Brain Method, Replace Nested Conditional with Guard "
            "Clauses për Deep Nesting, dhe Introduce Parameter Object për Long "
            "Parameter List, vetëm te metodat «private». Për katër erërat e tjera "
            "refaktorimi vetëm propozohet (Shtojca 8.4).",
            "Çdo transformim ka parakushtet e veta. Nëse ndonjë prej tyre nuk mund të "
            "provohet nga pema sintaksore, transformimi kthen «e paaplikueshme» "
            "bashkë me arsyen, dhe ky refuzim numërohet si rezultat.",
            "**Extract Method.** Nga trupi i metodës zgjidhet deklarata e përbërë më e "
            "madhe e nivelit të parë (një if, for, while, do, try ose switch), e matur "
            "në rreshta. Zgjedhja është mekanike, që e njëjta hyrje të japë gjithmonë "
            "të njëjtin rishkrim. Një analizë e rrjedhës së të dhënave i ndan "
            "variablat e bllokut në tri grupe: ato që blloku i lexon dhe që janë "
            "deklaruar para tij bëhen parametra; ajo që blloku e shkruan dhe që "
            "lexohet pas tij bëhet vlera që kthehet, dhe mund të jetë vetëm një; ato "
            "që deklarohen brenda tij mbeten brenda. Blloku refuzohet kur prej tij del "
            "një return, break ose continue, kur ka më shumë se një dalje, kur një "
            "variabël që lexon nuk ka vlerë me siguri, ose kur tipi i një variable "
            "nuk duket në skedar. Metoda e re është private, statike kur edhe metoda "
            "burimore është statike, dhe e trashëgon klauzolën «throws». Ajo quhet "
            "«extracted»: një emër sipas qëllimit kërkon të kuptosh për çfarë shërben "
            "kodi, gjë që pema sintaksore nuk e jep, ndaj emërtimi i lihet autorit.",
            "**Replace Nested Conditional with Guard Clauses.** Transformimi pranon "
            "vetëm një formë: metodë void, trupi i së cilës është një if i vetëm pa "
            "else. Kushti mbështillet si «!(kushti)», metoda del menjëherë kur ai "
            "vlen, dhe trupi i if-it zbret një nivel. Mbështjellja, në vend të "
            "përmbysjes së operatorit, e ruan kuptimin edhe për numrat me presje "
            "lëvizëse, ku «a > b» dhe «a <= b» mund të jenë të dy të rremë, dhe e "
            "vlerëson kushtin saktësisht një herë. Çdo formë tjetër refuzohet, sepse "
            "një degë else apo një vlerë kthyese do të kërkonin një vendim që sintaksa "
            "nuk e jep.",
            "**Introduce Parameter Object.** Zbatohet vetëm te metodat private, sepse "
            "Java i kufizon thirrjet e tyre brenda klasës së nivelit të lartë, pra "
            "brenda skedarit që rishkruhet. Parametrat mblidhen në një klasë të "
            "brendshme statike me fusha finale dhe konstruktor, metoda merr një "
            "parametër të vetëm, dhe çdo thirrje në skedar e ndërton objektin. Trupi "
            "i metodës nuk preket: në krye të tij parametrat e vjetër rideklarohen si "
            "variabla lokale me të njëjtin emër e tip, ndaj as fshehja e një emri as "
            "caktimi i një parametri nuk e ndryshojnë kuptimin. Refuzohen mbingarkesat, "
            "referencat ndaj metodës, parametrat me numër të ndryshueshëm, tipet "
            "gjenerike, parametrat me anotime dhe klasat që nuk mund të mbajnë një "
            "klasë të brendshme statike.",
            "**Gjetja e vendit dhe editimi.** Para rishkrimit skedari parsohet sërish, "
            "dhe entiteti gjendet me të njëjtin parim si mostrat e MLCQ-së: rreshti i "
            "fillimit si ankor, emri si kontroll. Kur skedari ka ndryshuar dhe rreshti "
            "mban diçka tjetër, vendi numërohet si i palokalizueshëm dhe nuk preket. "
            "Rishkrimi bëhet mbi pozicione bajtash, sepse tree-sitter jep pozicionet "
            "në bajta të tekstit UTF-8. Editimet aplikohen nga fundi i skedarit drejt "
            "fillimit, që pozicionet e të tjerave të mbeten të sakta, dhe dy editime "
            "që mbivendosen refuzohen.",
            "**Verifikimi.** Verifikimi ka tri nivele, sepse një skedar nga një depo "
            "reale varet nga fqinjët e tij dhe shpesh nuk kompilon i vetëm: skedari i "
            "rishkruar duhet të parsohet; javac, i ekzekutuar para dhe pas, nuk duhet "
            "të japë lloj të ri gabimi; dhe nëse skedari kompilonte i vetëm, duhet të "
            "kompilojë ende. Krahasohen llojet e mesazheve dhe jo numri i tyre, sepse "
            "një parametër i ri me tip të importuar shton një «cannot find symbol» që "
            "vjen nga izolimi e jo nga rishkrimi. Kompilatori thirret me argumente të "
            "fiksuara, me kufi kohe prej 60 sekondash dhe në një dosje të përkohshme. "
            "Ndikimi i izolimit matet veç: mbi një mostër skedarësh të zgjedhur me "
            "farë, i njëjti rishkrim kompilohet një herë i vetëm dhe një herë me "
            "burimet e projektit, dhe verdiktet krahasohen.",
            "Pas verifikimit, çdo entitet i rishkruar matet sërish me të njëjtët "
            "detektorë. Matet e gjithë klasa, para dhe pas, sepse Extract Method "
            "shton një metodë të re. Kështu shihet nëse era u hoq, sa ndryshoi "
            "metrika që e ndez detektorin, dhe nëse rishkrimi solli një erë të re.",
            "**Cilësia e rishkrimeve.** Kompilimi mbulon vetëm gjysmën e përkufizimit "
            "të Fowler-it (2018), ruajtjen e sjelljes. Nëse struktura u përmirësua e "
            "gjykon një njeri, mbi një mostër diff-esh, me një rubrikë me tri përmasa: "
            "**sjellja** (e ruajtur, e paqartë, e ndryshuar), **përfitimi** "
            "(përmirëson, asnjanës, përkeqëson) dhe **pranueshmëria** (ashtu si është, "
            "pas një ndreqjeje, e refuzuar). Mostra zgjidhet me farë, e shtresuar "
            "sipas transformimit, dhe shifra e përgjithshme ripeshohet sipas madhësisë "
            "së shtresave. Vlerësuesi nuk e sheh verdiktin e kompilatorit. Intervalet "
            "janë ato të Wilson (1927), sepse përafrimi normal me pak vëzhgime jep "
            "kufij jashtë [0, 1] (Brown et al., 2001). Vlerësuesi është vetë autori, "
            "çka është kufizim i deklaruar.",
        ],
    ),
    (
        "4.8",
        "Ndërfaqja web dhe API",
        [
            "Shërbimi HTTP ka njëmbëdhjetë pika hyrjeje: analizën e projektit, "
            "metrikat dhe kodin e një entiteti, shfletimin e dosjeve, importin nga "
            "GitHub, gjendjen e shërbimit, dhe pesë pika nën /refactor (pamja "
            "paraprake, patch-i, kontrolli dhe shkrimi në disk). Secila e validon "
            "kërkesën, thërret të njëjtat funksione si rreshti i komandës dhe kthen "
            "JSON.",
            "Aplikacioni ka një përdorues dhe dëgjon vetëm në localhost, ndaj "
            "rreziqet kryesore janë shtigjet dhe burimet, jo autentikimi. Pranohen "
            "vetëm shtigje brenda rrënjëve të lejuara, edhe pas lidhjeve simbolike; "
            "analiza ka kufij për skedarët, madhësinë dhe kohën; dhe gabimet kthehen "
            "pa detaje të brendshme. Meqë çdo faqe e hapur në shfletues mund ta "
            "arrijë localhost-in, refuzohen edhe emrat jo-lokalë te koka Host (DNS "
            "rebinding), kërkesat POST nga origjina të huaja dhe shfaqja e ndërfaqes "
            "brenda një faqeje tjetër. Importi nga GitHub ruan vetëm skedarët «.java» "
            "të një depoje publike, me kufij madhësie dhe me çdo shteg brenda dosjes "
            "së synuar.",
            "Shkrimi në disk është i vetmi veprim që ndryshon kodin e autorit, ndaj "
            "kërkon konfirmim të qartë, një depo git pa ndryshime të pakomituara dhe "
            "skedarë që git-i i ndjek, që një «git restore» t'i kthejë të gjitha. "
            "Përndryshe refuzohet me arsyen përkatëse. Shkruhen vetëm rishkrimet që "
            "kaluan verifikimin.",
            "Ndërfaqja është aplikacion React me TypeScript, që shërbehet nga i "
            "njëjti proces si API-ja. Projekti zgjidhet duke shfletuar dosjet ose "
            "duke importuar një depo. Për çdo gjetje shfaqen kushtet me vlerat e "
            "matura, shpjegimi i modelit, dhe diff-i i rishkrimit ose arsyeja e "
            "refuzimit. Pas shkrimit në disk tregohet cilat erëra u hoqën dhe cilat u "
            "shfaqën.",
        ],
    ),
    (
        "4.9",
        "Matja e performancës",
        [
            "Detektimi vlerësohet si klasifikim binar mbi etiketën e Nënkapitullit "
            "4.3. Te matrica konfuze, TP janë mostrat pozitive që detektori i shënon, "
            "FP negativet që shënon, FN pozitivet që i humbet dhe TN negativet që i "
            "lë. Prej saj llogariten precizioni, recall-i dhe F1:",
            ("equation", "P = TP / (TP + FP)"),
            ("equation", "R = TP / (TP + FN)"),
            ("equation", "F1 = 2 · P · R / (P + R)"),
            "Treguesi kryesor është koeficienti i korrelacionit i Matthews-it "
            "(Matthews, 1975), që i merr parasysh të katër qelizat:",
            ("equation", "MCC = (TP·TN − FP·FN) / √((TP+FP)(TP+FN)(TN+FP)(TN+FN))"),
            "Kjo ka rëndësi kur shumica e etiketave janë negative: një detektor që nuk "
            "ndez kurrë del i papërcaktuar sipas MCC-së, ndërsa saktësia e "
            "përgjithshme do t'i jepte shifër të lartë. Chicco & Jurman (2020) "
            "tregojnë se MCC-ja del e lartë vetëm kur parashikimi është i mirë në të "
            "katër qelizat, ndërsa saktësia dhe F1 mund të dalin tepër optimiste mbi "
            "bashkësi të çekuilibruara. Recall-i raportohet edhe sipas ashpërsisë që "
            "caktuan rishikuesit.",
            "Pajtimi mes dy qasjeve matet me koeficientin kappa (Cohen, 1960), ku A "
            "është pjesa e mostrave ku dy qasjet japin të njëjtin verdikt dhe E "
            "pajtimi që pritet rastësisht nga shpeshtësia me të cilën ndez secila:",
            ("equation", "κ = (A − E) / (1 − E)"),
            f"Kappa zgjidhet sepse kur {_negative_share()} e etiketave janë negative, "
            "dy detektorë që ndezin rrallë pajtohen shumë edhe rastësisht. Raportohen "
            "edhe të katër qelizat, bashkimi i dy qasjeve (mostra shënohet nëse e "
            "shënon njëra) dhe prerja e tyre (nëse e shënojnë të dyja).",
            "**Ndjeshmëria ndaj pragjeve.** Secili prag i katër strategjive të "
            f"vlerësuara shumëzohet me faktorët {_SETUP['factors']}, një prag në një "
            "kohë dhe me të tjerët te vlerat e botuara, dhe strategjia pikëzohet "
            "sërish. Pragjet nuk hyjnë në matje, ndaj kjo bëhet mbi tabelën e ruajtur "
            "të veçorive. Vlera që jep MCC-në më të lartë nuk adoptohet: e zgjedhur mbi "
            "të njëjtën bashkësi mbi të cilën raportohet, ajo do të matte sa mirë u "
            "përshtat pragu, jo sa mirë detekton strategjia.",
            "**Kalibrimi jashtë fold-it.** Për një shifër të ndershme me pragje të "
            f"lëvizura, korpusi ndahet në {_SETUP['folds']} folde sipas depos, si te "
            "Qasja B. Për secilin fold, nga i njëjti rrjet faktorësh zgjidhet pragu "
            "me MCC-në më të lartë mbi foldet e tjera, dhe ai zbatohet mbi foldin e "
            "mbajtur jashtë. Parashikimet e të gjitha foldeve bashkohen dhe pikëzohen "
            "një herë, ndaj shifra është jashtë fold-it në të njëjtin kuptim me atë "
            "të modeleve.",
            "**Intervalet e besimit.** Çdo tregues rillogaritet mbi "
            f"{_SETUP['resamples']} rimostrime me kthim (Efron & Tibshirani, 1993). "
            "Njësia e rimostrimit është depoja e jo mostra, që mostrat e një projekti "
            "të mbeten bashkë, dhe intervali 95% merret nga percentilet 2.5 dhe 97.5. "
            "Për dallimin B − A raportohet edhe pjesa e rimostrimeve ku ai ruan "
            "shenjën pozitive, dhe dallimi rillogaritet edhe kur Qasja A merr pragun e "
            "saj më të mirë nga fshirja.",
            "**Pajtimi mes rishikuesve.** Për çdo mostër me dy rishikime ose më shumë, "
            "çdo çift rishikimesh kalon nëpër të njëjtën matricë konfuze: njëri "
            "rishikues merret si e vërtetë, tjetri si parashikim. MCC-ja që del "
            "shërben si tavan orientues për detektorët dhe jo si kufi i rreptë, sepse "
            "etiketa e agreguar e zbut zhurmën e një rishikuesi të vetëm.",
            "Motori i refaktorimit matet ndryshe: numërohen vendet e detektuara, të "
            "transformuara dhe të refuzuara sipas arsyes, me verdiktin e verifikimit "
            "për çdo rishkrim.",
            "**Krahasimi me PMD-në.** Si krahasim i jashtëm, i njëjti vlerësim "
            "zbatohet te PMD (PMD Team, 2026), versioni 7.27.0, rregullat GodClass dhe "
            "DataClass të të cilit bazohen te strategjitë e Lanza & Marinescu (2006). "
            "PMD ekzekutohet me pragjet e veta, pikëzohet njësoj si Qasja A, dhe "
            "shkeljet lidhen me entitetet sipas emrit të klasës dhe të metodës. Meqë "
            "analizon një skedar në një kohë, ATFD-në e llogarit vetëm brenda "
            "skedarit, gjë që e vë në disavantazh; heqja e këtij handikapi do të "
            "kërkonte ndërtimin e çdo depoje në commit-in e vet historik. Rregull për "
            "Feature Envy PMD nuk ka, ndaj LawOfDemeter, që mat zinxhirët e thirrjeve, "
            "raportohet vetëm si referencë. Skedarët që PMD nuk i lexon dhe depot që "
            "nuk i përpunon hiqen nga të dyja anët, që dështimi i mjetit të mos "
            "lexohet si mosgjetje, dhe një raport XML i pavlefshëm lexohet me një "
            "rrugë rikuperimi që jep të njëjtat fusha. Dallimi i MCC-së ka interval të "
            "çiftuar, me të njëjtat rimostrime depo për të dyja anët.",
        ],
    ),
    (
        "4.10",
        "Validimi i sistemit",
        [
            "Sistemi validohet në katër nivele, dhe një ndryshim quhet i përfunduar "
            "vetëm kur i kalon të gjitha:",
            (
                "bullet",
                "Testet e backend-it me pytest, me vlera të pritura të llogaritura me "
                "dorë nga fiksturat dhe jo të marra nga dalja e kodit. Çdo detektor "
                "ka një rast pozitiv, një rast që plotëson vetëm disa kushte dhe një "
                "rast kufitar (ndërfaqe, enum, klasë bosh); çdo transformim testohet "
                "që aplikohet saktë, që refuzon kur nuk është i sigurt dhe që dalja "
                "kompilon.",
            ),
            (
                "bullet",
                "Testet e ndërfaqes me Vitest dhe testet end-to-end me Playwright, që "
                "e përdorin aplikacionin si përdorues dhe kontrollojnë edhe "
                "aksesueshmërinë me axe-core.",
            ),
            (
                "bullet",
                "Analiza statike: Ruff për stilin dhe mypy në modalitet strikt, që "
                "mbulon edhe skriptet e eksperimenteve, sepse ato prodhojnë numrat e "
                "punimit.",
            ),
            (
                "bullet",
                "Integrimi i vazhdueshëm: çdo commit ekzekuton pesë punë të pavarura, "
                "për backend-in, ndërfaqen, testet end-to-end, mjetet e Java-s dhe "
                "kontrollet e dokumentit.",
            ),
            "Rregulli kryesor është që asnjë prag, metrikë apo detektor nuk "
            "ndryshohet vetëm që të kalojë një test; kur kodi dhe testi nuk pajtohen, "
            "gjendet më parë cili është i gabuar. Në verifikimin e fundit, më "
            f"{VALIDATION_DATE}, kaluan {BACKEND_TESTS} teste të backend-it, me mbulim "
            f"{COVERAGE} të kodit, dhe {FRONTEND_TESTS} teste të ndërfaqes.",
            "Edhe vetë ky dokument kontrollohet automatikisht: çdo citim duhet të ketë "
            "referencë dhe anasjelltas, formati krahasohet me rregullat e shabllonit, "
            "tabela e riprodhimit krahasohet me skriptet që ekzistojnë, dhe fjalitë e "
            "përsëritura mes kapitujve raportohen.",
        ],
    ),
    (
        "4.11",
        "Riprodhueshmëria dhe mjedisi",
        [
            "Çdo numër në punim prodhohet nga një skript dhe ruhet si CSV ose JSON në "
            "depo. Farat e rastësisë dhe versionet e varësive janë të fiksuara, dhe "
            "mjedisi regjistrohet në çdo skedar rezultati.",
            "Kalimi mbi korpusin, afro një orë për rreth 690 mijë skedarë, bëhet një "
            "herë dhe prodhon një tabelë veçorish që ruhet në depo. Pragjet nuk hyjnë "
            "në këtë kalim, ndaj analiza e ndjeshmërisë i riekzekuton detektorët mbi "
            "rreshtat e ruajtur brenda sekondash. Radha e plotë e skripteve është te "
            "Shtojca 8.5.",
            "**Mjedisi eksperimental.** Eksperimentet u ekzekutuan në një laptop pa "
            f"kartë grafike të dedikuar, me {_SETUP['system']}, Python "
            f"{_SETUP['python']} dhe JDK 21. Çdo skedar rezultati mban commit-in e "
            "kodit që e prodhoi, platformën dhe versionin e Python-it, ndaj një "
            "shifër lidhet gjithmonë me kodin e saktë që e nxori. Trajnimi i modeleve "
            "zgjat disa minuta, ndërsa ekzekutimi i motorit të refaktorimit mbi tërë "
            "korpusin disa orë, sepse javac thirret dy herë për çdo skedar të "
            "rishkruar. Asnjë hap nuk kërkon shërbim në re apo me pagesë.",
        ],
    ),
    (
        "4.12",
        "Konsideratat etike",
        [
            "Punimi nuk mbledh të dhëna nga njerëz, ndaj pëlqimi i informuar dhe "
            "konfidencialiteti nuk zbatohen këtu. Të gjitha të dhënat janë publike: "
            "gjykimet e MLCQ-së, të mbledhura dhe publikuara nga autorët e saj "
            "(Madeyski & Lewowski, 2020), dhe kodi i depove Java me burim të hapur ku "
            "ndodhen mostrat.",
            "Ky kod përdoret vetëm si objekt matjeje dhe nuk ekzekutohet kurrë: "
            "analiza e lexon si tekst, dhe verifikimi e kompilon me javac pa e nisur. "
            "Korpusi nuk shpërndahet me punimin; kush do t'i riprodhojë rezultatet e "
            "shkarkon nga burimet origjinale me skriptin e parë të Shtojcës 8.5. "
            "Rezultatet negative raportohen njësoj si ato pozitive.",
            "Dataset-i MLCQ dhe depot e korpusit mbeten nën licencat e veta. Kodi i "
            "sistemit publikohet nën licencën MIT, ndërsa asnjë pjesë e kodit të huaj "
            "nuk shpërndahet bashkë me të.",
        ],
    ),
    (
        "4.13",
        "Kërcënimet ndaj vlefshmërisë",
        [
            "Kërcënimet grupohen sipas katër llojeve të vlefshmërisë që përdor "
            "literatura e eksperimenteve në inxhinierinë softuerike (Wohlin et al., "
            "2012), secili me masën që e zbut.",
            "**Vlefshmëria e konstruktit.** Pyetja është nëse shifra mat atë që "
            "pretendon. Etiketat e MLCQ-së janë gjykime njerëzore, dhe mënyra si "
            "bashkohen i ndryshon pozitivët; prandaj çdo agregim alternativ "
            "raportohet veç (Nënkapitulli 4.3). Numërimi i rreshtave dhe njohja e "
            "akses-metodave nga parashtesa janë zgjedhje që prekin disa metrika, dhe "
            "të dyja janë deklaruar te Nënkapitulli 4.4. Te refaktorimi, kompilimi "
            "provon se forma e kodit mbetet e ligjshme, jo se sjellja mbetet e njëjtë.",
            "**Vlefshmëria e brendshme.** Një lidhje e gabuar mes mostrës dhe "
            "entitetit do t'i prishte të gjitha shifrat pa u vënë re; prandaj "
            "përputhja ankorohet te rreshtat, kontrollohet me emrin, dhe çdo mostër e "
            "palidhur raportohet me shkakun. Rrjedhja mes trajnimit dhe testimit "
            "pengohet nga ndarja sipas depos, dhe peshat në vend të mbi-mostrimit e "
            "ruajnë atë ndarje. Pragjet pa burim të botuar janë emërtuar te "
            "Nënkapitulli 4.5.",
            "**Vlefshmëria e jashtme.** Rezultatet mbështeten te kod Java me burim të "
            "hapur, katër erëra dhe një dataset të vetëm, dhe asgjë këtu nuk provon se "
            "transferohen te gjuhë të tjera apo te kodi i mbyllur industrial. Humbja e "
            "disa depove mund ta anojë mostrën, dhe ky rrezik nuk matet dot pa kodin e "
            "tyre.",
            "**Vlefshmëria e përfundimeve.** Çdo model trajnohet një herë, me "
            "parametra të fiksuar dhe pa akordim. Pasiguria që vjen nga korpusi matet "
            "me bootstrap sipas depos, por ajo që vjen nga ndryshimi i farës nuk "
            "matet. Një dallim, intervali i të cilit përfshin zeron, raportohet si i "
            "padallueshëm dhe jo si fitore e njërës anë.",
        ],
    ),
]

# ======================================================================
# Kapitulli 6
# ======================================================================
def _context_conclusion() -> str:
    """A si u sollën verdiktet brenda kontekstit, lexuar nga skedari e jo i shtypur.

    Kjo klauzolë e pohonte në prozë përfundimin e mirë — «pa asnjë verdikt të
    përmbysur» — ndërsa Kapitulli 5 e lexonte të njëjtin numër nga skedari. Kur
    mostra u dyfishua dhe numri kaloi nga zero në një, Kapitulli 5 u përshtat
    vetvetiu dhe përfundimi mbeti i vjetruar (VD-55). Prandaj tani e ndan të
    njëjtin burim me të.
    """
    data = _load_if_present("verify_with_project.json")
    if data is None:
        return "pjesa që kompilon plotësisht rritet ndjeshëm"

    regressions = data["compiled_in_project"].get("new_errors", 0)
    total = data["rewrites"]
    if not regressions:
        return "pjesa që kompilon plotësisht rritet ndjeshëm pa asnjë verdikt të përmbysur"
    if regressions == 1:
        return (
            "pjesa që kompilon plotësisht rritet ndjeshëm, ndërsa një rishkrim i "
            f"vetëm nga {total} e përmbys verdiktin në drejtimin e kundërt dhe e "
            "kufizon pretendimin"
        )
    return (
        "pjesa që kompilon plotësisht rritet ndjeshëm, ndërsa "
        f"{_word(regressions)} rishkrime nga {total} e përmbysin verdiktin në drejtimin e "
        "kundërt dhe e kufizojnë pretendimin"
    )


def _blob_recall_limits() -> list:
    """Dy kufizimet që dalin nga Shtojca 8.8, të lexuara nga i njëjti skedar.

    Të shtypura me dorë do të ishin dy pohime numerike brenda kapitullit të
    fundit që lexon komisioni, dhe pikërisht ashtu rrëshqiti Kapitulli 6 një
    herë (VD-73). Nëse analiza mungon, paragrafët nuk ekzistojnë fare.
    """
    data = _load_if_present("blob_recall.json")
    if data is None:
        return []

    strategy = data["per_variant"]["strategy"]
    best = max(float(value) for value in strategy["separation"].values())

    # Numrat e rasteve janë te Shtojca 8.8; këtu jepet vetëm pasoja e tyre, që
    # e njëjta fjali të mos lexohet dy herë (VD-128).
    return [
        "Recall-i i Blob-it ka dy tavane që nuk varen nga pragjet (Shtojca 8.8). I "
        "pari: një pjesë e rasteve të humbura nuk janë më të mëdha se klasat e pastra, "
        "dhe asnjë metrikë e vetme klase nuk i ndan prej tyre (më e mira arrin "
        f"{best:.3f}); një detektor që mbështetet vetëm te këto metrika e ka të vështirë "
        "t'i kapë. I dyti: TCC-ja e papërcaktuar merr vlerën maksimale, të cilën God "
        "Class nuk e pranon. Ndreqja do ta shkëpuste TCC-në nga përkufizimi i botuar, "
        "ndaj u zgjodh raportimi.",
    ]


def _blocking_in_discussion() -> list:
    """Gjetja e tretë që tregon në të njëjtin drejtim si dy të parat.

    Ndërtuar nga të dhënat e jo e shtypur, sepse është pohim numerik brenda
    prozës së diskutimit dhe pikërisht atje rrëshqiti Kapitulli 6 një herë
    (VD-73). Nëse analiza mungon, paragrafi nuk ekziston fare, dhe dy gjetjet e
    tjera qëndrojnë vetë.
    """
    data = _load_if_present("blocking_conditions.json")
    if data is None:
        return []
    entry = data["by_smell"].get("blob")
    if entry is None:
        return []

    missed = int(str(entry["missed"]))
    alone = int(str(entry["blocked_by_one_clause"]))
    many = missed - alone
    return [
        f"E treta vjen nga vetë mospërputhjet. Nga {missed} raste që rishikuesit i "
        f"quajtën Blob dhe strategjia nuk i ndezi, {many} nuk e kalojnë as dy nga tri "
        "klauzolat (Shtojca 8.6). Humbja e tyre nuk zgjidhet pra duke lëvizur një "
        "prag: këto klasa dallojnë nga përkufizimi i strategjisë në më shumë se një "
        "dimension.",
    ]


# Mesorja më e mirë e MCC-së në konfigurimin DS1 të Madeyski & Lewowski (2023), mbi
# MLCQ. DS1 e quan pozitive një mostër me ashpërsi mbi «none», si agregimi parësor
# këtu. Për Long Method autorët japin vetëm kufirin («greater than 0.75»), ndaj
# vlera shkruhet si kufi. Burimi: seksionet 4.1-4.4 të artikullit.
MADEYSKI_2023_DS1 = {
    "blob": "0.51 (RF)",
    "data class": "0.57 (RF)",
    "feature envy": "0.31 (FDA)",
    "long method": "> 0.75 (RF)",
}


def _headline() -> dict:
    """Shifrat që diskutimi i përdor më shpesh, të lexuara një herë nga rezultatet."""
    rules = _load("rules_evaluation.json")
    ml = _load("ml_evaluation.json")
    smells = sorted(ml["per_smell"])
    strategy = {s: rules["per_smell"][s]["strategy"]["by_aggregation"]["mean"] for s in smells}
    model = {s: ml["per_smell"][s]["models"][ml["per_smell"][s]["best_model"]] for s in smells}
    return {"rules": rules, "ml": ml, "smells": smells, "strategy": strategy, "model": model}


def _span(values: list[float], digits: int = 3) -> str:
    return f"{min(values):.{digits}f} deri në {max(values):.{digits}f}"


def _joined(items: list[str]) -> str:
    """«A», «A dhe B», «A, B dhe C»: lidhëza shqipe para elementit të fundit."""
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " dhe " + items[-1]


# Emri i shkurtër shqip i arsyeve të refuzimit, për fjalitë e diskutimit. Kuptimi i
# plotë i secilës është te `REFUSAL_SQ`.
REASON_SHORT_SQ = {
    "shape_not_matched": "forma e kodit që nuk i përshtatet transformimit",
    "control_flow_escapes": "rrjedha e kontrollit që del nga blloku",
    "not_definitely_assigned": "një vlerë hyrëse ende e pacaktuar",
    "multiple_outputs": "më shumë se një vlerë dalëse",
    "ambiguous_overload": "mbingarkesa e paqartë",
    "unresolved_name": "një emër i pazgjidhur",
    "possible_side_effect": "një efekt anësor i mundshëm",
    "edit_conflict": "editime që mbivendosen",
    "unparseable": "kod që nuk parsohet",
}


def _calibration_verdict() -> str:
    """Ku ndihmoi kalibrimi jashtë fold-it, nga të dhënat e Nënkapitullit 5.5."""
    data = _load_if_present("threshold_calibration.json")
    if data is None:
        return ""
    clear, slight, worse = [], [], []
    for smell, entry in sorted(data["per_smell"].items()):
        gain = entry["calibrated"]["mcc"] - entry["published"]["mcc"]
        # 0.05 është vetëm kufiri i fjalës «qartë» në këtë fjali, jo prag i sistemit.
        (clear if gain > 0.05 else slight if gain > 0 else worse).append(SMELL_SQ[smell])
    parts = []
    if clear:
        parts.append(f"e ngriti MCC-në qartë te {' dhe '.join(clear)}")
    if slight:
        parts.append(f"pak te {' dhe '.join(slight)}")
    if worse:
        parts.append(f"e uli te {' dhe '.join(worse)}")
    return "Kalibrimi i pragjeve jashtë fold-it " + ", ".join(parts)


def _reading_of_detection(h: dict) -> list:
    """Interpretimi i PK1 dhe PK2, me çdo numër nga të dhënat."""
    smells, strategy, model, ml = h["smells"], h["strategy"], h["model"], h["ml"]
    worst = min(smells, key=lambda s: strategy[s]["recall"])
    best = max(smells, key=lambda s: strategy[s]["recall"])
    precise = all(strategy[s]["precision"] > 0.5 for s in smells)

    higher, reverse = 0, []
    for smell in smells:
        by = h["rules"]["per_smell"][smell]["strategy"].get("recall_by_severity") or {}
        if "major" in by and "minor" in by:
            if by["major"]["recall"] > by["minor"]["recall"]:
                higher += 1
            else:
                reverse.append(SMELL_SQ[smell])

    decisive, top_feature = [], {}
    for smell in smells:
        ranked = sorted(
            ml["per_smell"][smell]["explained"]["decisive_feature"].items(),
            key=lambda pair: -pair[1],
        )
        top_feature[smell] = ranked[0][0].split("_", 1)[1]
        decisive.append(f"{top_feature[smell]} te {SMELL_SQ[smell]}")
    shares = [ml["per_smell"][s]["explained"]["share"] for s in smells]
    envy_by_length = top_feature.get("feature envy") == "MLOC"

    beats = sum(
        1
        for s in smells
        if ml["per_smell"][s]["combined"]["intersection"]["precision"]
        > max(strategy[s]["precision"], model[s]["precision"])
    )
    vs = {s: ml["per_smell"][s]["vs_rules"] for s in smells}
    covers = all(vs[s]["only_model"] > vs[s]["only_rules"] for s in smells)
    # Era ku bashkimi humbet më shumë, dhe era ku rregulli ka më shumë raste të veta.
    worst_union = min(
        smells,
        key=lambda s: (ml["per_smell"][s]["combined"]["union"]["mcc"] or 0.0) - model[s]["mcc"],
    )
    richest = max(smells, key=lambda s: vs[s]["only_rules"] / max(vs[s]["only_model"], 1))

    # Sa raste major mbështesin erën që sillet ndryshe, që përjashtimi të lexohet
    # me peshën e vet e jo si kundërshtim i barabartë.
    thin = {
        SMELL_SQ[s]: h["rules"]["per_smell"][s]["strategy"]["recall_by_severity"]["major"]["support"]
        for s in smells
        if SMELL_SQ[s] in reverse
    }

    return [
        "**Qasja A.** "
        + (
            "Kur ndezin, strategjitë e publikuara kanë më shpesh të drejtë sesa gabim, "
            if precise
            else "Kur ndezin, strategjitë e publikuara kanë shpesh të drejtë, "
        )
        + "por i humbin shumicën e rasteve që rishikuesit i shënojnë, nga "
        f"{1 - strategy[best]['recall']:.0%} te {SMELL_SQ[best]} deri në "
        f"{1 - strategy[worst]['recall']:.0%} te {SMELL_SQ[worst]}. Pragjet e tyre, të "
        "llogaritura mbi sisteme krejt të tjera, janë pra konservative për mënyrën si i "
        "gjykojnë erërat rishikuesit e MLCQ-së.",
        "Kjo tërheqje nuk bie njësoj mbi të gjitha rastet. Shfaqjet e qarta të erës, ato "
        "që rishikuesit i quajtën major, kapen më lehtë se ato të butat (Nënkapitulli "
        "5.1): strategjitë reagojnë ndaj tepricës së dukshme dhe heshtin para asaj që "
        "mezi dallohet"
        + (
            "; përjashtimi, "
            + _joined([f"{name}, mbështetet te vetëm {count} raste major" for name, count in thin.items()])
            if thin
            else ""
        )
        + ". Një F1 i vetëm do ta fshihte këtë dallim.",
        *_sensitivity_reading(),
        "**Qasja B.** Modelet e tejkalojnë qasjen me rregulla te çdo erë, dhe meqë "
        "klasifikuesi i shumicës nuk ndez kurrë, fitimi nuk vjen nga çekuilibri i "
        "klasave." + _gain_split(h),
        *_intervals_reading(),
        "Shpjegimi për rast e zbut kundërshtimin standard ndaj mësimit të makinës, se "
        f"modeli fiton por nuk thotë pse. Te {min(shares):.0%} deri në {max(shares):.0%} "
        "të verdikteve një matje e vetme e mban shënimin, dhe matja më e shpeshtë "
        "vendimtare është "
        + ", ".join(decisive)
        + ". Zhvilluesi merr kështu një fjali me të njëjtën formë si klauzola e një "
        "strategjie."
        + (
            " Që Feature Envy shpjegohet kryesisht me gjatësinë e metodës, e jo me "
            "qasjet në të dhëna të huaja, tregon se modeli mëson atë që rishikuesit "
            "shënojnë, jo domosdoshmërisht përkufizimin e erës."
            if envy_by_length
            else ""
        ),
        (
            "Modeli pothuajse e përfshin rregullin: te çdo erë ai shënon më shumë raste "
            "që rregulli i humb sesa anasjelltas. "
            if covers
            else ""
        )
        + "Bashkimi i dy qasjeve nuk ndihmon, sepse bashkë me rastet e sakta të "
        "rregullit vijnë edhe pozitivët e tij të rremë, dhe mbi një bashkësi ku shumica "
        "e etiketave janë negative ky shkëmbim humbet"
        + (
            f"; ironikisht, bashkimi humbet më shumë pikërisht te {SMELL_SQ[richest]}, ku "
            "rregulli kishte më shumë raste të veta"
            if richest == worst_union
            else ""
        )
        + ". Prerja sillet ndryshe: "
        + (
            "te çdo erë, "
            if beats == len(smells)
            else f"te {beats} nga {len(smells)} erërat, "
        )
        + "kur dy qasje të pavarura pajtohen, precizioni del mbi secilën veç, sepse "
        "gabimet e tyre rrallë bien mbi të njëjtat mostra.",
    ]


def _sensitivity_reading() -> list:
    """Çfarë do të thotë ndjeshmëria ndaj pragjeve, e zhvendosur nga Kapitulli 5.

    Kapitulli 5 i jep vetëm vlerat (VD-136). Shpjegimi, që më parë qëndronte
    pranë tabelës, vjen këtu, i ndërtuar mbi të njëjtat skedarë.
    """
    sweep = _load("threshold_sweep.json")
    calibration = _load_if_present("threshold_calibration.json")

    def amplitude(smell: str) -> float:
        return max(
            max(point["mcc"] for point in points) - min(point["mcc"] for point in points)
            for points in sweep["per_smell"][smell].values()
        )

    wide = [s for s in sorted(sweep["per_smell"]) if amplitude(s) >= 0.2]
    narrow = [s for s in sorted(sweep["per_smell"]) if amplitude(s) < 0.2]
    paragraphs = []
    if wide and narrow:
        paragraphs.append(
            "Sa varet ky përfundim nga pragjet? Te "
            f"{_joined([SMELL_SQ[s] for s in narrow])} zhvendosja e çdo pragu mezi e "
            "lëviz MCC-në (Nënkapitulli 5.5), ndaj shifrat e tyre flasin për kodin dhe jo "
            f"për pragun. Te {_joined([SMELL_SQ[s] for s in wide])} amplituda është e "
            "madhe, pra shifra e raportuar flet po aq për pragun sa për kodin. Kjo vlen "
            "sa herë krahasohen mjete detektimi që përdorin pragje të ndryshme: dallimi "
            "mes tyre mund të jetë dallim pragjesh e jo metodash."
        )
    envy = sweep["per_smell"].get("feature envy", {}).get("feature_envy_fdp")
    method = sweep["per_smell"].get("long method", {}).get("long_method_loc")
    if method:
        published = next(p for p in method if p["factor"] == 1.0)
        top = max(method, key=lambda p: p["mcc"])
        if top["value"] < published["value"] and top["recall"] > published["recall"]:
            paragraphs.append(
                f"Te {SMELL_SQ['long method']}, pragu i botuar del konservativ për këtë "
                "korpus: me një prag më të ulët recall-i rritet shumë më tepër se sa bie "
                "precizioni, çka sugjeron se rishikuesit e MLCQ-së e quajnë një metodë të "
                "gjatë më herët se sa e vendos pragu. Fitimi megjithatë paguhet me "
                "precizion, dhe foldet e kalibrimit nuk bien dakord për vlerën."
            )
    if envy:
        published = next(p for p in envy if p["factor"] == 1.0)
        top = max(envy, key=lambda p: p["mcc"])
        both = top["precision"] > published["precision"] and top["recall"] > published["recall"]
        unanimous = (
            calibration is not None
            and sum(len(v) for v in calibration["per_smell"]["feature envy"]["chosen"].values())
            == 1
        )
        if both:
            paragraphs.append(
                f"Te {SMELL_SQ['feature envy']} vërehet diçka më e veçantë. Klauzola që "
                "kërkon që klasat-burim të jenë pak, kur relaksohet, i përmirëson "
                "njëkohësisht precizionin dhe recall-in"
                + (", dhe kalibrimi jashtë fold-it e zgjedh të njëjtën vlerë në çdo fold"
                   if unanimous else "")
                + ". Një kufizim që heq pozitivë të vërtetë pa hequr të rremë nuk e ndan "
                "sinjalin nga zhurma; mbi këtë korpus, pra, ajo klauzolë nuk e bën punën "
                "për të cilën u vendos."
            )
    if calibration is not None:
        paragraphs.append(
            f"Te {SMELL_SQ['long method']}, dallimi mes fshirjes dhe kalibrimit (Nënkapitulli "
            "5.5) është pikërisht ajo që fitohet kur zgjedhjes "
            "i lejohet ta shohë bashkësinë mbi të cilën do të raportohet, dhe arsyeja pse "
            "u raportua shifra e kalibruar."
        )
    return paragraphs


def _intervals_reading() -> list:
    """Çfarë do të thonë intervalet e besimit për krahasimin A↔B."""
    intervals = _load("bootstrap_intervals.json")
    per = intervals["per_smell"]
    above = [s for s in per if per[s]["intervals"]["difference_model_minus_rules"]["low"] > 0]
    lost = [
        SMELL_SQ[s]
        for s in sorted(per)
        if per[s]["intervals"]["difference_model_minus_rules_swept"]["low"] <= 0
    ]
    text = (
        "Intervalet e besimit e forcojnë këtë lexim (Nënkapitulli 5.7). Përparësia e "
        f"modelit mbetet mbi zero {_among(len(above), len(per))} kur korpusi rimostrohet "
        "sipas depos, pra nuk është artefakt i një korpusi të veçantë. Por intervalet "
        "janë të gjera, ndaj renditja e erërave mes tyre nuk qëndron: dallimi mes Data "
        "Class-it dhe Blob-it, për shembull, humbet brenda tyre."
    )
    if lost:
        text += (
            f" Kur rregullit i jepet pragu i tij më i mirë, përparësia zhduket te "
            f"{_joined(lost)}, pikërisht aty ku rregulli punonte më mirë; ky është "
            "kufizimi i vetëm i rëndësishëm i krahasimit mes dy qasjeve."
        )
    return [text]


def _isolation_reading(context: dict) -> str:
    """Çfarë thotë kompilimi brenda projektit për verdiktin e izoluar, nga të dhënat.

    Fjala që qëndronte këtu, «shumica e rasteve pa gabim të ri kompilojnë
    plotësisht», nuk ishte e vërtetë: brenda projektit kompilonte plotësisht një
    pakicë. U fut kur paragrafi u shkurtua (VD-128), dhe shtrembëronte origjinalin,
    që thoshte se gabimet e mbetura i përkasin izolimit. Pohonte gjithashtu se
    përmbysja e Ambari-t ishte e vetmja, ndërsa rimatja pas VD-130 nxori dy.
    """
    tolerant = context["compiled_alone"].get("no_new_errors", 0)
    lifted = context.get("moved", {}).get("no_new_errors -> compiles", 0)
    regressions = context["compiled_in_project"].get("new_errors", 0)
    if not regressions:
        overturn = "Asnjë rishkrim nuk shkon në drejtimin e kundërt. "
    elif regressions == 1:
        overturn = (
            "Një rishkrim i vetëm shkon në drejtimin e kundërt: pa gabim të ri i izoluar, "
            "me gabim të ri brenda projektit. "
        )
    else:
        overturn = (
            f"{_opens(_word(regressions))} rishkrime shkojnë në drejtimin e kundërt: pa "
            "gabim të ri të izoluara, me gabim të ri brenda projektit. "
        )
    return (
        "Verdikti i izoluar është më i rreptë se vetë rishkrimi. Brenda projektit të "
        f"vet (Nënkapitulli 5.4), {lifted} nga {tolerant} rishkrimet «pa gabim të ri» "
        "kompilojnë plotësisht, pra gabimet e tyre të mëparshme i detyroheshin mungesës "
        "së fqinjëve dhe jo transformimit. Te pjesa tjetër, gabimet ishin aty edhe para "
        "rishkrimit: korpusi nuk mban bibliotekat e jashtme. "
        + overturn
        + "Toleranca «pa lloj të ri gabimi» mbetet dëshmi e përdorshme ku kompilimi i "
        "plotë nuk arrihet, por jo garanci."
    )


def _reading_of_refactoring() -> list:
    """Interpretimi i PK3, me çdo numër nga të dhënat."""
    data = _load_if_present("refactoring_evaluation.json")
    if data is None:
        return []
    resolution = data.get("resolution") or {}
    introduced = data.get("introduced_smells") or {}
    refused = sorted(data["refused_by_reason"].items(), key=lambda pair: -pair[1])
    context = _load_if_present("verify_with_project.json")

    # Numrat e PK3 (norma, verdiktet, heqja e erës) jepen te Nënkapitulli 6.4; këtu
    # shpjegohet vetëm pse dolën ashtu, që të njëjtat shifra të mos lexohen dy herë
    # brenda një kapitulli (VD-128).
    paragraphs = [
        "**Qasja C.** Refuzimet e motorit tregojnë ku ndalet automatizimi i sigurt. "
        f"Arsyeja kryesore është {REASON_SHORT_SQ.get(refused[0][0], refused[0][0])}, e "
        f"ndjekur nga {REASON_SHORT_SQ.get(refused[1][0], refused[1][0])}, dhe sa më e "
        "rëndë metoda, aq më shumë peshon e dyta: një metodë e gjatë ose e ndërfutur "
        "thellë mban më shumë return, break e continue. Motori tërhiqet pra pikërisht te "
        "metodat ku ndihma do të vlente më shumë.",
    ]
    if context is not None:
        paragraphs.append(_isolation_reading(context))
    if resolution:
        paragraphs.append(
            "Që një rishkrim kompilon nuk do të thotë se e heq erën, dhe kur era mbetet, "
            "shkaku është te vetë transformimet. Guard Clauses heq saktësisht një nivel "
            "ndërfutjeje, ndërsa Deep Nesting ndez mbi tre, ndaj një metodë me gjashtë "
            "nivele mbetet mbi kufirin; Extract Method nxjerr bllokun më të madh pa garanci "
            "se metoda bie nën prag. Vetëm Introduce Parameter Object e zgjidh erën me "
            "ndërtim, sepse lista e parametrave bëhet një."
        )
    if introduced:
        top = max(introduced, key=lambda name: introduced[name])
        paragraphs.append(
            f"Erërat e reja janë më shpesh {_named(top)}, dhe shkaku është i drejtpërdrejtë: "
            "Extract Method ia kalon metodës së nxjerrë çdo vlerë që blloku lexonte, ndaj "
            "një bllok me gjashtë hyrje prodhon një metodë me gjashtë parametra. "
            "Transformimi është i saktë, por e zhvendos problemin. Prandaj numri i vendeve "
            "të transformuara nuk lexohet si numri i erërave të hequra: sa u shëruan, sa "
            "lëvizi matja dhe sa probleme të reja lindën duhen lexuar bashkë."
        )
    return paragraphs


def _literature_rows(h: dict) -> list:
    return [
        [
            SMELL_SQ[smell],
            f"{h['strategy'][smell]['mcc']:.3f}",
            f"{h['model'][smell]['mcc']:.3f}",
            MADEYSKI_2023_DS1[smell],
        ]
        for smell in h["smells"]
    ]


def _literature_comparison(h: dict) -> list:
    """Krahasimi me literaturën, me shifrat tona nga të dhënat.

    Shifrat e literaturës janë ato të botuara dhe shkruhen me citimin e tyre;
    shifrat e këtij punimi lexohen, që krahasimi të mos rrëshqasë po të
    rigjenerohet ndonjë rezultat.
    """
    model = h["model"]
    lower = [
        SMELL_SQ[s]
        for s in ("blob", "data class", "long method")
        if model[s]["mcc"] < float(MADEYSKI_2023_DS1[s].lstrip("> ").split()[0])
    ]
    f1 = [model[s]["f1"] for s in h["smells"]]
    ceiling = _load_if_present("reviewer_agreement.json")
    paragraphs = [
        "Krahasimi më i drejtpërdrejtë është me Madeyski & Lewowski (2023), të cilët "
        "trajnuan tetë algoritme mbi të njëjtin dataset MLCQ, me metrikat e PMD-së dhe "
        "të CODEBEAT-it si veçori. Konfigurimi i tyre DS1 e quan pozitive një mostër "
        "me të njëjtin kriter si ky punim (Nënkapitulli 4.9). Tabela vë përballë MCC-në e të dy qasjeve këtu me mesoren "
        "më të mirë të MCC-së që raportojnë ata.",
        ("table", "Krahasimi i MCC-së me Madeyski & Lewowski (2023), mbi MLCQ",
         ["Erë", "Qasja A", "Qasja B", "M&L 2023, DS1"], _literature_rows(h)),
        (
            f"Te {_joined(lower)} modelet e këtij punimi dalin pak nën ato të "
            "Madeyski & Lewowski-t. "
            if lower
            else ""
        )
        + "Dallimi i validimit e bën këtë të pritshme: ata e ndajnë bashkësinë me "
        "validim të kryqëzuar me pesë folde, të shtresuar sipas klasës por jo të "
        "grupuar sipas projektit, ndaj e njëjta depo mund ta ushqejë trajnimin dhe të "
        "vlerësohet në të njëjtën kohë, pikërisht rrjedhja që ky punim e shmang me "
        "GroupKFold. Ata raportojnë edhe mesoren e 120 ekzekutimeve me hiperparametra "
        "të optimizuar për MCC, ndërsa këtu modelet kanë parametra fiksë dhe një "
        "ekzekutim të vetëm jashtë fold-it. Me një ndarje më të rreptë dhe pa akordim, "
        "rezultatet e këtij punimi janë në të njëjtin brez.",
        f"Te Feature Envy drejtimi është i kundërt: {model['feature envy']['mcc']:.2f} "
        "këtu kundrejt 0.31 atje, ku autorët e quajnë erën më të vështirë. Shpjegimi më "
        "i mundshëm janë veçoritë: ky punim mat për çdo metodë ATFD, LAA, FDP dhe "
        "rreshtat efektivë, ndërsa ata përdorin metrika të mjeteve të përgjithshme. Dy "
        "punimet nuk vlerësohen mbi saktësisht të njëjtat mostra, sepse një pjesë e "
        "depove sot mungon, ndaj dallimi lexohet si tregues dhe jo si provë.",
        "Rezultatet janë shumë larg atyre të Arcelli Fontana et al. (2016), ku "
        "shumica e klasifikuesve kaluan 95% në saktësi dhe F-measure. Di Nucci et al. "
        "(2018) treguan se ato vlera vinin nga ndërtimi i dataset-it: me shpërndarje më "
        "realiste të metrikave, F-measure ra deri në 90% më poshtë. MLCQ është ky lloj "
        f"dataset-i realist, dhe F1-i i këtij punimi, nga {_span(f1, 2)}, e konfirmon "
        "drejtimin e Di Nucci et al.: mësimi i makinës ndihmon, por problemi nuk është "
        "i zgjidhur.",
    ]
    if ceiling is not None:
        values = [entry["mcc"] for entry in ceiling["per_smell"].values()]
        paragraphs.append(
            "Mäntylä & Lassenius (2006) gjetën se vlerësimi i erërave nga zhvilluesit "
            "është subjektiv, dhe ky punim e mat këtë mbi MLCQ: dy rishikues të së "
            f"njëjtës mostër pajtohen me MCC nga {_span(values, 2)}. Etiketa e agreguar "
            "është mesatare e disa gjykimeve dhe e zbut zhurmën e secilit, ndaj modelet "
            "mund të pajtohen me të më shumë se sa pajtohen dy rishikues mes tyre. Kjo "
            "nuk e bën modelin më të mirë se njeriun, por tregon se shifrat e fushës "
            "duhen lexuar kundrejt një tavani të ulët."
        )
    paragraphs.append(
        "Te rregullat, rezultati përputhet me vërejtjen e Nënkapitullit 2.3 se pragjet "
        "e nxjerra nga një korpus nuk transferohen lehtë në një tjetër: strategjitë e "
        "Lanza & Marinescu (2006) ruajnë precizion të lartë mbi MLCQ, por humbin "
        "shumicën e rasteve. PMD-ja, që zbaton të njëjtat strategji me pragjet e veta, "
        "nuk del më mirë në asnjë krahasim (Nënkapitulli 5.6), ndaj recall-i i ulët nuk "
        "është defekt i zbatimit tonë. Te refaktorimi, motori ndjek parimin e Opdyke "
        "(1992): transformimi aplikohet vetëm kur parakushtet provohen. Tsantalis & "
        "Chatzigeorgiou (2009) ia lënë vendimin përfundimtar projektuesit; ky punim e "
        "aplikon rishkrimin, por vetëm pas verifikimit me kompilator dhe vetëm aty ku "
        "kthimi është një komandë."
    )
    refactoring = _load("refactoring_evaluation.json")
    resolved = refactoring["resolution"]["resolved"] / refactoring["applied"]
    paragraphs.append(
        "Dy gjetje të tjera lidhen me literaturën për ndikimin e erërave. Roli i "
        "madhësisë te Blob-i, i diskutuar te Nënkapitulli 6.2, ka një paralel te "
        "Sjøberg et al. (2013): edhe atje madhësia e kodit peshonte më shumë se "
        "erërat vetë në përpjekjen e mirëmbajtjes. Te refaktorimi, Bavota et al. (2015) gjetën se vetëm 7% e "
        "refaktorimeve të zhvilluesve e heqin erën nga klasa; motori i këtij punimi e "
        f"heq atë te {resolved:.1%} e rishkrimeve që aplikon. Krahasimi nuk është i "
        "drejtpërdrejtë, sepse zhvilluesit shpesh refaktorojnë për arsye që nuk kanë "
        "lidhje me një erë (Silva et al., 2016), por tregon vlerën e një transformimi "
        "që zgjidhet për erën e gjetur dhe matet pas aplikimit."
    )
    return paragraphs


def _gain_parts(h: dict) -> dict[str, tuple[float, float]] | None:
    """Fitimi i Qasjes B mbi rregullin, i ndarë në dy pjesë, për çdo erë.

    E para është ajo që modeli fiton kur sheh vetëm metrikat e strategjisë, pra
    duke mësuar vetëm ku pritet kufiri. E dyta është ajo që shtojnë metrikat e
    tjera mbi të. Kthen `None` kur ablacioni nuk është ekzekutuar (VD-132).
    """
    data = _load_if_present("ml_strategy_features.json")
    if data is None:
        return None
    parts: dict[str, tuple[float, float]] = {}
    for smell in h["smells"]:
        entry = data["per_smell"].get(smell)
        if entry is None:
            continue
        restricted = entry["models"][entry["best_model"]]["mcc"]
        if restricted is None:
            continue
        parts[smell] = (
            restricted - h["strategy"][smell]["mcc"],
            h["model"][smell]["mcc"] - restricted,
        )
    return parts or None


def _gain_split(h: dict) -> str:
    """Nga vjen fitimi i Qasjes B, nga ablacioni i Nënkapitullit 5.2.

    Fjala që qëndronte këtu thoshte se strategjive «nuk u mungojnë metrikat, u
    mungon vendi ku t'i presin». Asgjë nuk e kishte matur. Modeli shihte 17 ose
    26 metrika kundrejt një deri në katër të strategjisë, dhe ablacioni tregoi se
    fitimi vjen nga të dyja anët (VD-132).
    """
    parts = _gain_parts(h)
    if parts is None:
        return ""
    cut = {smell: gain for smell, (gain, _) in parts.items()}
    extra = {smell: gain for smell, (_, gain) in parts.items()}
    rising = sum(1 for gain in cut.values() if gain > 0)
    most = max(extra, key=lambda smell: extra[smell])
    return (
        " Ablacioni i Nënkapitullit 5.2 e ndan këtë fitim në dy pjesë. Vetëm me "
        "metrikat e strategjisë, pra duke mësuar vetëm ku pritet kufiri, modeli e ngre "
        f"MCC-në {_among(rising, len(cut))}, me {_span(list(cut.values()))}. Metrikat e "
        f"tjera shtojnë edhe {_span(list(extra.values()))}, më së shumti te "
        f"{SMELL_SQ[most]}. Strategjive u mungojnë pra të dyja: kufiri i duhur dhe një "
        "pjesë e informacionit."
    )


def _gain_in_answer(h: dict) -> str:
    """Një fjali për PK2: a mbetet fitimi kur modeli sheh vetëm metrikat e strategjisë."""
    parts = _gain_parts(h)
    if parts is None:
        return ""
    if all(cut > 0 for cut, _ in parts.values()):
        return (
            " Fitimi mbetet, më i vogël, edhe kur modeli sheh vetëm metrikat e "
            "strategjisë, ndaj nuk vjen vetëm nga metrikat shtesë (Nënkapitulli 5.2)."
        )
    return (
        " Kur modeli sheh vetëm metrikat e strategjisë, fitimi nuk mbetet te çdo erë "
        "(Nënkapitulli 5.2)."
    )


def _answers(h: dict) -> list:
    """Përgjigjet e qarta ndaj tri pyetjeve kërkimore, nga të dhënat."""
    smells, strategy, model = h["smells"], h["strategy"], h["model"]
    best = max(smells, key=lambda s: strategy[s]["mcc"])
    worst = min(smells, key=lambda s: strategy[s]["mcc"])
    intervals = _load_if_present("bootstrap_intervals.json")
    positive = None
    if intervals is not None:
        positive = sum(
            1
            for entry in intervals["per_smell"].values()
            if entry["intervals"]["difference_model_minus_rules"]["low"] > 0
        )
    gained = sum(1 for s in smells if model[s]["recall"] > strategy[s]["recall"])
    cautious = sum(1 for s in smells if strategy[s]["precision"] > strategy[s]["recall"])

    def of_smells(count: int) -> str:
        return "te çdo erë" if count == len(smells) else f"te {count} nga {len(smells)} erërat"

    # Pyetjet shkruhen me një etiketë të shkurtër e jo të plota: janë te
    # Nënkapitulli 3.1, dhe rishkrimi i tyre fjalë për fjalë ishte përsëritja që
    # lexuesi e sheh e para (VD-128). Po ashtu, shifrat e plota të Kapitullit 5 nuk
    # rikopjohen; merret vetëm ajo që e mban përgjigjen.
    answers = [
        "**PK1, saktësia e strategjive.** Precizioni i tyre e kalon recall-in "
        f"{of_smells(cautious)}, dhe MCC-ja kundrejt rishikuesve shkon nga "
        f"{_span([strategy[s]['mcc'] for s in smells])}, më e larta te {SMELL_SQ[best]} "
        f"dhe më e ulëta te {SMELL_SQ[worst]}. Ashpërsia që derivojnë nuk pajtohet me "
        "atë të rishikuesve.",
        "**PK2, mësimi i makinës.** Po, e përmirëson. Modeli i mësuar mbi "
        "metrikat e sistemit e ngre MCC-në te të katër erërat: brezi kalon nga "
        f"{min(strategy[s]['mcc'] for s in smells):.3f}–"
        f"{max(strategy[s]['mcc'] for s in smells):.3f} në "
        f"{min(model[s]['mcc'] for s in smells):.3f}–"
        f"{max(model[s]['mcc'] for s in smells):.3f}"
        + (
            ", dhe intervalet bootstrap sipas depos e vendosin këtë përparësi mbi zero "
            + ("pa përjashtim" if positive == len(smells) else of_smells(positive))
            if positive is not None
            else ""
        )
        + f". Fitimi vjen kryesisht nga recall-i, që rritet {of_smells(gained)}. Një "
        "rezervë e vetme: kur rregullit i jepet pragu i tij më i "
        "mirë nga fshirja, dallimi te Long Method nuk ndahet më nga zeroja "
        "(Nënkapitulli 5.7)." + _gain_in_answer(h),
    ]

    data = _load_if_present("refactoring_evaluation.json")
    if data is not None:
        applied, detected = data["applied"], data["detected"]
        verdicts = data["verdicts"]
        resolution = data.get("resolution") or {}
        total = sum(resolution.values()) or 1
        safe = verdicts.get("no_new_errors", 0) + verdicts.get("compiles", 0)
        answers.append(
            "**PK3, refaktorimi.** Pjesërisht. Motori transformoi "
            f"{applied / detected:.1%} të vendeve të detektuara; nga rishkrimet, "
            f"{safe / applied:.1%} kompiluan ose nuk shtuan lloj të ri gabimi, dhe "
            f"{verdicts.get('new_errors', 0) / applied:.1%} shtuan. Era u hoq te "
            f"{resolution.get('resolved', 0) / total:.1%} e tyre, dhe metrika që e "
            "shkakton detektimin ra edhe aty ku era mbeti: struktura përmirësohet "
            "objektivisht në shumicën e rasteve, me koston e "
            f"{sum((data.get('introduced_smells') or {}).values())} erërave të reja. Kur "
            f"skedari kompilohet brenda projektit të vet, {_context_conclusion()}. "
            "Ruajtja e sjelljes **nuk u mat** (Nënkapitulli 3.4). Përgjigjja është pra po "
            "për strukturën dhe kompilueshmërinë, me kosto të matur, dhe e hapur për "
            "sjelljen."
        )
    return answers


def _one_in_how_many() -> str:
    """«rreth një në pesë vende», nga pjesa e vendeve që motori i transformoi.

    Ishte shtypur me dorë; po të ndryshonte norma, 6.5 do të fliste për një
    numër tjetër nga ai i Kapitullit 5.
    """
    data = _load_if_present("refactoring_evaluation.json")
    if data is None or not data["applied"]:
        return "një pjesë të vendeve"
    return f"rreth një në {_word(round(data['detected'] / data['applied']))} vende"


def _strategy_source(title: str) -> str:
    """Burimi i një strategjie, nga titulli që mban docstring-u i detektorit.

    Titujt janë në anglisht dhe të formave të ndryshme: «God Class (Lanza &
    Marinescu, p. 80)», «Long Method (Fowler): …», «Deeply nested control flow».
    Tabela i shkruante copat siç binin, ndaj dilte «Fowler): size alone…». Këtu
    merret vetëm kllapa, me vitin e referencës dhe «f.» për faqen.
    """
    match = re.search(r"\(([^)]*)\)", title)
    if match is None:
        return "—"
    author, _, page = match.group(1).partition(", p. ")
    year = {"Lanza & Marinescu": 2006, "Fowler": 2018}.get(author)
    source = f"{author} ({year})" if year else author
    return f"{source}, f. {page}" if page else source


def chapter_6() -> list:
    """Diskutimi dhe përfundimet, me pohimet empirike të lexuara nga rezultatet.

    Ishte listë statike, dhe pikërisht ashtu rrëshqiti: përfundimi pohonte se asnjë
    verdikt nuk u përmbys, ndërsa Kapitulli 5 e lexonte numrin nga skedari dhe e
    kishte tërhequr atë pohim kur mostra u dyfishua (VD-55). Kapitulli i fundit që
    lexon komisioni është vendi i fundit ku një pohim i vjetruar duhet të mbijetojë.

    Rregulli i mentores (VD-125): Kapitulli 5 i paraqet rezultatet pa i shpjeguar;
    këtu shpjegohet çfarë do të thotë secili, çfarë funksionoi dhe çfarë jo, si
    krahasohet me literaturën, dhe si përgjigjet secila pyetje kërkimore.
    """
    h = _headline()
    return [
        (
            "6.1",
            "Interpretimi i rezultateve",
            [
                *_reading_of_detection(h),
                *_reading_of_refactoring(),
            ],
        ),
        (
            "6.2",
            "Çfarë funksionoi dhe çfarë jo",
            [
                "**Çfarë funksionoi.** Tri zgjedhje metodologjike u dëshmuan të "
                "drejta. Ndarja e grupuar sipas depos e la vlerësimin pa rrjedhje, ndaj "
                "krahasimi i dy "
                "qasjeve mbi të njëjtat mostra është i ndershëm. Refuzimi si parim e "
                "mbajti motorin larg kodit që nuk e kuptonte, dhe dëmi mbeti te pakica e "
                "raportuar. Matja mbi kod real, më në fund, kapi tri defekte që testet e "
                "njësisë i kishin lënë të kalonin (Nënkapitulli 5.4).",
                "**Çfarë nuk funksionoi.** Strategjitë nuk matin plotësisht atë që "
                "emërtojnë. Dy gjetje të pavarura tregojnë në të njëjtin drejtim. E "
                "para: kur modeleve u lihet të zgjedhin vetë veçoritë, te Blob nuk "
                "zgjidhen TCC dhe WMC, pikërisht kushtet e kohezionit dhe të "
                "kompleksitetit mbi të cilat është ndërtuar God Class, por metrikat e "
                "madhësisë. E dyta: shtimi i një detektori që mbështetet vetëm te "
                "madhësia e përmirëson përputhjen me rishikuesit për të njëjtën erë.",
                *_blocking_in_discussion(),
                "Këto sugjerojnë se ajo që rishikuesit e MLCQ-së e quajnë «blob» "
                "shpjegohet më mirë me madhësi sesa me kohezionin që strategjia e vendos "
                "në qendër. Strategjia nuk bëhet e gabuar prej kësaj; rishikuesit dhe "
                "autorët e saj thjesht nuk kanë ndër mend saktësisht të njëjtën erë.",
                "Edhe ashpërsia doli rezultat negativ: e llogaritur nga teprica, ajo u "
                "pajtua me rishikuesit afërsisht sa rastësia te tri nga katër erërat, "
                "duke e mbivlerësuar sistematikisht (Shtojca 8.7). "
                f"{_calibration_verdict()}, dhe {_folds_disagree()}; një prag «optimal» "
                "që ndryshon me pjesën e korpusit që shihet është veti e bashkësisë, jo "
                "e gjuhës (Nënkapitulli 5.5).",
                "Te refaktorimi, dy transformime të rekomanduara gjerësisht e "
                "zhvendosin problemin në vend që ta heqin. Encapsulate Field, i "
                "rekomanduar për Data Class, e përkeqëson matjen sipas vetë përkufizimit "
                "të strategjisë: një fushë publike bëhet dy akses-metoda publike, dhe të "
                "dyja kushtet e strategjisë e numërojnë këtë si përkeqësim. Fowler-i e "
                "trajton atë si hap përgatitor, jo si ilaç. Extract Method e ka të "
                "njëjtin cen në shkallë më të vogël, përmes listës së gjatë të "
                "parametrave që lë pas (Nënkapitulli 6.1).",
            ],
        ),
        (
            "6.3",
            "Krahasimi me literaturën",
            _literature_comparison(h),
        ),
        (
            "6.4",
            "Përgjigjet ndaj pyetjeve kërkimore",
            _answers(h),
        ),
        (
            "6.5",
            "Implikimet teorike dhe praktike",
            [
                "**Implikime teorike.** Strategjitë e publikuara nuk hidhen poshtë nga "
                "këto rezultate: si njohuri e shpjegueshme për atë që e bën një klasë "
                "të dyshimtë, ato mbeten të vlefshme. Ajo që nuk kalon nga një korpus "
                "te tjetri janë kufijtë numerikë, të cilët duhen kalibruar ose mësuar "
                "për kodin ku zbatohen. Pajtimi i ulët mes rishikuesve i vë gjithashtu "
                "një tavan çdo detektori, përtej të cilit gabimi i përket paqartësisë "
                "së vetë erës.",
                "**Implikime praktike.** Për një ekip, strategjitë janë sinjal i rrallë "
                "por i besueshëm, i përshtatshëm si paralajmërim që nuk e mbyt "
                "zhvilluesin me zhurmë. Modeli vlen aty ku ka më shumë rëndësi të mos "
                "humbasë asnjë rast, dhe kur të dyja pajtohen, sistemi jep sinjalin e "
                "tij më të sigurt. Rishkrimi automatik mund t'i besohet mjetit për "
                f"{_one_in_how_many()}, me kusht që ai të refuzojë çdo gjë që nuk e provon "
                "dhe ta masë atë që ndodh pas rishkrimit.",
                "Meqë shumica e erërave lindin bashkë me kodin (Tufano et al., 2015), "
                "mjeti ka më shumë vlerë kur vepron herët, si portë në integrimin e "
                "vazhdueshëm, sesa si auditim i rrallë mbi një sistem të pjekur. Për "
                "Feature Envy, erën që literatura e trajton më shpesh si objektiv "
                "refaktorimi, mjetet e lira të përhapura ofrojnë pak: PMD nuk ka rregull "
                "për të, DesigniteJava nuk e përfshin mes erërave që dokumenton, dhe "
                "JDeodorant, që e gjen përmes mundësive për Move Method (Tsantalis & "
                "Chatzigeorgiou, 2009), punon si shtojcë e mjedisit të zhvillimit, ndërsa "
                "varianti i tij në rresht komande nuk mban licencë. Një detektor i lirë "
                "që punon nga rreshti i komandës e mbush pjesërisht këtë boshllëk.",
            ],
        ),
        (
            "6.6",
            "Kufizimet",
            [
                "Mostrat e depove që nuk ishin më të arritshme mungojnë nga vlerësimi "
                "(hyrja e Kapitullit 5); nëse ato ndryshojnë sistematikisht nga pjesa "
                "tjetër, shifrat e raportuara nuk e pasqyrojnë këtë. E vërteta "
                "bazë vjen nga një dataset i vetëm, me mospajtim të konsiderueshëm mes "
                "rishikuesve; prandaj çdo strategji agregimi raportohet veç, dhe mostrat "
                "që një strategji nuk i etiketon dot hidhen në vend që të lexohen si "
                "negative.",
                "Verifikimi i refaktorimeve kufizohet te kompilatori, dhe për shumicën e "
                "skedarëve vetëm te forma e tij më e dobët, mungesa e llojeve të reja të "
                "gabimit; testet e projekteve nuk u ekzekutuan, për arsyen e dhënë te "
                "Nënkapitulli 3.4. "
                "Cilësia e rishkrimeve u gjykua nga një rishikues i vetëm, autori i "
                "motorit, ndaj për të nuk ka pajtim mes rishikuesish që të matet.",
                "Pa zgjidhje simbolesh (Nënkapitulli 3.4), motori ndreq vetëm atë që "
                "mbyllet brenda një skedari; erërat që kërkojnë "
                "ndryshime në gjithë projektin mbeten te zhvilluesi. Për të njëjtën arsye, "
                "ATFD-ja nuk i ndjek marrësit me zinxhir («a.getB().getC()»): matet në "
                "mënyrë konservative, dhe mund t'i humbasë disa raste të Feature Envy-së e "
                "të God Class-it. Po ashtu, niveli i "
                "ashpërsisë që shfaq mjeti është renditje e brendshme e tij dhe jo "
                "parashikim i gjykimit njerëzor.",
                *_blob_recall_limits(),
            ],
        ),
        (
            "6.7",
            "Puna e ardhshme",
            [
                (
                    "bullet",
                    "Verifikim me suitat e testeve të projekteve të korpusit, që "
                    "pretendimi të ngrihet nga «kompilon» në «ruan sjelljen».",
                ),
                (
                    "bullet",
                    "Një zgjidhës i kufizuar simbolesh brenda një projekti, i cili do t'i "
                    "hapte rrugën Encapsulate Field-it dhe Move Method-it.",
                ),
                (
                    "bullet",
                    "Extract Method që e kufizon numrin e parametrave të metodës së "
                    "nxjerrë, që rishkrimi të mos sjellë Long Parameter List.",
                ),
                (
                    "bullet",
                    "Zgjerim i të vërtetës bazë përtej katër erërave që mbulon MLCQ, dhe "
                    "gjykim i cilësisë së rishkrimeve nga rishikues të pavarur.",
                ),
                (
                    "bullet",
                    "Ashpërsi e mësuar nga të dhënat në vend që të derivohet nga teprica, "
                    "me ndarjen e vet të korpusit.",
                ),
            ],
        ),
        (
            "6.8",
            "Përfundim",
            [
                "Punimi u nis nga pyetja nëse erërat e kodit mund të gjenden dhe të "
                "ndreqen automatikisht në një mënyrë të cilës zhvilluesi t'i besojë. "
                "Përgjigjja që japin të dhënat është e ndarë. Gjetja mund t'u besohet "
                "metrikave, por jo pragjeve të fiksuara gjetiu: kufiri i mësuar nga vetë "
                "bashkësia jep më shumë se ai i trashëguar. Ndreqja mund t'i besohet "
                "makinës vetëm aty ku ajo e provon se ka të drejtë, dhe kjo ndodh më rrallë "
                "sesa ndeshen erërat. Mes të dyjave qëndron një kufi që asnjë algoritëm nuk "
                "e kapërcen: as rishikuesit nuk pajtohen plotësisht se ku fillon një erë.",
                "Më i qëndrueshëm se çdo shifër është mësimi metodologjik. Dy qasje "
                "krahasohen me kuptim vetëm mbi të njëjtat mostra dhe me një ndarje që nuk "
                "rrjedh nga një depo te tjetra, dhe një rishkrim vlen aq sa verifikimi që "
                "e ndjek. Që këto të mos mbeten pohime, çdo numër i punimit rigjenerohet "
                "nga korpusi me një komandë, dhe çdo vendim ruhet bashkë me arsyen e vet.",
            ],
        ),
    ]


# ======================================================================
# Kapitulli 5: teksti rreth numrave, numrat nga data/results
# ======================================================================
# Analizat që nuk i përgjigjen drejtpërdrejt një pyetjeje kërkimore. VD-113 i nxori
# të gjashta te shtojcat nën një kufi prej 8 deri 10 mijë fjalësh që ishte lexuar gabim;
# rregulli i UBT-së është minimumi 10 000 fjalë pa shtojca. Tri që e mbajnë një shifër
# të Kapitullit 5 kthehen në kapitull, të plota, dhe tri të tjerat mbeten shtojca
# (VD-135). Numrat e seksioneve jepen sipas radhës, që asnjë vrimë të mos mbetet.
SECONDARY_IN_CHAPTER = ("5.5", "5.6", "5.9")
SECONDARY_RESULTS = ("5.7", "5.8", "5.10")
FIRST_SECONDARY_IN_CHAPTER = 5
FIRST_APPENDIX_FOR_RESULTS = 6


def chapter_5() -> list:
    """Rezultatet që u përgjigjen pyetjeve kërkimore, 5.1 deri 5.4, dhe tri analiza pas tyre."""
    kept = [section for section in _results_sections() if section[0] not in SECONDARY_RESULTS]
    renumbered = []
    offset = 0
    for number, title, paragraphs in kept:
        if number in SECONDARY_IN_CHAPTER:
            number = f"5.{FIRST_SECONDARY_IN_CHAPTER + offset}"
            offset += 1
        renumbered.append((number, title, paragraphs))
    return renumbered


def secondary_results() -> list:
    """Analizat dytësore që mbeten shtojca, të rinumëruara si Shtojcat 8.6 deri 8.8."""
    moved = [section for section in _results_sections() if section[0] in SECONDARY_RESULTS]
    return [
        (f"8.{FIRST_APPENDIX_FOR_RESULTS + offset}", title, paragraphs)
        for offset, (_, title, paragraphs) in enumerate(moved)
    ]


def _strategy_feature_paragraphs(rules: dict, ml: dict, smells: list) -> list:
    """Qasja B e kufizuar te metrikat e strategjisë, përballë rregullit dhe modelit të plotë."""
    data = _load_if_present("ml_strategy_features.json")
    if data is None:
        return []
    rows = []
    for smell in smells:
        entry = data["per_smell"].get(smell)
        if entry is None:
            continue
        full = ml["per_smell"][smell]
        rows.append(
            [
                SMELL_SQ[smell],
                ", ".join(entry["features"]),
                _mcc(rules["per_smell"][smell]["strategy"]["by_aggregation"]["mean"]["mcc"]),
                _mcc(entry["models"][entry["best_model"]]["mcc"]),
                _mcc(full["models"][full["best_model"]]["mcc"]),
            ]
        )
    return [
        "Vetëm me metrikat e strategjisë, modelet arrijnë këtë MCC:",
        ("table", "MCC me metrikat e strategjisë dhe me të gjitha metrikat",
         ["Erë", "Metrikat e strategjisë", "Rregulli", "Modeli, vetëm ato",
          "Modeli, të gjitha"], rows),  # fmt: skip
    ]


def _results_sections() -> list:
    """Të gjitha seksionet e rezultateve, të ndërtuara nga skedarët e komituar."""
    rules = _load("rules_evaluation.json")
    ml = _load("ml_evaluation.json")
    dataset = _load("mlcq_dataset.json")
    sweep = _load("threshold_sweep.json")

    smells = sorted(ml["per_smell"])
    scored = dataset["rows"]

    rules_rows = []
    for smell in smells:
        for variant, data in rules["per_smell"][smell].items():
            mean = data["by_aggregation"]["mean"]
            label = SMELL_SQ[smell] + ("" if variant == "strategy" else " (+ madhësi)")
            rules_rows.append(
                [
                    label,
                    f"{mean['precision']:.3f}",
                    f"{mean['recall']:.3f}",
                    f"{mean['f1']:.3f}",
                    f"{mean['mcc']:.3f}",
                    str(mean["support_positive"]),
                ]
            )

    ml_rows = []
    for smell in smells:
        entry = ml["per_smell"][smell]
        best = entry["models"][entry["best_model"]]
        ml_rows.append(
            [
                SMELL_SQ[smell],
                entry["best_model"].replace("_", " "),
                f"{best['precision']:.3f}",
                f"{best['recall']:.3f}",
                f"{best['f1']:.3f}",
                f"{best['mcc']:.3f}",
            ]
        )

    agreement_rows = []
    for smell in smells:
        vs = ml["per_smell"][smell]["vs_rules"]
        agreement_rows.append(
            [
                SMELL_SQ[smell],
                f"{vs['kappa']:.3f}",
                str(vs["both"]),
                str(vs["only_rules"]),
                str(vs["only_model"]),
                str(vs["n"]),
            ]
        )

    severity_rows = []
    for smell in smells:
        for variant, data in rules["per_smell"][smell].items():
            by_severity = data.get("recall_by_severity") or {}
            if "major" not in by_severity or "minor" not in by_severity:
                continue
            major, minor = by_severity["major"], by_severity["minor"]
            label = SMELL_SQ[smell] + ("" if variant == "strategy" else " (+ madhësi)")
            severity_rows.append(
                [
                    label,
                    f"{major['caught']}/{major['support']} ({major['caught'] / major['support']:.1%})",
                    f"{minor['caught']}/{minor['support']} ({minor['caught'] / minor['support']:.1%})",
                ]
            )

    sweep_rows = []
    for smell in smells:
        for name, points in sweep["per_smell"].get(smell, {}).items():
            values = [p["mcc"] for p in points if p["mcc"] is not None]
            published = next(p["mcc"] for p in points if p["factor"] == 1.00)
            sweep_rows.append(
                [
                    SMELL_SQ[smell],
                    name,
                    f"{published:.3f}",
                    f"{min(values):.3f} – {max(values):.3f}",
                    f"{max(values) - min(values):.3f}",
                ]
            )
    sweep_rows.sort(key=lambda r: -float(r[4]))

    best_mcc = max(ml["per_smell"][s]["models"][ml["per_smell"][s]["best_model"]]["mcc"] for s in smells)

    return [
        (
            None,
            "",
            [
                f"Të gjitha shifrat e këtij kapitulli janë prodhuar mbi {scored} mostra "
                f"nga {_repositories_in_dataset()} depo, dhe rigjenerohen me një komandë. "
                "Agregimi i etiketave është mesatarja e rrumbullakosur lart, përveç "
                "aty ku thuhet ndryshe.",
                _coverage_sentence(),
                ("figure", str(FIGURES / "shperndarja_e_mostrave.png"),
                 "Shpërndarja e mostrave sipas erës"),
                "Rezultatet kryesore ndjekin pyetjet kërkimore: 5.1 i përgjigjet PK1, "
                "5.2 dhe 5.3 PK2, dhe 5.4 PK3. Vëzhgimet dytësore vijnë pas tyre: "
                "ndjeshmëria ndaj pragjeve (5.5), krahasimi me një mjet ekzistues (5.6), "
                "dhe intervalet e besimit bashkë me pajtimin mes rishikuesve (5.7). "
                "Analizat e tjera dytësore janë te Shtojcat 8.6 deri 8.8.",
            ],
        ),
        (
            "5.1",
            "Qasja A: detektimi me rregulla",
            [
                "Kundrejt gjykimit të rishikuesve, strategjitë arrijnë këtë precizion (P), "
                "recall (R), F1 dhe MCC për çdo erë, mbi numrin e mostrave pozitive në "
                "kolonën e fundit.",
                ("table", "Qasja A kundrejt gjykimit të rishikuesve",
                 ["Erë", "P", "R", "F1", "MCC", "Pozitivë"], rules_rows),
                _precision_over_recall(rules, smells),
                "Recall-i ndryshon ndjeshëm sipas ashpërsisë që rishikuesit i dhanë "
                "secilës mostër.",
                ("table", "Recall-i sipas ashpërsisë",
                 ["Erë", "Recall te major", "Recall te minor"], severity_rows),
                ("figure", str(FIGURES / "recall_sipas_ashpersise.png"),
                 "Recall-i sipas ashpërsisë së caktuar nga rishikuesit"),
                _severity_direction(rules, smells),
            ],
        ),
        (
            "5.2",
            "Qasja B: detektimi me mësim makine",
            [
                "Për secilën erë raportohet modeli me MCC-në më të lartë, i pikëzuar mbi "
                "parashikimet jashtë fold-it. Klasifikuesi i shumicës nuk ndez asnjëherë "
                "për asnjë erë, ndaj MCC-ja e tij është e papërcaktuar.",
                ("table", "Modeli më i mirë për çdo erë",
                 ["Erë", "Modeli", "P", "R", "F1", "MCC"], ml_rows),
                f"MCC-ja më e lartë e arritur është {best_mcc:.3f}. Veçoritë që peshojnë më "
                "shumë te secila erë, të matura me permutim, janë këto:",
                ("figure", str(FIGURES / "rendesia_e_vecorive.png"),
                 "Veçoritë me rëndësi më të lartë, të matura me permutation importance"),
                *_explanation_paragraphs(ml),
                *_strategy_feature_paragraphs(rules, ml, smells),
            ],
        ),
        (
            "5.3",
            "Krahasimi i dy qasjeve",
            [
                ("figure", str(FIGURES / "mcc_a_vs_b.png"),
                 "MCC për të dyja qasjet"),
                _who_is_higher(rules, ml, smells),
                ("table", "Pajtimi mes dy qasjeve",
                 ["Erë", "κ", "Të dyja", "Vetëm A", "Vetëm B", "n"], agreement_rows),
                ("figure", str(FIGURES / "pajtimi_a_b.png"),
                 "Mostrat e shënuara nga secila qasje"),
                _only_rules_vs_only_model(ml, smells),
                *_combined_paragraphs(ml),
            ],
        ),
        (
            "5.4",
            "Qasja C: refaktorimi",
            [
                *_refactoring_section(),
                "Gjatë ekzekutimit mbi korpus, verifikimi nxori edhe tri defekte në "
                "motor që prodhonin kod që nuk kompilon, dhe që testet e shkruara me dorë "
                "nuk i kishin kapur: deklarimet brenda një cikli të mëparshëm "
                "numëroheshin si të dukshme, kllapat e vargut pas emrit të variablës nuk "
                "hynin në tip, dhe klauzola «throws» nuk bartej te metoda e nxjerrë.",
            ],
        ),
        (
            "5.5",
            "Ndjeshmëria ndaj pragjeve",
            [
                "Secili prag i strategjive u zhvendos veç me faktorët e Nënkapitullit "
                "4.9, ndërsa të tjerët mbetën te vlerat e botuara. Rreshtat renditen "
                "sipas amplitudës, pra dallimit mes MCC-së më të lartë dhe më të ulët "
                "që jep pragu:",
                ("table", "Sa lëviz MCC-ja kur zhvendoset një prag",
                 ["Erë", "Pragu", "Te vlera e botuar", "Brezi", "Amplituda"], sweep_rows),
                ("figure", str(FIGURES / "ndjeshmeria_e_pragjeve.png"),
                 "Ndjeshmëria e MCC-së ndaj zhvendosjes së pragjeve"),
                *_sweep_facts(sweep, sweep_rows),
                *_calibration_paragraphs(),
            ],
        ),
        (
            "5.6",
            "Krahasimi me një mjet ekzistues",
            [
                *_pmd_comparison_paragraphs(),
            ],
        ),
        *_blocking_section(),
        *_severity_section(),
        *_confidence_section(),
        *_blob_recall_section(),
    ]


SEVERITY_SCALE = ("minor", "major", "critical")

RESOLUTION_SQ = {
    "resolved": "era u hoq",
    "persists": "era mbeti",
    "unknown": "entiteti nuk u identifikua dot",
}


SMELL_VARIANT_SQ = {
    "blob/strategy": "Blob, strategjia",
    "blob/with_size": "Blob, me madhësinë",
    "data class/strategy": "Data Class",
    "long method/strategy": "Long Method",
    "feature envy/law_of_demeter": "Feature Envy (LawOfDemeter)",
}


def _mcc(value: float | None) -> str:
    """Një MCC i papërcaktuar shtypet si i tillë, kurrë si zero.

    I papërcaktuar do të thotë se njëra margjinë e matricës është bosh — zakonisht
    se detektori nuk ndezi kurrë. Zeroja do të thoshte se ndezi dhe nuk mësoi
    asgjë, dhe këto janë dy rezultate të ndryshme.
    """
    return "i papërcaktuar" if value is None else f"{value:.3f}"


def _who_leads(entry: dict) -> str | None:
    """Cila anë del përpara, vendosur nga intervali i çiftuar e jo nga dy pikat.

    Dy MCC-ra ndryshojnë pothuaj gjithmonë te shifra e tretë, ndaj pyetja nuk
    është cili numër është më i madh por a e mban riterheqja atë ndryshim. Këtu
    qëndronte një prag prej 0.005 që nuk vinte nga asgjë, dhe ai e shpallte
    fitore një ndryshim prej 0.009 që intervali e nxjerr si zhurmë. Numri i
    vetëm nuk mjafton për ta thënë; intervali e thotë.
    """
    if entry.get("ours") is None:
        return None
    difference = entry.get("difference")
    if difference is None:
        return None
    if not difference["excludes_zero"]:
        return "tie"
    return "ours" if difference["median"] > 0 else "pmd"

def _pmd_balance(data: dict) -> str:
    """Kush del përpara dhe sa herë, matur me interval e jo pohuar nga dy pika.

    Shkruar si degëzim sepse daljet — ne përpara, PMD përpara, të padallueshme —
    janë pohime të ndryshme, dhe fjalia e shkruar për njërën lexohet si mohim i
    tjetrës. Kjo tabelë ishte gjëja e parë që mund ta bënte punimin të pohonte një
    fitore që të dhënat nuk e mbajnë, dhe në një lexim të parë pothuajse e bëri:
    PMD dukej përpara te Blob-i me strategjinë, derisa intervali i çiftuar
    tregoi se ai ndryshim e përmban zeron.
    """
    leads = [_who_leads(entry) for entry in data["by_smell"].values()]
    ours = leads.count("ours")
    theirs = leads.count("pmd")
    tied = leads.count("tie")
    answered = ours + theirs + tied
    if not answered:
        return (
            "Asnjë krahasim nuk jep përgjigje: te secili rresht të paktën njëra anë "
            "nuk ndez mjaftueshëm sa koeficienti të përcaktohet."
        )

    ties = (
        ""
        if not tied
        else (
            f" Te {_word(tied)} prej tyre intervali e përmban zeron, "
            "pra dy anët nuk dallohen mbi këtë dëshmi."
        )
    )
    if theirs and not ours:
        return (
            f"Nga {_word(answered)} krahasimet me përgjigje, PMD del përpara te "
            f"{_word(theirs)} dhe "
            "detektorët e këtij punimi te asnjëri. Ky është rezultat negativ dhe "
            "raportohet si i tillë." + ties
        )
    if ours and not theirs:
        return (
            f"Nga {_word(answered)} krahasimet me përgjigje, detektorët e këtij punimi "
            f"dalin përpara te {_word(ours)} dhe PMD te asnjëri." + ties
        )
    if not ours and not theirs:
        return (
            f"Asnjë nga {_word(answered)} krahasimet nuk jep ndryshim që e mban rimostrimi: "
            "mbi këtë korpus dy anët nuk dallohen."
        )
    return (
        f"Rezultati ndahet: nga {_word(answered)} krahasimet me përgjigje, detektorët e "
        f"këtij punimi dalin përpara te {_word(ours)} dhe PMD te {_word(theirs)}." + ties
    )

def _band(difference: dict) -> str:
    """Intervali i çiftuar, i shkruar që shenja të lexohet pa u kërkuar.

    Shenja është e gjithë kuptimi: një interval që e përmban zeron thotë se dy
    anët nuk dallohen, dhe pa shenjat e plusit lexuesi duhet ta zbulojë vetë cila
    anë është përpara. Vlera e mesme nuk shtypet, sepse pyetja nuk është sa por a.
    """
    low, high = difference["low"], difference["high"]
    return f"{low:+.3f} deri {high:+.3f}"


def _pmd_comparison_paragraphs() -> list:
    """Krahasimi me PMD-në, ose një shënim se ekzekutimi nuk ka mbaruar."""
    data = _load_if_present("pmd_comparison.json")
    if data is None:
        return [
            "[PLOTËSO: krahasimi me mjetin e jashtëm gjenerohet nga hapi 19 i "
            "Shtojcës 8.5; tabela shfaqet sapo ai ekzekutim të përfundojë.]"
        ]

    rows = []
    for name, entry in data["by_smell"].items():
        pmd = entry["pmd"]
        ours = entry.get("ours")
        difference = entry.get("difference")
        rows.append(
            [
                SMELL_VARIANT_SQ.get(name, name),
                str(entry["scored"]),
                _mcc(pmd["mcc"]),
                "—" if ours is None else _mcc(ours["mcc"]),
                "—" if difference is None else _band(difference),
            ]
        )

    unreadable = data["files_pmd_could_not_read"]
    failed = len(data["repositories_failed"])

    paragraphs: list = [
        f"PMD {data['pmd_version']} u ekzekutua mbi të njëjtat {data['repositories']} "
        "depo, me pragjet e veta të parazgjedhura, dhe u pikëzua me të njëjtin kod "
        "dhe të njëjtin agregim si Qasja A. Të dyja kolonat rillogariten nga i njëjti "
        "skedar në të njëjtin ekzekutim.",
        ("table", "Detektorët e këtij punimi kundrejt PMD-së, mbi të njëjtat mostra",
         ["Erë", "Mostra", "MCC i PMD-së", "MCC i punimit", "Ndryshimi, IB 95%"],
         rows),  # fmt: skip
        _pmd_balance(data),
        "Për Feature Envy PMD nuk ka rregull, ndaj rreshti i saj ka vetëm MCC-në e "
        "LawOfDemeter-it, rregullit më të afërt, dhe nuk ka kolonë krahasimi.",
    ]

    if unreadable or failed:
        files = (
            "një skedar i vetëm nuk u lexua dot nga PMD"
            if unreadable == 1
            else f"{unreadable} skedarë nuk u lexuan dot nga PMD"
        )
        repos = (
            "një depo e vetme nuk u përpunua fare"
            if failed == 1
            else f"{failed} depo nuk u përpunuan fare"
        )
        total = int(str(_load("rules_evaluation.json")["scored"]))
        paragraphs.append(
            f"Nga ekzekutimi, {files} dhe {repos}. Mostrat e atyre depove janë hequr "
            "nga të dyja kolonat e tabelës, ndaj emëruesi i saj është më i vogël se "
            f"ai i Qasjes A, e cila vlerësoi {total} mostra."
        )
    recovered = len(data.get("reports_recovered", []))
    if recovered:
        which = (
            "Për një depo raporti i PMD-së doli"
            if recovered == 1
            else f"Për {recovered} depo raportet e PMD-së dolën"
        )
        paragraphs.append(
            f"{which} XML i pavlefshëm dhe u lexua me rrugën e rikuperimit të "
            "Nënkapitullit 4.9."
        )
    return paragraphs


def _crossing_share(intervals: dict) -> str:
    """Sa e ruajnë shenjën rimostrimet, te era e vetme që e kalon zeron.

    E nxjerrë e jo e shkruar: po të ndryshojë korpusi ose numri i rimostrimeve,
    fjalia lëviz bashkë me tabelën mbi të cilën mbështetet.
    """
    crossing = [
        band["intervals"]["difference_model_minus_rules_swept"]
        for band in intervals["per_smell"].values()
        if band["intervals"]["difference_model_minus_rules_swept"]["low"] <= 0
    ]
    return f"{min(c['share_positive'] for c in crossing):.1%}" if crossing else "—"


def _swept_best() -> str:
    """MCC-ja më e mirë që fshirja gjen për Long Method, nga vetë fshirja."""
    sweep = _load_if_present("threshold_sweep.json")
    if sweep is None:
        return "—"
    points = [
        point
        for variant in sweep["per_smell"]["long method"].values()
        for point in variant
        if point["mcc"] is not None
    ]
    return f"{max(p['mcc'] for p in points):.3f}" if points else "—"


def _intersection_floor(ml: dict) -> str:
    """Precizioni më i ulët i prerjes mbi erërat, pra dyshemeja e pretendimit."""
    values = [
        v["combined"]["intersection"]["precision"]
        for v in ml["per_smell"].values()
        if "combined" in v
    ]
    return f"{min(values):.2f}" if values else "—"


def _intersection_best(ml: dict) -> str:
    values = [
        v["combined"]["intersection"]["precision"]
        for v in ml["per_smell"].values()
        if "combined" in v
    ]
    return f"{max(values):.3f}" if values else "—"


def _confidence_section() -> list:
    """Intervalet e besimit dhe tavani i pajtimit njerëzor.

    Të dyja i përgjigjen së njëjtës pyetje nga dy anë: sa peshë mban një shifër e
    vetme. E para thotë sa lëviz ajo kur ndryshon korpusi; e dyta thotë kundrejt
    çfarë etikete matet.
    """
    intervals = _load("bootstrap_intervals.json")
    ceiling = _load_if_present("reviewer_agreement.json")

    def span(entry: dict) -> str:
        return f"[{entry['low']:.3f}, {entry['high']:.3f}]"

    rows = []
    swept_rows = []
    for smell in sorted(intervals["per_smell"]):
        data = intervals["per_smell"][smell]
        band = data["intervals"]
        difference = band["difference_model_minus_rules"]
        rows.append([
            SMELL_SQ[smell],
            span(band["rules"]),
            span(band[data["best_model"]]),
            span(difference),
            "po" if difference["low"] > 0 else "jo",
        ])
        swept = band["difference_model_minus_rules_swept"]
        swept_rows.append([
            SMELL_SQ[smell],
            data["swept_knob"],
            span(swept),
            "po" if swept["low"] > 0 else "jo",
            f"{swept['share_positive']:.1%}",
        ])

    widths = {
        SMELL_SQ[smell]: entry["intervals"]["difference_model_minus_rules"]["high"]
        - entry["intervals"]["difference_model_minus_rules"]["low"]
        for smell, entry in intervals["per_smell"].items()
    }
    widest = max(widths, key=lambda name: widths[name])
    above = sum(
        entry["intervals"]["difference_model_minus_rules"]["low"] > 0
        for entry in intervals["per_smell"].values()
    )
    paragraphs: list = [
        f"Me bootstrap sipas depos ({intervals['resamples']} rimostrime, Nënkapitulli "
        "4.9), MCC-ja e secilës qasje dhe dallimi mes tyre kanë këto intervale besimi "
        "95%:",
        ("table", "Intervale besimi 95% për MCC-në",
         ["Erë", "A: rregullat", "B: modeli", "B − A", "E kalon zeron"], rows),
        ("figure", str(FIGURES / "intervalet_e_besimit.png"),
         "MCC me interval besimi 95% për të dyja qasjet"),
        f"Kufiri i poshtëm i dallimit B − A është mbi zero {_among(above, len(widths))}. "
        f"Intervali më i gjerë i dallimit është te {widest}, "
        f"{widths[widest]:.3f} pikë MCC.",
        "Kur Qasja A merr pragun e saj më të mirë nga fshirja e Nënkapitullit 5.5, "
        "dallimi ka këto intervale:",
        ("table", "B − A kur rregullat marrin pragun e tyre më të mirë",
         ["Erë", "Pragu i zhvendosur", "B − A", "E kalon zeron", "Shenja e ruajtur"],
         swept_rows),
        f"{_swept_summary(intervals)} Te Long Method intervali e përfshin zeron, dhe "
        f"shenja pozitive ruhet në {_crossing_share(intervals)} të rimostrimeve.",
    ]

    if ceiling is None:
        return [("5.9", "Intervalet e besimit dhe pajtimi mes rishikuesve", paragraphs)]

    ceiling_rows = [
        [
            SMELL_SQ[smell],
            f"{data['mcc']:.3f}",
            f"{data['accuracy']:.3f}",
            _count(data["pairs"]),
        ]
        for smell, data in sorted(ceiling["per_smell"].items())
    ]
    best = max(data["mcc"] for data in ceiling["per_smell"].values())

    paragraphs += [
        "Pajtimi mes vetë rishikuesve të MLCQ-së, i matur me të njëjtin tregues mbi "
        "çdo çift rishikimesh të së njëjtës mostër (Nënkapitulli 4.9), jep këto "
        "vlera:",
        ("table", "Sa pajtohen rishikuesit me njëri-tjetrin",
         ["Erë", "MCC mes rishikuesve", "Saktësia", "Çifte"], ceiling_rows),
        f"MCC-ja mes rishikuesve nuk e kalon {best:.3f} te asnjë erë.",
    ]

    return [("5.9", "Intervalet e besimit dhe pajtimi mes rishikuesve", paragraphs)]


def _swept_summary(intervals: dict) -> str:
    """Te sa erëra dallimi mbetet mbi zero kur rregullat marrin pragun më të mirë."""
    kept = [
        SMELL_SQ[smell]
        for smell, entry in sorted(intervals["per_smell"].items())
        if entry["intervals"]["difference_model_minus_rules_swept"]["low"] > 0
    ]
    if not kept:
        return "Te asnjë erë kufiri i poshtëm nuk mbetet mbi zero."
    return f"Kufiri i poshtëm mbetet mbi zero te {_joined(kept)}."


def _explanation_paragraphs(ml: dict) -> list:
    """A mund ta arsyetojë modeli një verdikt të vetëm?

    Rëndësia me permutation thotë cila metrikë ka peshë mbi tërë korpusin. Ajo nuk
    i thotë asgjë zhvilluesit që ka përpara një klasë të shënuar. Kjo e mat pikërisht
    atë: sa shpesh një matje e vetme, e kthyer në tipike, e rrëzon verdiktin.
    """
    smells = sorted(ml["per_smell"])
    if not all("explained" in ml["per_smell"][s] for s in smells):
        return []

    rows = []
    for smell in smells:
        entry = ml["per_smell"][smell]["explained"]
        if not entry["flagged"]:
            continue
        # Renditur sipas numrit këtu e jo sipas skedarit: `json.dumps` e shkruan
        # atë me çelësa të renditur alfabetikisht, ndaj radha e ruajtur nuk është
        # radha e rëndësisë.
        ranked = sorted(entry["decisive_feature"].items(), key=lambda pair: -pair[1])
        top = ", ".join(f"{name} ({count})" for name, count in ranked[:3])
        rows.append([
            SMELL_SQ[smell],
            str(entry["flagged"]),
            f"{entry['share']:.1%}",
            top or "—",
        ])
    if not rows:
        return []

    shares = [entry["share"] for entry in (ml["per_smell"][s]["explained"] for s in smells)]
    return [
        "Me metodën e Nënkapitullit 4.6, shumica e verdikteve pozitive të modelit "
        "gjejnë një matje të vetme që i mban; matjet që dalin më shpesh vendimtare kanë "
        "numrin e rasteve në kllapa.",
        ("table", "Sa shpesh një matje e vetme e mban verdiktin",
         ["Erë", "Të shënuara", "Me shpjegim", "Matjet vendimtare"], rows),
        f"Pjesa e verdikteve me shpjegim shkon nga {min(shares):.1%} deri në "
        f"{max(shares):.1%}.",
    ]


def _calibration_paragraphs() -> list:
    """Sa arrijnë rregullat kur pragjet u kalibrohen ndershmërisht.

    Fshirja tregon sa lëviz rezultati; ajo nuk e jep dot një shifër të re, sepse
    vlera më e mirë mbi bashkësinë e vlerësimit është përshtatje ndaj saj. Këtu
    zgjedhja bëhet vetëm mbi foldet e trajnimit dhe pikëzohet mbi foldin e
    mbajtur jashtë, ndaj shifra qëndron.
    """
    data = _load_if_present("threshold_calibration.json")
    if data is None:
        return []

    rows = []
    for smell in sorted(data["per_smell"]):
        entry = data["per_smell"][smell]
        published, calibrated = entry["published"], entry["calibrated"]
        chosen = "; ".join(
            f"{name} = " + ", ".join(f"{value} ({count}×)" for value, count in values.items())
            for name, values in entry["chosen"].items()
        )
        rows.append([
            SMELL_SQ[smell],
            f"{published['mcc']:.3f}",
            f"{calibrated['mcc']:.3f}",
            f"{published['recall']:.3f} → {calibrated['recall']:.3f}",
            f"{published['precision']:.3f} → {calibrated['precision']:.3f}",
            chosen,
        ])

    return [
        f"Me kalibrimin jashtë fold-it ({data['folds']} folde sipas depos, Nënkapitulli "
        "4.9), rregullat arrijnë këto vlera; kolona e fundit jep pragun që zgjodhi "
        "secili fold dhe sa herë u zgjodh:",
        ("table", "Rregullat me pragje të kalibruara, të pikëzuara jashtë fold-it",
         ["Erë", "E botuar", "E kalibruar", "Recall", "Precizion", "Vlerat e zgjedhura"],
         rows),
        *_calibration_facts(data),
        f"Për Long Method, vlera më e mirë e fshirjes mbi tërë korpusin është "
        f"{_swept_best()}, ndërsa kalibrimi jashtë fold-it jep "
        f"{data['per_smell']['long method']['calibrated']['mcc']:.3f}.",
    ]


def _sweep_facts(sweep: dict, sweep_rows: list) -> list:
    """Çfarë tregon fshirja, si fakte të lexuara nga skedari e jo si shpjegim.

    Mentorja e do Kapitullin 5 pa «pse» (VD-125); shpjegimi i këtyre shifrave është
    te Nënkapitulli 6.1. Këtu mbeten vetëm vlerat, që të lëvizin bashkë me
    tabelën kur rigjenerohet fshirja.
    """
    amplitude: dict[str, float] = {}
    for row in sweep_rows:
        amplitude[row[0]] = max(amplitude.get(row[0], 0.0), float(row[4]))
    ordered = sorted(amplitude.items(), key=lambda item: -item[1])
    wide = [name for name, value in ordered if value >= 0.2]
    narrow = [name for name, value in ordered if value < 0.2]
    facts = []
    if wide and narrow:
        facts.append(
            f"Amplituda kalon 0.2 vetëm te {_joined(wide)}; te {_joined(narrow)} asnjë "
            f"prag nuk e lëviz MCC-në më shumë se {max(amplitude[n] for n in narrow):.3f}."
        )

    def at(smell: str, threshold: str, factor: float) -> dict:
        return next(
            point for point in sweep["per_smell"][smell][threshold] if point["factor"] == factor
        )

    def best(smell: str, threshold: str) -> dict:
        return max(sweep["per_smell"][smell][threshold], key=lambda point: point["mcc"])

    moved = []
    for smell, threshold in (("long method", "long_method_loc"), ("feature envy", "feature_envy_fdp")):
        if threshold not in sweep["per_smell"].get(smell, {}):
            continue
        published, top = at(smell, threshold, 1.0), best(smell, threshold)
        if top["factor"] == 1.0:
            continue
        moved.append(
            f"{threshold} = {top['value']:g} në vend të {published['value']:g} te "
            f"{SMELL_SQ[smell]} (MCC {top['mcc']:.3f}; recall {published['recall']:.3f} → "
            f"{top['recall']:.3f}, precizion {published['precision']:.3f} → "
            f"{top['precision']:.3f})"
        )
    if moved:
        facts.append(f"Vlera me MCC-në më të lartë është {_joined(moved)}.")
    return facts


def _calibration_facts(data: dict) -> list:
    """Sa pajtohen foldet dhe nga shkon precizioni, për secilën erë.

    Teksti i mëparshëm thoshte për Data Class-in se «dy» folde zgjodhën një prag
    tjetër nga «tre» të tjerët; skedari tregon një kundrejt katër. Fjalia tani
    ndërtohet nga numrat e zgjedhjeve, që të mos ndahet më prej tyre.
    """
    unanimous, same_knob, split = [], [], []
    for smell in sorted(data["per_smell"]):
        chosen = data["per_smell"][smell]["chosen"]
        values = sum(len(counts) for counts in chosen.values())
        if values == 1:
            unanimous.append(SMELL_SQ[smell])
        elif len(chosen) == 1:
            same_knob.append(SMELL_SQ[smell])
        else:
            parts = []
            for name, counts in sorted(chosen.items(), key=lambda item: -sum(item[1].values())):
                count = sum(counts.values())
                moved = "fold lëvizi" if count == 1 else "folde lëvizën"
                parts.append(f"{_word(count)} {moved} {name}")
            split.append(f"te {SMELL_SQ[smell]} {' dhe '.join(parts)}")
    clauses = []
    if unanimous:
        clauses.append(f"Të gjitha foldet zgjodhën të njëjtën vlerë vetëm te {_joined(unanimous)}")
    if same_knob:
        clauses.append(f"te {_joined(same_knob)} ranë dakord për pragun, por jo për vlerën")
    clauses.extend(split)
    facts = ["; ".join(clauses) + "."] if clauses else []

    def moved_up(key: str) -> list[str]:
        return [
            SMELL_SQ[smell]
            for smell, entry in sorted(data["per_smell"].items())
            if entry["calibrated"][key] > entry["published"][key]
        ]

    total = len(data["per_smell"])
    recall_up, precision_up, mcc_up = moved_up("recall"), moved_up("precision"), moved_up("mcc")
    facts.append(
        f"Recall-i u rrit {_among(len(recall_up), total)}, precizioni vetëm te "
        f"{_joined(precision_up) or 'asnjëra'}, dhe MCC-ja {_among(len(mcc_up), total)}."
    )
    return facts


def _combined_paragraphs(ml: dict) -> list:
    """A ndihmon bashkimi i dy qasjeve? Pyetja që kapitulli e ngriti vetë.

    Deri tani ajo mbetej vërejtje: rregulli kap disa raste që modeli i humb, pra
    bashkimi «do të kishte kuptim». Kjo e mat, në të dy drejtimet.
    """
    smells = sorted(ml["per_smell"])
    if not all("combined" in ml["per_smell"][s] for s in smells):
        return []

    rows = []
    for smell in smells:
        entry = ml["per_smell"][smell]
        best = entry["models"][entry["best_model"]]
        union = entry["combined"]["union"]
        crossing = entry["combined"]["intersection"]
        rows.append([
            SMELL_SQ[smell],
            f"{best['mcc']:.3f}",
            f"{union['mcc']:.3f}" if union["mcc"] is not None else "—",
            f"{crossing['mcc']:.3f}" if crossing["mcc"] is not None else "—",
            f"{union['recall']:.3f}",
            f"{crossing['precision']:.3f}" if crossing["precision"] is not None else "—",
        ])

    return [
        "Dy qasjet u kombinuan edhe drejtpërdrejt, si bashkim (A∪B) dhe si prerje "
        "(A∩B), me këto vlera:",
        ("table", "Të dyja qasjet së bashku",
         ["Erë", "B: modeli", "A∪B", "A∩B", "A∪B: recall", "A∩B: precizion"], rows),
        _union_against_model(ml, smells),
        _intersection_against_model(ml, smells),
    ]


def _union_against_model(ml: dict, smells: list) -> str:
    """Ku e ngre dhe ku e ul bashkimi MCC-në e modelit, nga të dhënat.

    Fjalia e mëparshme e shkruante me dorë se ku bie; tani lexohet.
    """
    up, down, raised = [], [], 0
    for smell in smells:
        entry = ml["per_smell"][smell]
        best = entry["models"][entry["best_model"]]
        union = entry["combined"]["union"]
        raised += union["recall"] > best["recall"]
        if union["mcc"] is None:
            continue
        change = f"{SMELL_SQ[smell]} ({best['mcc']:.3f} → {union['mcc']:.3f})"
        (up if union["mcc"] > best["mcc"] else down).append(change)
    text = f"Bashkimi e ngre recall-in mbi atë të modelit {_among(raised, len(smells))}"
    if up:
        text += f"; MCC-ja rritet te {_joined(up)}"
    if down:
        text += f", dhe bie te {_joined(down)}"
    return text + "."


def _intersection_against_model(ml: dict, smells: list) -> str:
    """Çfarë jep prerja kundrejt modelit, nga të dhënat."""
    lower = 0
    for smell in smells:
        entry = ml["per_smell"][smell]
        best = entry["models"][entry["best_model"]]
        crossing = entry["combined"]["intersection"]
        lower += crossing["recall"] < best["recall"] and (crossing["mcc"] or 0.0) < best["mcc"]
    top = max(smells, key=lambda s: ml["per_smell"][s]["combined"]["intersection"]["precision"])
    return (
        f"Te prerja, precizioni është të paktën {_intersection_floor(ml)} te çdo erë dhe "
        f"arrin {_intersection_best(ml)} te {SMELL_SQ[top]}, ndërsa recall-i dhe MCC-ja "
        f"janë nën ato të modelit {_among(lower, len(smells))}."
    )


CLAUSE_SQ = {
    "WMC": "WMC, kompleksiteti i peshuar",
    "TCC": "TCC, kohezioni",
    "ATFD": "ATFD, qasja në të dhëna të huaja",
    "LAA": "LAA, qasja te të vetat",
    "FDP": "FDP, sa klasa të huaja",
}


def _near_or_far(entry: dict, first: bool = True) -> str:
    """Sa larg janë të humburat, thënë me dy fakte e jo me një verdikt.

    Dy gjëra të ndryshme quhen «afër»: sa klauzola dështuan, dhe sa larg ishte
    secila. Ato nuk lëvizin bashkë — një erë mund t'i dështojë dy klauzola dhe
    prapë t'i ketë të dyja pranë — ndaj shkruhen të dyja. Një fjali e vetme që i
    përzien do të thoshte «nuk janë afër» për një rast ku gjysma janë.

    Shpjegimi i asaj që do të thotë shifra jepet vetëm herën e parë. I përsëritur
    për çdo erë, ai bëhej e njëjta fjali dy herë me radhë, me numra të tjerë
    (VD-128); më pas mjafton numri.
    """
    missed = int(str(entry["missed"]))
    alone = int(str(entry["blocked_by_one_clause"]))
    many = missed - alone
    distances = [float(v) for v in dict(entry["median_shortfall"]).values()]

    if many > alone:
        shape = (
            f"{many} nga {missed} i dështojnë dy ose tri klauzola njëkohësisht"
            if first
            else f"{many} nga {missed} ngecin te më shumë se një klauzolë"
        ) + (
            ", pra shumica nuk janë raste që një prag pak më i butë do t'i kapte: janë "
            "entitete që, të matura me këto metrika, nuk i ngjajnë erës nga disa anë "
            "njëherësh."
            if first
            else "; edhe këtu, shumica janë larg erës dhe jo pranë pragut."
        )
    else:
        shape = f"{alone} nga {missed} bllokohen nga një klauzolë e vetme" + (
            ", pra shumica janë raste kufitare ku mungesa është distancë e jo natyrë."
            if first
            else ", pra këtu mbizotërojnë rastet kufitare."
        )

    if not distances:
        return shape
    return (
        shape
        + (
            " Aty ku bllokuesi është një i vetëm, medianat e afrisë shkojnë nga "
            if first
            else " Me një bllokues të vetëm, rastet ndalen (në mesore) te "
        )
        + (
            f"{min(distances):.2f} te {max(distances):.2f} e pragut."
            if first
            else f"{min(distances):.2f}–{max(distances):.2f} e pragut."
        )
    )

def _folds_disagree() -> str:
    """Sa erëra kanë të paktën një prag ku foldet nuk zgjodhën të njëjtën vlerë.

    Numëruar e jo e shtypur: është pohimi që mban gjithë arsyen pse pragjet e
    kalibruara nuk adoptohen, dhe një numër i shtypur me dorë do të rrëshqiste
    heshtazi po të ndryshonte kalibrimi (VD-73).
    """
    data = _load_if_present("threshold_calibration.json")
    if data is None:
        return "foldet nuk pajtohen për të njëjtën vlerë te disa prej erërave"

    total = len(data["per_smell"])
    split = sum(
        1
        for entry in data["per_smell"].values()
        if any(len(votes) > 1 for votes in entry["chosen"].values())
    )
    if not split:
        return "foldet zgjedhin të njëjtën vlerë te secila erë"
    if split == total:
        return f"foldet nuk pajtohen për të njëjtën vlerë te asnjëra nga {total} erërat"
    return f"foldet nuk pajtohen për të njëjtën vlerë {_among(split, total)}"


def _blocking_predicts_calibration() -> list:
    """A e parashikon llogaria e klauzolave se ku do të ndihmojë kalibrimi?

    Dy matje të pavarura: njëra thotë sa larg janë mospërputhjet nga pragjet,
    tjetra sa fiton kalibrimi jashtë-fold-it. Nëse e para shpjegon të dytën, ajo
    është shpjegim që bën parashikim, e jo përshkrim i mëpasshëm. Ndërtohet nga të
    dy skedarët që të mos pohohet pajtim aty ku nuk ka.
    """
    blocking = _load_if_present("blocking_conditions.json")
    calibration = _load_if_present("threshold_calibration.json")
    if blocking is None or calibration is None:
        return []

    lines = []
    for smell, entry in blocking["by_smell"].items():
        tuned = calibration["per_smell"].get(smell)
        if tuned is None:
            continue
        gain = float(tuned["calibrated"]["mcc"]) - float(tuned["published"]["mcc"])
        distances = [float(v) for v in dict(entry["median_shortfall"]).values()]
        if not distances:
            continue
        lines.append((smell, sum(distances) / len(distances), gain))
    if len(lines) < 2:
        return []

    lines.sort(key=lambda item: item[1])
    near = lines[-1]
    far = lines[0]
    return [
        "Kjo llogari bën një parashikim që një matje tjetër e provon në mënyrë të "
        f"pavarur. Te {SMELL_SQ.get(far[0], far[0])}-i mospërputhjet janë larg pragjeve "
        f"(mediana mesatare {far[1]:.2f}), ndaj kalibrimi nuk duhet të ndihmojë shumë; "
        f"te {SMELL_SQ.get(near[0], near[0])} janë afër ({near[1]:.2f}), ndaj duhet. "
        f"Kalibrimi jashtë-fold-it i Nënkapitullit 5.5, i matur veç dhe pa e parë këtë "
        f"analizë, jep {far[2]:+.3f} MCC për të parin dhe {near[2]:+.3f} për të dytin. "
        "Dy erëra nuk provojnë një rregull, por drejtimi është ai që llogaria e "
        "klauzolave e priste, dhe kjo e bën atë shpjegim me vlerë parashikuese e jo "
        "përshkrim të mëpasshëm.",
    ]


def _blocking_section() -> list:
    """Pse nuk ndezin strategjitë, klauzolë për klauzolë.

    Nënkapitulli 5.1 raporton se sa gjejnë detektorët. Ky raporton pse nuk gjejnë
    pjesën tjetër, çka është pyetja që një lexues bën menjëherë pas së parës dhe
    që asnjë normë e vetme nuk e përgjigjet.
    """
    data = _load_if_present("blocking_conditions.json")
    if data is None:
        return []

    rows = []
    for smell, entry in data["by_smell"].items():
        for metric, count in entry["sole_blocker"].items():
            rows.append(
                [
                    SMELL_SQ.get(smell, smell),
                    CLAUSE_SQ.get(metric, metric),
                    str(count),
                    f"{entry['median_shortfall'][metric]:.2f}",
                ]
            )

    spread = []
    for smell, entry in data["by_smell"].items():
        counts = ", ".join(
            f"{n} me {k} klauzolë" if k == "1" else f"{n} me {k} klauzola"
            for k, n in sorted(entry["clauses_failing"].items())
        )
        spread.append([SMELL_SQ.get(smell, smell), str(entry["missed"]), counts])

    paragraphs: list = [
        "Një strategji e Lanza & Marinescu-t është konjunksion, ndaj çdo mospërputhje "
        "ka shkak të emërtueshëm: një klauzolë, ose dy, ose të tria nuk qëndruan. "
        "Matjet për ta thënë këtë ekzistojnë tashmë te tabela e veçorive, ndaj pyetja "
        "«pse nuk ndezi» ka përgjigje pa asnjë ekzekutim të ri.",
        ("table", "Sa klauzola dështuan te secila mospërputhje",
         ["Erë", "Të humbura", "Shpërndarja"], spread),  # fmt: skip
        ("table", "Kur një klauzolë e vetme e ndal strategjinë",
         ["Erë", "Klauzola", "Rastet", "Mediana e afrisë"], rows),  # fmt: skip
        "Kolona e fundit është distanca nga pragu si raport: 1.00 do të thoshte "
        "saktësisht mbi prag, 0.50 gjysma e rrugës. Të dy drejtimet lexohen njësoj, "
        "sepse një klauzolë që kërkon vlerë të madhe matet si e matura mbi pragun dhe "
        "një që kërkon vlerë të vogël si pragu mbi të maturën.",
    ]
    described = False
    for smell, entry in data["by_smell"].items():
        paragraphs.append(
            f"**{SMELL_SQ.get(smell, smell)}.** " + _near_or_far(entry, first=not described)
        )
        described = True

    paragraphs.extend(_blocking_predicts_calibration())
    paragraphs.append(
        "Analiza kufizohet te dy strategjitë që janë konjunksione të pastra: Long "
        "Method-i ka një klauzolë të vetme, ndërsa Data Class-i përzien konjunksion me "
        "disjunksion, ku «klauzola bllokuese» nuk përcaktohet pa një vendim arbitrar."
    )
    return [("5.7", "Pse nuk ndezin strategjitë", paragraphs)]


def _blob_size_rows(data: dict) -> list:
    """Kuartilet e madhësisë për secilën qelizë, variant pas varianti."""
    rows = []
    for variant, entry in data["per_variant"].items():
        for metric in ("CLOC", "NOM", "WMC"):
            cells = entry["quartiles"][metric]
            rows.append(
                [
                    SMELL_VARIANT_SQ.get(f"blob/{variant}", variant),
                    metric,
                    *(
                        "–".join(f"{value:g}" for value in cells[cell])
                        for cell in ("caught", "missed", "negative")
                    ),
                ]
            )
    return rows


def _blob_quartile_gap(data: dict) -> str:
    """A rrinë tri të katërtat e mospërputhjeve nën çerekun më të vogël të kapjeve?

    Pohimi shkruhet nga vetë kuartilet e jo me dorë, sepse është pohimi më i
    fortë i nënkapitullit dhe një ndryshim i vogël te tabela e veçorive do ta
    kthente në të pavërtetë pa e ndryshuar asnjë fjalë të tekstit.
    """
    gaps = [
        entry["quartiles"][metric]["missed"][2] < entry["quartiles"][metric]["caught"][0]
        for entry in data["per_variant"].values()
        for metric in ("CLOC", "NOM", "WMC")
    ]
    if all(gaps):
        return (
            "Shtrirjet madje nuk mbivendosen fare te kuartilet: tre të katërtat e "
            "mospërputhjeve rrinë nën çerekun më të vogël të klasave të kapura, te "
            "secila prej tri metrikave dhe te të dy variantet."
        )
    return (
        f"Te {sum(gaps)} nga {len(gaps)} palët metrikë–variant, tre të katërtat e "
        "mospërputhjeve rrinë nën çerekun më të vogël të klasave të kapura."
    )


def _blob_aggregation_flattens(data: dict) -> str:
    """Sa e rrafshon mesatarja shkallën e ashpërsisë, lexuar nga vetë mbështetjet.

    Ishte shkruar si ilustrim me gjashtë rishikues, çka është numri i pozitivëve
    tipikë e jo i mostrave: mediana e rishikimeve për Blob-in është dy. Mekanizmi
    qëndron, ilustrimi jo, ndaj tani e thotë vetë matja.
    """
    by_how = data["per_variant"]["strategy"]["recall_by_severity"]
    counts = {
        how: {label: int(entry[label]["support"]) for label in entry}
        for how, entry in by_how.items()
    }
    shape = lambda how: ", ".join(  # noqa: E731
        f"{label} {counts[how].get(label, 0)}" for label in SEVERITY_SCALE
    )
    return (
        "Shumica e mostrave mbajnë vetëm dy rishikime, dhe një votë «asnjë» përballë "
        "një vote të rëndë e ul mesataren për një shkallë të tërë. Nën mesatare "
        f"pozitivët ndahen {shape('mean')}, ndërsa nën MAX {shape('max')}: mesatarja e "
        "zbraz skajin e rëndë të shkallës, ndaj gradienti nuk shihet nën të."
    )


def _blob_agrees_with_the_model() -> list:
    """A i zgjedh Qasja B po ato metrika që kjo analizë i gjen më ndarëset?

    Dy matje të pavarura mbi të njëjtën tabelë veçorish: njëra rendit metrikat
    sipas sa mirë e ndajnë një mospërputhje nga një klasë e pastër, tjetra sipas
    sa peshë u dha një model i trajnuar. Nuk janë e njëjta llogari, ndaj
    përputhja e tyre është provë dhe jo përsëritje.
    """
    recall = _load_if_present("blob_recall.json")
    ml = _load_if_present("ml_evaluation.json")
    if recall is None or ml is None:
        return []
    top = ml["per_smell"].get("blob", {}).get("top_features")
    if not top:
        return []

    separation = recall["per_variant"]["strategy"]["separation"]
    ranked = [name for name, _ in sorted(separation.items(), key=lambda pair: -pair[1])][:4]
    chosen = [name.removeprefix("c_") for name in top[:4]]
    shared = [name for name in ranked if name in chosen]
    if len(shared) < 2:
        return []
    return [
        "Kjo renditje përputhet me një matje të pavarur: veçoritë që modeli i Qasjes B "
        f"zgjodhi për Blob-in (Figura e Nënkapitullit 5.2) ndajnë {_word(len(shared))} "
        "nga katër vendet e "
        f"para me të: {', '.join(shared)}. As TCC-ja dhe as WMC-ja, kushtet e "
        "strategjisë së botuar, nuk hyjnë te asnjëra listë.",
    ]


def _blob_severity_rows(data: dict) -> list:
    """Recall-i sipas ashpërsisë nën agregimin MAX, ku shkalla ruan shtrirjen."""
    rows = []
    for variant, entry in data["per_variant"].items():
        by_max = entry["recall_by_severity"]["max"]
        for label in SEVERITY_SCALE:
            bucket = by_max.get(label)
            if bucket is None:
                continue
            rows.append(
                [
                    SMELL_VARIANT_SQ.get(f"blob/{variant}", variant),
                    label,
                    str(bucket["support"]),
                    str(bucket["caught"]),
                    f"{bucket['recall']:.3f}" if bucket["recall"] is not None else "—",
                ]
            )
    return rows


def _blob_gradient(data: dict) -> str:
    """Sa herë më i lartë është recall-i te skaji i rëndë sesa te i lehti."""
    by_max = data["per_variant"]["strategy"]["recall_by_severity"]["max"]
    worst = by_max.get("critical", {}).get("recall")
    lightest = by_max.get("minor", {}).get("recall")
    if not worst or not lightest:
        return ""
    return (
        f"Te strategjia e botuar recall-i ngjitet nga {lightest:.3f} te rastet që vetëm "
        f"një rishikues i quajti të lehta, në {worst:.3f} te ato që dikush i quajti "
        f"kritike, pra rreth {worst / lightest:.0f} herë më i lartë. Mospërputhja nuk "
        "është e rastësishme: strategjia nuk pajton me rishikuesit pikërisht atje ku "
        "rishikuesit vetë ishin më pak të bindur."
    )


def _blob_saturated(data: dict) -> list:
    """Mospërputhjet që klauzola e kohezionit nuk i pranon dot me asnjë prag."""
    entry = data["saturated_cohesion"]
    if not entry["count"]:
        return []
    support = data["per_variant"]["strategy"]["support"]
    missed, caught = support["missed"], support["caught"]

    rows = [
        [
            item["class_name"],
            f"{item['CLOC']:g}",
            f"{item['NOM']:g}",
            f"{item['WMC']:g}",
            "—" if item["public_instance_methods"] is None else str(item["public_instance_methods"]),
        ]
        for item in entry["largest"]
    ]
    return [
        "Një pjesë e vogël e mospërputhjeve i detyrohet matjes e jo etiketave. TCC-ja "
        "e Bieman & Kang-ut (1995) mat pjesën e çifteve të metodave publike të "
        "instancës që ndajnë një fushë. Një klasë me më pak se dy metoda të tilla nuk "
        "ka çift, ndaj llogaritësi i jep vlerën 1.0; dhe çdo klauzolë e God Class-it e "
        "kërkon TCC-në **nën** një prag, pra kjo klasë nuk kapet me asnjë prag.",
        ("table", "Klasat që klauzola e kohezionit nuk i arrin dot",
         ["Klasa", "CLOC", "NOM", "WMC", "Metoda publike instance"], rows),  # fmt: skip
        f"Janë {entry['count']} mospërputhje të tilla, që e kalojnë klauzolën e "
        f"kompleksitetit dhe ndalen vetëm te kohezioni; {entry['checked']} u riparsuan "
        f"dhe {entry['confirmed_undefined']} dolën me TCC të papërcaktuar. Emrat "
        "tregojnë klasa ndihmëse krejt statike, ku kolona e fundit është zero.",
        f"Numri është i vogël, {entry['count']} nga {missed}, ndaj nuk e shpjegon "
        "recall-in e ulët. Ndryshimi i TCC-së do ta shkëpuste përkufizimin nga burimi, "
        f"për një fitim jo më të madh se {entry['count'] / (missed + caught):.3f} te "
        "recall-i (Nënkapitulli 6.6).",
    ]


def _blob_recall_section() -> list:
    """Si duket klasa që rishikuesi e quan blob kur strategjia nuk pajtohet.

    Shtojca 8.6 thotë cila klauzolë e ndali secilën mospërputhje dhe aty
    ndalet. Numri i klauzolave nuk dallon dot mes dy gjendjeve që kërkojnë punë
    të kundërt: strategjia që mat përmasat e gabuara, dhe e vërteta bazë që
    përmban raste të cilat asnjë prag nuk i arrin. Ky nënkapitull e dallon.
    """
    data = _load_if_present("blob_recall.json")
    if data is None:
        return []

    strategy = data["per_variant"]["strategy"]
    missed = strategy["support"]["missed"]
    below = strategy["below_negative_median"]["CLOC"]
    best_metric, best_value = max(strategy["separation"].items(), key=lambda pair: pair[1])

    paragraphs: list = [
        "Shtojca 8.6 numëron klauzolat që ndalën secilën mospërputhje, por nuk thotë si "
        "duket klasa që rishikuesi e quajti blob ndërsa strategjia jo. Ose klasat e "
        "humbura u ngjajnë atyre të kapura në një përmasë që strategjia nuk e lexon, dhe "
        "asaj i mungon një klauzolë; ose u ngjajnë klasave të pastra në çdo përmasë të "
        "matur, dhe atëherë asnjë prag nuk i arrin.",
        ("table", "Madhësia e klasave në secilën qelizë, si kuartil i poshtëm–mesatare–i sipërm",
         ["Varianti", "Metrika", "Të kapura", "Të humbura", "Të pastra"],
         _blob_size_rows(data)),  # fmt: skip
        "Tabela lexohet vetëm në një drejtim. Klasa mesatare e humbur është shumë më "
        "afër një klase që rishikuesit e pastruan sesa një blob-i që strategjia e kapi. "
        f"{_blob_quartile_gap(data)} "
        f"Nga {missed} mospërputhje të strategjisë së botuar, {below} nuk "
        "janë më të mëdha se klasa mesatare që vetë rishikuesit e quajtën të pastër.",
        "Asnjë metrikë e vetme nuk e mban dot ndarjen. Për secilën metrikë klase u mat "
        "statistika e Mann-Whitney-t, e lexuar si sipërfaqe nën kurbën ROC: 0.50 do të "
        "thotë asnjë informacion, 1.00 renditje e përsosur. Më e mira nga "
        f"{len(strategy['separation'])} metrikat është {best_metric} me {best_value:.3f}, "
        "pra përmasa që mungon nuk gjendet mes atyre që ky sistem di të masë.",
        *_blob_agrees_with_the_model(),
        ("table", "Recall-i sipas ashpërsisë që caktuan rishikuesit, agregim MAX",
         ["Varianti", "Ashpërsia", "Mbështetja", "Të kapura", "Recall"],
         _blob_severity_rows(data)),  # fmt: skip
        "Agregimi këtu është qëllimisht MAX e jo mesatarja e përdorur gjetiu. "
        f"{_blob_aggregation_flattens(data)}",
    ]
    gradient = _blob_gradient(data)
    if gradient:
        paragraphs.append(gradient)
    paragraphs.extend(_blob_saturated(data))
    paragraphs.append(
        "Përfundimi është për të vërtetën bazë, jo për detektorin. Ai nuk thotë se "
        "rishikuesit gabuan, por që recall-i kundrejt MLCQ-së mat sa shpesh një "
        "strategji e madhësisë dhe e kohezionit përputhet me një gjykim njerëzor që "
        "shpesh nuk mbështetet te madhësia."
    )
    return [("5.10", "Çfarë mbetet pa u kapur te Blob-i", paragraphs)]


def _severity_section() -> list:
    """Sa pajtohet ashpërsia që deriva sistemi me atë që caktuan rishikuesit.

    Shkalla e MLCQ-së u zgjodh pikërisht që ky krahasim të bëhej pa hap përkthimi.
    Numrat këtu e bëjnë atë krahasim për herë të parë, dhe dalin negativë.
    """
    rules = _load("rules_evaluation.json")
    sweep = _load("threshold_sweep.json")
    rank = {name: i for i, name in enumerate(SEVERITY_SCALE)}

    rows = []
    stricter = lenient = compared = 0
    for smell in sorted(rules["per_smell"]):
        for variant, data in rules["per_smell"][smell].items():
            agreement = data["severity_agreement"]
            if not agreement["n"]:
                continue
            label = SMELL_SQ[smell] + ("" if variant == "strategy" else " (+ madhësi)")
            rows.append([
                label,
                f"{agreement['exact']:.3f}",
                f"{agreement['within_one']:.3f}",
                "—" if agreement["kappa_quadratic"] is None else f"{agreement['kappa_quadratic']:.3f}",
                str(agreement["n"]),
            ])
            if variant != "strategy":
                continue
            for actual, predictions in agreement["matrix"].items():
                for predicted, count in predictions.items():
                    compared += count
                    if rank[predicted] > rank[actual]:
                        stricter += count
                    elif rank[predicted] < rank[actual]:
                        lenient += count

    # Sa larg e çon fshirja e pragjeve të ashpërsisë kappa-n, mbi të gjitha erërat.
    best = 0.0
    for per_threshold in sweep.get("severity", {}).values():
        for points in per_threshold.values():
            for point in points:
                if point["kappa_quadratic"] is not None:
                    best = max(best, point["kappa_quadratic"])

    return [
        (
            "5.8",
            "Ashpërsia e derivuar kundrejt gjykimit të rishikuesve",
            [
                "Ashpërsia e sistemit nuk caktohet, por derivohet: ajo është mesatarja e "
                "tepricës mbi pragje, e shprehur në të njëjtën shkallë që përdorën "
                "rishikuesit e MLCQ-së. Ajo zgjedhje u bë që të dyja anët të krahasoheshin "
                "pa hap përkthimi. Ky nënkapitull e bën atë krahasim.",
                "Matja kufizohet te mostrat ku të dyja anët shohin një erë. Askund tjetër "
                "shkallët nuk janë të krahasueshme: një detektor që nuk ndez nuk cakton "
                "ashpërsi, dhe një pozitiv i rremë është pyetje precizioni, jo ashpërsie.",
                ("table", "Pajtimi i ashpërsisë me rishikuesit",
                 ["Erë", "Përputhje e saktë", "Brenda një niveli", "κ me peshë", "n"], rows),
                f"Rezultati është negativ dhe duhet lexuar si i tillë. Për tri nga katër "
                f"erërat kappa qëndron pranë zeros, pra pajtimi nuk është më i mirë se "
                f"rastësia. Vetëm Long Method arrin një pajtim të matshëm, dhe edhe atje "
                f"vetëm i moderuar.",
                f"Matrica tregon edhe drejtimin e gabimit, i cili është i njëanshëm: nga "
                f"{compared} krahasime, {stricter} e vlerësojnë rastin më rëndë se "
                f"rishikuesit dhe vetëm {lenient} më lehtë "
                f"({stricter / compared:.0%} kundrejt {lenient / compared:.0%}). Sistemi "
                f"nuk gabon rastësisht: ai e mbivlerëson ashpërsinë.",
                ("figure", str(FIGURES / "ashpersia_kundrejt_rishikuesve.png"),
                 "Ashpërsia e derivuar kundrejt asaj që caktuan rishikuesit"),
                "Shpjegimi qëndron te ndërtimi i pikës. Për Long Method teprica matet mbi "
                "një metrikë të vetme; për strategjitë me disa kushte pika është mesatare e "
                "tepricave mbi metrika heterogjene, dhe asgjë nuk garanton se ajo përkon me "
                "atë që një zhvillues e quan problem të rëndë.",
                "Nuk është çështje kalibrimi: fshirja e pragjeve të ashpërsisë e ngre "
                f"kappa-n më së shumti deri në {best:.3f}, pra pajtimi mbetet i dobët.",
                "Ashpërsia e derivuar mbetet renditje brenda mjetit — cili rast të shihet "
                "i pari — dhe jo riprodhim i gjykimit të zhvilluesit. Ajo hyn në rezultatet "
                "e punimit vetëm përmes ndarjes së recall-it sipas ashpërsisë së "
                "rishikuesve.",
            ],
        ),
    ]


def _refactoring_section() -> list:
    """Tabela N/M/K, ose një shënim i ndershëm nëse ekzekutimi s'ka mbaruar."""
    data = _load_if_present("refactoring_evaluation.json")
    if data is None:
        return [
            "[PLOTËSO: ekzekutimi mbi korpusin e plotë është ende në vazhdim; kjo "
            "tabelë gjenerohet automatikisht sapo të përfundojë.]"
        ]

    detected = data["detected"]
    applied = data["applied"]
    rows = [
        ["Vende të detektuara", _count(detected), "100%"],
        ["Të transformuara", _count(applied), f"{applied / detected:.1%}"],
        ["Të refuzuara", _count(data["refused"]), f"{data['refused'] / detected:.1%}"],
    ]
    if data.get("unlocatable"):
        rows.append(
            ["Të palokalizueshme", _count(data["unlocatable"]),
             f"{data['unlocatable'] / detected:.1%}"]
        )  # fmt: skip

    refusals = [
        [reason.replace("_", " "), _count(count), f"{count / detected:.1%}"]
        for reason, count in sorted(data["refused_by_reason"].items(), key=lambda p: -p[1])
    ]

    verdicts = [
        [VERDICT_SQ.get(verdict, verdict.replace("_", " ")), _count(count),
         f"{count / applied:.1%}"]
        for verdict, count in sorted(data["verdicts"].items(), key=lambda p: -p[1])
    ]

    broken = data["verdicts"].get("new_errors", 0) + data["verdicts"].get("broken_syntax", 0)
    share = broken / applied if applied else 0.0

    return [
        f"Mbi {_count(data['files'])} skedarë të korpusit u detektuan {_count(detected)} "
        f"vende ku motori ka një transformim; prej tyre {_count(applied)} u transformuan.",
        ("table", "Rezultati i motorit të refaktorimit",
         ["", "Numri", "Pjesa"], rows),
        _applied_by_refactoring(data),
        "Refuzimet ndahen sipas arsyes, kuptimi i së cilës jepet te Shtojca 8.4, dhe "
        "rishkrimet e aplikuara sipas verdiktit të verifikimit.",
        ("table", "Pse u refuzuan",
         ["Arsyeja", "Numri", "Pjesa e vendeve"], refusals),
        ("table", "Verifikimi i atyre që u aplikuan",
         ["Verdikti", "Numri", "Pjesa e të aplikuarave"], verdicts),
        f"Nga {_count(applied)} rishkrime, {broken} futën një gabim që nuk ishte aty më parë "
        f"({share:.2%})."
        + _unanswered(data)
        + " Pjesa tjetër ose kompiloi, ose nuk shtoi asnjë lloj të ri gabimi kundrejt "
        "skedarit origjinal.",
        *_resolution_paragraphs(data),
        *_project_context_paragraphs(),
        *_rewrite_quality_paragraphs(),
        *_refusal_severity_paragraphs(),
    ]


def _unanswered(data: dict) -> str:
    """Rishkrimet për të cilat javac-u nuk dha verdikt, kur ka të tilla.

    Fjalia para kësaj i ndan rishkrimet në «futën gabim» dhe «pjesa tjetër», çka
    e mbulon korpusin vetëm kur javac-u përgjigjet për të gjithë. Ai nuk
    përgjigjet gjithmonë: skadon koha, ose dështon pa emërtuar një gabim mbi
    burimin, dhe atëherë verdikti është vetëm «u parsua» (VD-138). Ato nuk janë
    as sukses, as dështim, dhe nuk fshihen brenda «pjesës tjetër».
    """
    count = data["verdicts"].get("parses", 0)
    if not count:
        return ""
    return (
        f" Te {_rewrites(count)} javac-u nuk dha verdikt, ndaj për ato dihet vetëm se "
        "rishkrimi është Java e vlefshme."
    )


def _applied_by_refactoring(data: dict) -> str:
    """Sa rishkrime i takojnë secilit transformim.

    Metodologjia e shkruante «ExtractMethod përbën 93%» si arsye të shtresimit;
    numri është rezultat dhe raportohet këtu (VD-125).
    """
    per = data.get("applied_by_refactoring")
    if not per:
        return ""
    applied = data["applied"]
    parts = [
        f"{_named(name)} {_count(count)} ({count / applied:.1%})"
        for name, count in sorted(per.items(), key=lambda pair: -pair[1])
    ]
    return "Sipas transformimit, rishkrimet ndahen: " + ", ".join(parts) + "."


def _rewrites(count: int) -> str:
    """«një rishkrim» ose «N rishkrime».

    Numri hyn në fjali të ndryshme dhe shqipja e dallon njëjësin nga shumësi te
    emri dhe te folja. Një fjali e ndërtuar që del «1 rishkrime u refuzuan» do të
    rishkruhej me dorë, dhe atëherë numri s'do të lexohej më nga të dhënat.
    """
    return "një rishkrim" if count == 1 else f"{count} rishkrime"


def _opens(text: str) -> str:
    """E njëjta frazë kur nis fjalinë: shkronja e parë e madhe, pjesa tjetër e paprekur."""
    return text[:1].upper() + text[1:]


def _quality_shortfall(idle: int, reviewed: int) -> str:
    """Sa nga rishkrimet e lexuara nuk sjellin përfitim, dhe si quhet kjo.

    Degëzohet sepse zero dhe jo-zero janë pohime të kundërta: e para thotë se
    çdo rishkrim i lexuar përmirësoi strukturën, e dyta se një pjesë e tyre vetëm
    lëvizi bajta. Fjalia e shkruar për njërën lexohet si mohim i tjetrës.
    """
    if not idle:
        return "Asnjë rishkrim i lexuar nuk u gjykua pa përfitim strukturor."
    verb = "u gjykua" if idle == 1 else "u gjykuan"
    return f"{_opens(_rewrites(idle))} nga {reviewed} {verb} pa përfitim strukturor."


def _verdict_separates(table: dict[str, dict[str, int]]) -> str:
    """A e ndan verdikti i kompilatorit të pranuarën nga e refuzuara?

    Kjo është pyetja për të cilën fleta u mbajt e verbër. Përgjigjja lexohet nga
    tabela e kryqëzuar e jo nga pritshmëria: nëse refuzimet shpërndahen njësoj
    mes verdikteve, verdikti nuk parashikon asgjë për pranimin.
    """
    rejected = sum(
        row["reject"] for verdict, row in table.items() if verdict in {"compiles", "no_new_errors"}
    )
    if not rejected:
        return (
            "Asnjë rishkrim që kaloi kontrollin e kompilatorit nuk u refuzua nga "
            "rishikuesi."
        )
    verb = "u refuzua" if rejected == 1 else "u refuzuan"
    return (
        f"{_opens(_rewrites(rejected))} që kaloi kontrollin e kompilatorit {verb} nga "
        "rishikuesi."
    )


def _rewrite_quality_paragraphs() -> list:
    """Cilësia e rishkrimeve sipas rishikuesit, ose një shënim se fleta pret.

    Vetëplotësohet: derisa fleta të mbushet me dorë, skedari nuk ekziston dhe
    seksioni e thotë këtë hapur në vend që të mos ekzistojë fare. `check_format`
    e numëron atë shënim mes vendeve që i mbeten autorit, që puna e papërfunduar
    të jetë e dukshme te lista e tij e vet.
    """
    data = _load_if_present("rewrite_quality.json")
    if data is None:
        return [
            "[PLOTËSO: fleta e vlerësimit të cilësisë është nxjerrë me hapin 16 të "
            "Shtojcës 8.5 dhe pret gjykimin e rishikuesit; kjo tabelë gjenerohet "
            "automatikisht sapo ajo të mbushet dhe të pikëzohet me hapin 17.]"
        ]

    per = data["by_refactoring"]
    rows = [
        [
            name,
            str(entry["reviewed"]),
            str(entry["acceptance"]["as_is"]),
            str(entry["acceptance"]["after_edit"]),
            str(entry["acceptance"]["reject"]),
            f"{entry['acceptable']:.0%}",
            f"[{entry['acceptable_ci'][0]:.2f}, {entry['acceptable_ci'][1]:.2f}]",
        ]
        for name, entry in per.items()
    ]

    changed = sum(entry["behaviour"]["changed"] for entry in per.values())
    unclear = sum(entry["behaviour"]["unclear"] for entry in per.values())
    behaviour = (
        "Asnjë rishkrim i lexuar nuk u gjykua se e ndryshon sjelljen."
        if not changed
        else f"{_opens(_rewrites(changed))} u gjykua se e ndryshon sjelljen, çka është "
        "dështim i parakushteve dhe raportohet si i tillë."
        if changed == 1
        else f"{_opens(_rewrites(changed))} u gjykuan se e ndryshojnë sjelljen, çka është "
        "dështim i parakushteve dhe raportohet si i tillë."
    )
    if unclear:
        # «Të tjera» pas «asnjë» nuk qëndron: kur numri i ndryshimeve është zero,
        # nuk ka asgjë ndaj së cilës këto të jenë «të tjera».
        if changed:
            which = "një tjetër" if unclear == 1 else f"{unclear} të tjera"
        else:
            which = "një prej tyre" if unclear == 1 else f"{unclear} prej tyre"
        behaviour += (
            f" Për {which} rishikuesi nuk e dalloi dot nga leximi; kjo "
            "numërohet veç, sepse një rishikues që nuk e dallon dot nuk do ta "
            "pranonte as atë."
        )

    paragraphs: list = [
        f"Sipas rubrikës së Nënkapitullit 4.7 u lexua një mostër e mbjellë prej "
        f"{data['drawn']} rishkrimesh, {data['per_refactoring']} për çdo transformim.",
        ("table", "Pranueshmëria e rishkrimeve sipas rishikuesit",
         ["Transformimi", "Të lexuara", "Ashtu si është", "Pas ndreqjeje",
          "Të refuzuara", "Të pranueshme", "IB 95%"], rows),  # fmt: skip
        behaviour,
        _quality_shortfall(
            sum(e["benefit"]["neutral"] + e["benefit"]["worsens"] for e in per.values()),
            data["reviewed"],
        ),
    ]

    pooled = data.get("acceptable_reweighted")
    if pooled is not None:
        paragraphs.append(
            f"E ripeshuar me madhësitë reale të shtresave, norma e pranueshmërisë mbi "
            f"tërë vendet e rishkruara është {pooled:.1%}.",
        )

    table = data.get("acceptance_by_verdict")
    if table:
        paragraphs.append(_verdict_separates(table))
    return paragraphs


def _severity_direction(rules: dict, smells: list) -> str:
    """Në cilin drejtim ndryshon recall-i i strategjive mes rasteve major dhe minor.

    Lexohet nga të dhënat. Fjalia e shkruar me dorë që qëndronte këtu thoshte se
    detektorët i kapin rastet e rënda më mirë se të lehtat, ndërsa te Blob-i recall-i
    te major është gjysma e atij te minor (VD-117).
    """
    higher, reverse = 0, []
    for smell in smells:
        by_severity = rules["per_smell"][smell].get("strategy", {}).get("recall_by_severity") or {}
        if "major" not in by_severity or "minor" not in by_severity:
            continue
        major, minor = by_severity["major"], by_severity["minor"]
        if major["caught"] / major["support"] > minor["caught"] / minor["support"]:
            higher += 1
        else:
            reverse.append(SMELL_SQ[smell])
    text = (
        f"{_opens(_among(higher, higher + len(reverse)))}, strategjia e botuar i kap "
        "rastet major më shpesh se ato minor"
    )
    if reverse:
        text += f"; për {', '.join(reverse)} ndodh e kundërta"
    return text + "."


def _precision_over_recall(rules: dict, smells: list) -> str:
    """Brezi i precizionit dhe i recall-it të strategjive, i lexuar nga të dhënat.

    Zëvendëson fjalinë «kur strategjitë ndezin, kanë më shpesh të drejtë sesa
    gabim», e cila ishte lexim i tabelës dhe jo fakt i saj; leximi është te
    Kapitulli 6 (VD-125).
    """
    rows = [rules["per_smell"][smell]["strategy"]["by_aggregation"]["mean"] for smell in smells]
    above = sum(1 for row in rows if row["precision"] > row["recall"])
    precision = [row["precision"] for row in rows]
    recall = [row["recall"] for row in rows]
    return (
        f"Precizioni i strategjive është mbi recall-in {_among(above, len(rows))}: "
        f"precizioni shkon nga {min(precision):.3f} deri në {max(precision):.3f}, "
        f"recall-i nga {min(recall):.3f} deri në {max(recall):.3f}."
    )


def _who_is_higher(rules: dict, ml: dict, smells: list) -> str:
    """Te sa erëra Qasja B ka MCC më të lartë se Qasja A."""
    higher = [
        smell
        for smell in smells
        if ml["per_smell"][smell]["models"][ml["per_smell"][smell]["best_model"]]["mcc"]
        > rules["per_smell"][smell]["strategy"]["by_aggregation"]["mean"]["mcc"]
    ]
    return (
        f"Qasja B ka MCC më të lartë se Qasja A {_among(len(higher), len(smells))}. "
        "Pajtimi mes tyre matet me koeficientin kappa dhe me numrin e "
        "mostrave që shënon secila qasje, vetëm ose bashkë me tjetrën."
    )


def _only_rules_vs_only_model(ml: dict, smells: list) -> str:
    """Sa raste kap vetëm njëra qasje, erë për erë, nga të dhënat.

    Fjalia e mëparshme e quante «të krahasueshëm» numrin që rregulli kap vetëm te
    Feature Envy, ndërsa të dhënat japin 13 kundrejt 54 (VD-125).
    """
    # Numrat vetë janë te kolonat e tabelës; fjalia thotë vetëm modelin që ato
    # formojnë, që të mos rishtypë tabelën rresht për rresht (VD-129).
    only = {smell: ml["per_smell"][smell]["vs_rules"] for smell in smells}
    more = sum(1 for smell in smells if only[smell]["only_model"] > only[smell]["only_rules"])
    widest = max(smells, key=lambda s: only[s]["only_rules"] / max(only[s]["only_model"], 1))
    return (
        f"{_opens(_among(more, len(smells)))}, mostrat që shënon vetëm B janë më të "
        "shumta se ato që shënon vetëm A. Raporti më i afërt mes të dyjave është te "
        f"{SMELL_SQ[widest]}, {only[widest]['only_rules']} me "
        f"{only[widest]['only_model']}."
    )


def _overturned(regressions: int, total: int) -> str:
    """What the project-context pass says about rewrites that looked safe alone.

    Written as a branch rather than a sentence with a number in it, because the
    two outcomes mean opposite things and the earlier draft asserted the good one
    in prose while reading the number from the data. When the sample was doubled
    and the count moved from zero to one, that paragraph began contradicting
    itself: it claimed nothing had been overturned and then printed how many had.
    """
    if not regressions:
        return (
            "Asnjë verdikt nuk u përmbys: asnjë rishkrim që nuk shtonte gabim të ri i "
            "izoluar nuk shton brenda projektit të vet."
        )
    if regressions == 1:
        return (
            f"Një rishkrim nga {total} nuk shtonte lloj të ri gabimi i izoluar, por shton "
            "brenda projektit të vet." + _overturned_case()
        )
    return (
        f"{_opens(_word(regressions))} rishkrime nga {total} nuk shtonin lloj të ri gabimi "
        "të izoluara, por shtojnë brenda projektit të vet." + _overturned_case()
    )


def _overturned_case() -> str:
    """Cili rishkrim është, tani që rreshtat për-rishkrim ruhen.

    Kjo fjali qëndroi muaj si «rasti nuk u veçua». Ai ishte pohim i vërtetë për
    një matje që i hidhte rreshtat kur mbaronte me sukses (VD-55); ekzekutimi i
    dytë i ruajti, dhe rasti u emërtua. Lexohet nga skedari e nuk shtypet, që të
    mos rrijë i vjetruar po të ndryshojë mostra.
    """
    rows = _rows_if_present("verify_with_project_samples.csv")
    if rows is None:
        return ""
    overturned = [
        row for row in rows if row["alone"] == "no_new_errors" and row["in_project"] == "new_errors"
    ]
    if not overturned:
        return ""
    # Shkaku u veçua vetëm për rastin e Ambari-t, në matjen e parë; për të tjerët
    # skedari mban verdiktin e jo mesazhin e kompilatorit, ndaj nuk pohohet (VD-130).
    if len(overturned) == 1 and overturned[0]["class_name"] == "AlertSummaryRenderer":
        where = f"{overturned[0]['class_name']}.{overturned[0]['method']}"
        return (
            f" Rasti është një Extract Method mbi {where} te «AlertSummaryRenderer.java» "
            "e projektit Ambari, dhe të tria gabimet që shton janë paketa të palëve të "
            "treta që mungojnë në korpus."
        )
    named = [
        f"{REWRITE_OF_SMELL.get(row['smell'], row['smell'])} mbi "
        f"{row['class_name']}.{row['method']} në projektin «{_project_of(row['file'])}»"
        for row in overturned
    ]
    noun = "Rasti është" if len(named) == 1 else "Rastet janë"
    # Që nga VD-137 rreshti mban edhe gabimet që rishkrimi shtoi brenda projektit.
    # Një matje e vjetër pa këtë kolonë e thotë hapur që shkaku nuk u veçua.
    causes = [row.get("new_in_project", "").strip() for row in overturned]
    if not all(causes):
        return (
            f" {noun} {_joined(named)}. Skedari i matjes mban verdiktin e jo mesazhin e "
            "kompilatorit, ndaj shkaku i tyre nuk u veçua."
        )
    # Një rresht mund të mbajë disa gabime, të ndara me «|»; lexuesit i duhen të
    # veçanta dhe pa përsëritje.
    messages = dict.fromkeys(
        message.strip() for cause in causes for message in cause.split("|") if message.strip()
    )
    quoted = _joined([f"«{message}»" for message in messages])
    return f" {noun} {_joined(named)}. Gabimet që shtojnë janë {quoted}."


# Transformimi që motori aplikon për secilën erë, për emrat e rasteve.
REWRITE_OF_SMELL = {
    "LongMethod": "Extract Method",
    "BrainMethod": "Extract Method",
    "DeepNesting": "Guard Clauses",
    "LongParameterList": "Introduce Parameter Object",
}


def _project_of(file_path: str) -> str:
    """«apache__hive__2fa22bf36089» te shtegu i korpusit bëhet «hive».

    Shtegu është relativ ndaj rrënjës së korpusit që nga VD-137, ndaj dosja e
    projektit është pjesa e parë. Rezultatet e vjetra mbanin shtegun absolut, dhe
    aty dosja është ajo pas «corpus».
    """
    parts = file_path.replace("\\", "/").split("/")
    if "corpus" in parts and parts.index("corpus") + 1 < len(parts):
        folder = parts[parts.index("corpus") + 1]
    else:
        folder = parts[0]
    pieces = folder.split("__")
    return pieces[1] if len(pieces) > 1 else folder


def _project_context_paragraphs() -> list:
    """Sa do të forcohej verdikti po të kompilohej skedari brenda projektit.

    Verifikimi i mësipërm e kompilon skedarin të vetëm, dhe shumica e skedarëve
    të një depoje reale nuk kompilojnë ashtu. Kjo mat çmimin e asaj zgjedhjeje
    duke e bërë ndryshe mbi një mostër.
    """
    data = _load_if_present("verify_with_project.json")
    if data is None:
        return []

    alone = data["compiled_alone"]
    context = data["compiled_in_project"]
    total = data["rewrites"]
    # Emrat e verdikteve mbeten si te tabela ngjitur, që i njëjti verdikt të mos
    # shkruhet në dy mënyra në dy tabela që lexohen bashkë.
    rows = [
        [VERDICT_SQ.get(name, name.replace("_", " ")), str(alone.get(name, 0)),
         str(context.get(name, 0))]
        for name in sorted(set(alone) | set(context))
    ]

    compiles_alone = alone.get("compiles", 0)
    compiles_context = context.get("compiles", 0)
    unchecked = context.get("not_checked", 0)
    regressions = context.get("new_errors", 0)

    return [
        "Mbi mostrën e mbjellë të Nënkapitullit 4.7, prej "
        f"{data['files_checked']} skedarësh dhe {total} rishkrimesh, i njëjti rishkrim u "
        "kompilua i vetëm dhe brenda projektit të vet.",
        ("table", "Verdikti i të njëjtave rishkrime, të izoluara dhe brenda projektit",
         ["Verdikti", "I izoluar", "Brenda projektit"], rows),  # fmt: skip
        f"Verdikti «kompilon» kalon nga {compiles_alone} te {compiles_context} nga "
        f"{total} rishkrime, pra nga {compiles_alone / total:.1%} në "
        f"{compiles_context / total:.1%}.",
        _overturned(regressions, total) + _unchecked_sentence(unchecked),
    ]


def _unchecked_sentence(unchecked: int) -> str:
    """Pse një kompilim mbetet pa verdikt, dhe si numërohet.

    Kjo fjali i atribuohej vetëm kufirit kohor. Që nga VD-138 një `javac` që
    dështon pa emërtuar gabim mbi burimin nuk lexohet më si kompilim i pastër,
    ndaj edhe ai bie tek «i pakontrolluar», dhe matja nuk i ndan dot të dyja.
    """
    if not unchecked:
        return ""
    if unchecked == 1:
        return (
            " Një kompilim mbeti pa verdikt, nga kufiri kohor ose nga një javac që "
            "dështoi pa emërtuar gabim, dhe numërohet si i pakontrolluar, kurrë si sukses."
        )
    return (
        f" {_opens(_word(unchecked))} kompilime mbetën pa verdikt, nga kufiri kohor ose "
        "nga një javac që dështoi pa emërtuar gabim, dhe numërohen si të pakontrolluara, "
        "kurrë si sukses."
    )


def _refusal_severity_paragraphs() -> list:
    """Ku refuzon motori: te rastet e buta apo te ato të rënda?

    Norma e vetme e transformimit nuk e dallon një mjet që rishkruan gjithçka lehtë nga një
    që tërhiqet pikërisht aty ku kodi është më i keq. Kjo është pyetja tjetër, dhe
    përgjigjja e saj nuk lexohet dot nga tabela e mësipërme.
    """
    data = _load_if_present("refusals_by_severity.json")
    if data is None:
        return []

    per_smell = data["per_smell"]
    overall = data["overall"]
    rows = []
    for smell in sorted(per_smell):
        for level in ("critical", "major", "minor"):
            cell = per_smell[smell].get(level)
            if cell is None or cell["application_rate"] is None:
                continue
            judged = cell["applied"] + cell["refused"]
            rows.append(
                [_named(smell), level, _count(judged), _count(cell["applied"]),
                 f"{cell['application_rate']:.1%}"]
            )  # fmt: skip

    lowest = {}
    for smell, levels in per_smell.items():
        rates = {
            name: c["application_rate"]
            for name, c in levels.items()
            if c["application_rate"] is not None
        }
        if rates:
            lowest[smell] = min(rates, key=lambda name: rates[name])
    critical_lowest = sum(1 for name in lowest.values() if name == "critical")

    # Erërat ku niveli i mesëm rishkruhet më shpesh se i buti, nga të dhënat e jo
    # të shtypura: lidhja nuk është monotone, dhe cilat erëra e thyejnë lexohet.
    unmonotone = sorted(
        smell
        for smell, levels in per_smell.items()
        if all(levels.get(name, {}).get("application_rate") is not None for name in ("minor", "major"))
        and levels["major"]["application_rate"] > levels["minor"]["application_rate"]
    )
    return [
        f"Norma e përgjithshme e transformimit është {overall['application_rate']:.1%}. "
        "E ndarë sipas erës dhe sipas ashpërsisë që sistemi i cakton vendit, ajo "
        "shpërndahet kështu:",
        ("table", "Norma e transformimit sipas erës dhe ashpërsisë",
         ["Erë", "Ashpërsia", "Vende të gjykuara", "Të transformuara", "Norma"], rows),
        f"Niveli kritik ka normën më të ulët {_among(critical_lowest, len(lowest))}"
        + (
            f", dhe te {' dhe '.join(_named(smell) for smell in unmonotone)} niveli i mesëm ka normë më të lartë se "
            "i buti."
            if unmonotone
            else "."
        ),
        *_pooling_warning(data),
        *_refusal_reason_shift(data),
    ]


def _pooling_warning(data: dict) -> list:
    """Pse shifra e bashkuar mbi erërat nuk citohet.

    E bashkuar, ajo e përmbys shenjën e vetë matjes. Kjo nuk është hollësi
    statistikore por kusht leximi: pa të, e njëjta tabelë mbështet përfundimin e
    kundërt.
    """
    per_smell = data["per_smell"]
    pooled: dict[str, list[int]] = {"critical": [0, 0], "tjera": [0, 0]}
    for levels in per_smell.values():
        for name, cell in levels.items():
            bucket = pooled["critical" if name == "critical" else "tjera"]
            bucket[0] += cell["applied"]
            bucket[1] += cell["applied"] + cell["refused"]

    crit = pooled["critical"]
    rest = pooled["tjera"]
    if not crit[1] or not rest[1]:
        return []

    shares = []
    for smell, levels in sorted(per_smell.items()):
        judged = sum(c["applied"] + c["refused"] for c in levels.values())
        applied = sum(c["applied"] for c in levels.values())
        critical = levels.get("critical")
        share = ((critical["applied"] + critical["refused"]) / judged) if critical else 0.0
        shares.append((smell, applied / judged if judged else 0.0, share))

    # Zgjedhur sipas peshës së vendeve kritike e jo sipas normës, sepse mekanizmi
    # është pikërisht ai: era që sjell më shumë vende kritike në bashkim është
    # edhe ajo që rishkruhet lehtë, ndaj bashkimi e ngre nivelin kritik.
    high = max(shares, key=lambda row: row[2])
    low = min(shares, key=lambda row: row[2])

    return [
        f"E bashkuar mbi erërat, niveli kritik del me {crit[0] / crit[1]:.1%} kundrejt "
        f"{rest[0] / rest[1]:.1%} të niveleve të tjera, renditje e kundërt me atë të "
        f"erërave veç e veç (paradoksi i Simpson-it): {_named(high[0])} ka normë "
        f"{high[1]:.1%} dhe {high[2]:.1%} vende kritike, ndërsa {_named(low[0])} ka {low[1]:.1%} dhe "
        f"{low[2]:.1%}. Prandaj tabela nuk bashkohet.",
    ]


def _refusal_reason_shift(data: dict) -> list:
    """Ajo që lëviz me ashpërsinë nuk është sa refuzon, por pse.

    Kjo është gjetja e vërtetë e seksionit: monotone, e madhe, dhe me shpjegim
    mekanik në vetë përkufizimin e transformimit.
    """
    per_smell = data["per_smell"]
    totals: dict[str, dict[str, int]] = {}
    for levels in per_smell.values():
        for name, cell in levels.items():
            bucket = totals.setdefault(name, {})
            for reason, count in cell["refused_by_reason"].items():
                bucket[reason] = bucket.get(reason, 0) + count

    order = [name for name in ("minor", "major", "critical") if totals.get(name)]
    if len(order) < 2:
        return []

    reasons = sorted(
        {reason for bucket in totals.values() for reason in bucket},
        key=lambda reason: -sum(bucket.get(reason, 0) for bucket in totals.values()),
    )
    rows = []
    for reason in reasons:
        cells = []
        for name in order:
            bucket = totals[name]
            total = sum(bucket.values())
            cells.append(f"{bucket.get(reason, 0) / total:.0%}" if total else "-")
        rows.append([reason.replace("_", " "), *cells])

    return [
        "Brenda çdo niveli ashpërsie, arsyet e refuzimit kanë këtë përbërje:",
        ("table", "Përbërja e arsyeve të refuzimit brenda çdo niveli",
         ["Arsyeja", *order], rows),
        _reason_trend(totals, order),
    ]


def _reason_trend(totals: dict[str, dict[str, int]], order: list[str]) -> str:
    """Si ndryshojnë dy arsyet kryesore nga niveli më i butë te më i rëndi."""

    def share(level: str, reason: str) -> float:
        total = sum(totals[level].values())
        return totals[level].get(reason, 0) / total if total else 0.0

    first, last = order[0], order[-1]
    return (
        f"Nga niveli {first} te {last}, pjesa e refuzimeve për formën e kodit "
        f"(shape not matched) kalon nga {share(first, 'shape_not_matched'):.0%} në "
        f"{share(last, 'shape_not_matched'):.0%}, ndërsa ajo për rrjedhën e kontrollit "
        f"(control flow escapes) nga {share(first, 'control_flow_escapes'):.0%} në "
        f"{share(last, 'control_flow_escapes'):.0%}."
    )


def _resolution_paragraphs(data: dict) -> list:
    """A rishkroi motori erën, apo thjesht kodin?

    Verifikimi i mësipërm tregon se rishkrimi nuk e prish skedarin. Kjo është
    pyetja tjetër, dhe përgjigjet e tyre nuk përkojnë: një transformim mund të
    jetë i saktë, të kompilojë, dhe ta lërë erën aty ku ishte.
    """
    counts = data.get("resolution")
    if not counts:
        return []

    total = sum(counts.values())
    rows = [
        [RESOLUTION_SQ.get(name, name), str(count), f"{count / total:.1%}"]
        for name, count in sorted(counts.items(), key=lambda p: -p[1])
    ]
    return [
        "Çdo entitet i rishkruar u mat sërish, për të parë nëse detektori ende ndez "
        "mbi të.",
        ("table", "A u hoq era pas rishkrimit",
         ["Rezultati", "Numri", "Pjesa e të aplikuarave"], rows),
        *_metric_shift_paragraphs(data),
        *_introduced_paragraphs(data),
    ]


def _metric_shift_paragraphs(data: dict) -> list:
    """Sa lëvizi matja, edhe atje ku era mbeti.

    Pa këtë shifër, «era mbeti» dhe «asgjë nuk ndryshoi» lexohen njësoj, dhe nuk
    janë e njëjta gjë.
    """
    shift = data.get("metric_shift")
    if not shift:
        return []

    rows = [
        [
            _named(smell),
            entry["metric_before"] and f"{entry['metric_before']:g}",
            f"{entry['metric_after']:g}",
            _count(entry["sites"]),
        ]
        for smell, entry in sorted(shift.items())
    ]
    return [
        "Edhe metrika që e ndez detektorin u mat para dhe pas; mesoret mbi vendet e "
        "aplikuara janë:",
        ("table", "Sa lëvizi matja pas rishkrimit",
         ["Erë", "Para", "Pas", "Vende"], rows),
    ]


def _introduced_paragraphs(data: dict) -> list:
    """A e shkëmbeu motori një erë me një tjetër?"""
    introduced = data.get("introduced_smells")
    if not introduced:
        return []

    total = sum(introduced.values())
    listed = ", ".join(
        f"{_named(name)} ({count})" for name, count in sorted(introduced.items())
    )
    return [
        f"Pas rishkrimit u shfaqën {total} erëra që nuk ishin aty më parë: {listed}.",
    ]


# ======================================================================
# Kapitulli 8: shtojcat
# ======================================================================
# Çfarë do të thotë secila arsye refuzimi. Vlerat vijnë nga kodi; kuptimi
# shkruhet këtu, sepse është shpjegim për lexuesin dhe jo e dhënë e sistemit.
# Një arsye e re pa shpjegim del e shënuar në dokument dhe jo e heshtur.
REFUSAL_SQ = {
    "unresolved_name": (
        "Një emër, deklarimin e të cilit analiza nuk e gjen dot. Parser-i regjistron "
        "fakte sintaksore dhe me qëllim nuk është zgjidhës simbolesh."
    ),
    "possible_side_effect": (
        "Zhvendosja mund ta ndryshojë sjelljen, sepse diçka brenda mund të shkruajë "
        "gjendje ose të kryejë hyrje-dalje."
    ),
    "ambiguous_overload": "Disa metoda e ndajnë emrin dhe thirrja nuk lidhet dot me njërën.",
    "multiple_outputs": (
        "Blloku cakton më shumë se një variabël që lexohet pas tij, ndaj një vlerë e "
        "vetme kthimi nuk e nxjerr dot rezultatin jashtë."
    ),
    "control_flow_escapes": (
        "Një return, break ose continue del nga blloku, ndaj blloku nuk është shprehje "
        "dhe nuk ngrihet i tëri."
    ),
    "shape_not_matched": (
        "Kodi nuk e ka formën që ky transformim rishkruan. Nuk është dështim i "
        "analizës, por mjet i gabuar për atë vend."
    ),
    "edit_conflict": (
        "Dy editime kërkuan të njëjtat bajta. Gjithmonë defekt i transformimit që i "
        "prodhoi, dhe raportohet që të mos kalojë pa u vënë re."
    ),
    "not_definitely_assigned": (
        "Një vlerë që blloku e lexon është deklaruar por jo caktuar me siguri aty ku "
        "blloku ndodhet. Java e ndalon kalimin e saj, ndaj rishkrimi nuk do të "
        "kompilonte edhe pse përndryshe është i saktë."
    ),
    "unparseable": "Skedari nuk u parsua i pastër, ndaj asgjë për të nuk është e provuar.",
}

# Radha e ekzekutimit të eksperimenteve, me kohët e matura në një laptop pa GPU.
# Çdo hap veç 1 dhe 7 u krye dhe u krono më 2026-09-03. Hapi 1 kërkon rishkarkimin
# e korpusit; hapi 7 disa orë. Disa shifra dolën të gabuara në atë matje dhe u
# ndreqën: hapi 3 shkruante «~95 min» për 56, hapi 5 shkruante «sekonda» për 190
# sekonda pune, dhe hapi 8 shkruante «~1 min» për nëntë. Hapi 12 nuk merr dot
# shifër: kostoja e tij shkon sipas rishkrimit e jo sipas skedarit, dhe skedarët
# janë aq të pabarabartë — njëri mban 118 rishkrime — sa dyfishimi i mostrës nga 30
# skedarë në 60 e rriti punën nga 152 rishkrime në 405.
REPRODUCTION = [
    ("1", "fetch_corpus.py", "korpusi, jashtë git-it", "orë, një herë"),
    ("2", "report_matching.py", "mbulimi i përputhjes MLCQ↔entitet", "~2 min"),
    ("3", "build_dataset.py", "tabela e veçorive, e komituar", "~56 min"),
    ("4", "evaluate_rules.py --from-dataset data/results/mlcq_dataset.csv",
     "numrat e Qasjes A", "sekonda"),
    ("5", "train_models.py", "numrat e Qasjes B dhe modelet", "~3 min"),
    ("6", "sweep_thresholds.py", "analiza e ndjeshmërisë", "sekonda"),
    ("7", "evaluate_refactorings.py", "tabela N/M/K e Qasjes C", "orë"),
    ("8", "calibrate_thresholds.py", "pragjet e kalibruara jashtë fold-it", "sekonda"),
    ("9", "reviewer_agreement.py", "tavani i pajtimit mes rishikuesve", "sekonda"),
    ("10", "bootstrap_intervals.py", "intervalet e besimit", "nën një minutë"),
    ("11", "refusals_by_severity.py", "refuzimet sipas erës dhe ashpërsisë", "~2 min"),
    ("12", "verify_with_project.py", "verdikti brenda kontekstit të projektit", "orë"),
    ("13", "model_without_project.py", "Qasja B pa kontekstin e projektit", "~2 min"),
    ("14", "export_system_reference.py", "tabelat e kësaj shtojce", "sekonda"),
    ("15", "build_figures.py", "figurat e Kapitujve 4 dhe 5", "sekonda"),
    ("16", "review_rewrites.py --sample", "mostra e rishkrimeve dhe fleta e vlerësimit",
     "sekonda"),
    ("17", "review_rewrites.py --score", "cilësia e rishkrimeve sipas rishikuesit", "sekonda"),
    ("18", "fetch_pmd.py", "mjeti i jashtëm i krahasimit, jashtë git-it", "minuta, një herë"),
    ("19", "compare_with_pmd.py", "krahasimi me PMD-në mbi të njëjtat mostra", "orë"),
    ("20", "blocking_conditions.py", "cila klauzolë e ndal secilën strategji", "sekonda"),
    ("21", "blob_recall.py", "çfarë mbetet pa u kapur te Blob-i", "sekonda"),
    ("22", "train_strategy_features.py", "Qasja B vetëm me metrikat e strategjisë",
     "sekonda"),
]

REPOSITORY = "https://github.com/FlorentLatifi/Code-Smell-Detection-and-Refactoring-Recommendations"


def chapter_8() -> list:
    """Shtojcat, të ndërtuara nga `system_reference.json`.

    Asnjë vlerë këtu nuk shtypet me dorë. Pragjet, formulat dhe metrikat vijnë nga
    i njëjti kod që prodhoi rezultatet, ndaj një prag i ndryshuar pa u rigjeneruar
    shtojca nuk mund të kalojë i padukshëm: numri thjesht nuk ndodhet dot këtu.
    """
    reference = _load("system_reference.json")

    strategy_rows = []
    for entry in reference["strategies"]:
        strategy_rows.append(
            [
                _named(entry["smell"]),
                "klasë" if entry["scope"] == "class" else "metodë",
                entry["formula"],
                _strategy_source(entry["title"]),
            ]
        )

    quantifier_rows = [
        [name, f"{value:g}"] for name, value in sorted(reference["quantifiers"].items())
    ]
    threshold_rows = [
        [name, f"{value:g}"] for name, value in sorted(reference["thresholds"].items())
    ]

    class_metrics = reference["metrics"]["class"]
    method_metrics = reference["metrics"]["method"]
    metric_rows = [
        [f"Klasë ({len(class_metrics)})", ", ".join(class_metrics)],
        [f"Metodë ({len(method_metrics)})", ", ".join(method_metrics)],
    ]

    engine_rows = []
    for entry in reference["strategies"]:
        if entry["automated"]:
            does = f"aplikohet: {_named(entry['automated'])}"
        elif entry["advisory_reason"]:
            does = "vetëm propozohet"
        else:
            does = "nuk ka transformim"
        engine_rows.append(
            [_named(entry["smell"]), ", ".join(_named(r) for r in entry["refactorings"]), does]
        )

    refusal_rows = [
        [reason.replace("_", " "),
         REFUSAL_SQ.get(reason, "[PLOTËSO: arsye e re, pa shpjegim në shtojcë]")]
        for reason in reference["refusal_reasons"]
    ]

    commits, pythons, platforms = _provenance()
    # Joined rather than asserted: if a result were ever regenerated on another
    # machine, the appendix should say so instead of quoting one of the two.
    python_version = ", ".join(sorted(pythons))
    platform = ", ".join(sorted(platforms))

    return [
        (
            "8.1",
            "Strategjitë e detektimit",
            [
                "Tabela jep të tetë strategjitë ashtu si i zbaton sistemi. Kushtet janë "
                "ato të shkruara në kodin e detektorit dhe nxirren prej tij kur ndërtohet "
                "ky dokument, jo të kopjuara me dorë.",
                (
                    "table",
                    "Strategjitë e detektimit dhe burimet e tyre",
                    ["Erë", "Fusha", "Kushtet", "Burimi"],
                    strategy_rows,
                ),
                "Emrat me shkronja të mëdha te kolona e kushteve janë kuantifikuesit e "
                "Lanza & Marinescu-t, vlerat e të cilëve jepen më poshtë.",
            ],
        ),
        (
            "8.2",
            "Kuantifikuesit dhe pragjet",
            [
                "Strategjitë janë shkruar në një fjalor kuantifikuesish e jo në numra të "
                "veçantë. Vlerat numerike pas tyre vijnë nga statistikat e metrikave mbi "
                "dyzet e pesë sisteme Java.",
                (
                    "table",
                    "Kuantifikuesit e përgjithshëm",
                    ["Emri", "Vlera"],
                    quantifier_rows,
                ),
                "Poshtë janë pragjet me të cilat u prodhuan rezultatet e Kapitullit 5. "
                "Secili prej tyre është një nga ata që analiza e ndjeshmërisë i "
                "zhvendos, një nga një.",
                (
                    "table",
                    "Pragjet e përdorura",
                    ["Parametri", "Vlera"],
                    threshold_rows,
                ),
            ],
        ),
        (
            "8.3",
            "Metrikat e matura",
            [
                "Çdo entitet matet një herë dhe të gjitha metrikat shkojnë në tabelën e "
                "veçorive, edhe ato që asnjë strategji nuk i përdor: modelet e Qasjes B "
                "i shohin të gjitha, dhe pikërisht kjo e bën të përgjigjshme pyetjen nëse "
                "ato zgjedhin metrikat e strategjive. Kuptimi i shkurtesave jepet te "
                "Fjalori i termave.",
                (
                    "table",
                    "Metrikat sipas nivelit",
                    ["Niveli", "Metrikat"],
                    metric_rows,
                ),
            ],
        ),
        (
            "8.4",
            "Refaktorimet dhe arsyet e refuzimit",
            [
                "Kolona e fundit dallon çka propozon sistemi nga çka aplikon. Dallimi nuk "
                "vjen nga koha e zhvillimit: transformimet e mbetura kërkojnë gjetjen e "
                "çdo reference në projekt, çka analiza sintaksore nuk e provon dot.",
                (
                    "table",
                    "Çka propozohet dhe çka aplikohet",
                    ["Erë", "Refaktorimet e Fowler-it", "Motori"],
                    engine_rows,
                ),
                "Kur një parakusht nuk provohet, motori refuzon me një arsye të "
                "numërueshme. Shpërndarja e tyre mbi korpus jepet te Kapitulli 5.",
                (
                    "table",
                    "Arsyet e refuzimit",
                    ["Arsyeja", "Kuptimi"],
                    refusal_rows,
                ),
            ],
        ),
        (
            "8.5",
            "Riprodhimi i rezultateve",
            [
                f"Kodi burimor është i hapur te {REPOSITORY}. Skriptet ekzekutohen në "
                "këtë radhë; hapi i parë kërkon qasje në internet, të tjerët jo.",
                (
                    "table",
                    "Radha e ekzekutimit",
                    ["#", "Skripti", "Prodhon", "Kohë"],
                    [list(row) for row in REPRODUCTION],
                ),
                "Çdo skript shkruan rezultatin si CSV ose JSON në data/results/, bashkë me "
                "commit-in, versionin e Python-it dhe platformën që e prodhuan. Interpretuesi "
                f"dhe platforma janë të njëjtët për të gjithë: Python {python_version}, "
                f"{platform}. Commit-i jo: eksperimentet u ekzekutuan njëri pas tjetrit, ndaj "
                "secili skedar mban commit-in e vet, dhe ai duhet përdorur për ta riprodhuar.",
                (
                    "table",
                    "Commit-i që prodhoi çdo skedar rezultati",
                    ["Skedari", "Commit-i"],
                    [[name, commit[:10]] for name, commit in sorted(commits.items())],
                ),
                "Kapitulli 5 dhe kjo shtojcë ndërtohen nga ata skedarë, ndaj rigjenerimi i "
                "eksperimentit dhe rigjenerimi i dokumentit japin gjithmonë të njëjtat "
                "vlera.",
                "Ky premtim u vu në provë më 3 shtator 2026. Trembëdhjetë nga pesëmbëdhjetë "
                "hapat që kishte atëherë tabela u ri-ekzekutuan mbi të njëjtat hyrje, dhe të gjithë, me një "
                "përjashtim, dhanë skedarë identikë me të komituarit, veç commit-it dhe "
                "kohëzgjatjes që regjistrojnë. Tabela e veçorive, 4534 rreshta, doli bajt "
                "për bajt identike; po ashtu të katër modelet e stërvitura, dhe asnjë figurë "
                "nuk ndryshoi.",
                "Përjashtimi është hapi i dymbëdhjetë. Ai riprodhoi numrat që mbajnë "
                "pretendimin — po aq rishkrime, po aq verdikte «kompilon», asnjë përmbysje — "
                "por pesë kompilime që herën e parë e kaluan kufirin kohor, herën e dytë "
                "morën verdikt: ndarja mes «i kontrolluar» dhe «i pakontrolluar» varet nga "
                "ngarkesa e makinës. Ai riprodhim i përket mostrës së atëhershme prej 30 "
                "skedarësh; mostra u dyfishua më vonë në 60 skedarë, dhe Kapitulli 5 "
                "raporton matjen e saj më të fundit.",
                "Hapi 7, motori mbi korpusin, u riekzekutua më vonë dhe dha të njëjtat "
                "total: po aq vende, po aq rishkrime, po aq refuzime, e njëjta ndarje sipas "
                "transformimit dhe sipas arsyes. Krahasimi rresht për rresht nxori "
                "megjithatë 21 verdikte kompilimi të ndryshuara, dhe ato çuan te një defekt "
                "i vërtetë: një javac që dështon pa emërtuar gabim mbi burimin lexohej si "
                "kompilim i pastër, pra 19 rishkrime ishin regjistruar si «kompilon» mbi "
                "skedarë që nuk kompilojnë. Pas ndreqjes, kjo shtojcë dhe Kapitulli 5 "
                "raportojnë matjen e re. Vlera e riprodhimit qëndron pikërisht këtu: totalet "
                "përkonin, dhe defekti u pa vetëm sepse u krahasua çdo rresht.",
                "Hapi 1 mbetet i pariekzekutuar, sepse kërkon rishkarkimin e korpusit të "
                "plotë; për të riprodhimi mbetet pretendim i pakontrolluar, dhe thuhet këtu "
                "si i tillë.",
            ],
        ),
    ] + secondary_results()
